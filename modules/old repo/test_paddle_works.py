# test_paddle.py
"""
Script de prueba para verificar que PaddleOCR funciona correctamente
"""
import sys
import os

def test_paddle():
    print("=" * 60)
    print("TEST DE PADDLEOCR")
    print("=" * 60)
    
    # 1. Verificar Python
    print(f"\n1. Python version: {sys.version}")
    if not sys.version.startswith("3.10"):
        print("   ⚠ ADVERTENCIA: Deberías estar en Python 3.10")
    else:
        print("   ✓ Python 3.10 - OK")
    
    # 2. Verificar NumPy
    try:
        import numpy as np
        print(f"\n2. NumPy version: {np.__version__}")
        if np.__version__.startswith("1.23"):
            print("   ✓ NumPy compatible - OK")
        else:
            print("   ⚠ NumPy puede dar problemas")
    except ImportError as e:
        print(f"\n2. ✗ NumPy no instalado: {e}")
        return False
    
    # 3. Verificar OpenCV
    try:
        import cv2
        print(f"\n3. OpenCV version: {cv2.__version__}")
        print("   ✓ OpenCV instalado - OK")
    except ImportError as e:
        print(f"\n3. ✗ OpenCV no instalado: {e}")
        return False
    
    # 4. Verificar PaddlePaddle
    try:
        import paddle
        print(f"\n4. PaddlePaddle version: {paddle.__version__}")
        paddle.utils.run_check()
        print("   ✓ PaddlePaddle funciona - OK")
    except Exception as e:
        print(f"\n4. ✗ PaddlePaddle error: {e}")
        return False
    
    # 5. Verificar PaddleOCR
    try:
        from paddleocr import PaddleOCR
        print("\n5. Inicializando PaddleOCR...")
        ocr = PaddleOCR(
            use_angle_cls=True,
            lang='latin',
            show_log=False,
            use_gpu=False
        )
        print("   ✓ PaddleOCR inicializado - OK")
        
        # 6. Crear imagen de prueba
        print("\n6. Creando imagen de prueba...")
        import numpy as np
        from PIL import Image, ImageDraw, ImageFont
        
        # Crear imagen con texto
        img = Image.new('RGB', (400, 100), color='white')
        draw = ImageDraw.Draw(img)
        draw.text((10, 30), "BOLETA DE HONORARIOS", fill='black')
        draw.text((10, 60), "RUT: 12.345.678-9", fill='black')
        
        # Guardar temporalmente
        test_img_path = "test_paddle_img.png"
        img.save(test_img_path)
        print("   ✓ Imagen de prueba creada")
        
        # 7. Probar OCR
        print("\n7. Probando OCR en imagen de prueba...")
        result = ocr.ocr(test_img_path, cls=True)
        
        if result and result[0]:
            print("   ✓ OCR funcionó correctamente")
            print("\n   Texto detectado:")
            for line in result[0]:
                if line and len(line) > 1:
                    text = line[1][0] if isinstance(line[1], tuple) else line[1]
                    conf = line[1][1] if isinstance(line[1], tuple) and len(line[1]) > 1 else 0
                    print(f"     - {text} (confianza: {conf:.2f})")
        else:
            print("   ✗ OCR no detectó texto")
        
        # Limpiar
        os.remove(test_img_path)
        
        return True
        
    except ImportError as e:
        print(f"\n5. ✗ PaddleOCR no instalado: {e}")
        return False
    except Exception as e:
        print(f"\n5. ✗ Error en PaddleOCR: {e}")
        return False

def main():
    success = test_paddle()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ PADDLEOCR ESTÁ FUNCIONANDO CORRECTAMENTE")
        print("\nAhora puedes ejecutar:")
        print("  python main_enhanced.py")
        print("\nY seleccionar 'PaddleOCR' o 'Auto' como motor OCR")
    else:
        print("❌ PADDLEOCR NO ESTÁ FUNCIONANDO")
        print("\nSolución:")
        print("1. Asegúrate de estar en el entorno correcto:")
        print("   conda activate boletas310")
        print("2. Ejecuta:")
        print("   install_paddle_definitivo.bat")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
    input("\nPresiona Enter para salir...")
