"""Vista estática local de los tres borradores; no escribe en web/public ni en la DB."""
import html
from pathlib import Path
import re
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
FILES = ['01-resumir-pdf.md', '02-notebooklm-fuentes.md', '03-extraer-pdf-python.md']


def formatted(text):
    escaped = html.escape(text)
    escaped = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', escaped)
    return re.sub(r'`([^`]+)`', r'<code>\1</code>', escaped)


def inline(text):
    result, offset = [], 0
    for match in re.finditer(r'\[([^\]\n]+)\]\(([^)\s]+)\)', text):
        result.append(formatted(text[offset:match.start()]))
        label, target = match.groups()
        if target in FILES:
            target = '#' + Path(target).stem
        allowed = target.startswith('#') or (urlsplit(target).scheme == 'https') or target.startswith('resources/')
        if allowed:
            result.append(f'<a href="{html.escape(target, quote=True)}">{html.escape(label)}</a>')
        else:
            result.append(html.escape(label))
        offset = match.end()
    result.append(formatted(text[offset:]))
    return ''.join(result)


def render(source):
    out, paragraph, code, in_code, in_list = [], [], [], False, False
    def flush():
        if paragraph:
            out.append('<p>' + inline(' '.join(paragraph)) + '</p>')
            paragraph.clear()
    for line in source.splitlines():
        if line.startswith('```'):
            flush()
            if in_code:
                out.append('<pre><code>' + html.escape('\n'.join(code)) + '</code></pre>'); code.clear()
            in_code = not in_code
            continue
        if in_code:
            code.append(line); continue
        if in_list and not line.startswith('- '):
            out.append('</ul>'); in_list = False
        if line.startswith('#'):
            flush(); level = min(len(line) - len(line.lstrip('#')), 6)
            out.append(f'<h{level}>' + inline(line[level:].strip()) + f'</h{level}>')
        elif line.startswith('- '):
            flush()
            if not in_list: out.append('<ul>'); in_list = True
            out.append('<li>' + inline(line[2:]) + '</li>')
        elif not line.strip(): flush()
        else: paragraph.append(line)
    flush()
    if in_list: out.append('</ul>')
    return '\n'.join(out)


def main():
    body = '<p class="notice">REVISIÓN LOCAL · Tres borradores sin publicar. No hay analítica, anuncios ni conexión a la API del blog.</p>'
    body += '<nav aria-label="Artículos">' + ' · '.join(f'<a href="#{Path(f).stem}">Artículo {i}</a>' for i, f in enumerate(FILES, 1)) + '</nav>'
    for file in FILES:
        body += f'<article id="{Path(file).stem}">' + render((ROOT/file).read_text(encoding='utf-8')) + '</article>'
    (ROOT/'review.html').write_text('''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>Tres artículos para revisión · Foro IA al Día</title><style>body{max-width:800px;margin:30px auto;padding:0 22px;background:#f8f7f3;color:#242420;font:18px/1.75 Georgia,serif}a{color:#8b302a}h1{font-size:34px;line-height:1.2}h2{font-size:25px;line-height:1.3}article{border-top:2px solid;padding-top:24px;margin-top:50px;scroll-margin-top:20px}pre{padding:18px;background:#eeece5;overflow:auto;font:14px/1.6 monospace}nav,.notice{font:15px/1.6 Arial,sans-serif}.notice{padding:16px;border:1px solid}a:focus-visible{outline:3px solid #8b302a;outline-offset:3px}p,li{overflow-wrap:anywhere}</style></head><body>''' + body + '</body></html>', encoding='utf-8')


if __name__ == '__main__':
    main()
