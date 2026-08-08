import { useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'
import ReportChart from './ReportChart'
import type { ResearchResult } from './types'

type RunState = 'idle' | 'loading' | 'error'

const TOPIC_MAX_LENGTH = 200
const REQUEST_TIMEOUT_MS = 120_000

function App() {
  const [topic, setTopic] = useState('')
  const [runState, setRunState] = useState<RunState>('idle')
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ResearchResult | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmedTopic = topic.trim()
    if (!trimmedTopic) {
      setError('Please enter a research topic.')
      setRunState('error')
      return
    }

    setRunState('loading')
    setError(null)
    setResult(null)

    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)

    try {
      const response = await fetch('/research', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic: trimmedTopic }),
        signal: controller.signal,
      })

      if (!response.ok) {
        const body = await response.json().catch(() => null)
        throw new Error(body?.detail ?? 'Research failed, please try again')
      }

      const data: ResearchResult = await response.json()
      setResult(data)
      setRunState('idle')
    } catch (err) {
      const message =
        err instanceof DOMException && err.name === 'AbortError'
          ? 'Research is taking longer than expected. Please try again.'
          : err instanceof Error
            ? err.message
            : 'Research failed, please try again'
      setError(message)
      setRunState('error')
    } finally {
      clearTimeout(timeout)
    }
  }

  const showPlaceholder = !result && runState === 'idle'

  return (
    <div className="app">
      <header className="app-header">
        <h1>Deep Research</h1>
        <p>Enter a topic and get a synthesized report: summary, sources, and a chart.</p>
      </header>

      <main>
        <form className="topic-form" onSubmit={handleSubmit} noValidate>
          <label htmlFor="topic">Research topic</label>
          <div className="topic-form-row">
            <input
              id="topic"
              name="topic"
              type="text"
              placeholder="e.g. The state of solid-state batteries in 2026"
              value={topic}
              onChange={(event) => setTopic(event.target.value.slice(0, TOPIC_MAX_LENGTH))}
              autoComplete="off"
              disabled={runState === 'loading'}
              maxLength={TOPIC_MAX_LENGTH}
              aria-describedby="topic-hint"
            />
            <button type="submit" disabled={runState === 'loading'}>
              {runState === 'loading' && <span className="spinner" aria-hidden="true" />}
              {runState === 'loading' ? 'Researching…' : 'Research'}
            </button>
          </div>
          <span id="topic-hint" className="topic-hint">
            {topic.length}/{TOPIC_MAX_LENGTH}
          </span>
        </form>

        {runState === 'loading' && (
          <section className="status-banner status-loading" aria-live="polite">
            <span className="spinner" aria-hidden="true" />
            <p>Planning searches, gathering sources, and writing your report. This can take up to a minute…</p>
          </section>
        )}

        {runState === 'error' && error && (
          <section className="status-banner status-error" role="alert">
            <p>{error}</p>
          </section>
        )}

        {result && (
          <section className="report" aria-live="polite">
            <section className="status-banner status-success">
              <p>
                Report emailed to <strong>{result.email.recipient}</strong> ({result.email.status}).
              </p>
              <a
                className="download-link"
                href={`/reports/${result.email.report_id}`}
                download={result.email.filename}
              >
                Download report ({result.email.filename})
              </a>
            </section>

            <h2>{result.report.topic}</h2>
            <p className="summary">{result.report.summary}</p>

            <h3>Key insights</h3>
            <ul>
              {result.report.insights.map((insight) => (
                <li key={insight}>{insight}</li>
              ))}
            </ul>

            <h3>{result.report.chart.title}</h3>
            <ReportChart chart={result.report.chart} />

            <h3>Sources</h3>
            <ul className="sources">
              {result.sources.map((source) => (
                <li key={source.url}>
                  <a href={source.url} target="_blank" rel="noreferrer">
                    {source.title}
                  </a>
                </li>
              ))}
            </ul>
          </section>
        )}

        {showPlaceholder && (
          <section className="report-placeholder" aria-live="polite">
            <p>Your report will appear here once a run completes.</p>
          </section>
        )}
      </main>
    </div>
  )
}

export default App
