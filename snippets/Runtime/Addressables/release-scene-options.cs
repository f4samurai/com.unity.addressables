// op: insert-after
// extend: block
//
// ▼ anchor（上流のこの宣言を探す。上流側は変更しない）
// 上流: public static void Release<TObject>(AsyncOperationHandle<TObject> handle) { ... }
public\s+static\s+void\s+Release\s*<\s*TObject\s*>\s*\(\s*AsyncOperationHandle\s*<\s*TObject\s*>\s+\w+\s*\)
//
// ▼ body（アンカーの直後に空行を挟んで入る）
{{marker}}
public static void Release(AsyncOperationHandle<SceneInstance> handle, UnloadSceneOptions options)
{
    m_Addressables.Release(handle, options);
}
