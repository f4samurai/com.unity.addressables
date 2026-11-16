// op: replace
// extend: stmt
//
// ▼ anchor（上流のこの if 文の冒頭を探す。この if 文全体の前後に C# を足す。上流側は変更しない）
// 上流: if (EditorGUI.DropdownButton(assetDropDownRect, new GUIContent(nameToUse), ...))  文 or { ... }
// 条件の閉じ括弧までをアンカーにし、extend: stmt で直後の文（{ ... } または 1 文）までを範囲にする
if\s*\(\s*EditorGUI\s*\.\s*DropdownButton\s*\(\s*assetDropDownRect\s*,\s*new\s+GUIContent\s*\(\s*nameToUse\s*\)\s*,[^{;]*?\)(?=\s*[{\w])
//
// ▼ before（if 文の直前に入る）
{{marker}}
Color originalBackgroundColor = Color.clear;
bool isMissing = nameToUse.Contains("Missing");
if (isMissing)
{
    originalBackgroundColor = UnityEngine.GUI.backgroundColor;
    UnityEngine.GUI.backgroundColor = Color.red;
}

// ▼ after（if 文の直後に入る）
if (isMissing)
{
    UnityEngine.GUI.backgroundColor = originalBackgroundColor;
}
