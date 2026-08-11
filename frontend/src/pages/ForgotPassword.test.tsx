import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ForgotPassword from './ForgotPassword'
import ResetPassword from './ResetPassword'

const apiMock = vi.hoisted(() => ({
  auth: {
    forgotPassword: vi.fn(),
    resetPassword: vi.fn(),
  },
}))

vi.mock('../services/api', () => ({
  api: apiMock,
}))

const renderWithRouter = (ui: React.ReactNode, url = '/') => {
  window.history.pushState({}, '', url)
  return render(<BrowserRouter>{ui}</BrowserRouter>)
}

describe('ForgotPassword', () => {
  beforeEach(() => {
    apiMock.auth.forgotPassword.mockReset()
  })

  it('submits email and shows success message', async () => {
    apiMock.auth.forgotPassword.mockResolvedValue({ data: { message: 'ok' } })

    renderWithRouter(<ForgotPassword />)

    await userEvent.type(screen.getByPlaceholderText('you@example.com'), 'user@test.com')
    await userEvent.click(screen.getByRole('button', { name: 'Send reset link' }))

    await waitFor(() => {
      expect(apiMock.auth.forgotPassword).toHaveBeenCalledWith('user@test.com')
      expect(screen.getByText(/password reset link has been sent/i)).toBeTruthy()
    })
  })

  it('shows server errors', async () => {
    apiMock.auth.forgotPassword.mockRejectedValue({
      response: { data: { detail: 'Too many requests' } },
    })

    renderWithRouter(<ForgotPassword />)

    await userEvent.type(screen.getByPlaceholderText('you@example.com'), 'user@test.com')
    await userEvent.click(screen.getByRole('button', { name: 'Send reset link' }))

    expect(await screen.findByText('Too many requests')).toBeTruthy()
  })
})

describe('ResetPassword', () => {
  beforeEach(() => {
    apiMock.auth.resetPassword.mockReset()
  })

  it('resets the password with the token from the URL', async () => {
    apiMock.auth.resetPassword.mockResolvedValue({ data: { message: 'ok' } })

    renderWithRouter(<ResetPassword />, '/reset-password?token=abc123')

    await userEvent.type(screen.getByPlaceholderText('At least 8 characters'), 'NewPassword1')
    await userEvent.type(screen.getByPlaceholderText('Re-enter your new password'), 'NewPassword1')
    await userEvent.click(screen.getByRole('button', { name: 'Reset password' }))

    await waitFor(() => {
      expect(apiMock.auth.resetPassword).toHaveBeenCalledWith('abc123', 'NewPassword1')
      expect(screen.getByText(/password has been reset/i)).toBeTruthy()
    })
  })

  it('rejects mismatched passwords', async () => {
    renderWithRouter(<ResetPassword />, '/reset-password?token=abc123')

    await userEvent.type(screen.getByPlaceholderText('At least 8 characters'), 'NewPassword1')
    await userEvent.type(screen.getByPlaceholderText('Re-enter your new password'), 'Different1')
    await userEvent.click(screen.getByRole('button', { name: 'Reset password' }))

    expect(await screen.findByText('Passwords do not match')).toBeTruthy()
    expect(apiMock.auth.resetPassword).not.toHaveBeenCalled()
  })
})