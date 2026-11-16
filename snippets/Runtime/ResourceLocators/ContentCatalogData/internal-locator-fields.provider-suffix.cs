// op: replace
// within: (?<![\w.])class\s+ResourceLocator\b
//
// ▼ anchor（ResourceLocator 直下のフィールド宣言を探す。private や修飾子なしでもよい）
// 上流: private string providerSuffix;
^(?P<ind>[ \t]*)(?:private\s+)?(?P<mods>(?:(?:readonly|static|volatile)\s+)*)(?P<decl>string\s+providerSuffix\b)(?=\s*[;=])
// Before: private string providerSuffix;
// After:  internal string providerSuffix;
//
// ▼ body（internal にする。修飾子 readonly 等は残す）
{{ind}}internal {{mods}}{{decl}}
