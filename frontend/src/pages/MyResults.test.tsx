import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import MyResults from './MyResults'

const apiMock = vi.hoisted(() => ({
  reports: {
    getMyResults: vi.fn(),
  },
}))

vi.mock('../services/api', () => ({
  api: apiMock,
}))

const renderPage = () => render(
  <MemoryRouter>
    <MyResults />
  </MemoryRouter>
)

describe('MyResults', () => {
  beforeEach(() => {
    apiMock.reports.getMyResults.mockReset()
  })

  it('links completed results to the employee candidate report detail page', async () => {
    apiMock.reports.getMyResults.mockResolvedValue({
      data: [
        {
          response_id: 99,
          interview_title: 'Support Screen',
          total_score: 90,
          passed: true,
          confidence_score: 80,
          voice_quality: 85,
          face_visibility: 90,
          dominant_emotion: 'neutral',
          completed_at: '2026-07-20T00:00:00Z',
        },
      ],
    })

    renderPage()

    expect(await screen.findByText('Support Screen')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /view details/i })).toHaveAttribute('href', '/employee/candidate/99')
  })
})