import React, { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Loader, AlertCircle } from 'lucide-react'
import { ReviewSection } from '../components/ReviewSection'
import { getSharedReview } from '../services/shareService'
import { PublicReviewSummary } from '../types'

export const SharedReviewPage: React.FC = () => {
  const { token } = useParams<{ token: string }>()
  const [summary, setSummary] = useState<PublicReviewSummary | null>(null)
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    if (!token) {
      setError('This sharing link is invalid or the review is unavailable.')
      setIsLoading(false)
      return
    }

    let cancelled = false

    const load = async () => {
      setIsLoading(true)
      setError('')
      try {
        const data = await getSharedReview(token)
        if (!cancelled) {
          setSummary(data)
        }
      } catch (err) {
        if (!cancelled) {
          setSummary(null)
          setError(
            err instanceof Error
              ? err.message
              : 'Failed to load the shared review summary.'
          )
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [token])

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="mb-8">
          <p className="text-sm text-gray-500 mb-2">Shared portfolio review</p>
          <h1 className="text-3xl font-bold text-gray-900">Review Summary</h1>
          <p className="text-gray-600 mt-2">
            This is a read-only shared view. No account is required.
          </p>
        </div>

        {isLoading && (
          <div className="p-8 bg-white rounded-lg shadow text-center">
            <Loader className="w-8 h-8 animate-spin text-blue-600 mx-auto mb-4" />
            <p className="text-gray-900 font-semibold">Loading shared review...</p>
          </div>
        )}

        {!isLoading && error && (
          <div className="p-8 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-red-800 font-semibold">Unable to open shared review</p>
                <p className="text-red-700 text-sm mt-2">{error}</p>
                <Link
                  to="/login"
                  className="inline-block mt-4 text-blue-600 hover:text-blue-700 font-medium"
                >
                  Go to PathReview
                </Link>
              </div>
            </div>
          </div>
        )}

        {!isLoading && !error && summary && (
          <>
            {summary.overall_score !== undefined && summary.overall_score !== null && (
              <div className="mb-8 bg-white rounded-lg shadow p-8">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Overall Score</h2>
                <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
                  <div
                    className="h-full bg-blue-600 transition-all"
                    style={{ width: `${summary.overall_score * 100}%` }}
                  ></div>
                </div>
                <p className="mt-2 text-2xl font-bold text-blue-600">
                  {Math.round(summary.overall_score * 100)}/100
                </p>
              </div>
            )}

            <div className="space-y-6">
              <h2 className="text-2xl font-bold text-gray-900">Feedback</h2>
              {summary.sections && summary.sections.length > 0 ? (
                summary.sections.map((section, index) => (
                  <ReviewSection key={index} section={section} />
                ))
              ) : (
                <p className="text-gray-600">No feedback sections available</p>
              )}
            </div>

            <p className="mt-10 text-sm text-gray-500">
              Link expires{' '}
              {new Date(summary.expires_at).toLocaleString(undefined, {
                dateStyle: 'medium',
                timeStyle: 'short',
              })}
            </p>
          </>
        )}
      </div>
    </div>
  )
}
