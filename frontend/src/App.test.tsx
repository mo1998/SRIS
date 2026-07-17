import { render, screen } from '@testing-library/react'
import App from './App'

describe('App routing', () => {
  it('renders the login page for unauthenticated users', async () => {
    window.history.pushState({}, '', '/')

    render(<App />)

    expect(await screen.findByRole('button', { name: /login/i })).toBeInTheDocument()
    expect(screen.getByText(/don't have an account/i)).toBeInTheDocument()
  })
})