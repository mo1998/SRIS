import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import OrganizationSettings from './OrganizationSettings'

const apiMock = vi.hoisted(() => ({
  users: {
    getMyOrganization: vi.fn(),
    getOrganizationMembers: vi.fn(),
    addMembership: vi.fn(),
  },
}))

vi.mock('../services/api', () => ({
  api: apiMock,
}))

const renderPage = () => render(<OrganizationSettings />)

describe('OrganizationSettings', () => {
  beforeEach(() => {
    apiMock.users.getMyOrganization.mockReset()
    apiMock.users.getOrganizationMembers.mockReset()
    apiMock.users.addMembership.mockReset()
  })

  it('shows organization details on the Organization tab', async () => {
    apiMock.users.getMyOrganization.mockResolvedValue({ data: { id: 1, name: 'SRIS Test Co' } })
    apiMock.users.getOrganizationMembers.mockResolvedValue({ data: [] })

    renderPage()

    expect(await screen.findByText('SRIS Test Co')).toBeInTheDocument()
    expect(screen.getByText('Team members: 0')).toBeInTheDocument()
  })

  it('lists team members and adds a new member on the Team Access tab', async () => {
    apiMock.users.getMyOrganization.mockResolvedValue({ data: { id: 1, name: 'SRIS Test Co' } })
    apiMock.users.getOrganizationMembers
      .mockResolvedValueOnce({
        data: [
          { user_id: 10, email: 'owner@example.com', full_name: 'Omar Owner', role: 'owner' },
          { user_id: 11, email: 'reviewer@example.com', full_name: 'Rita Reviewer', role: 'reviewer' },
        ],
      })
      .mockResolvedValueOnce({
        data: [
          { user_id: 10, email: 'owner@example.com', full_name: 'Omar Owner', role: 'owner' },
          { user_id: 11, email: 'reviewer@example.com', full_name: 'Rita Reviewer', role: 'reviewer' },
          { user_id: 12, email: 'newmember@example.com', full_name: 'Nina New', role: 'reviewer' },
        ],
      })
    apiMock.users.addMembership.mockResolvedValue({
      data: { user_id: 12, email: 'newmember@example.com', role: 'reviewer' },
    })

    renderPage()

    await userEvent.click(await screen.findByRole('tab', { name: /team access/i }))

    expect(screen.getByText('Omar Owner')).toBeInTheDocument()
    expect(screen.getByText('Rita Reviewer')).toBeInTheDocument()
    expect(screen.getByText('reviewer@example.com')).toBeInTheDocument()

    await userEvent.type(screen.getByPlaceholderText('teammate@example.com'), 'newmember@example.com')
    await userEvent.click(screen.getByRole('button', { name: /add/i }))

    await waitFor(() => {
      expect(apiMock.users.addMembership).toHaveBeenCalledWith({
        email: 'newmember@example.com',
        role: 'reviewer',
      })
    })
    expect(await screen.findByText('newmember@example.com')).toBeInTheDocument()
    expect(screen.getByText('Nina New')).toBeInTheDocument()
  })
})
