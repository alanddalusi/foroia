"""Root/CI host helper: known examples in ephemeral containers, never generated code."""
import argparse
from datetime import UTC,datetime
import importlib.util
import json
import os
from pathlib import Path
import subprocess


def verify(image,manifest,runner=subprocess.run):
    result={}
    for key,example in manifest.EXAMPLES.items():
        code=example['code']+'\n'+example['test']
        cmd=['docker','run','--rm','-i','--network','none','--read-only','--tmpfs','/tmp:rw,noexec,nosuid,size=16m',
             '--memory','128m','--cpus','0.5','--pids-limit','32','--cap-drop','ALL','--security-opt','no-new-privileges',
             '--user','65534:65534',image,'python','-I','-']
        try:
            response=runner(cmd,input=code.encode(),capture_output=True,timeout=20)
            passed=response.returncode==0 and response.stdout==b'OK\n'
        except (subprocess.TimeoutExpired,OSError):passed=False
        result[key]={'sha256':manifest.example_hash(key),'status':'passed' if passed else 'failed'}
    return {'verified_at':datetime.now(UTC).isoformat(),'image_id':image,'isolation':'network_none_no_secrets_read_only', 'examples':result}


def image_manifest(image):
    """Inspect the tested image, not the workstation's installed packages."""
    command='import sys,json;sys.path.insert(0,"/app");from app.research.examples import EXAMPLES,example_hash,dependency_hash,runtime_versions;print(json.dumps({"runtime":runtime_versions(),"dependency_sha256":dependency_hash(),"examples":{k:example_hash(k) for k in EXAMPLES}}))'
    return json.loads(subprocess.check_output(['docker','run','--rm','--network','none','--read-only',
        '--cap-drop','ALL','--security-opt','no-new-privileges','--user','65534:65534',image,'python','-I','-c',command],timeout=30))


def check_image_receipt(image,receipt):
    command='import sys,json;from pathlib import Path;sys.path.insert(0,"/app");from datetime import datetime,UTC;from app.research.examples import EXAMPLES,receipt_status;path="/tmp/receipt.json";Path(path).write_text(sys.stdin.read());status={k:receipt_status(k,path,datetime.now(UTC)) for k in EXAMPLES};print(json.dumps(status));raise SystemExit(0 if all(v=="valid" for v in status.values()) else 1)'
    subprocess.run(['docker','run','--rm','-i','--network','none','--read-only','--tmpfs','/tmp:rw,noexec,nosuid,size=16m',
        '--cap-drop','ALL','--security-opt','no-new-privileges','--user','65534:65534',image,'python','-I','-c',command],
        input=json.dumps(receipt).encode(),check=True,timeout=30)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--receipt',required=True,type=Path);parser.add_argument('--image')
    parser.add_argument('--check-receipt',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    if args.check_receipt:
        command='from datetime import datetime,UTC;from app.research.examples import EXAMPLES,verified_example;import json;valid=sum(bool(verified_example(k,"/app/receipts/verified-examples.json",datetime.now(UTC))) for k in EXAMPLES);print(json.dumps({"valid_examples":valid,"executed_examples":0}));raise SystemExit(0 if valid==len(EXAMPLES) else 1)'
        subprocess.run(['docker','exec','foroia-production-research-worker-1','python','-c',command],check=True,timeout=20)
        return 0
    if root==Path('/opt/foroia'):
        raise SystemExit('Production may validate receipts only; run examples on a local or CI runner.')
    spec=importlib.util.spec_from_file_location('editorial_examples',root/'api/app/research/examples.py')
    manifest=importlib.util.module_from_spec(spec);spec.loader.exec_module(manifest)
    image=args.image or json.loads(subprocess.check_output(['docker','inspect','foroia-production-api-1']))[0]['Image']
    if not image.startswith('sha256:'):raise ValueError('Use an inspected immutable image ID')
    actual=image_manifest(image)
    if actual['dependency_sha256']!=manifest.dependency_hash() or actual['examples']!={k:manifest.example_hash(k) for k in manifest.EXAMPLES}:
        raise SystemExit('Image differs from the local manifest; rebuild before verifying examples.')
    receipt=verify(image,manifest)
    passed=sum(e['status']=='passed' for e in receipt['examples'].values())
    if passed!=len(receipt['examples']):
        print(json.dumps({'examples_passed':passed,'examples_total':len(receipt['examples']),'receipt_written':False}))
        return 1
    receipt['runtime']=actual['runtime']
    receipt.update(mode='immutable_build_artifact',execution_location='off_production',dependency_sha256=actual['dependency_sha256'])
    check_image_receipt(image,receipt)
    args.receipt.parent.mkdir(mode=0o755,parents=True,exist_ok=True)
    args.receipt.parent.chmod(0o755)
    temporary=args.receipt.with_suffix('.tmp')
    temporary.write_text(json.dumps(receipt,indent=2),encoding='utf-8');temporary.chmod(0o644)
    os.replace(temporary,args.receipt)
    passed=sum(e['status']=='passed' for e in receipt['examples'].values())
    print(json.dumps({'examples_passed':passed,'examples_total':len(receipt['examples']),'receipt_written':True}))
    return 0 if passed==len(receipt['examples']) else 1


if __name__=='__main__':raise SystemExit(main())
