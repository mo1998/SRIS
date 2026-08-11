import '@testing-library/jest-dom/vitest'
import { vi } from 'vitest'
import '../i18n'

vi.mock('chart.js', () => ({
  Chart: { register: vi.fn() },
  CategoryScale: vi.fn(),
  LinearScale: vi.fn(),
  BarElement: vi.fn(),
  Title: vi.fn(),
  Tooltip: vi.fn(),
  Legend: vi.fn(),
  ArcElement: vi.fn(),
  Bar: vi.fn(() => null),
  Doughnut: vi.fn(() => null),
}))

vi.mock('react-chartjs-2', () => ({
  Bar: () => null,
  Doughnut: () => null,
}))

beforeEach(() => {
  localStorage.clear()
})