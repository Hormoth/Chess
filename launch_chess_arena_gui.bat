@echo off
cd /d C:\data\workspace\Chess\chess_arena

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Set API URL for this session
set CHESS_ARENA_URL=http://127.0.0.1:8001

REM Launch the desktop GUI
python -m apps.desktop_gui.main

pause
