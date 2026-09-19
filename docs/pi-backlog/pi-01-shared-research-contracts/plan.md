# PI-01 Plan: Shared Research Context and Run Contracts

## Story

**As a research workflow, I need shared contracts for research context,
orchestration, run state, limits, and metrics so that clarification and
code/agent execution can evolve without duplicating or loosely defining state.**

**Story type:** Enabler  
**Priority:** Must  
**Dependencies:** None  
**Branch:** `pi-01-shared-research-contracts`

## Scope

### In scope

- Define a shared research context containing the original topic and optional
  clarification answers.
- Define an explicit orchestration mode for the code and agent paths.
- Define run status values and a structured representation of run state.
- Define configurable execution limits for questions, searches, sources, tool
  calls, and agent iterations.
- Define metrics fields needed to compare orchestration modes.
- Preserve the current request and response behavior for existing clients.
- Add model-level tests for valid values, defaults, and validation failures.

### Out of scope

- Generating clarification questions (PI-03).
- Rendering or submitting clarification answers in the frontend (PI-04).
- Implementing agent tools or agent execution (PI-07 and PI-08).
- Persisting run state or metrics in a database.
- Changing the current synchronous execution behavior.
- Adding user authentication or multi-user run ownership.

## Documentation rigor

**Required level: medium.**

This is a shared-contract enabler with moderate compatibility risk. The
implementation is expected to be small, but errors in names, defaults, or
serialization could affect every subsequent PI story. The plan therefore
requires explicit field definitions, validation rules, backward-compatibility
tests, and examples of serialized request/response shapes. A separate
architecture decision record is not required unless implementation reveals
competing approaches that materially affect later stories.

## Requirements

### Research context

The shared context must support:

- the required original topic;
- optional clarification answers;
- a normalized form suitable for planner, agent, and writer inputs.

Clarification data must be optional so a direct research run remains valid.
Answers must retain enough structure to associate each answer with its
question, rather than being represented only as an unstructured concatenated
string.

### Orchestration mode

The contract must distinguish at least:

- `code`: the existing deterministic Planner → Searcher → Writer → Emailer
  workflow;
- `agent`: LLM-directed orchestration with bounded tools.

The model should be extensible for a comparison mode or future strategies
without requiring consumers to use untyped strings.

### Run status

The contract must represent the lifecycle needed by the UI and future metrics,
including a not-started/accepted state, active execution, successful
completion, and failure. Status values must be finite and validated.

### Execution limits

Limits must be explicit and have safe defaults for the demo. They should cover
the controls required by the PI backlog, including maximum clarification
questions, searches, sources, tool calls, and agent iterations. Limits must be
non-negative and should reject invalid configurations rather than silently
falling back.

### Metrics

Metrics must support comparison without storing secrets. The initial contract
should allow recording orchestration mode, search count, source count, agent
iteration/tool-call count where applicable, duration, completion status, and
API usage counters when available. Exact provider billing fields are not
required for this story.

### Compatibility

The existing `POST /research` request with a topic string and the current
`ResearchResult` response shape must continue to validate. New fields should
be optional or have safe defaults until the dependent stories explicitly adopt
them. Existing frontend types and current component tests must not require
changes solely because these internal contracts are introduced.

## Proposed design

Place shared backend models in a new contract module, for example
`backend/app/research/schemas.py`, rather than coupling them to Planner,
Searcher, or Writer. Keep domain-specific models in their existing modules.

The proposed model boundaries are:

- `ClarificationAnswer`: question identifier/text and user answer;
- `ResearchContext`: topic plus optional clarification answers;
- `OrchestrationMode`: validated enum for `code` and `agent`;
- `RunStatus`: validated lifecycle enum;
- `ExecutionLimits`: bounded integer limits with demo-safe defaults;
- `RunMetrics`: optional counters and timing fields;
- `ResearchRun`: context, mode, status, limits, and metrics.

The current `ResearchRequest` and `ResearchResult` models remain compatible.
PI-03 and later stories may adopt `ResearchContext` and `ResearchRun` at the
API boundary after the contracts are established and tested.

## Success criteria

- Shared models exist in a neutral module and are not owned by a single
  pipeline component.
- Valid code and agent modes serialize consistently.
- Invalid modes and run statuses are rejected with clear validation errors.
- Direct topics with no clarification answers remain valid.
- Execution limits have documented defaults and reject invalid values.
- Metrics can represent both code and agent runs without secret values.
- Existing endpoint, planner, searcher, writer, orchestrator, and frontend
  tests remain passing without behavior regressions.
- Tests cover serialization, defaults, invalid values, and backward-compatible
  current request/response shapes.
- The final implementation and tests match this plan, or the plan is updated
  before the story is closed.

## Delivery plan

1. Confirm field names, enum values, and default limits against PI-03, PI-06,
   PI-07, and PI-10 consumers.
2. Add the neutral backend contract module and exports.
3. Add validation and serialization tests.
4. Add compatibility tests for the existing research request and result.
5. Run the targeted backend test suite and lint checks.
6. Update this plan with any design deviations.
7. Open the PI-01 pull request once all exit criteria are complete.

## Exit criteria

- [ ] All in-scope contracts are implemented and documented.
- [ ] Validation and backward-compatibility tests are passing.
- [ ] Existing backend and frontend behavior is unchanged.
- [ ] Targeted tests and linting pass.
- [ ] No secrets or unrelated story changes are included.
- [ ] This plan reflects the final design.
- [ ] Pull request is opened from `pi-01-shared-research-contracts` and links
  to this document.
