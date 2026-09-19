import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { ApiError, requestClarification, requestResearch } from './api'
import type { ResearchResult } from './types'

vi.mock('./api', async () => {
  const actual = await vi.importActual<typeof import('./api')>('./api')
  return {
    ...actual,
    requestClarification: vi.fn(),
    requestResearch: vi.fn(),
  }
})

const mockedRequestClarification = vi.mocked(requestClarification)
const mockedRequestResearch = vi.mocked(requestResearch)

const result = {
  report: {
    topic: 'topic',
    summary: 'summary',
    insights: ['insight'],
    chart: { title: 'chart', points: [{ label: 'a', value: 1 }] },
  },
  sources: [],
  email: { status: 'sent', recipient: 'demo@example.com', report_id: 'id', filename: 'id.md' },
} satisfies ResearchResult

describe('clarification flow', () => {
  beforeEach(() => {
    cleanup()
    vi.resetAllMocks()
  })

  it('continues directly to research when no questions are needed', async () => {
    mockedRequestClarification.mockResolvedValue({ needs_clarification: false, questions: [] })
    mockedRequestResearch.mockResolvedValue(result)
    render(<App />)

    fireEvent.change(screen.getByLabelText('Research topic'), { target: { value: 'topic' } })
    fireEvent.click(screen.getByRole('button', { name: 'Research' }))

    await waitFor(() => expect(mockedRequestResearch).toHaveBeenCalledWith('topic', [], 'code'))
    expect(screen.queryByRole('heading', { name: 'Clarify your research' })).not.toBeInTheDocument()
  })

  it('sends the selected mode and preserves it through clarification', async () => {
    mockedRequestClarification.mockResolvedValue({
      needs_clarification: true,
      questions: [{ id: 'q1', question: 'Which timeframe?', purpose: 'This narrows the search.' }],
    })
    mockedRequestResearch.mockResolvedValue(result)
    render(<App />)

    fireEvent.click(screen.getByLabelText('Agent'))
    fireEvent.change(screen.getByLabelText('Research topic'), { target: { value: 'topic' } })
    fireEvent.click(screen.getByRole('button', { name: 'Research' }))

    await screen.findByRole('heading', { name: 'Clarify your research' })
    fireEvent.change(screen.getByLabelText('Your answer'), { target: { value: 'Since 2020' } })
    fireEvent.click(screen.getByRole('button', { name: 'Research with these answers' }))

    await waitFor(() =>
      expect(mockedRequestResearch).toHaveBeenCalledWith(
        'topic',
        [{ question_id: 'q1', question: 'Which timeframe?', answer: 'Since 2020' }],
        'agent',
      ),
    )
  })

  it('renders questions and requires answers before continuing', async () => {
    mockedRequestClarification.mockResolvedValue({
      needs_clarification: true,
      questions: [{ id: 'q1', question: 'Which timeframe?', purpose: 'This narrows the search.' }],
    })
    mockedRequestResearch.mockResolvedValue(result)
    render(<App />)

    fireEvent.change(screen.getByLabelText('Research topic'), { target: { value: 'topic' } })
    fireEvent.click(screen.getByRole('button', { name: 'Research' }))

    await screen.findByRole('heading', { name: 'Clarify your research' })
    fireEvent.click(screen.getByRole('button', { name: 'Research with these answers' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Please answer: Which timeframe?')
    expect(mockedRequestResearch).not.toHaveBeenCalled()

    fireEvent.change(screen.getByLabelText('Your answer'), { target: { value: 'Since 2020' } })
    fireEvent.click(screen.getByRole('button', { name: 'Research with these answers' }))
    await waitFor(() =>
      expect(mockedRequestResearch).toHaveBeenCalledWith('topic', [
        { question_id: 'q1', question: 'Which timeframe?', answer: 'Since 2020' },
      ], 'code'),
    )
  })

  it('shows the Agent unsupported response without rendering a report', async () => {
    mockedRequestClarification.mockResolvedValue({ needs_clarification: false, questions: [] })
    mockedRequestResearch.mockRejectedValue(new ApiError('Agent orchestration is not available yet'))
    render(<App />)

    fireEvent.click(screen.getByLabelText('Agent'))
    fireEvent.change(screen.getByLabelText('Research topic'), { target: { value: 'topic' } })
    fireEvent.click(screen.getByRole('button', { name: 'Research' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Agent orchestration is not available yet',
    )
    expect(screen.queryByRole('heading', { name: 'summary' })).not.toBeInTheDocument()
  })

  it('preserves the question form after a clarification failure', async () => {
    mockedRequestClarification.mockRejectedValue(new Error('Clarification failed, please try again'))
    render(<App />)

    fireEvent.change(screen.getByLabelText('Research topic'), { target: { value: 'topic' } })
    fireEvent.click(screen.getByRole('button', { name: 'Research' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Clarification failed, please try again')
    expect(screen.getByDisplayValue('topic')).toBeInTheDocument()
  })
})
