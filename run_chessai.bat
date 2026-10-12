@echo off
setlocal
pushd "%~dp0"
where py >nul 2>&1
if not errorlevel 1 (
    py -3 -c "import sys; assert sys.version_info.major == 3" >nul 2>&1
    if not errorlevel 1 (
        py -3 src\gui\gui.py
        goto finished
    )
)
where python >nul 2>&1
if not errorlevel 1 (
    python -c "import sys; assert sys.version_info.major == 3" >nul 2>&1
    if not errorlevel 1 (
        python src\gui\gui.py
        goto finished
    )
)
echo Python 3 was not found. Install Python with Tkinter and enable its launcher or PATH option.
popd
pause
exit /b 1
:finished
set "chessai_exit=%errorlevel%"
if not "%chessai_exit%"=="0" (
    echo ChessAI could not start. Build build\Release\ChessAI.exe and check Python/Tkinter above.
    pause
)
popd
exit /b %chessai_exit%
