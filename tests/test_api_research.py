"""
Integration tests for Research API.
"""
import pytest
from fastapi.testclient import TestClient
import tempfile
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

# Set test environment before imports
os.environ["SQLITE_PATH"] = str(Path(tempfile.mkdtemp()) / "test.db")
os.environ["CHROMA_DIR"] = tempfile.mkdtemp()

from app.main import app


@pytest.fixture(autouse=True)
def stub_pipeline(monkeypatch):
    """Keep API tests offline: replace the full LangGraph run with a stub."""
    async def fake_run_research(*args, **kwargs):
        return {"status": "completed", "final_report": "stub", "sources": [], "errors": []}
    monkeypatch.setattr("app.api.routes_research.run_research", fake_run_research)


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Isolate both stores even when settings were imported before this module."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.db.models import Base
    from app.db.sqlite import get_db
    from app.api import routes_hive
    from app.hive.store import HiveStore
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    def db_override():
        with sessions() as session:
            yield session
    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = db_override
    store = HiveStore(str(tmp_path / 'hive.db'))
    monkeypatch.setattr(routes_hive, '_store', store)
    try:
        yield TestClient(app)
    finally:
        if previous is None: app.dependency_overrides.pop(get_db, None)
        else: app.dependency_overrides[get_db] = previous
        store.db.close()
        engine.dispose()


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_root(self, client):
        """Test root endpoint."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Hive Lite"
        assert data["status"] == "running"
    
    def test_health(self, client):
        """Test health endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "components" in data


class TestResearchAPI:
    """Test research endpoints."""
    
    def test_create_research_run(self, client):
        """Test creating a research run."""
        response = client.post(
            "/v1/research",
            json={
                "topic": "Transformer attention mechanisms",
                "depth": "quick",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "run_id" in data
        assert data["status"] == "pending"
    
    def test_create_research_with_constraints(self, client):
        """Test creating research with constraints."""
        response = client.post(
            "/v1/research",
            json={
                "topic": "Neural network optimization",
                "constraints": "Focus on papers from 2023",
                "depth": "normal",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "run_id" in data
    
    def test_create_research_validation(self, client):
        """Test validation of research request."""
        # Topic too short
        response = client.post(
            "/v1/research",
            json={"topic": "ab", "depth": "quick"}
        )
        
        assert response.status_code == 422
    
    def test_list_runs(self, client):
        """Test listing runs."""
        # Create a run first
        client.post("/v1/research", json={"topic": "Test topic", "depth": "quick"})
        
        response = client.get("/v1/runs")
        
        assert response.status_code == 200
        data = response.json()
        assert "runs" in data
        assert "total" in data


class TestRunStatus:
    """Test run status endpoints."""
    
    def test_get_run_not_found(self, client):
        """Test getting non-existent run."""
        response = client.get("/v1/runs/nonexistent-id")
        
        assert response.status_code == 404
    
    def test_get_run_after_create(self, client):
        """Test getting run after creation."""
        # Create run
        create_response = client.post(
            "/v1/research",
            json={"topic": "Machine learning basics", "depth": "quick"}
        )
        run_id = create_response.json()["run_id"]
        
        # Get run
        response = client.get(f"/v1/runs/{run_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == run_id
        assert data["objective"] == "Machine learning basics"


class TestFeedbackAPI:
    """Test feedback endpoints."""
    
    def test_submit_feedback(self, client):
        """Test submitting feedback."""
        # Create run first
        create_response = client.post(
            "/v1/research",
            json={"topic": "Test for feedback", "depth": "quick"}
        )
        run_id = create_response.json()["run_id"]
        
        # Submit feedback
        response = client.post(
            "/v1/feedback",
            json={
                "run_id": run_id,
                "rating": 4,
                "comment": "Good results!",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["rating"] == 4
    
    def test_submit_feedback_invalid_rating(self, client):
        """Test submitting feedback with invalid rating."""
        response = client.post(
            "/v1/feedback",
            json={
                "run_id": "some-id",
                "rating": 6,  # Invalid: must be 1-5
            }
        )
        
        assert response.status_code == 422
    
    def test_submit_feedback_run_not_found(self, client):
        """Test submitting feedback for non-existent run."""
        response = client.post(
            "/v1/feedback",
            json={
                "run_id": "nonexistent-id",
                "rating": 3,
            }
        )
        
        assert response.status_code == 404


class TestExportAPI:
    """Test export endpoints."""
    
    def test_export_not_found(self, client):
        """Test exporting non-existent run."""
        response = client.get("/v1/runs/nonexistent/export?format=markdown")
        
        assert response.status_code == 404
    
    def test_export_invalid_format(self, client):
        """Test exporting with invalid format."""
        # Create run
        create_response = client.post(
            "/v1/research",
            json={"topic": "Export test", "depth": "quick"}
        )
        run_id = create_response.json()["run_id"]
        
        response = client.get(f"/v1/runs/{run_id}/export?format=invalid")
        
        # FastAPI rejects values outside the Literal with 422 before the handler's own 400
        assert response.status_code in (400, 422)


class TestHiveAPI:
    def test_hive_run_end_to_end_with_mock_provider(self, client, monkeypatch):
        import json, re
        from app.llm import LLMConfig, LLMRouter, ModelSpec, set_router
        import app.hive.agents as agents

        async def fake_search(q, n):
            return [{"id": "s1", "title": "Paper", "url": "http://x/s1",
                     "abstract": "Graph memory reduces redundant retrieval calls in agent systems."}]
        monkeypatch.setattr(agents, "default_search", fake_search)

        def handler(spec, messages):
            sysm, user = messages[0]["content"], messages[-1]["content"]
            if "Knull" in sysm:
                return json.dumps({"subtasks": [{"title": "t", "query": "graph memory"}]})
            if "research symbiote" in sysm:
                eid = re.findall(r"\[(E-[0-9a-f]{8})\]", user)[0]
                return json.dumps({"claims": [{"claim": "Graph memory cuts retrieval calls.", "evidence_id": eid,
                                               "quote": "reduces redundant retrieval calls"}]})
            if "verifier" in sysm:
                return json.dumps({"verdict": "supported", "note": ""})
            return json.dumps({"fact_ids": [fact["id"] for fact in json.loads(user)["candidates"]]})
        m = ModelSpec(provider="mock", model="m")
        set_router(LLMRouter(LLMConfig(default=m), mock_handler=handler))
        try:
            r = client.post("/v1/hive/runs", json={"objective": "Graph memory for agents"})
            assert r.status_code == 202
            body = client.get(f"/v1/hive/runs/{r.json()['run_id']}").json()  # TestClient runs bg tasks inline
            assert body["status"] == "done" and "Graph memory cuts" in body["report"]
            assert body["facts"][0]["status"] == "verified"
        finally:
            set_router(None)

    def test_hive_not_found(self, client):
        assert client.get("/v1/hive/runs/nope").status_code == 404


class TestHiveEvidenceCompatibility:
    def test_historical_report_read_is_unchanged(self,client):
        from app.api import routes_hive
        store=routes_hive.get_store()
        historical_report='# Legacy report\r\n\r\n**Original** café [F-old].\n\n## Sources\n- <raw historical markup>\n'
        historical_gate={'passed':True,'sentences':1,'removed_uncited_or_unverified':[]}
        run_id=store.create_run('Historical report',1000)
        store.finish_run(run_id,'done_with_removals',historical_report,historical_gate)
        response=client.get('/v1/hive/runs/'+run_id)
        assert response.status_code==200
        body=response.json()
        assert body['report']==historical_report
        assert body['status']=='done_with_removals'
        assert 'gate' not in body
        import json
        assert json.loads(store.get_run(run_id)['gate'])==historical_gate

    @pytest.mark.parametrize('empty_selection',[False,True],ids=['accepted-findings','no-findings'])
    def test_generated_report_preserves_surface_and_stored_provenance(self,client,monkeypatch,empty_selection):
        import hashlib
        import json
        from app.api import routes_hive
        from app.hive import agents
        from app.llm import LLMRouter,set_router
        from tests.test_hive import routed_config,make_handler,fake_search
        base=make_handler()
        def handler(spec,messages):
            if empty_selection and 'writer symbiote' in messages[0]['content']:
                return '{"fact_ids":[]}'
            return base(spec,messages)
        monkeypatch.setattr(agents,'default_search',fake_search)
        set_router(LLMRouter(routed_config(),mock_handler=handler))
        try:
            created=client.post('/v1/hive/runs',json={'objective':'Supported report compatibility','subtasks':1,'workers':1})
            assert created.status_code==202
            assert set(created.json())=={'run_id','status'}
            run_id=created.json()['run_id']
            response=client.get('/v1/hive/runs/'+run_id)
            assert response.status_code==200
            body=response.json()
            assert set(body)=={'run_id','objective','status','report','spent_tokens','budget_tokens','tasks','facts','usage_by_route','events'}
            store=routes_hive.get_store()
            gate=json.loads(store.get_run(run_id)['gate'])
            writer=next(t for t in store.tasks(run_id) if t['kind']=='write')
            assert writer['result']=={'report':body['report'],'gate':gate}
            assert gate['policy_version']=='accepted-claims-v1'
            assert sum(f['status']=='verified' for f in body['facts'])==2
            assert all(f['status']!='rejected' for f in body['facts'])
            if empty_selection:
                assert body['status']=='blocked' and body['report']==''
                assert gate['passed'] is False and gate['finding_count']==0
                assert gate['reason']=='no_selected_findings'
                assert gate['selected_fact_ids']==gate['provenance']==[]
            else:
                assert body['status']=='done' and gate['passed'] is True
                assert gate['finding_count']==gate['sentences']==2
                assert gate['removed_uncited_or_unverified']==[]
                assert gate['selected_fact_ids']==[p['fact_id'] for p in gate['provenance']]
                for p in gate['provenance']:
                    fact=next(f for f in body['facts'] if f['id']==p['fact_id'])
                    evidence=store.evidence(run_id,p['evidence_id'])[0]
                    assert p['claim']==fact['claim']
                    assert p['source_id']==evidence['source_id']
                    assert p['claim_sha256']==hashlib.sha256(fact['claim'].encode()).hexdigest()
                    assert p['evidence_sha256']==hashlib.sha256(evidence['text'].encode()).hexdigest()
                    assert f'[{fact["id"]}]' in body['report'] and evidence['url'] in body['report']
        finally:set_router(None)

    def test_repeated_source_runs_preserve_contract(self,client,monkeypatch,tmp_path):
        from app.api import routes_hive
        from app.hive import agents
        from app.hive.store import HiveStore
        from app.llm import LLMRouter,set_router
        from tests.test_hive import routed_config,make_handler,fake_search
        store=HiveStore(str(tmp_path/'api-hive.db'))
        monkeypatch.setattr(routes_hive,'_store',store)
        monkeypatch.setattr(agents,'default_search',fake_search)
        set_router(LLMRouter(routed_config(),mock_handler=make_handler()))
        ids=[]
        try:
            for _ in range(2):
                response=client.post('/v1/hive/runs',json={'objective':'Repeated public source research','subtasks':1})
                assert response.status_code==202 and response.json()['status']=='running'
                run_id=response.json()['run_id'];ids.append(run_id)
                body=client.get('/v1/hive/runs/'+run_id).json()
                assert body['status']=='done' and '[F-' in body['report']
                assert sum(f['status']=='verified' for f in body['facts'])==2
                assert {'run_id','objective','status','report','spent_tokens','budget_tokens','tasks','facts','usage_by_route','events'} <= body.keys()
            assert ids[0]!=ids[1]
        finally:
            set_router(None);store.db.close()


@pytest.mark.parametrize('field',['task_timeout_s','run_timeout_s'])
def test_hive_deadline_validation_before_submission(client,monkeypatch,field):
    from app.api import routes_hive
    called=[]
    async def no_execution(*args,**kwargs):called.append(kwargs)
    monkeypatch.setattr(routes_hive,'run_hive',no_execution)
    response=client.post('/v1/hive/runs',json={'objective':'Deadline validation',field:0})
    assert response.status_code==422
    assert called==[] and routes_hive.get_store().db.execute('SELECT COUNT(*) FROM runs').fetchone()[0]==0


def test_hive_deadlines_forwarded_to_runner(client,monkeypatch):
    from app.api import routes_hive
    called=[]
    async def execute(*args,**kwargs):called.append(kwargs)
    monkeypatch.setattr(routes_hive,'run_hive',execute)
    response=client.post('/v1/hive/runs',json={'objective':'Deadline forwarding','task_timeout_s':12,'run_timeout_s':34})
    assert response.status_code==202
    assert called[0]['task_timeout_s']==12 and called[0]['run_timeout_s']==34
