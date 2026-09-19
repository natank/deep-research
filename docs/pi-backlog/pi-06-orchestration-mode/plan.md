# PI-06 Plan: User-Selected Orchestration Mode

## Story

**As a researcher, I want to choose Code or Agent orchestration for my run, so
that I can control how the research workflow is executed and later compare the
two approaches.**

**Story type:** Feature  
**Priority:** Must  
**Dependencies:** PI-01, PI-05  
**Branch:** `pi-06-orchestration-mode`

## Scope

### In scope

- Add a typed Code / Agent control to the frontend and keep the choice with
  the clarification session (frozen topic and answers).
- Accept optional `orchestration_mode` on `POST /research` using PI-01
  `OrchestrationMode`, defaulting to `code`.
- Dispatch on a server-built `ResearchRun`: Code runs the existing pipeline;
  Agent returns a typed 501 until PI-08. Never fall back from Agent to Code.
- Keep `/clarify` topic-only. Mode must not change clarification behavior.
- Keep `ResearchContext` as topic plus Q&A only. Mode is dispatch metadata
  and must not enter Planner or Writer prompts.
- Preserve topic-only clients and existing Code-path semantics.
- Add backend and frontend tests for validation, dispatch, propagation, and
  unsupported Agent behavior.

### Out of scope

- Agent tools, the agent loop, or replacing the 501 branch with execution
  (PI-07 and PI-08). This story’s Agent path must perform no OpenAI, Tavily,
  or report I/O.
- Honoring client-supplied `limits`, `tools`, `model`, `client`, `provider`,
  or `api_key`. Those fields stay off the public request. PI-08 must keep
  `ExecutionLimits` server-owned; unauthenticated Agent will be a cost
  switch then, not in this PR.
- Comparison runs or metrics (PI-10 and PI-11). Do not add a `compare` mode.
- Changing Planner, Searcher, Writer, or Emailer semantics for Code mode.
- Persisting run history or user preferences.
- Authentication, rate limiting, or public-deployment abuse controls.

## Documentation rigor

**Required level: high.**

Mode selection is the UI/API switch for a later, more expensive execution
path. A silent Agent→Code fallback would falsify the comparison study. A
request body dumped into `ResearchRun` would let PI-08 pick up client
limits. The plan therefore freezes the allowlisted body, server-owned
limits, dispatch-before-I/O, a distinct 501 vs 502 mapping, and tests that
Agent never calls the Code pipeline.

## Requirements

### Request contract

`POST /research` accepts only:

```json
{
  "topic": "artificial intelligence in education",
  "clarification_answers": [],
  "orchestration_mode": "code"
}
```

- `clarification_answers` optional, default `[]` (PI-05 rules unchanged).
- `orchestration_mode` optional, default `code`, type `OrchestrationMode`
  (`code` | `agent`). Unknown strings, including `compare`, return HTTP 422
  before any external call.
- Extra keys are ignored (`extra="ignore"`). The request model must not
  declare `limits`, `tools`, `model`, `client`, `provider`, or `api_key`.
  Those values must not appear on the `ResearchRun` used for dispatch.

`/clarify` remains `{ "topic": string }`. If a client sends
`orchestration_mode` there, ignore it; clarification must not depend on
mode.

### Run construction and dispatch

Keep `ResearchContext` responsible for topic and Q&A validation. After that
succeeds, build:

```text
ResearchRun(
  context=validated_context,
  orchestration_mode=mode,
  limits=ExecutionLimits(),   # server defaults only
)
```

Do not `ResearchRun(**request.model_dump())`. Mode is not a field on
`ResearchContext` and must not be passed into `format_research_context` or
any Planner/Writer `input`.

Dispatch order:

1. Validate the request (context + mode) with no provider I/O.
2. If `agent`, raise a typed `UnsupportedOrchestrationMode` (or equivalent)
   and map it to HTTP 501 with the fixed body
   `"Agent orchestration is not available yet"`. Catch this **before** the
   generic `Exception → 502` handler. Do not call Planner, Searcher, Writer,
   or Emailer.
3. If `code`, call the existing `run_research(context)` path.

Invalid mode is 422, not 501. Pipeline failures stay 502
`"Research failed, please try again"` with type-only logs and `from None`.
Logs may record the enum value `code`/`agent`; they must not record topic,
questions, answers, API keys, or provider `__cause__`.

PI-08 should replace only step 2’s 501 with the agent orchestrator, still
using server-owned limits. It must not start reading limits or tools from
the request.

### User flow

1. The user enters a topic and selects **Code** or **Agent** (default Code).
2. The app calls `/clarify` with the topic only. The selected mode is stored
   on the clarification session next to the frozen topic, not only on a live
   radio binding.
3. If questions are returned, the user answers them. Changing mode on that
   screen is allowed until research is submitted; the **submitted** mode is
   what the server runs. Controls are disabled while clarify or research is
   in flight so a request already sent cannot change mode.
4. The adapter sends `{ topic, clarification_answers?, orchestration_mode }`
   to `/research`. `App.tsx` does not assemble provider fields.
5. Code mode runs the existing flow and may render a report.
6. Agent mode shows the 501 message and must not set a report. Offer Code or
   Start over. Start over resets mode to `code`.

## Proposed design

Stop treating `ResearchRequest` as a bare `ResearchContext` alias. Give the
HTTP model the three public fields above and map them into `ResearchContext`
plus `OrchestrationMode`. Build `ResearchRun` in the handler as specified.

Add `UnsupportedOrchestrationMode` (or a similarly small error type) so 501
cannot be swallowed as 502.

On the frontend, extend the API adapter and types with `OrchestrationMode`.
Add an accessible radio group or select near the topic form. Persist the
choice on the clarification session. Disable the control during `checking`
and `loading`. The adapter allowlists the JSON body.

## Success criteria

- Users can select Code or Agent before starting a run.
- Selected mode is stored with the session, sent to `/research`, and absent
  from `/clarify`.
- Topic-only requests default to Code and behave as today.
- Invalid modes 422 before external calls.
- Code mode uses the existing pipeline; mode is not in LLM prompts.
- Agent mode returns 501 with the fixed generic body, no pipeline calls, no
  report.
- `ResearchRun.limits` are server defaults even if the JSON includes
  `limits` or `tools`.
- Mode cannot change during an in-flight clarify or research request.
- Starting over resets to Code.
- Frontend and backend tests cover the cases below.

## Test plan

### Backend

Cover at least:

- topic-only request defaults to `code` and runs the existing pipeline;
- explicit `code` with clarification answers runs the pipeline with that
  context;
- explicit `agent` returns 501 and the fixed body, and does not call
  Planner, Searcher, Writer, or Emailer;
- invalid mode (including `compare`) returns 422 before external calls;
- extra `model`, `limits`, `tools`, or `api_key` do not change mode,
  execution, or `ResearchRun.limits`;
- `orchestration_mode` does not appear in Planner or Writer prompt input;
- `/clarify` with `orchestration_mode` still behaves as topic-only;
- pipeline failure remains generic 502 with no topic or answers in the body.

### Frontend

Cover at least:

- Code and Agent controls render with an accessible label; default is Code;
- selected mode is passed to `requestResearch` and not to
  `requestClarification`;
- selected mode survives the clarification question state;
- mode controls are disabled during clarify and research requests;
- Agent 501 is shown without rendering a report;
- starting over resets the mode to Code;
- research JSON allowlists topic, optional answers, and mode (no provider
  fields).

## Delivery plan

1. Split the research request from `ResearchContext`; add mode; build
   `ResearchRun` with server-owned limits.
2. Add typed unsupported-Agent handling (501) before the generic 502 path.
3. Add frontend mode state on the clarification session, accessible
   control, and allowlisted adapter payload.
4. Preserve mode through clarification submit; lock it while requests are
   in flight.
5. Add backend and frontend tests for validation, dispatch, extras, and
   501 vs 502.
6. Run full backend tests/lint and frontend tests/lint/build.
7. Update this plan with implementation notes and completed exit criteria.
8. Open the PI-06 pull request once all exit criteria are complete.

## Implementation notes

- Added an explicit `ResearchRequest` with only topic, clarification answers,
  and `orchestration_mode`; Pydantic ignores unrelated extra keys and the
  handler constructs a server-owned `ResearchRun`.
- Added dispatch-before-I/O with a typed unsupported Agent exception mapped to
  HTTP 501. Code continues to call the unchanged `run_research(context)`
  pipeline, while Agent never invokes a provider or pipeline component.
- Added a frontend Code/Agent radio group, persisted the selected mode in the
  clarification session, sent it only to `/research`, locked it during
  in-flight requests, and reset it to Code on start over.
- Validation passed: 60 backend tests, backend Ruff, 5 frontend tests,
  frontend lint, and frontend production build. The build retains the
  pre-existing bundle-size warning.

## Exit criteria

- [x] `/research` accepts allowlisted `orchestration_mode` with a Code
      default; extras cannot set limits or tools.
- [x] `ResearchContext` stays topic+Q&A; mode is dispatch-only and stays
      out of LLM prompts.
- [x] Mode is stored with the clarification session and sent only to
      `/research`.
- [x] Code mode remains backward compatible.
- [x] Agent mode returns typed 501 with no provider I/O and no Code
      fallback.
- [x] `/clarify` remains topic-only.
- [x] Frontend mode control, in-flight lock, 501 handling, and start-over
      reset are complete.
- [x] Backend and frontend tests cover selection, dispatch, extras, and
      unsupported behavior.
- [x] Full backend tests/lint and frontend tests/lint/build pass.
- [x] No secrets or unrelated story changes are included.
- [x] This plan reflects the final mode contract, including the PI-08
      unauthenticated-Agent cost residual.
- [ ] Pull request is opened from `pi-06-orchestration-mode` and links to
      this document.
