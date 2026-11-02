@echo off
chcp 65001 >nul

echo ============================================
echo   文智汇 v1.0 - 首次安装并启动
echo ============================================
echo   本脚本会自动完成：
echo     1. 检测 Anaconda
echo     2. 创建 Python 环境
echo     3. 安装依赖（首次约 3-10 分钟）
echo     4. 启动服务
echo ============================================
echo.

:detect_conda
echo [1/4] 检测 Anaconda ...
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
if "%CONDA_EXE%"=="" goto no_conda
echo   OK 找到 Anaconda: %CONDA_EXE%
echo.

:check_env
echo [2/4] 准备 Python 环境 wenZhiHui ...
"%CONDA_EXE%" run -n wenZhiHui python --version >nul 2>&1
if errorlevel 1 (
    echo   首次使用，正在创建环境（约 2-3 分钟下载 Python）...
    "%CONDA_EXE%" create -n wenZhiHui python=3.11 -y
    if errorlevel 1 goto create_failed
) else (
    echo   OK 环境已存在
)
echo.

:install_deps
echo [3/4] 安装 Python 依赖（首次约 3-10 分钟，从清华源下载）...
"%CONDA_EXE%" run -n wenZhiHui pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 goto install_failed
echo   OK 依赖安装完成
echo.

:launch
echo [4/4] 启动服务，浏览器将自动打开 ...
echo   (关闭本窗口即可停止服务)
echo ============================================
cd /d "%~dp0"
start "" "http://127.0.0.1:8501"
"%CONDA_EXE%" run -n wenZhiHui streamlit run app.py --server.address=0.0.0.0 --server.port=8501 --browser.gatherUsageStats=false < NUL
goto end

:no_conda
echo.
echo   X 未检测到 Anaconda！
echo.
echo   请按以下步骤安装：
echo     1. 访问 https://www.anaconda.com/download
echo     2. 下载 "Windows 64-Bit" 版本
echo     3. 安装时务必勾选 "Add Anaconda3 to my PATH environment variable"
echo.
start "" "https://www.anaconda.com/download"
echo   安装完成后再双击本文件。
echo ============================================
pause
exit /b 1

:create_failed
echo.
echo   X 创建 Python 环境失败！
echo   可能原因：网络不通、磁盘满、或 conda 源被屏蔽。
echo   解决：换个网络（如手机热点）重试
echo ============================================
pause
exit /b 1

:install_failed
echo.
echo   X 安装依赖失败！
echo   可能原因：网络问题或清华源临时不可用
echo   解决：换个网络重试
echo ============================================
pause
exit /b 1

:end
pause