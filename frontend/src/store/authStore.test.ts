import { act } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const axiosMock = vi.hoisted(() => {
  const client = vi.fn()
  return Object.assign(client, {
    get: vi.fn(),
    post: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  })
})

vi.mock('axios', () => ({
  default: axiosMock,
}))

const importAuthStore = async () => {
  vi.resetModules()
  return import('./authStore')
}

describe('auth store', () => {
  beforeEach(() => {
    localStorage.clear()
    axiosMock.mockReset()
    axiosMock.get.mockReset()
    axiosMock.post.mockReset()
    axiosMock.interceptors.request.use.mockReset()
    axiosMock.interceptors.response.use.mockReset()
  })

  it('loads the current user when an access token is already stored', async () => {
    localStorage.setItem('token', 'saved-access-token')
    axiosMock.get.mockResolvedValue({
      data: {
        id: 1,
        email: 'employer@example.com',
        full_name: 'Test Employer',
        role: 'employer',
      },
    })

    const { useAuth } = await importAuthStore()

    await act(async () => {
      await useAuth.getState().initializeAuth()
    })

    expect(axiosMock.get).toHaveBeenCalledWith('/api/auth/me')
    expect(useAuth.getState()).toMatchObject({
      token: 'saved-access-token',
      isAuthenticated: true,
      isLoading: false,
      user: {
        email: 'employer@example.com',
        role: 'employer',
      },
    })
  })

  it('refreshes an expired access token and retries the original request once', async () => {
    localStorage.setItem('refreshToken', 'saved-refresh-token')
    axiosMock.post.mockResolvedValue({
      data: {
        access_token: 'new-access-token',
        refresh_token: 'new-refresh-token',
      },
    })
    axiosMock.mockResolvedValue({ data: { ok: true } })

    await importAuthStore()
    const responseInterceptor = axiosMock.interceptors.response.use.mock.calls[0][1]

    await responseInterceptor({
      response: { status: 401 },
      config: { headers: {} },
    })

    expect(axiosMock.post).toHaveBeenCalledWith('/api/auth/refresh', null, {
      params: { refresh_token: 'saved-refresh-token' },
    })
    expect(localStorage.getItem('token')).toBe('new-access-token')
    expect(localStorage.getItem('refreshToken')).toBe('new-refresh-token')
    expect(axiosMock).toHaveBeenCalledWith({
      _retry: true,
      headers: { Authorization: 'Bearer new-access-token' },
    })
  })

  it('updates the current user in auth state', async () => {
    const { useAuth } = await importAuthStore()

    act(() => {
      useAuth.getState().updateUser({
        id: 1,
        email: 'employer@example.com',
        full_name: 'Updated Employer',
        role: 'employer',
        phone: '+15551234567',
      })
    })

    expect(useAuth.getState().user).toMatchObject({
      full_name: 'Updated Employer',
      phone: '+15551234567',
    })
  })
})