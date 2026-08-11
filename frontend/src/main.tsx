import React from 'react'
import ReactDOM from 'react-dom/client'
import './i18n'
import App from './App'
import 'bootstrap/dist/css/bootstrap.min.css'
import './styles/theme.css'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
