import React from 'react'
import { Navbar as BSNavbar, Nav, Container, NavDropdown } from 'react-bootstrap'
import { useAuth } from '../store/authStore'
import { Link } from 'react-router-dom'
import { FiUser, FiLogOut, FiBriefcase, FiFileText } from 'react-icons/fi'

const Navbar: React.FC = () => {
  const { isAuthenticated, user, logout } = useAuth()
  
  const handleLogout = () => {
    logout()
    window.location.href = '/login'
  }
  
  return (
    <BSNavbar bg="primary" variant="dark" expand="lg">
      <Container>
        <BSNavbar.Brand as={Link} to="/">
          <FiBriefcase className="me-2" />
          Smart Interview System
        </BSNavbar.Brand>
        <BSNavbar.Toggle aria-controls="navbar-nav" />
        <BSNavbar.Collapse id="navbar-nav">
          <Nav className="ms-auto">
            {isAuthenticated ? (
              <>
                {user?.role === 'employer' && (
                  <>
                    <Nav.Link as={Link} to="/employer/dashboard">
                      <FiFileText className="me-1" /> Dashboard
                    </Nav.Link>
                    <Nav.Link as={Link} to="/employer/interviews/create">
                      Create Interview
                    </Nav.Link>
                  </>
                )}
                
                {user?.role === 'employee' && (
                  <Nav.Link as={Link} to="/employee/results">
                    My Results
                  </Nav.Link>
                )}
                
                <NavDropdown title={
                  <span>
                    <FiUser className="me-1" />
                    {user?.full_name}
                  </span>
                } id="user-dropdown">
                  <NavDropdown.Item>{user?.email}</NavDropdown.Item>
                  <NavDropdown.Item>{user?.role}</NavDropdown.Item>
                  <NavDropdown.Divider />
                  <NavDropdown.Item onClick={handleLogout}>
                    <FiLogOut className="me-1" /> Logout
                  </NavDropdown.Item>
                </NavDropdown>
              </>
            ) : (
              <>
                <Nav.Link as={Link} to="/login">Login</Nav.Link>
                <Nav.Link as={Link} to="/register">Register</Nav.Link>
              </>
            )}
          </Nav>
        </BSNavbar.Collapse>
      </Container>
    </BSNavbar>
  )
}

export default Navbar
