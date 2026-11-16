// op: replace
//
// ▼ anchor（上流のこの if 文と、波括弧なしの本体の代入文を探す。上流側は変更しない）
// 上流: if (!UnityWebRequestUtilities.RequestHasErrors(webReq, out UnityWebRequestResult uwrResult))
// 上流:     textResult = webReq.downloadHandler.text;
(?P<head>if\s*\(\s*!\s*UnityWebRequestUtilities\s*\.\s*RequestHasErrors\s*\(\s*webReq\s*,\s*out\s+(?:UnityWebRequestResult|var)\s+uwrResult\s*\)\s*\))\s*(?P<stmt>textResult\s*=\s*webReq\s*\.\s*downloadHandler\s*\.\s*text\s*;)
//
// ▼ body（if 本体を波括弧で囲み、代入文 {{stmt}} の直後に呼び出しを足す）
{{head}}
{
    {{stmt}}
    {{marker}}
    m_PI.ResourceManager.OnWebRequestComplete?.Invoke(webReq);
}
