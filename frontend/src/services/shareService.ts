import { PublicReviewSummary, ShareLinkResponse } from '../types'

const API_BASE = '/api'

function getAuthHeader(): { Authorization: string } | Record<string, never> {
  const token = localStorage.getItem('token')
  if (!token) return {}
  return { Authorization: `Bearer ${token}` }
}

async function parseError(response: Response): Promise<Error> {
  const error = await response.json().catch(() => ({}))
  const detail = error.detail || `Request failed with status ${response.status}`
  return new Error(detail)
}

/**
 * Request a public share link for a completed review and return the full URL.
 */
export async function createShareLink(reviewId: string): Promise<string> {
  const response = await fetch(`${API_BASE}/reviews/${reviewId}/share`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeader(),
    },
  })

  if (!response.ok) {
    throw await parseError(response)
  }

  const data: ShareLinkResponse = await response.json()
  return `${window.location.origin}${data.share_path}`
}

/**
 * Fetch a read-only public review summary by share token (no auth required).
 */
export async function getSharedReview(token: string): Promise<PublicReviewSummary> {
  const response = await fetch(`${API_BASE}/share/${encodeURIComponent(token)}`)

  if (!response.ok) {
    if (response.status === 410) {
      throw new Error('This sharing link has expired and is no longer valid.')
    }
    if (response.status === 404) {
      throw new Error('This sharing link is invalid or the review is unavailable.')
    }
    throw await parseError(response)
  }

  return response.json()
}

/**
 * Copy text to the clipboard, with a fallback for older browsers.
 */
export async function copyToClipboard(text: string): Promise<void> {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text)
    return
  }

  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.setAttribute('readonly', '')
  textarea.style.position = 'absolute'
  textarea.style.left = '-9999px'
  document.body.appendChild(textarea)
  textarea.select()
  const succeeded = document.execCommand('copy')
  document.body.removeChild(textarea)

  if (!succeeded) {
    throw new Error('Unable to copy link to clipboard')
  }
}
