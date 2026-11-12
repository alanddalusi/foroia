"""Prepare reviewable ArticleWrite payloads; never connects to an API or database."""
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
SPECS = [
    ('01-resumir-pdf.md', 'resumir-pdf-ia-comprobar-citas', 'tutoriales', 'Aprende a resumir un PDF con IA y revisar fechas, cifras y citas con un documento de ejemplo y una referencia que puedes comprobar.'),
    ('02-notebooklm-fuentes.md', 'notebooklm-pdf-fuentes-citas', 'herramientas', 'Prepara un PDF como fuente en NotebookLM y aprende a revisar sus citas. Guía documental con un ejercicio que puedes comprobar.'),
    ('03-extraer-pdf-python.md', 'extraer-texto-pdf-python', 'programacion', 'Extrae texto de un PDF con Python y pypdf, conserva las páginas y detecta casos sin texto antes de enviar el documento a una IA.'),
]


def main():
    paths = {file: '/articulos/' + slug for file, slug, _, _ in SPECS}
    payloads = []
    assets = REPO / 'web/public/recursos/guias-pdf'
    assets.mkdir(parents=True, exist_ok=True)
    checksums = {}
    for filename in ['extraer_pdf.py', 'taller-ejemplo.pdf', 'solo-imagen.pdf', 'generar_ejemplos.py']:
        source = ROOT / 'resources' / filename
        shutil.copyfile(source, assets / filename)
        checksums[filename] = hashlib.sha256(source.read_bytes()).hexdigest()
    for file, slug, section, summary in SPECS:
        text = (ROOT / file).read_text(encoding='utf-8')
        title, body = text.split('\n', 1)
        body = re.sub(r'\nEstado editorial:.*', '', body).strip()
        for local, public in paths.items():
            body = body.replace('](' + local + ')', '](' + public + ')')
        body = body.replace('](resources/', '](/recursos/guias-pdf/')
        body = body.replace('](https://foroiaaldia.com/', '](/')
        payloads.append(dict(slug=slug, title=title.removeprefix('# '), summary=summary,
                             body=body, section=section, author_name='Redacción de Foro IA al Día · con asistencia de IA',
                             sources=[dict(title=label, url=url, language='es' if 'hl=es' in url else 'en')
                                      for label, url in re.findall(r'\[([^\]]+)\]\((https://[^)]+)\)', text.split('## Fuente', 1)[1])]))
    for field in ['slug', 'title', 'summary']:
        assert len({p[field] for p in payloads}) == 3, field
    for item in payloads:
        assert not re.search(r'\]\((resources/|0[123]-)', item['body'])
        assert 50 <= len(item['summary']) <= 300
    (ROOT / 'publication.json').write_text(json.dumps(payloads, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (ROOT / 'resource-checksums.json').write_text(json.dumps(checksums, indent=2) + '\n', encoding='utf-8')
    print('Prepared 3 unique payloads and 4 static resources. No publication performed.')


if __name__ == '__main__':
    main()
