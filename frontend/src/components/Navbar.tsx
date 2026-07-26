import React from 'react'
import { Navbar as BSNavbar, Nav, Container, Button } from 'react-bootstrap'
import { Link } from 'react-router-dom'
import { FiBriefcase } from 'react-icons/fi'

const Navbar: React.FC = () => {
  return (
    <BSNavbar bg="white" expand="lg" className="border-bottom shadow-sm" sticky="top">
      <Container>
        <BSNavbar.Brand as={Link} to="/" className="fw-bold" style={{ color: 'var(--color-primary)' }}>
          <div className="d-inline-flex align-items-center justify-content-center rounded-2 me-2"
            style={{ width: 32, height: 32, background: 'var(--color-primary)', color: 'white', fontSize: '0.9rem' }}>
            <FiBriefcase />
          </div>
          SRIS
        </BSNavbar.Brand>
        <BSNavbar.Toggle aria-controls="navbar-nav" />
        <BSNavbar.Collapse id="navbar-nav">
          <Nav className="ms-auto align-items-lg-center gap-2">
            <Nav.Link as={Link} to="/login" className="text-muted">Sign in</Nav.Link>
            <Button as={Link as any} to="/register" variant="primary" size="sm" className="px-3">
              Get started
            </Button>
          </Nav>
        </BSNavbar.Collapse>
      </Container>
    </BSNavbar>
  )
}

export default Navbar
