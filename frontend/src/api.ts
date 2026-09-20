import type {
  ClarificationAnswer,
  ClarificationDecision,
  ClarificationQuestion,
  OrchestrationMode,
  ResearchResult,
} from './types'

const TOPIC_MAX_LENGTH = 200
const MAX_QUESTIONS = 3
const QUESTION_ID_PATTERN = /^[a-z0-9][a-z0-9_-]{0,31}$/
const QUESTION_TEXT_MAX_LENGTH = 200
const REQUEST_TIMEOUT_MS = 120_000

export class ApiError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function hasControlCharacters(value: string): boolean {
  return [...value].some((character) => character.charCodeAt(0) < 32)
}

function isSafeText(value: unknown, maxLength = 10_000): value is string {
  return typeof value === 'string' && value.length > 0 && value.length <= maxLength && !hasControlCharacters(value)
}

function isQuestion(value: unknown): value is ClarificationQuestion {
  if (!isRecord(value)) return false
  return (
    typeof value.id === 'string' &&
    QUESTION_ID_PATTERN.test(value.id) &&
    typeof value.question === 'string' &&
    value.question.length > 0 &&
    value.question.length <= QUESTION_TEXT_MAX_LENGTH &&
    typeof value.purpose === 'string' &&
    value.purpose.length > 0 &&
    value.purpose.length <= QUESTION_TEXT_MAX_LENGTH &&
    !hasControlCharacters(value.question) &&
    !hasControlCharacters(value.purpose)
  )
}

function parseClarificationDecision(value: unknown): ClarificationDecision {
  if (!isRecord(value) || typeof value.needs_clarification !== 'boolean' || !Array.isArray(value.questions)) {
    throw new ApiError('Clarification failed, please try again')
  }

  if (value.questions.length > MAX_QUESTIONS || !value.questions.every(isQuestion)) {
    throw new ApiError('Clarification failed, please try again')
  }

  const questions = value.questions
  const ids = new Set(questions.map((question) => question.id))
  const questionTexts = new Set(questions.map((question) => question.question.trim().toLocaleLowerCase()))
  if (ids.size !== questions.length || questionTexts.size !== questions.length) {
    throw new ApiError('Clarification failed, please try again')
  }

  if (value.needs_clarification !== (questions.length > 0)) {
    throw new ApiError('Clarification failed, please try again')
  }

  return { needs_clarification: value.needs_clarification, questions }
}

function parseResearchResult(value: unknown): ResearchResult {
  if (!isRecord(value) || !isRecord(value.report) || !Array.isArray(value.sources) || !isRecord(value.email)) {
    throw new ApiError('Research failed, please try again')
  }

  const report = value.report
  const chart = isRecord(report.chart) ? report.chart : null
  const points = chart && Array.isArray(chart.points) ? chart.points : null
  if (
    !isSafeText(report.topic, TOPIC_MAX_LENGTH) ||
    !isSafeText(report.summary) ||
    !Array.isArray(report.insights) ||
    !report.insights.every((insight) => isSafeText(insight)) ||
    !chart ||
    !isSafeText(chart.title) ||
    !points ||
    !points.every(
      (point) =>
        isRecord(point) &&
        isSafeText(point.label) &&
        typeof point.value === 'number' &&
        Number.isFinite(point.value),
    )
  ) {
    throw new ApiError('Research failed, please try again')
  }

  const sources = value.sources
  if (
    !sources.every(
      (source) =>
        isRecord(source) &&
        isSafeText(source.title, 300) &&
        isSafeText(source.url, 2_000) &&
        /^https?:\/\//i.test(source.url) &&
        isSafeText(source.content) &&
        typeof source.score === 'number' &&
        Number.isFinite(source.score),
    )
  ) {
    throw new ApiError('Research failed, please try again')
  }

  const email = value.email
  if (
    !isSafeText(email.status, 100) ||
    !isSafeText(email.recipient, 320) ||
    !isSafeText(email.report_id, 100) ||
    !isSafeText(email.filename, 255)
  ) {
    throw new ApiError('Research failed, please try again')
  }

  return {
    report: {
      topic: report.topic,
      summary: report.summary,
      insights: report.insights,
      chart: { title: chart.title, points: points.map((point) => ({ label: point.label, value: point.value })) },
    },
    sources: sources.map((source) => ({
      title: source.title,
      url: source.url,
      content: source.content,
      score: source.score,
    })),
    email: {
      status: email.status,
      recipient: email.recipient,
      report_id: email.report_id,
      filename: email.filename,
    },
  }
}

async function postJson<T>(
  path: string,
  body: Record<string, unknown>,
  timeoutMessage = 'Request is taking longer than expected. Please try again.',
): Promise<T> {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)

  try {
    const response = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: controller.signal,
    })
    const payload = await response.json().catch(() => null)
    if (!response.ok) {
      throw new ApiError(
        typeof payload === 'object' &&
          payload !== null &&
          'detail' in payload &&
          typeof payload.detail === 'string'
          ? payload.detail
          : 'Request failed, please try again',
      )
    }
    return payload as T
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError(timeoutMessage)
    }
    if (error instanceof ApiError) throw error
    throw new ApiError('Request failed, please try again')
  } finally {
    clearTimeout(timeout)
  }
}

export async function requestClarification(topic: string): Promise<ClarificationDecision> {
  const decision = await postJson<unknown>('/clarify', { topic })
  return parseClarificationDecision(decision)
}

export function requestResearch(
  topic: string,
  clarificationAnswers: ClarificationAnswer[] = [],
  orchestrationMode: OrchestrationMode = 'code',
): Promise<ResearchResult> {
  return postJson<unknown>(
    '/research',
    {
    topic,
    ...(clarificationAnswers.length > 0 ? { clarification_answers: clarificationAnswers } : {}),
    orchestration_mode: orchestrationMode,
    },
    'Research is taking longer than expected. The server may still be finishing; please try again.',
  ).then(parseResearchResult)
}

export { MAX_QUESTIONS, QUESTION_TEXT_MAX_LENGTH, TOPIC_MAX_LENGTH }
