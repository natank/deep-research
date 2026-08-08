import { useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'
import ReportChart from './ReportChart'
import type { ResearchResult } from './types'

type RunState = 'idle' | 'loading' | 'error'

function App() {
  const [topic, setTopic] = useState('')
  const [runState, setRunState] = useState<RunState>('idle')
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ResearchResult | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmedTopic = topic.trim()
    if (!trimmedTopic) return

    setRunState('loading')
    setError(null)
    setResult(null)

    try {
      const response = await fetch('/research', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic: trimmedTopic }),
      })

      if (!response.ok) {
        const body = await response.json().catch(() => null)
        throw new Error(body?.detail ?? 'Research failed, please try again')
      }

      const data: ResearchResult = await response.json()
      setResult(data)
      setRunState('idle')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Research failed, please try again')
      setRunState('error')
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Deep Research</h1>
        <p>Enter a topic and get a synthesized report: summary, sources, and a chart.</p>
      </header>

      <main>
        <form className="topic-form" onSubmit={handleSubmit}>
          <label htmlFor="topic">Research topic</label>
          <div className="topic-form-row">
            <input
              id="topic"
              name="topic"
              type="text"
              placeholder="e.g. The state of solid-state batteries in 2026"
              value={topic}
              onChange={(event) => setTopic(event.target.value)}
              autoComplete="off"
              disabled={runState === 'loading'}
              required
            />
            <button
              type="submit"
              disabled={topic.trim().length === 0 || runState === 'loading'}
            >
              {runState === 'loading' ? 'Researching…' : 'Research'}
            </button>
          </div>
        </form>

        {runState === 'loading' && (
          <section className="status-banner status-loading" aria-live="polite">
            <p>Planning searches, gathering sources, and writing your report…</p>
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

        {!result && runState !== 'loading' && (
          <section className="report-placeholder" aria-live="polite">
            <p>Your report will appear here once a run completes.</p>
          </section>
        )}
      </main>
    </div>
  )
}

export default App
