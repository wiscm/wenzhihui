@echo off
chcp 65001 >nul
cd /d "%~dp0"
start "" "http://127.0.0.1:8501"
"C:\ProgramData\anaconda3\envs\wenZhiHui\Scripts\streamlit.exe" run app.py --server.address=0.0.0.0 --server.port=8501 --browser.gatherUsageStats=false < NUL
pause