// op: replace
// within: (?<![\w.])class\s+ResourceLocator\b
//
// ▼ anchor（ResourceLocator 直下のフィールド宣言を探す。private や修飾子なしでもよい）
// 上流: private BinaryStorageBuffer.Reader reader;
^(?P<ind>[ \t]*)(?:private\s+)?(?P<mods>(?:(?:readonly|static|volatile)\s+)*)(?P<decl>BinaryStorageBuffer\s*\.\s*Reader\s+reader\b)(?=\s*[;=])
// Before: private BinaryStorageBuffer.Reader reader;
// After:  internal BinaryStorageBuffer.Reader reader;
//
// ▼ body（internal にする。修飾子 readonly 等は残す）
{{ind}}internal {{mods}}{{decl}}
