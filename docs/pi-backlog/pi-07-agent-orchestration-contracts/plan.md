# PI-07 Plan: Bounded Agent Tools and Stopping Rules

## Story

**As a product team, we want explicit, bounded contracts for Agent tools and
termination so that PI-08 can add autonomous research without allowing
uncontrolled tool use, cost growth, or invalid report output.**

**Story type:** Enabler  
**Priority:** Must  
**Dependencies:** PI-01  
**Branch:** `pi-07-agent-orchestration-contracts`

## Scope

### In scope

- Define typed Agent action, tool input, tool result, and execution-state
  contracts under the shared research/agent boundary.
- Map every allowlisted action onto server-owned PI-01 `ExecutionLimits`
  counters, plus a small server constant for report attempts.
- Define the only operations PI-08 may invoke: `search`, `inspect_source`,
  `revise_plan`, `write_report`, and `finish`.
- Restrict `inspect_source` to a server-assigned `source_id` and the existing
  Tavily/searcher extract path — not a model URL and not a general HTTP
  client.
- Define plan revision as query-list mutation only.
- Define terminal **success** as one validated `Report` from `write_report`
  over server-held evidence; every other stop is typed failure.
- Add unit tests for valid/invalid actions, limit accounting, result bounds,
  terminal states, SSRF-style inspect arguments, and untrusted provider
  content.
- Document PI-08 integration rules and residual risks in this plan.

### Out of scope

- Calling an LLM in an Agent loop or replacing PI-06’s Agent 501 (PI-08).
- Changing the Code pipeline (Planner, Searcher, Writer, Emailer).
- Adding Emailer, filesystem, shell, code execution, or arbitrary HTTP as
  Agent tools. PI-08 may send email **after** a successful report, outside
  the tool loop.
- A public cancel endpoint or job API. Timeout/cancel exist only as terminal
  reason codes for PI-08 to map from the existing request timeout.
- Browser/UI progress (PI-09), metrics (PI-10), or comparison runs (PI-11).
- Client-configurable limits, tools, model, or provider. Unauthenticated
  Agent cost remains a PI-08 residual bounded by these caps.

## Documentation rigor

**Required level: high.**

These contracts are the security boundary for an LLM-controlled path. Tool
names, arguments, result sizes, counters, and terminal transitions must be
allowlisted and validated independently of model output. PI-08 must hard-stop
without trusting the model to self-limit, inspect without opening SSRF, and
succeed only with a real report.

## Requirements

### Agent execution state

Typed in-memory state contains:

- validated `ResearchContext` (immutable for the run);
- a copy of server-owned `ExecutionLimits` from the `ResearchRun` (defaults
  from `ExecutionLimits()`, never request fields);
- current search-plan queries and a revision count;
- collected sources as bounded envelopes (`source_id`, `SourceArticle`
  fields with size caps);
- counters: iterations, tool calls, searches, sources, report attempts;
- terminal status and a safe reason code.

State must not hold API keys, client provider settings, arbitrary tool
names, system-prompt text, raw provider payloads, or `OrchestrationMode` as
research content. Mode stays dispatch metadata for PI-08.

### Allowlisted actions

Discriminated union, `extra="forbid"`, exactly:

1. **`search`** — Tavily search from validated query strings. Queries are
   not URLs and must not be fetched.
2. **`inspect_source`** — extra bounded content for a **`source_id` already
   in this run’s state**. The model must not pass a URL. The executor looks
   up the id and calls Tavily/searcher extract (or the existing searcher
   helper), never `httpx`/`requests`/open-ended HTTP. Unknown ids, extra
   `url` fields, `file://`, localhost, and link-local/metadata hosts are
   rejected with **no** network call.
3. **`revise_plan`** — replace or append the **query list only**, within
   count/length/C0/delimiter rules. Cannot change topic, answers, limits,
   sources, permissions, or terminal status.
4. **`write_report`** — produce the existing `Report` from
   `format_research_context(state.context)` plus collected sources in a
   separate sources block. Ignore any model-supplied source list,
   recipient, path, email target, provider, or extra instructions. Answers
   remain scope, not sources.
5. **`finish`** — stop the loop. Without a validated report already
   produced by `write_report`, the outcome is **failure**.

Unknown operations are rejected before I/O. After a terminal success or
failure, further actions are rejected.

### Input and result bounds

- Search queries: nonblank, same C0 and `</untrusted-` rules as PI-05,
  max length 200, max stored queries 8 (aligned with today’s planner cap
  and `max_searches`).
- `search` goes only to `TavilyClient.search` (or the current searcher
  wrapper).
- Results normalize to `SourceArticle` plus a server-assigned `source_id`.
  Cap title/url/content (content on the order of a few thousand
  characters). Provider text is untrusted data, not instructions.
- Store only these envelopes in state; never raw Tavily/OpenAI bodies or
  credentials.
- PI-08 must place envelopes in the tool/user role inside delimiters, not
  in the system prompt. This story defines the envelope so that path is
  possible.

### Limits and stopping rules

Use PI-01 defaults: `max_searches=8`, `max_sources=8`, `max_tool_calls=12`,
`max_agent_iterations=5`. Add a **server constant** `MAX_REPORT_ATTEMPTS = 2`
(not a request field). Optionally clamp `ExecutionLimits` with a modest
ceiling so internal callers cannot set `max_tool_calls=10**9`.

Accounting (check **and reserve** the counter in state **before** I/O;
failed I/O still consumes the reservation):

- each PI-08 model round increments `iterations`;
- `search` increments `searches` and `tool_calls`; collected sources stay
  ≤ `max_sources`;
- `inspect_source` and `revise_plan` increment `tool_calls`;
- `write_report` increments `report_attempts` and `tool_calls`.

Retries: at most **one** retry per operation, not model-controlled, and
each retry consumes `tool_calls`. Invalid actions never call a provider;
after **three** invalid actions, terminate as failure.

Stop with a typed terminal outcome when:

- `write_report` returns a validated `Report` → **success**;
- `finish` with no such report, limit hit, third invalid action, provider
  failure after the retry policy, or mapped request timeout → **failure**.

No limit exhaustion or `finish` may look like a successful partial report.
PI-08 maps failures to the existing generic 502 and must not fall back to
Code.

### Failure policy

- Validation and limit errors use reason codes only. Exception messages
  must not include topic, query, URL, source content, or provider bodies.
- Provider failures become typed tool failures; logs record exception
  **class** only.
- Timeout is a terminal reason on state (`timed_out`). Cancellation is the
  same class of reason (`cancelled`) for PI-08; this story does not add an
  HTTP cancel route.

## Proposed module design

Add `backend/app/agent/`, keeping shared primitives in
`backend/app/research/schemas.py` when both modes need them:

- `schemas.py` — action union (`extra="forbid"`), result envelopes,
  execution state, terminal outcome, reason codes;
- `limits.py` — `ExecutionLimits()` defaults, report-attempt constant,
  preflight reserve/increment;
- `validation.py` — action/result checks, `source_id` lookup, query
  normalization;
- `exceptions.py` — contract, limit, timeout, and provider errors with
  safe messages;
- a small **executor interface** whose methods PI-08 will call. The
  executor receives a server-built `ResearchRun`, not the HTTP body, and
  owns Tavily/Writer calls. This story can ship the interface and fakes;
  it must not run an LLM loop.

The Code orchestrator must not import Agent handlers.

## PI-08 integration

- Replace only the PI-06 Agent 501 branch with a loop over these
  contracts. Do not read `limits`/`tools` from the request.
- Static system prompt; context via `format_research_context`; tool
  results in delimited user/tool messages.
- Emailer runs after terminal success, not as a tool.
- Unauthenticated Agent is a cost switch; these caps are the demo bound.
- Indirect prompt injection via Tavily snippets is accepted residual;
  envelopes and role/delimiters reduce it, they do not prove obedience.

## Success criteria

- PI-08 has typed contracts for every allowlisted action and result.
- `inspect_source` accepts only a known `source_id` and never a URL or
  generic HTTP fetch.
- `revise_plan` can change queries only.
- Every operation has a pre-I/O limit check and a bounded result envelope.
- Terminal success is only a validated `Report` from `write_report` over
  server-held sources.
- Invalid, unknown, extra-field, over-limit, and post-terminal actions are
  rejected deterministically with reason codes.
- Existing Code tests and behavior remain unchanged.

## Test plan

### Contract and validation

Cover at least:

- each valid action parses with only allowlisted fields;
- unknown names, malformed discriminators, extra fields (`url` on inspect,
  `limits` on any action), blank/C0/delimiter queries, and oversized text
  are rejected;
- search results become bounded envelopes with server `source_id`s;
- inspect accepts a known id and rejects unknown ids, model URLs,
  `file://`, `127.0.0.1`, and metadata hosts with no network call;
- `revise_plan` cannot mutate context, limits, or sources;
- `write_report` results validate as `Report` and ignore model-supplied
  sources/recipient;
- `finish` without a report is failure; success then rejects further
  actions.

### Limits and failures

Cover at least:

- counters reserved before I/O and not exceeded;
- retries consume `tool_calls`;
- three invalid actions terminate without provider calls;
- provider failures are typed and exception text has no query/URL/body;
- timeout reason is terminal;
- limit exhaustion and `finish` without a report are not success.

### Regression

- Existing backend suite passes.
- Code orchestration does not import Agent tool handlers.

## Delivery plan

1. Define the agent package, action union, envelopes, and state.
2. Add limit accounting mapped to PI-01 fields plus report-attempt cap.
3. Add validation: queries, `source_id` inspect, query-only plan revision,
   write/finish success rules.
4. Add typed failure, retry, invalid-action threshold, and timeout
   reasons.
5. Add contract, SSRF-negative, limit, and Code regression tests.
6. Record PI-08 rules and residuals in this plan (this document).
7. Run backend tests and lint; do not add Agent execution.
8. Open the PI-07 pull request after exit criteria pass.

## Exit criteria

- [x] Typed actions, envelopes, state, and terminal outcomes exist.
- [x] Only the five allowlisted operations parse; extra fields are
      forbidden.
- [x] Inspect is `source_id` → Tavily/searcher extract only.
- [x] Limits are server-owned, mapped per action, checked before I/O, and
      immutable per run.
- [x] Success is only a validated `Report` from `write_report`; other stops
      are typed failure.
- [x] Invalid actions, provider failures, timeout, and limit exhaustion
      use reason codes without sensitive exception text.
- [x] No Agent loop or Code-path behavior changes.
- [x] Contract, bounds, inspect-negative, failure, and regression tests
      pass.
- [x] Backend test suite and Ruff pass.
- [x] No secrets or unrelated story changes are included.
- [x] This plan documents PI-08 constraints and residual risks.
- [ ] Pull request is opened from `pi-07-agent-orchestration-contracts`
      and links to this document.

## Implementation notes

- Added `backend/app/agent` contracts with strict discriminated actions,
  bounded source envelopes, typed terminal outcomes, and a provider-facing
  executor protocol. The package is not imported by the Code orchestrator.
- Added pre-I/O reservations for iterations, tool calls, searches, retries,
  plan revisions, report attempts, source capacity, and invalid-action
  termination. Limits are taken from a server-built run and cannot be changed
  by an action.
- Restricted source inspection to server-assigned `source_id` values and
  rejected model URL fields, prompt delimiters, control characters, and
  unknown source references before network access.
- Added typed provider, timeout, cancellation, invalid-action, limit, and
  finish-without-report outcomes. Only a validated `Report` transitions state
  to terminal success.
- Validation passed: 80 backend tests and Ruff. The existing Starlette/httpx
  deprecation warning remains non-blocking.
