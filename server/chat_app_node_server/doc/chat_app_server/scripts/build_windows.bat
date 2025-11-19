@echo off
REM Windows 平台打包脚本（调用 Nuitka）
REM 在 Windows 命令提示符中运行此脚本

SETLOCAL ENABLEDELAYEDEXPANSION
echo === 安装依赖 ===
python -m pip install -r requirements.txt
IF %ERRORLEVEL% NEQ 0 (
  echo 依赖安装失败。
  EXIT /B 1
)

echo === 使用 Nuitka 构建（目录型产物）===
python scripts\build_nuitka.py
IF %ERRORLEVEL% NEQ 0 (
  echo 构建失败。
  EXIT /B 1
)

echo ✓ 构建完成。
echo 产物位于 dist\chat_app_server_nuitka_windows_x64（目录型产物）
ENDLOCAL
EXIT /B 0