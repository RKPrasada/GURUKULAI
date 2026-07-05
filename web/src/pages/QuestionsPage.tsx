import { useEffect, useState } from 'react'
import { useAuthStore } from '@/store/auth'
import api from '@/services/api'
import { ThumbsUp, CheckCircle, MessageSquare, Plus, Tag } from 'lucide-react'

const SUBJECTS = ['Mathematics', 'General Intelligence', 'General Awareness', 'Physics', 'Chemistry', 'Biology', 'English', 'History', 'Geography']

interface Question {
  question_id: string
  student_id: string
  student_name: string
  subject: string
  topic: string
  content: string
  status: string
  upvotes: number
  upvoted_by: string[]
  answer: string | null
  created_at: string
  class_id: string | null
}

export default function QuestionsPage() {
  const student = useAuthStore((s) => s.student)
  const [questions, setQuestions] = useState<Question[]>([])
  const [showForm, setShowForm] = useState(false)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [filterSubject, setFilterSubject] = useState('')
  const [form, setForm] = useState({ subject: '', topic: '', content: '' })
  const [successMsg, setSuccessMsg] = useState('')
  const [submitError, setSubmitError] = useState('')

  const isNaga = student?.user_id === 'naga'

  useEffect(() => { load() }, [])

  const load = async () => {
    try {
      const res = await api.listQuestions()
      setQuestions(res.data)
    } catch { }
    setLoading(false)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setSubmitError('')
    setSuccessMsg('')
    try {
      await api.postQuestion(form.subject, form.topic, form.content)
      setSuccessMsg('Your question has been submitted. NAGA will review it shortly.')
      setShowForm(false)
      setForm({ subject: '', topic: '', content: '' })
    } catch (err: any) {
      setSubmitError(err.response?.data?.detail || err.message || 'Submission failed.')
    }
    setSubmitting(false)
  }

  const handleUpvote = async (questionId: string) => {
    try {
      const res = await api.upvoteQuestion(questionId)
      setQuestions((prev) => prev.map((q) =>
        q.question_id === questionId
          ? { ...q, upvotes: res.data.upvotes, upvoted_by: res.data.upvoted ? [...q.upvoted_by, student!.user_id] : q.upvoted_by.filter((id) => id !== student!.user_id) }
          : q
      ))
    } catch { }
  }

  const handleResolve = async (questionId: string) => {
    try {
      await api.resolveQuestion(questionId)
      setQuestions((prev) => prev.map((q) => q.question_id === questionId ? { ...q, status: 'resolved' } : q))
    } catch { }
  }

  const filtered = filterSubject ? questions.filter((q) => q.subject === filterSubject) : questions

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">❓ Ask NAGA</h1>
          <p className="text-gray-600 dark:text-gray-400 text-sm">Post your doubts — NAGA will answer or schedule a class</p>
        </div>
        {!isNaga && (
          <button
            onClick={() => setShowForm(!showForm)}
            className="flex items-center gap-2 bg-primary hover:bg-primary/90 text-white font-semibold py-2 px-4 rounded-lg"
          >
            <Plus size={18} /> Ask a Question
          </button>
        )}
      </div>

      {successMsg && (
        <div className="p-4 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-200 rounded-lg">
          {successMsg}
        </div>
      )}
      {submitError && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 rounded-lg flex items-start gap-2">
          <span className="shrink-0">⚠️</span>
          <span>{submitError}</span>
        </div>
      )}

      {/* Question Form */}
      {showForm && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Post Your Question</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Subject *</label>
                <select
                  required
                  value={form.subject}
                  onChange={(e) => setForm({ ...form, subject: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                >
                  <option value="">Select subject</option>
                  {SUBJECTS.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Topic *</label>
                <input
                  required
                  placeholder="e.g. Quadratic Equations"
                  value={form.topic}
                  onChange={(e) => setForm({ ...form, topic: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Your Question *</label>
              <textarea
                required
                rows={4}
                placeholder="Describe your doubt in detail..."
                value={form.content}
                onChange={(e) => setForm({ ...form, content: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>
            <div className="flex gap-3">
              <button type="submit" disabled={submitting} className="bg-primary hover:bg-primary/90 disabled:bg-gray-400 text-white font-semibold py-2 px-6 rounded-lg">
                {submitting ? 'Submitting...' : 'Submit Question'}
              </button>
              <button type="button" onClick={() => setShowForm(false)} className="bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-200 font-semibold py-2 px-6 rounded-lg">
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Filter */}
      <div className="flex gap-2 flex-wrap">
        <button
          onClick={() => setFilterSubject('')}
          className={`px-3 py-1 rounded-full text-sm font-semibold ${!filterSubject ? 'bg-primary text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300'}`}
        >
          All
        </button>
        {SUBJECTS.map((s) => (
          <button
            key={s}
            onClick={() => setFilterSubject(s === filterSubject ? '' : s)}
            className={`px-3 py-1 rounded-full text-sm font-semibold ${filterSubject === s ? 'bg-primary text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300'}`}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Questions List */}
      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading questions...</div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-12 text-gray-500">No questions yet. Be the first to ask!</div>
      ) : (
        <div className="space-y-4">
          {filtered.map((q) => (
            <div key={q.question_id} className={`bg-white dark:bg-gray-800 rounded-lg shadow p-6 border-l-4 ${q.status === 'resolved' ? 'border-green-500' : 'border-primary'}`}>
              <div className="flex justify-between items-start mb-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full font-semibold flex items-center gap-1">
                      <Tag size={11} /> {q.subject}
                    </span>
                    <span className="text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 px-2 py-0.5 rounded-full">{q.topic}</span>
                    {q.status === 'resolved' && (
                      <span className="text-xs bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 px-2 py-0.5 rounded-full flex items-center gap-1">
                        <CheckCircle size={11} /> Resolved
                      </span>
                    )}
                  </div>
                  <p className="text-gray-900 dark:text-white font-medium">{q.content}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    Asked by <strong>{q.student_name}</strong> · {new Date(q.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                  </p>
                </div>
                <div className="flex flex-col items-center ml-4 gap-2">
                  <button
                    onClick={() => handleUpvote(q.question_id)}
                    className={`flex flex-col items-center p-2 rounded-lg transition ${q.upvoted_by.includes(student?.user_id || '') ? 'text-primary bg-primary/10' : 'text-gray-400 hover:text-primary hover:bg-primary/5'}`}
                  >
                    <ThumbsUp size={18} />
                    <span className="text-xs font-bold">{q.upvotes}</span>
                  </button>
                </div>
              </div>

              {/* NAGA's Answer */}
              {q.answer && (
                <div className="mt-4 p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-800">
                  <p className="text-xs font-bold text-purple-700 dark:text-purple-300 mb-1 flex items-center gap-1">
                    <MessageSquare size={13} /> NAGA's Answer
                  </p>
                  <p className="text-gray-800 dark:text-gray-200 text-sm">{q.answer}</p>
                </div>
              )}

              {/* Actions */}
              {q.status !== 'resolved' && (q.student_id === student?.user_id || isNaga) && q.answer && (
                <button
                  onClick={() => handleResolve(q.question_id)}
                  className="mt-3 text-sm text-green-600 hover:underline flex items-center gap-1"
                >
                  <CheckCircle size={14} /> Mark as Resolved
                </button>
              )}

              {q.class_id && (
                <div className="mt-3 text-xs text-blue-600 dark:text-blue-400">
                  📅 NAGA has scheduled a class for this topic
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
