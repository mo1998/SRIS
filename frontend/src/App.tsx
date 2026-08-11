import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './store/authStore'
import Navbar from './components/Navbar'
import AppLayout from './components/layout/AppLayout'
import LoadingSpinner from './components/ui/LoadingSpinner'
import Login from './pages/Login'
import Register from './pages/Register'
import EmployerDashboard from './pages/EmployerDashboard'
import CreateInterview from './pages/CreateInterview'
import InterviewDetail from './pages/InterviewDetail'
import CandidateReport from './pages/CandidateReport'
import InterviewRoom from './pages/InterviewRoom'
import ResultsPortal from './pages/ResultsPortal'
import MyResults from './pages/MyResults'
import AccountSettings from './pages/AccountSettings'
import ForgotPassword from './pages/ForgotPassword'
import ResetPassword from './pages/ResetPassword'

const ProtectedRoute: React.FC<{ children: React.ReactNode; roles?: string[] }> = ({ children, roles }) => {
  const { isAuthenticated, isLoading, user } = useAuth()

  if (isLoading) {
    return <LoadingSpinner />
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" />
  }

  if (roles && user && !roles.includes(user.role)) {
    return <Navigate to="/" />
  }

  return <>{children}</>
}

const PublicLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <>
    <Navbar />
    <div className="container mt-4">{children}</div>
  </>
)

const AuthenticatedLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AppLayout>{children}</AppLayout>
)

const AppRoutes: React.FC = () => {
  const { isAuthenticated, isLoading, user } = useAuth()

  if (isLoading) {
    return (
      <Router>
        <LoadingSpinner />
      </Router>
    )
  }

  return (
    <Router>
      <Routes>
        <Route path="/login" element={
          isAuthenticated ? <Navigate to="/" /> : (
            <PublicLayout><Login /></PublicLayout>
          )
        } />
        <Route path="/register" element={
          isAuthenticated ? <Navigate to="/" /> : (
            <PublicLayout><Register /></PublicLayout>
          )
        } />
        <Route path="/forgot-password" element={
          isAuthenticated ? <Navigate to="/" /> : (
            <PublicLayout><ForgotPassword /></PublicLayout>
          )
        } />
        <Route path="/reset-password" element={
          isAuthenticated ? <Navigate to="/" /> : (
            <PublicLayout><ResetPassword /></PublicLayout>
          )
        } />

        <Route path="/" element={
          isAuthenticated ? (
            user?.role === 'employer' ? <Navigate to="/employer/dashboard" /> : <Navigate to="/employee/results" />
          ) : (
            <Navigate to="/login" />
          )
        } />

        <Route path="/employer/dashboard" element={
          <ProtectedRoute roles={['employer']}>
            <AuthenticatedLayout><EmployerDashboard /></AuthenticatedLayout>
          </ProtectedRoute>
        } />

        <Route path="/employer/interviews/create" element={
          <ProtectedRoute roles={['employer']}>
            <AuthenticatedLayout><CreateInterview /></AuthenticatedLayout>
          </ProtectedRoute>
        } />

        <Route path="/employer/interviews/:id" element={
          <ProtectedRoute roles={['employer']}>
            <AuthenticatedLayout><InterviewDetail /></AuthenticatedLayout>
          </ProtectedRoute>
        } />

        <Route path="/employer/candidate/:responseId" element={
          <ProtectedRoute roles={['employer']}>
            <AuthenticatedLayout><CandidateReport /></AuthenticatedLayout>
          </ProtectedRoute>
        } />

        <Route path="/account/settings" element={
          <ProtectedRoute>
            <AuthenticatedLayout><AccountSettings /></AuthenticatedLayout>
          </ProtectedRoute>
        } />

        <Route path="/interview/:token" element={<InterviewRoom />} />

        <Route path="/results/:token" element={<ResultsPortal />} />

        <Route path="/employee/results" element={
          <ProtectedRoute roles={['employee']}>
            <AuthenticatedLayout><MyResults /></AuthenticatedLayout>
          </ProtectedRoute>
        } />

        <Route path="/employee/candidate/:responseId" element={
          <ProtectedRoute roles={['employee']}>
            <AuthenticatedLayout><CandidateReport /></AuthenticatedLayout>
          </ProtectedRoute>
        } />
      </Routes>
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
