// op: replace
//
// ▼ anchor（上流の class 宣言を探す。既に partial でも同じ結果になる）
// 上流: public class ResourceManager
(?<![\w.])(?P<mods>(?:(?:public|internal|private|protected|static|sealed|abstract|unsafe|new)\s+)*)(?:partial\s+)?(?P<decl>class\s+ResourceManager\b)
// Before: public class ResourceManager
// After:  // f4-patch:<id>
//         public partial class ResourceManager
//
// ▼ body（宣言の直前にマーカー行を足して partial 化する）
{{marker}}
{{mods}}partial {{decl}}
