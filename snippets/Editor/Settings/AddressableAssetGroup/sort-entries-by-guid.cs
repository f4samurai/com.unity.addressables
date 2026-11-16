// op: insert-in-block
// requires: m_SerializeEntries
//
// ▼ anchor（上流のこのメソッドを探す。上流側は変更しない）
// 上流: void [ISerializationCallbackReceiver.]OnBeforeSerialize() { ... }
void\s+(?:ISerializationCallbackReceiver\s*\.\s*)?OnBeforeSerialize\s*\(\s*\)
//
// ▼ body（メソッド本体の末尾、閉じ括弧の直前に入る）
{{marker}}
m_SerializeEntries.Sort((e1, e2) => e1.guid.CompareTo(e2.guid));
