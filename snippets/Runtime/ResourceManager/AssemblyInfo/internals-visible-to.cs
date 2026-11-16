// op: replace
// trailing-newline: yes
//
// ▼ anchor（ファイル末尾＝最終改行の直後）
// 上流: （ファイルの最後の行の後ろ）
(?<=\n)\Z
// Before: （末尾）
// After:  // f4-patch:<id>
//         [assembly: InternalsVisibleTo("F4samurai.Addressables")]
//
// ▼ body（末尾に追記する）
{{marker}}
[assembly: InternalsVisibleTo("F4samurai.Addressables")]
