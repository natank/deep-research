# Deep Research App — Master Plan

This document operationalizes the structured approach defined in [purpose.md](./purpose.md) into concrete phases, deliverables, and a task breakdown to kick off implementation.

## 0. Repo Setup

- Create GitHub repo, `main` branch, initial README commit.
- Add `.gitignore` (node/python as applicable), `.env.example` (OpenAI API key placeholder, no real secrets committed).
- Branch protection on `main`: PRs required, no direct pushes.

## 1. Operational Concept

**What we're building:** a single-user, browser-based demo app that takes a research topic and produces a report (summary + articles + visualizations), delivered via a simulated email flow.

**Why:** portfolio piece demonstrating full-stack + LLM-integrated application development.

**Core user flow:**
1. User enters a topic in the browser UI.
2. App plans a set of searches for that topic.
3. App executes searches and retrieves articles/data.
4. App synthesizes a report (summary, key insights, visualizations).
5. App "sends" the report via simulated email, shows a success notification in the UI, and then makes the report available for download in the UI (in place of an actual emailed report).

## 2. Requirements & Scope

### In scope
- Web UI: topic input, run status/progress, report display, "email sent" notification, report download (replaces actual email delivery).
- Backend pipeline with four logical components: **Planner, Searcher, Writer, Emailer**.
- LLM calls via OpenAI API, using the `gpt-5.4-mini` model to minimize demo cost.
- Search/retrieval via a web search API (provider TBD in architecture phase).
- Report includes: narrative summary, list of source articles/links, and at least one data visualization (chart type left to design).
- Emailer is simulated — no real email delivery; UI displays a success notification, then offers the report as a downloadable file (e.g. PDF/Markdown/HTML, format left to design).
- Basic automated tests (unit tests per component at minimum; integration test for the end-to-end pipeline is a stretch goal).

### Out of scope
- Multi-user auth/accounts.
- Persisted history of past research runs (nice-to-have, not required).
- Real email delivery/SMTP integration.
- Production-grade scaling, rate limiting, or cost controls beyond using a cheap model.

### Non-functional requirements (demo-appropriate defaults)
- Single concurrent user assumed; no load/perf targets beyond "feels responsive for a demo" (report generation completing in roughly under a minute is a reasonable target, not a hard SLA).
- Cost control: use `gpt-5.4-mini`; cap number of searches/sources per report (e.g. 5–8 sources) to bound token and API usage.
- No sensitive data handling; OpenAI API key stored in `.env`, never committed.
- Error handling: surface failures gracefully in the UI (e.g. "search failed, try again") rather than crashing.

## 3. Architecture & UI Design

To be finalized as its own design pass, but starting shape:

- **Frontend:** single-page web UI — topic input form, run/progress indicator, report view (summary, source list, chart), success notification for "email sent," followed by a report download action.
- **Backend:** API service exposing an endpoint to kick off a research run, orchestrating the four components:
  - **Planner** — takes the topic, calls OpenAI (`gpt-5.4-mini`) to produce a structured search plan (list of queries/subtopics).
  - **Searcher** — executes the planned queries against the Tavily search API, retrieves and normalizes source articles/data (deduped by URL, ranked by relevance score, capped at 8 sources).
  - **Writer** — calls OpenAI (`gpt-5.4-mini`) to synthesize retrieved content into a report (summary, key insights, chart data).
  - **Emailer** — simulates sending the report by rendering it to Markdown and writing it to a per-run file (logged as a "sent" event), returns a success status to the frontend, and exposes the report file for download in place of real delivery.
- **Data flow:** UI → orchestrator/API → Planner → Searcher → Writer → Emailer → UI notification → report download.
- Chart library: Recharts, rendering the Writer's chart data as a bar chart.
- The pipeline runs synchronously behind `POST /research` (topic in, report + email status out); no progress streaming for this demo.

## 4. Implementation Plan (task breakdown)

Each task below is scoped to land as its own PR into `main`, reviewed and tested before merge.

| # | Task | Depends on | Status |
|---|------|------------|--------|
| 1 | Repo scaffolding: project structure, tooling, lint/format config, README | — | Done |
| 2 | Backend skeleton: API server, health check endpoint, `.env` config loading | 1 | Done |
| 3 | Frontend skeleton: base app shell, topic input form (no backend wiring yet) | 1 | Done |
| 4 | Planner component: OpenAI-backed search-plan generation + unit tests | 2 | Done |
| 5 | Searcher component: search API integration, source retrieval/normalization + unit tests | 2 | Done |
| 6 | Writer component: OpenAI-backed report synthesis (summary, insights, chart data) + unit tests | 4, 5 | Done |
| 7 | Emailer component: simulated send + success status + report made available for download + unit tests | 2 | Done |
| 8 | Orchestration: wire Planner → Searcher → Writer → Emailer behind a single API endpoint | 4, 5, 6, 7 | Done |
| 9 | Frontend integration: submit topic, show progress, render report, show "email sent" notification, offer report download | 3, 8 | Done |
| 10 | Data visualization: pick chart type(s) and render in report view | 6, 9 | Done |
| 11 | Error handling & UX polish: loading states, failure messages, basic input validation | 9 | Done |
| 12 | End-to-end test pass + README usage docs | all above | Done |

## 5. Execution

- Work through tasks in dependency order above; each task = one branch + one PR.
- PR checklist: tests pass, self-reviewed diff, README/docs updated if behavior changes.

## 6. Testing

- Unit tests per component (Planner, Searcher, Writer, Emailer) with mocked external calls (OpenAI, search API).
- Manual end-to-end pass: run a real topic through the full flow and verify report quality, UI states, and notification.
- Verify no secrets are committed (`.env` gitignored, `.env.example` only).
