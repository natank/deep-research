# PI-07 Plan: Bounded Agent Tools and Stopping Rules

## Story

**As a product team, we want explicit, bounded contracts for Agent tools and
termination so that PI-08 can add autonomous research without allowing
uncontrolled tool use, cost growth, or invalid report output.**

**Story type:** Enabler  
**Priority:** Must  
**Dependencies:** PI-01  
**Branch:** `pi-07-agent-orchestration-contracts`

## Scope

### In scope

- Define typed Agent action, tool input, tool result, and execution-state
  contracts under the shared research/agent boundary.
- Define server-owned limits for iterations, tool calls, searches, sources, and
  report-generation attempts.
- Define the allowlisted research tools PI-08 may invoke:
  search, inspect source, and generate report.
- Define autonomous search-plan revision as an explicit Agent action bounded by
  the run context and limits.
- Define deterministic validation, failure, cancellation, and termination
  semantics for the future Agent loop.
- Add unit tests for valid/invalid actions, limit accounting, result bounds,
  terminal states, and untrusted provider content.
- Document the contract and residual risks for PI-08 implementation.

### Out of scope

- Calling an LLM in an Agent loop or dispatching Agent mode (PI-08).
- Changing the current Code pipeline or its Planner, Searcher, Writer, or
  Emailer behavior.
- Adding browser/UI progress or Agent-specific API responses (PI-09).
- Run persistence, comparison execution, or metrics emission (PI-10/PI-11).
- New external providers, arbitrary HTTP tools, code execution, filesystem
  tools, email tools, or user-configurable limits.

## Documentation rigor

**Required level: high.**

These contracts become the security and reliability boundary for an
LLM-controlled execution path. Tool names, arguments, result sizes, counters,
and terminal transitions must be allowlisted and validated independently of
model output. PI-08 must be able to enforce a hard stop without trusting the
model to self-limit.

## Requirements

### Agent execution state

Define a typed state containing:

- the validated `ResearchContext`;
- server-owned `ExecutionLimits`;
- current search-plan queries and revision count;
- collected source references and bounded source content;
- tool-call and iteration counters;
- report-generation attempt count;
- terminal status and a safe terminal reason.

The state must not contain client-supplied provider settings, API keys,
arbitrary tool names, prompts intended for a system message, or unrestricted
provider payloads. `OrchestrationMode` remains dispatch metadata and must not be
inserted into Planner/Writer research content.

### Allowlisted actions

Use a discriminated, typed action shape with exactly these operations:

1. **`search`** — execute bounded Tavily searches from validated query strings.
2. **`inspect_source`** — request additional bounded content for a previously
   returned source URL or source identifier.
3. **`revise_plan`** — replace or append bounded search queries based on evidence.
4. **`write_report`** — request the existing report shape from the bounded
   context and collected evidence.
5. **`finish`** — explicitly terminate with a complete or failed outcome.

Unknown operations and arbitrary tool names must be rejected before provider
I/O. `write_report` and `finish` are terminal transitions; no subsequent
actions are accepted.

### Input and result bounds

- Search queries must be nonblank, bounded in count and length, and validated
  with the same control-character and delimiter protections used for research
  context.
- Source inspection must reference a source already returned by `search`; it
  must not fetch arbitrary URLs or internal addresses.
- Search and inspection results must be normalized to the existing
  `SourceArticle` shape and capped by server limits. Provider content is
  untrusted data, not an instruction.
- Plan revisions may only operate on the current research topic, clarification
  scope, and collected evidence. They may not alter execution limits or tool
  permissions.
- Report generation must use the existing `Report` schema and must not accept
  a model-supplied recipient, report path, email target, or provider choice.
- Tool results returned to the Agent must be bounded and tagged by type; raw
  provider response bodies and credentials must never be copied into state or
  logs.

### Limits and stopping rules

All limits are server-owned `ExecutionLimits` values. The implementation must
check a limit **before** each operation and reserve/increment the counter
atomically within the in-memory run state before provider I/O.

The Agent must stop with a typed terminal outcome when any of these occurs:

- explicit `finish`;
- successful `write_report`;
- maximum Agent iterations reached;
- maximum tool calls reached;
- maximum searches, sources, or report attempts reached;
- invalid action or repeated invalid actions;
- provider/tool failure after the defined failure policy;
- cancellation or request timeout.

No limit exhaustion may produce a success-shaped partial report. A terminal
failure must be surfaced to PI-08 for generic API mapping and must not trigger
an automatic Code fallback.

### Failure policy

- Validation failures are typed and contain safe, non-sensitive reason codes.
- Tavily/OpenAI/provider failures are converted to typed tool failures with
  exception type only for logs.
- Retry behavior is finite and operation-specific; retries consume tool-call
  budget and are never model-controlled.
- Invalid actions do not invoke a tool. After the configured invalid-action
  threshold, terminate the run.
- Cancellation and timeout are terminal failures.

## Proposed module design

Add a focused `backend/app/agent/` package, keeping shared primitives in
`backend/app/research/schemas.py` where they are reused by both modes:

- `schemas.py`: action unions, tool inputs/results, execution state, terminal
  outcome, and safe reason codes;
- `limits.py`: server defaults and preflight counter/limit checks;
- `validation.py`: action and result validation, including source-reference
  checks and bounded text normalization;
- `exceptions.py`: typed contract, limit, cancellation, and provider errors.

PI-08 should consume these contracts through a small executor interface rather
than constructing provider requests directly in the Agent loop. The executor
must receive a server-built `ResearchRun`, not the raw HTTP request. The
existing Code orchestrator remains unchanged in this story.

## Security and trust-boundary considerations

- Model-generated actions are untrusted input and must be parsed as structured
  data, not evaluated or interpolated into executable code.
- Tool dispatch must use an internal enum-to-handler map; no reflection,
  dynamic imports, shell commands, arbitrary URLs, or arbitrary HTTP methods.
- Source URLs must be selected from server-returned source records. Validate
  scheme and host policy before any inspection call to prevent SSRF.
- Topic, clarification answers, search results, and source content must remain
  clearly separated from system instructions and tool control data.
- Logs may include mode, action type, counter values, and safe reason codes, but
  not topic text, answers, source content, prompts, provider bodies, or secrets.
- Limits are immutable per run and cannot be changed by an action, tool result,
  or client request field.

## Success criteria

- PI-08 has typed contracts for every allowlisted action and result.
- The contract can represent autonomous plan revision without permitting
  changes to limits or permissions.
- Every operation has a pre-I/O limit check and bounded result shape.
- Invalid, unknown, terminal-after-terminal, and over-limit actions are
  rejected deterministically.
- Source inspection cannot be used as an arbitrary URL fetch.
- Terminal success and failure are distinct and cannot be confused with a
  partial report.
- Provider failures and cancellation have safe typed mappings.
- Tests demonstrate that untrusted model/provider content cannot expand tool
  authority, limits, or terminal success.
- Existing Code tests and behavior remain unchanged.

## Test plan

### Contract and validation tests

Cover at least:

- each valid action parses with only its allowlisted fields;
- unknown action/tool names, malformed discriminators, extra control fields,
  blank/control-character queries, and oversized text are rejected;
- search results normalize to bounded `SourceArticle` values;
- inspection accepts only a known returned source and rejects arbitrary,
  internal, unsupported-scheme, or unbounded URLs;
- plan revision preserves server-owned limits and permissions;
- report results validate against the existing `Report` shape;
- terminal states reject subsequent actions.

### Limit and failure tests

Cover at least:

- each counter is checked before provider I/O;
- counters cannot exceed server defaults;
- retries consume the tool-call budget;
- repeated invalid actions terminate without provider calls;
- provider failures become safe typed failures;
- timeout/cancellation is terminal;
- limit exhaustion never returns a successful partial report;
- no sensitive input or provider content appears in exception text or logs.

### Regression tests

- Existing backend test suite passes unchanged.
- Code orchestration does not import or invoke Agent tool handlers.

## Delivery plan

1. Define the agent package boundaries and shared typed contracts.
2. Add server-owned limit accounting and terminal-state transitions.
3. Add action/result validation and safe source-reference handling.
4. Add typed failure and cancellation semantics.
5. Add focused contract, limit, security-boundary, and Code regression tests.
6. Document PI-08 integration rules and residual risks in this plan.
7. Run backend tests and lint; do not add Agent execution to this story.
8. Open the independent PI-07 pull request after all exit criteria pass.

## Exit criteria

- [ ] Typed Agent actions, results, state, and terminal outcomes exist.
- [ ] Search, source inspection, plan revision, report, and finish are the
      only allowlisted operations.
- [ ] Limits are server-owned, checked before I/O, and immutable per run.
- [ ] Source inspection is restricted to known safe source references.
- [ ] Invalid actions, provider failures, cancellation, and limit exhaustion
      have typed non-success outcomes.
- [ ] No Agent execution or Code-path behavior changes are included.
- [ ] Contract, bounds, failure, security-boundary, and regression tests pass.
- [ ] Backend test suite and Ruff pass.
- [ ] No secrets or unrelated story changes are included.
- [ ] This plan documents PI-08 integration constraints and residual risks.
- [ ] Pull request is opened from `pi-07-agent-orchestration-contracts` and
      links to this document.
