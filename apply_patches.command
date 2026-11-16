#!/bin/bash
# F4 パッチを適用する（Mac）。ツールのフォルダを PYTHONPATH に加えてから Python を起動する。
# 使い方: ./apply_patches.command --target <パッケージのルート> [--include ID[,ID...]] [--dry-run]
#         引数なしのダブルクリック起動では、対象パッケージのパスを入力して実行する。
DIR="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="$DIR${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONDONTWRITEBYTECODE=1

if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 が見つかりません。python3 をインストールしてください。"
    [ $# -eq 0 ] && read -r -p "Enterキーで閉じます" _
    exit 127
fi

if [ $# -gt 0 ]; then
    python3 "$DIR/apply_patches.py" "$@"
    exit $?
fi

echo "対象パッケージ（com.unity.addressables のフォルダ）のパスを入力してください。"
echo "フォルダをこのウィンドウにドラッグ&ドロップしても貼れます。"
read -r -p "> " TARGET
# ドラッグ&ドロップで付くことがある前後の空白・引用符・バックスラッシュを取り除く
TARGET="$(printf '%s' "$TARGET" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e "s/^'\(.*\)'\$/\1/" -e 's/\\\(.\)/\1/g')"
if [ -z "$TARGET" ]; then
    echo "入力が空のため何もしません。"
    read -r -p "Enterキーで閉じます" _
    exit 0
fi
python3 "$DIR/apply_patches.py" --target "$TARGET"
RC=$?
read -r -p "Enterキーで閉じます" _
exit $RC
