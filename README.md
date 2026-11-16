# F4 パッチツール

## ① これは何か

上流の `com.unity.addressables`（C#）に、F4 独自の修正を「アンカー検索＋置換」で当てるツールです。
Python 3 標準ライブラリのみ・1ファイル（`apply_patches.py`）で動き、パッチはすべて「カード」（`snippets/` の C# 片）に書き、
パッチ一覧は `patches.json`（キー4つのオブジェクトの配列）だけです。何度実行しても結果は同じ（冪等）で、上流が変わって
アンカーが合わなくなったときは書き込まずに失敗を知らせます。上流ファイルの BOM と改行コード（LF/CRLF）は保ったまま書き換えます。

## ② 使い方

実行ファイル経由（Mac は `./apply_patches.command`、Windows は `apply_patches.bat`）か、直接 `python3 apply_patches.py` で実行します。
引数なしでダブルクリックすると、対象パッケージのパスを聞かれます（フォルダのドラッグ&ドロップで貼れます）。

```
./apply_patches.command --target <パス> [--include ID[,ID...]] [--dry-run]    # Mac
apply_patches.bat --target <パス> [--include ID[,ID...]] [--dry-run]         :: Windows
python3 apply_patches.py --target <パス> [--include ID[,ID...]] [--dry-run]
```

- `--target PATH`: 適用先の com.unity.addressables のフォルダ（package.json がある場所）。必須
- `--include IDS`: 指定したパッチだけ適用する。patches.json の patchId をカンマ区切りで。省略すると全パッチ
- `--dry-run`: ファイルを書き込まず、各パッチの結果（APPLIED / ALREADY / FAILED）だけ表示する
- 詳しくは `python3 apply_patches.py --help`（結果の見方・終了コード・例）

| 終了コード | 意味 |
|---|---|
| 0 | 成功（ERROR パッチの失敗なし。WARN の失敗は skip して続行） |
| 1 | ERROR パッチが失敗（何も書き込まない） |
| 2 | `--target` が com.unity.addressables ではない / `--include` に不明なパッチID / patches.json の不備（読めない・ID重複・キー欠落など） |

## ③ 1回の実行の流れ

1. `target/package.json` の name を確認し、`patches.json`（`--include` で絞り込み）を順に処理する
2. パッチ内の編集（カード）を対象ファイルごとにまとめる
3. `// f4-patch:<id>` のマーカーが必要数あれば何もしない（ALREADY）。一部だけなら失敗
4. 無ければ編集を順に適用する。テキストからアンカーをちょうど1件探して書き換える
5. 1パッチ内で失敗したら、そのパッチは何も変えない（WARN は skip して続行）
6. ERROR が1つでもあれば全体で何も書かない。無ければ変更のあったファイルだけ書く（`--dry-run` なら書かない）

**制約**: アンカーの検索自体はコメントや文字列の中身もそのまま対象にする。コメント内に同じアンカーがあれば2件になって失敗する（黙って誤適用はしない）。
括弧（`{ }` `( )` `[ ]` `;`）の対応はコメント（`//` `/* */`）と文字列（通常・`@"…"`・raw `"""…"""`）・文字リテラルを飛ばして数えるので、その中の括弧は無視される。

## ④ スニペットの置き方

`snippets/<上流のファイルパス(.cs を除く)>/<パッチID>[.説明].cs`

- カードの対象ファイルは置き場所で決まる（`snippets/` からの相対パスの末尾＝カード名を除き、`.cs` を付けたもの）
- 例: 対象が `Runtime/Addressables.cs` なら `snippets/Runtime/Addressables/<パッチID>.cs`
- 同じファイルに同じパッチのカードが複数あるときだけ `.説明` を付ける
- ネームスペースやクラス名は使わない（AssemblyInfo.cs や 1ファイル内の複数クラスも同じ規則）

```
snippets/Runtime/Addressables/web-request-complete.cs                       → Runtime/Addressables.cs
snippets/Editor/Settings/AssetReferenceDrawerUtilities/missing-asset-label.constants.cs → Editor/Settings/AssetReferenceDrawerUtilities.cs
snippets/Runtime/ResourceLocators/ContentCatalogData/internal-locator-fields.key-data.cs → Runtime/ResourceLocators/ContentCatalogData.cs
snippets/Runtime/AssemblyInfo/internals-visible-to.cs                       → Runtime/AssemblyInfo.cs
```

カードの先頭は `// op: ...` のヘッダ（`op` / `anchor` / `within` /
`requires` / `extend` / `blank` / `trailing-newline: yes`＝本文末尾の改行を残す）、続いて `// ▼ anchor（説明）` / `// ▼ body（説明）` の節にコードを書く
（見出しの先頭は `anchor` / `body` / `before` / `after` のいずれか。`before` + `after` だけのカードは 本文 = 前 + 元の範囲 + 後ろ。括弧内の日本語は自由）。
対象ファイルのヘッダ（`// file:`）は無い。置き場所だけが対象を決める。
各カードに `// 上流: <アンカーが合う典型的な1行>` と Before→After を書く。実例は既存のカードを参照。

## ⑤ パッチを足す手順

1. 対象の上流コードを見て、op（下記3種類）と一意に見つかるアンカー（正規表現）を決める
2. カードを `snippets/<上流のファイルパス(.cs除く)>/<パッチID>.cs` に書く（置き場所が対象ファイルを決める。`// file:` は書かない）
3. `patches.json` の配列の末尾に `{"patchId": "ID", "severity": "ERROR" か "WARN", "description": "説明", "cards": ["カードのパス", ...]}` を追加し（ID の重複・キー欠落・JSON の文法エラーは読み込み時にエラー、終了コード 2。最後の要素の後ろにカンマを付けない）、⑥で検証する

本文には `{{marker}}`（`// f4-patch:<id>` に置換）を必ず入れる。冪等判定に使う。

**replace**: アンカーの範囲を本文で置き換える（`{{グループ名}}` で一致部分を再利用）

```csharp
// Before
public class Foo
// After
// f4-patch:my-patch
public partial class Foo
```

**insert-after**: アンカーの行の次に、空行を挟んで本文を足す

```csharp
// Before
public int X { get; }
// After
public int X { get; }

// f4-patch:my-patch
public int Y { get; }
```

**insert-in-block**: アンカーのメソッド本体の末尾（閉じ括弧の直前）に足す

```csharp
// Before
void Init()
{
    Setup();
}
// After
void Init()
{
    Setup();
    // f4-patch:my-patch
    F4.Hook();
}
```

## ⑥ 検証のしかた

```
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -t .
python3 apply_patches.py --target <素の上流のパス> --dry-run
```

- `-t .` が必要（無いと tests/ が基準になり import が通らない）
- テスト: 3つの op・冪等・アンカー数・コメント内の重複アンカーで失敗・カード見出しの不正・ERROR 時に書かないこと
- 素の上流（未適用）に `--dry-run` で試し、全パッチが APPLIED になることを確かめる
- 複数の ref での適用可否の確認は、各 ref を git archive で展開して --dry-run を手で実行する

## ⑦ patches.json

```json
[
    {
        "patchId": "partial-addressables",
        "severity": "ERROR",
        "description": "Addressables を partial 化",
        "cards": ["Runtime/Addressables/partial-addressables.cs"]
    }
]
```

- キーは4つ: `patchId`（パッチID。`// f4-patch:<ID>` のマーカーにもなる）/ `severity`（`"ERROR"`=失敗で全体中止、`"WARN"`=失敗は skip）/ `description`（表示用の説明）/ `cards`（カードのパスのリスト）
- 適用順は配列の並び順、cards 内もリストの順
- JSON にコメントは書けない。パッチの説明・意図は README か各カード（`// 上流:` と Before→After）に書く
- UTF-8（BOM なし）・LF・インデント4スペース。日本語はそのまま書く

## ⑧ 実行ファイル

| 実行ファイル | 役割 |
|---|---|
| `apply_patches.command` / `.bat` | パッチ適用。引数はそのまま渡す。引数なしなら対象パスを入力（ダブルクリック用） |

- Mac: `./apply_patches.command --target <パス>`（初回は `chmod +x *.command` が要ることがある） / Windows: `apply_patches.bat --target <パス>`
- 実行ファイルは、自分のフォルダを PYTHONPATH の先頭に加えてから Python を起動する（そのプロセス内だけ。永続的な環境変数は変えない）。終了コードは Python のものをそのまま返す
- ダブルクリック起動（引数なし）のときだけ「Enterキーで閉じます」で待つ。引数付きでは待たない
- **実行ファイルを今後作るときは、必ずツールのフォルダを PYTHONPATH に加えること**（Python 側では `sys.path` を触らない）

## ⑨ フォルダ構成

```
apply_patches.py        パッチ適用の本体（load_patches() で patches.json を読む）
patches.json            パッチ一覧（キー4つのオブジェクトの配列）
apply_patches.command / .bat   実行ファイル（Mac / Windows）
snippets/               カード（上流のファイルパス(.cs除く)/<パッチID>.cs）
tests/                  unittest（__init__.py あり）
```
