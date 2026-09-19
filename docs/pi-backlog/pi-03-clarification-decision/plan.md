# PI-03 Plan: Clarification Decision Step

## Story

**As a researcher, I want the app to identify when my topic needs clarification
and generate focused questions, so that my research request produces more
relevant results.**

**Story type:** Feature  
**Priority:** Must  
**Dependencies:** PI-01  
**Branch:** `pi-03-clarification-decision`

## Scope

### In scope

- Define a structured clarification decision and question model.
- Use the configured LLM to decide whether a topic is sufficiently specific.
- Generate focused questions for ambiguous or underspecified topics.
- Skip questions for clear topics.
- Enforce the PI-01 maximum-question limit.
- Validate the structured result and surface malformed or unavailable results
  as explicit errors.
- Treat the topic and all model-produced strings as untrusted; enforce
  security invariants in code, not only in the prompt.
- Add unit tests with mocked OpenAI responses, including adversarial and
  failure cases.

### Out of scope

- Rendering questions or collecting answers in the frontend (PI-04).
- Passing answers into Planner, Searcher, Writer, or Agent orchestration
  (PI-05 and later).
- Selecting Code or Agent mode (PI-06).
- Persisting clarification sessions or user history.
- Asking follow-up questions after the user has submitted answers.
- Replacing the existing `/research` endpoint flow.
- Adding authentication, rate limiting, or a public clarification HTTP route.
  PI-04 must not expose this service as an unauthenticated paid LLM endpoint
  without addressing abuse.

## Documentation rigor

**Required level: medium-high.**

This feature introduces an LLM decision into the user workflow and can create
friction or poor research results if it asks unnecessary, vague, or excessive
questions. The implementation is small, but its output becomes a contract for
the UI and later orchestration stories. Structured model output is a schema
boundary, not a security boundary: string fields can still carry injection,
secret-seeking, or oversized content.

The plan therefore requires explicit schemas, question-quality rules, hard
bounds, fail-closed malformed-output handling, a documented trust boundary,
server-side security invariants, and tests for clear, ambiguous, over-limit,
adversarial, and failed responses.

## Requirements

### Decision contract

The clarification service must return a structured decision containing:

- `needs_clarification`: whether the topic needs user input before research;
- `questions`: zero or more focused questions;
- a stable `id` on every question so PI-04 can associate submitted answers
  with the correct question.

Questions should also include a short purpose or rationale so the UI and later
evaluation can understand what ambiguity each question addresses.

Question identifiers are a service-owned contract, not model-owned data.
PI-04 must key answers by these ids. Do not use model-supplied strings as
DOM ids, object keys, filenames, or URL path segments without the format
rules below.

### Decision behavior

- Clear, sufficiently scoped topics return no questions.
- Ambiguous topics return a small set of questions targeting scope,
  geography, timeframe, audience, comparison criteria, or desired outcome.
- Questions must be answerable by the user and must not ask for secrets or
  sensitive personal information. Prompt instructions are not sufficient;
  the service must reject matching questions after parse.
- Questions must not duplicate one another after strip and case-fold of the
  question text.
- The service must never return more questions than the configured
  `max_clarification_questions` limit.
- A decision that says clarification is unnecessary must expose an empty
  question list.
- A decision that requires clarification must contain at least one question.
- When the configured limit is zero, the service must not call the LLM. It
  must return `needs_clarification=false` and an empty question list.

### Input and field bounds

- Reuse PI-01 `ResearchContext` topic rules: strip, reject empty, and cap at
  `TOPIC_MAX_LENGTH` (200). The service must not accept a longer topic than
  the shared contract.
- Callers that do not pass a full `ResearchRun` must use the same default as
  `ExecutionLimits.max_clarification_questions` (3). Do not invent a looser
  default.
- Cap question text and purpose length (200 characters for the question,
  200 for the purpose). Reject, do not truncate, values over the cap.
- Question ids must match `^[a-z0-9][a-z0-9_-]{0,31}$` and be unique within
  a decision. Prefer server-assigned ids (`q1`…`qn`) after a successful
  parse so the model cannot choose colliding or injection-prone ids.
- Question and purpose text must be plain language. Reject HTML/script
  markup, `javascript:` URLs, and control characters other than ordinary
  spaces.

### Error behavior

If the LLM call fails, returns no parseable structured result, or violates
any decision or security invariant, the service must raise a typed
`ClarificationError` for the caller. It must not:

- treat the failure as a clear topic;
- continue with a success-shaped response;
- silently truncate, drop, rewrite, or otherwise repair the model output.

Caller-facing error messages must be stable and generic (for example,
"Clarification failed"). Do not put raw model output, provider error bodies,
API keys, or topic text into the exception message. Logs may record
exception class and HTTP/provider status, not completions, topics, or
secrets.

### Security constraints

Trust boundary: the topic and every model-produced string are untrusted.
The system prompt is a static string. The topic belongs only in the user
message, inside a delimited untrusted block, never concatenated into the
system prompt.

`responses.parse` constrains shape, not meaning. After parse, the service
must enforce all of the following and raise `ClarificationError` on
violation:

1. `needs_clarification=false` if and only if `questions` is empty, except
   the limit-zero short-circuit above.
2. `len(questions) <= max_clarification_questions`.
3. Unique, server-assigned or allowlisted ids.
4. Field max lengths and plain-text rules.
5. No duplicate question text.
6. No secret- or PII-seeking questions (credentials, API keys, passwords,
   tokens, SSNs, government ids, home address, and similar). A conservative
   keyword/pattern check is enough for this demo; false positives that
   reject a decision are acceptable.

Do not copy the Planner's silent `queries[:MAX]` slice. Truncation is a
repair and is forbidden here.

Residual risk: the current API is unauthenticated. This story does not add
a route. PI-04 must not accept model name, API client, or limit overrides
from the request body. PI-04 should render question and purpose as text,
not HTML or Markdown. PI-05 and later must treat question text and answers
as untrusted data in planner, searcher, writer, and agent prompts.

## Proposed design

Add a dedicated clarification package, for example
`backend/app/clarification/`, with:

- `schemas.py` for `ClarificationQuestion` and `ClarificationDecision`;
- `service.py` for the OpenAI-backed decision function;
- `exceptions.py` for `ClarificationError`;
- `__init__.py` for the public exports.

Follow the Planner service pattern for client wiring only: inject an
optional `OpenAI` client for tests, call `responses.parse` with the
structured decision model, and use `settings.openai_api_key` in production.
Do not accept a client, model, or limit override from untrusted input.

Suggested models:

- `ClarificationQuestion`: `id`, `question`, `purpose`;
- `ClarificationDecision`: `needs_clarification`, `questions`.

Pydantic field constraints should encode max lengths and the id pattern so
invalid values fail validation. Invariant checks that depend on the
configured limit or on several fields together belong in the service after
parse (limit vs list length, flag vs emptiness, duplicate text,
secret-seeking content).

Use PI-01's `ExecutionLimits.max_clarification_questions` as the service
boundary. Pass the numeric limit into the user or system prompt so the
model is asked for the same bound the service will enforce. If the parsed
list is longer than the limit, raise; do not slice.

When the limit is zero, return the empty decision immediately and do not
construct an OpenAI client or send a request.

The LLM prompt should instruct the model to:

- assess ambiguity rather than asking questions by default;
- return only questions that materially improve research quality;
- avoid overlapping questions;
- focus on answerable research scope;
- never ask for secrets or sensitive personal information;
- return no questions when the topic is already clear.

Those instructions are defense in depth. The post-parse invariants are the
contract.

Wrap provider exceptions and missing `output_parsed` as `ClarificationError`
with a generic message. Preserve the original exception with `from err`
for traceback, not for user-visible text.

## Success criteria

- Clear topics produce a valid no-question decision.
- Ambiguous topics produce one or more focused, structured questions.
- Question count never exceeds the configured limit.
- Limit zero skips the LLM and returns an empty decision.
- Questions have service-owned identifiers and purpose text suitable for
  PI-04.
- Contradictory, oversized, duplicate, secret-seeking, or malformed model
  output is rejected with `ClarificationError`.
- OpenAI failures and empty parsed responses surface as `ClarificationError`
  without leaking raw provider or model content.
- Topic text stays in a delimited user message; the system prompt stays
  static.
- Unit tests cover the cases listed under Tests.
- No existing endpoint behavior changes before PI-04 and PI-05 adopt the
  clarification flow.

## Tests

Mock the OpenAI client. Cover at least:

- a clear topic → `needs_clarification=false`, empty list, no repair;
- an ambiguous topic → one or more valid questions, ids `q1`…`qn` or
  equivalent, count ≤ limit;
- parsed list longer than the limit → `ClarificationError` (not a truncated
  success);
- `needs_clarification=true` with an empty list, or `false` with a non-empty
  list → `ClarificationError`;
- missing `output_parsed` → `ClarificationError`;
- provider/API failure → `ClarificationError` with a generic message;
- `max_clarification_questions=0` → no `responses.parse` call, empty
  decision;
- topic empty or over `TOPIC_MAX_LENGTH` → rejected before the LLM call;
- duplicate question text → `ClarificationError`;
- oversized question or purpose → `ClarificationError`;
- HTML, `javascript:`, or control characters in question text →
  `ClarificationError`;
- secret-seeking questions (API key, password, SSN, and similar) →
  `ClarificationError`;
- prompt-injection topic that tries to override the system rules → either a
  valid in-contract decision or `ClarificationError`, never secret-seeking
  questions and never a silent pass of disallowed fields.

## Delivery plan

1. Define clarification schemas, id rules, field bounds, and
   `ClarificationError`.
2. Implement the OpenAI-backed decision service with injectable client,
   delimited untrusted topic, limit-zero short-circuit, and post-parse
   invariant enforcement (raise, do not repair).
3. Add tests for valid decisions, caps, invariant failures, adversarial
   content, and API failures.
4. Export the service, schemas, and error type from the clarification
   package.
5. Run the full backend test suite and linting.
6. Update this plan with implementation notes and completed exit criteria.
7. Open the PI-03 pull request once all exit criteria are complete.

## Exit criteria

- [ ] Clarification schemas and invariants are implemented, including id
      format, field max lengths, and secret-seeking rejection.
- [ ] The decision service uses structured LLM output, a static system
      prompt, a delimited untrusted topic, and `ClarificationError`.
- [ ] Configured question limits are enforced by rejection, not truncation.
      Limit zero skips the LLM.
- [ ] Tests cover all required decision, failure, and adversarial cases.
- [ ] Existing backend behavior remains unchanged.
- [ ] Full backend tests and linting pass.
- [ ] No secrets or unrelated story changes are included.
- [ ] This plan reflects the final design.
- [ ] Pull request is opened from `pi-03-clarification-decision` and links to
      this document.
