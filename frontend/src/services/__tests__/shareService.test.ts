import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { copyToClipboard, createShareLink, getSharedReview } from '../shareService'

describe('shareService', () => {
  const originalFetch = globalThis.fetch
  const storage = new Map<string, string>()

  beforeEach(() => {
    storage.clear()
    storage.set('token', 'test-jwt')
    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      value: {
        getItem: (key: string) => storage.get(key) ?? null,
        setItem: (key: string, value: string) => {
          storage.set(key, value)
        },
        removeItem: (key: string) => {
          storage.delete(key)
        },
        clear: () => storage.clear(),
      },
    })
    globalThis.fetch = vi.fn()
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { origin: 'http://localhost:5173' },
    })
  })

  afterEach(() => {
    globalThis.fetch = originalFetch
    vi.restoreAllMocks()
  })

  it('createShareLink posts to the share endpoint and builds a full URL', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue({
      ok: true,
      json: async () => ({
        token: 'tok123',
        expires_at: '2026-12-02T00:00:00Z',
        share_path: '/share/tok123',
      }),
    } as Response)

    const url = await createShareLink('review-1')

    expect(globalThis.fetch).toHaveBeenCalledWith('/api/reviews/review-1/share', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer test-jwt',
      },
    })
    expect(url).toBe('http://localhost:5173/share/tok123')
  })

  it('getSharedReview fetches public summary without auth headers', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue({
      ok: true,
      json: async () => ({
        status: 'complete',
        overall_score: 0.9,
        sections: [],
        expires_at: '2026-12-02T00:00:00Z',
      }),
    } as Response)

    const summary = await getSharedReview('public-token')

    expect(globalThis.fetch).toHaveBeenCalledWith('/api/share/public-token')
    expect(summary.status).toBe('complete')
  })

  it('getSharedReview maps 410 to an expired-link error', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue({
      ok: false,
      status: 410,
      json: async () => ({ detail: 'expired' }),
    } as Response)

    await expect(getSharedReview('old')).rejects.toThrow(
      'This sharing link has expired and is no longer valid.'
    )
  })

  it('copyToClipboard uses navigator.clipboard when available', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, { clipboard: { writeText } })

    await copyToClipboard('http://example.com/share/abc')

    expect(writeText).toHaveBeenCalledWith('http://example.com/share/abc')
  })
})
