import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AccountSettings from './AccountSettings'

const apiMock = vi.hoisted(() => ({
  users: {
    updateMe: vi.fn(),
  },
}))

const authMock = vi.hoisted(() => ({
  user: {
    id: 1,
    email: 'employer@example.com',
    full_name: 'Test Employer',
    role: 'employer',
    phone: '',
  },
  updateUser: vi.fn(),
}))

vi.mock('../services/api', () => ({
  api: apiMock,
}))

vi.mock('../store/authStore', () => ({
  useAuth: () => authMock,
}))

describe('AccountSettings', () => {
  beforeEach(() => {
    apiMock.users.updateMe.mockReset()
    authMock.updateUser.mockReset()
  })

  it('submits profile updates', async () => {
    apiMock.users.updateMe.mockResolvedValue({
      data: {
        id: 1,
        email: 'employer@example.com',
        full_name: 'Updated Employer',
        role: 'employer',
        phone: '+15551234567',
      },
    })

    render(<AccountSettings />)

    const fullNameInput = screen.getByLabelText(/full name/i)
    await userEvent.clear(fullNameInput)
    await userEvent.type(fullNameInput, 'Updated Employer')
    await userEvent.type(screen.getByLabelText(/phone/i), '+15551234567')
    await userEvent.click(screen.getByRole('button', { name: /save changes/i }))

    await waitFor(() => {
      expect(apiMock.users.updateMe).toHaveBeenCalledWith({
        full_name: 'Updated Employer',
        phone: '+15551234567',
      })
    })
    expect(await screen.findByText('Account updated')).toBeInTheDocument()
    expect(authMock.updateUser).toHaveBeenCalledWith({
      id: 1,
      email: 'employer@example.com',
      full_name: 'Updated Employer',
      role: 'employer',
      phone: '+15551234567',
    })
  })
})