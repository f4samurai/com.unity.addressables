@echo off
chcp 65001 >nul
rem F4 パッチを適用する（Windows）。ツールのフォルダを PYTHONPATH に加えてから Python を起動する（このプロセス内だけ）。
rem 使い方: apply_patches.bat --target <パッケージのルート> [--include ID[,ID...]] [--dry-run]
rem         引数なしのダブルクリック起動では、対象パッケージのパスを入力して実行する。
setlocal
set "PYTHONPATH=%~dp0;%PYTHONPATH%"
set "PYTHONDONTWRITEBYTECODE=1"

set "PY=python"
python --version >nul 2>&1
if errorlevel 1 (
    set "PY=py -3"
    py -3 --version >nul 2>&1
    if errorlevel 1 (
        echo Python が見つかりません。Python 3 をインストールしてください。
        if "%~1"=="" pause
        exit /b 127
    )
)

if not "%~1"=="" (
    %PY% "%~dp0apply_patches.py" %*
    exit /b %errorlevel%
)

echo 対象パッケージ（com.unity.addressables のフォルダ）のパスを入力してください。
echo フォルダをこのウィンドウにドラッグ^&ドロップしても貼れます。
set "TARGET="
set /p "TARGET=> "
if not defined TARGET (
    echo 入力が空のため何もしません。
    pause
    exit /b 0
)
set "TARGET=%TARGET:"=%"
%PY% "%~dp0apply_patches.py" --target "%TARGET%"
set "RC=%errorlevel%"
echo Enterキーで閉じます
pause >nul
exit /b %RC%
