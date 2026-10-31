"""Attempt ownership and finite dependency progress on real SQLite."""
import asyncio
import sqlite3
from concurrent.futures import ThreadPoolExecutor
import threading

import pytest

from app.hive.store import HiveStore

@pytest.fixture
def store(tmp_path):
    s=HiveStore(str(tmp_path/'execution.db'))
    yield s
    s.db.close()


def setup_task(store):
    run=store.create_run('objective',1000)
    tid=store.add_task(run,'work','research','work',{})
    a=store.claim(run,'same-worker',lease_s=10,now=100)
    return run,tid,a


@pytest.mark.parametrize('action',['release','exhaust','heartbeat','publish'])
def test_old_attempt_cannot_mutate_replacement_or_completion(store,action):
    run,tid,a=setup_task(store)
    store.expire_leases(run,now=111)
    b=store.claim(run,'same-worker',lease_s=20,now=112)
    def stale():
        args=(tid,'same-worker',a['attempt'],a['fence'])
        if action=='release':return store.release(*args,'late failure',now=113)
        if action=='exhaust':return store.mark_exhausted(tid,'late failure',worker='same-worker',attempt=a['attempt'],fence=a['fence'],now=113)
        if action=='heartbeat':return store.heartbeat(*args,lease_s=100,now=113)
        return store.publish(*args,{'stale':True},now=113)
    before=store.get_task(tid)
    assert stale() is False and store.get_task(tid)==before
    assert store.publish(tid,'same-worker',b['attempt'],b['fence'],{'accepted':True},now=114)
    before=store.get_task(tid)
    assert stale() is False and store.get_task(tid)==before


@pytest.mark.parametrize('action',['release','exhaust','heartbeat'])
def test_expired_owner_cannot_mutate_without_reclaim(store,action):
    run,tid,a=setup_task(store)
    if action=='release':ok=store.release(tid,'same-worker',a['attempt'],a['fence'],'late',now=110)
    elif action=='exhaust':ok=store.mark_exhausted(tid,'late',worker='same-worker',attempt=a['attempt'],fence=a['fence'],now=110)
    else:ok=store.heartbeat(tid,'same-worker',a['attempt'],a['fence'],now=110)
    assert ok is False and store.get_task(tid)['status']=='claimed'


def test_separate_handle_renewal_expiry_and_competing_claims(store):
    run,tid,a=setup_task(store)
    other=HiveStore(store.path)
    try:
        assert other.heartbeat(tid,'same-worker',a['attempt'],a['fence'],lease_s=20,now=109)
        assert store.expire_leases(run,now=111)==[]
        assert other.publish(tid,'same-worker',a['attempt'],a['fence'],{'good':True},now=112)
        assert store.expire_leases(run,now=150)==[]
        second=store.add_task(run,'new','research','new',{})
        barrier=threading.Barrier(2)
        def claim(s,w):barrier.wait(timeout=3);return s.claim(run,w,now=200)
        with ThreadPoolExecutor(2) as pool:
            results=[f.result(timeout=5) for f in [pool.submit(claim,store,'a'),pool.submit(claim,other,'b')]]
        assert sum(r is not None for r in results)==1
        assert next(r for r in results if r)['id']==second
    finally:other.db.close()


def test_failed_dependency_blocks_descendants_but_preserves_independent_branch(store):
    run,tid,a=setup_task(store)
    child=store.add_task(run,'child','verify','verify',{},[tid])
    grandchild=store.add_task(run,'grandchild','write','write',{},[child])
    independent=store.add_task(run,'other','research','other',{})
    assert store.mark_exhausted(tid,'permanent failure',worker='same-worker',attempt=a['attempt'],fence=a['fence'],now=101)
    store.block_unsatisfied(run)
    assert store.get_task(child)['status']==store.get_task(grandchild)['status']=='blocked'
    assert store.get_task(child)['result']['prerequisites']==[tid]
    task=store.claim(run,'other',now=102)
    assert task['id']==independent
    assert store.publish(independent,'other',task['attempt'],task['fence'],{},now=103)
    assert store.open_tasks(run)==0


@pytest.mark.parametrize('damage',['missing','cross_run','cycle','unknown_kind'])
def test_invalid_dependency_graph_rejected_before_execution(store,damage):
    run,tid,a=setup_task(store)
    child=store.add_task(run,'child','verify','child',{},[tid])
    if damage=='missing':store.db.execute("UPDATE tasks SET deps='[\"missing\"]' WHERE id=?",(tid,))
    elif damage=='cross_run':
        other=store.create_run('other',100)
        foreign=store.add_task(other,'x','research','foreign',{})
        import json
        store.db.execute('UPDATE tasks SET deps=? WHERE id=?',(json.dumps([foreign]),tid))
    elif damage=='cycle':
        import json
        store.db.execute('UPDATE tasks SET deps=? WHERE id=?',(json.dumps([child]),tid))
    else:store.db.execute("UPDATE tasks SET kind='arbitrary' WHERE id=?",(tid,))
    with pytest.raises(ValueError):store.validate_graph(run)


def test_no_progress_blocking_is_transactional_and_causal(store):
    run=store.create_run('x',100)
    tid=store.add_task(run,'x','research','x',{})
    store.db.execute("UPDATE tasks SET deps='[\"absent\"]' WHERE id=?",(tid,))
    store.block_unsatisfied(run)
    assert store.get_task(tid)['status']=='blocked'
    assert store.get_task(tid)['result']['prerequisites']==['absent']
    assert store.open_tasks(run)==0


@pytest.fixture
def mock_router():
    from app.llm import LLMRouter,set_router
    from tests.test_hive import routed_config,make_handler
    set_router(LLMRouter(routed_config(),mock_handler=make_handler()))
    yield
    set_router(None)


async def test_permanent_tool_outage_terminates_with_causal_blocking(store,mock_router):
    from app.hive import run_hive
    calls=0
    async def down(q,n):
        nonlocal calls
        calls+=1
        raise OSError('tool unavailable')
    result=await asyncio.wait_for(run_hive('objective',store,search=down,max_subtasks=1,max_attempts=2,tick_s=.005),2)
    assert result.status=='blocked' and calls==2
    tasks=store.tasks(result.run_id)
    assert {t['status'] for t in tasks}=={'exhausted','blocked'}
    assert all(t['result']['prerequisites'] for t in tasks if t['status']=='blocked')


async def test_long_running_task_renews_without_duplicate_attempt(store,mock_router,monkeypatch):
    from app.hive import run_hive
    from tests.test_hive import SRC
    renewed=asyncio.Event();count=0;original=store.heartbeat
    def heartbeat(*args,**kwargs):
        nonlocal count
        accepted=original(*args,**kwargs)
        if accepted:
            count+=1
            if count==8:renewed.set()
        return accepted
    monkeypatch.setattr(store,'heartbeat',heartbeat)
    async def search(q,n):await renewed.wait();return SRC
    result=await asyncio.wait_for(run_hive('objective',store,search=search,max_subtasks=1,workers=1,
                                          lease_s=.12,heartbeat_s=.02,tick_s=.005),2)
    assert result.status=='done' and count>=8
    assert all(t['attempt']==1 for t in store.tasks(result.run_id))


async def test_task_deadline_stops_hung_search_and_blocks_descendants(store,mock_router):
    from app.hive import run_hive
    cancelled=asyncio.Event()
    async def search(q,n):
        try:await asyncio.Event().wait()
        finally:cancelled.set()
    result=await asyncio.wait_for(run_hive('objective',store,search=search,max_subtasks=1,workers=1,
                                          task_timeout_s=.03,run_timeout_s=.5,max_attempts=2,tick_s=.005),1)
    assert result.status=='blocked' and cancelled.is_set()
    assert store.open_tasks(result.run_id)==0
    assert any(t['result'].get('code')=='task_timeout' for t in store.tasks(result.run_id))


async def test_run_deadline_includes_planning_and_records_stop(store,mock_router,monkeypatch):
    from app.hive import run_hive,agents
    async def plan(*args):await asyncio.Event().wait()
    monkeypatch.setattr(agents,'knull_plan',plan)
    result=await asyncio.wait_for(run_hive('objective',store,run_timeout_s=.03),.5)
    assert result.status=='stopped' and result.gate['code']=='run_timeout'


async def test_cancellation_cleans_workers_watchdog_and_assignments(store,mock_router):
    from app.hive import run_hive
    started=asyncio.Event()
    async def search(q,n):started.set();await asyncio.Event().wait()
    before=set(asyncio.all_tasks())
    task=asyncio.create_task(run_hive('objective',store,search=search,max_subtasks=1,tick_s=.005))
    try:
        await asyncio.wait_for(started.wait(),1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):await task
        await asyncio.sleep(0)
        assert not [t for t in asyncio.all_tasks()-before if not t.done()]
        run=store.db.execute('SELECT id,status,gate FROM runs').fetchone()
        assert run['status']=='stopped' and 'cancelled' in run['gate']
        assert store.open_tasks(run['id'])==0
        assert not any(t['status']=='claimed' for t in store.tasks(run['id']))
    finally:
        task.cancel()
        leftovers=[t for t in asyncio.all_tasks()-before if not t.done()]
        for t in leftovers:t.cancel()
        await asyncio.gather(*leftovers,return_exceptions=True)


async def test_watchdog_failure_supervises_all_workers(store,mock_router,monkeypatch):
    from app.hive import run_hive
    def broken(*args,**kwargs):raise RuntimeError('database unavailable')
    monkeypatch.setattr(store,'expire_leases',broken)
    async def search(q,n):await asyncio.Event().wait()
    with pytest.raises(RuntimeError,match='database unavailable'):
        await asyncio.wait_for(run_hive('objective',store,search=search,max_subtasks=1,tick_s=.005),.5)
    run=store.db.execute('SELECT id,status FROM runs').fetchone()
    assert run['status']=='failed' and store.open_tasks(run['id'])==0


@pytest.mark.parametrize('options',[
    {'workers':0},{'workers':9},{'max_subtasks':0},{'budget_tokens':0},{'max_attempts':0},
    {'lease_s':0},{'lease_s':float('nan')},{'tick_s':0},{'task_timeout_s':0},
    {'run_timeout_s':float('inf')},{'lease_s':1,'heartbeat_s':1},
])
async def test_invalid_limits_rejected_before_run_creation(store,options,mock_router):
    from app.hive import run_hive
    with pytest.raises(ValueError):await asyncio.wait_for(run_hive('objective',store,**options),.2)
    assert store.db.execute('SELECT COUNT(*) FROM runs').fetchone()[0]==0


@pytest.mark.parametrize('bad_response',['outage','malformed'])
async def test_verifier_execution_failure_does_not_reject_facts(store,bad_response):
    from app.hive import run_hive
    from app.llm import LLMError,LLMRouter,set_router
    from tests.test_hive import routed_config,make_handler,fake_search
    original=make_handler();calls=0
    def handler(spec,messages):
        nonlocal calls
        if 'verifier' in messages[0]['content']:
            calls+=1
            if bad_response=='outage':raise LLMError('temporary outage')
            return '{"verdict":"unrecognized"}'
        return original(spec,messages)
    set_router(LLMRouter(routed_config(),mock_handler=handler))
    try:
        result=await asyncio.wait_for(run_hive('objective',store,search=fake_search,max_subtasks=1,max_attempts=2,tick_s=.005),2)
        assert result.status=='blocked' and result.facts_rejected==0
        assert len(store.facts(result.run_id,'proposed'))==2
        assert calls==(2 if bad_response=='outage' else 1)
    finally:set_router(None)


async def test_caller_rechecks_lease_before_each_model_call(store):
    from app.hive.agents import Caller
    from app.hive.watchdog import BudgetGovernor
    from app.llm import LLMRouter,set_router
    from tests.test_hive import routed_config
    run,tid,a=setup_task(store);calls=0
    def handler(*args):
        nonlocal calls
        calls+=1
        return '{}'
    def guard():
        if not store.owns(tid,'same-worker',a['attempt'],a['fence'],now=101):raise RuntimeError('lease lost')
    set_router(LLMRouter(routed_config(),mock_handler=handler))
    try:
        call=Caller(store,run,BudgetGovernor(store,run,1000),before_call=guard)
        await call('workers','researcher','system','input')
        store.expire_leases(run,now=111)
        with pytest.raises(RuntimeError,match='lease lost'):await call('workers','researcher','system','second')
        assert calls==1
    finally:set_router(None)


async def test_zero_retry_router_failure_has_no_post_failure_backoff():
    from app.llm import LLMError,LLMRouter
    from tests.test_hive import routed_config
    def down(*args):raise LLMError('temporary outage')
    router=LLMRouter(routed_config(),mock_handler=down)
    with pytest.raises(LLMError):
        await asyncio.wait_for(router.complete([{'role':'user','content':'x'}],retries=0),.1)


def test_expiry_transaction_excludes_concurrent_renewal(tmp_path):
    """Losing renewal cannot slip between expiry's observed fence and transition."""
    path=str(tmp_path/'race.db');s=HiveStore(path);run,tid,a=setup_task(s)
    other=HiveStore(path);other.db.execute('PRAGMA busy_timeout=0')
    selected=threading.Event();proceed=threading.Event()
    def trace(sql):
        if sql.startswith('SELECT id,attempt,fence,lease_expires FROM tasks'):
            selected.set()
            assert proceed.wait(3)
    s.db.set_trace_callback(trace)
    try:
        with ThreadPoolExecutor(1) as pool:
            expiry=pool.submit(s.expire_leases,run,3,111)
            try:
                assert selected.wait(3)
                with pytest.raises(sqlite3.OperationalError,match='locked'):
                    other.heartbeat(tid,'same-worker',a['attempt'],a['fence'],lease_s=30,now=109)
            finally:proceed.set()
            assert expiry.result(timeout=3)==[{'task':tid,'action':'requeued'}]
        assert not other.heartbeat(tid,'same-worker',a['attempt'],a['fence'],now=112)
        replacement=other.claim(run,'same-worker',now=113)
        assert replacement['attempt']==2 and replacement['fence']==2
    finally:
        proceed.set();s.db.close();other.db.close()


async def test_default_search_outage_retries_and_records_execution_failure(store,mock_router,monkeypatch):
    import app.tools as tools
    from app.hive import run_hive
    calls=[]
    async def unavailable(*args,**kwargs):calls.append(1);raise OSError('backend unavailable')
    for name in ('search_arxiv','search_semantic_scholar','search_wikipedia'):
        monkeypatch.setattr(tools,name,unavailable)
    result=await asyncio.wait_for(run_hive('objective',store,workers=1,max_subtasks=1,max_attempts=2,tick_s=.005),1)
    assert result.status=='blocked'
    assert len(calls)==6
    research=next(t for t in store.tasks(result.run_id) if t['kind']=='research')
    assert research['status']=='exhausted' and research['attempt']==2
    assert sum(e['kind']=='task_error' for e in result.events)==2


@pytest.mark.parametrize('tool',['arxiv','semantic_scholar','wikipedia'])
async def test_strict_search_adapters_preserve_errors_and_legacy_empty_contract(monkeypatch,tool):
    import importlib
    module=importlib.import_module('app.tools.'+tool)
    if tool=='arxiv':
        class BrokenClient:
            def results(self,*args,**kwargs):raise OSError('unavailable')
        monkeypatch.setattr(module.arxiv,'Client',BrokenClient)
    else:
        class BrokenClient:
            def __init__(self,*args,**kwargs):pass
            async def __aenter__(self):return self
            async def __aexit__(self,*args):pass
            async def get(self,*args,**kwargs):raise OSError('unavailable')
        monkeypatch.setattr(module.httpx,'AsyncClient',BrokenClient)
        if tool=='semantic_scholar':
            async def no_rate_limit():pass
            monkeypatch.setattr(module,'_rate_limit',no_rate_limit)
    search=getattr(module,'search_'+tool)
    assert await search('query')==[]
    with pytest.raises(OSError):await search('query',raise_on_error=True)


async def test_arxiv_fetch_does_not_block_event_loop(monkeypatch):
    import importlib,time
    module=importlib.import_module('app.tools.arxiv')
    entered=threading.Event();release=threading.Event();order=[]
    class Client:
        def results(self,*args):
            entered.set();order.append('fetch-start')
            release.wait(.15)
            order.append('fetch-end')
            return iter([])
    monkeypatch.setattr(module.arxiv,'Client',Client)
    async def tick():
        # Runs promptly only if sync retrieval is outside the event loop.
        while not entered.is_set():await asyncio.sleep(0)
        order.append('tick');release.set()
    await asyncio.gather(module.search_arxiv('query'),tick())
    assert order==['fetch-start','tick','fetch-end']


@pytest.mark.parametrize('partial',[False,True])
async def test_default_search_preserves_empty_success_and_partial_sources(monkeypatch,partial):
    import app.tools as tools
    from app.hive.agents import default_search
    class Source:
        def to_dict(self):return {'id':'one','title':'source','abstract':'evidence'}
    async def arxiv(*args,**kwargs):
        if partial:raise OSError('one backend down')
        return []
    async def scholar(*args,**kwargs):return [Source()] if partial else []
    async def wiki(*args,**kwargs):return []
    monkeypatch.setattr(tools,'search_arxiv',arxiv)
    monkeypatch.setattr(tools,'search_semantic_scholar',scholar)
    monkeypatch.setattr(tools,'search_wikipedia',wiki)
    assert await default_search('query',3)==([{'id':'one','title':'source','abstract':'evidence'}] if partial else [])


async def test_lease_loss_cancels_execution_and_blocks_its_next_subcall(store,mock_router,monkeypatch):
    from app.hive import run_hive
    from tests.test_hive import SRC
    searches=0;cancelled=asyncio.Event();original=store.heartbeat;lost=False
    async def search(q,n):
        nonlocal searches
        searches+=1
        if searches==1:
            try:await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancelled.set()
                return SRC  # A late tool response must still fail the authority guard.
        assert cancelled.is_set()
        return SRC
    def heartbeat(tid,worker,attempt,fence,**kwargs):
        nonlocal lost
        if not lost:
            lost=True
            run=store.get_task(tid)['run_id']
            import time
            store.expire_leases(run,now=time.time()+1)
        return original(tid,worker,attempt,fence,**kwargs)
    monkeypatch.setattr(store,'heartbeat',heartbeat)
    result=await asyncio.wait_for(run_hive('objective',store,search=search,workers=1,max_subtasks=1,
                                          lease_s=.12,heartbeat_s=.02,tick_s=.005),1)
    assert result.status=='done' and searches==2 and cancelled.is_set()
    assert any(e['kind']=='lease_lost' for e in result.events)
    research=next(t for t in store.tasks(result.run_id) if t['kind']=='research')
    assert research['attempt']==2
    assert sum(u['calls'] for u in result.usage_by_route if u['agent']=='researcher')==1
