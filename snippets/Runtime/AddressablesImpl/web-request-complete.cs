// op: insert-after
// extend: block
//
// ▼ anchor（上流のこの宣言を探す。上流側は変更しない）
// 上流: public Action<UnityWebRequest> WebRequestOverride { ... }
public\s+Action\s*<\s*UnityWebRequest\s*>\s+WebRequestOverride\b
//
// ▼ body（アンカーの直後に空行を挟んで入る）
{{marker}}
public Action<UnityWebRequest> OnWebRequestComplete
{
    get { return ResourceManager.OnWebRequestComplete; }
    set { ResourceManager.OnWebRequestComplete = value; }
}
