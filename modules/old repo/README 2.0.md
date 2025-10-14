# Sistema de Procesamiento de Boletas de Honorarios v2.0

## 📋 Descripción

Sistema modular y escalable para el procesamiento automático de boletas de honorarios chilenas mediante OCR, con capacidad de generar informes detallados por convenio y resúmenes mensuales.

## 🚀 Nuevas Características v2.0

### 1. **Arquitectura Modular**
- **config.py**: Configuración centralizada
- **modules/ocr_extraction.py**: Motor de OCR con múltiples variantes
- **modules/data_processing.py**: Procesamiento y extracción de campos
- **modules/report_generator.py**: Generación de informes avanzados
- **modules/utils.py**: Utilidades compartidas

### 2. **Generación de Informes por Convenio**
- Hojas separadas por cada convenio detectado
- Tablas mensuales con detalles de cada boleta
- Resúmenes con totales y estadísticas
- Fórmulas dinámicas que se actualizan automáticamente
- Base de datos persistente y actualizable

### 3. **Mejoras en OCR**
- Detección inteligente de texto embebido en PDFs
- Verificación de legibilidad antes de aplicar OCR
- 6 variantes de preprocesamiento para diferentes calidades de escaneo
- Mejor manejo de documentos con bajo contraste

## 📁 Estructura del Proyecto

```
proyecto_boletas/
├── main.py                 # Aplicación principal con GUI
├── config.py               # Configuración global
├── modules/
│   ├── __init__.py
│   ├── ocr_extraction.py   # Módulo de extracción OCR
│   ├── data_processing.py  # Procesamiento de datos
│   ├── report_generator.py # Generación de informes
│   └── utils.py           # Utilidades compartidas
├── bin/                    # Binarios de Tesseract y Poppler (opcional)
├── debug_preproc/          # Debug de preprocesamiento (opcional)
├── review_previews/        # Previews para revisión manual
├── Registro/               # Carpeta con archivos a procesar
└── Export/                 # Carpeta de salida
```

## 🔧 Instalación

### Requisitos Previos

1. **Python 3.7+**
2. **Tesseract OCR 4.0+**
   - Windows: https://github.com/tesseract-ocr/tesseract
   - Linux: `sudo apt-get install tesseract-ocr tesseract-ocr-spa`
   - Mac: `brew install tesseract`

3. **Poppler** (para PDFs)
   - Windows: https://github.com/oschwartz10612/poppler-windows/releases
   - Linux: `sudo apt-get install poppler-utils`
   - Mac: `brew install poppler`

### Instalación del Sistema

1. Clonar o descargar el proyecto
2. Las librerías Python se instalarán automáticamente al ejecutar el programa

## 📖 Uso

### Ejecutar la Aplicación

```bash
python main.py
```

### Interfaz Principal

#### Pestaña "Procesamiento"
1. **Carpeta raíz**: Seleccionar carpeta con las boletas a procesar
2. **Archivo de salida**: Definir nombre y ubicación del Excel resultante
3. **Opciones**:
   - ✅ **Excluir registros con baja confianza**: Filtra automáticamente registros poco confiables
   - ✅ **Revisión manual automática**: Abre diálogo para revisar boletas dudosas
   - ✅ **Generar informes por convenio**: Crea hojas adicionales con resúmenes

### Generación de Informes

Cuando se activa "Generar informes por convenio", el sistema:

#### Hoja "Base de Datos"
- Todos los registros procesados
- Campos completos extraídos
- Datos editables que actualizan los informes

#### Hojas por Convenio (ej: "Informe_PRAPS")
- **Encabezado**: Total de boletas, monto total, personas únicas
- **Tablas mensuales**: 
  - Cada mes con sus boletas detalladas
  - Campos: Nombre, RUT, N° Boleta, Fecha, Monto, Decreto, Horas, Glosa
  - Total mensual calculado automáticamente
- **Resumen anual**:
  - Tabla comparativa de todos los meses
  - Número de boletas por mes
  - Total y promedio mensual
  - Porcentaje del total anual

### Campos Extraídos

- **nombre**: Nombre del prestador de servicios
- **rut**: RUT con formato XX.XXX.XXX-X
- **nro_boleta**: Número de folio de la boleta
- **fecha_documento**: Fecha en formato YYYY-MM-DD
- **monto**: Monto bruto de honorarios
- **convenio**: Programa o convenio asociado (PRAPS, APS, SSVSA, etc.)
- **horas**: Horas trabajadas si se especifica
- **tipo**: Semanal o mensual
- **glosa**: Descripción del servicio
- **decreto_alcaldicio**: Número de decreto si aplica
- **confianza**: Nivel de confianza del OCR (0-1)

## 🔍 Convenios Detectados

El sistema reconoce automáticamente los siguientes convenios:
- AIDIA
- PASMI
- PRAPS
- DIR
- FONIS
- Mejor Niñez
- APS
- SSVSA
- HCV
- PAI / PAI-PG
- SENDA

## 🛠️ Configuración Avanzada

### Variables de Entorno
- `TESSERACT_CMD`: Ruta al ejecutable de Tesseract
- `POPPLER_PATH`: Ruta a los binarios de Poppler

### Modo Debug
Activar en la pestaña "Configuración" para guardar imágenes preprocesadas en `debug_preproc/`

## 📊 Ejemplo de Uso

1. Organizar boletas en carpetas:
   ```
   Registro/
   ├── 2024/
   │   ├── Enero/
   │   │   ├── boleta_juan_perez.pdf
   │   │   └── boleta_maria_garcia.jpg
   │   └── Febrero/
   │       └── boletas_febrero.pdf
   ```

2. Ejecutar `main.py`
3. Seleccionar carpeta "Registro"
4. Activar "Generar informes por convenio"
5. Clic en "Iniciar procesamiento"
6. Revisar boletas dudosas si aparece el diálogo
7. Abrir Excel generado con:
   - Hoja "Base de Datos" con todos los registros
   - Hojas separadas por convenio con resúmenes mensuales

## ⚠️ Solución de Problemas

### El OCR no reconoce bien el texto
- Verificar que Tesseract esté instalado con idioma español (`spa`)
- Aumentar la calidad de escaneo (mínimo 300 DPI)
- Usar la revisión manual para corregir

### No se detectan convenios
- Los convenios deben aparecer en la glosa o en el texto de la boleta
- Se pueden agregar nuevos convenios en `config.py`

### Error al procesar PDFs
- Instalar Poppler y configurar la ruta
- Verificar que los PDFs no estén protegidos con contraseña

## 📄 Licencia

Sistema de uso interno para procesamiento de boletas de honorarios.

## 🆘 Soporte

Para reportar problemas o solicitar mejoras, contactar al administrador del sistema.