"""Run ownership, immutable provenance and atomic acceptance contracts."""
import pytest

from app.hive.store import HiveStore
from tests.hive_testkit import legacy_database

E={'id':'E-same','source_id':'source','title':'Title','url':'https://source','text':'exact source text'}

@pytest.fixture
def store(tmp_path):
    s=HiveStore(str(tmp_path/'hive.db'))
    yield s
    s.db.close()


def claimed(store, run, key='research', now=1):
    store.add_task(run,key,'research','Research',{})
    return store.claim(run,'worker',lease_s=100,now=now)


def publish(store, task, *, evidence=None, facts=None):
    return store.publish(task['id'],'worker',task['attempt'],task['fence'],{'accepted':True},
                         evidence=evidence,facts=facts,now=2)


def test_two_runs_publish_same_evidence_id(store):
    runs=[store.create_run('one',100),store.create_run('two',100)]
    for run in runs:
        assert publish(store,claimed(store,run),evidence=[E])
        assert store.evidence(run)==[{**E,'run_id':run}]
    assert store.db.execute('SELECT COUNT(*) FROM evidence').fetchone()[0]==2


def test_two_runs_preserve_different_source_text(store):
    a=store.create_run('one',100); b=store.create_run('two',100)
    publish(store,claimed(store,a),evidence=[E])
    publish(store,claimed(store,b),evidence=[{**E,'text':'changed text'}])
    assert store.evidence(a)[0]['text']=='exact source text'
    assert store.evidence(b)[0]['text']=='changed text'


def test_same_run_identical_evidence_is_idempotent(store):
    run=store.create_run('one',100)
    assert publish(store,claimed(store,run,'a'),evidence=[E])
    assert publish(store,claimed(store,run,'b'),evidence=[E,E])
    assert len(store.evidence(run))==1


@pytest.mark.parametrize('field',['source_id','title','url','text','same_batch'])
def test_same_run_conflict_rolls_back_batch(store,field):
    from app.hive.store import EvidenceIntegrityError
    run=store.create_run('one',100)
    publish(store,claimed(store,run,'a'),evidence=[E])
    task=claimed(store,run,'b')
    fresh={**E,'id':'E-new'}
    incoming=[fresh,{**E,field:'changed'}] if field!='same_batch' else [fresh,{**fresh,'text':'conflict'}]
    with pytest.raises(EvidenceIntegrityError):
        publish(store,task,evidence=incoming,facts=[{'id':'F-new','claim':'new','evidence_id':'E-new'}])
    assert store.evidence(run)==[{**E,'run_id':run}]
    assert store.facts(run)==[]
    assert store.get_task(task['id'])['status']=='claimed' and store.get_task(task['id'])['result'] is None


@pytest.mark.parametrize('ref',['E-missing',None,'','E-foreign'])
def test_missing_or_foreign_fact_evidence_rolls_back_batch(store,ref):
    from app.hive.store import EvidenceIntegrityError
    foreign=store.create_run('foreign',100)
    publish(store,claimed(store,foreign),evidence=[{**E,'id':'E-foreign'}])
    run=store.create_run('own',100); task=claimed(store,run)
    with pytest.raises(EvidenceIntegrityError):
        publish(store,task,evidence=[E],facts=[{'id':'F-valid','claim':'valid','evidence_id':E['id']},
                                              {'id':'F-bad','claim':'invalid','evidence_id':ref}])
    assert store.evidence(run)==[] and store.facts(run)==[]
    assert store.get_task(task['id'])['status']=='claimed'
    assert store.get_task(task['id'])['result'] is None


def test_fact_evidence_may_be_existing_or_same_batch(store):
    run=store.create_run('own',100)
    publish(store,claimed(store,run,'first'),evidence=[E])
    task=claimed(store,run,'second')
    assert publish(store,task,evidence=[{**E,'id':'E-new'}],facts=[
        {'id':'F-old','claim':'old','evidence_id':E['id']},
        {'id':'F-new','claim':'new','evidence_id':'E-new'}])
    assert len(store.facts(run))==2 and store.get_task(task['id'])['result']=={'accepted':True}


def test_stale_publication_writes_no_provenance(store):
    run=store.create_run('own',100); old=claimed(store,run)
    store.expire_leases(run,now=102)
    new=store.claim(run,'worker',lease_s=100,now=103)
    assert not store.publish(old['id'],'worker',old['attempt'],old['fence'],{},[E],
                             [{'id':'F-stale','claim':'bad','evidence_id':'E-same'}],now=104)
    assert store.evidence(run)==[] and store.facts(run)==[]
    assert store.publish(new['id'],'worker',new['attempt'],new['fence'],{'ok':True},[E],
                         [{'id':'F-new','claim':'good','evidence_id':'E-same'}],now=104)
    assert len(store.evidence(run))==len(store.facts(run))==1


def migrated(tmp_path):
    from app.hive.migrate import upgrade_hive_database
    path=legacy_database(tmp_path/'old.db')
    upgrade_hive_database(str(path),str(tmp_path/'backup.db'))
    return HiveStore(str(path))


def test_legacy_verified_fact_without_evidence_is_ineligible(tmp_path):
    s=migrated(tmp_path)
    try:
        assert {f['id'] for f in s.facts('old')}=={'F-good','F-bad'}
        assert [f['id'] for f in s.facts('old','verified')]==['F-good']
        assert s.get_run('old')['report']=='historical report'
        assert s.evidence('old','E-foreign')==[]
    finally: s.db.close()


async def test_writer_never_receives_missing_provenance_fact(tmp_path):
    from app.hive.agents import run_writer
    s=migrated(tmp_path)
    seen=[]
    async def call(layer,agent,system,user,max_tokens):
        seen.append(user)
        return '## Findings\nSupported [F-12345678].'
    try:
        await run_writer(s,'old','objective',call)
        assert len(seen)==1 and 'orphan' not in seen[0] and 'valid' in seen[0]
        s.db.execute("DELETE FROM evidence WHERE run_id='old'")
        report,gate=await run_writer(s,'old','objective',call)
        assert report=='' and gate=={'passed':False,'reason':'no verified facts'}
        assert len(seen)==1 and s.get_run('old')['report']=='historical report'
    finally: s.db.close()


def test_verified_promotion_with_missing_evidence_rolls_back(tmp_path):
    from app.hive.store import EvidenceIntegrityError
    s=migrated(tmp_path)
    try:
        s.db.execute("UPDATE facts SET status='proposed'")
        task=claimed(s,'old','verify')
        with pytest.raises(EvidenceIntegrityError):
            s.set_fact_status(task['id'],'worker',task['attempt'],task['fence'],
                              {'F-good':('verified','new'),'F-bad':('verified','new')},{},now=2)
        assert all(f['status']=='proposed' and f['note']=='unchanged' for f in s.facts('old'))
        assert s.get_task(task['id'])['result'] is None
        assert not s.set_fact_status(task['id'],'worker',999,999,{'F-bad':('verified','')},{},now=2)
    finally: s.db.close()
