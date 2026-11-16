// op: insert-after
// extend: block
// requires: UnloadSceneAsync, m_SceneInstances, SceneOperationCount, UnloadSceneOpExcludeReleaseCallback, AutoReleaseHandleOnCompletion
//
// ▼ anchor（上流のこの宣言を探す。上流側は変更しない）
// 上流: [修飾子] void Release<TObject>(AsyncOperationHandle<TObject> handle) { ... }
(?:(?:public|internal|private|protected|static|override|virtual)\s+)*void\s+Release\s*<\s*TObject\s*>\s*\(\s*AsyncOperationHandle\s*<\s*TObject\s*>\s+\w+\s*\)
//
// ▼ body（アンカーの直後に空行を挟んで入る）
{{marker}}
public void Release(AsyncOperationHandle<SceneInstance> handle, UnloadSceneOptions unloadSceneOptions)
{
    SceneInstance sceneInstance = (SceneInstance)Convert.ChangeType(handle.Result, typeof(SceneInstance));
    if (sceneInstance.Scene.isLoaded && handle.ReferenceCount == 1)
    {
        if (SceneOperationCount == 1 && m_SceneInstances.First().Equals(handle))
            m_SceneInstances.Clear();
        UnloadSceneAsync(handle, unloadSceneOptions, true);
    }
    else if (!sceneInstance.Scene.isLoaded && handle.ReferenceCount == 2 && !handle.UnloadSceneOpExcludeReleaseCallback)
    {
        AutoReleaseHandleOnCompletion(handle, unloadSceneOptions);
    }

    m_ResourceManager.Release(handle);
}
