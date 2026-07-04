import axios, { AxiosInstance } from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

class ApiService {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    this.client.interceptors.request.use((config) => {
      const token = localStorage.getItem('access_token')
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
      return config
    })

    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('access_token')
          localStorage.removeItem('student')
          window.location.href = '/login'
        }
        return Promise.reject(error)
      }
    )
  }

  // Auth endpoints
  async register(data: {
    username: string
    email: string
    password: string
    confirm_password: string
    full_name: string
    exam_target: string
    preferred_language: string
    trade?: string
    engineering_discipline?: string
  }) {
    return this.client.post('/api/auth/register', data)
  }

  async login(username: string, password: string) {
    return this.client.post('/api/auth/login', { username, password })
  }

  async demoLogin(examTarget = 'rrb_ntpc', preferredLanguage = 'en', name = 'Demo Student') {
    return this.client.post('/api/student/demo', {
      exam_target: examTarget,
      preferred_language: preferredLanguage,
      name,
    })
  }

  async forgotPassword(email: string) {
    return this.client.post('/api/auth/forgot-password', null, { params: { email } })
  }

  async resetPassword(user_id: string, reset_token: string, new_password: string, confirm_password: string) {
    return this.client.post('/api/auth/reset-password', {
      user_id,
      reset_token,
      new_password,
      confirm_password,
    })
  }

  async changePassword(user_id: string, old_password: string, new_password: string, confirm_password: string) {
    return this.client.post('/api/auth/change-password', {
      user_id,
      old_password,
      new_password,
      confirm_password,
    })
  }

  // Student endpoints
  async getStudent(studentId: string) {
    return this.client.get(`/api/student/${studentId}`)
  }

  // Diagnostic endpoints
  async startDiagnostic() {
    return this.client.post('/api/session/diagnostic/start')
  }

  async submitDiagnostic(sessionId: string, answers: { [key: string]: number }) {
    return this.client.post('/api/session/diagnostic/submit', {
      session_id: sessionId,
      answers,
    })
  }

  // Session endpoints (chat)
  async sendMessage(message: string) {
    return this.client.post('/api/session/chat', {
      message,
    })
  }

  async confirmSessionAction(token: string) {
    return this.client.post('/api/session/confirm-action', { token })
  }

  async cancelSessionAction(token: string) {
    return this.client.post('/api/session/cancel-action', { token })
  }

  // Assessment endpoints
  async startAssessment(difficulty: string) {
    return this.client.post('/api/session/assessment/start', {
      difficulty,
    })
  }

  async submitAnswer(sessionId: string, questionId: string, answerIndex: number) {
    return this.client.post('/api/session/assessment/answer', {
      session_id: sessionId,
      question_id: questionId,
      answer_index: answerIndex,
    })
  }

  // Progress endpoints
  async getStudyPlan(studentId: string) {
    return this.client.get(`/api/progress/${studentId}/plan`)
  }

  async createSchedule(studentId: string) {
    return this.client.post(`/api/progress/${studentId}/schedule`)
  }

  // Dabbu study plan (new)
  async getDabbuActivePlan() {
    return this.client.get('/api/dabbu/study-plan')
  }
  async getDabbuProposedPlan() {
    return this.client.get('/api/dabbu/study-plan/proposed')
  }
  async generateDabbuPlan(examDate?: string) {
    return this.client.post('/api/dabbu/study-plan', { exam_date: examDate ?? null })
  }
  async checkProgress() {
    return this.client.post('/api/dabbu/check-progress')
  }

  async confirmAction(studentId: string, token: string, route: string) {
    return this.client.post(`/api/progress/${studentId}/${route}/execute`, null, {
      params: { token },
    })
  }

  async sendDigest(studentId: string, email: string, name: string) {
    return this.client.post(`/api/progress/${studentId}/digest`, {
      student_id: studentId,
      email,
      name,
    })
  }

  // Admin endpoints
  async listYouTubeChannels() {
    return this.client.get('/api/admin/youtube-channels')
  }

  async listExamChannels(examTarget: string) {
    return this.client.get(`/api/admin/youtube-channels/${examTarget}`)
  }

  async addYouTubeChannel(examTarget: string, channel: {
    channel_id: string
    name: string
    description?: string
    priority?: number
  }) {
    return this.client.post(`/api/admin/youtube-channels/${examTarget}`, channel)
  }

  async updateYouTubeChannel(
    examTarget: string,
    channelId: string,
    channel: {
      channel_id: string
      name: string
      description?: string
      priority?: number
    }
  ) {
    return this.client.put(`/api/admin/youtube-channels/${examTarget}/${channelId}`, channel)
  }

  async deleteYouTubeChannel(examTarget: string, channelId: string) {
    return this.client.delete(`/api/admin/youtube-channels/${examTarget}/${channelId}`)
  }

  // ── Mentor (NAGA) endpoints ──────────────────────────────────────────────

  // Questions
  async postQuestion(subject: string, topic: string, content: string) {
    return this.client.post('/api/mentor/questions', { subject, topic, content })
  }
  async listQuestions() {
    return this.client.get('/api/mentor/questions')
  }
  async pendingQuestions() {
    return this.client.get('/api/mentor/questions/pending')
  }
  async approveQuestion(questionId: string, approved: boolean) {
    return this.client.post(`/api/mentor/questions/${questionId}/approve`, { approved })
  }
  async answerQuestion(questionId: string, answer: string) {
    return this.client.post(`/api/mentor/questions/${questionId}/answer`, { answer })
  }
  async upvoteQuestion(questionId: string) {
    return this.client.post(`/api/mentor/questions/${questionId}/upvote`)
  }
  async resolveQuestion(questionId: string) {
    return this.client.post(`/api/mentor/questions/${questionId}/resolve`)
  }

  // Classes
  async scheduleClass(data: {
    title: string; description: string; subject: string; topic: string
    class_type: string; scheduled_at: string; duration_minutes?: number
    target_student_id?: string; linked_question_ids?: string[]; max_students?: number
  }) {
    return this.client.post('/api/mentor/classes', data)
  }
  async listClasses() {
    return this.client.get('/api/mentor/classes')
  }
  async rsvpClass(classId: string) {
    return this.client.post(`/api/mentor/classes/${classId}/rsvp`)
  }
  async cancelClass(classId: string) {
    return this.client.delete(`/api/mentor/classes/${classId}`)
  }

  // Meeting requests
  async requestMeeting(message: string, preferredTimes: string[] = []) {
    return this.client.post('/api/mentor/meeting-requests', { message, preferred_times: preferredTimes })
  }
  async listMeetingRequests() {
    return this.client.get('/api/mentor/meeting-requests')
  }
  async respondMeetingRequest(requestId: string, data: {
    accepted: boolean; naga_note?: string; scheduled_at?: string; duration_minutes?: number
  }) {
    return this.client.post(`/api/mentor/meeting-requests/${requestId}/respond`, data)
  }

  // Notifications
  async getNotifications() {
    return this.client.get('/api/mentor/notifications')
  }
  async markNotificationRead(notificationId: string) {
    return this.client.post(`/api/mentor/notifications/${notificationId}/read`)
  }
  async markAllNotificationsRead() {
    return this.client.post('/api/mentor/notifications/read-all')
  }

  // NAGA dashboard
  async nagaDashboard() {
    return this.client.get('/api/mentor/dashboard')
  }

  // Dabbu approvals
  async dabbuAllPending() {
    return this.client.get('/api/dabbu/naga/all-pending')
  }
  async dabbuApprovePlan(studentId: string, nagaNote = '') {
    return this.client.post('/api/dabbu/naga/approve-plan', { student_id: studentId, naga_note: nagaNote })
  }
  async dabbuRejectPlan(studentId: string, reason = '') {
    return this.client.post('/api/dabbu/naga/reject-plan', { student_id: studentId, reason })
  }
  async dabbuApproveNote(exam: string, subject: string, topic: string, nagaNote = '') {
    return this.client.post('/api/dabbu/naga/notes/approve', { exam, subject, topic, naga_note: nagaNote })
  }
  async dabbuRejectNote(exam: string, subject: string, topic: string, reason = '') {
    return this.client.post('/api/dabbu/naga/notes/reject', { exam, subject, topic, naga_note: reason })
  }
  async dabbuApproveVideo(videoId: string) {
    return this.client.post('/api/dabbu/naga/videos/approve', { video_id: videoId })
  }
  async dabbuRejectVideo(videoId: string) {
    return this.client.post('/api/dabbu/naga/videos/reject', { video_id: videoId })
  }
  async dabbuBlacklist(videoId?: string, channel?: string) {
    return this.client.post('/api/dabbu/naga/videos/blacklist', { video_id: videoId, channel })
  }
  async getContentKeywords() {
    return this.client.get('/api/dabbu/naga/keywords')
  }
  async addContentKeyword(word: string, tier: 'blocked' | 'flagged') {
    return this.client.post('/api/dabbu/naga/keywords/add', { word, tier })
  }
  async removeContentKeyword(word: string, tier: 'blocked' | 'flagged') {
    return this.client.post('/api/dabbu/naga/keywords/remove', { word, tier })
  }

  // Progress tracking
  async getProgress() {
    return this.client.get('/api/progress')
  }
  async forceSnapshot(label = 'manual') {
    return this.client.post('/api/progress/snapshot', { label })
  }
  async logActivity() {
    return this.client.post('/api/progress/log-activity')
  }
  async completeBlock(blockId: string, subject: string, topic: string, sessionType = 'STUDY') {
    return this.client.post('/api/progress/block-complete', {
      block_id: blockId, subject, topic, session_type: sessionType,
    })
  }
  async triggerDabbuAnalysis() {
    return this.client.post('/api/progress/dabbu-analyze')
  }
  async getMyInterventions() {
    return this.client.get('/api/progress/interventions')
  }

  // NAGA intervention management
  async nagaListInterventions(status = 'pending') {
    return this.client.get(`/api/dabbu/naga/interventions?status=${status}`)
  }
  async nagaApproveIntervention(interventionId: string, nagaNote = '') {
    return this.client.post('/api/dabbu/naga/interventions/approve', {
      intervention_id: interventionId, naga_note: nagaNote,
    })
  }
  async nagaAmendIntervention(interventionId: string, nagaNote: string, amendedActions?: object[]) {
    return this.client.post('/api/dabbu/naga/interventions/amend', {
      intervention_id: interventionId, naga_note: nagaNote, amended_actions: amendedActions,
    })
  }
  async nagaDismissIntervention(interventionId: string, nagaNote = '') {
    return this.client.post('/api/dabbu/naga/interventions/dismiss', {
      intervention_id: interventionId, naga_note: nagaNote,
    })
  }

  // Mock test
  async getMockStatus(examKey: string) {
    return this.client.get(`/api/mock/status/${examKey}`)
  }
  async getMockPaper(examKey: string) {
    return this.client.get(`/api/mock/paper/${examKey}`)
  }
  async startMockSession(examKey: string) {
    return this.client.post('/api/mock/session/start', { exam_key: examKey })
  }
  async autosaveMock(sessionId: string, answers: number[], flagged: number[]) {
    return this.client.put(`/api/mock/session/${sessionId}`, { answers, flagged })
  }
  async submitMock(sessionId: string, answers: number[], flagged: number[], timedOut: boolean) {
    return this.client.post(`/api/mock/session/${sessionId}/submit`, {
      answers, flagged, timed_out: timedOut,
    })
  }
  async getMockSession(sessionId: string) {
    return this.client.get(`/api/mock/session/${sessionId}`)
  }
  async getMockHistory() {
    return this.client.get('/api/mock/history')
  }
  async triggerMockGeneration(examKey: string, scheduledDate?: string) {
    const params = scheduledDate ? `?scheduled_date=${scheduledDate}` : ''
    return this.client.post(`/api/mock/generate/${examKey}${params}`)
  }
}

export default new ApiService()
