# PI-04 Plan: Clarification UI and Answer Submission

## Story

**As a researcher, I want to answer focused clarification questions before
research begins, so that the app can use my intended scope to produce a more
relevant report.**

**Story type:** Feature  
**Priority:** Must  
**Dependencies:** PI-03  
**Branch:** `pi-04-clarification-ui`

## Scope

### In scope

- Display a clarification decision and its questions in the frontend.
- Let users provide an answer for each question.
- Validate required answers before continuing.
- Allow users to skip clarification when no questions are returned.
- Preserve the original topic while submitting structured answers.
- Show loading, validation, failure, and retry states.
- Keep question and purpose content rendered as text, not HTML or Markdown.
- Define the frontend/API contract needed by PI-05 to pass context into code
  orchestration.
- Add frontend tests for rendering, validation, submission, and error states.

### Out of scope

- Generating clarification questions (PI-03).
- Applying answers inside Planner, Searcher, Writer, or Agent orchestration
  (PI-05 and later).
- Orchestration-mode selection (PI-06).
- Persisting clarification sessions or user history.
- Authentication, rate limiting, or general abuse-prevention infrastructure.
  Any clarification API exposure must use server-owned defaults and must not
  accept model, client, or execution-limit overrides from the browser.
- Rendering arbitrary model output as HTML or Markdown.

## Documentation rigor

**Required level: high.**

This story changes the primary user flow and crosses the frontend/backend
boundary. Poor state handling could lose user input, create unnecessary paid
LLM calls, or allow untrusted model output to become executable content. The
plan therefore requires explicit state transitions, request/response shapes,
validation behavior, accessibility expectations, timeout/error handling, and
security tests. Visual polish beyond the existing application style is not
required.

## Requirements

### User flow

1. The user enters a topic and starts research.
2. If the clarification decision contains no questions, the existing research
   flow continues without an extra interaction.
3. If questions are returned, the UI displays the topic, each question, and its
   purpose.
4. The user enters an answer for every displayed question.
5. The user submits the answers or retries after an error.
6. The app submits the original topic and structured answers, preserving the
   service-owned question ids.
7. The user receives clear progress feedback while the next research step runs.

The user must not be asked to choose or edit question ids, model names, API
clients, execution limits, or other server-controlled fields.

### Form behavior

- Each question has an associated label and answer control.
- Empty or whitespace-only answers are rejected before submission.
- The form identifies the first invalid answer and exposes an accessible error.
- Existing topic validation and 200-character limit remain unchanged.
- Browser-side limits improve UX but do not replace backend validation.
- Submit controls are disabled while the clarification request is in flight.
- A failed request preserves the topic and already entered answers.
- A retry does not duplicate controls or silently discard answers.

### Rendering and security

- Render question and purpose values as text nodes.
- Do not use `dangerouslySetInnerHTML`, HTML interpolation, Markdown
  rendering, or model-provided URLs for clarification content.
- Use stable question ids only for form associations and React keys after
  validating the API response shape.
- Reject an invalid clarification response rather than rendering unsafe or
  structurally invalid content.
- Do not expose provider errors, raw model output, API keys, or topic content in
  user-facing error messages.

### API boundary

The implementation must agree with PI-05 on a structured context shape:

- original topic;
- list of `{question_id, question, answer}` values;
- no browser-controlled execution limits, model, client, or provider settings.

If PI-04 adds an HTTP clarification endpoint, it must use server-owned limits,
generic errors, and the same request timeout/error policy as the existing API.
It must not become an unrestricted unauthenticated paid LLM endpoint. If the
backend contract is deferred to PI-05, PI-04 must still implement and test the
frontend adapter against a typed boundary rather than duplicating request
construction in components.

## Proposed design

Extend the frontend types with the PI-03 decision and answer contracts:

- `ClarificationQuestion`;
- `ClarificationDecision`;
- `ClarificationAnswer`;
- a typed research context or clarification request.

Keep API calls in a small client/helper module so `App.tsx` manages state and
presentation rather than assembling untrusted payloads. Model the UI state
explicitly, for example:

- `idle`;
- `checking`;
- `questions`;
- `submitting`;
- `error`;
- existing `loading`/`success` states as applicable.

The component should preserve the current direct-topic form and report view.
The clarification panel can be a sibling section in the existing single-page
layout, using the repository's current CSS conventions and accessible labels.

The backend service remains the source of truth for question ids and content.
The frontend may validate the response shape for safe rendering, but must not
reassign ids, alter questions, or infer security approval from client-side
checks.

## Success criteria

- Clear topics proceed without displaying an unnecessary clarification form.
- Returned questions display with readable purpose text and correctly associated
  answer controls.
- Users cannot submit missing or blank required answers.
- Submitted payloads preserve the original topic and service-owned question ids.
- Validation and network errors are visible, generic, and retryable without
  losing entered answers.
- Loading and disabled states prevent duplicate submissions.
- Clarification content is rendered as text and cannot inject HTML, scripts, or
  links.
- Invalid response shapes fail closed rather than rendering unsafe content.
- Existing direct research, report rendering, and error behavior remain intact.
- Tests cover clear, questioned, invalid, failed, retry, and accessibility
  states.

## Test plan

Add or update frontend tests to cover at least:

- no-question decision skips the clarification UI;
- one or more questions render with labels and purposes;
- each answer is keyed by the returned question id;
- blank answers block submission and identify the invalid field;
- successful answer submission sends the expected structured context;
- network/API failure shows a generic error and preserves input;
- retry succeeds without duplicating questions or answers;
- submit controls disable while requests are active;
- unsafe-looking response strings render as text rather than markup;
- malformed response data fails closed;
- existing topic-only research behavior still works.

If the repository does not yet have a frontend test runner, document that
constraint in the implementation notes and add the smallest appropriate test
setup rather than relying only on manual inspection.

## Delivery plan

1. Confirm the PI-03 response and PI-05 context boundary before changing UI
   state.
2. Add typed frontend contracts and an API adapter.
3. Implement the clarification form, validation, accessible error states, and
   retry behavior.
4. Integrate the form with the existing research flow without regressing the
   direct-topic path.
5. Add frontend tests and run existing lint/build checks.
6. Update this plan with implementation notes and completed exit criteria.
7. Open the PI-04 pull request once all exit criteria are complete.

## Exit criteria

- [ ] Clarification UI and answer submission are implemented.
- [ ] Typed contracts preserve topic and service-owned question ids.
- [ ] Browser validation, loading, retry, and failure states are complete.
- [ ] Model-produced text is rendered safely as text only.
- [ ] No browser-controlled model, client, limit, or provider override exists.
- [ ] Frontend tests cover the required behavior and accessibility states.
- [ ] Existing frontend lint/build and direct research behavior pass.
- [ ] No secrets or unrelated story changes are included.
- [ ] This plan reflects the final design and API boundary.
- [ ] Pull request is opened from `pi-04-clarification-ui` and links to this
  document.
