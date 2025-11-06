#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fix simple para agregar imports en main.py"""

import sys
from pathlib import Path

def main():
    print("\n" + "="*50)
    print("FIX RAPIDO - main.py")
    print("="*50 + "\n")
    
    # Verificar main.py
    if not Path("main.py").exists():
        print("ERROR: main.py no encontrado")
        print("Ejecuta desde la raiz del proyecto")
        return 1
    
    print("[1/3] Leyendo main.py...")
    try:
        with open("main.py", "r", encoding="utf-8") as f:
            content = f.read()
    except:
        print("ERROR: No se pudo leer main.py")
        return 1
    
    # Verificar si ya tiene el fix
    if "from typing import" in content:
        print("OK - Ya tiene los imports necesarios\n")
        print("Ejecuta: python main.py")
        return 0
    
    # Crear backup
    print("[2/3] Creando backup...")
    Path("backups").mkdir(exist_ok=True)
    try:
        with open("backups/main.py.backup", "w", encoding="utf-8") as f:
            f.write(content)
        print("OK - Backup creado")
    except:
        print("Advertencia: No se pudo crear backup")
    
    # Aplicar fix
    print("[3/3] Aplicando correccion...")
    lines = content.split("\n")
    new_lines = []
    fixed = False
    
    for line in lines:
        new_lines.append(line)
        if "from datetime import datetime" in line and not fixed:
            new_lines.append("from typing import List, Dict, Optional, Tuple")
            fixed = True
    
    if not fixed:
        print("ERROR: No se encontro la linea de referencia")
        print("\nSOLUCION MANUAL:")
        print("1. Abre main.py")
        print("2. Busca: from datetime import datetime")
        print("3. Agrega debajo: from typing import List, Dict, Optional, Tuple")
        return 1
    
    # Guardar
    try:
        with open("main.py", "w", encoding="utf-8") as f:
            f.write("\n".join(new_lines))
        print("OK - Correccion aplicada")
    except:
        print("ERROR: No se pudo guardar main.py")
        return 1
    
    # Resumen
    print("\n" + "="*50)
    print("CORRECCION COMPLETADA")
    print("="*50)
    print("\nAhora ejecuta:")
    print("  python main.py\n")
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nCancelado\n")
        sys.exit(130)
    except Exception as e:
        print(f"\nERROR: {e}\n")
        sys.exit(1)
