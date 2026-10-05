@echo off
setlocal
python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
python -m PyInstaller --noconfirm --clean --windowed --name WPOS_PRO_2 app\wpos_app.py
if errorlevel 1 exit /b 1
python -m PyInstaller --noconfirm --clean --windowed --name WPOS_Password_Reset app\reset_tool.py
if errorlevel 1 exit /b 1
echo Build selesai. EXE ada di dist\WPOS_PRO_2 dan dist\WPOS_Password_Reset.
