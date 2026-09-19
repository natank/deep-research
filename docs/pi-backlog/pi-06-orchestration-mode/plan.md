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

- Add a typed orchestration-mode selection to the frontend.
- Accept and validate the selected mode at the `/research` boundary.
- Preserve the selected mode in the run context for later metrics and agent
  execution.
- Keep Code as the currently executable reference path.
- Make Agent selection explicit and fail clearly until PI-08 implements it;
  never silently fall back from Agent to Code.
- Preserve clarification context and topic-only compatibility.
- Add backend and frontend tests for mode validation, propagation, and
  selection behavior.

### Out of scope

- Implementing agent tools or agent orchestration (PI-07 and PI-08).
- Adding comparison execution or metrics collection (PI-10 and PI-11).
- Changing Planner, Searcher, Writer, or Emailer semantics for Code mode.
- Allowing the browser to choose model names, providers, API clients,
  execution limits, or tool permissions.
- Persisting run history or user preferences.
- Authentication, rate limiting, or public-deployment abuse controls.

## Documentation rigor

**Required level: high.**

Mode selection crosses the UI/API boundary and controls a security- and
cost-sensitive execution decision. An invalid or silently ignored mode could
cause users to believe they tested Agent orchestration while the app actually
ran Code. The plan therefore requires enum validation, explicit unsupported-mode
behavior, no fallback, immutable request state during execution, and tests
covering both topic-only and clarified runs.

## Requirements

### Mode contract

Use the PI-01 `OrchestrationMode` enum:

- `code`: the existing Planner → Searcher → Writer → Emailer path;
- `agent`: the future LLM-directed path implemented by PI-08.

`/research` must accept an optional `orchestration_mode` field with a
server-owned default of `code` for existing topic-only clients. Unknown mode
strings must return HTTP 422 before any external call. Extra fields such as
`model`, `provider`, `client`, `api_key`, `limits`, or `tools` must be ignored
or rejected without changing server behavior; they are not part of the
contract.

The selected mode must be represented by the typed run/context state rather
than an arbitrary string. It must remain stable for the duration of a run.

### User flow

1. The user enters a topic.
2. The user selects **Code** or **Agent**.
3. The selected mode is retained while clarification is checked and, if
   needed, while answers are collected.
4. The frontend sends the frozen topic, clarification answers, and selected
   mode to `/research`.
5. Code mode runs the existing flow.
6. Agent mode returns an explicit, generic “Agent orchestration is not
   available yet” response until PI-08 implements execution. It must not
   execute Code mode as a fallback.

The UI must prevent mode changes while a clarification or research request is
in flight. Starting over resets mode to the documented default.

### Error behavior

- Invalid mode input returns 422 without OpenAI, Tavily, or report I/O.
- Agent mode before PI-08 returns a deliberate unsupported-mode response,
  preferably HTTP 501 with a generic body.
- Provider or pipeline failures retain the existing generic 502 behavior.
- Errors and logs must not include topic, question text, answers, API keys, or
  provider details.

## Proposed design

Extend the backend research request with:

```python
orchestration_mode: OrchestrationMode = OrchestrationMode.CODE
```

Build a `ResearchRun` or equivalent typed execution object from the validated
`ResearchContext` and selected mode. Keep `ResearchContext` responsible for
topic/Q&A validation and use `OrchestrationMode` for dispatch. PI-08 can later
replace the Agent unsupported branch with an agent orchestrator without
changing the public request shape.

Extend the frontend API adapter and types with `OrchestrationMode`. Add an
accessible radio group or select control near the topic form. Keep the choice
in React state and pass it through the clarification session so answers cannot
reset it. The adapter must construct the request; `App.tsx` must not send
provider or execution settings.

For the pre-PI-08 Agent response, use a stable typed/API error mapping so the
UI explains that the mode is not available yet and offers Code or Start over.
Do not present an Agent result as successful research.

## Success criteria

- Users can select Code or Agent before starting a run.
- Selected mode survives clarification and is sent to `/research`.
- Existing topic-only requests default to Code and behave unchanged.
- Invalid modes are rejected before external calls.
- Code mode continues to use the existing pipeline.
- Agent mode before PI-08 fails explicitly without Code fallback.
- Mode cannot change during an active clarification or research request.
- Clarification answers remain associated with the selected mode.
- No browser-controlled provider, model, client, limits, or tools are accepted.
- Frontend and backend tests cover mode selection, propagation, validation,
  unsupported Agent behavior, and existing report rendering.

## Test plan

### Backend

Cover at least:

- topic-only request defaults to `code`;
- explicit `code` request runs the existing pipeline;
- explicit `agent` request returns the unsupported response without running
  Planner, Searcher, Writer, or Emailer;
- invalid mode returns 422 before external calls;
- mode survives with valid clarification answers;
- extra provider/control fields do not change mode or execution;
- failures remain generic and do not leak research context.

### Frontend

Cover at least:

- Code and Agent controls render with an accessible label;
- selected mode is sent to `/research`;
- selected mode survives the clarification question state;
- mode controls are disabled during clarify and research requests;
- Agent unsupported response is shown without rendering a report;
- topic-only/no-question flow defaults to Code;
- starting over resets the mode to Code.

## Delivery plan

1. Extend the validated research request and run dispatch contract with
   `OrchestrationMode`.
2. Add explicit unsupported-Agent handling without Code fallback.
3. Add frontend mode state, accessible control, and API payload support.
4. Preserve mode through clarification and answer submission.
5. Add backend and frontend tests for validation, propagation, and unsupported
   behavior.
6. Run full backend tests/lint and frontend tests/lint/build.
7. Update this plan with implementation notes and completed exit criteria.
8. Open the PI-06 pull request once all exit criteria are complete.

## Exit criteria

- [ ] `/research` accepts a validated orchestration mode with a Code default.
- [ ] Mode propagates through clarification and research submission.
- [ ] Code mode remains backward compatible.
- [ ] Agent mode fails explicitly before PI-08 and never falls back to Code.
- [ ] Mode and provider-control validation occur before external calls.
- [ ] Frontend mode control and locked states are complete.
- [ ] Backend and frontend tests cover selection, propagation, validation, and
      unsupported behavior.
- [ ] Full backend tests/lint and frontend tests/lint/build pass.
- [ ] No secrets or unrelated story changes are included.
- [ ] This plan reflects the final mode contract and residual risks.
- [ ] Pull request is opened from `pi-06-orchestration-mode` and links to this
      document.
