@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ============================================
echo   Discord Debug 模式啟動器
echo ============================================
echo.

REM 檢查 Discord 是否已在執行
tasklist /FI "IMAGENAME eq Discord.exe" 2>nul | findstr /i "Discord.exe" >nul
if %ERRORLEVEL% EQU 0 (
    echo [錯誤] Discord 已在執行中，請先關閉 Discord 後再執行此腳本。
    echo.
    echo 請在系統匣中右鍵點擊 Discord 圖示，選擇「Quit Discord」完全關閉後再試。
    echo.
    pause
    exit /b 1
)

REM 設定 Discord 路徑
set "DISCORD_UPDATE=%LOCALAPPDATA%\Discord\Update.exe"

REM 檢查 Discord 是否已安裝
if not exist "%DISCORD_UPDATE%" (
    echo [錯誤] 找不到 Discord 安裝路徑：%DISCORD_UPDATE%
    echo 請確認 Discord 已正確安裝。
    echo.
    pause
    exit /b 1
)

REM 以 Debug 模式啟動 Discord
echo [資訊] 正在以 Debug 模式啟動 Discord...
echo.
start "" "%DISCORD_UPDATE%" --processStart Discord.exe --process-start-args="--remote-debugging-port=9222"

REM 等待 Discord 啟動
echo [資訊] 等待 Discord 啟動中...
timeout /t 5 /nobreak >nul

echo.
echo ============================================
echo   Discord 已以 Debug 模式啟動
echo ============================================
echo.
echo CDP 連線位址: http://localhost:9222
echo.
echo 您現在可以執行 Python 監聽腳本：
echo   python src/main.py
echo.
echo ============================================
pause
