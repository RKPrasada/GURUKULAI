export interface Student {
  user_id: string
  username: string
  full_name: string
  email: string
  exam_target: 'rrb_ntpc' | 'nda' | 'jee' | 'neet'
  preferred_language: 'en' | 'hi'
  diagnostic_done: boolean
  weakness_map: WeaknessMap[]
  study_streak_days: number
  total_questions_attempted: number
}

export interface WeaknessMap {
  subject: string
  topic: string
  score_pct: number
  attempts: number
  last_attempted: string
  ease_factor: number
  interval_days: number
  next_review_date: string
}

export interface Question {
  question_id: string
  exam: string
  subject: string
  topic: string
  difficulty: 1 | 2 | 3
  question_text_en: string
  question_text_hi?: string
  options: string[]
  correct_index: number
  explanation_en: string
  explanation_hi?: string
}

export interface DiagnosticSession {
  session_id: string
  questions: Question[]
  total: number
}

export interface APIResponse<T = any> {
  data?: T
  error?: string
  message?: string
}
