import { useRef, useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'
import ReportChart from './ReportChart'
import { ApiError, requestClarification, requestResearch } from './api'
import type {
  ClarificationAnswer,
  ClarificationQuestion,
  OrchestrationMode,
  ResearchResult,
} from './types'

type RunState = 'idle' | 'checking' | 'questions' | 'loading' | 'error'

const TOPIC_MAX_LENGTH = 200

interface ClarificationSession {
  topic: string
  questions: ClarificationQuestion[]
  answers: Record<string, string>
  orchestrationMode: OrchestrationMode
}

interface ResearchPayload {
  topic: string
  clarificationAnswers: ClarificationAnswer[]
  orchestrationMode: OrchestrationMode
}

function App() {
  const [topic, setTopic] = useState('')
  const [runState, setRunState] = useState<RunState>('idle')
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ResearchResult | null>(null)
  const [clarification, setClarification] = useState<ClarificationSession | null>(null)
  const [orchestrationMode, setOrchestrationMode] = useState<OrchestrationMode>('code')
  const [lastResearch, setLastResearch] = useState<ResearchPayload | null>(null)
  const generationRef = useRef(0)
  const researchInFlightRef = useRef(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmedTopic = topic.trim()
    if (!trimmedTopic) {
      setError('Please enter a research topic.')
      setRunState('error')
      return
    }

    setRunState('checking')
    setError(null)
    setResult(null)

    try {
      const decision = await requestClarification(trimmedTopic)
      if (decision.questions.length === 0) {
        await runResearch({ topic: trimmedTopic, clarificationAnswers: [], orchestrationMode })
        return
      }

      setClarification({
        topic: trimmedTopic,
        questions: decision.questions,
        answers: Object.fromEntries(decision.questions.map((question) => [question.id, ''])),
        orchestrationMode,
      })
      setRunState('questions')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Clarification failed, please try again')
      setRunState('error')
    }
  }

  async function runResearch(payload: ResearchPayload) {
    if (researchInFlightRef.current) return
    researchInFlightRef.current = true
    const generation = ++generationRef.current
    setLastResearch(payload)
    setRunState('loading')
    setError(null)
    try {
      const researchResult = await requestResearch(
        payload.topic,
        payload.clarificationAnswers,
        payload.orchestrationMode,
      )
      if (generation !== generationRef.current) return
      setResult(researchResult)
      setRunState('idle')
    } catch (err) {
      if (generation !== generationRef.current) return
      setError(err instanceof ApiError ? err.message : 'Research failed, please try again')
      setRunState('error')
    } finally {
      researchInFlightRef.current = false
    }
  }

  function updateAnswer(questionId: string, answer: string) {
    setClarification((current) =>
      current ? { ...current, answers: { ...current.answers, [questionId]: answer.slice(0, 500) } } : current,
    )
  }

  function updateOrchestrationMode(mode: OrchestrationMode) {
    setOrchestrationMode(mode)
    setClarification((current) => (current ? { ...current, orchestrationMode: mode } : current))
  }

  async function handleClarificationSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!clarification) return

    const firstEmptyQuestion = clarification.questions.find(
      (question) => !clarification.answers[question.id]?.trim(),
    )
    if (firstEmptyQuestion) {
      setError(`Please answer: ${firstEmptyQuestion.question}`)
      setRunState('questions')
      document.getElementById(`answer-${firstEmptyQuestion.id}`)?.focus()
      return
    }

    const answers: ClarificationAnswer[] = clarification.questions.map((question) => ({
      question_id: question.id,
      question: question.question,
      answer: clarification.answers[question.id].trim(),
    }))
    if (answers.some((answer) => answer.answer.length > 500)) {
      setError('Answers must be 500 characters or fewer.')
      setRunState('questions')
      return
    }

    await runResearch({
      topic: clarification.topic,
      clarificationAnswers: answers,
      orchestrationMode: clarification.orchestrationMode,
    })
  }

  async function handleRetry() {
    if (clarification) {
      const answers = clarification.questions.map((question) => ({
        question_id: question.id,
        question: question.question,
        answer: clarification.answers[question.id].trim(),
      }))
      if (answers.some((answer) => !answer.answer)) {
        setRunState('questions')
        return
      }
      await runResearch({
        topic: clarification.topic,
        clarificationAnswers: answers,
        orchestrationMode: clarification.orchestrationMode,
      })
      return
    }
    if (lastResearch) await runResearch(lastResearch)
  }

  function handleStartOver() {
    generationRef.current += 1
    setTopic('')
    setClarification(null)
    setResult(null)
    setError(null)
    setLastResearch(null)
    setRunState('idle')
    setOrchestrationMode('code')
  }

  const topicLocked = runState === 'checking' || runState === 'questions' || runState === 'loading'
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
              disabled={topicLocked}
              maxLength={TOPIC_MAX_LENGTH}
              aria-describedby="topic-hint"
            />
            <button type="submit" disabled={topicLocked}>
              {(runState === 'checking' || runState === 'loading') && (
                <span className="spinner" aria-hidden="true" />
              )}
              {runState === 'checking'
                ? 'Checking…'
                : runState === 'loading'
                  ? 'Researching…'
                  : 'Research'}
            </button>
          </div>
          <span id="topic-hint" className="topic-hint">
            {topic.length}/{TOPIC_MAX_LENGTH}
          </span>
          <fieldset
            className="mode-selector"
            disabled={runState === 'checking' || runState === 'loading'}
            aria-describedby="mode-hint"
          >
            <legend>Orchestration mode</legend>
            <label>
              <input
                type="radio"
                name="orchestration-mode"
                value="code"
                checked={orchestrationMode === 'code'}
                onChange={() => updateOrchestrationMode('code')}
              />
              <span>Code orchestration</span>
            </label>
            <label>
              <input
                type="radio"
                name="orchestration-mode"
                value="agent"
                checked={orchestrationMode === 'agent'}
                onChange={() => updateOrchestrationMode('agent')}
              />
              <span>Agent orchestration</span>
            </label>
            <span id="mode-hint" className="mode-hint">
              {orchestrationMode === 'code'
                ? 'A predictable fixed workflow.'
                : 'Adaptive search decisions within server limits.'}
            </span>
          </fieldset>
        </form>

        {runState === 'loading' && (
          <section className="status-banner status-loading" aria-live="polite">
            <span className="spinner" aria-hidden="true" />
            <p>
              {orchestrationMode === 'agent'
                ? 'Agent is researching, adapting its search plan, and writing your report. This can take up to a minute…'
                : 'Planning searches, gathering sources, and writing your report. This can take up to a minute…'}
            </p>
          </section>
        )}

        {runState === 'checking' && (
          <section className="status-banner status-loading" aria-live="polite">
            <span className="spinner" aria-hidden="true" />
            <p>Checking whether your topic needs clarification…</p>
          </section>
        )}

        {error && (
          <section className="status-banner status-error" role="alert">
            <p>{error}</p>
            {lastResearch && (
              <button type="button" className="retry-button" onClick={handleRetry} disabled={runState === 'loading'}>
                Retry research
              </button>
            )}
          </section>
        )}

        {clarification && (runState === 'questions' || runState === 'error') && (
          <section className="clarification-panel" aria-labelledby="clarification-heading">
            <div>
              <h2 id="clarification-heading">Clarify your research</h2>
              <p className="clarification-topic">
                Research topic: <strong>{clarification.topic}</strong>
              </p>
            </div>
            <form className="clarification-form" onSubmit={handleClarificationSubmit} noValidate>
              {clarification.questions.map((question) => (
                <fieldset key={question.id}>
                  <legend>{question.question}</legend>
                  <p id={`purpose-${question.id}`} className="clarification-purpose">
                    {question.purpose}
                  </p>
                  <label htmlFor={`answer-${question.id}`}>Your answer</label>
                  <textarea
                    id={`answer-${question.id}`}
                    name={question.id}
                    value={clarification.answers[question.id]}
                    onChange={(event) => updateAnswer(question.id, event.target.value)}
                    maxLength={500}
                    autoComplete="off"
                    aria-describedby={`purpose-${question.id}`}
                  />
                </fieldset>
              ))}
              <div className="clarification-actions">
                <button type="submit" disabled={runState !== 'questions'}>
                  Research with these answers
                </button>
                <button type="button" className="secondary-button" onClick={handleStartOver}>
                  Start over
                </button>
              </div>
            </form>
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
