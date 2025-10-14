# ============================================================================
# README.md
# ============================================================================
# 📋 Sistema de Procesamiento de Boletas de Honorarios v3.0

## 🚀 Inicio Rápido

### 1. Ejecutar el Sistema
```batch
ejecutar_sistema.bat
```

El sistema verificará automáticamente:
- ✅ Versión de Python
- ✅ Paquetes necesarios
- ✅ Herramientas externas
- ✅ Instalará lo que falte

### 2. Primera Ejecución

Al ejecutar por primera vez, el sistema:
1. Verificará la versión de Python (3.8 - 3.11 recomendado)
2. Creará un archivo `requirements_auto.txt` personalizado
3. Instalará automáticamente los paquetes necesarios
4. Intentará instalar PaddleOCR (opcional pero recomendado)
5. Verificará Tesseract OCR y Poppler

## 🛠️ Requisitos

### Software Necesario
- **Python 3.8 a 3.11** (3.10 recomendado)
- **Tesseract OCR** (para procesamiento de imágenes)
- **Poppler** (para conversión de PDFs) - Opcional

### Instalación de Tesseract
```batch
instalar_tesseract.bat
```
O manualmente desde: https://github.com/UB-Mannheim/tesseract/wiki

### Para Mejor Compatibilidad con PaddleOCR
```batch
crear_entorno_python310.bat
```

## 📁 Estructura del Proyecto

```
proyecto_boletas/
├── main.py                 # Punto de entrada con autoinstalador
├── app_main.py            # Aplicación GUI principal
├── modules/               # Módulos del sistema
│   ├── __init__.py
│   ├── config.py          # Configuración
│   ├── ocr_processor.py   # Procesamiento OCR
│   ├── data_extractor.py  # Extracción de campos
│   ├── report_generator.py # Generación de reportes
│   └── utils.py           # Utilidades
├── Registro/              # Carpeta de entrada (boletas)
├── Export/                # Carpeta de salida (Excel)
├── temp/                  # Archivos temporales
├── ejecutar_sistema.bat   # Lanzador principal
├── instalar_tesseract.bat # Ayuda para instalar Tesseract
└── README.md              # Este archivo
```

## 💡 Uso del Sistema

### 1. Preparar las Boletas
Coloque los archivos PDF o imágenes en la carpeta `Registro/`

### 2. Ejecutar el Programa
```batch
ejecutar_sistema.bat
```

### 3. Configurar Opciones
- **Motor OCR**: Auto (recomendado), Tesseract o PaddleOCR
- **Revisión Manual**: Para corregir registros dudosos
- **Informes**: Genera análisis por convenio

### 4. Procesar
Click en "▶ Iniciar Procesamiento"

### 5. Revisar Resultados
El archivo Excel se guardará en `Export/boletas_procesadas.xlsx`

## 🔧 Solución de Problemas

### "Python no está instalado"
- Descargue Python desde: https://python.org
- Durante la instalación, marque "Add Python to PATH"

### "PaddleOCR no funciona"
- Normal en Python 3.12+
- Solución: Use `crear_entorno_python310.bat` para crear un entorno compatible

### "Tesseract no encontrado"
- Ejecute `instalar_tesseract.bat`
- O instale manualmente desde GitHub

### "No se detectan los textos"
- Verifique que los escaneos tengan al menos 300 DPI
- Pruebe cambiar el motor OCR en las opciones
- Active la revisión manual para corregir

## 📊 Características

### Extracción Automática
- ✅ Nombre del prestador
- ✅ RUT con validación
- ✅ Número de boleta
- ✅ Fecha del documento
- ✅ Monto bruto
- ✅ Convenio asociado
- ✅ Horas trabajadas
- ✅ Tipo (mensual/semanal)
- ✅ Glosa descriptiva
- ✅ Decreto alcaldicio

### Motores OCR
- **Auto**: Selección inteligente según el documento
- **Tesseract**: Rápido para documentos limpios
- **PaddleOCR**: Mejor para imágenes problemáticas
- **Embebido**: Para PDFs con texto seleccionable

### Reportes
- Base de datos completa en Excel
- Hojas separadas por convenio
- Resúmenes mensuales automáticos
- Fórmulas dinámicas

## 🆘 Soporte

Si encuentra problemas:
1. Revise que cumple los requisitos
2. Ejecute nuevamente `ejecutar_sistema.bat`
3. Verifique el log en la ventana del programa

## 📄 Licencia

Sistema de uso interno para procesamiento de boletas de honorarios.

---

**Versión 3.0** - Sistema con autoinstalación y múltiples motores OCR