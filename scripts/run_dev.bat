@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%.." >nul
set "PROJECT_DIR=%CD%"
popd >nul
set "VENV_DIR=%PROJECT_DIR%\.venv"

cd /d "%PROJECT_DIR%"

where py >nul 2>nul
if %errorlevel%==0 (
    set "PY=py -3"
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo Python nao encontrado no PATH.
        exit /b 1
    )
    set "PY=python"
)

if not exist "%VENV_DIR%" (
    echo Criando virtualenv em "%VENV_DIR%"...
    %PY% -m venv "%VENV_DIR%"
)

call "%VENV_DIR%\Scripts\activate.bat"

python -m pip install --upgrade pip >nul
python -m pip install -r "%PROJECT_DIR%\requirements.txt"

python -m easyjlc %*
exit /b %errorlevel%
