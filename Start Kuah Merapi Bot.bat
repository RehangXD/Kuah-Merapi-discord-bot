@echo off
title Bot Discord - Kuah Merapi
color 0a

echo Menyalakan Bot...
cd /d "C:\Users\dll"

echo Mengaktifkan Virtual Environment...
call dc_env\Scripts\activate.bat

echo Menjalankan main.py...
python main.py

echo.
echo Bot terhenti atau terjadi error!
pause
