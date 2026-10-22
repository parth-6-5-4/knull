"""Validated immutable contracts shared by local admission and governed completion.

Only JSON values cross persisted boundaries. Nested inputs are defensively copied
and frozen; call messages remain local to their originating coroutine.
"""
from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass, fields
import hashlib
import json
import math
import time
from types import MappingProxyType
from typing import Protocol

from app.llm import LLMError

MAX_INT64 = (1 << 63) - 1


class ResourceError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class ResourceInputError(ResourceError): pass
class ResourceConflict(ResourceError): pass
class ResourceDenied(ResourceError): pass
class ResourceQueueFull(ResourceError): pass
class ResourceBusy(ResourceError): pass
class ResourceProfileError(ResourceError): pass
class ResourcePersistenceError(ResourceError): pass


class Clock(Protocol):
    def utc(self) -> float: ...
    def monotonic(self) -> float: ...
    async def sleep(self, seconds: float) -> None: ...


class SystemClock:
    def utc(self) -> float: return time.time()
    def monotonic(self) -> float: return time.monotonic()
    async def sleep(self, seconds: float) -> None: await asyncio.sleep(seconds)


def integer(value, name, *, minimum=0):
    """Validate counts before arithmetic or SQLite conversion (bool is not int)."""
    if type(value) is not int or not minimum <= value <= MAX_INT64:
        raise ResourceInputError(f'{name}: expected signed-64-bit integer >= {minimum}')
    return value


def checked_add(*values: int) -> int:
    total = 0
    for value in values:
        integer(value, 'count')
        total += value
        integer(total, 'sum')
    return total


def finite_number(value, name, *, positive=False):
    try:
        valid = type(value) in (int, float) and math.isfinite(value) and (not positive or value > 0)
    except OverflowError:
        valid = False
    if not valid:
        raise ResourceInputError(f'{name}: expected finite number' + (' > 0' if positive else ''))
    return value


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ResourceInputError(f'{name}: expected nonempty text')


def _boolean(value, name):
    if type(value) is not bool: raise ResourceInputError(f'{name}: expected boolean')


def _mode(value):
    if value not in ('hard', 'estimated'): raise ResourceInputError('budget_mode: expected hard or estimated')


def _freeze(value):
    if value is None or type(value) in (str, bool): return value
    if type(value) is int:
        if not -MAX_INT64-1 <= value <= MAX_INT64: raise ResourceInputError('JSON integer overflow')
        return value
    if type(value) is float:
        finite_number(value, 'JSON number')
        return value
    if isinstance(value, Mapping):
        if any(type(key) is not str for key in value): raise ResourceInputError('JSON object keys must be strings')
        return MappingProxyType({key: _freeze(item) for key,item in value.items()})
    if isinstance(value, (tuple, list)): return tuple(_freeze(item) for item in value)
    raise ResourceInputError('Expected JSON-compatible immutable data')


def _plain(value):
    if isinstance(value, Mapping): return {key:_plain(item) for key,item in value.items()}
    if isinstance(value, tuple): return [_plain(item) for item in value]
    return value


def _mapping(record, name):
    value = getattr(record, name)
    if not isinstance(value, Mapping): raise ResourceInputError(f'{name}: expected object')
    object.__setattr__(record, name, _freeze(value))


class _Record:
    def to_dict(self):
        return {field.name: (_plain(value.to_dict()) if isinstance(value, _Record) else _plain(value))
                for field in fields(self) for value in (getattr(self, field.name),)}


@dataclass(frozen=True)
class ResourcePolicy(_Record):
    active_runs: int = 4
    queued_runs: int = 20
    global_calls: int = 8
    run_calls: int = 3
    provider_calls: int = 2
    queued_calls: int = 128
    run_queued_calls: int = 16
    queue_wait_s: float = 60
    call_timeout_s: float = 120
    owner_heartbeat_s: float = 3
    owner_lease_s: float = 15
    waiter_refresh_s: float = 1
    waiter_lease_s: float = 5
    busy_timeout_ms: int = 50
    cleanup_timeout_s: float = 5
    clock_skew_s: float = 2

    def __post_init__(self):
        for name in ('active_runs','queued_runs','global_calls','run_calls','provider_calls',
                     'queued_calls','run_queued_calls','busy_timeout_ms'):
            integer(getattr(self,name),name,minimum=1)
        for name in ('queue_wait_s','call_timeout_s','owner_heartbeat_s','owner_lease_s',
                     'waiter_refresh_s','waiter_lease_s','cleanup_timeout_s','clock_skew_s'):
            finite_number(getattr(self,name),name,positive=True)
            # Equivalent numeric values have one policy identity.
            object.__setattr__(self,name,float(getattr(self,name)))
        if (self.run_calls > self.global_calls or self.provider_calls > self.global_calls
                or self.run_queued_calls > self.queued_calls
                or self.owner_heartbeat_s >= self.owner_lease_s
                or self.waiter_refresh_s >= self.waiter_lease_s
                or self.waiter_refresh_s > 1):
            raise ResourceInputError('Invalid policy limit/lease relationship')

    @property
    def canonical_json(self): return json.dumps(self.to_dict(),sort_keys=True,separators=(',',':'),allow_nan=False)

    @property
    def digest(self): return hashlib.sha256(self.canonical_json.encode()).hexdigest()


@dataclass(frozen=True)
class RunRequest(_Record):
    objective: str
    workers: int = 3
    max_subtasks: int = 4
    budget_tokens: int = 200_000
    task_timeout_s: float = 600
    run_timeout_s: float = 1800
    budget_mode: str = 'hard'
    max_attempts: int = 3
    lease_s: float = 300
    heartbeat_s: float | None = None
    tick_s: float = 0.2

    def __post_init__(self):
        _text(self.objective,'objective'); _mode(self.budget_mode)
        for name in ('workers','max_subtasks','budget_tokens','max_attempts'):
            integer(getattr(self,name),name,minimum=1)
        if self.workers>8 or self.max_subtasks>8: raise ResourceInputError('workers/max_subtasks must be <= 8')
        finite_number(self.lease_s,'lease_s',positive=True)
        if self.heartbeat_s is None:
            object.__setattr__(self,'heartbeat_s',min(60,self.lease_s/5))
        for name in ('task_timeout_s','run_timeout_s','lease_s','heartbeat_s','tick_s'):
            finite_number(getattr(self,name),name,positive=True)
        if self.heartbeat_s >= self.lease_s: raise ResourceInputError('heartbeat_s must be below lease_s')


@dataclass(frozen=True)
class RunTicket(_Record):
    run_id: str
    allocation_id: str
    accepted_at_utc: float
    expires_at_utc: float
    policy_digest: str
    profile_digest: str
    budget_mode: str

    def __post_init__(self):
        for name in ('run_id','allocation_id','policy_digest','profile_digest'): _text(getattr(self,name),name)
        finite_number(self.accepted_at_utc,'accepted_at_utc');finite_number(self.expires_at_utc,'expires_at_utc')
        if self.expires_at_utc<=self.accepted_at_utc: raise ResourceInputError('Run expiry must follow acceptance')
        _mode(self.budget_mode)


@dataclass(frozen=True)
class RunAuthority(_Record):
    run_id: str
    owner_id: str
    fence: int

    def __post_init__(self):
        _text(self.run_id,'run_id');_text(self.owner_id,'owner_id');integer(self.fence,'fence',minimum=1)


@dataclass(frozen=True)
class CallAuthority(_Record):
    run: RunAuthority
    allocation_id: str
    role: str
    task_id: str | None
    task_owner: str | None
    task_attempt: int | None
    task_fence: int | None
    ordinal: int

    def __post_init__(self):
        if not isinstance(self.run,RunAuthority): raise ResourceInputError('run: expected RunAuthority')
        _text(self.allocation_id,'allocation_id');_text(self.role,'role');integer(self.ordinal,'ordinal')
        task=(self.task_id,self.task_owner,self.task_attempt,self.task_fence)
        if all(value is None for value in task):
            if self.role!='planner': raise ResourceInputError('Only planner has run-scoped authority')
        elif any(value is None for value in task) or self.role=='planner':
            raise ResourceInputError('Task authority must contain complete assignment identity')
        else:
            _text(self.task_id,'task_id');_text(self.task_owner,'task_owner')
            integer(self.task_attempt,'task_attempt',minimum=1);integer(self.task_fence,'task_fence',minimum=1)


@dataclass(frozen=True)
class PreparedCall(_Record):
    call_id: str
    authority: CallAuthority
    provider: str
    model: str
    endpoint_id: str
    profile_digest: str
    sdk_version: str
    request_fingerprint: str
    messages: tuple
    temperature: float
    max_output_tokens: int
    bound_tokens: int
    budget_mode: str
    expires_at_utc: float

    def __post_init__(self):
        if not isinstance(self.authority,CallAuthority): raise ResourceInputError('authority: expected CallAuthority')
        for name in ('call_id','provider','model','endpoint_id','profile_digest','sdk_version','request_fingerprint'):
            _text(getattr(self,name),name)
        if not isinstance(self.messages,(tuple,list)) or not self.messages:
            raise ResourceInputError('messages: expected nonempty sequence')
        if any(not isinstance(message,Mapping) for message in self.messages): raise ResourceInputError('messages: expected objects')
        object.__setattr__(self,'messages',_freeze(self.messages))
        finite_number(self.temperature,'temperature');finite_number(self.expires_at_utc,'expires_at_utc')
        if self.temperature < 0: raise ResourceInputError('temperature must be nonnegative')
        integer(self.max_output_tokens,'max_output_tokens',minimum=1);integer(self.bound_tokens,'bound_tokens',minimum=1)
        if self.bound_tokens < self.max_output_tokens: raise ResourceInputError('bound_tokens is below output bound')
        _mode(self.budget_mode)


@dataclass(frozen=True)
class UsageReceipt(_Record):
    receipt_id: str
    receipt_digest: str
    provider: str
    requested_model: str
    resolved_model: str | None
    request_id: str | None
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    categories: Mapping
    usage_complete: bool
    execution_terminal: bool

    def __post_init__(self):
        for name in ('receipt_id','receipt_digest','provider','requested_model'): _text(getattr(self,name),name)
        for name in ('resolved_model','request_id'):
            if getattr(self,name) is not None: _text(getattr(self,name),name)
        for name in ('input_tokens','output_tokens','total_tokens'):
            if getattr(self,name) is not None: integer(getattr(self,name),name)
        _boolean(self.usage_complete,'usage_complete');_boolean(self.execution_terminal,'execution_terminal')
        if self.usage_complete and self.total_tokens is None: raise ResourceInputError('Complete usage requires authoritative total')
        _mapping(self,'categories')


@dataclass(frozen=True)
class CallOutcome(_Record):
    text: str
    receipt: UsageReceipt

    def __post_init__(self):
        if not isinstance(self.text,str) or not isinstance(self.receipt,UsageReceipt): raise ResourceInputError('Invalid call outcome')


class ProviderCallError(LLMError):
    """Transport classification: only proven pre-send failure can say sent=False."""
    def __init__(self, code, retryable, sent, execution_terminal, receipt=None):
        _text(code,'code')
        for name,value in (('retryable',retryable),('sent',sent),('execution_terminal',execution_terminal)): _boolean(value,name)
        if not sent and not execution_terminal: raise ResourceInputError('Proven pre-send failure is execution-terminal')
        if receipt is not None and not isinstance(receipt,UsageReceipt): raise ResourceInputError('Invalid receipt')
        self.code=code;self.retryable=retryable;self.sent=sent;self.execution_terminal=execution_terminal;self.receipt=receipt
        super().__init__(code)


@dataclass(frozen=True)
class CallRecord(_Record):
    call_id: str
    state: str
    bound_tokens: int
    actual_tokens: int | None
    permits_held: bool
    usage_complete: bool
    execution_terminal: bool
    request_fingerprint: str

    def __post_init__(self):
        _text(self.call_id,'call_id');_text(self.request_fingerprint,'request_fingerprint');integer(self.bound_tokens,'bound_tokens')
        if self.state not in ('queued','reserved','dispatched','unknown','settled','released','cancelled','expired'): raise ResourceInputError('Invalid call state')
        if self.actual_tokens is not None: integer(self.actual_tokens,'actual_tokens')
        for name in ('permits_held','usage_complete','execution_terminal'): _boolean(getattr(self,name),name)
        if self.usage_complete and self.actual_tokens is None: raise ResourceInputError('Complete call requires actual total')
        if self.execution_terminal and self.permits_held: raise ResourceInputError('Execution-terminal call cannot hold permits')


@dataclass(frozen=True)
class AllocationSnapshot(_Record):
    allocation_id: str
    limit_tokens: int
    used_tokens: int
    available_tokens: int
    debt_tokens: int
    closed: bool
    frozen: bool

    def __post_init__(self):
        _text(self.allocation_id,'allocation_id')
        for name in ('limit_tokens','used_tokens','available_tokens','debt_tokens'): integer(getattr(self,name),name)
        _boolean(self.closed,'closed');_boolean(self.frozen,'frozen')
        if self.available_tokens!=max(0,self.limit_tokens-self.used_tokens) or self.debt_tokens!=max(0,self.used_tokens-self.limit_tokens):
            raise ResourceInputError('Allocation availability/debt does not reconcile')


@dataclass(frozen=True)
class ResourceInspection(_Record):
    accounting_kind: str
    budget_mode: str | None
    hard_tokens: bool | None
    actual_tokens: int
    reserved_tokens: int
    unknown_tokens: int
    available_tokens: int | None
    debt_tokens: int
    frozen: bool
    queue: Mapping
    occupancy: Mapping

    def __post_init__(self):
        if self.accounting_kind not in ('governed-v1','historical-measured'): raise ResourceInputError('Invalid accounting_kind')
        if self.accounting_kind=='governed-v1':
            _mode(self.budget_mode)
            if self.hard_tokens is None or self.available_tokens is None: raise ResourceInputError('Governed inspection requires allowance')
        elif self.budget_mode is not None or self.hard_tokens is not None or self.available_tokens is not None:
            raise ResourceInputError('Historical measured inspection has no governed mode/headroom')
        if self.hard_tokens is not None: _boolean(self.hard_tokens,'hard_tokens')
        if self.accounting_kind == 'governed-v1' and self.hard_tokens is not (self.budget_mode == 'hard'):
            raise ResourceInputError('hard_tokens must reflect qualified hard mode')
        for name in ('actual_tokens','reserved_tokens','unknown_tokens','debt_tokens'):
            integer(getattr(self,name),name)
        if self.available_tokens is not None: integer(self.available_tokens,'available_tokens')
        _boolean(self.frozen,'frozen');_mapping(self,'queue');_mapping(self,'occupancy')
