@echo off
rem Lance le lint (ruff), le typage (mypy) et les tests sur chaque version de Python supportee, comme le CI.
rem
rem Usage :
rem   scripts\test_matrix.bat              -> 3.10, 3.11, 3.12 et 3.13
rem   scripts\test_matrix.bat 3.12 3.13    -> seulement ces versions
rem
rem Necessite uv (https://docs.astral.sh/uv/) : il telecharge les versions de
rem Python manquantes et cree un environnement temporaire par version, sans
rem toucher au .venv du projet.

setlocal EnableDelayedExpansion
cd /d "%~dp0.."

set "VERSIONS=%*"
if "%VERSIONS%"=="" set "VERSIONS=3.10 3.11 3.12 3.13"

where uv >nul 2>nul
if %errorlevel%==0 (
    set "UV=uv"
) else if exist ".venv\Scripts\uv.exe" (
    set "UV=.venv\Scripts\uv.exe"
) else (
    echo uv introuvable. Installe-le avec : pip install uv
    exit /b 1
)

set "FAILED="
for %%V in (%VERSIONS%) do (
    echo === Python %%V
    set "OK=1"
    "!UV!" run -q --no-project --python %%V --with-editable .[dev] -- python -m ruff check .
    if errorlevel 1 set "OK=0"
    if "!OK!"=="1" (
        "!UV!" run -q --no-project --python %%V --with-editable .[dev] -- python -m mypy
        if errorlevel 1 set "OK=0"
    )
    if "!OK!"=="1" (
        "!UV!" run -q --no-project --python %%V --with-editable .[dev] -- python -m pytest -q -p no:cacheprovider
        if errorlevel 1 set "OK=0"
    )
    if "!OK!"=="1" (
        echo --^> Python %%V : OK
    ) else (
        echo --^> Python %%V : ECHEC
        set "FAILED=!FAILED! %%V"
    )
    echo.
)

if "!FAILED!"=="" (
    echo Toutes les versions passent : %VERSIONS%
    exit /b 0
)
echo Echec sur :!FAILED!
exit /b 1
