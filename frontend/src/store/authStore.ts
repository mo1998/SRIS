import { create } from 'zustand'
import { useEffect } from 'react'
import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'

interface User {
  id: number
  email: string
  full_name: string
  role: 'employer' | 'employee' | 'admin'
  company_name?: string
  phone?: string
}

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  initializeAuth: () => Promise<void>
  updateUser: (user: User) => void
  login: (email: string, password: string) => Promise<void>
  register: (data: any) => Promise<void>
  logout: () => void
}

type RetryRequestConfig = InternalAxiosRequestConfig & { _retry?: boolean }

const getStoredToken = () => localStorage.getItem('token')
const getStoredRefreshToken = () => localStorage.getItem('refreshToken')

const storeTokens = (accessToken: string, refreshToken: string) => {
  localStorage.setItem('token', accessToken)
  localStorage.setItem('refreshToken', refreshToken)
}

const clearTokens = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('refreshToken')
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  token: getStoredToken(),
  isAuthenticated: false,
  isLoading: !!getStoredToken(),

  initializeAuth: async () => {
    const token = getStoredToken()
    if (!token) {
      set({ user: null, token: null, isAuthenticated: false, isLoading: false })
      return
    }

    try {
      const response = await axios.get('/api/auth/me')
      set({
        user: response.data,
        token,
        isAuthenticated: true,
        isLoading: false
      })
    } catch {
      clearTokens()
      set({ user: null, token: null, isAuthenticated: false, isLoading: false })
    }
  },

  updateUser: (user: User) => {
    set({ user })
  },
  
  login: async (email: string, password: string) => {
    const formData = new FormData()
    formData.append('username', email)
    formData.append('password', password)
    
    const response = await axios.post('/api/auth/login', formData)
    const { access_token, refresh_token } = response.data
    
    storeTokens(access_token, refresh_token)
    
    // Get user info
    const userResponse = await axios.get('/api/auth/me', {
      headers: { Authorization: `Bearer ${access_token}` }
    })
    
    set({
      user: userResponse.data,
      token: access_token,
      isAuthenticated: true,
      isLoading: false
    })
  },
  
  register: async (data: any) => {
    const response = await axios.post('/api/auth/register', data)
    const user = response.data
    
    // Auto login after registration
    const formData = new FormData()
    formData.append('username', data.email)
    formData.append('password', data.password)
    
    const loginResponse = await axios.post('/api/auth/login', formData)
    const { access_token, refresh_token } = loginResponse.data
    
    storeTokens(access_token, refresh_token)
    
    set({
      user: user,
      token: access_token,
      isAuthenticated: true,
      isLoading: false
    })
  },
  
  logout: () => {
    clearTokens()
    set({ user: null, token: null, isAuthenticated: false, isLoading: false })
  }
}))

// Axios interceptor for auth
axios.interceptors.request.use(
  (config) => {
    const token = getStoredToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

axios.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as RetryRequestConfig | undefined
    const refreshToken = getStoredRefreshToken()
    const isRefreshRequest = originalRequest?.url?.includes('/api/auth/refresh')

    if (error.response?.status !== 401 || !originalRequest || originalRequest._retry || !refreshToken || isRefreshRequest) {
      return Promise.reject(error)
    }

    originalRequest._retry = true

    try {
      const response = await axios.post('/api/auth/refresh', null, {
        params: { refresh_token: refreshToken }
      })
      const { access_token, refresh_token } = response.data
      storeTokens(access_token, refresh_token)
      useAuth.setState({ token: access_token, isAuthenticated: true })
      originalRequest.headers.Authorization = `Bearer ${access_token}`
      return axios(originalRequest)
    } catch (refreshError) {
      clearTokens()
      useAuth.setState({ user: null, token: null, isAuthenticated: false, isLoading: false })
      return Promise.reject(refreshError)
    }
  }
)

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const initializeAuth = useAuth((state) => state.initializeAuth)

  useEffect(() => {
    initializeAuth()
  }, [initializeAuth])

  return children
}
