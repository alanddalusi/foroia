# Cómo resumir un PDF con IA y comprobar sus citas

Un resumen puede sonar convincente y cambiar un plazo, omitir una condición o añadir algo que el documento nunca dice. Para usarlo con confianza, necesitas poder volver desde cada afirmación importante hasta el fragmento que la respalda.

Este procedimiento propone separar tres tareas: comprobar que el PDF se lee, pedir un resumen acotado y contrastar sus datos. No exige una herramienta concreta ni presupone que la IA vaya a acertar.

## 1. Empieza por un archivo que puedas revisar

Utiliza un documento propio o que tengas permiso para tratar. Para practicar, tienes el [PDF de ejemplo de dos páginas](resources/taller-ejemplo.pdf), creado expresamente para esta guía. Describe un taller ficticio: no es una convocatoria real.

Antes de subir un archivo a un servicio, revisa sus condiciones y el tipo de cuenta. Un contrato, unas notas médicas o una lista de alumnos no son buenos documentos para una primera prueba. El ejemplo evita datos personales y permite comprobar las respuestas sin conocimientos especializados.

Abre el PDF e intenta seleccionar y copiar una frase. Si aparece texto reconocible, ya tienes una comprobación inicial; no demuestra que todas las páginas se extraigan bien. Si solo ves una imagen, puede hacer falta reconocimiento óptico de caracteres, llamado OCR. También existen documentos mixtos, con páginas de ambos tipos. La documentación de pypdf distingue estos casos y explica que extraer texto y hacer OCR no son lo mismo. [1]

## 2. Define qué necesitas del resumen

«Resume este PDF» deja abiertas demasiadas decisiones. Es más útil fijar una finalidad: recordar los requisitos de una actividad, localizar condiciones o preparar preguntas de repaso.

Puedes adaptar esta petición:

```text
Trabaja solo con el documento que he adjuntado.
Resume su contenido en cinco puntos como máximo.
Para cada dato importante, indica la página y el fragmento que lo respalda.
Separa hechos del documento de recomendaciones tuyas.
Si una información no aparece, escribe «no consta en el documento».
No deduzcas fechas, importes ni requisitos que no estén escritos.
```

Es una instrucción de trabajo, no una garantía. La herramienta elegida puede no admitir archivos, no conservar la paginación o no ofrecer citas comprobables. Si solo trabaja con texto pegado, conserva marcadores de página, pero comprueba que no se hayan perdido tablas o notas.

## 3. Comprueba el ejemplo sin depender de una respuesta de IA

Estas son las respuestas que se pueden verificar leyendo directamente el PDF de práctica:

- Duración del taller: **90 minutos**, en la página 1.
- Fin de inscripción: **12 de noviembre de 2026**, en la página 1.
- Plazas: **24**, en la página 2.
- Material indicado: **un portátil**, en la página 2.
- Precio: **no consta**. La página 2 dice expresamente que el documento no indica un precio.

Si un resumen afirma «el taller es gratuito», ha dado un salto injustificado. No indicar un precio no significa que el precio sea cero. Del mismo modo, el plazo de inscripción no es la fecha de celebración: ese día no figura en el ejemplo.

Esta lista es una referencia preparada a partir del documento original, **no una salida obtenida de un modelo**. Puedes usarla para evaluar la herramienta que elijas sin tomar su respuesta como verdad de partida.

## 4. Revisa cifras, negaciones y condiciones

No hace falta comparar cada palabra del resumen. Empieza por los datos que podrían cambiar una decisión: fechas, cantidades, unidades, excepciones y obligaciones.

Para cada uno, anota qué dice el resumen, dónde aparece en el PDF y si conserva su alcance. Una cita puede existir y, aun así, no respaldar la conclusión. Revisa el párrafo completo, no solo la coincidencia de una palabra.

Si la herramienta proporciona referencias interactivas, ábrelas. La ayuda de NotebookLM —que actualmente puede aparecer como Gemini Notebook en la documentación— explica cómo consultar la cita y volver al contexto de la fuente. Esa posibilidad facilita la comprobación, pero no la sustituye. [2]

## 5. Corrige el resumen o vuelve al documento

Si detectas un error, pide una corrección concreta: «La página 2 no establece que sea gratis. Retira esa afirmación y señala que el precio no consta». Después revisa también la versión corregida.

Cuando no puedas localizar el respaldo, conserva el dato como pendiente. Y si la extracción pierde páginas o mezcla columnas, resuelve ese problema antes de pedir más resúmenes. Una respuesta más larga no recupera información que nunca llegó al modelo.

Para continuar, consulta la [guía de fuentes y citas en NotebookLM](02-notebooklm-fuentes.md) o el [ejemplo de extracción local con Python](03-extraer-pdf-python.md). También puedes recorrer las secciones de [Tutoriales](https://foroiaaldia.com/tutoriales) y [Programación](https://foroiaaldia.com/programacion).

## Qué se ha comprobado en esta guía

Se ha creado el PDF original y se ha ejecutado su extracción con Python para contrastar los datos de las dos páginas. No se ha enviado a una IA ni se ha probado el rendimiento de un producto comercial. La petición propuesta y los criterios de revisión son un procedimiento editorial, no resultados experimentales de un modelo.

## Fuentes

1. [pypdf: extracción de texto, PDFs escaneados y límites](https://pypdf.readthedocs.io/en/stable/user/extract-text.html).
2. [Ayuda de Google: conversación y revisión de citas](https://support.google.com/gemininotebook/answer/16179559?hl=es).

Estado editorial: borrador pendiente de aprobación. Los enlaces a las otras dos guías son locales para esta revisión; las URLs públicas previstas figuran en el plan editorial.
