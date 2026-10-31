"""Internal conserved resource accounting, serialized by the owning HiveStore.

Admission owns fairness and permit limits. This store supplies accounting inside
that same transaction; successful reservation alone is never permission to send.
Only the first committed dispatch transition authorizes an external attempt.
"""
from __future__ import annotations

import json

from app.hive.resource_types import (
    AllocationSnapshot, CallAuthority, CallRecord, PreparedCall, ResourceConflict,
    ResourceDenied, ResourceInputError, ResourceInspection, ResourceBusy, UsageReceipt,
    checked_add, finite_number, integer,
)


def _id(value, name='id'):
    if not isinstance(value, str) or not value.strip():
        raise ResourceInputError(f'{name}: expected nonempty identity')
    return value


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


class ResourceStore:
    def __init__(self, hive):
        self._hive = hive

    def _write(self, fn, *, deadline_monotonic=None):
        return self._hive.transactions.write(fn, deadline_monotonic=deadline_monotonic)

    def _allocation(self, db, allocation_id):
        _id(allocation_id, 'allocation_id')
        row = db.execute('SELECT * FROM resource_allocations WHERE allocation_id=?', (allocation_id,)).fetchone()
        if row is None:
            raise ResourceInputError('resource_allocation_missing')
        return row

    def _call(self, db, call_id):
        _id(call_id, 'call_id')
        row = db.execute('SELECT * FROM resource_calls WHERE call_id=?', (call_id,)).fetchone()
        if row is None:
            raise ResourceInputError('resource_call_missing')
        return row

    @staticmethod
    def _record(row):
        return CallRecord(row['call_id'], row['state'], row['bound_tokens'], row['actual_tokens'],
                          bool(row['permits_held']), bool(row['usage_complete']),
                          bool(row['execution_terminal']), row['request_fingerprint'])

    def _tree(self, db, root_id, *, replacing=None):
        """Checked Python sums, including open grants; SQLite SUM may overflow."""
        allocations = {r['allocation_id']: r for r in db.execute(
            'SELECT * FROM resource_allocations WHERE root_id=?', (root_id,))}
        own = {identity: 0 for identity in allocations}
        for row in db.execute('SELECT c.* FROM resource_calls c JOIN resource_allocations a '
                              'ON a.allocation_id=c.allocation_id WHERE a.root_id=?', (root_id,)):
            if replacing is not None and row['call_id'] == replacing[0]:
                charge = replacing[1]
            elif row['usage_complete']:
                charge = row['actual_tokens']
            elif row['state'] in ('reserved', 'dispatched', 'unknown'):
                charge = max(row['bound_tokens'], row['actual_tokens'] or 0)
            else:
                charge = 0
            own[row['allocation_id']] = checked_add(own[row['allocation_id']], charge)
        children = {identity: [] for identity in allocations}
        for row in allocations.values():
            if row['parent_id'] is not None:
                children[row['parent_id']].append(row['allocation_id'])
        # Iterative postorder keeps arbitrarily nested grants off Python's stack.
        used = {}
        pending = [(root_id, False)]
        while pending:
            identity, visited = pending.pop()
            if not visited:
                pending.append((identity, True))
                pending.extend((child, False) for child in children[identity])
                continue
            used[identity] = checked_add(own[identity], *(
                used[child] if allocations[child]['closed'] else max(allocations[child]['limit_tokens'], used[child])
                for child in children[identity]))
        return allocations, used

    def _snapshot(self, db, allocation_id):
        row = self._allocation(db, allocation_id)
        allocations, used = self._tree(db, row['root_id'])
        spent = used[allocation_id]
        return AllocationSnapshot(allocation_id, row['limit_tokens'], spent,
                                  max(0, row['limit_tokens'] - spent), max(0, spent - row['limit_tokens']),
                                  bool(row['closed']), bool(allocations[row['root_id']]['frozen']))

    def _available(self, db, allocation_id):
        row = self._allocation(db, allocation_id)
        allocations, used = self._tree(db, row['root_id'])
        if allocations[row['root_id']]['frozen']:
            raise ResourceDenied('resource_root_frozen')
        ancestor = row
        while True:
            if ancestor['closed']:
                raise ResourceDenied('resource_allocation_closed')
            if ancestor['parent_id'] is None:
                break
            ancestor = allocations[ancestor['parent_id']]
        return max(0, row['limit_tokens'] - used[allocation_id])

    def create_root(self, allocation_id, run_id, limit_tokens):
        return self._write(lambda db: self._create_root_in_transaction(db, allocation_id, run_id, limit_tokens))

    def _create_root_in_transaction(self, db, allocation_id, run_id, limit_tokens):
        self._require_transaction(db)
        _id(allocation_id, 'allocation_id'); _id(run_id, 'run_id')
        integer(limit_tokens, 'limit_tokens', minimum=1)
        if not db.execute('SELECT 1 FROM runs WHERE id=?', (run_id,)).fetchone():
            raise ResourceInputError('resource_run_missing')
        row = db.execute('SELECT * FROM resource_allocations WHERE allocation_id=?', (allocation_id,)).fetchone()
        if row is not None:
            if row['parent_id'] is not None or row['run_id'] != run_id or row['limit_tokens'] != limit_tokens:
                raise ResourceConflict('resource_allocation_identity_conflict')
            return self._snapshot(db, allocation_id)
        if db.execute('SELECT 1 FROM resource_allocations WHERE run_id=? AND parent_id IS NULL', (run_id,)).fetchone():
            raise ResourceConflict('resource_root_identity_conflict')
        db.execute('INSERT INTO resource_allocations(allocation_id,run_id,root_id,limit_tokens) VALUES(?,?,?,?)',
                   (allocation_id, run_id, allocation_id, limit_tokens))
        return self._snapshot(db, allocation_id)

    def allocate(self, parent_id, child_id, limit_tokens):
        _id(parent_id, 'parent_id'); _id(child_id, 'child_id'); integer(limit_tokens, 'limit_tokens', minimum=1)
        def allocate(db):
            parent = self._allocation(db, parent_id)
            child = db.execute('SELECT * FROM resource_allocations WHERE allocation_id=?', (child_id,)).fetchone()
            if child is not None:
                if child['parent_id'] != parent_id or child['limit_tokens'] != limit_tokens:
                    raise ResourceConflict('resource_allocation_identity_conflict')
                return self._snapshot(db, child_id)
            available = self._available(db, parent_id)
            # Validate even a denied addition before asking SQLite to store it.
            snapshot = self._snapshot(db, parent_id)
            checked_add(snapshot.used_tokens, limit_tokens)
            if limit_tokens > available:
                raise ResourceDenied('resource_tokens_exhausted')
            db.execute('INSERT INTO resource_allocations(allocation_id,run_id,root_id,parent_id,limit_tokens) '
                       'VALUES(?,?,?,?,?)', (child_id, parent['run_id'], parent['root_id'], parent_id, limit_tokens))
            return self._snapshot(db, child_id)
        return self._write(allocate)

    @staticmethod
    def _identity(prepared):
        return dict(run_id=prepared.authority.run.run_id, allocation_id=prepared.authority.allocation_id,
                    authority_json=_json(prepared.authority.to_dict()), request_fingerprint=prepared.request_fingerprint,
                    provider=prepared.provider, model=prepared.model, endpoint_id=prepared.endpoint_id,
                    profile_digest=prepared.profile_digest, sdk_version=prepared.sdk_version,
                    budget_mode=prepared.budget_mode, bound_tokens=prepared.bound_tokens)

    def _check_authority(self, db, authority, now_utc):
        run = db.execute('SELECT * FROM resource_runs WHERE run_id=?', (authority.run.run_id,)).fetchone()
        allocation = self._allocation(db, authority.allocation_id)
        if run is None or allocation['run_id'] != authority.run.run_id:
            raise ResourceInputError('resource_run_allocation_mismatch')
        if (run['state'] != 'active' or run['owner_id'] != authority.run.owner_id or
                run['fence'] != authority.run.fence or run['lease_expires_at_utc'] is None or
                run['lease_expires_at_utc'] <= now_utc or run['expires_at_utc'] <= now_utc):
            raise ResourceDenied('resource_authority_stale')
        if authority.task_id is not None:
            task = db.execute('SELECT * FROM tasks WHERE id=?', (authority.task_id,)).fetchone()
            if (task is None or task['run_id'] != authority.run.run_id or task['status'] != 'claimed' or
                    task['owner'] != authority.task_owner or task['attempt'] != authority.task_attempt or
                    task['fence'] != authority.task_fence or task['lease_expires'] is None or
                    task['lease_expires'] <= now_utc):
                raise ResourceDenied('resource_authority_stale')
        return run

    def reserve(self, prepared: PreparedCall, *, deadline_monotonic):
        return self._write(lambda db: self._reserve_in_transaction(
            db, prepared, now_utc=self._hive.clock.utc(), deadline_monotonic=deadline_monotonic),
            deadline_monotonic=deadline_monotonic)

    def _require_transaction(self, db):
        if db is not self._hive.db or not db.in_transaction:
            raise RuntimeError('Resource composition requires the owning HiveStore transaction')

    def _reserve_in_transaction(self, connection, prepared, *, now_utc, deadline_monotonic):
        """Accounting composition seam; caller owns transaction and permit policy."""
        self._require_transaction(connection)
        if not isinstance(prepared, PreparedCall):
            raise ResourceInputError('resource_prepared_call_required')
        finite_number(now_utc, 'now_utc'); finite_number(deadline_monotonic, 'deadline_monotonic')
        if self._hive.clock.monotonic() >= deadline_monotonic:
            raise ResourceBusy('resource_deadline_exceeded')
        db = connection
        identity = self._identity(prepared)
        row = db.execute('SELECT * FROM resource_calls WHERE call_id=?', (prepared.call_id,)).fetchone()
        if row is not None and any(row[key] != value for key, value in identity.items()):
            raise ResourceConflict('resource_call_identity_conflict')
        if row is not None and row['state'] != 'queued':
            return self._record(row)
        duplicate = db.execute('SELECT call_id FROM resource_calls WHERE run_id=? AND authority_json=?',
                               (identity['run_id'], identity['authority_json'])).fetchone()
        if duplicate is not None and duplicate['call_id'] != prepared.call_id:
            raise ResourceConflict('resource_call_identity_conflict')
        run = self._check_authority(db, prepared.authority, now_utc)
        if prepared.budget_mode != run['budget_mode'] or prepared.profile_digest != run['profile_digest']:
            raise ResourceConflict('resource_call_profile_conflict')
        if prepared.expires_at_utc <= now_utc or (row is not None and row['expires_at_utc'] <= now_utc):
            raise ResourceDenied('resource_call_expired')
        available = self._available(db, identity['allocation_id'])
        checked_add(self._snapshot(db, identity['allocation_id']).used_tokens, prepared.bound_tokens)
        if prepared.bound_tokens > available:
            raise ResourceDenied('resource_tokens_exhausted')
        if row is None:
            sequence = checked_add(max((r[0] for r in db.execute('SELECT sequence FROM resource_calls')), default=0), 1)
            values = dict(call_id=prepared.call_id, **identity, state='reserved', sequence=sequence,
                          expires_at_utc=prepared.expires_at_utc, waiter_expires_at_utc=prepared.expires_at_utc,
                          permits_held=1)
            db.execute(f'INSERT INTO resource_calls({",".join(values)}) VALUES({",".join("?" for _ in values)})',
                       tuple(values.values()))
        else:
            db.execute("UPDATE resource_calls SET state='reserved',permits_held=1 WHERE call_id=?", (prepared.call_id,))
        return self._record(self._call(db, prepared.call_id))

    def mark_dispatched(self, call_id, authority, *, deadline_monotonic):
        if not isinstance(authority, CallAuthority):
            raise ResourceInputError('resource_call_authority_required')
        def dispatch(db):
            row = self._call(db, call_id)
            if row['authority_json'] != _json(authority.to_dict()):
                raise ResourceConflict('resource_call_authority_conflict')
            if row['state'] != 'reserved':
                return False
            now = self._hive.clock.utc()
            self._check_authority(db, authority, now)
            if row['expires_at_utc'] <= now:
                raise ResourceDenied('resource_call_expired')
            self._available(db, row['allocation_id'])
            db.execute("UPDATE resource_calls SET state='dispatched' WHERE call_id=?", (call_id,))
            return True
        return self._write(dispatch, deadline_monotonic=deadline_monotonic)

    def mark_unknown(self, call_id, *, execution_terminal=False):
        if type(execution_terminal) is not bool:
            raise ResourceInputError('execution_terminal: expected bool')
        def unknown(db):
            row = self._call(db, call_id)
            if row['state'] not in ('dispatched', 'unknown', 'settled'):
                raise ResourceConflict('resource_call_transition_conflict')
            terminal = row['execution_terminal'] or execution_terminal
            state = 'settled' if row['usage_complete'] else 'unknown'
            db.execute('UPDATE resource_calls SET state=?,execution_terminal=?,permits_held=? WHERE call_id=?',
                       (state, int(terminal), int(not terminal), call_id))
            return self._record(self._call(db, call_id))
        return self._write(unknown)

    def release_reserved(self, call_id):
        def release(db):
            row = self._call(db, call_id)
            if row['state'] == 'released':
                return self._record(row)
            if row['state'] != 'reserved':
                raise ResourceConflict('resource_call_transition_conflict')
            db.execute("UPDATE resource_calls SET state='released',permits_held=0,execution_terminal=1 WHERE call_id=?", (call_id,))
            return self._record(self._call(db, call_id))
        return self._write(release)

    def settle(self, call_id, receipt: UsageReceipt):
        if not isinstance(receipt, UsageReceipt):
            raise ResourceInputError('resource_usage_receipt_required')
        receipt_data = receipt.to_dict()
        def settle(db):
            row = self._call(db, call_id)
            if row['state'] not in ('dispatched', 'unknown', 'settled'):
                raise ResourceConflict('resource_call_transition_conflict')
            if row['provider'] != receipt.provider or row['model'] != receipt.requested_model:
                raise ResourceConflict('resource_receipt_route_conflict')
            history = json.loads(row['receipt_json'])['receipts'] if row['receipt_json'] else []
            for prior in history:
                if prior['receipt_id'] == receipt.receipt_id:
                    if prior != receipt_data:
                        raise ResourceConflict('resource_receipt_conflict')
                    return self._record(row)
            if row['usage_complete']:
                raise ResourceConflict('resource_receipt_conflict')
            # Retain every accepted partial provenance item. A delayed replay must
            # remain immutable after a complete receipt supersedes its charge.
            for other in db.execute('SELECT call_id,receipt_json FROM resource_calls WHERE receipt_json IS NOT NULL AND call_id!=?', (call_id,)):
                if any(prior['receipt_id'] == receipt.receipt_id for prior in json.loads(other['receipt_json'])['receipts']):
                    raise ResourceConflict('resource_receipt_identity_conflict')
            receipt_json = _json({'receipts': [*history, receipt_data]})
            # Total is authoritative when present; absent totals use known disjoint
            # input/output counts. Provider adapters normalize category semantics.
            known_pair = checked_add(receipt.input_tokens or 0, receipt.output_tokens or 0)
            known = receipt.total_tokens
            if known is None:
                known = known_pair
                if receipt.input_tokens is None and receipt.output_tokens is None:
                    known = None
            terminal = row['execution_terminal'] or receipt.execution_terminal
            if not receipt.usage_complete:
                known = max(row['actual_tokens'] or 0, known or 0) if known is not None or row['actual_tokens'] is not None else None
            allocation = self._allocation(db, row['allocation_id'])
            charge = known if receipt.usage_complete else max(row['bound_tokens'], known or 0)
            self._tree(db, allocation['root_id'], replacing=(call_id, charge))
            db.execute('UPDATE resource_calls SET state=?,actual_tokens=?,receipt_id=?,receipt_digest=?,receipt_json=?, '
                       'usage_complete=?,execution_terminal=?,permits_held=? WHERE call_id=?',
                       ('settled' if receipt.usage_complete else 'unknown', known, receipt.receipt_id,
                        receipt.receipt_digest, receipt_json, int(receipt.usage_complete), int(terminal), int(not terminal), call_id))
            if (known or 0) > row['bound_tokens']:
                db.execute('UPDATE resource_allocations SET frozen=1 WHERE allocation_id=?', (allocation['root_id'],))
            if receipt.usage_complete:
                # Legacy pair is compatibility history, not authoritative governed
                # totals. Preserve null/missing counts rather than inventing zero.
                cursor = db.execute('INSERT INTO ledger(run_id,ts,layer,agent,provider,model,in_tok,out_tok) '
                                    'VALUES(?,?,?,?,?,?,?,?)',
                                    (row['run_id'], self._hive.clock.utc(), 'hive', json.loads(row['authority_json'])['role'],
                                     receipt.provider, receipt.resolved_model or receipt.requested_model,
                                     receipt.input_tokens, receipt.output_tokens))
                db.execute('INSERT INTO resource_usage_projection VALUES(?,?)', (call_id, cursor.lastrowid))
            return self._record(self._call(db, call_id))
        return self._write(settle)

    def close_allocation(self, allocation_id):
        def close(db):
            row = self._allocation(db, allocation_id)
            if not row['closed']:
                if db.execute('SELECT 1 FROM resource_allocations WHERE parent_id=? AND closed=0', (allocation_id,)).fetchone():
                    raise ResourceDenied('resource_allocation_has_open_children')
                if db.execute("SELECT 1 FROM resource_calls WHERE allocation_id=? AND "
                              "(state IN ('reserved','dispatched','unknown') OR permits_held=1)", (allocation_id,)).fetchone():
                    raise ResourceDenied('resource_allocation_has_held_calls')
                db.execute('UPDATE resource_allocations SET closed=1 WHERE allocation_id=?', (allocation_id,))
            return self._snapshot(db, allocation_id)
        return self._write(close)

    def inspect(self, run_id):
        _id(run_id, 'run_id')
        def inspect(db):
            if not db.execute('SELECT 1 FROM runs WHERE id=?', (run_id,)).fetchone():
                raise ResourceInputError('resource_run_missing')
            run = db.execute('SELECT * FROM resource_runs WHERE run_id=?', (run_id,)).fetchone()
            root = db.execute('SELECT * FROM resource_allocations WHERE run_id=? AND parent_id IS NULL', (run_id,)).fetchone()
            if root is None:
                total = checked_add(*(checked_add(r[0] or 0, r[1] or 0) for r in db.execute(
                    'SELECT in_tok,out_tok FROM ledger WHERE run_id=?', (run_id,))))
                return ResourceInspection('historical-measured', None, None, total, 0, 0, None, 0, False, {}, {})
            actual = reserved = unknown = 0
            for row in db.execute('SELECT * FROM resource_calls WHERE run_id=?', (run_id,)):
                if row['usage_complete']:
                    actual = checked_add(actual, row['actual_tokens'])
                elif row['state'] == 'unknown':
                    unknown = checked_add(unknown, max(row['bound_tokens'], row['actual_tokens'] or 0))
                elif row['state'] in ('reserved', 'dispatched'):
                    reserved = checked_add(reserved, row['bound_tokens'])
            snapshot = self._snapshot(db, root['allocation_id'])
            if run is None:
                raise ResourceConflict('resource_run_not_admitted')
            mode = run['budget_mode']
            queue = dict(global_calls=db.execute("SELECT COUNT(*) FROM resource_calls WHERE state='queued'").fetchone()[0],
                         run_calls=db.execute("SELECT COUNT(*) FROM resource_calls WHERE run_id=? AND state='queued'", (run_id,)).fetchone()[0],
                         queued_runs=db.execute("SELECT COUNT(*) FROM resource_runs WHERE state='queued'").fetchone()[0])
            occupancy = dict(global_calls=db.execute('SELECT COUNT(*) FROM resource_calls WHERE permits_held=1').fetchone()[0],
                             run_calls=db.execute('SELECT COUNT(*) FROM resource_calls WHERE run_id=? AND permits_held=1', (run_id,)).fetchone()[0],
                             active_runs=db.execute("SELECT COUNT(*) FROM resource_runs WHERE state='active'").fetchone()[0],
                             providers={r[0]:r[1] for r in db.execute('SELECT provider,COUNT(*) FROM resource_calls WHERE permits_held=1 GROUP BY provider')})
            return ResourceInspection('governed-v1', mode, mode == 'hard', actual, reserved, unknown,
                                      snapshot.available_tokens, snapshot.debt_tokens, snapshot.frozen, queue, occupancy)
        return self._write(inspect)
