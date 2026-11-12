"""Crea únicamente fixtures originales: texto digital e imagen sin capa de texto."""
from pathlib import Path
import zlib


def pdf(objects: list[bytes]) -> bytes:
    result = b'%PDF-1.4\n'
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(result))
        result += f'{number} 0 obj\n'.encode() + obj + b'\nendobj\n'
    start = len(result)
    result += f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode()
    result += b''.join(f'{n:010d} 00000 n \n'.encode() for n in offsets[1:])
    result += f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n'.encode()
    return result


def stream(data: bytes, extra: bytes = b'') -> bytes:
    return b'<< /Length ' + str(len(data)).encode() + b' ' + extra + b' >>\nstream\n' + data + b'\nendstream'


def main():
    root = Path(__file__).resolve().parent
    pages = [
        ['Ejemplo ficticio de Foro IA al Dia. Pagina 1.',
         'El taller dura 90 minutos.', 'La inscripcion termina el 12 de noviembre de 2026.'],
        ['Ejemplo ficticio de Foro IA al Dia. Pagina 2.',
         'Hay 24 plazas.', 'Trae un portatil. El documento no indica un precio.'],
    ]
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>',
               b'<< /Type /Pages /Kids [3 0 R 5 0 R] /Count 2 >>',
               b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 7 0 R >> >> /Contents 4 0 R >>', b'',
               b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 7 0 R >> >> /Contents 6 0 R >>', b'',
               b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    for index, lines in enumerate(pages):
        data = b'BT /F1 14 Tf 50 780 Td 24 TL\n' + b'\n'.join(('(' + line + ') Tj T*').encode('ascii') for line in lines) + b'\nET'
        objects[3 + 2 * index] = stream(data)
    (root/'taller-ejemplo.pdf').write_bytes(pdf(objects))
    image = zlib.compress(bytes([160, 220, 220, 160]))
    (root/'solo-imagen.pdf').write_bytes(pdf([
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /XObject << /Im1 5 0 R >> >> /Contents 4 0 R >>',
        stream(b'q 200 0 0 200 50 500 cm /Im1 Do Q'),
        stream(image, b'/Type /XObject /Subtype /Image /Width 2 /Height 2 /ColorSpace /DeviceGray /BitsPerComponent 8 /Filter /FlateDecode')]))


if __name__ == '__main__':
    main()
