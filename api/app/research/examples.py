"""Reviewed executable examples. The model selects IDs, never supplies runnable code."""
import hashlib
import json
import platform
from importlib.metadata import version
from datetime import UTC, datetime, timedelta
from pathlib import Path

EXAMPLES = {
    'json_validation': {
        'code': '''import json

def parse_response(raw):
    if len(raw.encode("utf-8")) > 10_000:
        raise ValueError("Respuesta demasiado grande")
    value = json.loads(raw)
    if not isinstance(value, dict) or not isinstance(value.get("resumen"), str):
        raise ValueError("Se esperaba un objeto con resumen de texto")
    return value["resumen"]
''',
        'test': '''assert parse_response('{"resumen":"Ejemplo"}') == "Ejemplo"
for raw in ('{', '[]', '{"resumen":8}', 'x' * 10001):
    try: parse_response(raw)
    except (ValueError, TypeError): pass
    else: raise AssertionError("Invalid input accepted")
print("OK")
''', 'docs': ['https://docs.python.org/3.12/library/json.html']},
    'json_csv': {
        'code': '''import csv
import io
import json

def response_to_csv(raw):
    rows = json.loads(raw)
    if not isinstance(rows, list) or len(rows) > 100:
        raise ValueError("Se esperaba una lista pequeña")
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=["tema", "resumen"], extrasaction="raise")
    writer.writeheader()
    for row in rows:
        if set(row) != {"tema", "resumen"} or not all(isinstance(v, str) for v in row.values()):
            raise ValueError("Columnas no válidas")
        if any(v.lstrip().lstrip(chr(65279)).lstrip().startswith(("=", "+", "-", "@")) for v in row.values()):
            raise ValueError("Celda potencialmente interpretable como fórmula")
        writer.writerow(row)
    return output.getvalue()
''',
        'test': '''assert response_to_csv('[{"tema":"IA","resumen":"Texto, con coma"}]') == 'tema,resumen\\r\\nIA,"Texto, con coma"\\r\\n'
for value in ("=1+1", chr(9)+"=1+1", "  +1", chr(65279)+"=1+1"):
    try: response_to_csv(json.dumps([{"tema":value,"resumen":"Texto"}]))
    except ValueError: pass
    else: raise AssertionError("Unsafe cell accepted")
print("OK")
''', 'docs':['https://docs.python.org/3.12/library/csv.html','https://docs.python.org/3.12/library/json.html']},
    'sqlite_results': {
        'code': '''import sqlite3

def save_summary(connection, topic, summary):
    connection.execute("CREATE TABLE IF NOT EXISTS summaries (topic TEXT PRIMARY KEY, summary TEXT NOT NULL)")
    connection.execute("INSERT OR REPLACE INTO summaries VALUES (?, ?)", (topic, summary))
    connection.commit()
''',
        'test': '''with sqlite3.connect(":memory:") as connection:
    save_summary(connection, "Tema ' de ejemplo", "Resumen")
    assert connection.execute("SELECT summary FROM summaries").fetchall() == [("Resumen",)]
    save_summary(connection, "Tema ' de ejemplo", "Revisión")
    assert connection.execute("SELECT COUNT(*) FROM summaries").fetchone()[0] == 1
print("OK")
''', 'docs':['https://docs.python.org/3.12/library/sqlite3.html','https://www.sqlite.org/lang_conflict.html']},
    'text_normalization': {
        'code': '''import unicodedata

def comparison_key(text):
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())
''',
        'test': '''assert comparison_key("  IA   EN ESPAÑOL ") == "ia en español"
assert comparison_key("ＡＩ") == "ai"
assert comparison_key("año") != comparison_key("ano")
print("OK")
''','docs':['https://docs.python.org/3.12/library/unicodedata.html','https://docs.python.org/3.12/library/stdtypes.html']},
    'pydantic_response': {
        'code': '''from pydantic import BaseModel, ConfigDict, Field

class Summary(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    title: str = Field(min_length=3, max_length=120)
    points: list[str] = Field(min_length=1, max_length=5)
''',
        'test': '''from pydantic import ValidationError
assert Summary.model_validate({"title":"Tema","points":["Idea"]}).title == "Tema"
for payload in ({"title":8,"points":["Idea"]}, {"title":"Tema","points":[]}, {"title":"Tema","points":["Idea"],"other":1}):
    try: Summary.model_validate(payload)
    except ValidationError: pass
    else: raise AssertionError("Invalid payload accepted")
print("OK")
''','docs':['https://pydantic.dev/docs/validation/latest/concepts/models/','https://pydantic.dev/docs/validation/latest/concepts/strict_mode/']},
    'fastapi_body': {
        'code': '''from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field

app = FastAPI()

class PromptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=500)

@app.post("/prepare")
def prepare(payload: PromptRequest):
    return {"text": payload.text.strip()}
''',
        'test': '''import asyncio, json
async def request(payload):
    messages = []
    body = json.dumps(payload).encode()
    async def receive(): return {"type":"http.request", "body":body, "more_body":False}
    async def send(message): messages.append(message)
    scope={"type":"http","asgi":{"version":"3.0"},"http_version":"1.1","method":"POST","scheme":"http","path":"/prepare","raw_path":b"/prepare","query_string":b"","headers":[(b"content-type",b"application/json")],"client":("127.0.0.1",1),"server":("sandbox",80),"root_path":""}
    await app(scope,receive,send)
    return messages[0]["status"]
assert asyncio.run(request({"text":"Ejemplo"})) == 200
assert asyncio.run(request({"text":""})) == 422
assert asyncio.run(request({"text":"Ejemplo","extra":1})) == 422
print("OK")
''','docs':['https://fastapi.tiangolo.com/tutorial/body/','https://fastapi.tiangolo.com/tutorial/body-fields/']},
}


def example_hash(key):
    example=EXAMPLES[key]
    return hashlib.sha256((example['code']+'\n'+example['test']).encode()).hexdigest()


def dependency_hash():
    root=Path(__file__).resolve().parents[2]
    return hashlib.sha256(b'\0'.join((root/name).read_text(encoding='utf-8-sig').encode() for name in ['requirements.txt','constraints.txt'])).hexdigest()


def runtime_versions():return {'python':platform.python_version(),'fastapi':version('fastapi'),'pydantic':version('pydantic')}


def receipt_status(key, receipt_path, now, *, _receipt=None):
    """Machine-readable diagnostics; never turn a mismatch into an approval."""
    if key not in EXAMPLES: return 'unknown_example'
    try:
        receipt=_receipt if _receipt is not None else json.loads(Path(receipt_path).read_text(encoding='utf-8'))
        at=datetime.fromisoformat(receipt['verified_at'])
        if at.tzinfo is None or at>now+timedelta(minutes=5): return 'invalid_verification_date'
        if receipt.get('mode')=='immutable_build_artifact':
            if receipt.get('execution_location')!='off_production':return 'untrusted_execution_location'
            if receipt.get('dependency_sha256')!=dependency_hash():return 'dependency_mismatch'
            if receipt.get('runtime')!=runtime_versions():return 'runtime_mismatch'
        elif at<now-timedelta(hours=48):return 'receipt_expired'
        row=receipt['examples'][key]
        if row['sha256']!=example_hash(key):return 'example_code_mismatch'
        if row['status']!='passed':return 'example_test_failed'
        if not receipt['image_id'].startswith('sha256:'):return 'invalid_image_identity'
        return 'valid'
    except (OSError,ValueError,KeyError,TypeError):return 'receipt_missing_or_invalid'


def verified_example(key, receipt_path, now):
    try:receipt=json.loads(Path(receipt_path).read_text(encoding='utf-8'))
    except (OSError,ValueError,TypeError):return None
    if receipt_status(key,receipt_path,now,_receipt=receipt)!='valid':return None
    return dict(EXAMPLES[key],id=key,sha256=receipt['examples'][key]['sha256'],
        verified_at=receipt['verified_at'],image_id=receipt['image_id'],runtime=receipt.get('runtime',{}))
