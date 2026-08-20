import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import EmployerDashboard from './EmployerDashboard'

const apiMock = vi.hoisted(() => ({
  interviews: {
    list: vi.fn(),
    delete: vi.fn(),
  },
  users: {
    getOrganizationMembers: vi.fn(),
  },
}))

vi.mock('../services/api', () => ({
  api: apiMock,
}))

const renderDashboard = () => render(
  <BrowserRouter>
    <EmployerDashboard />
  </BrowserRouter>
)

describe('EmployerDashboard', () => {
  beforeEach(() => {
    apiMock.interviews.list.mockReset()
    apiMock.interviews.delete.mockReset()
    apiMock.users.getOrganizationMembers.mockReset()
  })

  it('shows interview stats and the interview list', async () => {
    apiMock.interviews.list.mockResolvedValue({
      data: [
        { id: 1, title: 'Backend Interview', status: 'active', duration_minutes: 30, pass_score: 70, created_at: '2025-01-01T00:00:00Z' },
        { id: 2, title: 'Frontend Interview', status: 'draft', duration_minutes: 45, pass_score: 60, created_at: '2025-01-02T00:00:00Z' },
      ],
    })
    apiMock.users.getOrganizationMembers.mockResolvedValue({
      data: [
        { user_id: 10, email: 'owner@example.com', full_name: 'Omar Owner', role: 'owner' },
        { user_id: 11, email: 'reviewer@example.com', full_name: 'Rita Reviewer', role: 'reviewer' },
      ],
    })

    renderDashboard()

    expect(await screen.findByText('Backend Interview')).toBeInTheDocument()
    expect(screen.getByText('Frontend Interview')).toBeInTheDocument()
    expect(screen.getByText('Total Interviews')).toBeInTheDocument()
    expect(screen.getByText('Team Members')).toBeInTheDocument()
    expect(screen.getAllByText('2').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Active').length).toBeGreaterThan(0)
    expect(screen.getByText('Draft')).toBeInTheDocument()
  })

  it('deletes a draft interview after confirmation', async () => {
    apiMock.interviews.list.mockResolvedValue({
      data: [
        { id: 1, title: 'Backend Interview', status: 'active', duration_minutes: 30, pass_score: 70, created_at: '2025-01-01T00:00:00Z' },
        { id: 2, title: 'Frontend Interview', status: 'draft', duration_minutes: 45, pass_score: 60, created_at: '2025-01-02T00:00:00Z' },
      ],
    })
    apiMock.users.getOrganizationMembers.mockResolvedValue({ data: [] })
    apiMock.interviews.delete.mockResolvedValue({ data: {} })

    renderDashboard()

    await screen.findByText('Frontend Interview')

    const deleteButtons = screen.getAllByRole('button', { name: /delete/i })
    expect(deleteButtons.length).toBe(1)

    await userEvent.click(deleteButtons[0])
    await userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: /^delete$/i }))

    await waitFor(() => {
      expect(apiMock.interviews.delete).toHaveBeenCalledWith(2)
    })
    expect(screen.queryByText('Frontend Interview')).not.toBeInTheDocument()
    expect(screen.getByText('Backend Interview')).toBeInTheDocument()
  })
})
