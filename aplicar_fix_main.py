#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para aplicar el fix de imports en main.py
Alternativa en Python al script .bat
"""
import sys
import shutil
from pathlib import Path
from datetime import datetime

def aplicar_fix():
    """Aplica el fix de imports en main.py"""
    
    print("\n" + "="*60)
    print("FIX RÁPIDO - Imports Faltantes en main.py")
    print("="*60 + "\n")
    
    # Verificar que main.py existe
    main_path = Path("main.py")
    if not main_path.exists():
        print("❌ ERROR: No se encuentra main.py en la carpeta actual")
        print("   Ejecuta este script desde la raíz del proyecto")
        return False
    
    print("[1/4] Leyendo main.py...")
    content = main_path.read_text(encoding='utf-8')
    
    # Verificar si ya tiene el fix
    if 'from typing import' in content and all(
        t in content for t in ['List', 'Dict', 'Optional', 'Tuple']
    ):
        print("  ℹ️  main.py ya tiene los imports necesarios")
        print("  No se requieren cambios\n")
        return True
    
    # Crear backup
    print("\n[2/4] Creando backup...")
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"main.py.backup_{timestamp}"
    shutil.copy2(main_path, backup_path)
    print(f"  ✓ Backup creado: {backup_path}")
    
    # Aplicar fix
    print("\n[3/4] Aplicando corrección...")
    
    # Buscar la línea "from datetime import datetime"
    lines = content.split('\n')
    new_lines = []
    fix_applied = False
    
    for line in lines:
        new_lines.append(line)
        if 'from datetime import datetime' in line and not fix_applied:
            # Agregar el import de typing después de datetime
            new_lines.append('from typing import List, Dict, Optional, Tuple')
            fix_applied = True
    
    if not fix_applied:
        print("  ⚠️  No se pudo aplicar el fix automáticamente")
        print("     Agrega manualmente después de los imports:")
        print("     from typing import List, Dict, Optional, Tuple")
        return False
    
    # Guardar archivo modificado
    new_content = '\n'.join(new_lines)
    main_path.write_text(new_content, encoding='utf-8')
    print("  ✓ Archivo main.py actualizado")
    
    # Verificar
    print("\n[4/4] Verificando corrección...")
    try:
        # Intentar importar para verificar
        import importlib.util
        spec = importlib.util.spec_from_file_location("main", main_path)
        if spec and spec.loader:
            # Solo verificar que no hay errores de sintaxis
            compile(new_content, str(main_path), 'exec')
            print("  ✓ Sintaxis correcta")
        
        # Verificar que tiene el import
        if 'from typing import List' in new_content:
            print("  ✓ Import de typing agregado correctamente")
        else:
            print("  ⚠️  Advertencia: No se detectó el import")
            
    except SyntaxError as e:
        print(f"  ⚠️  Error de sintaxis: {e}")
        print("     Revisa el archivo manualmente")
        return False
    except Exception as e:
        print(f"  ⚠️  No se pudo verificar completamente: {e}")
        print("     Intenta ejecutar: python main.py")
    
    print("\n" + "="*60)
    print("✓ CORRECCIÓN APLICADA EXITOSAMENTE")
    print("="*60)
    print("\nAhora puedes ejecutar:")
    print("  python main.py")
    print("\nO verificar el sistema completo:")
    print("  python verificar_sistema_completo.py\n")
    
    return True

def main():
    """Función principal"""
    try:
        success = aplicar_fix()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\n⚠️  Operación cancelada por el usuario\n")
        return 130
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
