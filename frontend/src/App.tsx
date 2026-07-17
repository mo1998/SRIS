import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './store/authStore'
import Navbar from './components/Navbar'
import Login from './pages/Login'
import Register from './pages/Register'
import EmployerDashboard from './pages/EmployerDashboard'
import CreateInterview from './pages/CreateInterview'
import InterviewDetail from './pages/InterviewDetail'
import CandidateReport from './pages/CandidateReport'
import InterviewRoom from './pages/InterviewRoom'
import MyResults from './pages/MyResults'

const ProtectedRoute: React.FC<{ children: React.ReactNode; roles?: string[] }> = ({ children, roles }) => {
  const { isAuthenticated, user } = useAuth()
  
  if (!isAuthenticated) {
    return <Navigate to="/login" />
  }
  
  if (roles && user && !roles.includes(user.role)) {
    return <Navigate to="/" />
  }
  
  return <>{children}</>
}

const AppRoutes: React.FC = () => {
  const { isAuthenticated, user } = useAuth()
  
  return (
    <Router>
      <Navbar />
      <div className="container mt-4">
        <Routes>
          <Route path="/login" element={isAuthenticated ? <Navigate to="/" /> : <Login />} />
          <Route path="/register" element={isAuthenticated ? <Navigate to="/" /> : <Register />} />
          
          <Route path="/" element={
            isAuthenticated ? (
              user?.role === 'employer' ? <Navigate to="/employer/dashboard" /> : <Navigate to="/employee/results" />
            ) : (
              <Navigate to="/login" />
            )
          } />
          
          <Route path="/employer/dashboard" element={
            <ProtectedRoute roles={['employer']}>
              <EmployerDashboard />
            </ProtectedRoute>
          } />
          
          <Route path="/employer/interviews/create" element={
            <ProtectedRoute roles={['employer']}>
              <CreateInterview />
            </ProtectedRoute>
          } />
          
          <Route path="/employer/interviews/:id" element={
            <ProtectedRoute roles={['employer']}>
              <InterviewDetail />
            </ProtectedRoute>
          } />
          
          <Route path="/employer/candidate/:responseId" element={
            <ProtectedRoute roles={['employer']}>
              <CandidateReport />
            </ProtectedRoute>
          } />
          
          <Route path="/interview/:token" element={<InterviewRoom />} />
          
          <Route path="/employee/results" element={
            <ProtectedRoute roles={['employee']}>
              <MyResults />
            </ProtectedRoute>
          } />
        </Routes>
      </div>
    </Router>
  )
}

function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}

export default App
