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

- Make the existing Code/Agent selection an explicit, understandable
  end-to-end choice now that Agent execution is available.
- Show mode-appropriate loading/progress copy during clarification and the
  synchronous research request.
- Preserve selected mode through clarification, submission, errors, and
  retry/start-over behavior.
- Surface generic Agent failures with actionable recovery while preserving
  answer state where safe.
- Render Agent results through the same report, sources, chart, email status,
  and download experience as Code.
- Add frontend API/UI tests for mode payloads, loading states, errors, retries,
  and identical report rendering.

### Out of scope

- Streaming progress, polling, a job API, or server-side cancellation. PI-08
  intentionally uses a synchronous request with no public cancel route.
- Run metrics, comparison mode, history, or persisted mode preferences
  (PI-10/PI-11).
- Changes to Agent limits, tools, prompts, provider behavior, or the Code
  pipeline.
- Client-side interpretation of Agent internals, tool names, source content,
  or provider errors.
- Authentication, rate limiting, or deployment abuse controls.

## Documentation rigor

**Required level: medium-high.**

This story changes the user-visible behavior of a high-cost, model-directed
path. The UI must not claim granular progress it cannot observe, expose
provider details, or imply that a failed Agent run produced a report. Mode and
clarification state must remain consistent across async transitions, and
controls must prevent duplicate submissions.

## Requirements

### Mode selection

- Keep Code as the default.
- Label the choices clearly as **Code orchestration** and **Agent
  orchestration**, with concise descriptions of predictable fixed workflow
  versus adaptive search decisions.
- Keep the control accessible as a labeled radio group.
- Allow mode changes while the clarification form is displayed, but freeze the
  submitted mode once research starts.
- Do not send mode to `/clarify`; send it only through the typed `/research`
  adapter.
- Starting over resets mode to Code and clears the previous result/error.

### Progress and loading

The backend is synchronous and exposes no step events. Show honest
phase-level copy only:

- clarification check: “Checking whether your topic needs clarification…”
- Code run: planning, gathering sources, and writing;
- Agent run: “Agent is researching, adapting its search plan, and writing
  your report…” with a note that this may take up to a minute.

Use `aria-live="polite"` for progress and disable topic/mode/submit controls
while the corresponding request is in flight. Do not display fabricated
iteration counts, tool names, percentages, or completion predictions.

### Success and failure

- A successful Agent response uses the existing `ResearchResult` rendering
  without a separate report component or alternate source format.
- Show the same email status and download link for both modes.
- Treat any non-2xx Agent response as failure; never render a report from a
  partial response.
- Keep server-provided errors generic. Do not surface raw provider messages,
  prompts, URLs, source content, or exception details.
- Preserve the clarification panel and entered answers after a research
  failure so the user can retry or change mode. A clarification failure
  remains recoverable by start over.
- Provide a clear retry action that resubmits the frozen topic and current
  answers with the selected mode, without invoking `/clarify` again.
- Starting over is always available after a failure and returns to the clean
  Code-default state.

## Proposed design

Update `frontend/src/App.tsx` with an explicit `ResearchMode` presentation
model and a request-phase helper:

- retain the existing typed `OrchestrationMode` value;
- store the mode in the clarification session and active run state;
- derive loading copy from `runState` and mode;
- track the last submitted research payload only for safe retry;
- keep the existing report rendering path shared by both modes.

Update `frontend/src/api.ts` only through the existing allowlisted
`requestResearch` adapter. Keep response parsing and `ApiError` generic;
avoid adding provider-specific status or payload handling.

Add focused styles for mode descriptions, progress copy, and retry actions
without changing the report layout. Ensure keyboard focus and labels remain
visible and the layout works on narrow screens.

No backend contract changes are expected. If a backend change becomes
necessary, preserve the PI-08 request/response shape and generic error
behavior rather than exposing Agent internals.

## Security and reliability considerations

- Never render model-generated instructions as UI markup; continue using React
  text nodes and existing safe response parsing.
- Never include topic, answers, source content, provider bodies, or API data in
  client error messages or analytics.
- Do not retry automatically: an Agent run can spend provider budget. Make
  retry an explicit user action and send the same allowlisted payload.
- Disable controls during requests to prevent duplicate costly runs.
- Do not use a client timeout shorter than the existing API adapter timeout for
  the synchronous Agent path.
- On stale or malformed responses, show a generic failure and leave no
  success-shaped state.

## Success criteria

- All users can select and successfully run Agent mode through the existing UI.
- Agent and Code display honest mode-specific progress and the same final
  report experience.
- Clarification answers and selected mode survive the entire flow.
- Agent failures are generic, recoverable, and never render partial reports.
- Explicit retry does not re-run clarification or lose answers.
- Start over clears all run state and resets Code as the default.
- No duplicate submissions occur while a request is active.
- Existing Code behavior and report rendering remain unchanged.

## Test plan

### Mode and clarification flow

- Code is selected by default and is sent for a clear topic.
- Agent selection is sent only to `/research`, not `/clarify`.
- Agent selection survives clarification and answer submission.
- Mode controls are enabled during questions and disabled during requests.
- Starting over resets mode, topic, answers, result, and errors.

### Progress and errors

- Code and Agent show distinct honest loading copy.
- Clarification loading copy remains unchanged.
- Agent 502/generic failure shows an alert, no report, and preserves topic,
  mode, questions, and answers.
- Retry resubmits the same topic/answers/mode once explicitly.
- A malformed or rejected response cannot populate the report.
- Controls prevent duplicate submit clicks during loading.

### Shared results and regression

- An Agent `ResearchResult` renders summary, insights, chart, sources, email
  status, and download link identically to Code.
- Existing no-question and answered-question Code tests remain green.
- Frontend tests, lint, and production build pass.

## Delivery plan

1. Refine mode selector labels/descriptions and active-run state.
2. Add honest mode-specific loading copy and accessible status behavior.
3. Add explicit retry handling that preserves the submitted payload.
4. Add Agent success/failure and shared-result tests.
5. Run frontend tests, lint, and build; run backend regression tests.
6. Update this plan with implementation notes and completed exit criteria.
7. Open the independent PI-09 pull request after all exit criteria pass.

## Exit criteria

- [ ] Agent mode is usable end to end for all users.
- [ ] Mode and clarification state survive selection, questions, submission,
      success, failure, retry, and start over.
- [ ] Progress copy is phase-accurate without fabricated Agent internals.
- [ ] Agent failures are generic, recoverable, and never render partial data.
- [ ] Retry is explicit, bounded to the submitted payload, and does not rerun
      clarification.
- [ ] Shared Code/Agent report, source, email, and download rendering works.
- [ ] Accessible controls and loading/error states are complete.
- [ ] Frontend tests/lint/build and backend regression tests pass.
- [ ] No secrets or unrelated story changes are included.
- [ ] This plan reflects final UX behavior and residual synchronous-request
      limitations.
- [ ] Pull request is opened from `pi-09-agent-ui-integration` and links to
      this document.
