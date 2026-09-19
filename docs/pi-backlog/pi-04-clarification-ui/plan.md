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

- Add a server-owned `POST /clarify` endpoint that accepts only a topic and
  returns a PI-03 `ClarificationDecision`.
- Display that decision and its questions in the frontend.
- Let users provide a bounded answer for each returned question.
- Validate required answers before continuing.
- Continue without an extra interaction when the server returns no questions.
- Freeze the original topic for the clarification session and carry structured
  answers in typed client state for PI-05.
- Show loading, validation, failure, and retry states without duplicate paid
  calls while a request is in flight.
- Render question, purpose, and topic as text, not HTML or Markdown.
- Add frontend tests for rendering, validation, submission, and error states,
  plus backend tests for the new route.

### Out of scope

- Changing how PI-03 generates or validates questions.
- Applying answers inside Planner, Searcher, Writer, or Agent orchestration
  (PI-05). `/research` stays topic-only in this story.
- Orchestration-mode selection (PI-06).
- Persisting clarification sessions, signed decision tokens, or user history.
  Client-supplied question text is therefore untrusted; PI-05 must treat it as
  data, not as a server attestation.
- Authentication, rate limiting, or public-deployment abuse controls. This
  remains a local demo: the new route uses server-owned limits and request
  bounds, but is not safe to expose on the public internet.
- Calling OpenAI, or any other provider, from the browser.
- Rendering arbitrary model output as HTML or Markdown.

## Documentation rigor

**Required level: high.**

This story changes the primary user flow and is the first HTTP exposure of
the PI-03 LLM call. Poor state handling could lose user input, create
unnecessary paid calls, trust browser-supplied question text, or turn model
output into executable content. The plan therefore requires a frozen request
shape, explicit trust rules, state transitions, validation and error mapping,
accessibility expectations, and tests for both the UI and the new route.
Visual polish beyond the existing application style is not required.

## Requirements

### User flow

1. The user enters a topic and starts research.
2. The app sends that topic to `POST /clarify`. It does not send model names,
   API clients, execution limits, or provider settings.
3. If the decision contains no questions, the existing `POST /research` flow
   continues with the same topic and no extra interaction. There is no client
   "skip" control when questions were returned.
4. If questions are returned, the UI shows the frozen topic plus each
   question and purpose as read-only text, with an answer field per question.
5. The user enters an answer for every displayed question.
6. The user submits or retries after an error. Retry of a failed clarify call
   is user-initiated only and must not loop automatically.
7. Typed client state keeps the original topic, service-owned question ids,
   question text, and answers for PI-05. This story does not yet send answers
   to `/research`.
8. The user sees progress while the next research step runs.

The user must not choose or edit question ids, question text, model names,
API clients, execution limits, or other server-controlled fields. Editing the
topic field while questions are shown does not change the session topic;
cancel or start over is required to clarify a different topic.

### Form behavior

- Each question has an associated label and a single answer control.
- Questions and purposes are read-only text, not editable inputs.
- Empty or whitespace-only answers are rejected before submission.
- Answers are capped at 500 characters in the UI and on the server. Reject
  over-long values; do not truncate.
- Answer count must match the returned questions; extra answers are rejected.
- The form identifies the first invalid answer and exposes an accessible
  error.
- Answer fields use `autoComplete="off"`.
- Existing topic validation and 200-character limit remain unchanged.
- Browser-side limits improve UX but do not replace backend validation.
- Submit controls are disabled while a clarify or research request is in
  flight, so a double click cannot start a second paid call.
- A failed request preserves the frozen topic and already entered answers.
- A retry does not duplicate controls or silently discard answers.

### Rendering

- Render topic, question, and purpose as React text nodes.
- Do not use `dangerouslySetInnerHTML`, HTML interpolation, Markdown, or
  model-provided `href`, `src`, `style`, or `action` values.
- After validating the response shape, use service-owned question ids only as
  React keys and form `htmlFor` / input id suffixes.
- Reject an invalid clarification response rather than rendering it.
- Do not infer safety from the PI-03 denylist or from client-side checks.
  Text rendering is the XSS control.

### API boundary

`decide_clarification` runs only on the server. The frontend never holds a
provider key and never calls OpenAI.

**`POST /clarify`**

- Request: `{ "topic": string }` with the same strip / empty / 200-character
  rules as `ResearchContext`. Extra fields are ignored. `model`, `client`,
  `limits`, and `api_key` are not part of the contract and must not change
  server behavior if a client sends them.
- Server uses `ExecutionLimits()` defaults. Limit zero still skips the LLM.
- Response: the PI-03 `ClarificationDecision` (`needs_clarification`,
  `questions` with `id`, `question`, `purpose`).
- Errors: `ClarificationError` and unexpected provider failures map to HTTP
  502 with a generic body such as `"Clarification failed"`. Empty or over-long
  topics map to 422. Do not put topic text, questions, answers, raw model
  output, provider bodies, or exception `__cause__` in `detail`.
- Logs may record exception class and status only. Do not log topic,
  questions, or answers.
- Reuse the existing request timeout policy. The Vite proxy and localhost
  CORS config must include `/clarify` the same way as `/research`.

**Answers held for PI-05**

The structured context shape remains:

- original frozen topic;
- list of `{ question_id, question, answer }`;
- no browser-controlled execution limits, model, client, or provider
  settings.

Until PI-05 extends `/research`, that list lives in the frontend adapter
state only. Submitted `question` and `answer` strings are untrusted user
data, even when the UI copied them from the last `/clarify` response. Without
session storage, the server cannot prove those strings are the model output.
PI-05 must delimit them in the user message the same way PI-03 delimits the
topic.

Validate ids against `^[a-z0-9][a-z0-9_-]{0,31}$`, uniqueness, count at most
`ExecutionLimits.max_clarification_questions` (3), and the 200 / 500
character field caps before treating a payload as well-formed. The frontend
does this before holding state; PI-05 must do it again on the server.

## Proposed design

Add `POST /clarify` next to the existing research route. The handler builds a
`ResearchContext` from the topic, calls `decide_clarification` with default
limits, and maps `ClarificationError` to a generic 502. It does not accept an
injected OpenAI client or a client-supplied `ExecutionLimits`.

Extend the frontend types with the PI-03 decision and answer contracts:

- `ClarificationQuestion`;
- `ClarificationDecision`;
- `ClarificationAnswer`;
- a typed research context held in the client until PI-05.

Keep API calls in a small client/helper module so `App.tsx` manages state and
presentation rather than assembling payloads. The helper sends `{ topic }` to
`/clarify` and `{ topic }` to `/research`. Model the UI state explicitly, for
example:

- `idle`;
- `checking` (clarify in flight);
- `questions` (frozen topic and read-only questions);
- `submitting` / existing `loading` (research in flight);
- `error`;
- success when a report is shown.

The component should preserve the current topic form and report view. The
clarification panel can be a sibling section in the existing single-page
layout, using the repository's current CSS conventions and accessible labels.

The backend remains the source of truth for ids and content on the clarify
response. The frontend may validate that shape for safe rendering, but must
not reassign ids, alter questions, or treat a successful render as a security
review of the model output.

## Success criteria

- Clear topics call `/clarify`, receive no questions, and proceed to
  `/research` without a clarification form.
- Returned questions display as read-only text with purpose and correctly
  associated answer controls, keyed by service-owned ids.
- The session topic stays frozen until the user cancels or starts over.
- Users cannot submit missing, blank, extra, or over-long answers.
- Held context preserves the original topic and service-owned question ids
  without model, client, or limit fields.
- Validation and network errors are generic, retryable without losing
  answers, and never include topic or provider text.
- In-flight states prevent duplicate clarify or research calls.
- Clarification content cannot inject HTML, scripts, or links.
- Invalid response shapes fail closed.
- `/clarify` ignores client-supplied provider settings and uses server-owned
  limits.
- Existing direct research, report rendering, and error behavior remain
  intact for the `/research` step.
- Tests cover the UI states and the route contract below.

## Test plan

### Frontend

If the repository does not yet have a frontend test runner, add the smallest
appropriate setup rather than relying only on manual inspection.

Cover at least:

- no-question decision skips the clarification UI and starts research;
- one or more questions render as text with labels and purposes;
- each answer is keyed by the returned question id;
- questions are not editable and the topic cannot be swapped under an
  in-progress session;
- blank and over-long answers block submission and identify the invalid
  field;
- successful continuation holds the expected structured context for PI-05;
- network/API failure shows a generic error and preserves input;
- retry succeeds without duplicating questions or answers or auto-looping;
- submit controls disable while requests are active;
- strings that look like HTML, `javascript:`, or Markdown render as text;
- malformed or over-limit response data fails closed;
- existing topic-only research behavior still works after a no-question
  decision.

### Backend

Cover at least:

- `{ "topic": "..." }` returns a valid decision using default limits;
- empty and over-long topics return 422 without calling the LLM when
  validation fails first;
- extra request fields such as `limits`, `model`, and `api_key` do not
  change behavior;
- `ClarificationError` becomes HTTP 502 with a generic body and no topic in
  the message;
- unexpected provider exceptions become the same generic 502;
- response questions keep PI-03 ids, bounds, and count limits;
- Vite/CORS proxy configuration includes `/clarify`.

## Delivery plan

1. Add `POST /clarify` with the frozen request shape, generic error mapping,
   and proxy/CORS coverage.
2. Add typed frontend contracts and an API adapter that calls `/clarify` then
   `/research` without sending answers yet.
3. Implement the clarification form, frozen topic, validation, accessible
   error states, and retry behavior.
4. Integrate with the existing research flow without regressing the
   no-question path.
5. Add frontend and backend tests; run lint/build and the backend suite.
6. Update this plan with implementation notes and completed exit criteria.
7. Open the PI-04 pull request once all exit criteria are complete.

## Exit criteria

- [x] `POST /clarify` is implemented with server-owned limits and a
      topic-only request body.
- [x] Clarification UI, frozen topic, and answer collection are implemented.
- [x] Typed client state preserves topic and service-owned question ids for
      PI-05 without sending answers to `/research` yet.
- [x] Browser validation, loading, retry, and failure states are complete.
- [x] Model-produced text is rendered only as text.
- [x] No browser-controlled model, client, limit, or provider override
      exists, including on the new route.
- [x] HTTP errors are generic and logs do not include topic, questions, or
      answers.
- [x] Frontend and backend tests cover the required behavior.
- [x] Existing lint/build and direct research behavior pass.
- [x] No secrets or unrelated story changes are included.
- [x] This plan reflects the final design and API boundary.
- [ ] Pull request is opened from `pi-04-clarification-ui` and links to this
      document.

## Implementation notes

- Added the topic-only `POST /clarify` route with server-owned PI-01 limits,
  generic 422/502 responses, and type-only failure logging.
- Added a typed frontend API adapter that validates clarification response
  shape, ids, bounds, duplicates, and decision invariants before rendering.
- Added the clarification form with a frozen topic, read-only question text,
  bounded answers, accessible labels, duplicate-submit prevention, retry
  preservation, and start-over behavior.
- Answers remain in typed client state for PI-05 and are intentionally not
  sent to the topic-only `/research` endpoint yet.
- Added a minimal Vitest and Testing Library setup for frontend behavior
  coverage.
- Validation: 52 backend tests passed, 3 frontend tests passed, Ruff passed,
  frontend lint passed, and frontend build passed.
