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
- Add unit tests with mocked OpenAI responses.

### Out of scope

- Rendering questions or collecting answers in the frontend (PI-04).
- Passing answers into Planner, Searcher, Writer, or Agent orchestration
  (PI-05 and later).
- Selecting Code or Agent mode (PI-06).
- Persisting clarification sessions or user history.
- Asking follow-up questions after the user has submitted answers.
- Replacing the existing `/research` endpoint flow.

## Documentation rigor

**Required level: medium-high.**

This feature introduces an LLM decision into the user workflow and can create
friction or poor research results if it asks unnecessary, vague, or excessive
questions. The implementation is small, but its output becomes a contract for
the UI and later orchestration stories. The plan therefore requires explicit
schemas, question-quality rules, hard bounds, malformed-output handling, and
tests for clear, ambiguous, over-limit, and failed responses.

## Requirements

### Decision contract

The clarification service must return a structured decision containing:

- `needs_clarification`: whether the topic needs user input before research;
- `questions`: zero or more focused questions;
- enough stable question metadata for PI-04 to associate submitted answers with
  the correct question.

Questions should also include a short purpose or rationale so the UI and later
evaluation can understand what ambiguity each question addresses.

### Decision behavior

- Clear, sufficiently scoped topics return no questions.
- Ambiguous topics return a small set of questions targeting scope,
  geography, timeframe, audience, comparison criteria, or desired outcome.
- Questions must be answerable by the user and must not ask for secrets or
  sensitive personal information.
- Questions must not duplicate one another.
- The service must never return more questions than the configured
  `max_clarification_questions` limit.
- A decision that says clarification is unnecessary must expose an empty
  question list.
- A decision that requires clarification must contain at least one question
  unless the configured limit is zero.

### Error behavior

If the LLM call fails or returns no parseable structured result, the service
must raise an explicit error for the caller. It must not silently treat the
failure as a clear topic or continue with a success-shaped response.

## Proposed design

Add a dedicated clarification package, for example
`backend/app/clarification/`, with:

- `schemas.py` for `ClarificationQuestion` and `ClarificationDecision`;
- `service.py` for the OpenAI-backed decision function;
- `__init__.py` for the public exports.

Follow the Planner service pattern: inject an optional `OpenAI` client for
tests, call `responses.parse` with the structured decision model, and raise a
clear `ValueError` when `output_parsed` is missing.

Use PI-01's `ExecutionLimits.max_clarification_questions` as the service
boundary. The service may also define a safe default for callers that do not
yet construct a full `ResearchRun`. Apply the cap after parsing as a defense in
depth, while ensuring the prompt also requests the same bound.

The LLM prompt should instruct the model to:

- assess ambiguity rather than asking questions by default;
- return only questions that materially improve research quality;
- avoid overlapping questions;
- focus on answerable research scope;
- return no questions when the topic is already clear.

The service should validate decision invariants after parsing instead of
silently repairing contradictory output. If a result violates the contract,
raise an explicit validation error.

## Success criteria

- Clear topics produce a valid no-question decision.
- Ambiguous topics produce one or more focused, structured questions.
- Question count never exceeds the configured limit.
- Questions have stable identifiers and purpose text suitable for PI-04.
- Contradictory or malformed model output is rejected explicitly.
- OpenAI failures and empty parsed responses surface as errors.
- Unit tests cover clear, ambiguous, over-limit, invalid, and failed responses.
- No existing endpoint behavior changes before PI-04 and PI-05 adopt the
  clarification flow.

## Delivery plan

1. Define clarification schemas and invariants.
2. Implement the OpenAI-backed decision service with injectable client and
   limit enforcement.
3. Add tests for valid decisions, caps, invariant failures, and API failures.
4. Export the service and schemas from the clarification package.
5. Run the full backend test suite and linting.
6. Update this plan with implementation notes and completed exit criteria.
7. Open the PI-03 pull request once all exit criteria are complete.

## Exit criteria

- [ ] Clarification schemas and invariants are implemented.
- [ ] The decision service uses structured LLM output and explicit errors.
- [ ] Configured question limits are enforced.
- [ ] Tests cover all required decision and failure cases.
- [ ] Existing backend behavior remains unchanged.
- [ ] Full backend tests and linting pass.
- [ ] No secrets or unrelated story changes are included.
- [ ] This plan reflects the final design.
- [ ] Pull request is opened from `pi-03-clarification-decision` and links to
  this document.
