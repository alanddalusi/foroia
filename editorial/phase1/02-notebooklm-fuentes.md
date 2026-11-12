# NotebookLM con un PDF: prepara las fuentes y revisa las citas

Subir un archivo no basta para saber si una respuesta lo interpreta bien. Lo importante es poder identificar qué documento se usó y comprobar el fragmento que sostiene cada dato.

Esta guía explica un recorrido basado en la ayuda oficial de NotebookLM. En las páginas consultadas, Google también utiliza el nombre **Gemini Notebook**. Los nombres y la disposición de los controles pueden variar entre versiones y cuentas. No hemos iniciado sesión en la aplicación ni realizado una prueba con una cuenta: los pasos se apoyan en documentación, y el ejercicio tiene una referencia que puedes comprobar por tu cuenta.

## Qué preparar antes de abrir el cuaderno

Empieza en la versión web con un archivo propio y pequeño. Puedes utilizar nuestro [PDF ficticio de un taller](resources/taller-ejemplo.pdf). Mantén abierta una copia para consultar sus dos páginas.

La ayuda de Google incluye PDF entre los formatos de fuente admitidos. Antes de trabajar con documentos extensos, consulta sus requisitos y los límites que correspondan a tu cuenta; esta guía no presupone un número de documentos o una cuota de preguntas. Tampoco evalúa diferencias entre planes. [1]

No subas material privado solo para probar una función. Las condiciones de tratamiento pueden depender del servicio y de la cuenta. Revisa además qué compartes: un enlace a una vista simplificada del chat no debe tratarse como garantía de que los demás no puedan acceder a las fuentes del cuaderno. La documentación de creación y uso compartido explica los permisos disponibles. [2]

## 1. Crea un cuaderno para una sola tarea

La secuencia documentada por Google consiste en abrir el servicio, crear un cuaderno y añadir una fuente. Para este ejercicio, usa un nombre reconocible, como «Prueba de citas: taller ficticio», y añade únicamente el PDF de práctica. [2]

Trabajar con una sola fuente al principio evita una duda frecuente: no saber si una cifra vino del documento que querías resumir o de otro material. No significa que los cuadernos con varias fuentes sean incorrectos; simplemente reduce el trabajo de comprobación inicial.

Si no puedes cargar el archivo, comprueba primero su formato y las condiciones indicadas en la ayuda. Una extracción vacía puede requerir diagnóstico u OCR; no concluyas automáticamente que el problema es la cuenta o el modelo.

## 2. Selecciona la fuente y pregunta por hechos concretos

Según la ayuda del chat, puedes elegir las fuentes que se usarán para responder y consultar las citas asociadas a una respuesta. [3] En vez de empezar por un resumen abierto, plantea una pregunta con una respuesta fácil de comprobar:

```text
Usando únicamente el PDF del taller:
¿cuánto dura, cuándo termina la inscripción y cuántas plazas hay?
Incluye una referencia de la fuente para cada dato.
Si algo no está indicado, dilo expresamente.
```

La referencia manual del ejemplo es: 90 minutos y cierre de inscripción el 12 de noviembre de 2026 en la página 1; 24 plazas en la página 2. Esta es la solución de control del ejercicio, no una transcripción de una respuesta del servicio.

No es necesario que la respuesta coincida palabra por palabra. Debe conservar las cantidades, el significado y el respaldo.

## 3. Abre la cita y lee su contexto

Google documenta que se puede mostrar el texto de una referencia y seleccionarla para revisar el contexto. [3] Comprueba que el fragmento citado contiene el dato y que no pertenece a otra condición.

Por ejemplo, una respuesta podría citar la fecha de inscripción correctamente y presentarla como fecha del taller. La cita existiría, pero la interpretación sería incorrecta. En este PDF no hay fecha de celebración, de modo que ese dato debe quedar como no indicado.

Si una respuesta no aporta referencias útiles, no la conviertas en una conclusión confirmada. Reformula la pregunta o busca el dato directamente en el documento.

## 4. Pon a prueba lo que el documento no dice

Una segunda pregunta ayuda a detectar inferencias no justificadas:

```text
¿Cuál es el precio y qué día se celebra el taller?
No deduzcas que es gratuito ni confundas la fecha de inscripción
con la de celebración. Señala qué información no aparece.
```

La respuesta verificable es que **ninguno de esos dos datos está establecido**. Si el servicio ofrece una fecha o un precio, vuelve al PDF y exige el respaldo correspondiente. No hemos ejecutado esta pregunta en NotebookLM; la proponemos como comprobación reproducible para el lector.

## 5. Guarda una nota que siga siendo comprobable

Si decides conservar el resumen, incluye el nombre del documento, cuándo lo revisaste y los datos que quedaron pendientes. No guardes solo un texto fluido separado de sus fuentes: al reutilizarlo después, podrías olvidar qué se comprobó y qué era una sugerencia.

Cuando cambie el archivo de origen, revisa cómo se actualiza ese tipo de fuente en el servicio. No presupongas que una copia subida refleja automáticamente todas las modificaciones posteriores. [1]

La [guía para resumir PDFs y contrastar sus datos](01-resumir-pdf.md) amplía esta revisión. Si el archivo no ofrece texto reconocible, tienes un [procedimiento local con Python](03-extraer-pdf-python.md). Las categorías relacionadas son [Herramientas](https://foroiaaldia.com/herramientas) y [Tutoriales](https://foroiaaldia.com/tutoriales).

## Alcance de la comprobación

Se han consultado las páginas oficiales citadas y se ha validado el contenido del documento de práctica. No hay capturas de una sesión, resultados medidos del producto ni una comparación con otro servicio. No prometemos exactitud por el hecho de que una respuesta lleve citas.

## Fuentes

1. [Google: formatos, importación y actualización de fuentes](https://support.google.com/gemininotebook/answer/16215270?hl=es).
2. [Google: crear un cuaderno y permisos para compartir](https://support.google.com/gemininotebook/answer/16206563?hl=es).
3. [Google: conversación, selección de fuentes y citas](https://support.google.com/gemininotebook/answer/16179559?hl=es).

Estado editorial: borrador pendiente de aprobación. Los enlaces a otras guías son locales para revisión, todavía no URLs publicadas.
