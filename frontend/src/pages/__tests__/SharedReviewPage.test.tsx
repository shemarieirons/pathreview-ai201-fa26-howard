import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { SharedReviewPage } from '../SharedReviewPage'

const getSharedReview = vi.fn()

vi.mock('../../services/shareService', () => ({
  getSharedReview: (...args: unknown[]) => getSharedReview(...args),
}))

vi.mock('../../components/ReviewSection', () => ({
  ReviewSection: ({ section }: { section: { section_name: string } }) => (
    <div>{section.section_name}</div>
  ),
}))

function renderSharedPage(token: string) {
  return render(
    <MemoryRouter initialEntries={[`/share/${token}`]}>
      <Routes>
        <Route path="/share/:token" element={<SharedReviewPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('SharedReviewPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('displays a valid shared review summary', async () => {
    getSharedReview.mockResolvedValue({
      status: 'complete',
      overall_score: 0.75,
      sections: [
        {
          section_name: 'Project Experience',
          content: 'Good projects',
          confidence: 0.8,
          suggestions: ['Add impact metrics'],
        },
      ],
      expires_at: '2026-12-02T12:00:00Z',
    })

    renderSharedPage('valid-token')

    expect(await screen.findByText('Review Summary')).toBeInTheDocument()
    expect(screen.getByText('Project Experience')).toBeInTheDocument()
    expect(screen.getByText('75/100')).toBeInTheDocument()
    expect(getSharedReview).toHaveBeenCalledWith('valid-token')
  })

  it('shows a helpful message for expired links', async () => {
    getSharedReview.mockRejectedValue(
      new Error('This sharing link has expired and is no longer valid.')
    )

    renderSharedPage('expired-token')

    expect(
      await screen.findByText('This sharing link has expired and is no longer valid.')
    ).toBeInTheDocument()
    expect(screen.getByText('Unable to open shared review')).toBeInTheDocument()
  })

  it('shows a helpful message for invalid links', async () => {
    getSharedReview.mockRejectedValue(
      new Error('This sharing link is invalid or the review is unavailable.')
    )

    renderSharedPage('bad-token')

    await waitFor(() => {
      expect(
        screen.getByText('This sharing link is invalid or the review is unavailable.')
      ).toBeInTheDocument()
    })
  })
})
