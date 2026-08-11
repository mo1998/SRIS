import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import NotificationBell from './NotificationBell'

const apiMock = vi.hoisted(() => ({
  notifications: {
    list: vi.fn(),
    unreadCount: vi.fn(),
    markRead: vi.fn(),
    markAllRead: vi.fn(),
  },
}))

vi.mock('../services/api', () => ({
  api: apiMock,
}))

const notifications = [
  { id: 1, type: 'response_completed', title: 'Candidate submitted interview', message: 'Alice completed "Screen".', link: '/interviews/1', is_read: false, created_at: new Date(Date.now() - 60000).toISOString() },
  { id: 2, type: 'evaluation_completed', title: 'Evaluation completed', message: 'Bob scored 80%.', link: '/interviews/1', is_read: true, created_at: new Date(Date.now() - 3600000).toISOString() },
]

const renderBell = () => render(
  <BrowserRouter>
    <NotificationBell />
  </BrowserRouter>
)

describe('NotificationBell', () => {
  beforeEach(() => {
    apiMock.notifications.list.mockReset()
    apiMock.notifications.unreadCount.mockReset()
    apiMock.notifications.markRead.mockReset()
    apiMock.notifications.markAllRead.mockReset()
  })

  it('loads notifications and shows unread badge', async () => {
    apiMock.notifications.list.mockResolvedValue({ data: { notifications, unread_count: 1 } })
    apiMock.notifications.unreadCount.mockResolvedValue({ data: { unread_count: 1 } })

    renderBell()

    await waitFor(() => {
      expect(screen.getByLabelText('Notifications')).toBeTruthy()
      expect(screen.getByText('1')).toBeTruthy()
    })
  })

  it('opens dropdown with notifications and marks one read on click', async () => {
    apiMock.notifications.list.mockResolvedValue({ data: { notifications, unread_count: 1 } })
    apiMock.notifications.unreadCount.mockResolvedValue({ data: { unread_count: 1 } })
    apiMock.notifications.markRead.mockResolvedValue({ data: {} })

    renderBell()

    const bell = screen.getByLabelText('Notifications')
    await userEvent.click(bell)

    await waitFor(() => {
      expect(screen.getByText('Candidate submitted interview')).toBeTruthy()
      expect(screen.getByText('Evaluation completed')).toBeTruthy()
    })

    await userEvent.click(screen.getByText('Candidate submitted interview'))
    expect(apiMock.notifications.markRead).toHaveBeenCalledWith(1)
  })

  it('marks all notifications read', async () => {
    apiMock.notifications.list.mockResolvedValue({ data: { notifications, unread_count: 1 } })
    apiMock.notifications.unreadCount.mockResolvedValue({ data: { unread_count: 1 } })
    apiMock.notifications.markAllRead.mockResolvedValue({ data: { marked: 1 } })

    renderBell()

    await userEvent.click(screen.getByLabelText('Notifications'))
    await waitFor(() => {
      expect(screen.getByText('Mark all read')).toBeTruthy()
    })

    await userEvent.click(screen.getByText('Mark all read'))
    expect(apiMock.notifications.markAllRead).toHaveBeenCalled()
  })
})
