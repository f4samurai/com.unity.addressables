// op: replace
// within: (?<![\w.])class\s+ContentCatalogData\b
//
// ▼ anchor（上流の class 宣言を探す。既に partial でも同じ結果になる）
// 上流: class Serializer : BinaryStorageBuffer.ISerializationAdapter<ContentCatalogData>
(?<![\w.])(?P<mods>(?:(?:public|internal|private|protected|static|sealed|abstract|unsafe|new)\s+)*)(?:partial\s+)?(?P<decl>class\s+Serializer\b\s*:\s*BinaryStorageBuffer\s*\.\s*ISerializationAdapter\s*<\s*ContentCatalogData\s*>)
// Before: class Serializer : BinaryStorageBuffer.ISerializationAdapter<ContentCatalogData>
// After:  // f4-patch:<id>
//         partial class Serializer : BinaryStorageBuffer.ISerializationAdapter<ContentCatalogData>
//
// ▼ body（宣言の直前にマーカー行を足して partial 化する）
{{marker}}
{{mods}}partial {{decl}}
