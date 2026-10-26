@echo off
chcp 65001 >nul
set "INSTDIR=%~dp0"
echo 正在卸载 文智汇（文智汇 / WenZhiHui）...
echo.

:: 删除桌面与开始菜单快捷方式
set "DESKTOP=%USERPROFILE%\Desktop"
set "STARTMENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
if exist "%DESKTOP%\文智汇.lnk" del /f "%DESKTOP%\文智汇.lnk"
if exist "%STARTMENU%\文智汇.lnk" del /f "%STARTMENU%\文智汇.lnk"
if exist "%STARTMENU%\卸载 文智汇.lnk" del /f "%STARTMENU%\卸载 文智汇.lnk"

:: 删除“添加/删除程序”中的卸载项（HKCU，无需管理员）
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\文智汇" /f >nul 2>&1

:: 延迟删除整个安装目录（含本文件自身）
start "" /b cmd /c "ping -n 2 127.0.0.1 >nul & rmdir /s /q \"%INSTDIR%\""

echo.
echo 文智汇已卸载，安装目录已删除。
echo 若浏览器窗口仍开着，请手动关闭。
pause
