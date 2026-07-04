import { create } from 'zustand'
import { Student } from '@/types'

interface AuthStore {
  student: Student | null
  token: string | null
  isLoading: boolean
  login: (student: Student, token: string) => void
  logout: () => void
  updateStudent: (student: Student) => void
  setLoading: (loading: boolean) => void
}

export const useAuthStore = create<AuthStore>((set) => ({
  student: localStorage.getItem('student') ? JSON.parse(localStorage.getItem('student')!) : null,
  token: localStorage.getItem('access_token'),
  isLoading: false,

  login: (student: Student, token: string) => {
    localStorage.setItem('student', JSON.stringify(student))
    localStorage.setItem('access_token', token)
    set({ student, token })
  },

  logout: () => {
    localStorage.removeItem('student')
    localStorage.removeItem('access_token')
    set({ student: null, token: null })
  },

  updateStudent: (student: Student) => {
    localStorage.setItem('student', JSON.stringify(student))
    set({ student })
  },

  setLoading: (loading: boolean) => {
    set({ isLoading: loading })
  },
}))
