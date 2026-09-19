import type {
  ClarificationDecision,
  ClarificationQuestion,
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

async function postJson<T>(path: string, body: Record<string, string>): Promise<T> {
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
      throw new ApiError('Request is taking longer than expected. Please try again.')
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

export function requestResearch(topic: string): Promise<ResearchResult> {
  return postJson<ResearchResult>('/research', { topic })
}

export { MAX_QUESTIONS, QUESTION_TEXT_MAX_LENGTH, TOPIC_MAX_LENGTH }
