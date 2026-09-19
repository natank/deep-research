# PI-05 Plan: Pass Clarified Context Through Code Orchestration

## Story

**As a researcher, I want my clarification answers to influence the research
plan and report, so that the results reflect the scope I specified.**

**Story type:** Feature  
**Priority:** Must  
**Dependencies:** PI-04  
**Branch:** `pi-05-clarified-context`

## Scope

### In scope

- Extend `POST /research` to accept optional structured clarification answers.
- Validate topic and answer context on the server using bounded, typed models.
- Preserve topic-only requests for existing clients.
- Pass `ResearchContext` through the code-driven orchestrator.
- Incorporate clarification context into Planner and Writer user messages.
- Update the frontend to submit the collected answers.
- Keep question and answer content untrusted and delimited in LLM prompts.
- Add backend and frontend tests proving that context changes the planner/writer
  inputs and remains safe.

### Out of scope

- Generating clarification questions (PI-03).
- Adding persistent clarification sessions, signed decision tokens, or user
  accounts.
- Proving that submitted question text came from the latest `/clarify`
  response; without session storage, it is untrusted client data.
- Agent orchestration (PI-06 through PI-09).
- Changing Searcher behavior or Tavily integration.
- Changing the report schema or adding new report sections.
- Adding public-deployment authentication, rate limiting, or abuse controls.

## Documentation rigor

**Required level: high.**

This story crosses the public API, frontend state, orchestration, and multiple
LLM prompt boundaries. It also introduces user-controlled text into prompts
and must preserve topic-only clients. The plan therefore requires explicit
request validation, compatibility behavior, trust-boundary rules, prompt
construction tests, generic error handling, and end-to-end contract coverage.

## Requirements

### Research request contract

`POST /research` must accept:

```json
{
  "topic": "artificial intelligence in education",
  "clarification_answers": [
    {
      "question_id": "q1",
      "question": "Which education level should be covered?",
      "answer": "Higher education"
    }
  ]
}
```

`clarification_answers` is optional and defaults to an empty list. The existing
topic-only request remains valid and must produce the same pipeline behavior.
Unknown request fields must not change server behavior or expose provider
configuration.

### Server validation

Before any LLM, Tavily, or report call:

- Reuse PI-01 topic rules: strip, reject empty, and cap topic length at 200.
- Validate question ids against
  `^[a-z0-9][a-z0-9_-]{0,31}$`.
- Require unique question ids.
- Require between zero and `ExecutionLimits.max_clarification_questions` (3 by
  default) answers.
- Cap question and answer text at 200 and 500 characters respectively; reject
  over-long values rather than truncating.
- Reject blank question or answer text.
- Do not accept model names, API clients, API keys, limits, or provider
  settings from the request body.
- Preserve answer order as submitted.

The server cannot attest that question text came from `/clarify`; treat both
question and answer strings as untrusted data. The validation and prompt
delimiters are the security boundary for this story.

### Orchestration behavior

The code path must pass one `ResearchContext` through:

1. Planner;
2. Searcher using the resulting plan;
3. Writer;
4. Emailer.

Planner behavior must use the topic and answers to create a more targeted
search plan. Writer behavior must use the same context when synthesizing the
report. Searcher and Emailer need no semantic changes, but their callers must
continue to receive the existing plan, sources, and report types.

Topic-only calls must remain supported for internal callers and existing tests,
either through a compatibility wrapper or a default `ResearchContext`.

### Prompt safety

- Keep Planner and Writer system prompts static.
- Put topic, question text, and answer text only in delimited user-message
  sections clearly marked as untrusted research context.
- Never interpolate clarified text into a system prompt.
- Do not render or execute answer text as HTML, Markdown instructions, URLs, or
  tool arguments.
- Do not include raw context, provider bodies, API keys, or exception causes in
  caller-facing errors or logs.
- Prompt-injection text in a topic, question, or answer must remain data and
  must not override system instructions or enable tools.

## Proposed design

Extend the backend request model with an optional list of PI-01
`ClarificationAnswer` values, adding field constraints needed for the HTTP
boundary if they are not already present in the shared model. Build a
`ResearchContext` after request validation and pass it to
`run_research(context)`.

Keep compatibility with existing internal calls by allowing
`run_research` to accept a topic string and normalize it to a context, or by
providing a small explicit compatibility wrapper. New code should use the
structured context path.

Update Planner and Writer service signatures to accept `ResearchContext` (with
an internal topic-only normalization helper where needed). Use dedicated
formatting helpers for untrusted context so delimiters and field labels are
consistent and easy to test. The report’s existing `topic` field remains the
original topic.

Update the frontend API adapter so `requestResearch` accepts the typed
`ClarificationAnswer[]` held by the clarification session and sends them only
to `/research`. The no-question path sends an empty list or preserves the
topic-only request, while the answered path sends the structured context.

## Success criteria

- Topic-only `/research` requests remain valid and behave as before.
- Answered requests validate before external calls and pass one structured
  context through the code pipeline.
- Planner receives clarification scope and can produce queries informed by it.
- Writer receives the same context and produces the existing report shape.
- Searcher, Emailer, report download, and frontend report rendering remain
  compatible.
- Invalid ids, duplicates, blanks, over-limit answers, and unknown unsafe
  fields are handled without provider calls.
- Clarification text and answers appear only in delimited user messages, never
  system prompts.
- Prompt-injection content remains inert data and does not alter orchestration.
- Errors remain generic and logs do not expose topic, questions, answers, raw
  model output, or provider details.
- Frontend tests prove collected answers are sent and topic-only behavior still
  works.

## Test plan

### Backend

Cover at least:

- topic-only request uses the existing pipeline;
- valid clarified request builds the expected `ResearchContext`;
- Planner and Writer receive context containing topic, question, and answer;
- question ids are validated and preserved;
- duplicate ids, blank values, over-long fields, and more than three answers
  return 422 before external calls;
- extra `model`, `client`, `limits`, or `api_key` fields do not change behavior;
- topic/question/answer prompt-injection strings stay in user content and do
  not appear in system prompts;
- provider/pipeline failures return the existing generic research failure
  response without leaking context.

### Frontend

Cover at least:

- no-question flow sends a topic-only research request;
- answered flow sends the original topic and structured answers;
- question ids and text are preserved from the clarification session;
- answer text is not sent to `/clarify`;
- duplicate submissions remain prevented;
- existing report rendering continues after a clarified run.

## Delivery plan

1. Extend and validate the research request/context boundary.
2. Update orchestrator, Planner, and Writer to accept structured context while
   preserving topic-only compatibility.
3. Add safe context-formatting helpers and prompt-boundary tests.
4. Update the frontend API adapter and clarification submit path to send
   answers to `/research`.
5. Add backend and frontend regression/security tests.
6. Run full backend tests/lint and frontend tests/lint/build.
7. Update this plan with implementation notes and completed exit criteria.
8. Open the PI-05 pull request once all exit criteria are complete.

## Exit criteria

- [ ] `/research` accepts validated optional clarification answers.
- [ ] Topic-only requests remain backward compatible.
- [ ] Structured context flows through Planner, Searcher, Writer, and Emailer.
- [ ] Clarification content is delimited untrusted user data in prompts.
- [ ] Server validation rejects invalid, oversized, duplicate, or excessive
      answer context before external calls.
- [ ] Frontend sends collected answers only to `/research`.
- [ ] Backend and frontend tests cover compatibility, context propagation, and
      prompt-boundary/security behavior.
- [ ] Full backend tests/lint and frontend tests/lint/build pass.
- [ ] No secrets or unrelated story changes are included.
- [ ] This plan reflects the final design and API boundary.
- [ ] Pull request is opened from `pi-05-clarified-context` and links to this
      document.
