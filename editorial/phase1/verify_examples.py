"""Run with the isolated Python that has pypdf installed. No model/API calls."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import pypdf

ROOT = Path(__file__).resolve().parent
RESOURCES = ROOT/'resources'


def main():
    env = {**os.environ, 'PYTHONIOENCODING': 'utf-8'}
    subprocess.run([sys.executable, str(RESOURCES/'generar_ejemplos.py')], check=True)
    with tempfile.TemporaryDirectory() as folder:
        out = Path(folder)
        def run(name, target):
            return subprocess.run([sys.executable, str(RESOURCES/'extraer_pdf.py'), str(RESOURCES/name), str(target)],
                                  capture_output=True, text=True, encoding='utf-8', env=env)
        digital = run('taller-ejemplo.pdf', out/'taller.txt')
        assert digital.returncode == 0
        text = (out/'taller.txt').read_text(encoding='utf-8')
        for value in ['90 minutos', '12 de noviembre de 2026', '24 plazas', 'un portatil', 'no indica un precio', 'Página 1', 'Página 2']:
            assert value in text, value
        image = run('solo-imagen.pdf', out/'imagen.txt')
        assert image.returncode == 0 and 'Páginas sin texto extraíble: 1' in image.stdout
        assert run('taller-ejemplo.pdf', out/'taller.txt').returncode != 0
        assert (out/'taller.txt').read_text(encoding='utf-8') == text
        assert run('no-existe.pdf', out/'missing.txt').returncode != 0 and not (out/'missing.txt').exists()
    report = {'python': sys.version.split()[0], 'pypdf': pypdf.__version__, 'digital_pdf': 'passed',
              'image_only_pdf': 'passed', 'overwrite_prevention': 'passed', 'missing_input': 'passed',
              'sha256': {name: hashlib.sha256((RESOURCES/name).read_bytes()).hexdigest()
                         for name in ['taller-ejemplo.pdf', 'solo-imagen.pdf', 'extraer_pdf.py']}}
    (ROOT/'EXAMPLE_VERIFICATION.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('Four local example checks passed. No OCR or model calls performed.')


if __name__ == '__main__':
    main()
