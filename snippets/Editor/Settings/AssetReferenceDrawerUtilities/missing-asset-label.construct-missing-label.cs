// op: insert-after
// extend: expr
//
// ▼ anchor（上流のこの宣言を探す。上流側は変更しない）
// 上流: [修飾子] string FormatNoAssetString(string n) => ...;
(?:(?:internal|private|public|static)\s+)*string\s+FormatNoAssetString\s*\(\s*string\s+\w+\s*\)\s*=>
//
// ▼ body（アンカーの直後に空行を挟んで入る）
{{marker}}
internal static string ConstructMissingAssetLabel(Type t)
{
    if (t == null || t == typeof(AssetReference))
        return FormatMissingAssetString(string.Empty);
    t = GetGenericType(t);
    if (t == null || t == typeof(AssetReference))
        return FormatMissingAssetString(string.Empty);
    return FormatMissingAssetString(t.Name);
}

static string FormatMissingAssetString(string n) => string.IsNullOrEmpty(n) ? missingAssetString : string.Format(missingAssetTypeStringformat, n);
