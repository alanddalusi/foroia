"""Ejemplo local para PDFs pequeños y de confianza. No implementa OCR ni llama a IA."""
import argparse
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError


def extraer(path: Path) -> tuple[str, list[int]]:
    if path.stat().st_size > 5_000_000:
        raise ValueError('Este ejemplo admite archivos de hasta 5 MB.')
    reader = PdfReader(path)
    if reader.is_encrypted:
        raise ValueError('El ejemplo no procesa documentos cifrados.')
    if len(reader.pages) > 20:
        raise ValueError('Este ejemplo admite como máximo 20 páginas.')
    parts, empty = [], []
    for number, page in enumerate(reader.pages, 1):
        text = (page.extract_text() or '').strip()
        if not text:
            empty.append(number)
        parts.append(f'--- Página {number} ---\n{text}')
    return '\n\n'.join(parts) + '\n', empty


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf', type=Path)
    parser.add_argument('salida', type=Path)
    args = parser.parse_args()
    if args.salida.exists():
        parser.error('La salida ya existe. Elige otro nombre para no sobrescribirla.')
    try:
        text, empty = extraer(args.pdf)
        # Exclusive creation: another process cannot cause an existing file to be overwritten.
        with args.salida.open('x', encoding='utf-8') as target:
            target.write(text)
    except (OSError, ValueError, PdfReadError) as error:
        parser.exit(1, f'No se pudo extraer el PDF: {error}\n')
    if empty:
        print('Páginas sin texto extraíble: ' + ', '.join(map(str, empty)))
        print('Puede haber imágenes, páginas vacías o un problema de extracción; revísalas visualmente.')
    else:
        print('Texto extraído. Revisa su orden, cifras y correspondencia con el PDF.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
