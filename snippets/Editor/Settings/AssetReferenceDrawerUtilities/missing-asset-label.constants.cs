// op: insert-after
// blank: no
//
// ▼ anchor（上流のこの定数宣言を探す。上流側は変更しない）
// 上流: [修飾子] const string noAssetTypeStringformat = ...;
^[ \t]*(?:\w+[ \t]+)*const\s+string\s+noAssetTypeStringformat\s*=[^;]*;
//
// ▼ body（アンカーにマッチした行の直後に、空行なしで入る）
{{marker}}
internal const string missingAssetString = "Missing";
internal const string missingAssetTypeStringformat = "Missing ({0})";
