import React from 'react'
import { useTranslation } from 'react-i18next'
import { FiGlobe } from 'react-icons/fi'
import { setLanguage } from '.'

const LanguageSwitcher: React.FC = () => {
  const { i18n } = useTranslation()
  const current = i18n.language || 'en'

  const toggle = () => {
    setLanguage(current === 'ar' ? 'en' : 'ar')
  }

  return (
    <button
      type="button"
      className="btn btn-sm btn-outline-secondary d-inline-flex align-items-center gap-1"
      onClick={toggle}
      aria-label="Switch language"
      title="Switch language"
    >
      <FiGlobe />
      {current === 'ar' ? 'English' : 'العربية'}
    </button>
  )
}

export default LanguageSwitcher
