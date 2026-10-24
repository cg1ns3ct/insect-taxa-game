@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist node_modules (
  echo 第一次运行，正在安装依赖...
  call npm install
)
start "虫阶本地服务器" cmd /k "npm run dev -- --host 127.0.0.1"
timeout /t 4 >nul
start "" "http://127.0.0.1:5173/"
exit
