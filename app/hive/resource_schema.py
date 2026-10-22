"""Additive schema v2. Historical table DDL lives unchanged in schema.V1_SCHEMA."""
RESOURCE_SCHEMA = """
CREATE TABLE resource_policy(
  singleton INTEGER PRIMARY KEY CHECK(singleton=1),
  digest TEXT NOT NULL UNIQUE CHECK(length(digest)>0),
  canonical_json TEXT NOT NULL CHECK(json_valid(canonical_json)));
CREATE TABLE resource_profiles(
  digest TEXT PRIMARY KEY NOT NULL CHECK(length(digest)>0),
  canonical_json TEXT NOT NULL CHECK(json_valid(canonical_json)));
CREATE TABLE resource_allocations(
  allocation_id TEXT PRIMARY KEY NOT NULL,
  root_id TEXT NOT NULL REFERENCES resource_allocations(allocation_id),
  parent_id TEXT REFERENCES resource_allocations(allocation_id),
  limit_tokens INTEGER NOT NULL CHECK(typeof(limit_tokens)='integer' AND limit_tokens>=0),
  closed INTEGER NOT NULL DEFAULT 0 CHECK(closed IN (0,1)),
  frozen INTEGER NOT NULL DEFAULT 0 CHECK(frozen IN (0,1)),
  CHECK((parent_id IS NULL AND root_id=allocation_id) OR
        (parent_id IS NOT NULL AND parent_id!=allocation_id)));
CREATE INDEX resource_allocations_parent ON resource_allocations(parent_id);
CREATE TABLE resource_runs(
  run_id TEXT PRIMARY KEY NOT NULL REFERENCES runs(id),
  allocation_id TEXT NOT NULL UNIQUE REFERENCES resource_allocations(allocation_id),
  request_json TEXT NOT NULL CHECK(json_valid(request_json)),
  policy_digest TEXT NOT NULL REFERENCES resource_policy(digest),
  profile_digest TEXT NOT NULL REFERENCES resource_profiles(digest),
  budget_mode TEXT NOT NULL CHECK(budget_mode IN ('hard','estimated')),
  accepted_at_utc REAL NOT NULL, expires_at_utc REAL NOT NULL CHECK(expires_at_utc>accepted_at_utc),
  state TEXT NOT NULL CHECK(state IN ('queued','active','completed','stopped','interrupted','cancelled','expired')),
  sequence INTEGER NOT NULL UNIQUE CHECK(typeof(sequence)='integer' AND sequence>=0),
  origin_id TEXT NOT NULL, replayable INTEGER NOT NULL CHECK(replayable IN (0,1)),
  owner_id TEXT, fence INTEGER NOT NULL DEFAULT 0 CHECK(typeof(fence)='integer' AND fence>=0),
  lease_expires_at_utc REAL,
  CHECK((owner_id IS NULL AND lease_expires_at_utc IS NULL) OR
        (owner_id IS NOT NULL AND lease_expires_at_utc IS NOT NULL)));
CREATE INDEX resource_runs_queue ON resource_runs(state,sequence);
CREATE TABLE resource_calls(
  call_id TEXT PRIMARY KEY NOT NULL,
  run_id TEXT NOT NULL REFERENCES resource_runs(run_id),
  allocation_id TEXT NOT NULL REFERENCES resource_allocations(allocation_id),
  authority_json TEXT NOT NULL CHECK(json_valid(authority_json)),
  request_fingerprint TEXT NOT NULL,
  provider TEXT NOT NULL, model TEXT NOT NULL, endpoint_id TEXT NOT NULL,
  profile_digest TEXT NOT NULL REFERENCES resource_profiles(digest), sdk_version TEXT NOT NULL,
  budget_mode TEXT NOT NULL CHECK(budget_mode IN ('hard','estimated')),
  bound_tokens INTEGER NOT NULL CHECK(typeof(bound_tokens)='integer' AND bound_tokens>=0),
  state TEXT NOT NULL CHECK(state IN ('queued','reserved','dispatched','unknown','settled','released','cancelled','expired')),
  sequence INTEGER NOT NULL UNIQUE CHECK(typeof(sequence)='integer' AND sequence>=0),
  expires_at_utc REAL NOT NULL, waiter_expires_at_utc REAL NOT NULL,
  actual_tokens INTEGER CHECK(actual_tokens IS NULL OR (typeof(actual_tokens)='integer' AND actual_tokens>=0)),
  receipt_id TEXT UNIQUE, receipt_digest TEXT, receipt_json TEXT CHECK(receipt_json IS NULL OR json_valid(receipt_json)),
  usage_complete INTEGER NOT NULL DEFAULT 0 CHECK(usage_complete IN (0,1)),
  execution_terminal INTEGER NOT NULL DEFAULT 0 CHECK(execution_terminal IN (0,1)),
  permits_held INTEGER NOT NULL DEFAULT 0 CHECK(permits_held IN (0,1)),
  CHECK(usage_complete=0 OR actual_tokens IS NOT NULL),
  CHECK(execution_terminal=0 OR permits_held=0),
  UNIQUE(run_id,authority_json));
CREATE INDEX resource_calls_queue ON resource_calls(state,sequence);
CREATE INDEX resource_calls_run_queue ON resource_calls(run_id,state,sequence);
CREATE INDEX resource_calls_provider ON resource_calls(provider,permits_held);
CREATE TABLE resource_cursors(
  scope_id TEXT PRIMARY KEY NOT NULL,
  last_run_id TEXT REFERENCES resource_runs(run_id),
  last_allocation_id TEXT REFERENCES resource_allocations(allocation_id),
  CHECK((scope_id='global' AND last_allocation_id IS NULL) OR
        (scope_id!='global' AND last_run_id IS NULL)));
CREATE TABLE resource_usage_projection(
  call_id TEXT PRIMARY KEY NOT NULL REFERENCES resource_calls(call_id),
  ledger_id INTEGER NOT NULL UNIQUE REFERENCES ledger(id));
"""
