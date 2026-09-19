# PI-09 Plan: Integrate Agent Mode into the End-to-End UI

## Story

**As a researcher, I want Agent runs to have clear progress, failure, and
results behavior in the same UI as Code runs, so that Agent mode is usable by
all users rather than only being an API capability.**

**Story type:** Feature  
**Priority:** Must  
**Dependencies:** PI-06, PI-08  
**Branch:** `pi-09-agent-ui-integration`

## Scope

### In scope

- Make Code/Agent an explicit end-to-end choice now that Agent execution
  exists, with static descriptions (not copy from the API).
- Show honest, mode-specific loading copy during clarification and the
  synchronous research request. No fabricated iterations, tools, or
  percentages.
- Keep a **single** in-flight `/research` fetch. Retry, submit, and start
  over must not start a second research call until that fetch has settled.
- Preserve mode, frozen topic, and answers through questions, errors, and
  explicit retry. Retry does not call `/clarify`.
- Parse `ResearchResult` before paint; ignore stale responses after abort
  or start over.
- Render Agent results through the same report, sources, chart, email, and
  download path as Code (text nodes; no `source.content` body).
- Add frontend tests for payloads, loading, abort/retry, malformed
  responses, and shared rendering.

### Out of scope

- Streaming, polling, a job API, or server-side cancellation. Aborting the
  fetch does **not** stop the PI-08 worker. Do not add a UI control that
  looks like cancel.
- Auto-retry on timeout or 502.
- Run metrics, comparison mode, history, or persisted mode (PI-10/PI-11).
- Changes to Agent limits, tools, prompts, or the Code pipeline.
- Client interpretation of tool names, source snippets, reason codes, or
  provider errors. Do not special-case HTTP 501 as “not implemented.”
- Authentication, rate limiting, or deployment abuse controls.
  Unauthenticated Agent is now a button for every user; server caps remain
  the cost bound.

## Documentation rigor

**Required level: medium-high.**

The UI is how all users spend Agent budget. It must not claim progress it
cannot observe, expose internals, paint a report from a bad or stale 200,
or imply that abort cancelled the server. Retry is another paid run.

## Requirements

### Mode selection

- Default **Code**. Labels: **Code orchestration** and **Agent
  orchestration**, plus a short static note (fixed workflow vs adaptive
  search). Accessible radio group.
- Mode may change on the questions screen. Once `/research` is in flight,
  topic, mode, and submit are frozen.
- Send mode only through `requestResearch`. `/clarify` stays `{ topic }`.
- Start over resets mode to Code and clears topic, answers, result, error,
  and any last-payload / in-flight generation.

### In-flight research

Exactly one research request at a time:

- Disable Research, Retry, mode, and topic while `checking` or `loading`.
- Do not add a second `AbortController` “cancel.” Keep the existing adapter
  timeout (do not shorten it for Agent).
- When that timeout aborts, treat it as failure **and** say the server may
  still be finishing. Retry is a **new** paid run, not resume or cancel.
- Tie each `/research` call to a generation id. After abort or start over,
  ignore a late 200 so an abandoned Agent result cannot paint.

Retry payload is only `{ topic, clarification_answers?, orchestration_mode }`
from the last submitted (frozen topic, current answers, selected mode). No
`limits`, `model`, `tools`, or `api_key`. One submit per click; no loop.

### Progress copy

Synchronous backend, no step events. Phase-level copy only:

- clarification: “Checking whether your topic needs clarification…”
- Code: planning, gathering sources, and writing;
- Agent: “Agent is researching, adapting its search plan, and writing your
  report…” plus that this can take up to a minute.

`aria-live="polite"`. No tool names, counters, or completion predictions.

### Success and failure

- Non-2xx, abort, and parse failure: generic alert, `result` stays null.
  Use string `detail` only when it is a string (existing `ApiError` rule).
  Never show reason codes, prompts, URLs, source bodies, or 501-specific
  “not available” copy.
- Parse `ResearchResult` before `setResult` (required report fields, email
  `report_id` / status). Malformed 200 → generic failure, no success state.
- Preserve the clarification panel and answers after a **research**
  failure so the user can retry or change mode. Clarification failure:
  start over.
- Start over after failure returns to Code-default empty state.

### Shared rendering

One report path for both modes:

- topic, summary, insights, chart title as React text nodes;
- sources: title as text, `href={url}` as today (optional shared `http:` /
  `https:` filter; no Agent-only list);
- do **not** render `source.content`;
- same email line and `/reports/{report_id}` download.

No Markdown, `dangerouslySetInnerHTML`, or model-provided `src`/`style`.

## Proposed design

Update `App.tsx`:

- keep typed `OrchestrationMode` on the clarification session;
- derive loading copy from `runState` + mode;
- hold `inFlightGeneration` (or equivalent) and last allowlisted payload;
- shared report JSX as today.

Update `api.ts` with a `ResearchResult` parser analogous to clarification
parsing. Do not add provider-specific status handling.

Styles for mode descriptions, progress, retry, and abort copy; report
layout unchanged. No backend contract changes. If the backend must change,
keep PI-08 shapes and generic 502s.

## Residual risks

- Frontend abort does not cancel the worker; a report may still be emailed
  after the UI gave up.
- Retry after abort can overlap that still-running loop (second spend).
  Copy must not claim otherwise; in-flight locking only prevents a second
  fetch from **this** page until the first fetch object settles.
- Unauthenticated Agent is a main-button cost switch; caps are server-side.
- Source `href` values remain Tavily URLs (same as Code).

## Success criteria

- All users can run Agent from the existing UI.
- Honest mode-specific progress; same final report experience as Code.
- Mode and answers survive the flow; retry does not re-clarify.
- Failures are generic, never a partial report, never 501-as-unimplemented.
- Malformed or stale 200s do not paint a report.
- No second `/research` while one fetch is in flight; abort copy does not
  claim cancel.
- Start over clears all run state and resets Code.
- Existing Code behavior remains unchanged.

## Test plan

### Mode and clarification

- Code default; sent on a clear topic.
- Agent sent only to `/research`, not `/clarify`.
- Agent survives questions and answer submit.
- Mode enabled on questions, disabled during requests.
- Start over resets mode, topic, answers, result, errors, and generation.

### Progress, abort, errors

- Distinct honest Code vs Agent loading copy.
- 502/generic failure: alert, no report, preserved topic/mode/answers.
- Abort: generic failure plus “server may still be finishing”; Retry is
  explicit and allowlisted; no auto-retry.
- Submit/Retry disabled while loading; cannot stack two research fetches.
- Malformed 200 does not set a report; stale 200 after start over is
  ignored.

### Shared results and regression

- Agent `ResearchResult` renders summary, insights, chart, source titles
  and links, email, download — no `source.content`.
- Existing Code tests stay green.
- Frontend tests, lint, and production build pass.

## Delivery plan

1. Mode labels/descriptions and frozen in-flight state.
2. Honest loading copy; generation id for stale responses.
3. `ResearchResult` parser; explicit retry of the allowlisted payload.
4. Abort copy; tests for success, failure, malformed/stale, no stacked
   fetches.
5. Frontend tests/lint/build; backend regression.
6. Update this plan with implementation notes and exit criteria.
7. Open the PI-09 pull request after exit criteria pass.

## Exit criteria

- [x] Agent mode is usable end to end for all users.
- [x] Mode and clarification state survive selection, questions,
      submission, success, failure, retry, and start over.
- [x] Progress copy is phase-accurate without Agent internals.
- [x] Failures are generic; no partial or stale reports; no 501 special
      case.
- [x] Retry is explicit, allowlisted, does not re-clarify, and cannot
      start while a fetch is in flight.
- [x] Abort does not claim the server stopped.
- [x] Shared Code/Agent report rendering does not show source bodies.
- [x] Accessible controls and loading/error states are complete.
- [x] Frontend tests/lint/build and backend regression tests pass.
- [x] Residual sync-request limitations are documented.
- [x] No secrets or unrelated story changes are included.
- [ ] Pull request is opened from `pi-09-agent-ui-integration` and links
      to this document.

## Implementation notes

- Added explicit Code/Agent orchestration labels and static descriptions,
  honest mode-specific synchronous loading copy, and accessible progress/error
  states.
- Added an allowlisted `ResearchResult` parser that validates report, chart,
  source-link, and email fields before updating UI state. Source bodies remain
  unrendered.
- Added frozen research payload tracking, explicit retry without re-running
  clarification, single-fetch protection, and generation checks that ignore
  late responses after start over.
- Timeout copy states that the server may still be finishing; the UI does not
  claim that abort cancels the backend worker. No automatic retry was added.
- Validation passed: 10 frontend tests, frontend lint, frontend production
  build, and the backend regression suite. The existing Vite bundle-size and
  Starlette/httpx deprecation warnings remain non-blocking.
