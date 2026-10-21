"""CLI compatibility using real runner/store and mock model/search boundary."""
import json
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
            summaries.append(summary)
        assert summaries[0]['run_id']!=summaries[1]['run_id']
        store=HiveStore(str(path))
        assert len(store.evidence(summaries[0]['run_id']))==len(store.evidence(summaries[1]['run_id']))==2
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
