// op: insert-after
// extend: block
//
// ▼ anchor（上流のこの宣言を探す。上流側は変更しない）
// 上流: public static Action<UnityWebRequest> WebRequestOverride { ... }
public\s+static\s+Action\s*<\s*UnityWebRequest\s*>\s+WebRequestOverride\b
//
// ▼ body（アンカーの直後に空行を挟んで入る）
{{marker}}
public static Action<UnityWebRequest> OnWebRequestComplete
{
    get { return m_Addressables.OnWebRequestComplete; }
    set { m_Addressables.OnWebRequestComplete = value; }
}
