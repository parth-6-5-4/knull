"""Conserved allowances and durable call transitions on real SQLite handles."""
from dataclasses import replace
import multiprocessing as mp
import sqlite3
import time
import pytest
from app.hive.store import HiveStore
from app.hive.resource_types import (MAX_INT64, CallAuthority, RunAuthority, ResourceInputError,
    ResourceConflict, ResourceDenied, ResourceBusy)
from tests.hive_resource_testkit import prepared_call, usage_receipt, attach_resource_run


def resources(hive):
    from app.hive.resource_store import ResourceStore
    return ResourceStore(hive)


@pytest.fixture
def ledger(tmp_path):
    hive=HiveStore(str(tmp_path/'resources.db')); run=hive.create_run('objective',100)
    store=resources(hive);store.create_root('root',run,100);attach_resource_run(hive,run)
    yield hive,store,run
    hive.db.close()


def reserve(store,run,**kwargs):
    p=prepared_call(run,**kwargs)
    return p,store.reserve(p,deadline_monotonic=time.monotonic()+3)


def dispatch(store,p):
    return store.mark_dispatched(p.call_id,p.authority,deadline_monotonic=time.monotonic()+3)


@pytest.mark.parametrize('invalid',[0,-1,True,1.5,MAX_INT64+1,'10',None])
def test_invalid_resource_values_are_atomic(ledger,invalid):
    hive,store,run=ledger
    with pytest.raises(ResourceInputError):store.allocate('root','child',invalid)
    assert store.inspect(run).available_tokens==100
    assert hive.db.execute('SELECT COUNT(*) FROM resource_allocations').fetchone()[0]==1
    with pytest.raises(ResourceInputError):store.create_root('',run,100)
    with pytest.raises(ResourceInputError):store.allocate('missing','child',10)


def test_nested_grants_conserve_authority(ledger):
    _,store,run=ledger
    store.allocate('root','child',60);store.allocate('child','leaf',20)
    assert store.inspect(run).available_tokens==40
    with pytest.raises(ResourceDenied):store.allocate('child','excess',41)
    store.close_allocation('leaf')
    p,_=reserve(store,run,allocation_id='child');dispatch(store,p);store.settle('call',usage_receipt())
    assert store.close_allocation('child').available_tokens==30
    assert store.inspect(run).available_tokens==70
    assert store.allocate('root','child',60).closed
    with pytest.raises(ResourceConflict):store.allocate('root','child',61)
    with pytest.raises(ResourceConflict):store.allocate('child','root',1)


def test_close_returns_only_unused_grant(ledger):
    _,store,run=ledger
    store.allocate('root','child',60)
    root_available_before_close=store.inspect(run).available_tokens
    p,_=reserve(store,run,allocation_id='child');dispatch(store,p);store.settle('call',usage_receipt())
    child_available_after_receipt=store.close_allocation('child').available_tokens
    root_available_after_child_close=store.inspect(run).available_tokens
    assert root_available_before_close==40
    assert child_available_after_receipt==30
    assert root_available_after_child_close==70
    assert store.close_allocation('child').closed
    with pytest.raises(ResourceDenied):reserve(store,run,allocation_id='child',call_id='later',authority=replace(p.authority,ordinal=2))


def test_call_transition_matrix(ledger):
    _,store,run=ledger
    p,record=reserve(store,run)
    assert record.state=='reserved' and record.permits_held
    with pytest.raises(ResourceConflict):store.settle('call',usage_receipt())
    assert dispatch(store,p) is True
    assert dispatch(store,p) is False
    with pytest.raises(ResourceConflict):store.release_reserved('call')
    store.mark_unknown('call')
    assert store.inspect(run).unknown_tokens==50
    done=store.settle('call',usage_receipt())
    assert done.state=='settled' and done.actual_tokens==30 and not done.permits_held
    store.mark_unknown('call')
    assert store.inspect(run).actual_tokens==30
    p,_=reserve(store,run,call_id='unsent',authority=replace(p.authority,ordinal=2))
    store.release_reserved('unsent');store.release_reserved('unsent')
    assert dispatch(store,p) is False
    with pytest.raises(ResourceConflict):store.mark_unknown('unsent')
    with pytest.raises(ResourceConflict):store.settle('unsent',usage_receipt(receipt_id='other'))


def test_overrun_freezes_root_and_siblings(ledger):
    _,store,run=ledger
    store.allocate('root','child',60);store.allocate('root','sibling',40)
    p,_=reserve(store,run,allocation_id='child');dispatch(store,p)
    store.settle('call',usage_receipt(80))
    assert store.close_allocation('child').debt_tokens==20
    assert store.inspect(run).frozen
    with pytest.raises(ResourceDenied):store.allocate('sibling','new',1)
    with pytest.raises(ResourceDenied):reserve(store,run,allocation_id='sibling',call_id='new')
    store.close_allocation('sibling')
    assert store.inspect(run).frozen and store.inspect(run).available_tokens==20


def test_resource_integer_overflow_is_atomic(tmp_path):
    hive=HiveStore(str(tmp_path/'overflow.db'));run=hive.create_run('o',MAX_INT64);store=resources(hive)
    try:
        store.create_root('root',run,MAX_INT64);attach_resource_run(hive,run)
        store.allocate('root','child',MAX_INT64)
        with pytest.raises(ResourceInputError):store.allocate('root','overflow',1)
        p,_=reserve(store,run,allocation_id='child');dispatch(store,p)
        second,_=reserve(store,run,allocation_id='child',call_id='next',bound_tokens=1,max_output_tokens=1,authority=replace(p.authority,ordinal=2));dispatch(store,second)
        store.settle('call',usage_receipt(MAX_INT64-1))
        with pytest.raises(ResourceInputError):store.settle('next',usage_receipt(2,receipt_id='next',receipt_digest='next'))
        assert store.inspect(run).actual_tokens==MAX_INT64-1
        assert store.inspect(run).reserved_tokens==1
        assert hive.db.execute('SELECT COUNT(*) FROM resource_usage_projection').fetchone()[0]==1
    finally:hive.db.close()


@pytest.mark.parametrize('field,value',[('request_fingerprint','changed'),('endpoint_id','other'),('provider','other'),('model','other'),('sdk_version','other'),('budget_mode','estimated'),('profile_digest','other'),('bound_tokens',51)])
def test_call_identity_binds_request_and_assignment(ledger,field,value):
    _,store,run=ledger;p,_=reserve(store,run)
    with pytest.raises(ResourceConflict):store.reserve(replace(p,**{field:value}),deadline_monotonic=time.monotonic()+3)
    with pytest.raises(ResourceConflict):store.reserve(replace(p,authority=replace(p.authority,ordinal=2)),deadline_monotonic=time.monotonic()+3)
    with pytest.raises(ResourceConflict):store.reserve(replace(p,call_id='different'),deadline_monotonic=time.monotonic()+3)
    with pytest.raises(ResourceConflict):store.mark_dispatched('call',replace(p.authority,run=RunAuthority(run,'other',2)),deadline_monotonic=time.monotonic()+3)
    assert store.inspect(run).reserved_tokens==50


def test_terminal_partial_receipt_releases_only_capacity(ledger):
    hive,store,run=ledger;p,_=reserve(store,run);dispatch(store,p)
    partial=usage_receipt(None,usage_complete=False,input_tokens=20,output_tokens=None,categories={'disjoint':{'input':20}})
    record=store.settle('call',partial)
    assert record.state=='unknown' and record.execution_terminal and not record.permits_held
    assert not record.usage_complete and record.actual_tokens==20
    info=store.inspect(run)
    assert (info.actual_tokens,info.reserved_tokens,info.unknown_tokens,info.available_tokens)==(0,0,50,50)
    assert info.occupancy['global_calls']==0
    assert hive.db.execute('SELECT COUNT(*) FROM ledger').fetchone()[0]==0
    assert 'input' in hive.db.execute("SELECT receipt_json FROM resource_calls").fetchone()[0]
    store.settle('call',usage_receipt(receipt_id='complete',receipt_digest='complete'))
    assert store.inspect(run).available_tokens==70


def test_partial_overrun_is_lower_bound_not_double_hold(ledger):
    _,store,run=ledger;p,_=reserve(store,run);dispatch(store,p)
    store.settle('call',usage_receipt(None,usage_complete=False,input_tokens=80,output_tokens=None))
    assert store.inspect(run).unknown_tokens==80 and store.inspect(run).available_tokens==20
    assert store.inspect(run).frozen
    store.settle('call',usage_receipt(30,receipt_id='complete',receipt_digest='complete'))
    assert store.inspect(run).frozen and store.inspect(run).available_tokens==70


def test_receipt_replay_is_idempotent(ledger):
    hive,store,run=ledger;p,_=reserve(store,run);dispatch(store,p)
    receipt=usage_receipt();first=store.settle('call',receipt)
    assert store.settle('call',receipt)==first
    for changed in (replace(receipt,total_tokens=31),replace(receipt,receipt_id='different'),replace(receipt,receipt_digest='different')):
        with pytest.raises(ResourceConflict):store.settle('call',changed)
    assert hive.db.execute('SELECT COUNT(*) FROM ledger').fetchone()[0]==1
    assert store.inspect(run).actual_tokens==30
    hive.finish_run(run,'stopped')
    assert store.settle('call',receipt)==first


def test_unknown_child_prevents_close(ledger):
    _,store,run=ledger;store.allocate('root','child',60)
    with pytest.raises(ResourceDenied):store.close_allocation('root')
    p,_=reserve(store,run,allocation_id='child');dispatch(store,p);store.mark_unknown('call',execution_terminal=True)
    with pytest.raises(ResourceDenied):store.close_allocation('child')
    assert store.inspect(run).unknown_tokens==50
    assert store.inspect(run).occupancy['global_calls']==0


def _grant_worker(path,run,child,pipe):
    hive=HiveStore(path);store=resources(hive)
    try:
        pipe.send('ready');pipe.recv()
        try:store.allocate('root',child,60);pipe.send('granted')
        except ResourceDenied:pipe.send('denied')
    finally:hive.db.close();pipe.close()


def test_competing_process_grants_cannot_overallocate(ledger):
    hive,store,run=ledger;ctx=mp.get_context('spawn');workers=[]
    try:
        for name in ('a','b'):
            parent,child=ctx.Pipe();process=ctx.Process(target=_grant_worker,args=(hive.path,run,name,child));process.start();child.close();workers.append((process,parent))
        for _,pipe in workers:assert pipe.poll(10) and pipe.recv()=='ready'
        for _,pipe in workers:pipe.send('go')
        results=[]
        for process,pipe in workers:
            assert pipe.poll(10);results.append(pipe.recv());process.join(5);assert process.exitcode==0
        assert sorted(results)==['denied','granted']
        assert store.inspect(run).available_tokens==40
    finally:
        for process,pipe in workers:
            if process.is_alive():process.kill();process.join(5)
            pipe.close()


def _race_worker(path,prepared,operation,pipe):
    # PreparedCall contains immutable mapping proxies: construct it in this process.
    hive=HiveStore(path);store=resources(hive);p=prepared_call(prepared)
    try:
        pipe.send('ready');pipe.recv()
        try:
            result=dispatch(store,p) if operation=='dispatch' else store.release_reserved('call')
            pipe.send('won' if result is not False else 'lost')
        except ResourceConflict:pipe.send('lost')
    finally:hive.db.close();pipe.close()


def test_release_dispatch_race_has_one_winner(ledger):
    hive,store,run=ledger;reserve(store,run);ctx=mp.get_context('spawn');workers=[]
    try:
        for op in ('dispatch','release'):
            parent,child=ctx.Pipe();process=ctx.Process(target=_race_worker,args=(hive.path,run,op,child));process.start();child.close();workers.append((process,parent))
        for _,pipe in workers:assert pipe.poll(10) and pipe.recv()=='ready'
        for _,pipe in workers:pipe.send('go')
        results=[]
        for process,pipe in workers:
            assert pipe.poll(10);results.append(pipe.recv());process.join(5);assert process.exitcode==0
        assert sorted(results)==['lost','won']
        assert store.inspect(run).available_tokens in (50,100)
    finally:
        for process,pipe in workers:
            if process.is_alive():process.kill();process.join(5)
            pipe.close()


def _dispatch_and_wait(path,run,pipe):
    hive=HiveStore(path);store=resources(hive);p=prepared_call(run)
    store.reserve(p,deadline_monotonic=time.monotonic()+3);dispatch(store,p)
    pipe.send('dispatched-committed');pipe.recv()


def test_crash_reopen_retains_dispatched_charge(ledger):
    hive,_,run=ledger;ctx=mp.get_context('spawn');parent,child=ctx.Pipe();process=ctx.Process(target=_dispatch_and_wait,args=(hive.path,run,child));process.start();child.close()
    try:assert parent.poll(10) and parent.recv()=='dispatched-committed'
    finally:
        process.terminate();process.join(5)
        if process.is_alive():process.kill();process.join(5)
        parent.close()
    reopened=HiveStore(hive.path)
    try:
        info=resources(reopened).inspect(run)
        assert info.reserved_tokens==50 and info.occupancy['global_calls']==1 and info.available_tokens==50
        p=prepared_call(run,call_id='after',bound_tokens=60,authority=replace(prepared_call(run).authority,ordinal=2))
        with pytest.raises(ResourceDenied):resources(reopened).reserve(p,deadline_monotonic=time.monotonic()+3)
    finally:reopened.db.close()


@pytest.mark.parametrize('lock',['reader','writer'])
def test_resource_busy_is_atomic_and_retryable(ledger,lock):
    hive,store,run=ledger;other=sqlite3.connect(hive.path,isolation_level=None)
    hive.db.execute('PRAGMA busy_timeout=17')
    try:
        other.execute('BEGIN' if lock=='reader' else 'BEGIN IMMEDIATE')
        if lock=='reader':other.execute('SELECT * FROM resource_allocations').fetchall()
        with pytest.raises(ResourceBusy):store.allocate('root','child',60)
        assert not hive.db.in_transaction
        other.execute('ROLLBACK')
        assert store.inspect(run).available_tokens==100
        store.allocate('root','child',60)
        assert store.inspect(run).available_tokens==40
        assert hive.db.execute('PRAGMA busy_timeout').fetchone()[0]==17
    finally:other.close()


def test_historical_inspection_never_invents_allowance(tmp_path):
    hive=HiveStore(str(tmp_path/'history.db'));run=hive.create_run('old',100)
    try:
        hive.record_usage(run,'layer','agent','provider','model',7,11)
        info=resources(hive).inspect(run)
        assert info.accounting_kind=='historical-measured' and info.actual_tokens==18
        assert info.available_tokens is None and info.budget_mode is None and info.hard_tokens is None
    finally:hive.db.close()


def test_root_identity_binds_run_and_cannot_multiply_authority(ledger):
    hive,store,run=ledger
    assert store.create_root('root',run,100).available_tokens==100
    other=hive.create_run('other',100)
    with pytest.raises(ResourceConflict):store.create_root('root',other,100)
    with pytest.raises(ResourceConflict):store.create_root('extra',run,100)
    with pytest.raises(ResourceConflict):store.create_root('root',run,101)
    assert hive.db.execute("SELECT run_id FROM resource_allocations WHERE allocation_id='root'").fetchone()[0]==run
    with pytest.raises(ResourceInputError):store.create_root('orphan','missing',1)


def test_complete_usage_and_execution_certainty_are_independent(ledger):
    _,store,run=ledger;p,_=reserve(store,run);dispatch(store,p)
    record=store.settle('call',usage_receipt(execution_terminal=False))
    assert record.usage_complete and record.permits_held and not record.execution_terminal
    assert store.inspect(run).actual_tokens==30 and store.inspect(run).occupancy['global_calls']==1
    with pytest.raises(ResourceDenied):store.close_allocation('root')
    store.mark_unknown('call',execution_terminal=True)
    assert store.inspect(run).occupancy['global_calls']==0
    assert store.close_allocation('root').used_tokens==30


def test_receipt_reordering_retains_immutable_partial_provenance(ledger):
    hive,store,run=ledger;p,_=reserve(store,run);dispatch(store,p)
    partial=usage_receipt(None,usage_complete=False,input_tokens=20,output_tokens=None)
    store.settle('call',partial)
    complete=usage_receipt(30,receipt_id='complete',receipt_digest='complete')
    done=store.settle('call',complete)
    assert store.settle('call',partial)==done
    with pytest.raises(ResourceConflict):store.settle('call',replace(partial,input_tokens=21))
    metadata=hive.db.execute('SELECT receipt_json FROM resource_calls').fetchone()[0]
    assert 'complete' in metadata and '"receipt"' in metadata
    assert hive.db.execute('SELECT COUNT(*) FROM resource_usage_projection').fetchone()[0]==1


def test_old_partial_receipt_identity_cannot_be_reused_on_another_call(ledger):
    _,store,run=ledger;p,_=reserve(store,run);dispatch(store,p)
    partial=usage_receipt(None,usage_complete=False,input_tokens=20,output_tokens=None)
    store.settle('call',partial)
    store.settle('call',usage_receipt(receipt_id='complete',receipt_digest='complete'))
    second,_=reserve(store,run,call_id='second',authority=replace(p.authority,ordinal=2));dispatch(store,second)
    with pytest.raises(ResourceConflict):store.settle('second',partial)
    assert store.inspect(run).actual_tokens==30 and store.inspect(run).reserved_tokens==50


def test_partial_receipt_count_overflow_is_atomic(ledger):
    hive,store,run=ledger;p,_=reserve(store,run);dispatch(store,p)
    with pytest.raises(ResourceInputError):store.settle('call',usage_receipt(None,usage_complete=False,input_tokens=MAX_INT64,output_tokens=1))
    assert store.inspect(run).reserved_tokens==50 and not store.inspect(run).frozen
    assert hive.db.execute('SELECT receipt_json FROM resource_calls').fetchone()[0] is None


def test_dispatch_rechecks_current_assignment_and_deadlines(ledger):
    hive,store,run=ledger;p,_=reserve(store,run)
    hive.db.execute('UPDATE resource_runs SET fence=2 WHERE run_id=?',(run,))
    with pytest.raises(ResourceDenied):dispatch(store,p)
    hive.db.execute('UPDATE resource_runs SET fence=1 WHERE run_id=?',(run,))
    hive.db.execute('UPDATE resource_calls SET expires_at_utc=1')
    with pytest.raises(ResourceDenied):dispatch(store,p)
    assert store.inspect(run).reserved_tokens==50
    store.release_reserved('call')
    assert store.inspect(run).available_tokens==100


def test_late_complete_receipt_after_stop_reconciles_original_hold(ledger):
    hive,store,run=ledger;p,_=reserve(store,run);dispatch(store,p);store.mark_unknown('call')
    hive.finish_run(run,'stopped');hive.db.execute("UPDATE resource_runs SET state='stopped',fence=2")
    done=store.settle('call',usage_receipt())
    assert done.usage_complete and store.inspect(run).available_tokens==70


def test_task_assignment_and_cross_run_allocation_are_bound(ledger):
    hive,store,run=ledger
    hive.db.execute("INSERT INTO tasks(id,run_id,status,owner,attempt,fence,lease_expires) VALUES('t',?,'claimed','worker',1,2,?)",(run,time.time()+60))
    authority=CallAuthority(RunAuthority(run,'owner',1),'root','researcher','t','worker',1,2,1)
    p,_=reserve(store,run,authority=authority)
    hive.db.execute("UPDATE tasks SET fence=3 WHERE id='t'")
    with pytest.raises(ResourceDenied):dispatch(store,p)
    store.release_reserved('call')
    other=hive.create_run('other',100);store.create_root('other-root',other,100)
    with pytest.raises(ResourceInputError):reserve(store,run,allocation_id='other-root',call_id='bad')


def test_queued_calls_have_no_charge_and_reserve_composes_atomically(ledger):
    hive,store,run=ledger;p,_=reserve(store,run)
    hive.db.execute("UPDATE resource_calls SET state='queued',permits_held=0")
    assert store.inspect(run).available_tokens==100
    def rollback(db):
        record=store._reserve_in_transaction(db,p,now_utc=time.time(),deadline_monotonic=time.monotonic()+3)
        assert record.state=='reserved'
        raise RuntimeError('rollback enclosing admission')
    with pytest.raises(RuntimeError):hive.transactions.write(rollback)
    assert store.inspect(run).available_tokens==100
    assert store.reserve(p,deadline_monotonic=time.monotonic()+3).state=='reserved'


def test_internal_composition_requires_owning_transaction(ledger):
    hive,store,run=ledger
    with pytest.raises(RuntimeError):store._reserve_in_transaction(hive.db,prepared_call(run),now_utc=time.time(),deadline_monotonic=time.monotonic()+3)
    assert store.inspect(run).available_tokens==100
    other=sqlite3.connect(':memory:',isolation_level=None)
    try:
        other.execute('BEGIN')
        with pytest.raises(RuntimeError):store._reserve_in_transaction(other,prepared_call(run),now_utc=time.time(),deadline_monotonic=time.monotonic()+3)
    finally:other.close()


def test_complete_receipt_pair_overflow_is_atomic(ledger):
    hive,store,run=ledger;p,_=reserve(store,run);dispatch(store,p)
    with pytest.raises(ResourceInputError):store.settle('call',usage_receipt(30,input_tokens=MAX_INT64,output_tokens=1))
    assert store.inspect(run).reserved_tokens==50
    assert hive.db.execute('SELECT COUNT(*) FROM ledger').fetchone()[0]==0
