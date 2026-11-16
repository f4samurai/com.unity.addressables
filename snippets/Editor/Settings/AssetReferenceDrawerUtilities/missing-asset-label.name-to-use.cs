// op: replace
//
// ▼ anchor（このコードを下の C# に置き換える）
// 上流: string nameToUse = currentRef.editorAsset != null ? currentRef.editorAsset.name : ConstructNoAssetLabel(propertyField.FieldType);
string\s+nameToUse\s*=\s*currentRef\s*\.\s*editorAsset\s*!=\s*null\s*\?\s*currentRef\s*\.\s*editorAsset\s*\.\s*name\s*:\s*ConstructNoAssetLabel\s*\(\s*propertyField\s*\.\s*FieldType\s*\)\s*;
//
// ▼ body（置き換え後の C#）
{{marker}}
var editorAsset = currentRef.editorAsset;
string nameToUse = editorAsset != null ? currentRef.editorAsset.name : ConstructNoAssetLabel(propertyField.FieldType);
if (editorAsset == null && !string.IsNullOrEmpty(currentRef.AssetGUID))
{
    nameToUse = ConstructMissingAssetLabel(propertyField.FieldType);
}
