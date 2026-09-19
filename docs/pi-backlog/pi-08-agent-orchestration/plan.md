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

- Replace PI-06’s Agent 501 branch with a bounded server-side Agent loop.
- Use PI-07 actions, envelopes, counters, and terminal outcomes as the only
  execution contract. Copy `run.limits` from the server-built `ResearchRun`
  and do not mutate them.
- Parse exactly one PI-07 `AgentAction` per model round via structured
  output (no extra OpenAI tools).
- Search, inspect by `source_id` through Tavily extract only, revise the
  query list, and write a report only when `state.sources` is non-empty.
- Email once after `complete_report`, not as a tool. Return the existing
  `ResearchResult` shape.
- Add fake model/provider tests for dispatch, bounds, empty-source write,
  inspect-without-local-HTTP, retries, terminals, clarification as scope,
  and no Code fallback.

### Out of scope

- Frontend progress, cancellation controls, or Agent-specific UX (PI-09).
  This story has **no** public cancel route. A frontend abort does not stop
  the sync worker; residual cost runs until the loop hits a PI-07 limit
  (no extra server wall-clock deadline in this PR).
- Run metrics or comparison execution (PI-10/PI-11).
- Changing Code orchestration, its prompts, or provider behavior.
- Client-configurable limits, model, tools, or API keys.
- Local HTTP clients, shell, filesystem, or Emailer-as-tool. If Tavily
  extract is missing, inspect is a typed provider failure, not `httpx.get`.
- Persisting or resuming Agent state.

## Documentation rigor

**Required level: high.**

Agent mode is the first user-selectable path that follows model-chosen
tools and spends provider budget. Untrusted topic, Q&A, and Tavily text
must stay out of the system prompt. Actions must parse as PI-07 data
before I/O. Inspect must not become SSRF. A report without sources must
not count as success. Failures must not fall back to Code.

## Requirements

### API and orchestration boundary

`POST /research` keeps the PI-06 body
`{ topic, clarification_answers?, orchestration_mode? }` and builds:

```text
ResearchRun(context=validated_context, orchestration_mode=mode, limits=ExecutionLimits())
```

Dispatch:

1. Validate context and mode with no provider I/O.
2. Code → existing `run_research(context)` unchanged.
3. Agent → `run_agent(run)` using `run.limits`, never request `limits` /
   `tools` / `model`.
4. On terminal **success** only, call Emailer **once** and return
   `ResearchResult`. Do not email from a tool handler and do not email
   inside the loop.
5. Any Agent failure → HTTP 502 `"Research failed, please try again"` with
   `from None`. Never call `run_research`. Never return a report.

`/clarify` and the request/report schemas stay as they are.

### Agent loop

Build `AgentExecutionState` from `run.context` and a copy of `run.limits`.
Each model round:

1. `reserve_iteration` before the OpenAI call.
2. Static **module-level** system prompt: the five operations, stop rules,
   inspect-by-`source_id` only, answers are scope not sources, no extra
   tools. Do not interpolate topic, Q&A, snippets, or mode.
3. User/tool content only: `format_research_context`, current queries, and
   envelopes in delimited blocks (`<untrusted-…>`, `<research-sources>` or
   `<untrusted-tool-result>`). Server-owned cap numbers may appear as
   user text, not in the system prompt.
4. Production adapter: `responses.parse` (or equivalent) into **one**
   PI-07 `AgentAction`. Do not register other functions (no Emailer, HTTP,
   shell). Missing `output_parsed`, a list of length ≠ 1, or
   `extra="forbid"` failure → invalid action, no Tavily/Writer.
5. `reserve_action` then the fixed handler map.
6. Append only typed envelopes to the next user/tool turn.

Stop on `complete_report` (success) or a PI-07 typed failure. `finish`
without a report is failure.

### Tool handlers

Server-owned executor behind `AgentToolExecutor`. No reflection, no
dynamic imports, no `httpx`/`requests`/`urllib`.

- **Search:** `TavilyClient.search` with the validated query and the
  existing per-query result cap. Dedup by URL. Assign opaque server ids
  (`src_` + counter or uuid), never a URL hash. `normalize_source` +
  `add_sources`. Queries are not fetched as URLs.
- **Inspect:** `require_known_source(state, source_id)` then Tavily
  **extract** using the envelope’s stored URL as Tavily’s parameter only.
  The model never passes a URL. Unknown ids, extra `url` fields, and
  missing extract → typed failure and **zero** local HTTP calls. Optional:
  skip extract for non-https or private/link-local hosts (inspect
  failure, no call). Tavily extract of a stored URL is fetch-by-proxy
  residual, not app-side SSRF.
- **Revise plan:** `apply_plan_revision` (query list only).
- **Write report:** if `state.sources` is empty, treat as invalid action
  (no Writer, no Emailer). Otherwise reconstruct `SourceArticle`s from
  envelopes, call existing `write_report(context, sources)` with
  `format_research_context` and a separate sources block, validate
  `Report`, then `complete_report`. Ignore model-supplied evidence,
  recipient, path, or provider.
- **Finish:** `finish_without_report`; no provider call.

### Failure and retry

- At most one server-driven retry per operation; `reserve_retry`; not
  model-selected.
- Three invalid actions → `invalid_action` and stop, no provider I/O.
- Provider failure, limit exhaustion, finish-without-report, and
  `timed_out`/`cancelled` (if a later story maps a deadline) → typed
  failure → 502.
- Logs: exception class, mode, operation, reason code. Never topic,
  answers, prompts, URLs, source content, provider bodies, or secrets.

## Proposed design

Add `backend/app/agent/service.py`:

- `AgentModel` protocol and OpenAI adapter (`responses.parse` → one
  `AgentAction`);
- `AgentProviderExecutor` implementing PI-07’s protocol (Tavily search +
  extract, Writer from state);
- `run_agent(run: ResearchRun)` looping until terminal outcome;
- report+sources returned to the orchestrator, which emails once.

Keep parsing and counters in PI-07 modules. `run_research` stays
untouched. `main.py` chooses `run_agent` vs `run_research` and maps
Agent failures to 502 (the 501 branch goes away).

## Residual risks

- Unauthenticated Agent is a cost switch bounded only by PI-01 caps and
  PI-07 counters (5 iterations, 12 tool calls, 8 searches/sources). No
  server deadline in this story.
- Tavily snippets can still instruct the model; delimiters and roles
  constrain placement, not obedience.
- Tavily extract may fetch a URL that search stored, including a poor
  host, on Tavily’s side.
- Frontend abort does not cancel the in-flight loop.

## Success criteria

- Agent mode returns the existing `ResearchResult` only after a validated
  report from non-empty server-held sources, then one Emailer call.
- Inspect uses Tavily extract by `source_id` only; tests show no local
  HTTP client.
- `write_report` with empty sources fails without Writer/Emailer.
- Clarification answers are scope in delimited user content, not sources
  or permissions.
- The model adapter accepts only one PI-07 action per round.
- Agent failure is generic 502, never `run_research`, never a report.
- Code tests and behavior remain unchanged.

## Test plan

### Agent loop

- Fake model: search → revise → search → write report.
- First-action `write_report` fails; Emailer not called.
- Clarification context appears in user content and Writer input, not the
  system prompt.
- Each action hits only its handler; extra/unknown/malformed actions make
  no provider call.
- `finish` without a report fails; post-terminal actions are rejected.

### Bounds, inspect, failures

- Iteration, search, source, report-attempt, and retry limits stop before
  I/O.
- Inspect unknown id / extra `url` / extract-unavailable: no local HTTP
  import or GET.
- Three invalid actions fail with no Tavily/Writer.
- Failed provider call consumes reservation; at most one retry.
- Agent 502 body has no topic, answers, URLs, or provider text; Code path
  is not invoked.

### Integration and regression

- `orchestration_mode=agent` runs Agent and emails only after success.
- Topic-only requests still default to Code.
- Existing Code, endpoint, and frontend tests/lint/build stay green.

## Delivery plan

1. OpenAI adapter: structured parse to one `AgentAction`.
2. Executor: Tavily search, extract-only inspect, Writer from state,
   empty-source write rejected.
3. Loop: `reserve_iteration`, delimited prompts, `reserve_action`,
   dispatch, PI-07 terminals.
4. `main.py`: Agent dispatch, one Emailer after success, 502 on failure.
5. Tests as above.
6. Backend and frontend validation.
7. Update this plan with implementation notes and exit criteria.
8. Open the PI-08 pull request after exit criteria pass.

## Exit criteria

- [x] Agent loop returns the existing result shape after a sourced,
      validated report.
- [x] Inspect is `source_id` → Tavily extract only; no local HTTP fetch.
- [x] Empty-source `write_report` is not success; Emailer runs once after
      `complete_report`.
- [x] One PI-07 action per round; extra tools are not registered.
- [x] Limits, retries, invalid actions, and provider failures stop at
      PI-07 boundaries.
- [x] Agent never falls back to Code and does not accept client controls.
- [x] Clarification is scope in delimited user content.
- [x] API errors/logs are generic and non-sensitive.
- [x] Residual risks above are unchanged in the implementation notes.
- [x] Agent, endpoint, and regression tests pass.
- [x] Backend and frontend tests/lint/build pass.
- [x] No secrets or unrelated story changes are included.
- [ ] Pull request is opened from `pi-08-agent-orchestration` and links to
      this document.

## Implementation notes

- Added a structured OpenAI Agent adapter that parses exactly one
  `AgentDecision` containing a PI-07 action per round. The system prompt is
  module-level and dynamic research context is delimited user content.
- Added a fixed executor for Tavily search/extract and existing Writer
  integration. Search assigns opaque source IDs; inspect resolves only known
  IDs and never performs local HTTP. Empty-source report attempts are rejected.
- Replaced the PI-06 Agent 501 branch with bounded Agent execution. Successful
  validated reports are emailed exactly once after terminal completion; Agent
  failures map to generic 502 and never invoke Code orchestration.
- Added fake-model/provider and endpoint coverage for adaptive execution,
  clarification scope, sourced-report requirements, no fallback, and generic
  failures. Validation passed: 86 backend tests, Ruff, frontend tests, lint,
  and production build. The existing Vite bundle-size warning remains
  non-blocking.
- Residuals remain as planned: unauthenticated Agent cost is bounded by
  counters but has no wall-clock deadline, Tavily content can still attempt
  prompt injection despite delimiters, Tavily may fetch stored URLs on its
  side, and frontend abort does not cancel the synchronous worker.
