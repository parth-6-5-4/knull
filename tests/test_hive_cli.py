"""CLI compatibility using real runner/store and mock model/search boundary."""
import json
import hashlib
import subprocess
import sys

from app.hive import agents, cli
from app.hive.store import HiveStore
from app.llm import LLMRouter, set_router
from tests.test_hive import make_handler, routed_config, fake_search


def test_cli_repeated_sources_preserve_output(tmp_path,monkeypatch,capsys):
    path=tmp_path/'cli.db'
    monkeypatch.setattr(agents,'default_search',fake_search)
    set_router(LLMRouter(routed_config(),mock_handler=make_handler()))
    summaries=[]
    try:
        for _ in range(2):
            monkeypatch.setattr(sys,'argv',['hive','research objective','--db',str(path),'--workers','1','--subtasks','1'])
            cli.main()
            output=capsys.readouterr().out
            assert '[F-' in output and '## Sources' in output
            summary=json.loads('{\n'+output.split('\n{\n',1)[1])
            assert summary['status']=='done' and summary['verified']==2
            assert summary['gate']['policy_version']=='accepted-claims-v1'
            assert summary['gate']['passed'] is True
            assert summary['gate']['finding_count']==2
            assert summary['gate']['sentences']==2
            assert set(summary)=={'run_id','status','spent_tokens','verified','rejected','gate','usage_by_route'}
            summaries.append(summary)
        assert summaries[0]['run_id']!=summaries[1]['run_id']
        store=HiveStore(str(path))
        assert len(store.evidence(summaries[0]['run_id']))==len(store.evidence(summaries[1]['run_id']))==2
        for summary in summaries:
            gate=json.loads(store.get_run(summary['run_id'])['gate'])
            assert {k:v for k,v in gate.items() if k!='removed_uncited_or_unverified'}==summary['gate']
            writer=next(t for t in store.tasks(summary['run_id']) if t['kind']=='write')
            assert writer['result']['gate']==gate
            assert gate['selected_fact_ids']==[p['fact_id'] for p in gate['provenance']]
            for provenance in gate['provenance']:
                fact=next(f for f in store.facts(summary['run_id']) if f['id']==provenance['fact_id'])
                evidence=store.evidence(summary['run_id'],fact['evidence_id'])[0]
                assert provenance['claim']==fact['claim']
                assert provenance['claim_sha256']==hashlib.sha256(fact['claim'].encode()).hexdigest()
                assert provenance['evidence_sha256']==hashlib.sha256(evidence['text'].encode()).hexdigest()
                assert provenance['source_id']==evidence['source_id']
                assert f'[{fact["id"]}]' in writer['result']['report']
                assert evidence['url'] in writer['result']['report']
        store.db.close()
    finally: set_router(None)


def test_cli_help_is_offline():
    result=subprocess.run([sys.executable,'-m','app.hive.cli','--help'],capture_output=True,text=True,timeout=10)
    assert result.returncode==0 and '--workers' in result.stdout and '--db' in result.stdout


def test_cli_deadline_options_control_actual_run(tmp_path,monkeypatch,capsys):
    path=tmp_path/'bounded.db'
    monkeypatch.setattr(agents,'default_search',fake_search)
    monkeypatch.setattr(sys,'argv',['hive','bounded objective','--db',str(path),'--workers','1',
                                     '--subtasks','1','--task-timeout','5','--run-timeout','10'])
    set_router(LLMRouter(routed_config(),mock_handler=make_handler()))
    try:
        cli.main()
        assert '"status": "done"' in capsys.readouterr().out
    finally:set_router(None)


def test_cli_empty_selection_is_blocked(tmp_path,monkeypatch,capsys):
    path=tmp_path/'empty.db'
    base=make_handler()
    def handler(spec,messages):
        if 'writer symbiote' in messages[0]['content']:
            return '{"fact_ids":[]}'
        return base(spec,messages)
    monkeypatch.setattr(agents,'default_search',fake_search)
    monkeypatch.setattr(sys,'argv',['hive','empty selection','--db',str(path),'--workers','1','--subtasks','1'])
    set_router(LLMRouter(routed_config(),mock_handler=handler))
    try:
        cli.main()
        output=capsys.readouterr().out
        assert output.startswith('(no report)\n')
        summary=json.loads(output.split('\n',1)[1])
        assert summary['status']=='blocked' and summary['verified']==2 and summary['rejected']==0
        assert summary['gate']['policy_version']=='accepted-claims-v1'
        assert summary['gate']['passed'] is False and summary['gate']['finding_count']==0
        assert summary['gate']['reason']=='no_selected_findings'
        assert summary['gate']['selected_fact_ids']==summary['gate']['provenance']==[]
        store=HiveStore(str(path))
        try:
            assert store.get_run(summary['run_id'])['report']==''
            writer=next(t for t in store.tasks(summary['run_id']) if t['kind']=='write')
            assert writer['result']['report']==''
            assert writer['result']['gate']['reason']=='no_selected_findings'
        finally:store.db.close()
    finally:set_router(None)
