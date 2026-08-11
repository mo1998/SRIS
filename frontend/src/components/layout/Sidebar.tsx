import React from 'react'
import { NavLink } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../../store/authStore'
import { FiBriefcase, FiFileText, FiPlusCircle, FiUser, FiBarChart2, FiUsers } from 'react-icons/fi'

interface SidebarProps {
  open: boolean
  onClose: () => void
}

const Sidebar: React.FC<SidebarProps> = ({ open, onClose }) => {
  const { user } = useAuth()
  const { t } = useTranslation()

  return (
    <>
      {open && <div className="d-md-none" onClick={onClose} style={{ position: 'fixed', inset: 0, zIndex: 999 }} />}
      <aside className={`sidebar${open ? ' open' : ''}`}>
        <div className="sidebar-header">
          <div className="brand-icon">
            <FiBriefcase />
          </div>
          <span className="brand-text">{t('sidebar.brand')}</span>
        </div>

        <nav className="sidebar-nav">
          {user?.role === 'employer' && (
            <>
              <div className="sidebar-section-label">{t('sidebar.sectionEmployer')}</div>
              <NavLink to="/employer/dashboard" className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`} onClick={onClose}>
                <FiBarChart2 className="link-icon" />
                {t('sidebar.dashboard')}
              </NavLink>
              <NavLink to="/employer/interviews/create" className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`} onClick={onClose}>
                <FiPlusCircle className="link-icon" />
                {t('sidebar.createInterview')}
              </NavLink>
            </>
          )}

          {user?.role === 'employee' && (
            <>
              <div className="sidebar-section-label">{t('sidebar.sectionEmployee')}</div>
              <NavLink to="/employee/results" className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`} onClick={onClose}>
                <FiFileText className="link-icon" />
                {t('sidebar.myResults')}
              </NavLink>
            </>
          )}

          <div className="sidebar-section-label mt-3">{t('sidebar.sectionGeneral')}</div>
          <NavLink to="/account/settings" className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`} onClick={onClose}>
            <FiUser className="link-icon" />
            {t('sidebar.accountSettings')}
          </NavLink>
        </nav>

        <div className="sidebar-footer">
          <div className="d-flex align-items-center gap-2 px-1">
            <div
              className="d-flex align-items-center justify-content-center rounded-circle flex-shrink-0"
              style={{ width: 32, height: 32, background: 'var(--color-primary)', fontSize: '0.75rem', fontWeight: 600 }}
            >
              {user?.full_name?.charAt(0)?.toUpperCase() || '?'}
            </div>
            <div className="min-w-0">
              <div style={{ fontSize: '0.8rem', fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {user?.full_name || 'User'}
              </div>
              <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.5)', textTransform: 'capitalize' }}>
                {user?.role || ''}
              </div>
            </div>
          </div>
        </div>
      </aside>
    </>
  )
}

export default Sidebar
