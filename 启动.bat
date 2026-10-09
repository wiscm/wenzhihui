@echo off
chcp 65001 >nul

echo ============================================
echo   文智汇 v1.0 - 启动
echo ============================================
echo.

set "CONDA_EXE="
for %%p in (
    "C:\ProgramData\anaconda3"
    "C:\ProgramData\Anaconda3"
    "C:\Program Files\anaconda3"
    "%USERPROFILE%\anaconda3"
    "%LOCALAPPDATA%\Continuum\anaconda3"
) do (
    if exist "%%~p\Scripts\conda.exe" set "CONDA_EXE=%%~p\Scripts\conda.exe"
)

if "%CONDA_EXE%"=="" (
    echo   X 未找到 Anaconda！
    echo   首次使用请双击 首次安装并启动.bat
    echo ============================================
    pause
    exit /b 1
)

echo   启动中，浏览器将自动打开 http://127.0.0.1:8501
echo   关闭本窗口即可停止服务
echo ============================================
cd /d "%~dp0"
start "" "http://127.0.0.1:8501"
"%CONDA_EXE%" run -n wenZhiHui streamlit run app.py --server.address=0.0.0.0 --server.port=8501 --browser.gatherUsageStats=false < NUL
pause