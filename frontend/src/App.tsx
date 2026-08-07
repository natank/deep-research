import { useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'

function App() {
  const [topic, setTopic] = useState('')

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    // Backend wiring lands in a later task.
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
              required
            />
            <button type="submit" disabled={topic.trim().length === 0}>
              Research
            </button>
          </div>
        </form>

        <section className="report-placeholder" aria-live="polite">
          <p>Your report will appear here once a run completes.</p>
        </section>
      </main>
    </div>
  )
}

export default App
