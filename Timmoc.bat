@echo off
setlocal enabledelayedexpansion

REM === Ir a la carpeta del script (repo) ===
cd /d "%~dp0"

REM === Verificación básica ===
git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Esta carpeta no es un repositorio Git.
  echo Si aun no lo tienes, clona el repo:
  echo   git clone https://github.com/PSIMAFG/proyecto_boletas.git
  exit /b 1
)

REM === Confirmar remoto ===
for /f "delims=" %%r in ('git remote') do set HASREMOTE=1
if not defined HASREMOTE (
  echo [ERROR] No hay remoto configurado. Agrega origin:
  echo   git remote add origin https://github.com/PSIMAFG/proyecto_boletas.git
  exit /b 1
)

echo === Fetch desde remoto ===
git fetch --all || (echo [ERROR] fetch fallo & exit /b 1)

REM === Detectar rama principal: main o master ===
set BRANCH=
git rev-parse --verify main >nul 2>&1 && set BRANCH=main
if "%BRANCH%"=="" git rev-parse --verify master >nul 2>&1 && set BRANCH=master
if "%BRANCH%"=="" (
  echo No encuentro main ni master. Usare la rama actual.
  for /f "tokens=1" %%b in ('git branch --show-current') do set BRANCH=%%b
)

echo === Cambiar a "%BRANCH%" ===
git switch "%BRANCH%" || (echo [ERROR] no pude cambiar de rama & exit /b 1)

REM === Si hay cambios sin commit, ofrecer stash ===
for /f "delims=" %%s in ('git status --porcelain') do set DIRTY=1
if defined DIRTY (
  echo Tienes cambios locales sin commit. Guardando en stash temporal...
  git stash push -m "auto-stash bajar_cambios" || (echo [ERROR] no pude hacer stash & exit /b 1)
  set DIDSTASH=1
)

REM === Pull con rebase (historia mas limpia) ===
echo === Pull (rebase) desde origin/%BRANCH% ===
git pull --rebase origin "%BRANCH%"
if errorlevel 1 (
  echo [ADVERTENCIA] El rebase fallo. Intentando pull con merge clasico...
  git rebase --abort >nul 2>&1
  git pull origin "%BRANCH%" || (echo [ERROR] no pude hacer pull & goto :RESTORE)
)

:RESTORE
REM === Restaurar stash si se creo ===
if defined DIDSTASH (
  echo === Restaurando tus cambios locales (stash) ===
  git stash pop
)

echo === Listo. Estado actual: ===
git --no-pager log --oneline -5
echo.
git status

endlocal
