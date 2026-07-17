import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import EmployerDashboard from './EmployerDashboard'

const apiMock = vi.hoisted(() => ({
  interviews: {
    list: vi.fn(),
  },
  users: {
    getMyOrganization: vi.fn(),
    getMyMemberships: vi.fn(),
    addMembership: vi.fn(),
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
    apiMock.users.getMyOrganization.mockReset()
    apiMock.users.getMyMemberships.mockReset()
    apiMock.users.addMembership.mockReset()
  })

  it('shows organization details and adds an existing team member', async () => {
    apiMock.interviews.list.mockResolvedValue({ data: [] })
    apiMock.users.getMyOrganization.mockResolvedValue({
      data: { id: 1, name: 'SRIS Test Co' },
    })
    apiMock.users.getMyMemberships.mockResolvedValue({
      data: [{ id: 1, user_id: 10, role: 'owner' }],
    })
    apiMock.users.addMembership.mockResolvedValue({
      data: { id: 2, user_id: 11, role: 'reviewer' },
    })

    renderDashboard()

    expect(await screen.findByText('SRIS Test Co')).toBeInTheDocument()
    expect(screen.getByText('Team members: 1')).toBeInTheDocument()
    expect(screen.getByText('owner')).toBeInTheDocument()

    await userEvent.type(screen.getByPlaceholderText('teammate@example.com'), 'reviewer@example.com')
    await userEvent.click(screen.getByRole('button', { name: /add/i }))

    await waitFor(() => {
      expect(apiMock.users.addMembership).toHaveBeenCalledWith({
        email: 'reviewer@example.com',
        role: 'reviewer',
      })
    })
    expect(await screen.findByText('Team member added')).toBeInTheDocument()
    expect(screen.getByText('reviewer')).toBeInTheDocument()
  })
})