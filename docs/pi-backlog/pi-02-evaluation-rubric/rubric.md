# PI-02 Evaluation Rubric

## Purpose

This rubric compares the existing Code orchestration with Agent orchestration
using the same topic, context, limits, and model configuration. It combines
reviewer-scored report qualities with run-level measurements.

## Scoring scale

Qualitative dimensions use a 1-5 scale:

| Score | Meaning |
|---|---|
| 1 | Fails the requirement or provides little usable value |
| 2 | Partially addresses the requirement with substantial weaknesses |
| 3 | Adequate for a demo, with noticeable gaps |
| 4 | Strong result with only minor gaps |
| 5 | Excellent result that fully satisfies the requirement |

Reviewers should score the report and source list produced by each run, not
their expectations about which orchestration method produced it.

## Qualitative dimensions

| Dimension | What to assess | 1-point anchor | 3-point anchor | 5-point anchor |
|---|---|---|---|---|
| Relevance | Whether the report answers the requested topic and respects scope or clarification answers | Mostly answers a different question or ignores scope | Addresses the main question but misses meaningful context | Directly answers the question and consistently respects the requested scope |
| Completeness | Coverage of important aspects, comparisons, time periods, and requested outcomes | Omits most important aspects | Covers the main aspects but has material omissions | Covers the important dimensions with an appropriate level of depth |
| Source quality | Credibility, relevance, freshness, and diversity of sources | Sources are weak, stale, or poorly related | Sources are generally useful but uneven | Sources are credible, well matched, current when needed, and appropriately diverse |
| Citation coverage | Ability to trace factual claims to returned sources | Claims are largely unsupported or untraceable | Major claims have some support but coverage is incomplete | Material claims are clearly grounded in the returned sources |
| Adaptability | Response to ambiguity, conflicting evidence, or an initially incomplete search path | Repeats an ineffective path or ignores evidence gaps | Makes limited adjustments | Identifies evidence gaps and makes focused, useful adjustments |

## Operational dimensions

| Dimension | Measurement | Preferred result |
|---|---|---|
| Reliability | Successful completion rate, failure category, and whether limits were respected | Higher completion, clear failures, no limit violations |
| Efficiency | Duration, search count, source count, tool calls, agent iterations, and available API usage counters | Lower cost and latency when quality is comparable |
| Repeatability | Variation in completion, scores, sources, and conclusions across repeated runs | Smaller variation without systematic quality loss |

Operational dimensions should not be reduced to a single arbitrary score. Report
the raw values and explain meaningful tradeoffs.

## Comparison summary

For each topic, report:

- the mean and range of reviewer scores for each qualitative dimension;
- completion and failure outcomes;
- run metrics for each orchestration mode;
- material differences in sources, conclusions, and search behavior;
- reviewer confidence and notable limitations.

An overall recommendation must state whether one mode is preferred for the
tested use cases, whether the modes have different strengths, or whether the
evidence is inconclusive. Do not claim statistical significance from this
small demonstration dataset.

## Reviewer guidance

- Review paired runs without relying on mode labels until scoring is complete.
- Score only what is supported by the report and returned sources.
- Distinguish missing evidence from a conclusion that the evidence is mixed.
- Treat a polished but unsupported claim as a citation-coverage failure.
- Record concrete examples for scores of 1, 2, or 5.
- If a run is incomplete, score only dimensions that can be assessed and mark
  the remaining dimensions not applicable.
