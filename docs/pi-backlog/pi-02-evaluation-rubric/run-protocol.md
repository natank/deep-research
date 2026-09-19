# PI-02 Paired-Run Protocol

## Objective

Compare Code and Agent orchestration under matched conditions using the topics
and rubric in this folder.

## Fixed conditions

For every paired comparison, keep these inputs fixed:

- exact topic prompt;
- clarification answers, or an explicit record that no clarification was used;
- OpenAI model and relevant prompt/configuration version;
- Tavily configuration and source limits;
- execution limits from the shared PI-01 contracts;
- reviewer instructions and rubric version.

Record the run date and time because current topics can produce different web
results over time.

## Procedure

For each topic:

1. Create the research context and decide whether clarification is needed.
2. Capture the exact topic and answers before running either mode.
3. Run Code orchestration once.
4. Run Agent orchestration once with the same context and limits.
5. Record raw outputs, source URLs, run metrics, status, and errors.
6. Score both outputs independently before discussing differences.
7. Compare sources, conclusions, search behavior, and operational metrics.
8. Record any non-comparable condition or manual intervention.

Use the same order for both modes where practical. If order could affect an
external result, alternate the order for repeated runs and record it.

## Repetitions

Run each mode at least twice for the full five-topic set when API budget and
availability allow. A single run may be used only for an exploratory smoke
test and must not be treated as repeatability evidence.

If fewer than two repetitions are completed, state that limitation in the
findings and do not draw conclusions about consistency.

## Failure handling

Record a run as failed or incomplete when it:

- returns an API or application error;
- exceeds a configured limit;
- produces no usable report;
- loses required source attribution;
- requires an undocumented manual intervention.

Do not silently retry and replace the original result. Retries must have their
own run record and should identify the reason for retrying.

Incomplete runs can still contribute to reliability and failure-behavior
findings. Do not assign unsupported quality scores to missing outputs.

## Measurements

Capture the following from each run where available:

- orchestration mode;
- topic and clarification context;
- completion status and failure category;
- duration;
- search, source, tool-call, and agent-iteration counts;
- API call and token counters;
- returned source URLs;
- reviewer scores and concrete observations.

Keep raw metrics separate from reviewer judgments. A faster run is not better
if it produces materially lower-quality or unsupported results.

## Review process

Two reviewers should score each completed paired run independently when
available. Resolve differences by discussing the specific report evidence, not
by averaging away disagreements without explanation. Record the final score,
initial score range, and notable disagreement in the result record.

## Reporting

Summarize findings at three levels:

1. **Run level:** exact outcome and metrics.
2. **Topic level:** paired quality scores, source differences, and tradeoffs.
3. **Overall:** patterns, exceptions, limitations, and a cautious recommendation.

The dataset is intentionally small. Findings describe observed behavior in this
demo and must not be presented as general proof that one orchestration method
always outperforms the other.
