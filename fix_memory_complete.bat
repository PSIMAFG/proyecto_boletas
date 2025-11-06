

@echo off
echo Corrigiendo referencias a self.memory...

REM Backup
copy main.py main.py.backup_memory

REM Reemplazar self.memory por MEMORY (usando PowerShell)
powershell -Command "(Get-Content main.py) -replace 'self\.memory', 'MEMORY' | Set-Content main.py.tmp"
move /Y main.py.tmp main.py

REM Verificar importación
findstr /C:"from modules import MEMORY" main.py >nul
if errorlevel 1 (
    echo Agregando importación de MEMORY...
    powershell -Command "$content = Get-Content main.py; $content = $content -replace '(from modules\.utils import \*)', '$1`nfrom modules import MEMORY'; $content | Set-Content main.py"
)

echo ✓ Corrección completada
pause