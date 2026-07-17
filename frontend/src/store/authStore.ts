import { create } from 'zustand'
import axios from 'axios'

interface User {
  id: number
  email: string
  full_name: string
  role: 'employer' | 'employee' | 'admin'
  company_name?: string
}

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  register: (data: any) => Promise<void>
  logout: () => void
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem('token'),
  isAuthenticated: !!localStorage.getItem('token'),
  
  login: async (email: string, password: string) => {
    const formData = new FormData()
    formData.append('username', email)
    formData.append('password', password)
    
    const response = await axios.post('/api/auth/login', formData)
    const { access_token, refresh_token } = response.data
    
    localStorage.setItem('token', access_token)
    localStorage.setItem('refreshToken', refresh_token)
    
    // Get user info
    const userResponse = await axios.get('/api/auth/me', {
      headers: { Authorization: `Bearer ${access_token}` }
    })
    
    set({
      user: userResponse.data,
      token: access_token,
      isAuthenticated: true
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
    
    localStorage.setItem('token', access_token)
    localStorage.setItem('refreshToken', refresh_token)
    
    set({
      user: user,
      token: access_token,
      isAuthenticated: true
    })
  },
  
  logout: () => {
    localStorage.removeItem('token')
    localStorage.removeItem('refreshToken')
    set({ user: null, token: null, isAuthenticated: false })
  }
}))

// Axios interceptor for auth
axios.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  return children
}
