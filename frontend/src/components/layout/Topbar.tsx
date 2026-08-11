import React from 'react'
import { useAuth } from '../../store/authStore'
import { FiLogOut, FiMenu, FiUser, FiChevronDown } from 'react-icons/fi'
import { useNavigate } from 'react-router-dom'
import NotificationBell from '../NotificationBell'

interface TopbarProps {
  onToggleSidebar: () => void
}

const Topbar: React.FC<TopbarProps> = ({ onToggleSidebar }) => {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = React.useState(false)
  const menuRef = React.useRef<HTMLDivElement>(null)

  React.useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  const handleLogout = () => {
    setMenuOpen(false)
    logout()
    navigate('/login')
  }

  return (
    <header className="topbar">
      <div className="topbar-left">
        <button className="sidebar-toggle d-md-none" onClick={onToggleSidebar}>
          <FiMenu />
        </button>
        <button
          className="btn btn-link d-none d-md-flex text-muted p-1"
          onClick={onToggleSidebar}
          style={{ fontSize: '1.25rem' }}
        >
          <FiMenu />
        </button>
      </div>

      <div className="topbar-right" ref={menuRef}>
        <div className="me-2">
          <NotificationBell />
        </div>
        <div className="topbar-user" onClick={() => setMenuOpen(!menuOpen)}>
          <div className="topbar-avatar">
            {user?.full_name?.charAt(0)?.toUpperCase() || '?'}
          </div>
          <span className="d-none d-sm-inline" style={{ fontSize: '0.875rem', fontWeight: 500 }}>
            {user?.full_name || 'User'}
          </span>
          <FiChevronDown size={14} className="text-muted" />
        </div>

        {menuOpen && (
          <div
            style={{
              position: 'absolute',
              top: '100%',
              right: '1rem',
              background: 'var(--color-white)',
              border: '1px solid var(--color-gray-200)',
              borderRadius: 'var(--radius-md)',
              boxShadow: 'var(--shadow-lg)',
              minWidth: 180,
              zIndex: 1000,
              padding: '0.25rem',
            }}
          >
            <button
              className="dropdown-item"
              onClick={() => { setMenuOpen(false); navigate('/account/settings') }}
              style={{ borderRadius: 'var(--radius-sm)' }}
            >
              <FiUser className="me-2" />Account Settings
            </button>
            <hr className="my-1" />
            <button
              className="dropdown-item"
              onClick={handleLogout}
              style={{ borderRadius: 'var(--radius-sm)', color: 'var(--color-danger)' }}
            >
              <FiLogOut className="me-2" />Logout
            </button>
          </div>
        )}
      </div>
    </header>
  )
}

export default Topbar
