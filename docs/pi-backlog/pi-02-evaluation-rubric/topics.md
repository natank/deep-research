# PI-02 Comparison Topics

These topics are a small, deliberately varied demonstration dataset. They are
intended to expose differences in clarification, search planning, source
selection, adaptation, and report synthesis rather than to represent a
statistically significant benchmark.

## Topic 1: Clear trend

**Prompt:** How has global solar power capacity changed since 2015?

**Why included:** Tests a focused historical trend that should be answerable
without clarification and should produce quantitative or time-series evidence.

**Expected good behavior:**

- Identify a consistent global capacity measure and time range.
- Prefer authoritative energy or industry sources with clear dates.
- Distinguish installed capacity from generation where relevant.
- Ground the chart and trend claims in returned sources.

**Clarification expectation:** Usually no clarification.

## Topic 2: Ambiguous scope

**Prompt:** What are the benefits and risks of artificial intelligence in
education?

**Why included:** Tests whether the system notices broad scope and either asks
useful questions or makes its chosen scope explicit.

**Expected good behavior:**

- Cover both benefits and risks rather than advocating one side.
- Consider relevant stakeholders such as learners, educators, and institutions.
- Distinguish evidence from speculation and identify important limitations.
- Use varied sources, including research or institutional sources where possible.

**Clarification expectation:** Clarification is likely useful, especially for
education level, geography, audience, or intended use.

## Topic 3: Multi-dimensional comparison

**Prompt:** Compare solid-state, lithium-ion, and sodium-ion batteries for
electric vehicles.

**Why included:** Tests structured comparison across several technologies and
the ability to keep criteria consistent.

**Expected good behavior:**

- Compare the same dimensions across all three technologies.
- Cover energy density, cost, safety, maturity, supply chain, and use cases
  where sources support them.
- Separate commercial availability from laboratory potential.
- Avoid presenting incomparable measurements as directly equivalent.

**Clarification expectation:** Optional; a good system may ask about market,
technical, or consumer focus.

## Topic 4: Current and fast-changing

**Prompt:** What are the latest major developments in reusable launch vehicles?

**Why included:** Tests freshness, search adaptation, date awareness, and
handling of rapidly changing information.

**Expected good behavior:**

- State the research date or temporal boundary.
- Prefer recent, credible sources and distinguish announcements from completed
  milestones.
- Identify uncertainty where developments are planned rather than achieved.
- Avoid treating one current event as a complete industry trend.

**Clarification expectation:** Optional; the system may ask for a time window or
geographic/organizational scope.

## Topic 5: Evidence-sensitive

**Prompt:** What does current research say about the effectiveness of remote
work on productivity?

**Why included:** Tests synthesis of mixed evidence, study quality, definitions,
and cautious conclusions.

**Expected good behavior:**

- Define or qualify what productivity means in the cited evidence.
- Distinguish correlation, causation, self-reported outcomes, and measured
  outcomes where possible.
- Represent conflicting findings rather than selecting only convenient results.
- Explain relevant moderators such as role, management practices, or work
  arrangement.

**Clarification expectation:** Clarification may be useful for industry,
geography, time period, or type of productivity evidence.

## Dataset handling

The exact prompt, clarification answers, model, configuration, and execution
limits used for every run must be recorded. If a topic becomes unsuitable
because of a major change in current events or source availability, record the
reason and do not silently replace it.
