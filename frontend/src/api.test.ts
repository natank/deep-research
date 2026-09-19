import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, requestResearch } from './api'

afterEach(() => {
  vi.unstubAllGlobals()
})

const validResult = {
  report: {
    topic: 'topic',
    summary: 'summary',
    insights: ['insight'],
    chart: { title: 'chart', points: [{ label: 'a', value: 1 }] },
  },
  sources: [
    { title: 'Title', url: 'https://example.com', content: 'content', score: 0.5 },
  ],
  email: { status: 'sent', recipient: 'demo@example.com', report_id: 'id', filename: 'id.md' },
}

function response(payload: unknown, ok = true): Response {
  return {
    ok,
    json: async () => payload,
  } as Response
}

describe('research API response handling', () => {
  it('parses a valid result and sends only the research contract', async () => {
    const fetchMock = vi.fn().mockResolvedValue(response(validResult))
    vi.stubGlobal('fetch', fetchMock)

    await expect(
      requestResearch('topic', [], 'agent'),
    ).resolves.toMatchObject({ report: validResult.report })
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      topic: 'topic',
      orchestration_mode: 'agent',
    })
  })

  it('rejects malformed successful responses without a report', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ report: {} })))

    await expect(requestResearch('topic')).rejects.toEqual(
      new ApiError('Research failed, please try again'),
    )
  })

  it('uses generic detail text for failed responses', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(response({ detail: 'Research failed, please try again' }, false)),
    )

    await expect(requestResearch('topic')).rejects.toEqual(
      new ApiError('Research failed, please try again'),
    )
  })
})
