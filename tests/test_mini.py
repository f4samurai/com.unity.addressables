# -*- coding: utf-8 -*-
"""apply_patches.py の小さな固定フィクスチャによるテスト（op・冪等・アンカー数・カード見出し・ERROR 時は書かない）。"""
import contextlib
import io
import json
import os
import tempfile
import unittest
from unittest import mock

import apply_patches as ap

SRC = "class Foo\n{\n    int X;\n    void Init()\n    {\n        Setup();\n    }\n}\n"
PARTIAL = dict(file="A.cs", op="replace", anchor=r"(?P<d>class\s+Foo\b)", body="{{marker}}\npartial {{d}}")


def P(patchId, cards):
    return {"patchId": patchId, "severity": "ERROR", "description": "d", "cards": cards}


def edit(op, anchor, body, **kw):
    return dict(file="A.cs", op=op, anchor=anchor, body=body, **kw)


class OpsTest(unittest.TestCase):
    def test_replace(self):
        self.assertEqual(ap.apply_file(SRC, [PARTIAL], "p").split("\n")[:2], ["// f4-patch:p", "partial class Foo"])

    def test_insert_after(self):
        e = edit("insert-after", r"int X;", "{{marker}}\nint Y;")
        self.assertIn("    int X;\n\n    // f4-patch:p\n    int Y;\n", ap.apply_file(SRC, [e], "p"))

    def test_insert_in_block(self):
        e = edit("insert-in-block", r"void Init\(\)", "{{marker}}\nHook();", requires="Setup")
        self.assertIn("        Setup();\n        // f4-patch:p\n        Hook();\n    }\n", ap.apply_file(SRC, [e], "p"))

    def test_idempotent_by_marker(self):
        once = ap.apply_file(SRC, [PARTIAL], "p")
        self.assertEqual(ap.apply_file(once, [PARTIAL], "p"), once)

    def test_anchor_count_must_be_one(self):
        with self.assertRaises(ap.PatchError):
            ap.apply_file(SRC, [edit("replace", r"class\s+Nope", "{{marker}}")], "p")
        with self.assertRaises(ap.PatchError):
            ap.apply_file(SRC + SRC, [edit("replace", r"class\s+Foo", "{{marker}}")], "p")

    def test_anchor_in_comment_counts_and_fails(self):
        text = "// class Foo\nclass Foo\n{\n}\n"
        with self.assertRaises(ap.PatchError) as cm:
            ap.apply_file(text, [PARTIAL], "p")
        self.assertIn("2件", str(cm.exception))


class BracketTest(unittest.TestCase):
    def block(self, inner):
        text = "class Foo\n{\n    void Init()\n    {\n" + inner + "    }\n    void Next()\n    {\n    }\n}\n"
        e = edit("insert-in-block", r"void Init\(\)", "{{marker}}\nHook();")
        out = ap.apply_file(text, [e], "p")
        self.assertIn(inner + "        // f4-patch:p\n        Hook();\n    }\n    void Next()", out)

    def test_string_and_comment_braces_ignored(self):
        self.block('        var s = "}";\n        // {\n        /* } */ var c = \'}\';\n')

    def test_verbatim_and_raw_strings(self):
        self.block('        var a = @"{ "" }";\n        var b = """{ }""";\n')

    def test_expr_end_ignores_semicolon_in_string(self):
        e = edit("replace", r"int X =>", "{{marker}}\nint X => {{expr}} + 1;", extend="expr")
        out = ap.apply_file("class Foo\n{\n    int X => F(\";\") ?? '}';\n}\n", [e], "p")
        self.assertIn("// f4-patch:p\n    int X => F(\";\") ?? '}' + 1;\n}", out)


class MainTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name
        with open(os.path.join(self.root, "package.json"), "w") as f:
            json.dump({"name": ap.PACKAGE}, f)
        with open(os.path.join(self.root, "A.cs"), "w", newline="\n") as f:
            f.write(SRC)

    def run_main(self, patches):
        path = os.path.join(self.root, "patches.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write(patches if isinstance(patches, str) else json.dumps(patches))
        with mock.patch.object(ap, "PATCHES_JSON", path), contextlib.redirect_stdout(io.StringIO()) as out, \
                contextlib.redirect_stderr(io.StringIO()):
            rc = ap.main(["--target", self.root])
        return rc, out.getvalue()

    def read(self):
        with open(os.path.join(self.root, "A.cs"), newline="") as f:
            return f.read()

    def test_second_run_is_already(self):
        patches = [P("p", [PARTIAL])]
        self.assertEqual(self.run_main(patches)[0], 0)
        first = self.read()
        self.assertNotEqual(first, SRC)
        rc, out = self.run_main(patches)
        self.assertEqual(rc, 0)
        self.assertIn("ALREADY", out)
        self.assertEqual(self.read(), first)

    def test_error_failure_writes_nothing(self):
        bad = edit("replace", r"class\s+Nope", "{{marker}}")
        rc, out = self.run_main([P("ok", [PARTIAL]), P("bad", [bad])])
        self.assertEqual(rc, 1)
        self.assertIn("FAILED", out)
        self.assertEqual(self.read(), SRC)

    def test_card_location_decides_target_file(self):
        # カードの置き場所が対象ファイルを決める。上流に無ければ「ファイルが無い」で FAILED
        self.assertEqual(ap.card("Runtime/Addressables/web-request-complete.cs")["file"], "Runtime/Addressables.cs")
        patches = [P("web-request-complete", ["Runtime/Addressables/web-request-complete.cs"])]
        rc, out = self.run_main(patches)
        self.assertEqual(rc, 1)
        self.assertIn("ファイルが無い: Runtime/Addressables.cs", out)

    def test_card_bad_heading_is_failed(self):
        os.makedirs(os.path.join(self.root, "snippets", "A"))
        with open(os.path.join(self.root, "snippets", "A", "x.cs"), "w", encoding="utf-8") as f:
            f.write("// op: replace\n// ▼ アンカー（旧見出し）\nclass Foo\n")
        with mock.patch.object(ap, "HERE", self.root):
            with self.assertRaises(ap.PatchError) as cm:
                ap.card("A/x.cs")
            self.assertIn("A/x.cs", str(cm.exception))
            self.assertIn("// ▼ アンカー（旧見出し）", str(cm.exception))
            rc, out = self.run_main([P("x", ["A/x.cs"])])
        self.assertEqual(rc, 1)
        self.assertIn("FAILED", out)
        self.assertEqual(self.read(), SRC)

    def test_duplicate_patch_id_is_rejected(self):
        rc, out = self.run_main([P("x", [PARTIAL]), P("x", [PARTIAL])])
        self.assertEqual(rc, 2)
        self.assertEqual(self.read(), SRC)

    def test_broken_json_is_rejected(self):
        for text in ("[{", '{"patchId": "x"}'):
            with self.subTest(text=text):
                rc, out = self.run_main(text)
                self.assertEqual(rc, 2)
                self.assertEqual(self.read(), SRC)

    def test_bad_severity_is_rejected(self):
        bad = P("x", [PARTIAL])
        bad["severity"] = "INFO"
        self.assertEqual(self.run_main([bad])[0], 2)

    def test_missing_key_is_rejected(self):
        bad = P("x", [PARTIAL])
        del bad["description"]
        rc, out = self.run_main([bad])
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
