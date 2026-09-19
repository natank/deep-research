# PI-08 Plan: Implement Bounded Agent Orchestration

## Story

**As a researcher, I want Agent mode to autonomously revise searches, inspect
evidence, and produce the same report shape as Code mode, so that I can benefit
from adaptive research without unbounded execution.**

**Story type:** Feature  
**Priority:** Must  
**Dependencies:** PI-05, PI-07  
**Branch:** `pi-08-agent-orchestration`

## Scope

### In scope

- Replace PI-06's Agent 501 branch with a bounded server-side Agent loop.
- Use the PI-07 typed actions, source envelopes, counters, terminal outcomes,
  and failure reasons as the only execution contract.
- Let the Agent autonomously search, inspect known sources, revise the query
  list, and request report generation within server-owned limits.
- Use the existing OpenAI, Tavily, Writer, and Emailer services through narrow
  interfaces and preserve the existing `ResearchResult` shape.
- Return Agent reports through the same `/research` response and email/download
  behavior as Code mode.
- Add deterministic fake model/provider tests for action dispatch, bounds,
  retries, terminal states, clarification propagation, and no Code fallback.

### Out of scope

- Frontend progress, cancellation controls, or Agent-specific UX (PI-09).
- Run metrics, usage capture, or comparison execution (PI-10/PI-11).
- Changing Code orchestration or its prompts and provider behavior.
- Client-configurable limits, model/provider selection, tools, or API keys.
- New arbitrary HTTP, shell, filesystem, email, or code-execution tools.
- Persisting Agent state or resuming interrupted runs.

## Documentation rigor

**Required level: high.**

This story turns a user-selectable mode into a provider-driven execution path.
The Agent receives untrusted topic, clarification, and source content, and
produces untrusted structured actions. Every action must be parsed and
authorized before I/O; every counter must be reserved server-side; failures
must not become partial success or silently switch to Code. The existing Code
path is the protected reliability baseline.

## Requirements

### API and orchestration boundary

`POST /research` keeps the PI-06 allowlisted request body and builds a
server-owned `ResearchRun` with default `ExecutionLimits`. Dispatch is:

1. Validate context and mode before provider I/O.
2. Run the existing `run_research(context)` for Code.
3. Run `run_agent(run)` for Agent.
4. On Agent success, send the validated report through the existing Emailer
   and return the same `ResearchResult`.
5. Map any Agent failure to HTTP 502 with the existing generic body. Never
   fall back to Code and never return a report without a successful Agent
   terminal outcome.

The Agent path must not change `/clarify`, the request schema, report schema,
or the Code path's ordering.

### Agent loop

Build `AgentExecutionState` from the server-created run. Each model round:

- reserves one iteration before the model call;
- supplies a static system instruction describing the five operations and
  termination rules;
- supplies context, current bounded query plan, and bounded source envelopes
  in delimited user/tool content;
- parses exactly one PI-07 `AgentAction`;
- rejects invalid actions without provider/tool I/O and records the invalid
  action threshold;
- reserves the action's tool-call budget before invoking its handler;
- appends only typed, bounded tool results to the next model input.

The loop stops only on a validated `write_report` success or a typed failure.
`finish` without a prior validated report is failure. Iteration, action, source,
search, retry, report-attempt, and invalid-action limits are hard stops.

### Tool handlers

Implement a server-owned executor behind the PI-07 protocol:

- **Search:** call the configured Tavily client with a validated query and
  bounded result count; deduplicate URLs; assign opaque server `source_id`
  values; normalize to `SourceEnvelope`; reserve source capacity.
- **Inspect source:** look up the `source_id` in state, obtain its existing
  server-held URL, and call Tavily's bounded extract operation if available.
  The model never supplies a URL. Reject unknown IDs before network access.
- **Revise plan:** replace the query list only after PI-07 validation. Do not
  mutate context, limits, sources, permissions, or terminal state.
- **Write report:** call the existing writer with `ResearchContext` and
  server-held `SourceArticle` values reconstructed from envelopes. Ignore any
  model-supplied evidence, recipient, path, or provider settings. Validate the
  returned `Report` before terminal success.
- **Finish:** mark typed failure unless a validated report has already
  completed. No provider call is made.

If Tavily extract is unavailable in the installed client, source inspection
must fail with a typed provider failure rather than using a generic HTTP
fallback.

### Model integration

Use the configured OpenAI model only. Keep the system prompt static. Put topic,
clarification answers, search results, source content, and model-generated
plan data in explicitly delimited user/tool content. Treat all provider text as
untrusted data and do not place it in a system message.

Use a narrow model adapter in tests so the loop does not depend on live OpenAI
calls. The production adapter must request the strict PI-07 action wrapper and
reject missing or unparsable actions.

### Failure and retry behavior

- Retry a failed provider operation at most once; each retry reserves another
  tool call and is not selected by the model.
- Invalid actions never invoke a provider. After three invalid actions, fail
  with `invalid_action`.
- Provider failures, timeout, cancellation, limit exhaustion, and finish
  without a report map to typed non-success outcomes.
- Log only exception class, mode, operation, and safe reason code. Never log
  topic, answers, prompts, URLs, source content, provider bodies, or secrets.
- Preserve the existing generic 502 response and `from None` behavior at the
  API boundary.

## Proposed design

Add `backend/app/agent/service.py` containing:

- `AgentModel` protocol and production OpenAI adapter;
- `AgentProviderExecutor` implementing PI-07's `AgentToolExecutor`;
- `run_agent(run: ResearchRun) -> ResearchResult`;
- loop/action dispatch and safe provider failure mapping.

Keep action parsing and accounting in PI-07 modules. Extend the protocol only
where necessary to make source normalization and report conversion explicit.
Update `backend/app/orchestrator.py` with a separate `run_agent` entry point
and keep `run_research` unchanged. Have `main.py` select the Agent entry point
and email only after Agent report success.

## Security and reliability controls

- Construct Agent state only from validated `ResearchContext` and
  server-created `ResearchRun`; never from raw request dictionaries.
- Keep `ExecutionLimits` immutable by convention and exclude limits/tools/model
  from model-visible action schemas.
- Dispatch through a fixed operation-to-handler map; no reflection, dynamic
  imports, shell, arbitrary HTTP, or model-provided URLs.
- Use opaque source IDs and server-side lookup to prevent SSRF-style source
  inspection.
- Enforce counters before external calls, including failed calls and retries.
- Reconstruct writer sources from state, not from model output.
- Do not silently downgrade Agent failure to Code or return partial reports.

## Success criteria

- Agent mode performs a bounded adaptive research run and returns the existing
  `ResearchResult` shape on successful report generation.
- The Agent can revise queries and inspect previously found evidence while
  respecting all PI-07 limits.
- Clarification answers affect Agent scope but are never treated as sources or
  tool permissions.
- Agent failures are generic at the API boundary and do not leak sensitive
  input or provider details.
- Agent and Code use the same report/source/email/download contract.
- Existing Code tests and behavior remain unchanged.

## Test plan

### Agent loop

Cover at least:

- a fake model performs search → revise plan → search → write report;
- clarification context is passed to the Agent and writer;
- each action dispatches to only its allowlisted handler;
- malformed/unknown/extra-field actions make no provider call;
- `finish` without a validated report fails;
- only a validated `Report` yields terminal success;
- post-terminal actions are rejected.

### Bounds and failures

Cover at least:

- iteration, action, search, source, report-attempt, and retry limits stop
  before provider I/O;
- failed provider operations consume their reservation and retry at most once;
- three invalid actions fail without external calls;
- timeout, cancellation, provider failure, and limit failure map to safe 502;
- Agent failure never invokes `run_research` and never returns a report;
- logs and error bodies exclude topic, answers, source content, URLs, and
  provider bodies.

### Integration and regression

- `/research` with `orchestration_mode=agent` runs Agent and then Emailer only
  after successful report generation.
- topic-only requests still default to Code.
- Code pipeline tests, endpoint tests, frontend tests, lint, and build remain
  green.

## Delivery plan

1. Add production model and provider adapters around PI-07 contracts.
2. Implement bounded Agent loop and fixed action dispatch.
3. Implement Tavily search/source inspection and server source IDs.
4. Integrate Agent dispatch and post-success Emailer into `/research`.
5. Add focused Agent, endpoint, security-boundary, and regression tests.
6. Run backend and frontend validation.
7. Update this plan with implementation notes and completed exit criteria.
8. Open the independent PI-08 pull request after all exit criteria pass.

## Exit criteria

- [ ] Agent mode executes a bounded loop and returns the existing result shape.
- [ ] Adaptive plan revision and known-source inspection work through PI-07
      contracts.
- [ ] Report generation is validated and Emailer runs only after success.
- [ ] Limits, retries, invalid actions, timeout, and provider failures stop
      safely before or at the defined boundary.
- [ ] Agent never falls back to Code and does not accept client controls.
- [ ] Clarification context is preserved as scope, not evidence.
- [ ] API errors/logs are generic and non-sensitive.
- [ ] Agent, endpoint, and regression tests pass.
- [ ] Backend and frontend tests/lint/build pass.
- [ ] No secrets or unrelated story changes are included.
- [ ] This plan documents final PI-08 behavior and residual risks.
- [ ] Pull request is opened from `pi-08-agent-orchestration` and links to
      this document.
