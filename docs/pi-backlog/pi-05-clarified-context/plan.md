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
- Tighten the shared PI-01 `ClarificationAnswer` and `ResearchContext` models
  so HTTP and orchestrator validation are the same boundary.
- Preserve topic-only requests for existing clients.
- Pass one validated `ResearchContext` through the code-driven orchestrator.
- Put topic and Q&A into Planner and Writer **user** messages via a shared
  delimiter helper; keep system prompts static.
- Use answers as research **scope** for Planner queries and Writer focus, not
  as sources or as Tavily search strings.
- Update the frontend adapter to send the frozen session topic and collected
  answers only to `/research`.
- Align `/research` error and log handling with `/clarify` so failures do not
  echo topic, questions, or answers.
- Add backend and frontend tests for validation, prompt placement, and
  compatibility.

### Out of scope

- Generating clarification questions (PI-03).
- Persistent clarification sessions, signed decision tokens, or user
  accounts. Submitted question text is untrusted client data, not a proof
  that `/clarify` produced it.
- Guaranteeing that the model will ignore user-role instructions. Delimiters
  and a static system prompt constrain placement; they do not prove
  obedience.
- Agent orchestration or LLM tools (PI-06 through PI-09).
- Changing Searcher/Tavily integration, search/source caps, or passing raw
  answers into `TavilyClient.search`.
- Changing the report schema or Markdown-rendering the report in the UI.
- Authentication, rate limiting, or public-deployment abuse controls. This
  remains a local demo with the same unauthenticated cost residual as
  `/clarify`.

## Documentation rigor

**Required level: high.**

This story crosses the public API, frontend state, orchestration, and two
LLM prompt boundaries. It introduces additional untrusted strings into
Planner and Writer and must keep topic-only clients working. The plan
therefore requires one shared validation model, an explicit delimiter
helper, a narrowed injection residual, generic errors, and tests for
placement rather than for model obedience.

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

`clarification_answers` is optional and defaults to an empty list. A
topic-only body remains valid and must produce the same pipeline behavior.
The request model must not include `model`, `client`, `limits`, or
`api_key`. Extra fields are ignored (`extra="ignore"`) and must not change
server behavior.

The HTTP handler builds a `ResearchContext` from the body and calls
`run_research(context)`. It must not parse answers separately and then call
a topic-string overload that skips those checks.

### Shared validation

Put the HTTP bounds on the shared PI-01 models in
`app.research.schemas`, not only on a local request DTO:

- Topic: strip, reject empty, max 200 characters (already on
  `ResearchContext`).
- `question_id`: `^[a-z0-9][a-z0-9_-]{0,31}$`.
- Unique ids within the list; preserve submitted order.
- `clarification_answers` length 0–`ExecutionLimits.max_clarification_questions`
  (default 3). Use that default; do not read limits from the request.
- `question` max 200 characters; `answer` max 500; strip; reject blanks;
  reject rather than truncate.
- Reject C0 control characters (other than ordinary spaces) and the
  delimiter closer used by the prompt helper (see below).

Invalid context returns HTTP 422 **before** any OpenAI, Tavily, or report
I/O. Internal `run_research("topic")` compatibility, if kept, must
normalize to `ResearchContext(topic=...)` so it cannot carry unchecked
answers.

Question and answer strings are untrusted even when the UI copied them from
`/clarify`. Forged Q&A is an accepted residual without session storage; an
attacker who can POST `/research` can already set the topic.

### Orchestration behavior

Pass one `ResearchContext` through:

1. Planner — topic plus Q&A as scope for search queries;
2. Searcher — existing `search_plan(plan)` only; do not pass answers,
   question text, or topic as Tavily queries;
3. Writer — same context as **scope** (audience, timeframe, geography).
   Answers are not sources and must not introduce unsourced claims. Ground
   claims in retrieved sources as today;
4. Emailer — unchanged report type.

Searcher and Emailer keep their current types and caps (`MAX_SOURCES`,
queries per plan). Planner query strings remain model output executed by
code, subject to the existing query cap.

The report `topic` field stays the original topic string.

### Prompt construction

Use one formatting helper for Planner and Writer user messages so labels
and delimiters stay testable:

- System prompts remain static string constants. Do not interpolate topic,
  question, or answer into them. Writer’s system prompt should state that
  clarification answers constrain scope and are not sources.
- User message contains:
  - `<untrusted-research-topic>…</untrusted-research-topic>`
  - `<untrusted-clarification>…</untrusted-clarification>` with numbered
    `question_id` / `question` / `answer` lines when the list is non-empty
  - Writer only: a separate sources block, not nested inside the
    clarification tags
- If topic, question, or answer contains a closer tag (`</untrusted-…>`)
  or C0 controls, reject at validation time rather than splicing it into
  the prompt.
- Do not put untrusted strings in `href`, tool arguments, or Searcher
  calls.

These rules guarantee **placement**: untrusted text is only in the user
message, Searcher never sees raw answers, and search/source caps stay in
code. They do **not** guarantee the model will ignore user-role
instructions. That model-following residual is accepted for this demo.

### Errors and logs

Match `/clarify`, and **change** the current research handler that logs the
topic:

- Validation → 422 with Pydantic/HTTP detail that does not include provider
  bodies or exception causes.
- Pipeline/provider failure → 502 `"Research failed, please try again"`
  with `from None`.
- Logs record exception class (and optionally status) only. Do not log
  topic, questions, answers, raw model output, or `__cause__`.
- The frontend must not stringify a structured FastAPI `detail` object into
  the banner.

Secrets pasted into answers may still appear in the generated report and
`reports/*.md` because the product uses that scope. Do not add a secret
scanner in this story; do not add them to logs.

### Frontend submit path

`requestResearch` sends the **frozen session topic** and, when present, the
held `ClarificationAnswer[]` to `/research` only. It never sends answers to
`/clarify` and never sends `model`, `client`, `limits`, or `api_key`.

The no-question path may omit `clarification_answers` or send `[]`. The
answered path sends the structured list. Duplicate in-flight submits stay
disabled. Report UI keeps rendering summary, insights, and sources as text
nodes.

## Proposed design

Tighten `ClarificationAnswer` and the answers list on `ResearchContext` in
`app.research.schemas`. Point `ResearchRequest` at those types so there is
one validation path.

Change `run_research` to take `ResearchContext`. Keep a thin topic-string
wrapper for old unit tests that only builds `ResearchContext(topic=topic)`.
Update Planner and Writer signatures to accept `ResearchContext` and call
the shared format helper. Leave Searcher and Emailer signatures as they
are.

Update `/research` to construct `ResearchContext`, map `ValidationError` to
422, and use type-only failure logging like `/clarify`.

Update the frontend API adapter so the clarification session’s frozen topic
and answers are the research payload. `App.tsx` should not assemble that
JSON inline.

## Success criteria

- Topic-only `/research` remains valid and behaves as before.
- Answered requests validate on the shared models before external calls and
  pass one `ResearchContext` through the pipeline.
- Planner user content includes delimited topic and Q&A; its system prompt
  does not.
- Writer uses the same delimited context as scope, keeps sources in a
  separate block, and still emits the existing report shape with the
  original topic.
- Searcher is invoked only with plan queries; answers are absent from
  Tavily calls.
- Extra provider fields do not change behavior.
- Invalid ids, duplicates, blanks, over-long fields, delimiter closers, and
  more than three answers return 422 without provider calls.
- Research 502 responses and logs contain no topic, questions, or answers.
- Frontend sends collected answers only to `/research`, using the frozen
  topic.
- Existing report rendering, download, and no-question flow still work.

## Test plan

### Backend

Cover at least:

- topic-only request uses the existing pipeline;
- valid clarified request builds the expected `ResearchContext`;
- Planner and Writer user messages contain the delimited topic and Q&A
  blocks and their system prompts do not;
- Writer keeps sources outside the clarification tags;
- Searcher/Tavily is not called with answer or question text;
- question ids match the pattern and order is preserved;
- duplicate ids, blanks, over-long fields, C0 controls, closer tags, and
  more than three answers return 422 before external calls;
- extra `model`, `client`, `limits`, or `api_key` fields do not change
  behavior;
- pipeline failure returns generic 502 with no topic or answers in the
  body.

### Frontend

Cover at least:

- no-question flow sends topic-only (or empty answers) research request
  with no provider fields;
- answered flow sends the frozen topic and structured answers to
  `/research` only;
- answers are not sent to `/clarify`;
- duplicate submissions remain prevented;
- report fields still render as text after a clarified run.

## Delivery plan

1. Tighten shared `ClarificationAnswer` / `ResearchContext` constraints and
   extend `ResearchRequest`.
2. Switch the orchestrator, Planner, and Writer to `ResearchContext`; add
   the delimiter helper; keep Searcher on plan queries only.
3. Update `/research` validation, generic 502, and type-only logging.
4. Point the frontend adapter at the frozen session payload.
5. Add backend and frontend tests for validation, prompt placement, and
   compatibility.
6. Run full backend tests/lint and frontend tests/lint/build.
7. Update this plan with implementation notes and completed exit criteria.
8. Open the PI-05 pull request once all exit criteria are complete.

## Exit criteria

- [x] Shared models enforce id pattern, uniqueness, list cap, and
      question/answer length; `/research` uses them.
- [x] Topic-only requests remain backward compatible.
- [x] One `ResearchContext` flows through Planner, Searcher, Writer, and
      Emailer.
- [x] Topic and Q&A appear only in delimited user messages; system prompts
      stay static; Writer treats answers as scope, not sources.
- [x] Searcher does not receive raw answers; search/source caps are
      unchanged.
- [x] `/research` 422s invalid context before external calls and 502s
      without logging or returning topic, questions, or answers.
- [x] Frontend sends collected answers only to `/research` with the frozen
      topic.
- [x] Tests cover compatibility, validation, prompt placement, and the
      Searcher boundary.
- [x] Full backend tests/lint and frontend tests/lint/build pass.
- [x] No secrets or unrelated story changes are included.
- [x] This plan reflects the final design, including the accepted
      model-following and forged-Q&A residuals.
- [ ] Pull request is opened from `pi-05-clarified-context` and links to
      this document.

## Implementation notes

- Tightened PI-01 shared context models with bounded question/answer fields,
  ID format and uniqueness validation, control-character rejection, and
  delimiter-closer rejection.
- Added one shared context formatter used by Planner and Writer. Topic and Q&A
  appear only in delimited user messages; Writer keeps sources in a separate
  block and treats answers as scope rather than evidence.
- Updated `/research` to accept validated optional answers while preserving
  topic-only requests and generic type-only failure logging.
- Updated the frontend adapter to send frozen-topic answers only to
  `/research`; `/clarify` remains topic-only.
- Validation: 57 backend tests passed, Ruff passed, 3 frontend tests passed,
  frontend lint passed, and frontend build passed.
