import json
from datetime import timedelta

import pytest

from app.research.examples import EXAMPLES, example_hash, dependency_hash, runtime_versions, receipt_status, verified_example
from test_editorial_engines import NOW
from test_research import client,database


@pytest.mark.parametrize('fault,reason', [
    (None,'valid'), ('dependencies','dependency_mismatch'), ('runtime','runtime_mismatch'),
    ('code','example_code_mismatch'), ('failed','example_test_failed'),
    ('location','untrusted_execution_location'), ('date','invalid_verification_date')])
def test_exact_receipt_diagnostics_never_approve_mismatches(tmp_path,fault,reason):
    receipt={'verified_at':NOW.isoformat(),'image_id':'sha256:'+'a'*64,
             'mode':'immutable_build_artifact','execution_location':'off_production',
             'dependency_sha256':dependency_hash(),'runtime':runtime_versions(),
             'examples':{k:{'sha256':example_hash(k),'status':'passed'} for k in EXAMPLES}}
    if fault=='dependencies':receipt['dependency_sha256']='0'*64
    if fault=='runtime':receipt['runtime']['python']='0.0.0'
    if fault=='code':receipt['examples']['json_validation']['sha256']='0'*64
    if fault=='failed':receipt['examples']['json_validation']['status']='failed'
    if fault=='location':receipt['execution_location']='production'
    if fault=='date':receipt['verified_at']=(NOW+timedelta(days=1)).isoformat()
    path=tmp_path/'receipt.json';path.write_text(json.dumps(receipt))
    assert receipt_status('json_validation',path,NOW)==reason
    assert bool(verified_example('json_validation',path,NOW))==(reason=='valid')


@pytest.mark.parametrize('fault',['stale_image','failed_test'])
def test_receipt_builder_preserves_previous_receipt_when_verification_fails(tmp_path,monkeypatch,fault):
    import importlib.util
    from pathlib import Path
    import sys
    spec=importlib.util.spec_from_file_location('receipt_builder',Path(__file__).parents[1]/'scripts/verify_editorial_examples.py')
    builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
    path=tmp_path/'receipt.json';path.write_text('previous verified artifact')
    manifest={'runtime':runtime_versions(),'dependency_sha256':dependency_hash(),
              'examples':{k:example_hash(k) for k in EXAMPLES}}
    if fault=='stale_image':manifest['dependency_sha256']='0'*64
    monkeypatch.setattr(builder,'image_manifest',lambda image:manifest)
    monkeypatch.setattr(builder,'verify',lambda image,manifest:{'examples':{k:{'status':'failed'} for k in EXAMPLES}})
    monkeypatch.setattr(sys,'argv',['verify','--receipt',str(path),'--image','sha256:'+'a'*64])
    if fault=='stale_image':
        with pytest.raises(SystemExit,match='Image differs'):builder.main()
    else:assert builder.main()==1
    assert path.read_text()=='previous verified artifact'


def test_only_resolved_receipt_rejections_are_reopened_once(client,tmp_path):
    from sqlalchemy import select,func
    from app.models import EditorialCandidate,AuditLog
    from app.research import queue
    from test_editorial_engines import receipt
    path=receipt(tmp_path)
    async def operation(db):
        await queue.seed_evergreen(db)
        rows=(await db.scalars(select(EditorialCandidate).order_by(EditorialCandidate.id))).all()
        for row,reason in zip(rows[:2],['example_not_verified','editorial_style_rejected']):
            row.state='rejected';row.reason=reason;row.details=dict(row.details,preflight_failures=3)
        await db.commit()
        assert await queue.recover_verified_examples(db,NOW,tmp_path/'absent')==0
        assert await queue.recover_verified_examples(db,NOW,path)==1
        assert await queue.recover_verified_examples(db,NOW,path)==0
        assert rows[0].state=='queued' and rows[0].attempts==0
        assert rows[1].state=='rejected' and rows[1].reason=='editorial_style_rejected'
        assert await db.scalar(select(func.count(AuditLog.id)).where(AuditLog.action=='example_receipt_recovered'))==1
    database(operation)
