"""Empaquetar solo codigo; nunca .env, claves, datos ni cachés locales."""
import hashlib
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {'.git', '.local', '.venv', 'venv', 'node_modules', '.nuxt', '.output',
            '__pycache__', '.pytest_cache', 'production.env'}


def make_release(target: Path):
    paths = [ROOT / p for p in ('api', 'web', 'deploy', 'scripts', 'docs', 'compose.production.yml', 'DEPLOYMENT.md')]
    target.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(target, 'x:gz') as archive:
        for entry in paths:
            files = sorted(entry.rglob('*')) if entry.is_dir() else [entry]
            for file in files:
                relative = file.relative_to(ROOT)
                if any(p in EXCLUDED or p.startswith('.env') for p in relative.parts):
                    continue
                if file.is_symlink() or not file.is_file() or file.suffix.lower() in {'.pem', '.key', '.age', '.pyc', '.dump', '.sql'}:
                    continue
                if ROOT not in file.resolve().parents:
                    raise ValueError('Archivo fuera del proyecto')
                archive.add(file, arcname=relative.as_posix(), recursive=False)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix(target.suffix + '.sha256').write_text(f'{digest}  {target.name}\n', encoding='ascii')
    print(f'Paquete preparado: {target.name}; SHA256 {digest}')


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        raise SystemExit('Uso: python deploy/make-release.py RUTA_ARCHIVO_NUEVO.tar.gz')
    make_release(Path(sys.argv[1]).resolve())
