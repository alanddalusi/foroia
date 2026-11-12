from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_local_environment_is_ignored():
    # Un archivo local es necesario para Compose; debe quedar fuera de Git.
    ignored = (ROOT / '.gitignore').read_text(encoding='utf-8').splitlines()
    assert '.env' in ignored
    assert (ROOT / '.env.example').exists()

def test_codex_instructions_exist():
    assert (ROOT / 'AGENTS.md').exists()
    assert (ROOT / 'docs/SECURITY.md').exists()

def test_only_published_topics_are_exposed():
    source = (ROOT / 'api/app/modules/forum.py').read_text(encoding='utf-8')
    assert 'Topic.published.is_(True)' in source
