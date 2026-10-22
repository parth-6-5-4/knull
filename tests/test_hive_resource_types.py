"""Pure validation and deep immutability at the shared resource boundary."""
from dataclasses import FrozenInstanceError, replace
import math
import pytest


def test_policy_canonical_identity_and_relationships():
    from app.hive.resource_types import ResourcePolicy, ResourceInputError
    policy=ResourcePolicy()
    assert policy.digest==ResourcePolicy().digest
    assert policy.digest!=replace(policy,global_calls=9).digest
    for changes in ({'active_runs':True},{'queued_calls':2**63},{'queue_wait_s':math.inf},
                    {'busy_timeout_ms':-1},{'owner_heartbeat_s':15}, {'waiter_refresh_s':6},
                    {'run_calls':9},{'provider_calls':9},{'clock_skew_s':float('nan')}):
        with pytest.raises(ResourceInputError): replace(policy,**changes)
    with pytest.raises(FrozenInstanceError): policy.active_runs=8


def test_run_request_preserves_defaults_and_rejects_unsafe_counts():
    from app.hive.resource_types import RunRequest, ResourceInputError
    req=RunRequest('objective')
    assert (req.workers,req.max_subtasks,req.budget_tokens,req.budget_mode)==(3,4,200000,'hard')
    assert (req.lease_s,req.heartbeat_s,req.tick_s,req.max_attempts)==(300,60,0.2,3)
    for changes in ({'workers':9},{'budget_tokens':True},{'max_attempts':0},{'run_timeout_s':float('nan')},
                    {'budget_mode':'maybe'},{'heartbeat_s':300},{'objective':''}):
        with pytest.raises(ResourceInputError):replace(req,**changes)


def test_nested_payloads_are_copied_and_deeply_immutable():
    from app.hive.resource_types import UsageReceipt,ResourceInspection,ResourceInputError
    payload={'cached':{'tokens':3,'kind':'subset'},'charges':[{'name':'text','tokens':7}]}
    receipt=UsageReceipt('receipt','digest','provider','model','model',None,7,4,11,payload,True,True)
    payload['cached']['tokens']=90;payload['charges'][0]['tokens']=80
    assert receipt.categories['cached']['tokens']==3
    assert receipt.categories['charges'][0]['tokens']==7
    with pytest.raises(TypeError):receipt.categories['cached']['tokens']=2
    inspection=ResourceInspection('governed-v1','hard',True,11,0,0,9,0,False,{'run':[1]}, {'provider':2})
    with pytest.raises(TypeError):inspection.queue['run'][0]=2
    with pytest.raises(ResourceInputError):replace(receipt,total_tokens=None)
    with pytest.raises(ResourceInputError):replace(receipt,input_tokens=True)
    with pytest.raises(ResourceInputError):replace(receipt,categories={'bad':object()})


def test_authority_requires_complete_task_identity():
    from app.hive.resource_types import CallAuthority,RunAuthority,ResourceInputError
    run=RunAuthority('r','owner',1)
    authority=CallAuthority(run,'a','planner',None,None,None,None,0)
    with pytest.raises(ResourceInputError):replace(authority,task_id='t')
    with pytest.raises(ResourceInputError):replace(run,fence=True)
    with pytest.raises(ResourceInputError):replace(authority,ordinal=2**63)
    assert replace(authority,role='researcher',task_id='t',task_owner='w',task_attempt=1,task_fence=2).task_id=='t'


def test_prepared_call_copies_messages_and_validates_route_bound():
    from app.hive.resource_types import PreparedCall,CallAuthority,RunAuthority,ResourceInputError
    messages=[{'role':'user','content':[{'text':'hello'}]}]
    call=PreparedCall('id',CallAuthority(RunAuthority('r','owner',1),'a','planner',None,None,None,None,0),
                      'p','m','endpoint','profile','sdk','fingerprint',messages,0,100,200,'hard',50)
    messages[0]['content'][0]['text']='changed'
    assert call.messages[0]['content'][0]['text']=='hello'
    with pytest.raises(TypeError):call.messages[0]['content'][0]['text']='changed'
    for changes in ({'bound_tokens':99},{'temperature':float('nan')},{'expires_at_utc':float('inf')}):
        with pytest.raises(ResourceInputError):replace(call,**changes)


def test_errors_do_not_retry_as_llm_errors_except_provider_failures():
    from app.hive.resource_types import ResourceBusy,ProviderCallError,UsageReceipt,ResourceInputError
    from app.llm import LLMError
    assert not isinstance(ResourceBusy('resource_busy'),LLMError)
    err=ProviderCallError('transport',True,True,False)
    assert isinstance(err,LLMError) and err.sent and not err.execution_terminal
    with pytest.raises(ResourceInputError):ProviderCallError('bad',True,False,False)


def test_inspection_hard_indicator_is_boolean_and_historical_is_unknown():
    from app.hive.resource_types import ResourceInspection,ResourceInputError
    hard=ResourceInspection('governed-v1','hard',True,10,5,0,15,0,False,{}, {})
    assert hard.hard_tokens is True
    assert replace(hard,budget_mode='estimated',hard_tokens=False).hard_tokens is False
    historical=replace(hard,accounting_kind='historical-measured',budget_mode=None,hard_tokens=None,available_tokens=None)
    assert historical.hard_tokens is None
    with pytest.raises(ResourceInputError):replace(hard,hard_tokens=30)
    with pytest.raises(ResourceInputError):replace(hard,budget_mode='estimated')


def test_counts_tickets_snapshots_and_checked_arithmetic_are_strict():
    from app.hive.resource_types import (RunTicket,AllocationSnapshot,CallRecord,CallOutcome,
        UsageReceipt,ResourceInputError,checked_add)
    ticket=RunTicket('r','a',10,20,'policy','profile','hard')
    for changes in ({'accepted_at_utc':True},{'expires_at_utc':10},{'run_id':''}):
        with pytest.raises(ResourceInputError):replace(ticket,**changes)
    snapshot=AllocationSnapshot('a',20,23,0,3,False,True)
    with pytest.raises(ResourceInputError):replace(snapshot,available_tokens=1)
    call=CallRecord('c','unknown',20,None,True,False,False,'fingerprint')
    with pytest.raises(ResourceInputError):replace(call,usage_complete=True)
    with pytest.raises(ResourceInputError):replace(call,execution_terminal=True)
    assert checked_add(2**63-2,1)==2**63-1
    with pytest.raises(ResourceInputError):checked_add(2**63-1,1)
    with pytest.raises(ResourceInputError):checked_add(False)
    receipt=UsageReceipt('id','digest','p','m',None,None,None,None,None,{},False,False)
    outcome=CallOutcome('',receipt)
    assert outcome.to_dict()['receipt']['total_tokens'] is None


def test_oversized_numeric_deadlines_and_parameters_reject_cleanly():
    from app.hive.resource_types import ResourcePolicy,ResourceInputError
    with pytest.raises(ResourceInputError):ResourcePolicy(queue_wait_s=10**1000)


def test_request_custom_lease_retains_runner_derived_heartbeat_default():
    from app.hive.resource_types import RunRequest
    assert RunRequest('objective',lease_s=30).heartbeat_s==6


def test_inspection_requires_measured_counts_even_when_headroom_unknown():
    from app.hive.resource_types import ResourceInspection,ResourceInputError
    historical=ResourceInspection('historical-measured',None,None,10,0,0,None,0,False,{}, {})
    with pytest.raises(ResourceInputError):replace(historical,actual_tokens=None)
    with pytest.raises(ResourceInputError):replace(historical,hard_tokens=False)
