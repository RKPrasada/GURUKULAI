import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import StudyPage from '../StudyPage'
import api from '@/services/api'
import { useAuthStore } from '@/store/auth'

// Mock the API and Auth Store
vi.mock('@/services/api', () => ({
  default: {
    sendMessage: vi.fn(),
  }
}))

vi.mock('@/store/auth', () => ({
  useAuthStore: vi.fn()
}))

describe('StudyPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    
    // Mock user being logged in with some mock data
    const mockStudent = {
      student_id: '123',
      weakness_map: []
    }
    
    ;(useAuthStore as any).mockImplementation((selector: any) => 
      selector({ student: mockStudent })
    )
    
    // Mock the API response to avoid errors during test execution
    ;(api.sendMessage as any).mockResolvedValue({
      data: { text: "Here is your schedule.", cardData: null }
    })
  })

  it('renders the Generate My Schedule button', () => {
    render(
      <BrowserRouter>
        <StudyPage />
      </BrowserRouter>
    )
    
    const button = screen.getByRole('button', { name: /Generate My Schedule/i })
    expect(button).toBeInTheDocument()
  })

  it('invokes api.sendMessage with the exact string when Generate My Schedule is clicked', async () => {
    render(
      <BrowserRouter>
        <StudyPage />
      </BrowserRouter>
    )
    
    const button = screen.getByRole('button', { name: /Generate My Schedule/i })
    
    // Simulate user click
    fireEvent.click(button)
    
    // Verify that the API was called with the specific prompt
    expect(api.sendMessage).toHaveBeenCalledTimes(1)
    expect(api.sendMessage).toHaveBeenCalledWith('Generate my full syllabus schedule')
  })
})
