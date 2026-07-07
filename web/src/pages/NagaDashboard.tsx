import { useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import api from '@/services/api'
import { MessageSquare, Calendar, Users, Clock, CheckCircle, X, Video, Plus, ShieldAlert, TrendingUp, AlertTriangle, Edit2 } from 'lucide-react'

interface DashboardStats {
  pending_questions: number
  total_questions: number
  upcoming_classes: number
  pending_meeting_requests: number
  unread_notifications: number
  total_students: number
}

interface Question {
  question_id: string
  student_name: string
  subject: string
  topic: string
  content: string
  status: string
  upvotes: number
  created_at: string
}

interface MeetingRequest {
  request_id: string
  student_name: string
  student_email: string
  message: string
  preferred_times: string[]
  status: string
  created_at: string
}

const SUBJECTS = ['Mathematics', 'General Intelligence', 'General Awareness', 'Physics', 'Chemistry', 'Biology', 'English', 'History', 'Geography']

export default function NagaDashboard() {
  const [tab, setTab] = useState<'overview' | 'questions' | 'meetings' | 'schedule' | 'student_schedules' | 'approvals'>('overview')
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [questions, setQuestions] = useState<Question[]>([])
  const [meetings, setMeetings] = useState<MeetingRequest[]>([])
  const [loading, setLoading] = useState(true)

  // Approvals tab state
  interface PendingPlan { type: 'study_plan'; student_id: string; plan_id: string; exam_target: string; duration_months: number; diagnostic_score: number; weak_topics_count: number; total_study_hours: number; created_at: string }
  interface PendingNote { type: 'note'; exam: string; subject: string; topic: string; status: string; created_at: string; preview: string }
  interface FlaggedVideo { type: 'video'; video_id: string; title: string; channel: string; url: string; topic: string; flag_reason: string; status: string }
  const [approvals, setApprovals] = useState<{ study_plans: PendingPlan[]; notes: PendingNote[]; videos: FlaggedVideo[]; totals: { total: number } } | null>(null)
  const [approvalsLoading, setApprovalsLoading] = useState(false)
  const [approvalsMsg, setApprovalsMsg] = useState('')
  const [planNotes, setPlanNotes] = useState<{ [id: string]: string }>({})
  const [noteRejectReasons, setNoteRejectReasons] = useState<{ [key: string]: string }>({})
  const [kbStats, setKbStats] = useState<{ total: number; by_exam: Record<string, number> } | null>(null)
  const [expandedNote, setExpandedNote] = useState<string | null>(null)
  const [keywords, setKeywords] = useState<{ blocked: string[]; flagged: string[] } | null>(null)
  const [newKw, setNewKw] = useState('')
  const [newKwTier, setNewKwTier] = useState<'blocked' | 'flagged'>('blocked')
  const [kwMsg, setKwMsg] = useState('')

  // Intervention state
  interface InterventionAction { type: string; priority: string; subject?: string; topic?: string; description: string }
  interface Intervention {
    intervention_id: string; student_id: string; exam_target: string; proposed_at: string
    status: string; severity: string; summary: string; actions: InterventionAction[]; naga_note: string
    analysis_snapshot: { avg_score: number; stagnant_count: number; declining_count: number; critical_stuck_count: number; overdue_reviews: number; plan_completion_pct: number }
  }
  const [interventions, setInterventions] = useState<Intervention[]>([])
  const [interventionNotes, setInterventionNotes] = useState<Record<string, string>>({})
  const [expandedIntervention, setExpandedIntervention] = useState<string | null>(null)
  const [interventionMsg, setInterventionMsg] = useState('')

  const loadInterventions = async () => {
    try {
      const res = await api.nagaListInterventions('pending')
      setInterventions(res.data.interventions ?? [])
    } catch { /* non-critical */ }
  }

  const loadKeywords = async () => {
    try {
      const res = await api.getContentKeywords()
      setKeywords(res.data)
    } catch { /* non-critical */ }
  }

  const loadApprovals = async () => {
    setApprovalsLoading(true)
    try {
      const res = await api.dabbuAllPending()
      setApprovals(res.data)
    } catch { setApprovalsMsg('Failed to load pending approvals.') }
    setApprovalsLoading(false)
  }

  const loadKbStats = async () => {
    try {
      const res = await api.get('/api/dabbu/knowledge-base/stats')
      setKbStats(res.data)
    } catch { /* non-critical */ }
  }

  // Schedule class form
  const [classForm, setClassForm] = useState({
    title: '', description: '', subject: '', topic: '',
    class_type: 'group', scheduled_at: '', duration_minutes: 60,
    target_student_id: '', linked_question_ids: [] as string[], max_students: 50,
  })
  const [scheduling, setScheduling] = useState(false)
  const [scheduleMsg, setScheduleMsg] = useState('')

  // Answer form
  const [answerData, setAnswerData] = useState<{ [id: string]: string }>({})

  // Meeting response
  const [meetResponse, setMeetResponse] = useState<{ [id: string]: { scheduled_at: string; note: string } }>({})

  // Student Schedule view
  const [studentIdInput, setStudentIdInput] = useState('')
  const [studentSchedule, setStudentSchedule] = useState<any>(null)
  const [scheduleLoading, setScheduleLoading] = useState(false)
  const [scheduleError, setScheduleError] = useState('')

  useEffect(() => {
    loadAll()
    if (tab === 'approvals') { loadApprovals(); loadKeywords(); loadInterventions(); loadKbStats() }
  }, [tab])

  const loadAll = async () => {
    setLoading(true)
    try {
      if (tab === 'overview') {
        const res = await api.nagaDashboard()
        setStats(res.data)
      } else if (tab === 'questions') {
        const res = await api.pendingQuestions()
        setQuestions(res.data)
      } else if (tab === 'meetings') {
        const res = await api.listMeetingRequests()
        setMeetings(res.data.filter((m: MeetingRequest) => m.status === 'pending'))
      }
    } catch { }
    setLoading(false)
  }

  const handleApprove = async (questionId: string, approved: boolean) => {
    await api.approveQuestion(questionId, approved)
    setQuestions((prev) => prev.filter((q) => q.question_id !== questionId))
  }

  const handleAnswer = async (questionId: string) => {
    const answer = answerData[questionId]
    if (!answer?.trim()) return
    await api.answerQuestion(questionId, answer)
    setQuestions((prev) => prev.filter((q) => q.question_id !== questionId))
  }

  const handleMeetingResponse = async (requestId: string, accepted: boolean) => {
    const data = meetResponse[requestId] || {}
    await api.respondMeetingRequest(requestId, {
      accepted,
      naga_note: data.note || '',
      scheduled_at: accepted ? data.scheduled_at : undefined,
      duration_minutes: 30,
    })
    setMeetings((prev) => prev.filter((m) => m.request_id !== requestId))
  }

  const handleScheduleClass = async (e: React.FormEvent) => {
    e.preventDefault()
    setScheduling(true)
    setScheduleMsg('')
    try {
      const res = await api.scheduleClass({
        ...classForm,
        linked_question_ids: classForm.linked_question_ids,
      })
      setScheduleMsg(`✅ Class scheduled! Meet link: ${res.data.meet_link}`)
      setClassForm({ title: '', description: '', subject: '', topic: '', class_type: 'group', scheduled_at: '', duration_minutes: 60, target_student_id: '', linked_question_ids: [], max_students: 50 })
    } catch (err: any) {
      setScheduleMsg(`❌ Error: ${err.response?.data?.detail || err.message}`)
    }
    setScheduling(false)
  }

  const tabs = [
    { id: 'overview', label: '📊 Overview' },
    { id: 'questions', label: `❓ Pending Questions${stats ? ` (${stats.pending_questions})` : ''}` },
    { id: 'meetings', label: `📞 Meeting Requests${stats ? ` (${stats.pending_meeting_requests})` : ''}` },
    { id: 'approvals', label: `✅ Dabbu Approvals${approvals ? ` (${approvals.totals.total + interventions.length})` : ''}` },
    { id: 'schedule', label: '📅 Schedule Class' },
    { id: 'student_schedules', label: '🗓️ Student Schedules' },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">👨‍🏫 NAGA Mentor Dashboard</h1>
        <p className="text-gray-500 dark:text-gray-400 text-sm">Manage questions, schedule classes, handle meeting requests</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 flex-wrap bg-gray-100 dark:bg-gray-700 p-1 rounded-lg">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id as any)}
            className={`flex-1 py-2 px-3 rounded-md text-sm font-semibold transition ${
              tab === t.id ? 'bg-white dark:bg-gray-800 text-primary shadow' : 'text-gray-600 dark:text-gray-300'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {loading && <div className="text-center py-8 text-gray-500">Loading...</div>}

      {/* Overview */}
      {tab === 'overview' && stats && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          {[
            { label: 'Pending Questions', value: stats.pending_questions, icon: MessageSquare, color: 'text-orange-500' },
            { label: 'Upcoming Classes', value: stats.upcoming_classes, icon: Calendar, color: 'text-blue-500' },
            { label: 'Meeting Requests', value: stats.pending_meeting_requests, icon: Clock, color: 'text-purple-500' },
            { label: 'Total Students', value: stats.total_students, icon: Users, color: 'text-green-500' },
            { label: 'Total Questions', value: stats.total_questions, icon: MessageSquare, color: 'text-gray-500' },
            { label: 'Unread Notifications', value: stats.unread_notifications, icon: MessageSquare, color: 'text-red-500' },
          ].map((s) => (
            <div key={s.label} className="bg-white dark:bg-gray-800 rounded-lg shadow p-5">
              <s.icon size={24} className={`${s.color} mb-2`} />
              <p className="text-3xl font-bold text-gray-900 dark:text-white">{s.value}</p>
              <p className="text-sm text-gray-500">{s.label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Pending Questions */}
      {tab === 'questions' && !loading && (
        <div className="space-y-4">
          {questions.length === 0 ? (
            <div className="text-center py-12 text-gray-500 bg-white dark:bg-gray-800 rounded-lg shadow">
              No pending questions
            </div>
          ) : questions.map((q) => (
            <div key={q.question_id} className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <div className="flex justify-between items-start mb-3">
                <div>
                  <div className="flex gap-2 mb-1">
                    <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full">{q.subject}</span>
                    <span className="text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 px-2 py-0.5 rounded-full">{q.topic}</span>
                    <span className="text-xs text-orange-600 font-semibold">👍 {q.upvotes}</span>
                  </div>
                  <p className="text-gray-900 dark:text-white font-medium">{q.content}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    By <strong>{q.student_name}</strong> · {new Date(q.created_at).toLocaleDateString('en-IN')}
                  </p>
                </div>
              </div>

              {/* Approve / Reject */}
              <div className="flex gap-2 mb-4">
                <button onClick={() => handleApprove(q.question_id, true)} className="flex items-center gap-1 text-sm bg-green-500 hover:bg-green-600 text-white py-1.5 px-3 rounded-lg">
                  <CheckCircle size={14} /> Approve & Publish
                </button>
                <button onClick={() => handleApprove(q.question_id, false)} className="flex items-center gap-1 text-sm bg-red-100 hover:bg-red-200 text-red-600 py-1.5 px-3 rounded-lg">
                  <X size={14} /> Reject
                </button>
              </div>

              {/* Answer inline */}
              <div className="space-y-2">
                <textarea
                  rows={2}
                  placeholder="Type your answer here (optional — approve first, then answer)..."
                  value={answerData[q.question_id] || ''}
                  onChange={(e) => setAnswerData({ ...answerData, [q.question_id]: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
                />
                <button
                  onClick={() => handleAnswer(q.question_id)}
                  disabled={!answerData[q.question_id]?.trim()}
                  className="text-sm bg-primary hover:bg-primary/90 disabled:bg-gray-300 text-white py-1.5 px-4 rounded-lg"
                >
                  Approve & Answer
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Meeting Requests */}
      {tab === 'meetings' && !loading && (
        <div className="space-y-4">
          {meetings.length === 0 ? (
            <div className="text-center py-12 text-gray-500 bg-white dark:bg-gray-800 rounded-lg shadow">
              No pending meeting requests
            </div>
          ) : meetings.map((mr) => (
            <div key={mr.request_id} className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <div className="mb-4">
                <h3 className="font-bold text-gray-900 dark:text-white">{mr.student_name}</h3>
                <p className="text-xs text-gray-500">{mr.student_email}</p>
                <p className="text-gray-700 dark:text-gray-300 mt-2">{mr.message}</p>
                {mr.preferred_times.length > 0 && (
                  <div className="mt-2">
                    <p className="text-xs font-semibold text-gray-600 dark:text-gray-400">Preferred times:</p>
                    <ul className="text-xs text-gray-600 dark:text-gray-400 mt-1 space-y-0.5">
                      {mr.preferred_times.map((t, i) => (
                        <li key={i}>• {new Date(t).toLocaleString('en-IN', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Schedule At *</label>
                    <input
                      type="datetime-local"
                      value={meetResponse[mr.request_id]?.scheduled_at || ''}
                      onChange={(e) => setMeetResponse({ ...meetResponse, [mr.request_id]: { ...meetResponse[mr.request_id], scheduled_at: e.target.value } })}
                      className="w-full px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Note to student</label>
                    <input
                      type="text"
                      placeholder="Optional message..."
                      value={meetResponse[mr.request_id]?.note || ''}
                      onChange={(e) => setMeetResponse({ ...meetResponse, [mr.request_id]: { ...meetResponse[mr.request_id], note: e.target.value } })}
                      className="w-full px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
                    />
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleMeetingResponse(mr.request_id, true)}
                    className="flex items-center gap-1 text-sm bg-green-500 hover:bg-green-600 text-white py-1.5 px-4 rounded-lg"
                  >
                    <Video size={14} /> Accept & Create Meet
                  </button>
                  <button
                    onClick={() => handleMeetingResponse(mr.request_id, false)}
                    className="flex items-center gap-1 text-sm bg-red-100 hover:bg-red-200 text-red-600 py-1.5 px-4 rounded-lg"
                  >
                    <X size={14} /> Decline
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Schedule Class */}
      {tab === 'schedule' && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <Plus size={20} /> Schedule a New Class
          </h2>
          {scheduleMsg && (
            <div className={`mb-4 p-3 rounded-lg text-sm ${scheduleMsg.startsWith('✅') ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300' : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300'}`}>
              {scheduleMsg}
            </div>
          )}
          <form onSubmit={handleScheduleClass} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Class Title *</label>
                <input required value={classForm.title} onChange={(e) => setClassForm({ ...classForm, title: e.target.value })}
                  placeholder="e.g. Mastering Quadratic Equations" className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Subject *</label>
                <select required value={classForm.subject} onChange={(e) => setClassForm({ ...classForm, subject: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white">
                  <option value="">Select subject</option>
                  {SUBJECTS.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Topic *</label>
                <input required value={classForm.topic} onChange={(e) => setClassForm({ ...classForm, topic: e.target.value })}
                  placeholder="e.g. Discriminant & Nature of Roots" className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Class Type *</label>
                <select value={classForm.class_type} onChange={(e) => setClassForm({ ...classForm, class_type: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white">
                  <option value="group">👥 Group Class (all students)</option>
                  <option value="one_to_one">👤 1-to-1 (specific student)</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Date & Time *</label>
                <input required type="datetime-local" value={classForm.scheduled_at}
                  onChange={(e) => setClassForm({ ...classForm, scheduled_at: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Duration (minutes)</label>
                <input type="number" value={classForm.duration_minutes} min={15} max={180}
                  onChange={(e) => setClassForm({ ...classForm, duration_minutes: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white" />
              </div>
              <div className="col-span-2">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Description</label>
                <textarea rows={3} value={classForm.description} onChange={(e) => setClassForm({ ...classForm, description: e.target.value })}
                  placeholder="What will be covered in this class?" className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white" />
              </div>
            </div>
            <button type="submit" disabled={scheduling}
              className="flex items-center gap-2 bg-primary hover:bg-primary/90 disabled:bg-gray-400 text-white font-semibold py-2 px-6 rounded-lg transition">
              <Video size={18} /> {scheduling ? 'Scheduling...' : 'Schedule & Generate Meet Link'}
            </button>
          </form>
        </div>
      )}
      {/* Dabbu Approvals */}
      {tab === 'approvals' && (
        <div className="space-y-6">
          {approvalsMsg && <p className="text-red-500 text-sm">{approvalsMsg}</p>}
          {approvalsLoading && <p className="text-gray-500 text-sm">Loading pending items…</p>}

          {/* Study Plans */}
          <section>
            <h2 className="text-base font-bold text-gray-800 dark:text-white mb-3 flex items-center gap-2">
              📋 Study Plans <span className="bg-violet-100 text-violet-700 text-xs font-semibold px-2 py-0.5 rounded-full">{approvals?.study_plans.length ?? 0}</span>
            </h2>
            {(approvals?.study_plans.length ?? 0) === 0
              ? <p className="text-sm text-gray-400">No study plans pending.</p>
              : approvals!.study_plans.map((plan) => (
                <div key={plan.plan_id} className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-4 mb-3">
                  <div className="flex flex-wrap gap-3 text-sm mb-3">
                    <span className="font-semibold text-gray-900 dark:text-white">Student: {plan.student_id.slice(0, 12)}…</span>
                    <span className="text-gray-500">Exam: {plan.exam_target}</span>
                    <span className="text-gray-500">Duration: {plan.duration_months} months</span>
                    <span className="text-gray-500">Score: {(plan.diagnostic_score * 100).toFixed(0)}%</span>
                    <span className="text-gray-500">Weak topics: {plan.weak_topics_count}</span>
                    <span className="text-gray-500">Hours: {plan.total_study_hours?.toFixed(0)}</span>
                  </div>
                  <input
                    type="text"
                    placeholder="Optional note to student…"
                    value={planNotes[plan.plan_id] ?? ''}
                    onChange={(e) => setPlanNotes((p) => ({ ...p, [plan.plan_id]: e.target.value }))}
                    className="w-full mb-3 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-1.5 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                  <div className="flex gap-2">
                    <button onClick={async () => {
                      await api.dabbuApprovePlan(plan.student_id, planNotes[plan.plan_id] ?? '')
                      setApprovalsMsg('Plan approved ✓')
                      loadApprovals()
                    }} className="bg-green-600 hover:bg-green-700 text-white text-sm font-semibold px-4 py-1.5 rounded-lg transition">Approve</button>
                    <button onClick={async () => {
                      await api.dabbuRejectPlan(plan.student_id, planNotes[plan.plan_id] ?? '')
                      setApprovalsMsg('Plan rejected.')
                      loadApprovals()
                    }} className="bg-red-100 hover:bg-red-200 text-red-700 text-sm font-semibold px-4 py-1.5 rounded-lg transition">Reject</button>
                  </div>
                </div>
              ))
            }
          </section>

          {/* Knowledge Base Stats */}
          {kbStats !== null && (
            <div className="bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-700 rounded-xl p-4 mb-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-emerald-700 dark:text-emerald-400 font-bold text-sm">🧠 Knowledge Base</span>
                <span className="bg-emerald-100 dark:bg-emerald-800 text-emerald-700 dark:text-emerald-300 text-xs font-semibold px-2 py-0.5 rounded-full">{kbStats.total} notes</span>
              </div>
              {kbStats.total === 0
                ? <p className="text-xs text-emerald-600 dark:text-emerald-400">No approved notes in vector store yet. Approve notes below to populate it.</p>
                : <div className="flex flex-wrap gap-2">
                    {Object.entries(kbStats.by_exam).map(([exam, count]) => (
                      <span key={exam} className="text-xs bg-white dark:bg-gray-800 border border-emerald-200 dark:border-emerald-700 rounded-lg px-2 py-0.5 text-gray-700 dark:text-gray-300">
                        {exam.toUpperCase().replace(/_/g, ' ')}: <strong>{count}</strong>
                      </span>
                    ))}
                  </div>
              }
            </div>
          )}

          {/* Notes */}
          <section>
            <h2 className="text-base font-bold text-gray-800 dark:text-white mb-3 flex items-center gap-2">
              📝 Study Notes <span className="bg-blue-100 text-blue-700 text-xs font-semibold px-2 py-0.5 rounded-full">{approvals?.notes.length ?? 0}</span>
            </h2>
            {(approvals?.notes.length ?? 0) === 0
              ? <p className="text-sm text-gray-400">No notes pending.</p>
              : approvals!.notes.map((note) => {
                const key = `${note.exam}|${note.subject}|${note.topic}`
                const isExpanded = expandedNote === key
                const isSystemGenerated = !note.requested_by || note.requested_by === 'Testing / System'
                return (
                  <div key={key} className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-4 mb-3">

                    {/* Header row: topic + exam + requester */}
                    <div className="flex flex-wrap items-center gap-2 mb-2">
                      <span className="font-semibold text-gray-900 dark:text-white">{note.topic}</span>
                      <span className="text-xs text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded-full">
                        {note.subject} · {note.exam.toUpperCase().replace(/_/g, ' ')}
                      </span>
                      {/* Requester badge */}
                      {isSystemGenerated
                        ? <span className="text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 px-2 py-0.5 rounded-full">
                            🤖 Testing / System
                          </span>
                        : <span className="text-xs font-medium bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 px-2 py-0.5 rounded-full">
                            👤 Requested by: {note.requested_by}
                          </span>
                      }
                      {note.generated_at && (
                        <span className="text-xs text-gray-400 ml-auto">
                          {new Date(note.generated_at).toLocaleString()}
                        </span>
                      )}
                    </div>

                    {/* Full notes content — rendered as Markdown */}
                    {note.content
                      ? <>
                          <div className={`relative bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg px-4 py-3 mb-2 overflow-y-auto transition-all ${isExpanded ? 'max-h-[36rem]' : 'max-h-40 overflow-hidden'}`}>
                            <div className="prose prose-sm dark:prose-invert max-w-none
                              prose-headings:font-bold prose-headings:text-gray-900 dark:prose-headings:text-white
                              prose-h2:text-base prose-h3:text-sm
                              prose-p:text-gray-700 dark:prose-p:text-gray-300 prose-p:text-sm prose-p:my-1
                              prose-li:text-gray-700 dark:prose-li:text-gray-300 prose-li:text-sm
                              prose-code:bg-amber-50 dark:prose-code:bg-amber-900/30 prose-code:text-amber-800 dark:prose-code:text-amber-200 prose-code:px-1 prose-code:rounded prose-code:text-xs prose-code:font-mono
                              prose-strong:text-gray-900 dark:prose-strong:text-white
                              prose-blockquote:border-blue-400 prose-blockquote:bg-blue-50 dark:prose-blockquote:bg-blue-900/20 prose-blockquote:text-sm prose-blockquote:rounded prose-blockquote:px-3
                              prose-table:text-xs prose-th:bg-gray-100 dark:prose-th:bg-gray-700">
                              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {note.content}
                              </ReactMarkdown>
                            </div>
                            {!isExpanded && (
                              <div className="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-white dark:from-gray-900 to-transparent rounded-b-lg" />
                            )}
                          </div>
                          <button
                            onClick={() => setExpandedNote(isExpanded ? null : key)}
                            className="text-xs text-blue-600 dark:text-blue-400 hover:underline mb-3 block"
                          >
                            {isExpanded ? '▲ Collapse notes' : '▼ Expand full notes'}
                          </button>
                        </>
                      : <p className="text-xs text-gray-400 mb-3 italic">No content available.</p>
                    }

                    <input
                      type="text"
                      placeholder="Optional feedback / rejection reason…"
                      value={noteRejectReasons[key] ?? ''}
                      onChange={(e) => setNoteRejectReasons((p) => ({ ...p, [key]: e.target.value }))}
                      className="w-full mb-3 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-1.5 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    />
                    <div className="flex gap-2 flex-wrap items-center">
                      <button onClick={async () => {
                        await api.dabbuApproveNote(note.exam, note.subject, note.topic, noteRejectReasons[key] ?? '')
                        setApprovalsMsg(`Notes for '${note.topic}' approved ✓ — published to Knowledge Base`)
                        loadApprovals()
                        loadKbStats()
                      }} className="bg-green-600 hover:bg-green-700 text-white text-sm font-semibold px-4 py-1.5 rounded-lg transition">Approve &amp; Publish to KB</button>
                      {kbStats?.by_exam[note.exam] !== undefined && (
                        <span className="text-xs text-emerald-700 dark:text-emerald-400 font-semibold flex items-center gap-1">
                          <CheckCircle size={13} /> In Knowledge Base
                        </span>
                      )}
                      <button onClick={async () => {
                        await api.dabbuRejectNote(note.exam, note.subject, note.topic, noteRejectReasons[key] ?? '')
                        setApprovalsMsg(`Notes for '${note.topic}' rejected — regenerating improved version in background…`)
                        loadApprovals()
                      }} className="bg-red-100 hover:bg-red-200 text-red-700 text-sm font-semibold px-4 py-1.5 rounded-lg transition">Reject &amp; Regenerate</button>
                    </div>
                  </div>
                )
              })
            }
          </section>

          {/* YouTube Videos */}
          <section>
            <h2 className="text-base font-bold text-gray-800 dark:text-white mb-3 flex items-center gap-2">
              <Video size={16} /> Flagged Videos <span className="bg-amber-100 text-amber-700 text-xs font-semibold px-2 py-0.5 rounded-full">{approvals?.videos.length ?? 0}</span>
            </h2>
            {(approvals?.videos.length ?? 0) === 0
              ? <p className="text-sm text-gray-400">No videos pending review.</p>
              : approvals!.videos.map((vid) => (
                <div key={vid.video_id} className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-4 mb-3">
                  <div className="flex flex-wrap gap-2 text-sm mb-1">
                    <span className="font-semibold text-gray-900 dark:text-white truncate max-w-xs">{vid.title}</span>
                    <span className="text-gray-400">·</span>
                    <span className="text-gray-500">{vid.channel}</span>
                  </div>
                  <p className="text-xs text-amber-600 dark:text-amber-400 mb-1">Flag reason: {vid.flag_reason}</p>
                  <p className="text-xs text-gray-400 mb-3">Topic: {vid.topic}</p>
                  <div className="flex flex-wrap gap-2">
                    <a href={vid.url} target="_blank" rel="noopener noreferrer"
                      className="text-xs text-primary underline">Watch ↗</a>
                    <button onClick={async () => {
                      await api.dabbuApproveVideo(vid.video_id)
                      setApprovalsMsg('Video approved ✓')
                      loadApprovals()
                    }} className="bg-green-600 hover:bg-green-700 text-white text-xs font-semibold px-3 py-1 rounded-lg transition">Approve</button>
                    <button onClick={async () => {
                      await api.dabbuRejectVideo(vid.video_id)
                      setApprovalsMsg('Video blocked.')
                      loadApprovals()
                    }} className="bg-red-100 hover:bg-red-200 text-red-700 text-xs font-semibold px-3 py-1 rounded-lg transition">Block</button>
                    <button onClick={async () => {
                      await api.dabbuBlacklist(vid.video_id, vid.channel)
                      setApprovalsMsg(`Channel '${vid.channel}' permanently blacklisted.`)
                      loadApprovals()
                    }} className="bg-gray-200 hover:bg-gray-300 text-gray-700 text-xs font-semibold px-3 py-1 rounded-lg transition">Blacklist Channel</button>
                  </div>
                </div>
              ))
            }
          </section>

          {/* Progress Interventions */}
          <section>
            <h2 className="text-base font-bold text-gray-800 dark:text-white mb-3 flex items-center gap-2">
              <TrendingUp size={16} /> Progress Interventions
              {interventions.length > 0 && (
                <span className="bg-red-100 text-red-700 text-xs font-semibold px-2 py-0.5 rounded-full">{interventions.length}</span>
              )}
            </h2>
            {interventionMsg && <p className="text-xs text-green-600 dark:text-green-400 mb-3">{interventionMsg}</p>}
            {interventions.length === 0
              ? <p className="text-sm text-gray-400">No pending interventions — students are on track.</p>
              : interventions.map((iv) => {
                const isOpen = expandedIntervention === iv.intervention_id
                const sevColor = iv.severity === 'high'
                  ? 'border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-700'
                  : iv.severity === 'medium'
                    ? 'border-amber-300 bg-amber-50 dark:bg-amber-900/20 dark:border-amber-700'
                    : 'border-gray-200 bg-white dark:bg-gray-800 dark:border-gray-700'
                return (
                  <div key={iv.intervention_id} className={`border rounded-xl mb-3 overflow-hidden ${sevColor}`}>
                    <button
                      className="w-full flex items-start justify-between p-4 text-left"
                      onClick={() => setExpandedIntervention(isOpen ? null : iv.intervention_id)}
                    >
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <AlertTriangle size={14} className={iv.severity === 'high' ? 'text-red-500' : 'text-amber-500'} />
                          <span className={`text-xs font-bold uppercase px-2 py-0.5 rounded-full ${
                            iv.severity === 'high' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'
                          }`}>{iv.severity}</span>
                          <span className="text-xs text-gray-400">{iv.exam_target.toUpperCase()}</span>
                          <span className="text-xs text-gray-400">· {iv.proposed_at.slice(0, 10)}</span>
                        </div>
                        <p className="text-sm font-semibold text-gray-900 dark:text-white">{iv.summary}</p>
                        <div className="flex gap-4 mt-1 text-xs text-gray-500">
                          <span>Avg: {(iv.analysis_snapshot.avg_score * 100).toFixed(0)}%</span>
                          <span>Stagnant: {iv.analysis_snapshot.stagnant_count}</span>
                          <span>Declining: {iv.analysis_snapshot.declining_count}</span>
                          <span>Plan: {iv.analysis_snapshot.plan_completion_pct.toFixed(0)}%</span>
                        </div>
                      </div>
                      <span className="text-xs text-primary ml-2 mt-1 flex-shrink-0">{isOpen ? '▲' : '▼'}</span>
                    </button>
                    {isOpen && (
                      <div className="border-t border-gray-200 dark:border-gray-700 p-4 space-y-3">
                        <div className="space-y-2">
                          {iv.actions.map((action, ai) => (
                            <div key={ai} className={`flex gap-2 text-xs p-2 rounded-lg ${
                              action.priority === 'high'
                                ? 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200'
                                : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
                            }`}>
                              <span className="font-bold flex-shrink-0">{ai + 1}.</span>
                              <span>{action.description}</span>
                            </div>
                          ))}
                        </div>
                        <textarea
                          placeholder="NAGA's note / amendment (optional)…"
                          rows={2}
                          value={interventionNotes[iv.intervention_id] ?? ''}
                          onChange={(e) => setInterventionNotes(n => ({ ...n, [iv.intervention_id]: e.target.value }))}
                          className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white resize-none"
                        />
                        <div className="flex flex-wrap gap-2">
                          <button onClick={async () => {
                            await api.nagaApproveIntervention(iv.intervention_id, interventionNotes[iv.intervention_id] ?? '')
                            setInterventionMsg('Intervention approved — student notified ✓')
                            loadInterventions()
                          }} className="bg-green-600 hover:bg-green-700 text-white text-xs font-semibold px-4 py-1.5 rounded-lg transition">
                            ✓ Approve as-is
                          </button>
                          <button onClick={async () => {
                            await api.nagaAmendIntervention(iv.intervention_id, interventionNotes[iv.intervention_id] ?? '')
                            setInterventionMsg('Intervention amended and approved — student notified ✓')
                            loadInterventions()
                          }} className="bg-primary hover:bg-primary/90 text-white text-xs font-semibold px-4 py-1.5 rounded-lg transition flex items-center gap-1">
                            <Edit2 size={11} /> Amend & Approve
                          </button>
                          <button onClick={async () => {
                            await api.nagaDismissIntervention(iv.intervention_id, interventionNotes[iv.intervention_id] ?? '')
                            setInterventionMsg('Intervention dismissed.')
                            loadInterventions()
                          }} className="bg-gray-200 hover:bg-gray-300 text-gray-700 text-xs font-semibold px-4 py-1.5 rounded-lg transition">
                            Dismiss
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )
              })
            }
          </section>

          {/* Keyword Blocklist Manager */}
          <section>
            <h2 className="text-base font-bold text-gray-800 dark:text-white mb-3 flex items-center gap-2">
              <ShieldAlert size={16} /> Content Keyword Blocklist
            </h2>
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
              <strong>Blocked</strong> keywords drop videos silently. <strong>Flagged</strong> keywords send videos to this review queue.
              Changes take effect immediately — no restart needed.
            </p>

            {/* Add keyword form */}
            <div className="flex gap-2 mb-4">
              <input
                value={newKw}
                onChange={e => setNewKw(e.target.value)}
                placeholder="Enter keyword..."
                className="flex-1 text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-1.5 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
              <select
                value={newKwTier}
                onChange={e => setNewKwTier(e.target.value as 'blocked' | 'flagged')}
                className="text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-2 py-1.5 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option value="blocked">Blocked</option>
                <option value="flagged">Flagged</option>
              </select>
              <button
                onClick={async () => {
                  if (!newKw.trim()) return
                  const res = await api.addContentKeyword(newKw.trim(), newKwTier)
                  setKwMsg(res.data.status === 'already_present' ? `'${newKw}' already in ${newKwTier} list.` : `Added '${newKw}' to ${newKwTier} list.`)
                  setNewKw('')
                  loadKeywords()
                }}
                className="bg-primary hover:bg-primary/90 text-white text-sm font-semibold px-3 py-1.5 rounded-lg transition flex items-center gap-1"
              >
                <Plus size={14} /> Add
              </button>
            </div>
            {kwMsg && <p className="text-xs text-green-600 dark:text-green-400 mb-3">{kwMsg}</p>}

            {keywords && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {(['blocked', 'flagged'] as const).map(tier => (
                  <div key={tier} className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-3">
                    <p className={`text-xs font-bold uppercase tracking-wide mb-2 ${tier === 'blocked' ? 'text-red-600' : 'text-amber-600'}`}>
                      {tier} ({keywords[tier].length})
                    </p>
                    <div className="flex flex-wrap gap-1.5 max-h-40 overflow-y-auto">
                      {keywords[tier].map(kw => (
                        <span key={kw} className={`flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium ${
                          tier === 'blocked'
                            ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
                            : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'
                        }`}>
                          {kw}
                          <button
                            onClick={async () => {
                              await api.removeContentKeyword(kw, tier)
                              setKwMsg(`Removed '${kw}' from ${tier} list.`)
                              loadKeywords()
                            }}
                            className="hover:opacity-70 ml-0.5 leading-none"
                            aria-label={`Remove ${kw}`}
                          >×</button>
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          <button onClick={() => { loadApprovals(); loadKeywords(); loadInterventions() }} className="text-sm text-primary font-medium hover:underline">↺ Refresh</button>
        </div>
      )}

      {/* Student Schedules */}
      {tab === 'student_schedules' && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-4">View Student Schedule</h2>
          <form
            onSubmit={async (e) => {
              e.preventDefault()
              if (!studentIdInput.trim()) return
              setScheduleLoading(true)
              setScheduleError('')
              setStudentSchedule(null)
              try {
                const res = await api.getStudyPlan(studentIdInput.trim())
                setStudentSchedule(res.data)
              } catch (err: any) {
                setScheduleError('Failed to fetch schedule. Ensure the student ID is correct or that they have generated a schedule.')
              }
              setScheduleLoading(false)
            }}
            className="flex gap-4 mb-6"
          >
            <input
              type="text"
              placeholder="Enter Student ID (e.g. stu_1234)"
              value={studentIdInput}
              onChange={(e) => setStudentIdInput(e.target.value)}
              className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
            <button
              type="submit"
              disabled={scheduleLoading || !studentIdInput.trim()}
              className="bg-primary hover:bg-primary/90 disabled:opacity-50 text-white font-semibold py-2 px-6 rounded-lg transition"
            >
              {scheduleLoading ? 'Loading...' : 'Fetch Schedule'}
            </button>
          </form>

          {scheduleError && <div className="text-red-500 mb-4">{scheduleError}</div>}

          {studentSchedule && (
            <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
              <div className="bg-primary/10 px-4 py-3 border-b border-primary/20">
                <h3 className="font-bold text-primary dark:text-primary-light flex items-center gap-2">
                  <Calendar size={18} />
                  {studentSchedule.plan_type === 'adaptive' ? 'Adaptive Study Plan' : 'Study Schedule'}
                </h3>
                <div className="flex gap-4 mt-1 text-xs text-gray-600 dark:text-gray-400">
                  <span>Total Hours: {studentSchedule.total_hours || 0}</span>
                  <span>Target: {studentSchedule.exam_target || 'General'}</span>
                </div>
              </div>
              <div className="divide-y divide-gray-100 dark:divide-gray-700">
                {(studentSchedule.plan || studentSchedule.schedule || []).map((day: any, i: number) => (
                  <details key={i} className="group p-4 bg-gray-50 dark:bg-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-800 cursor-pointer">
                    <summary className="font-medium text-sm text-gray-900 dark:text-white flex justify-between items-center outline-none">
                      <span>{day.day ? `Day ${day.day}` : day.month || day.week || `Phase ${i+1}`} {day.date ? `— ${day.date}` : ''}</span>
                      <span className="text-gray-400 group-open:rotate-180 transition-transform">▼</span>
                    </summary>
                    <div className="mt-3 space-y-2 pl-2">
                      {(day.sessions || day.topics || []).map((s: any, j: number) => (
                        <div key={j} className="flex gap-3 text-sm">
                          <span className="text-gray-500 w-16 shrink-0">{s.time || s.duration_minutes ? `${s.duration_minutes}m` : '•'}</span>
                          <span className="text-gray-800 dark:text-gray-200 font-medium">{s.topic || s.name || s}</span>
                        </div>
                      ))}
                    </div>
                  </details>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
