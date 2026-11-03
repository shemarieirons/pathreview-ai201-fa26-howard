import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { ReviewPage } from '../ReviewPage'

const createShareLink = vi.fn()
const copyToClipboard = vi.fn()
const getReview = vi.fn()

vi.mock('../../hooks/useReviewStatus', () => ({
  useReviewStatus: vi.fn(() => ({
    review: { id: 'review-1', status: 'complete' },
    isPolling: false,
    error: '',
  })),
}))

vi.mock('../../services/api', () => ({
  apiClient: {
    getReview: (...args: unknown[]) => getReview(...args),
  },
}))

vi.mock('../../services/shareService', () => ({
  createShareLink: (...args: unknown[]) => createShareLink(...args),
  copyToClipboard: (...args: unknown[]) => copyToClipboard(...args),
}))

vi.mock('../../components/ReviewSection', () => ({
  ReviewSection: ({ section }: { section: { section_name: string } }) => (
    <div>{section.section_name}</div>
  ),
}))

function renderReviewPage() {
  return render(
    <MemoryRouter initialEntries={['/reviews/review-1']}>
      <Routes>
        <Route path="/reviews/:reviewId" element={<ReviewPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('ReviewPage copy link', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getReview.mockResolvedValue({
      id: 'review-1',
      profile_id: 'profile-1',
      status: 'complete',
      overall_score: 0.82,
      sections: [
        {
          section_name: 'Technical Skills',
          content: 'Strong fundamentals',
          confidence: 0.9,
          suggestions: ['Add metrics'],
        },
      ],
      created_at: '2026-11-01T00:00:00Z',
      updated_at: '2026-11-01T00:00:00Z',
    })
    createShareLink.mockResolvedValue('http://localhost:5173/share/secure-token')
    copyToClipboard.mockResolvedValue(undefined)
  })

  it('shows a Copy link button on the completed review summary', async () => {
    renderReviewPage()

    expect(await screen.findByRole('button', { name: /Copy link/i })).toBeInTheDocument()
  })

  it('requests a share link and copies it to the clipboard', async () => {
    const user = userEvent.setup()
    renderReviewPage()

    const button = await screen.findByRole('button', { name: /Copy link/i })
    await user.click(button)

    await waitFor(() => {
      expect(createShareLink).toHaveBeenCalledWith('review-1')
      expect(copyToClipboard).toHaveBeenCalledWith('http://localhost:5173/share/secure-token')
    })
    expect(await screen.findByText('Link copied to clipboard!')).toBeInTheDocument()
  })

  it('shows an error when share link generation fails', async () => {
    createShareLink.mockRejectedValueOnce(new Error('Failed to create share link'))
    const user = userEvent.setup()
    renderReviewPage()

    await user.click(await screen.findByRole('button', { name: /Copy link/i }))

    expect(await screen.findByText('Failed to create share link')).toBeInTheDocument()
  })

  it('disables the button while generating a link', async () => {
    let resolveShare: (value: string) => void = () => undefined
    createShareLink.mockImplementation(
      () =>
        new Promise<string>((resolve) => {
          resolveShare = resolve
        })
    )
    const user = userEvent.setup()
    renderReviewPage()

    const button = await screen.findByRole('button', { name: /Copy link/i })
    await user.click(button)

    expect(await screen.findByRole('button', { name: /Generating/i })).toBeDisabled()

    resolveShare('http://localhost:5173/share/secure-token')
    expect(await screen.findByText('Link copied to clipboard!')).toBeInTheDocument()
  })
})
