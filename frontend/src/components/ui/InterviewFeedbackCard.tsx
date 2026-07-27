import React, { useState } from 'react'
import { Card, Badge } from 'react-bootstrap'
import { FiChevronDown, FiChevronUp, FiCheck, FiX } from 'react-icons/fi'

interface Evidence {
  provider?: string
  provider_version?: string
  model?: string
  matched_criteria?: string[]
  missing_criteria?: string[]
  matched_keywords?: string[]
  missing_keywords?: string[]
  evidence?: string
  provider_fallback_from?: string
  provider_fallback_reason?: string
  [key: string]: unknown
}

interface InterviewFeedbackCardProps {
  questionNumber: number
  questionText: string
  expectedAnswer?: string
  answerText?: string
  score: number
  emotion?: string
  feedbackEn?: string
  feedbackAr?: string
  evidence?: Evidence | null
  videoUrl?: string
  defaultExpanded?: boolean
}

function sanitizeFeedback(text?: string): string {
  if (!text) return ''
  return text
    .replace(/^(local_vllm\s+\S+\s*:\s*)/i, '')
    .replace(/^(deterministic_baseline\s+v?[\d.]+\s*:\s*)/i, '')
    .replace(/\s*Arabic feedback:\s*.*$/i, '')
    .trim()
}

function getMatchedItems(evidence?: Evidence | null): string[] {
  if (!evidence) return []
  return evidence.matched_criteria || evidence.matched_keywords || []
}

function getMissingItems(evidence?: Evidence | null): string[] {
  if (!evidence) return []
  return evidence.missing_criteria || evidence.missing_keywords || []
}

function getScoreVariant(score: number): string {
  if (score >= 80) return 'success'
  if (score >= 60) return 'warning'
  return 'danger'
}

function getEmotionVariant(emotion?: string): string {
  if (!emotion) return 'secondary'
  const happy = ['happy', 'neutral', 'surprise']
  return happy.includes(emotion.toLowerCase()) ? 'success' : 'warning'
}

const InterviewFeedbackCard: React.FC<InterviewFeedbackCardProps> = ({
  questionNumber,
  questionText,
  expectedAnswer,
  answerText,
  score,
  emotion,
  feedbackEn,
  feedbackAr,
  evidence,
  videoUrl,
  defaultExpanded = false,
}) => {
  const [expanded, setExpanded] = useState(defaultExpanded)

  const matched = getMatchedItems(evidence)
  const missing = getMissingItems(evidence)
  const evidenceText = evidence?.evidence || ''
  const isFallback = !!evidence?.provider_fallback_from
  const sanitizedFeedbackEn = sanitizeFeedback(feedbackEn)
  const hasArabic = !!feedbackAr

  return (
    <Card
      className={`mb-3 border ${expanded ? 'shadow-sm' : ''}`}
      style={{ cursor: 'pointer', transition: 'box-shadow 0.2s ease' }}
      onClick={() => setExpanded(!expanded)}
      onMouseEnter={(e) => { if (!expanded) (e.currentTarget as HTMLElement).style.boxShadow = '0 0.125rem 0.25rem rgba(0,0,0,0.075)' }}
      onMouseLeave={(e) => { if (!expanded) (e.currentTarget as HTMLElement).style.boxShadow = 'none' }}
    >
      <Card.Body className="p-4">
        <div className="d-flex align-items-start justify-content-between">
          <div className="d-flex align-items-center gap-3 flex-grow-1 min-w-0">
            <span className="badge bg-light text-dark border border-secondary rounded-circle d-flex align-items-center justify-content-center"
              style={{ width: 32, height: 32, minWidth: 32, fontSize: '0.8rem', fontWeight: 600 }}>
              {questionNumber}
            </span>
            <div className="min-w-0">
              <p className="mb-0 fw-semibold text-truncate" style={{ fontSize: '0.95rem' }}>
                {questionText}
              </p>
              {!expanded && sanitizedFeedbackEn && (
                <p className="mb-0 text-muted text-truncate small mt-1">
                  {sanitizedFeedbackEn}
                </p>
              )}
            </div>
          </div>
          <div className="d-flex align-items-center gap-2 ms-3 flex-shrink-0">
            <Badge bg={getScoreVariant(score)} className="rounded-pill px-3 py-2" style={{ fontSize: '0.8rem' }}>
              {score.toFixed(1)}%
            </Badge>
            {emotion && (
              <Badge bg={getEmotionVariant(emotion)} className="rounded-pill px-2 py-1" style={{ fontSize: '0.7rem' }}>
                {emotion}
              </Badge>
            )}
            {isFallback && (
              <Badge bg="warning" className="rounded-pill px-2 py-1" style={{ fontSize: '0.65rem' }}>
                Fallback
              </Badge>
            )}
            <span className="text-muted">
              {expanded ? <FiChevronUp size={18} /> : <FiChevronDown size={18} />}
            </span>
          </div>
        </div>

        {expanded && (
          <div className="mt-4 pt-3 border-top">
            {answerText && (
              <div className="mb-3">
                <small className="text-muted fw-semibold text-uppercase" style={{ fontSize: '0.7rem', letterSpacing: '0.05em' }}>Candidate Answer</small>
                <p className="mb-0 mt-1 p-3 bg-light rounded border-start border-4" style={{ borderLeftColor: '#6366f1', fontSize: '0.9rem' }}>
                  {answerText}
                </p>
              </div>
            )}
            {videoUrl && (
              <div className="mb-3">
                <small className="text-muted fw-semibold text-uppercase" style={{ fontSize: '0.7rem', letterSpacing: '0.05em' }}>Recorded Video</small>
                <video src={videoUrl} controls style={{ width: '100%', maxHeight: 400, borderRadius: 8 }} className="mt-1" />
              </div>
            )}

            {expectedAnswer && (
              <div className="mb-3">
                <small className="text-muted fw-semibold text-uppercase" style={{ fontSize: '0.7rem', letterSpacing: '0.05em' }}>Expected Answer</small>
                <p className="mb-0 mt-1 text-muted" style={{ fontSize: '0.85rem' }}>{expectedAnswer}</p>
              </div>
            )}

            {sanitizedFeedbackEn && (
              <div className="mb-3" dir="ltr">
                <small className="text-muted fw-semibold text-uppercase" style={{ fontSize: '0.7rem', letterSpacing: '0.05em' }}>Feedback</small>
                <div className="mt-1 p-3 bg-white border rounded" style={{ fontSize: '0.9rem', lineHeight: 1.6 }}>
                  {sanitizedFeedbackEn}
                </div>
              </div>
            )}

            {hasArabic && (
              <div className="mb-3" dir="rtl">
                <small className="text-muted fw-semibold text-uppercase" style={{ fontSize: '0.7rem', letterSpacing: '0.05em' }}>الملاحظات</small>
                <div className="mt-1 p-3 bg-white border rounded" style={{ fontSize: '0.9rem', lineHeight: 1.8, fontFamily: 'system-ui, sans-serif' }}>
                  {feedbackAr}
                </div>
              </div>
            )}

            <div className="row g-3 mb-3">
              {matched.length > 0 && (
                <div className="col-md-6">
                  <small className="text-muted fw-semibold text-uppercase d-block mb-2" style={{ fontSize: '0.7rem', letterSpacing: '0.05em' }}>
                    <FiCheck className="me-1" style={{ color: '#059669' }} /> Matched Criteria
                  </small>
                  <div className="d-flex flex-wrap gap-1">
                    {matched.map((item, i) => (
                      <span key={i} className="badge border rounded-pill px-3 py-2"
                        style={{ backgroundColor: '#ecfdf5', color: '#065f46', borderColor: '#a7f3d0', fontSize: '0.78rem' }}>
                        <FiCheck size={12} className="me-1" style={{ color: '#059669' }} />
                        {item}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {missing.length > 0 && (
                <div className="col-md-6">
                  <small className="text-muted fw-semibold text-uppercase d-block mb-2" style={{ fontSize: '0.7rem', letterSpacing: '0.05em' }}>
                    <FiX className="me-1" style={{ color: '#e11d48' }} /> Missing Criteria
                  </small>
                  <div className="d-flex flex-wrap gap-1">
                    {missing.map((item, i) => (
                      <span key={i} className="badge border rounded-pill px-3 py-2"
                        style={{ backgroundColor: '#fff1f2', color: '#be123c', borderColor: '#fecdd3', fontSize: '0.78rem' }}>
                        <FiX size={12} className="me-1" style={{ color: '#e11d48' }} />
                        {item}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {evidenceText && (
              <div>
                <small className="text-muted fw-semibold text-uppercase" style={{ fontSize: '0.7rem', letterSpacing: '0.05em' }}>Evidence</small>
                <blockquote className="mt-1 mb-0 p-3 bg-light border-start border-4 rounded-end"
                  style={{ borderLeftColor: '#6366f1', fontSize: '0.88rem', fontStyle: 'italic', color: '#334155' }}>
                  &ldquo;{evidenceText}&rdquo;
                </blockquote>
              </div>
            )}
          </div>
        )}
      </Card.Body>
    </Card>
  )
}

export default InterviewFeedbackCard
