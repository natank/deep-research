# PI-02 Plan: Evaluation Rubric and Comparison Dataset

## Story

**As a product team, I need a repeatable rubric and representative topic set
so that Code and Agent orchestration can be compared using evidence rather than
anecdotal impressions.**

**Story type:** Spike  
**Priority:** Must  
**Dependencies:** None  
**Branch:** `pi-02-evaluation-rubric`

## Scope

### In scope

- Define a practical rubric for report quality, source quality, reliability,
  efficiency, repeatability, and adaptability.
- Define representative research topics covering clear, ambiguous,
  comparative, current, and evidence-sensitive requests.
- Define the run protocol for comparing Code and Agent modes fairly.
- Define which measurements come from run metrics and which require human
  assessment.
- Define a result-recording template and a recommendation format.
- Document limitations and sources of evaluation bias.

### Out of scope

- Implementing an automated evaluator or scoring service.
- Changing the research pipeline or orchestration behavior.
- Running the full comparison study (PI-11).
- Selecting a permanent production default based on this spike alone.
- Creating new external datasets or making claims about factual topic answers.

## Documentation rigor

**Required level: medium-high.**

This is a discovery spike, but its outputs determine how the most important PI
tradeoffs are judged. The rubric must be specific enough for two reviewers to
score the same output similarly, while remaining small enough to use during a
portfolio-demo evaluation. The topic set must exercise materially different
research behaviors without becoming a statistically unsupported benchmark.

The delivered documentation must therefore include scoring anchors, a
repeatable run protocol, topic rationale, result templates, and explicit
limitations. Automated code tests are not required, but the documents should
be internally consistent and reviewed before PI-11 begins.

## Requirements

### Evaluation dimensions

The rubric must assess at least:

1. **Relevance:** the report answers the requested topic and respects any
   clarified scope.
2. **Completeness:** important dimensions and requested comparisons are covered.
3. **Source quality:** sources are credible, relevant, current where needed, and
   appropriately diverse.
4. **Citation coverage:** factual claims can be traced to the returned sources.
5. **Reliability:** the run completes, handles failures clearly, and respects
   configured limits.
6. **Efficiency:** duration, search/tool calls, token usage, and source counts
   are recorded where available.
7. **Repeatability:** repeated runs with the same inputs produce acceptably
   consistent outcomes.
8. **Adaptability:** the orchestration responds appropriately when initial
   evidence is incomplete, conflicting, or points to a useful new angle.

Each qualitative dimension must have a defined score range and anchors for low,
middle, and high performance. Operational dimensions must state how they are
measured and whether lower or higher values are preferred.

### Comparison topics

The initial dataset must include these five topics:

1. **Clear trend:** “How has global solar power capacity changed since 2015?”
2. **Ambiguous scope:** “What are the benefits and risks of artificial
   intelligence in education?”
3. **Multi-dimensional comparison:** “Compare solid-state, lithium-ion, and
   sodium-ion batteries for electric vehicles.”
4. **Current and fast-changing:** “What are the latest major developments in
   reusable launch vehicles?”
5. **Evidence-sensitive:** “What does current research say about the
   effectiveness of remote work on productivity?”

Each topic must document why it is included, what a good report should cover,
which risks or failure modes it probes, and whether clarification is expected.

### Run protocol

The protocol must specify:

- identical topic and clarification inputs for comparable runs;
- the Code and Agent modes being evaluated;
- fixed execution limits and model/configuration details;
- how many repetitions are required for repeatability;
- how failed or incomplete runs are recorded;
- separation of automated metrics from reviewer scores;
- how conflicting reviewer assessments are resolved;
- how results are summarized without overstating significance.

The protocol should favor paired comparisons: run both modes for the same topic
under the same conditions before comparing results.

### Result artifacts

The spike must define templates for:

- one run record;
- one topic-level comparison;
- an overall findings summary;
- a recommendation with confidence and known limitations.

Records must not include API keys, private user data, or unnecessary source
content copied into committed documentation.

## Proposed design

Store the spike outputs alongside this plan:

- `rubric.md` — dimensions, scoring anchors, metric definitions, and reviewer
  guidance;
- `topics.md` — the comparison dataset, topic rationale, expected behaviors,
  and clarification expectations;
- `run-protocol.md` — setup, paired-run procedure, repetition rules, and
  failure handling;
- `result-template.md` — structured template for PI-11 observations.

Keep the rubric human-readable and independent of a particular orchestration
implementation. Use the shared fields from PI-01 where applicable:
orchestration mode, search count, source count, tool calls, agent iterations,
duration, completion status, and API usage counters.

## Success criteria

- A reviewer can score a report using the rubric without inventing missing
  criteria.
- Every score dimension has clear anchors and a defined measurement method.
- The five topics cover the agreed research patterns and include rationale.
- The paired-run protocol controls topic, inputs, limits, and configuration.
- The protocol defines handling for failures, non-comparable runs, and repeated
  results.
- Result templates capture both quantitative metrics and qualitative findings.
- The documents identify important limitations and avoid unsupported claims
  about statistical significance.
- PI-11 can begin without needing to make unresolved evaluation-policy
  decisions.

## Delivery plan

1. Draft the scoring dimensions, anchors, and metric definitions in `rubric.md`.
2. Document the five-topic dataset and expected behaviors in `topics.md`.
3. Define the paired-run and repeatability procedure in `run-protocol.md`.
4. Add the run, topic comparison, and findings templates in
   `result-template.md`.
5. Review the documents for consistency with PI-01 contracts and the PI
   backlog.
6. Record unresolved limitations or decisions explicitly.
7. Open the PI-02 pull request once all exit criteria are complete.

## Exit criteria

- [x] `rubric.md` defines all required dimensions, scoring anchors, and metric
  collection methods.
- [x] `topics.md` contains all five representative topics, rationale, expected
  behaviors, and clarification expectations.
- [x] `run-protocol.md` defines paired runs, repetitions, fixed conditions, and
  failure handling.
- [x] `result-template.md` supports run-level, topic-level, and overall
  findings.
- [x] Limitations, reviewer guidance, and unresolved decisions are documented.
- [x] The artifacts are consistent with PI-01 and contain no secrets or
  unnecessary private/source content.
- [ ] Pull request is opened from `pi-02-evaluation-rubric` and links to this
  document.

## Delivery notes

- The five topics are intentionally a small demonstration dataset, not a
  statistically significant benchmark.
- The protocol requires paired runs and recommends two repetitions per mode and
  topic when API budget allows.
- Quality dimensions use a 1-5 anchored scale; operational dimensions remain
  raw measurements with explicit tradeoff discussion.
