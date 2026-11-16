#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F4 パッチツール: 上流 com.unity.addressables の C# にアンカー検索＋置換で独自修正を当てる（1ファイル）。

使い方: python3 apply_patches.py --target <パッケージのルート> [--include ID[,ID...]] [--dry-run]
終了コード: 0=成功 / 1=ERROR パッチが失敗（何も書かない） / 2=target が com.unity.addressables ではない・patches.json の不備

1回の実行の流れ:
  1. main: target/package.json の name を確認 → load_patches()＝patches.json（--include で絞り込み）を順に処理
  2. apply_patch: パッチ内の編集（カード snippets/<上流のファイルパス>/*.cs）をファイルごとにまとめる
  3. apply_file: `// f4-patch:<id>` が必要数あれば何もしない(ALREADY)。一部だけなら失敗。無ければ編集を順に適用
  4. 各編集 op（replace / insert-after / insert-in-block）はテキストからアンカーをちょうど1件探し、書き換える
  5. 1パッチ内で失敗したらそのパッチは何も変えない（WARN は skip して続行）。ERROR が1つでもあれば全体で何も書かない
  6. ERROR が無ければ、変更のあったファイルだけ書き込む（--dry-run なら書かない）
"""
import argparse
import json
import os
import re
import sys
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
PATCHES_JSON = os.path.join(HERE, "patches.json")
ERROR, WARN = "ERROR", "WARN"
BOM = b"\xef\xbb\xbf"
PACKAGE = "com.unity.addressables"


class PatchError(Exception):
    """パッチ適用の失敗（理由は1行の短い文）。"""


def load_patches():
    """patches.json を読み、検証済みのパッチ定義のリストを返す。不備は PatchError（理由は1行）。"""
    try:
        with open(PATCHES_JSON, "rb") as f:
            patches = json.loads(f.read().decode("utf-8-sig"))
        if not isinstance(patches, list) or not all(isinstance(p, dict) for p in patches):
            raise ValueError("オブジェクトの配列ではありません")
    except (OSError, ValueError) as err:
        raise PatchError("patches.json が読めません: " + str(err).replace("\n", " "))
    seen = set()
    for p in patches:  # 定義の検証（ID重複・必須キー欠落・severity不正・cards空）
        pid = p.get("patchId")
        missing = [k for k in ("patchId", "severity", "description", "cards") if not p.get(k)]
        if pid in seen or missing or p["severity"] not in (ERROR, WARN):
            raise PatchError("パッチIDが重複: {0}".format(pid) if pid in seen else
                             "パッチ定義に {0} がありません: {1}".format(missing[0] if missing else "severity(ERROR/WARN)", pid))
        seen.add(pid)
    return patches


# --- テキスト部品（括弧は TOKEN でコメント・文字列を飛ばして数える） ---
TOKEN = re.compile(r"""
    //[^\n]*                          # 行コメント      // { を無視
  | /\*.*?\*/                         # ブロックコメント /* } */
  | @"(?:[^"]|"")*"                   # verbatim 文字列 @"{ "" }"
  | (?P<q>"{3,}).*?(?P=q)             # raw 文字列      三連引用符で囲む { }
  | "(?:\\.|[^"\\\n])*"               # 通常の文字列    "}" や "a\\"b"
  | '(?:\\.|[^'\\\n])*'               # 文字リテラル    '{'
  | [{}()\[\];]                       # 括弧（これだけ数える）
""", re.S | re.X)


def brackets(text, start):
    """start 以降の括弧トークン `{ } ( ) [ ] ;` を (文字, 位置) で順に返す（コメント・文字列の中身は出ない）。"""
    for m in TOKEN.finditer(text, start):
        if m.group() in "{}()[];":
            yield m.group(), m.start()


def match_brace(text, i):
    """text[i] の `{` に対応する `}` の位置。 `{ a { b } }` の先頭 `{` なら末尾 `}` の位置。"""
    depth = 0
    for c, k in brackets(text, i):
        depth += (c == "{") - (c == "}")
        if depth == 0:
            return k
    raise PatchError("括弧の対応が取れない")


def expr_end(text, i):
    """i 以降で、括弧の深さ 0 の最初の ';' の位置。 `Foo(a; b) ?? c;` の末尾 ';'（括弧内の ';' は数えない）。"""
    depth = 0
    for c, k in brackets(text, i):
        depth += (c in "([{") - (c in ")]}")
        if c == ";" and depth <= 0:
            return k
    raise PatchError("式の終端 ';' が無い")


def line_start(text, pos):
    return text.rfind("\n", 0, pos) + 1


def indent_of(text, pos):
    return re.compile(r"[ \t]*").match(text, line_start(text, pos)).group()


def unit_of(indent):  # インデント 1 段: タブを含むならタブ、そうでなければ 4 スペース
    return "\t" if "\t" in indent else "    "


def indent_block(code, indent):
    """各行に indent を付ける（空行・空白だけの行は空にする）。 `if (a)\\n{\\n\\n}` → `    if (a)\\n    {\\n\\n    }`"""
    return re.sub(r"(?m)^.*$", lambda m: indent + m.group() if m.group().strip() else "", code)


def to_unit(code, unit):
    """カード本文の「4 スペース = 1 段」を、対象ファイルの 1 段（タブ or 4 スペース）に直す。"""
    return re.sub(r"(?m)^((?: {4})+)", lambda m: unit * (len(m.group()) // 4), code)


def fill(code, vals):
    """`{{名前}}` を vals の値に置換する（未定義の名前は KeyError → FAILED）。"""
    return re.sub(r"\{\{(\w+)\}\}", lambda m: vals[m.group(1)], code)


def find_one(text, pattern, start=0, end=None, what="アンカー", direct=False):
    """[start, end) でパターンがちょうど1件マッチすることを要求する。direct=True は start の `{` 直下（深さ1）のマッチだけ数える。"""
    found = list(re.compile(pattern, re.M).finditer(text, start, len(text) if end is None else end))
    if direct:
        found = [m for m in found if sum((c == "{") - (c == "}") for c, k in brackets(text, start) if k < m.start()) == 1]
    if len(found) != 1:
        raise PatchError("{0}が{1}件（ちょうど1件が必要）: {2}".format(what, len(found), pattern[:50]))
    return found[0]


def scope(text, e):
    """within（外側の型宣言の正規表現）があればその `{ }` の範囲、無ければ全体を返す。 `class Inner { int X; }` なら中だけ。"""
    if not e.get("within"):
        return 0, len(text)
    m = find_one(text, e["within"], what="within")
    o = text.find("{", m.end())
    if o < 0:
        raise PatchError("within の '{' が無い")
    return o, match_brace(text, o)


def locate(text, e):
    """アンカーに（within があればその直下で）ちょうど1件マッチする位置を返す。"""
    lo, hi = scope(text, e)
    return find_one(text, e["anchor"], lo, hi, direct=bool(e.get("within")))


def need(region, e):
    """requires（カンマ区切りのトークン）が region に全部あることを要求する。"""
    miss = [t.strip() for t in e["requires"].split(",") if t.strip() not in region]
    if miss:
        raise PatchError("前提のトークンが無い: " + ", ".join(miss))


def extend(text, pos, kind):
    """アンカーの終端 pos から、kind に応じて範囲を伸ばした終端と、expr 用の式テキストを返す。

    block: 次の `{` を対にした `}` まで（先に `;` / `=>` が来たら失敗）  `int X { get; }`  → `}` の直後
    expr : 次の深さ0の `;` まで、式は {{expr}} 用   `int X => a + b;`      → `;` の直後、expr=`a + b`
    stmt : 次の文（`{...}` か `...;`）まで           `if (c)\\n  F();`      → `;` の直後
    """
    if not kind:
        return pos, None
    if kind == "block":
        s = re.compile(r"[{;]|=>").search(text, pos)
        if s is None or s.group() != "{":
            raise PatchError("本体が波括弧ブロックではない")
        return match_brace(text, s.start()) + 1, None
    i = len(text) - len(text[pos:].lstrip())
    if kind == "stmt":
        return (match_brace(text, i) if text[i:i + 1] == "{" else expr_end(text, i)) + 1, None
    if kind == "expr":
        semi = expr_end(text, i)
        return semi + 1, text[i:len(text[:semi].rstrip())]
    raise PatchError("未知の extend: " + kind)


# --- op（3種類）: op(text, e, pid) -> 新しい text ---
def op_replace(text, e, pid):
    """アンカー（extend で伸ばした範囲）を本文で置き換える。本文の {{match}}=元の範囲, {{expr}}, {{marker}}, {{グループ名}} が使える。

    Before:  public class Foo            アンカー (?P<mods>public\\s+)(?P<decl>class\\s+Foo\\b)
    After :  // f4-patch:<id>            本文 `{{marker}}\\n{{mods}}partial {{decl}}`
             public partial class Foo
    """
    m = locate(text, e)
    if e.get("requires"):
        need(text, e)
    end, expr = extend(text, m.end(), e.get("extend"))
    ind = indent_of(text, m.start())
    u = unit_of(ind)
    vals = {k: text[slice(*m.span(k))] for k in m.re.groupindex}
    vals.update(match=text[m.start():end], marker="// f4-patch:" + pid)
    if expr is not None:  # 2行目以降は dedent して「基準インデント + 2段」に揃える
        first, _, rest = expr.partition("\n")
        lines = textwrap.dedent(rest).split("\n") if rest else []
        vals["expr"] = "\n".join([first] + [(ind + u * 2 + l) if l.strip() else "" for l in lines])
    new = fill(indent_block(to_unit(e["body"], u), ind)[len(ind):], vals)  # 1行目は既存のインデントの後ろに入る
    return text[:m.start()] + new + text[end:]


def op_insert_after(text, e, pid):
    """アンカー（extend で伸ばした範囲）の終わる行の次に、本文を挿入する（既定は空行を挟む。blank: no で挟まない）。

    Before:  public int X { get; }
    After :  public int X { get; }
                                        ← 空行
             // f4-patch:<id>
             public int Y { get; }      ← 本文（アンカー行と同じインデント）
    """
    m = locate(text, e)
    if e.get("requires"):
        need(text, e)
    end, _ = extend(text, m.end(), e.get("extend"))
    ind = indent_of(text, m.start())
    code = fill(indent_block(to_unit(e["body"], unit_of(ind)), ind), {"marker": "// f4-patch:" + pid})
    eol = (text + "\n").find("\n", end - 1)  # アンカー終端を含む行の末尾
    return text[:eol] + "\n" + ("" if e.get("blank") == "no" else "\n") + code + text[eol:]


def op_insert_in_block(text, e, pid):
    """アンカーのメソッド本体 `{ ... }` の末尾（閉じ括弧の直前の行）に本文を挿入する。requires は本体内で判定。

    Before:  void Init()
             {
                 Setup();
             }
    After :      Setup();
                 // f4-patch:<id>
                 F4.Hook();             ← 本文（閉じ括弧のインデント + 1段）
             }
    """
    m = locate(text, e)
    end, _ = extend(text, m.end(), "block")
    close = end - 1
    if e.get("requires"):
        need(text[m.end():close], e)
    ls = line_start(text, close)
    close_ind = text[ls:close]
    if close_ind.strip():
        raise PatchError("閉じ括弧が単独行ではない")
    code = indent_block(to_unit(e["body"], unit_of(close_ind)), close_ind + unit_of(close_ind))
    return text[:ls] + fill(code, {"marker": "// f4-patch:" + pid}) + "\n" + text[ls:]


OPS = {"replace": op_replace, "insert-after": op_insert_after, "insert-in-block": op_insert_in_block}


# --- カード（snippets/<上流のファイルパス(.cs除く)>/<パッチID>[.説明].cs） ---
def card(path):
    """カードを編集 dict にする（ヘッダ `// key: 値` と `// ▼ anchor|body|before|after（説明）` の節）。アンカーは正規表現（`//` 行は読み物）。
    前/後ろの節だけのカードは 本文 = 前 + `{{match}}`（元の範囲）+ 後ろ。"""
    with open(os.path.join(HERE, "snippets", *path.split("/")), encoding="utf-8") as f:
        lines = f.read().split("\n")
    # 対象ファイルは置き場所で決まる: snippets/ からの相対パスの末尾（カード名）を除き ".cs" を付ける
    e, sec, cur = {}, {}, None
    for line in lines:
        if line.startswith("// ▼ "):
            h = re.match(r"// ▼ (anchor|body|before|after)\b", line)
            if not h:
                raise PatchError("{0}: 見出しは anchor / body / before / after のいずれかで始めてください: {1}".format(path, line))
            cur = h.group(1)
            sec[cur] = []
        elif cur:
            sec[cur].append(line)
        else:
            m = re.match(r"//\s*([\w-]+):\s*(.*?)\s*$", line)
            if m:
                e[m.group(1)] = m.group(2)
    e["card"], e["file"] = path, "/".join(path.split("/")[:-1]) + ".cs"  # file: ヘッダは無視し、置き場所を優先
    e["anchor"] = "".join(l.strip() for l in sec["anchor"] if l.strip() and not l.lstrip().startswith("//"))
    text = lambda role: "\n".join(sec[role]).rstrip("\n")  # noqa: E731
    e["body"] = text("body") if "body" in sec else text("before") + "\n{{match}}\n" + text("after")
    if e.get("trailing-newline") == "yes":  # 本文末尾の改行を残す（ファイル末尾への追記用）
        e["body"] += "\n"
    return e


# --- 適用 ---
def apply_file(text, edits, pid):
    """1ファイル分。マーカーが必要数あれば何もしない / 一部だけなら失敗 / 無ければ編集を順に適用。

    Before:  public class Foo            After(1回目): // f4-patch:<id> + public partial class Foo
    2回目: マーカーが既にあるので text をそのまま返す（ALREADY）。
    """
    n = len(re.findall(r"//[ \t]*f4-patch:" + re.escape(pid) + r"(?![\w-])", text))
    total = sum(e["body"].count("{{marker}}") for e in edits)
    if n >= total:
        return text
    if n:
        raise PatchError("部分適用（マーカー {0}/{1}）".format(n, total))
    for e in edits:
        try:
            text = OPS[e["op"]](text, e, pid)
        except PatchError as err:
            raise PatchError("{0}: {1}".format(e.get("card") or e["file"], err))
    return text


def apply_patch(root, files, pid, patch):
    """1パッチ（全ファイル成功時だけ files に反映）。変更があれば True。失敗は例外。"""
    by_file = {}
    for x in patch["cards"]:
        e = card(x) if isinstance(x, str) else x
        by_file.setdefault(e["file"], []).append(e)
    work = {}
    for rel, es in by_file.items():
        if rel not in files:
            files[rel] = load(root, rel)
        work[rel] = apply_file(files[rel]["text"], es, pid)
    changed = any(work[rel] != files[rel]["text"] for rel in work)
    for rel in work:
        files[rel]["text"] = work[rel]
    return changed


def load(root, rel):
    path = os.path.join(root, *rel.split("/"))
    if not os.path.isfile(path):
        raise PatchError("ファイルが無い: " + rel)
    with open(path, "rb") as f:
        raw = f.read()
    bom = raw.startswith(BOM)
    raw = raw[len(BOM):] if bom else raw
    text = raw.decode("utf-8").replace("\r\n", "\n")
    return {"text": text, "orig": text, "bom": bom, "crlf": b"\r\n" in raw}


def save(root, rel, st):
    text = st["text"].replace("\n", "\r\n") if st["crlf"] else st["text"]
    with open(os.path.join(root, *rel.split("/")), "wb") as f:
        f.write((BOM if st["bom"] else b"") + text.encode("utf-8"))


HELP_EPILOG = """\
結果の見方:
  APPLIED  今回適用した
  ALREADY  適用済み（マーカーあり）
  FAILED   失敗（理由を表示）

終了コード:
  0  成功
  1  ERROR のパッチが失敗（何も書き込まない）
  2  --target・patches.json・--include の指定が不正

例:
  python3 apply_patches.py --target /path/to/com.unity.addressables
  python3 apply_patches.py --target /path/to/com.unity.addressables --dry-run
  python3 apply_patches.py --target /path/to/com.unity.addressables --include partial-addressables"""


def main(argv=None):
    ap = argparse.ArgumentParser(
        usage="apply_patches.py --target <パッケージのルート> [--include ID[,ID...]] [--dry-run]",
        description="F4 の独自修正を、上流の com.unity.addressables に当てる。\n"
        "パッチの一覧は patches.json、挿入するコードは snippets/ のカードに書く。",
        epilog=HELP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
    )
    ap.add_argument("-h", "--help", action="help", help="このヘルプを表示して終了する")
    ap.add_argument("--target", required=True, metavar="PATH",
                    help="適用先の com.unity.addressables のフォルダ（package.json がある場所）。必須")
    ap.add_argument("--include", default="", metavar="IDS",
                    help="指定したパッチだけ適用する。patches.json の patchId をカンマ区切りで指定。省略すると全パッチ")
    ap.add_argument("--dry-run", action="store_true",
                    help="ファイルを書き込まず、各パッチの結果（APPLIED / ALREADY / FAILED）だけ表示する")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.target)

    try:
        with open(os.path.join(root, "package.json"), "rb") as f:
            name = json.loads(f.read().decode("utf-8-sig")).get("name")
    except (OSError, ValueError):
        name = None

    if name != PACKAGE:
        print("ERROR: {0} ではない: {1}".format(PACKAGE, root), file=sys.stderr)
        return 2

    try:
        patches = load_patches()
    except PatchError as err:
        print("ERROR: " + str(err), file=sys.stderr)
        return 2
    seen = {p["patchId"] for p in patches}
    ids = [s.strip() for s in args.include.split(",") if s.strip()]
    if set(ids) - seen:
        print("ERROR: 不明なパッチID: " + args.include, file=sys.stderr)
        return 2
    files, failed_error = {}, False
    for p in [p for p in patches if not ids or p["patchId"] in ids]:
        pid = p["patchId"]
        try:
            status, reason = ("APPLIED" if apply_patch(root, files, pid, p) else "ALREADY"), ""
        except Exception as err:  # 想定外の例外も FAILED にして他のパッチは続ける
            status, reason = "FAILED", str(err) or repr(err)
            failed_error |= p["severity"] == ERROR
            reason += "" if p["severity"] == ERROR else "（WARN: skip）"
        print("{0:<28} {1:<8} {2}".format(pid, status, reason).rstrip())
    if failed_error:
        print("ERROR パッチが失敗したため何も書き込まない", file=sys.stderr)
        return 1
    if not args.dry_run:
        for rel, st in sorted(files.items()):
            if st["text"] != st["orig"]:
                save(root, rel, st)
    return 0


if __name__ == "__main__":
    sys.exit(main())
