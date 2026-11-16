// op: insert-after
// extend: block
//
// ▼ anchor（上流のこの宣言を探す。上流側は変更しない）
// 上流: [修飾子] void AutoReleaseHandleOnCompletion<TObject>(AsyncOperationHandle<TObject> handle) { ... }
(?:(?:public|internal|private|protected|static|override|virtual)\s+)*void\s+AutoReleaseHandleOnCompletion\s*<\s*TObject\s*>\s*\(\s*AsyncOperationHandle\s*<\s*TObject\s*>\s+\w+\s*\)
//
// ▼ body（アンカーの直後に空行を挟んで入る）
{{marker}}
internal void AutoReleaseHandleOnCompletion(AsyncOperationHandle<SceneInstance> handle, UnloadSceneOptions unloadSceneOptions)
{
    handle.Completed += op => Release(op, unloadSceneOptions);
}
