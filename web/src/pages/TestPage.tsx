import { useState, useRef, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'
import api from '@/services/api'
import {
  ChevronRight, ChevronLeft, CheckCircle, XCircle, Zap,
  Loader2, MessageCircle, Send, ShieldAlert, BookOpen, BarChart2,
} from 'lucide-react'

// ── Types ────────────────────────────────────────────────────────────────────

interface SyllabusTopic { name: string; subtopics: string[] }
interface SyllabusSubject { name: string; topics: SyllabusTopic[] }

interface Question {
  question_id: string
  subject: string
  topic: string
  subtopic?: string
  question_text_en: string
  options: string[]
  correct_index: number
  difficulty: number
  explanation_en: string
}

// ── AI Chat panel (unchanged) ─────────────────────────────────────────────

interface ChatMessage { role: 'user' | 'ai'; text: string; isGuardrail?: boolean }

function AiChatPanel({ questionText: _q }: { questionText: string }) {
  const [open, setOpen] = useState(false)
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const send = async (e: React.FormEvent) => {
    e.preventDefault()
    const msg = input.trim()
    if (!msg || loading) return
    setInput('')
    setMessages(prev => [...prev, { role: 'user', text: msg }])
    setLoading(true)
    try {
      const res = await api.sendMessage(msg)
      const d = res.data
      const isGuardrail = !!(d.agent === 'guardrail' || d.threat || d.quarantined)
      setMessages(prev => [...prev, { role: 'ai', text: d.response || d.notes || d.message || "I'm here to help!", isGuardrail }])
    } catch (err: any) {
      setMessages(prev => [...prev, { role: 'ai', text: err.response?.data?.detail || 'Could not get a response.', isGuardrail: false }])
    } finally { setLoading(false) }
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700">
      <button onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-5 py-3 text-sm font-semibold text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition rounded-lg">
        <span className="flex items-center gap-2"><MessageCircle size={16} className="text-primary" /> Ask Naga about this question</span>
        <ChevronRight size={16} className={`text-gray-400 transition-transform ${open ? 'rotate-90' : ''}`} />
      </button>
      {open && (
        <div className="border-t border-gray-100 dark:border-gray-700">
          {messages.length === 0 && <p className="px-5 py-3 text-xs text-gray-400">Ask anything about the concept, formula, or approach.</p>}
          <div className="max-h-64 overflow-y-auto px-4 py-2 space-y-3">
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] px-3 py-2 rounded-xl text-sm ${
                  m.role === 'user' ? 'bg-primary text-white rounded-br-sm'
                  : m.isGuardrail ? 'bg-amber-50 dark:bg-amber-900/20 border border-amber-200 text-amber-800 rounded-bl-sm'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-bl-sm'}`}>
                  {m.isGuardrail && <span className="flex items-center gap-1 text-xs font-semibold mb-1"><ShieldAlert size={12} /> Guardrail</span>}
                  {m.text}
                </div>
              </div>
            ))}
            {loading && <div className="flex justify-start"><div className="bg-gray-100 dark:bg-gray-700 px-3 py-2 rounded-xl rounded-bl-sm"><Loader2 size={14} className="animate-spin text-primary" /></div></div>}
            <div ref={bottomRef} />
          </div>
          <form onSubmit={send} className="flex gap-2 px-4 pb-4 pt-2">
            <input value={input} onChange={e => setInput(e.target.value)}
              placeholder="Ask about the concept, formula, or approach…"
              className="flex-1 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-primary outline-none" />
            <button type="submit" disabled={!input.trim() || loading}
              className="p-2 bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-40 transition">
              <Send size={16} />
            </button>
          </form>
        </div>
      )}
    </div>
  )
}

// ── Difficulty picker (reused in two places) ──────────────────────────────

const DIFFICULTIES = [
  { value: 'easy',     label: 'Easy',     desc: 'Fundamental concepts and formulas' },
  { value: 'medium',   label: 'Medium',   desc: 'Application and word problems' },
  { value: 'hard',     label: 'Hard',     desc: 'Advanced problems and edge cases' },
  { value: 'adaptive', label: 'Adaptive', desc: 'Matches your current level' },
]

function DifficultyPicker({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <div className="space-y-3">
      {DIFFICULTIES.map(opt => (
        <button key={opt.value} onClick={() => onChange(opt.value)}
          className={`w-full text-left p-4 border-2 rounded-xl transition ${
            value === opt.value ? 'border-primary bg-primary/5 dark:bg-primary/10' : 'border-gray-200 dark:border-gray-700 hover:border-primary/40'}`}>
          <div className="flex items-center justify-between">
            <div>
              <p className="font-semibold text-gray-900 dark:text-white">{opt.label}</p>
              <p className="text-sm text-gray-500 dark:text-gray-400">{opt.desc}</p>
            </div>
            <div className={`w-5 h-5 rounded-full border-2 shrink-0 ${value === opt.value ? 'border-primary bg-primary' : 'border-gray-300 dark:border-gray-600'}`} />
          </div>
        </button>
      ))}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────

type Step = 'subject' | 'topic' | 'subtopic' | 'difficulty' | 'running' | 'results'

interface SessionResult {
  topic: string
  subtopic?: string
  subject: string
  score_pct: number
  correct: number
  total: number
  review: Array<{
    question_text: string
    options: string[]
    your_answer: number
    correct_index: number
    correct: boolean
    explanation: string
  }>
}

export default function TestPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const student = useAuthStore(s => s.student)

  // If navigated from StudyPage with ?topic=… (and optionally &subtopic=…)
  // skip straight to difficulty
  const topicFromUrl = searchParams.get('topic') || ''
  const subjectFromUrl = searchParams.get('subject') || ''
  const subtopicFromUrl = searchParams.get('subtopic') || ''

  // Syllabus
  const [subjects, setSubjects] = useState<SyllabusSubject[]>([])
  const [syllabusLoading, setSyllabusLoading] = useState(true)

  // Selection state
  const [step, setStep] = useState<Step>(topicFromUrl ? 'difficulty' : 'subject')
  const [selectedSubject, setSelectedSubject] = useState<SyllabusSubject | null>(
    subjectFromUrl ? { name: subjectFromUrl, topics: [] } : null
  )
  const [selectedTopic, setSelectedTopic] = useState<SyllabusTopic | null>(
    topicFromUrl ? { name: topicFromUrl, subtopics: [] } : null
  )
  const [selectedSubtopic, setSelectedSubtopic] = useState(subtopicFromUrl)
  const [difficulty, setDifficulty] = useState('adaptive')

  // Session state
  const [sessionId, setSessionId] = useState('')
  const [questions, setQuestions] = useState<Question[]>([])
  const [currentIdx, setCurrentIdx] = useState(0)
  const [answers, setAnswers] = useState<number[]>([])   // -1 = not attempted
  const [pickedIndex, setPickedIndex] = useState<number | null>(null)
  const [showFeedback, setShowFeedback] = useState(false)
  const [loading, setLoading] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)
  const [capReached, setCapReached] = useState(false)
  const [batchExhausted, setBatchExhausted] = useState(false)
  const [sessionError, setSessionError] = useState('')
  const [result, setResult] = useState<SessionResult | null>(null)

  useEffect(() => {
    api.getPracticeSyllabus()
      .then(res => setSubjects(res.data.subjects || []))
      .catch(() => {})
      .finally(() => setSyllabusLoading(false))
  }, [])

  // ── Start session ──────────────────────────────────────────────────────

  const startSession = async () => {
    if (!selectedTopic) return
    // Subject may be unknown when arriving from notes — use 'General' as fallback
    const subject = selectedSubject?.name || 'General'
    const examKey = student?.exam_target || ''
    setSessionError('')
    setLoading(true)
    try {
      const res = await api.startPracticeSession(
        examKey, subject, selectedTopic.name, selectedSubtopic, difficulty, 10,
      )
      const d = res.data
      if (!d.questions || d.questions.length === 0) {
        setSessionError('No questions available for this topic yet. Try again in a moment.')
        return
      }
      setSessionId(d.session_id)
      setQuestions(d.questions)
      setAnswers(new Array(d.questions.length).fill(-1))
      setCurrentIdx(0)
      setPickedIndex(null)
      setShowFeedback(false)
      setCapReached(false)
      setBatchExhausted(false)
      setStep('running')
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Could not load questions. Please try again.'
      setSessionError(msg)
    } finally {
      setLoading(false)
    }
  }

  // ── Answer a question ─────────────────────────────────────────────────

  const submitAnswer = () => {
    if (pickedIndex === null) return
    const updated = [...answers]
    updated[currentIdx] = pickedIndex
    setAnswers(updated)
    setShowFeedback(true)
  }

  const goNext = () => {
    // Advance within the loaded batch; at the last loaded question the UI shows
    // "Next 10" / "Finish" choices instead of auto-advancing.
    if (currentIdx < questions.length - 1) {
      setCurrentIdx(currentIdx + 1)
      setPickedIndex(null)
      setShowFeedback(false)
    }
  }

  const loadMore = async () => {
    setLoadingMore(true)
    try {
      const res = await api.morePracticeQuestions(sessionId)
      const more: Question[] = res.data.questions || []
      if (more.length === 0) {
        setBatchExhausted(true)
        return
      }
      setQuestions(prev => [...prev, ...more])
      setAnswers(prev => [...prev, ...new Array(more.length).fill(-1)])
      setCapReached(!!res.data.cap_reached)
      // Move to the first question of the new batch
      setCurrentIdx(questions.length)
      setPickedIndex(null)
      setShowFeedback(false)
    } catch (err) {
      console.error('Load more failed', err)
    } finally {
      setLoadingMore(false)
    }
  }

  const finishSession = async (finalAnswers: number[]) => {
    setLoading(true)
    try {
      const res = await api.submitPracticeSession(sessionId, finalAnswers)
      setResult(res.data)
      setStep('results')
    } catch (err) {
      console.error('Submit failed', err)
    } finally {
      setLoading(false)
    }
  }

  // ── Render: subject selection ─────────────────────────────────────────

  if (step === 'subject') {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-1">🎯 Practice Test</h1>
          <p className="text-gray-500 dark:text-gray-400 text-sm mb-6">Choose a subject to practise</p>

          {syllabusLoading ? (
            <div className="flex justify-center py-10"><Loader2 size={28} className="animate-spin text-primary" /></div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {subjects.map(subj => (
                <button key={subj.name}
                  onClick={() => { setSelectedSubject(subj); setSelectedTopic(null); setSelectedSubtopic(''); setStep('topic') }}
                  className="text-left p-4 border-2 border-gray-200 dark:border-gray-700 rounded-xl hover:border-primary hover:bg-primary/5 transition group">
                  <div className="flex items-center gap-3">
                    <BookOpen size={18} className="text-primary shrink-0" />
                    <div className="min-w-0">
                      <p className="font-semibold text-gray-900 dark:text-white truncate">{subj.name}</p>
                      <p className="text-xs text-gray-400">{subj.topics.length} topics</p>
                    </div>
                    <ChevronRight size={16} className="text-gray-300 group-hover:text-primary ml-auto shrink-0" />
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    )
  }

  // ── Render: topic selection ───────────────────────────────────────────

  if (step === 'topic') {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
          <button onClick={() => setStep('subject')}
            className="flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400 hover:text-primary mb-4 transition">
            <ChevronLeft size={16} /> Back to subjects
          </button>
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-1">{selectedSubject?.name}</h2>
          <p className="text-gray-500 dark:text-gray-400 text-sm mb-5">Choose a topic to practise</p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {(selectedSubject?.topics || []).map(topic => (
              <button key={topic.name}
                onClick={() => {
                  setSelectedTopic(topic)
                  setSelectedSubtopic('')
                  // Skip subtopic step if this topic has none
                  setStep(topic.subtopics && topic.subtopics.length > 0 ? 'subtopic' : 'difficulty')
                }}
                className="text-left px-4 py-3 border-2 border-gray-200 dark:border-gray-700 rounded-xl hover:border-primary hover:bg-primary/5 transition text-sm font-medium text-gray-800 dark:text-gray-200 flex items-center justify-between group">
                <span>
                  {topic.name}
                  {topic.subtopics?.length > 0 && (
                    <span className="text-xs text-gray-400 ml-1">({topic.subtopics.length})</span>
                  )}
                </span>
                <ChevronRight size={14} className="text-gray-300 group-hover:text-primary shrink-0" />
              </button>
            ))}
          </div>
        </div>
      </div>
    )
  }

  // ── Render: subtopic selection ────────────────────────────────────────

  if (step === 'subtopic') {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
          <button onClick={() => setStep('topic')}
            className="flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400 hover:text-primary mb-4 transition">
            <ChevronLeft size={16} /> Back to topics
          </button>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 px-2 py-1 rounded-full">{selectedSubject?.name}</span>
            <span className="text-xs bg-primary/10 text-primary px-2 py-1 rounded-full font-medium">{selectedTopic?.name}</span>
          </div>
          <p className="text-gray-500 dark:text-gray-400 text-sm mt-3 mb-4">Choose a subtopic to drill</p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {/* Whole-topic option */}
            <button
              onClick={() => { setSelectedSubtopic(''); setStep('difficulty') }}
              className="text-left px-4 py-3 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-xl hover:border-primary hover:bg-primary/5 transition text-sm font-medium text-gray-600 dark:text-gray-300 flex items-center justify-between group">
              All of {selectedTopic?.name}
              <ChevronRight size={14} className="text-gray-300 group-hover:text-primary shrink-0" />
            </button>
            {(selectedTopic?.subtopics || []).map(sub => (
              <button key={sub}
                onClick={() => { setSelectedSubtopic(sub); setStep('difficulty') }}
                className="text-left px-4 py-3 border-2 border-gray-200 dark:border-gray-700 rounded-xl hover:border-primary hover:bg-primary/5 transition text-sm font-medium text-gray-800 dark:text-gray-200 flex items-center justify-between group">
                {sub}
                <ChevronRight size={14} className="text-gray-300 group-hover:text-primary shrink-0" />
              </button>
            ))}
          </div>
        </div>
      </div>
    )
  }

  // ── Render: difficulty selection ──────────────────────────────────────

  if (step === 'difficulty') {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
          {!topicFromUrl && (
            <button
              onClick={() => {
                setSessionError('')
                // Back to subtopic if the topic has subtopics, else topics
                setStep(selectedTopic?.subtopics && selectedTopic.subtopics.length > 0 ? 'subtopic' : 'topic')
              }}
              className="flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400 hover:text-primary mb-4 transition">
              <ChevronLeft size={16} /> Back
            </button>
          )}
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-1">🎯 Practice Test</h2>
          <div className="flex flex-wrap items-center gap-2 mb-5">
            {selectedSubject?.name && (
              <span className="text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 px-2 py-1 rounded-full">{selectedSubject.name}</span>
            )}
            {selectedTopic?.name && (
              <span className="text-xs bg-primary/10 text-primary px-2 py-1 rounded-full font-medium">{selectedTopic.name}</span>
            )}
            {selectedSubtopic && (
              <span className="text-xs bg-secondary/10 text-secondary px-2 py-1 rounded-full font-medium">{selectedSubtopic}</span>
            )}
          </div>

          <p className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Choose difficulty</p>
          <DifficultyPicker value={difficulty} onChange={setDifficulty} />

          {sessionError && (
            <div className="mt-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl px-4 py-3">
              <p className="text-sm text-red-700 dark:text-red-300">{sessionError}</p>
              <p className="text-xs text-red-500 dark:text-red-400 mt-1">
                Questions are being generated for this topic — try again in 15 seconds.
              </p>
            </div>
          )}

          <button onClick={startSession} disabled={loading || !selectedTopic}
            className="mt-4 w-full bg-primary hover:bg-primary/90 disabled:bg-gray-300 dark:disabled:bg-gray-600 text-white font-semibold py-3 px-6 rounded-xl transition flex items-center justify-center gap-2">
            {loading
              ? <><Loader2 size={16} className="animate-spin" /> Loading questions…</>
              : <><Zap size={18} /> Start Practice</>}
          </button>
        </div>
      </div>
    )
  }

  // ── Render: results ───────────────────────────────────────────────────

  if (step === 'results' && result) {
    const pct = Math.round(result.score_pct)
    const color = pct >= 70 ? 'text-green-600' : pct >= 40 ? 'text-yellow-500' : 'text-red-500'
    return (
      <div className="max-w-2xl mx-auto space-y-5 pb-12">
        {/* Score card */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6 text-center">
          <BarChart2 size={36} className="mx-auto mb-2 text-primary" />
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-1">{result.topic}</h2>
          <p className={`text-5xl font-extrabold ${color} my-3`}>{pct}%</p>
          <p className="text-gray-600 dark:text-gray-400">{result.correct} correct out of {result.total}</p>
        </div>

        {/* Per-question review */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-5 space-y-5">
          <h3 className="font-bold text-gray-900 dark:text-white">Answer Review</h3>
          {result.review.map((r, i) => (
            <div key={i} className={`border-2 rounded-xl overflow-hidden ${r.correct ? 'border-green-200 dark:border-green-800' : 'border-red-200 dark:border-red-800'}`}>
              <div className={`flex items-start gap-3 p-4 ${r.correct ? 'bg-green-50 dark:bg-green-900/20' : 'bg-red-50 dark:bg-red-900/20'}`}>
                {r.correct
                  ? <CheckCircle size={18} className="text-green-600 shrink-0 mt-0.5" />
                  : <XCircle size={18} className="text-red-500 shrink-0 mt-0.5" />}
                <p className="text-sm font-medium text-gray-900 dark:text-white">{i + 1}. {r.question_text}</p>
              </div>
              <div className="p-4 space-y-1.5">
                {r.options.map((opt, oi) => {
                  const isCorrect = oi === r.correct_index
                  const isWrong = oi === r.your_answer && !r.correct
                  return (
                    <div key={oi} className={`text-sm px-3 py-2 rounded-lg ${
                      isCorrect ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200 font-semibold'
                      : isWrong ? 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200 font-semibold'
                      : 'text-gray-600 dark:text-gray-400'}`}>
                      {opt}{isCorrect ? ' ✓' : ''}{isWrong ? ' ✗' : ''}
                    </div>
                  )
                })}
                {r.explanation && (
                  <p className="text-xs text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-blue-900/20 rounded-lg px-3 py-2 mt-2">{r.explanation}</p>
                )}
              </div>
            </div>
          ))}
        </div>

        <div className="flex gap-3">
          <button onClick={() => { setStep('difficulty'); setResult(null) }}
            className="flex-1 border-2 border-primary text-primary font-semibold py-3 rounded-xl hover:bg-primary/5 transition">
            Practise again
          </button>
          <button onClick={() => navigate('/progress')}
            className="flex-1 bg-primary text-white font-semibold py-3 rounded-xl hover:bg-primary/90 transition">
            View Progress →
          </button>
        </div>
      </div>
    )
  }

  // ── Render: running session ───────────────────────────────────────────

  if (step !== 'running' || questions.length === 0) {
    if (loading) return <div className="flex justify-center py-20"><Loader2 size={32} className="animate-spin text-primary" /></div>
    return null
  }

  const q = questions[currentIdx]
  const progress = ((currentIdx + (showFeedback ? 1 : 0)) / questions.length) * 100
  const isCorrect = showFeedback && pickedIndex === q.correct_index

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      {/* Progress */}
      <div>
        <div className="flex justify-between items-center mb-1.5">
          <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">
            Q {currentIdx + 1} of {questions.length}
          </span>
          <span className="text-xs text-gray-400">{selectedSubtopic || selectedTopic?.name}</span>
        </div>
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
          <div className="bg-primary h-2 rounded-full transition-all duration-300" style={{ width: `${progress}%` }} />
        </div>
      </div>

      {/* Question card */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
        <div className="mb-5">
          <span className="inline-block text-xs bg-primary/10 text-primary px-2.5 py-1 rounded-full font-medium mb-3">
            {q.subject} · {q.topic}
          </span>
          <h2 className="text-lg font-bold text-gray-900 dark:text-white leading-snug">{q.question_text_en}</h2>
        </div>

        {/* Options */}
        <div className="space-y-2.5 mb-6">
          {q.options.map((opt, oi) => {
            let cls = 'border-gray-200 dark:border-gray-700 hover:border-primary/50'
            if (showFeedback) {
              if (oi === q.correct_index) cls = 'border-green-500 bg-green-50 dark:bg-green-900/20'
              else if (oi === pickedIndex) cls = 'border-red-500 bg-red-50 dark:bg-red-900/20'
            } else if (pickedIndex === oi) {
              cls = 'border-primary bg-primary/5'
            }
            return (
              <button key={oi} disabled={showFeedback} onClick={() => setPickedIndex(oi)}
                className={`w-full text-left p-3.5 border-2 rounded-xl transition flex items-center gap-3 ${cls} disabled:cursor-default`}>
                <div className={`shrink-0 w-6 h-6 rounded-full border-2 flex items-center justify-center text-xs font-bold
                  ${showFeedback && oi === q.correct_index ? 'border-green-500 bg-green-500 text-white'
                  : showFeedback && oi === pickedIndex ? 'border-red-500 bg-red-500 text-white'
                  : pickedIndex === oi ? 'border-primary bg-primary text-white'
                  : 'border-gray-300 dark:border-gray-600 text-gray-400'}`}>
                  {String.fromCharCode(65 + oi)}
                </div>
                <span className="text-gray-800 dark:text-gray-200 text-sm">{opt}</span>
                {showFeedback && oi === q.correct_index && <CheckCircle size={16} className="text-green-500 ml-auto shrink-0" />}
                {showFeedback && oi === pickedIndex && oi !== q.correct_index && <XCircle size={16} className="text-red-500 ml-auto shrink-0" />}
              </button>
            )
          })}
        </div>

        {/* Explanation after answer */}
        {showFeedback && (
          <div className={`rounded-xl p-4 mb-5 ${isCorrect ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800' : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800'}`}>
            <p className="font-semibold text-sm text-gray-900 dark:text-white mb-1">
              {isCorrect ? '✅ Correct!' : '❌ Incorrect'}
            </p>
            {q.explanation_en && <p className="text-sm text-gray-700 dark:text-gray-300">{q.explanation_en}</p>}
          </div>
        )}

        {/* Action button */}
        <div className="flex justify-end">
          {!showFeedback ? (
            <button onClick={submitAnswer} disabled={pickedIndex === null}
              className="bg-primary hover:bg-primary/90 disabled:bg-gray-300 dark:disabled:bg-gray-600 text-white font-semibold py-2.5 px-6 rounded-xl transition flex items-center gap-2">
              Submit <ChevronRight size={18} />
            </button>
          ) : currentIdx < questions.length - 1 ? (
            <button onClick={goNext}
              className="bg-primary hover:bg-primary/90 text-white font-semibold py-2.5 px-6 rounded-xl transition flex items-center gap-2">
              Next <ChevronRight size={18} />
            </button>
          ) : (
            // Last question of the current batch → offer more or finish
            <div className="flex flex-col sm:flex-row gap-2 w-full sm:w-auto">
              {!capReached && !batchExhausted && (
                <button onClick={loadMore} disabled={loadingMore}
                  className="border-2 border-primary text-primary hover:bg-primary/5 font-semibold py-2.5 px-5 rounded-xl transition flex items-center justify-center gap-2">
                  {loadingMore
                    ? <><Loader2 size={15} className="animate-spin" /> Loading…</>
                    : <>Next 10 questions <ChevronRight size={16} /></>}
                </button>
              )}
              <button onClick={() => finishSession([...answers])} disabled={loading}
                className="bg-primary hover:bg-primary/90 text-white font-semibold py-2.5 px-6 rounded-xl transition flex items-center justify-center gap-2">
                {loading ? <><Loader2 size={15} className="animate-spin" /> Saving…</>
                  : <>Finish &amp; Review <ChevronRight size={18} /></>}
              </button>
            </div>
          )}
        </div>
        {(capReached || batchExhausted) && !showFeedback && currentIdx === questions.length - 1 && (
          <p className="text-xs text-gray-400 text-center mt-3">
            {capReached
              ? 'You’ve reached the 100-question limit for this session.'
              : 'No more new questions for this subtopic right now — finish to see your results.'}
          </p>
        )}
      </div>

      <AiChatPanel key={q.question_id} questionText={q.question_text_en} />
    </div>
  )
}
