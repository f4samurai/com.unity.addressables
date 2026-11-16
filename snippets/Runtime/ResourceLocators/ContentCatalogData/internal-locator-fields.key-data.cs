// op: replace
// within: (?<![\w.])class\s+ResourceLocator\b
//
// ▼ anchor（ResourceLocator 直下のフィールド宣言を探す。private や修飾子なしでもよい）
// 上流: private Dictionary<object, uint> keyData;
^(?P<ind>[ \t]*)(?:private\s+)?(?P<mods>(?:(?:readonly|static|volatile)\s+)*)(?P<decl>Dictionary\s*<\s*object\s*,\s*uint\s*>\s+keyData\b)(?=\s*[;=])
// Before: private Dictionary<object, uint> keyData;
// After:  // f4-patch:<id>
//         internal Dictionary<object, uint> keyData;
//
// ▼ body（internal にする。修飾子 readonly 等は残す。マーカーはこの1枚だけ）
{{ind}}{{marker}}
internal {{mods}}{{decl}}
