// op: replace
// within: (?<![\w.])class\s+Serializer\b\s*:\s*BinaryStorageBuffer\s*\.\s*ISerializationAdapter\s*<\s*ContentCatalogData\s*>
// extend: expr
//
// ▼ anchor（上流のこのプロパティを探す。`=>` から `;` までの式が {{expr}} に入る）
// 上流: public IEnumerable<BinaryStorageBuffer.ISerializationAdapter> Dependencies =>
public\s+IEnumerable\s*<\s*BinaryStorageBuffer\s*\.\s*ISerializationAdapter\s*>\s+Dependencies\s*=>
//
// ▼ body（アンカーの先頭から式の `;` までをこれに置き換える）
public IEnumerable<BinaryStorageBuffer.ISerializationAdapter> Dependencies
{
    get
    {
        var adapters = new List<BinaryStorageBuffer.ISerializationAdapter>({{expr}});
        {{marker}}
        AddAdditionalAdapters(adapters);
        return adapters;
    }
}

// 実装が存在しない場合は呼び出しごと取り除かれる
static partial void AddAdditionalAdapters(List<BinaryStorageBuffer.ISerializationAdapter> adapters);
