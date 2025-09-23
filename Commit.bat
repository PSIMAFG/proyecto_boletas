@echo off
setlocal
REM Mensaje de commit desde el primer parámetro o uno por defecto
set MSG=%*
if "%MSG%"=="" set MSG=Actualiza proyecto

echo === Ubicando repo ===
cd /d "%~dp0"

echo === Estado ===
git status

echo === Agregando cambios ===
git add .

echo === Creando commit ===
git commit -m "%MSG%"

echo === Rebase con remoto (main) ===
git pull --rebase origin main

echo === Subiendo ===
git push origin HEAD

echo === Listo ===
endlocal
