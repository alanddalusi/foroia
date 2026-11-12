# Extraer texto de un PDF con Python antes de usar IA

Si un resumen omite información, quizá el problema ocurrió antes de redactarlo: el texto del PDF pudo extraerse incompleto o en un orden distinto al que ves en pantalla.

Con Python y pypdf puedes hacer una comprobación local, página por página, antes de enviar nada a un modelo. El programa de esta guía no utiliza una API, no hace OCR y no necesita una clave de IA.

## Qué necesitas y qué límites tiene el ejemplo

Necesitas Python y un entorno donde puedas instalar pypdf. La ejecución que acompaña a esta guía utiliza **Python 3.13 y pypdf 6.21.2** en Windows, en un entorno virtual independiente del blog.

Empieza con PDFs pequeños y de confianza. El script limita el tamaño a 5 MB y la longitud a 20 páginas, pero esos límites **no son una protección completa frente a archivos maliciosos o consumos elevados de memoria**. Un PDF comprimido puede requerir bastante más memoria al procesarse. No lo conviertas directamente en un servicio web de subida de archivos. [1]

Además, obtener texto no demuestra que conserve correctamente columnas, tablas, notas o el orden de lectura. La revisión visual sigue siendo necesaria.

## 1. Prepara un entorno separado

En Windows PowerShell, desde una carpeta de trabajo:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install pypdf==6.21.2
```

Usamos una versión fijada para que el ejemplo sea reproducible. No necesitas cambiar las dependencias de ningún proyecto que ya tengas. Si tu instalación utiliza otro lanzador de Python, adapta el primer comando a ese entorno.

Descarga en esa carpeta el [script extraer_pdf.py](resources/extraer_pdf.py) y el [PDF digital del taller ficticio](resources/taller-ejemplo.pdf). También tienes un [PDF sintético que contiene solo una imagen](resources/solo-imagen.pdf) para comprobar el caso sin capa de texto.

## 2. Entiende la parte principal del código

El programa completo incluye argumentos, errores básicos y protección contra sobrescritura. Su recorrido de extracción es este:

```python
reader = PdfReader(path)
parts, empty = [], []
for number, page in enumerate(reader.pages, 1):
    text = (page.extract_text() or '').strip()
    if not text:
        empty.append(number)
    parts.append(f'--- Página {number} ---\n{text}')
```

`PdfReader` abre el documento y `extract_text()` intenta recuperar el texto de cada página. Los marcadores permiten volver al PDF cuando revises una cifra. El fragmento anterior explica el núcleo; para ejecutarlo utiliza el archivo completo enlazado, que incorpora importaciones y controles.

## 3. Ejecuta la extracción del documento digital

```powershell
.\.venv\Scripts\python.exe extraer_pdf.py taller-ejemplo.pdf taller.txt
```

El programa crea un archivo UTF-8. Ábrelo junto al PDF y comprueba estos datos:

- Página 1: duración de 90 minutos y fin de inscripción el 12 de noviembre de 2026.
- Página 2: 24 plazas, un portátil como material y ausencia de precio indicado.

En la ejecución local, el script recuperó esos textos y separó las dos páginas con sus marcadores. No se detectaron páginas vacías en ese documento. Es un resultado sobre un PDF original de ejemplo, no una medición de precisión con documentos reales variados.

Si vuelves a usar `taller.txt` como salida, el programa se detiene para no sobrescribirlo. Elige otro nombre si necesitas conservar varias versiones.

## 4. Comprueba el caso de una página sin texto

```powershell
.\.venv\Scripts\python.exe extraer_pdf.py solo-imagen.pdf imagen.txt
```

En nuestra ejecución, la página 1 quedó señalada como sin texto extraíble. Ese archivo se ha generado como imagen sin capa de texto; no es un escaneo real ni una prueba de reconocimiento óptico.

pypdf no reconoce por sí mismo las letras de una imagen. Para ese caso necesitas un paso de OCR y otra revisión de sus resultados. Tampoco conviene asumir que cualquier página vacía sea un escaneo: puede estar realmente en blanco o presentar un problema de extracción. [1]

## 5. Decide si el texto sirve para el siguiente paso

Antes de usar una IA, compara al menos una página con su original, revisa las cifras que importan y busca saltos extraños entre columnas o encabezados. Si la información salió mal, corrige la extracción o reduce el documento a las páginas necesarias.

La salida conserva texto, no una representación completa del PDF. No prometemos reconstrucción fiel de tablas ni preservación de imágenes. Tampoco hace falta enviar todo el documento a un servicio externo para descubrir que una página está vacía.

Cuando tengas una extracción revisada, puedes seguir el [procedimiento de resumen con comprobación de citas](01-resumir-pdf.md). Si prefieres trabajar con una herramienta de fuentes documentales, consulta la [guía de NotebookLM basada en documentación](02-notebooklm-fuentes.md). Encontrarás más contenidos de este tipo en [Programación](https://foroiaaldia.com/programacion).

## Qué se ha ejecutado

Se han probado la extracción del PDF digital de dos páginas, el PDF de imagen sin texto, la negativa a sobrescribir una salida y un archivo inexistente. Puedes descargar también el [generador de los PDFs de ejemplo](resources/generar_ejemplos.py) para repetir la comprobación. No se han evaluado OCR, PDFs cifrados de terceros, documentos enormes ni la calidad de respuestas de un modelo.

## Fuente

1. [Documentación oficial de pypdf: extracción, dificultades del formato y OCR](https://pypdf.readthedocs.io/en/stable/user/extract-text.html).

Estado editorial: borrador pendiente de aprobación. Los recursos y enlaces entre guías son locales para revisión; no se han publicado.
