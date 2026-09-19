# Product Increment Kickoff: Interactive and Agentic Research

## Purpose

This product increment (PI) builds on the existing Deep Research demo by making
research more interactive and by exploring alternative orchestration strategies.
The increment should improve the relevance of generated reports while creating a
clear, evidence-based comparison between predictable code orchestration and
more flexible LLM-based orchestration.

## Product goals

- Help users refine an ambiguous or broad research topic before searching.
- Enable the system to make more dynamic research decisions as evidence is
  collected.
- Preserve a dependable baseline so that changes in report quality and
  reliability can be measured.
- Produce useful implementation learnings about when agentic orchestration is
  worth its additional complexity and variability.

## Recommended PI planning approach

Use **vertical-slice planning with a protected baseline**. The current
code-driven orchestration remains the reference implementation while each new
capability is delivered end to end across the UI, API, orchestration layer, and
evaluation workflow.

### Delivery sequence

1. Define shared contracts, safety limits, run metrics, and the evaluation
   rubric.
2. Add clarifying questions while preserving the existing code-driven flow.
3. Add user-selectable **Code** and **Agent** orchestration modes.
4. Implement the agent with bounded tools and autonomous search-plan revision.
5. Run both modes against the representative comparison topics.
6. Document the findings, tradeoffs, and recommended use cases for each mode.

This approach delivers visible product value early, protects existing behavior,
and evaluates the agent through complete user journeys rather than an isolated
technical prototype. It also makes it possible to compare quality,
reliability, cost, latency, and adaptability without losing the dependable
code-driven path.

## Initial PI backlog

The backlog is ordered by dependency and value. Each item should be delivered
as a reviewable vertical slice where practical, with automated tests and
documentation updated when behavior changes.

| ID | Backlog item | Outcome | Depends on | Priority |
|---|---|---|---|---|
| PI-01 | Define shared research context and run contracts | Common models represent clarification answers, orchestration mode, run status, limits, and metrics without breaking the current API contract. | — | Must |
| PI-02 | Define evaluation rubric and comparison dataset | Agreed measures and representative topics cover relevance, source quality, citation coverage, completion, latency, usage, repeatability, and adaptability. | — | Must |
| PI-03 | Add clarification decision step | The app determines whether a topic needs clarification and returns a bounded set of focused questions. | PI-01 | Must |
| PI-04 | Add clarification UI and answer submission | Users can answer questions, skip unnecessary clarification, and continue to research. | PI-03 | Must |
| PI-05 | Pass clarified context through code orchestration | Answers influence the existing planner, searcher, writer, and report while the baseline flow remains reliable. | PI-04 | Must |
| PI-06 | Add user-selected orchestration mode | Users can select **Code** or **Agent** before starting a research run. | PI-01 | Must |
| PI-07 | Define bounded agent tools and stopping rules | Search, source inspection, and report-generation tools have explicit schemas, limits, failure behavior, and termination conditions. | PI-01 | Must |
| PI-08 | Implement agent orchestration | Agent mode can autonomously revise the search plan, gather evidence, and produce the existing report shape within configured limits. | PI-05, PI-07 | Must |
| PI-09 | Integrate agent mode into the end-to-end UI flow | All users can run the agent path, see progress and failures, and receive the same report, sources, visualization, and download experience. | PI-06, PI-08 | Must |
| PI-10 | Capture comparable run metrics | Both modes record mode, searches, sources, iterations, duration, completion status, and API usage without logging secrets. | PI-06, PI-08 | Should |
| PI-11 | Run the comparison study | Code and Agent modes are run against the agreed topic set with repeat runs where needed. | PI-02, PI-09, PI-10 | Must |
| PI-12 | Publish findings and recommendation | Documentation summarizes tradeoffs, recommended use cases, risks, and follow-up work for each orchestration mode. | PI-11 | Must |

### Backlog completion standard

An item is complete when its user-visible or technical outcome is implemented,
covered by appropriate automated tests, integrated with the existing error
handling and limits, and documented when it changes the supported behavior.

## Features in scope

### 1. Clarifying questions

Before planning searches, the app may ask the user a small number of targeted
questions when the topic is ambiguous, underspecified, or has multiple
reasonable interpretations. Questions should help establish details such as:

- scope, geography, or time period;
- the intended audience or level of detail;
- the desired comparison, outcome, or point of view.

The user can answer the questions and continue, or proceed with the original
topic when clarification is unnecessary. The answers become part of the
research context supplied to the planner and report writer.

### 2. Agent-based orchestration

Add an orchestration mode in which an LLM coordinates research activities rather
than relying exclusively on the fixed application workflow. The agent may
decide which search to run next, whether additional evidence is needed, and
when the available sources are sufficient to write the report.

The agent must operate through explicit, bounded tools and retain the existing
source limits, error handling, and report contract. It should not bypass source
attribution or create unsupported claims.

### 3. Orchestration comparison

Keep the current code-driven pipeline as a control implementation and compare
it with the agent-driven implementation. The comparison should consider:

- report relevance and completeness;
- source quality, diversity, and citation coverage;
- successful completion and failure behavior;
- latency and API usage;
- repeatability and ease of debugging;
- ability to adapt searches to unexpected findings.

The result should be documented as product and engineering findings rather than
assuming that either approach is universally better.

## Proposed user flows

### Clarified research

1. The user enters a research topic.
2. The app evaluates whether clarification is needed.
3. If needed, the app asks focused questions.
4. The user answers and starts the research run.
5. The selected orchestration mode plans and executes searches.
6. The app displays the report, sources, visualization, and simulated email
   result as it does today.

### Direct research

For clear topics, the app skips questions and starts research immediately. This
keeps the existing low-friction experience.

### Orchestration selection

For the experiment, the UI or a configuration setting should make the
orchestration mode explicit, such as **Code**, **Agent**, or **Compare**. The
default should remain the code-driven pipeline until the agent path is proven
reliable.

## Initial technical direction

- Extend the research request and response models to represent clarification
  state and user answers.
- Add a clarification component that returns either “no questions” or a
  bounded list of questions.
- Keep the existing Planner → Searcher → Writer → Emailer path intact as the
  reference implementation.
- Add an agent orchestrator with narrowly scoped tools for search, source
  inspection, and report generation.
- Enforce maximum questions, search calls, sources, and iteration count.
- Record the selected mode and basic run metrics so the two approaches can be
  evaluated consistently.
- Reuse the current source and report schemas wherever possible.

## Success criteria

- Users can complete a research run after answering clarifying questions.
- Clear topics can still proceed without unnecessary questions.
- Clarification answers affect the resulting search plan and report.
- Code and agent orchestration produce the same required report shape and
  source links.
- The agent cannot exceed configured tool, search, source, or iteration limits.
- Failures are surfaced clearly and do not silently produce an incomplete
  report.
- A repeatable comparison using representative topics identifies strengths,
  weaknesses, and recommended use cases for each orchestration method.
- Existing code-driven behavior and its automated tests remain functional.

## Suggested workstreams

1. Define clarification states, question limits, and UI interaction.
2. Implement clarification generation and incorporate answers into context.
3. Define the agent tool contract, limits, and stopping conditions.
4. Implement the agent orchestrator behind the existing report contract.
5. Add mode selection and run metadata.
6. Create a comparison test set and capture quality, reliability, latency, and
   usage observations.
7. Document the recommendation and update the user-facing setup and usage
   documentation.

## Risks and guardrails

- **Unnecessary friction:** skip clarification for sufficiently clear topics.
- **Agent loops or cost growth:** enforce hard iteration and tool-call limits.
- **Unsupported claims:** require the writer to ground claims in returned
  sources and preserve source links.
- **Nondeterministic behavior:** retain the code path and compare repeated runs.
- **Hard-to-debug failures:** log orchestration mode, tool actions, and terminal
  error states without exposing secrets.

## Key decisions for the PI

- **Orchestration selection:** The user selects the orchestration mode. The
  available modes are **Code**, **Agent**, and, where useful, **Compare**.
- **Search-plan autonomy:** The agent may autonomously revise the search plan
  based on the evidence it finds, subject to the configured search, source, and
  iteration limits.
- **Initial availability:** Agent orchestration is exposed to all users in the
  initial release rather than being hidden behind an experiment-only flag.

### Representative comparison topics

The initial comparison should use topics with different levels of ambiguity and
different evidence patterns:

1. **Clear trend:** “How has global solar power capacity changed since 2015?”
2. **Ambiguous scope:** “What are the benefits and risks of artificial
   intelligence in education?”
3. **Multi-dimensional comparison:** “Compare solid-state, lithium-ion, and
   sodium-ion batteries for electric vehicles.”
4. **Current and fast-changing:** “What are the latest major developments in
   reusable launch vehicles?”
5. **Evidence-sensitive:** “What does current research say about the
   effectiveness of remote work on productivity?”

These topics should be evaluated using the same rubric for relevance,
completeness, source quality and diversity, citation coverage, successful
completion, latency, API usage, repeatability, and adaptability.
