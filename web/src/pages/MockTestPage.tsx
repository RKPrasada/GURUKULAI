import { useEffect, useRef, useState } from 'react'
import { useAuthStore } from '@/store/auth'
import { Link } from 'react-router-dom'
import {
  Clock, Flag, ChevronLeft, ChevronRight, AlertTriangle,
  CheckCircle2, BarChart2, BookOpen, RefreshCw, Trophy,
} from 'lucide-react'
import api from '@/services/api'

// ── Types ──────────────────────────────────────────────────────────────────────

interface Question {
  question_id: string
  section: string
  topic: string
  difficulty: 'easy' | 'medium' | 'hard'
  question_text_en: string
  options: string[]
  marks: number
  negative_marks: number
  correct_index?: number
  explanation_en?: string
}

interface Section { name: string; count: number; questions: Question[] }

interface Paper {
  paper_id: string
  exam_key: string
  exam_name: string
  scheduled_date: string
  total_questions: number
  duration_mins: number
  negative_marking: number
  marks_per_question: number
  sections: Section[]
}

interface SectionScore {
  name: string; score: number; max_score: number
  correct: number; wrong: number; unattempted: number; accuracy_pct: number
}

interface HistoryEntry {
  session_id: string; exam_key: string; paper_id: string
  started_at: string; submitted_at: string; timed_out: boolean
  score: number; max_score: number; score_pct: number
  rank_estimate_pct: number; section_scores: SectionScore[]
}

// ── helpers ────────────────────────────────────────────────────────────────────

function fmtTime(secs: number) {
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  const s = secs % 60
  return h > 0
    ? `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
    : `${m}:${String(s).padStart(2, '0')}`
}

const diffColor = (d: string) =>
  d === 'easy' ? 'text-emerald-500' : d === 'medium' ? 'text-amber-500' : 'text-red-500'

const scoreColor = (pct: number) =>
  pct >= 70 ? 'text-emerald-600' : pct >= 50 ? 'text-amber-600' : 'text-red-600'

// ── Q status enum (for navigator colouring) ───────────────────────────────────
// 0=unvisited, 1=answered, 2=flagged, 3=answered+flagged, 4=visited-not-answered
const navColor = (status: number, current: boolean) => {
  if (current) return 'bg-primary text-white ring-2 ring-primary ring-offset-1'
  if (status === 1) return 'bg-blue-500 text-white'
  if (status === 2) return 'bg-orange-400 text-white'
  if (status === 3) return 'bg-purple-500 text-white'
  if (status === 4) return 'bg-gray-300 dark:bg-gray-600 text-gray-700 dark:text-gray-200'
  return 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400'
}

// ── Landing view ──────────────────────────────────────────────────────────────

function LandingView({
  status, history, onStart, onResume, activeSessionId, secsRemaining,
}: {
  status: any; history: HistoryEntry[]; onStart: () => void
  onResume: () => void; activeSessionId: string | null; secsRemaining: number | null
}) {
  const student = useAuthStore((s) => s.student)
  const best = history.length > 0 ? Math.max(...history.map((h) => h.score_pct)) : null

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-8">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-14 h-14 bg-indigo-100 dark:bg-indigo-900/40 rounded-full flex items-center justify-center flex-shrink-0">
            <BookOpen size={28} className="text-indigo-600 dark:text-indigo-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Weekly Mock Test</h1>
            <p className="text-sm text-gray-400">Every Saturday · Full exam pattern · Negative marking</p>
          </div>
        </div>

        {status?.available ? (
          <>
            <div className="grid grid-cols-3 gap-3 mb-6">
              <InfoChip icon={<Clock size={16} />} label="Duration" value={`${status.duration_mins} min`} />
              <InfoChip icon={<AlertTriangle size={16} />} label="Questions" value={`${status.total_questions} Q`} />
              <InfoChip icon={<CheckCircle2 size={16} />} label="Paper date" value={status.scheduled_date} />
            </div>

            <div className="text-xs text-gray-500 mb-1">Sections</div>
            <div className="flex flex-wrap gap-2 mb-6">
              {status.section_names?.map((s: string) => (
                <span key={s} className="text-xs bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 px-2 py-1 rounded-full font-medium">
                  {s}
                </span>
              ))}
            </div>

            <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg p-3 mb-6 text-xs text-amber-800 dark:text-amber-200">
              <strong>Negative marking:</strong> Each correct answer = +{status.marks_per_question ?? 1} mark. Each wrong = −{((1/3)).toFixed(2)} marks. Unattempted = 0.
              Do not guess randomly.
            </div>

            {activeSessionId ? (
              <div className="space-y-3">
                <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg p-3 text-sm text-blue-800 dark:text-blue-200">
                  You have an in-progress session with <strong>{fmtTime(secsRemaining ?? 0)}</strong> remaining.
                </div>
                <button onClick={onResume} className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-xl transition">
                  Resume Test →
                </button>
              </div>
            ) : (
              <button
                onClick={onStart}
                disabled={!student?.diagnostic_done}
                className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-bold py-3 rounded-xl transition text-lg"
              >
                {student?.diagnostic_done ? 'Start Mock Test' : 'Complete Diagnostic First'}
              </button>
            )}
          </>
        ) : (
          <div className="text-center py-8">
            <RefreshCw size={32} className="text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500 dark:text-gray-400 mb-2">No paper available yet.</p>
            <p className="text-xs text-gray-400">Papers are generated every Saturday at 15:00. Check back then.</p>
          </div>
        )}
      </div>

      {history.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-5">
          <h2 className="text-base font-bold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
            <Trophy size={16} className="text-amber-500" /> Past Attempts
            {best !== null && <span className="text-xs font-normal text-gray-400 ml-1">Best: <strong className={scoreColor(best)}>{best.toFixed(1)}%</strong></span>}
          </h2>
          <div className="space-y-2">
            {history.slice(0, 5).map((h) => (
              <div key={h.session_id} className="flex items-center justify-between text-sm p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                <div>
                  <span className="font-medium text-gray-800 dark:text-gray-200">{h.paper_id}</span>
                  {h.timed_out && <span className="ml-2 text-xs text-orange-500">Timed out</span>}
                  <p className="text-xs text-gray-400">{h.submitted_at?.slice(0, 10)}</p>
                </div>
                <div className="text-right">
                  <p className={`font-bold text-base ${scoreColor(h.score_pct)}`}>{h.score_pct.toFixed(1)}%</p>
                  <p className="text-xs text-gray-400">{h.score}/{h.max_score} · Top {(100 - h.rank_estimate_pct).toFixed(0)}%ile</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function InfoChip({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
      <div className="text-indigo-500 mb-1">{icon}</div>
      <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
      <p className="text-sm font-semibold text-gray-800 dark:text-gray-200">{value}</p>
    </div>
  )
}

// ── Test view ─────────────────────────────────────────────────────────────────

function TestView({
  paper, sessionId, initialAnswers, initialFlagged, initialSecsLeft,
  onSubmit,
}: {
  paper: Paper
  sessionId: string
  initialAnswers: number[]
  initialFlagged: number[]
  initialSecsLeft: number
  onSubmit: (answers: number[], flagged: number[], timedOut: boolean) => void
}) {
  // Flatten questions into a single array with global indices
  const allQuestions: Question[] = paper.sections.flatMap((s) => s.questions)

  const [answers, setAnswers] = useState<number[]>(initialAnswers)
  const [flagged, setFlagged] = useState<Set<number>>(new Set(initialFlagged))
  const [currentIdx, setCurrentIdx] = useState(0)
  const [visited, setVisited] = useState<Set<number>>(new Set([0]))
  const [secsLeft, setSecsLeft] = useState(initialSecsLeft)
  const [activeSec, setActiveSec] = useState(0)
  const [showConfirm, setShowConfirm] = useState(false)
  const [showNav, setShowNav] = useState(false)
  const autosaveRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Section boundary indices
  const secBoundaries: Array<[number, number]> = []
  let idx = 0
  for (const sec of paper.sections) {
    secBoundaries.push([idx, idx + sec.count - 1])
    idx += sec.count
  }

  // Update active section when question changes
  useEffect(() => {
    for (let i = 0; i < secBoundaries.length; i++) {
      const [start, end] = secBoundaries[i]
      if (currentIdx >= start && currentIdx <= end) { setActiveSec(i); break }
    }
    setVisited((v) => new Set([...v, currentIdx]))
  }, [currentIdx])

  // Countdown timer
  useEffect(() => {
    const t = setInterval(() => {
      setSecsLeft((s) => {
        if (s <= 1) {
          clearInterval(t)
          onSubmit(answers, Array.from(flagged), true)
          return 0
        }
        return s - 1
      })
    }, 1000)
    return () => clearInterval(t)
  }, [])

  // Autosave every 30s
  useEffect(() => {
    autosaveRef.current = setInterval(async () => {
      try {
        await api.autosaveMock(sessionId, answers, Array.from(flagged))
      } catch { /* non-critical */ }
    }, 30_000)
    return () => { if (autosaveRef.current) clearInterval(autosaveRef.current) }
  }, [answers, flagged])

  const q = allQuestions[currentIdx]
  const isAnswered = (i: number) => answers[i] !== -1
  const isFlagged = (i: number) => flagged.has(i)

  const qStatus = (i: number): number => {
    const ans = isAnswered(i)
    const fl = isFlagged(i)
    if (ans && fl) return 3
    if (ans) return 1
    if (fl) return 2
    if (visited.has(i)) return 4
    return 0
  }

  const selectAnswer = (optIdx: number) => {
    setAnswers((a) => { const n = [...a]; n[currentIdx] = optIdx; return n })
  }

  const clearAnswer = () => {
    setAnswers((a) => { const n = [...a]; n[currentIdx] = -1; return n })
  }

  const toggleFlag = () => {
    setFlagged((f) => {
      const n = new Set(f)
      if (n.has(currentIdx)) n.delete(currentIdx); else n.add(currentIdx)
      return n
    })
  }

  const timerColor = secsLeft < 300 ? 'text-red-500' : secsLeft < 900 ? 'text-amber-500' : 'text-gray-700 dark:text-gray-200'

  const answered = answers.filter((a) => a !== -1).length
  const total = allQuestions.length

  return (
    <div className="min-h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
      {/* ── Fixed header ── */}
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 sticky top-0 z-20 px-4 py-2">
        <div className="flex items-center justify-between max-w-5xl mx-auto">
          <div>
            <span className="font-bold text-gray-900 dark:text-white text-sm">{paper.exam_name}</span>
            <span className="ml-2 text-xs text-gray-400">{answered}/{total} answered</span>
          </div>
          <div className={`flex items-center gap-1.5 font-mono font-bold text-lg ${timerColor}`}>
            <Clock size={18} />
            {fmtTime(secsLeft)}
          </div>
          <button
            onClick={() => setShowConfirm(true)}
            className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold px-4 py-1.5 rounded-lg transition"
          >
            Submit
          </button>
        </div>

        {/* Section tabs */}
        <div className="flex gap-1 overflow-x-auto mt-2 max-w-5xl mx-auto pb-1">
          {paper.sections.map((sec, i) => {
            const [start, end] = secBoundaries[i]
            const doneInSec = answers.slice(start, end + 1).filter((a) => a !== -1).length
            return (
              <button
                key={sec.name}
                onClick={() => setCurrentIdx(start)}
                className={`flex-shrink-0 text-xs px-3 py-1 rounded-lg font-medium transition ${
                  activeSec === i
                    ? 'bg-indigo-600 text-white'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                }`}
              >
                {sec.name} ({doneInSec}/{sec.count})
              </button>
            )
          })}
        </div>
      </header>

      <div className="flex flex-1 max-w-5xl mx-auto w-full gap-4 p-4">
        {/* ── Question panel ── */}
        <main className="flex-1 min-w-0">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-5">
            {/* Q header */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-gray-400">Q {currentIdx + 1}/{total}</span>
                <span className={`text-xs font-semibold px-1.5 py-0.5 rounded ${diffColor(q.difficulty)} bg-gray-100 dark:bg-gray-700`}>
                  {q.difficulty}
                </span>
                <span className="text-xs text-gray-400">{q.topic}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-400">+{q.marks} / −{q.negative_marks.toFixed(2)}</span>
                <button
                  onClick={toggleFlag}
                  className={`flex items-center gap-1 text-xs px-2 py-1 rounded-lg font-medium transition ${
                    isFlagged(currentIdx)
                      ? 'bg-orange-100 text-orange-600 dark:bg-orange-900/30 dark:text-orange-400'
                      : 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400 hover:bg-orange-50 hover:text-orange-500'
                  }`}
                >
                  <Flag size={12} /> {isFlagged(currentIdx) ? 'Flagged' : 'Flag'}
                </button>
              </div>
            </div>

            {/* Question text */}
            <p className="text-gray-900 dark:text-white leading-relaxed mb-5 font-medium">
              {q.question_text_en}
            </p>

            {/* Options */}
            <div className="space-y-2">
              {q.options.map((opt, oi) => {
                const selected = answers[currentIdx] === oi
                return (
                  <button
                    key={oi}
                    onClick={() => selectAnswer(oi)}
                    className={`w-full flex items-start gap-3 p-3 rounded-xl border text-left text-sm transition ${
                      selected
                        ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-900 dark:text-indigo-100'
                        : 'border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/50 text-gray-800 dark:text-gray-200 hover:border-indigo-300 hover:bg-indigo-50/50 dark:hover:bg-indigo-900/20'
                    }`}
                  >
                    <span className={`flex-shrink-0 w-6 h-6 rounded-full border-2 flex items-center justify-center text-xs font-bold ${
                      selected ? 'border-indigo-500 bg-indigo-500 text-white' : 'border-gray-300 dark:border-gray-500 text-gray-500'
                    }`}>
                      {String.fromCharCode(65 + oi)}
                    </span>
                    <span>{opt}</span>
                  </button>
                )
              })}
            </div>

            {/* Footer nav */}
            <div className="flex items-center justify-between mt-5 pt-4 border-t border-gray-100 dark:border-gray-700">
              <button onClick={clearAnswer} disabled={!isAnswered(currentIdx)}
                className="text-xs text-gray-400 hover:text-gray-600 disabled:opacity-30 transition">
                Clear response
              </button>
              <div className="flex gap-2">
                <button onClick={() => setCurrentIdx((i) => Math.max(0, i - 1))}
                  disabled={currentIdx === 0}
                  className="flex items-center gap-1 text-sm px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 disabled:opacity-30 hover:bg-gray-100 dark:hover:bg-gray-700 transition">
                  <ChevronLeft size={14} /> Prev
                </button>
                <button onClick={() => setCurrentIdx((i) => Math.min(total - 1, i + 1))}
                  disabled={currentIdx === total - 1}
                  className="flex items-center gap-1 text-sm px-3 py-1.5 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-30 transition">
                  Next <ChevronRight size={14} />
                </button>
              </div>
            </div>
          </div>
        </main>

        {/* ── Question navigator ── */}
        <aside className="hidden lg:block w-56 flex-shrink-0">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-4 sticky top-32">
            <p className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3">Navigator</p>
            <div className="flex flex-wrap gap-1.5 mb-3">
              {allQuestions.map((_, i) => (
                <button key={i} onClick={() => setCurrentIdx(i)}
                  className={`w-7 h-7 text-xs font-semibold rounded transition ${navColor(qStatus(i), i === currentIdx)}`}>
                  {i + 1}
                </button>
              ))}
            </div>
            <div className="space-y-1 text-xs text-gray-500 dark:text-gray-400 border-t border-gray-100 dark:border-gray-700 pt-3">
              {[
                ['bg-blue-500', 'Answered'],
                ['bg-orange-400', 'Flagged'],
                ['bg-purple-500', 'Ans + Flagged'],
                ['bg-gray-300 dark:bg-gray-600', 'Visited'],
                ['bg-gray-100 dark:bg-gray-700', 'Not visited'],
              ].map(([color, label]) => (
                <div key={label} className="flex items-center gap-2">
                  <span className={`w-4 h-4 rounded ${color} flex-shrink-0`} />
                  <span>{label}</span>
                </div>
              ))}
            </div>
          </div>
        </aside>
      </div>

      {/* Mobile navigator toggle */}
      <button
        onClick={() => setShowNav(!showNav)}
        className="lg:hidden fixed bottom-4 right-4 bg-indigo-600 text-white rounded-full w-12 h-12 flex items-center justify-center shadow-lg z-20"
      >
        <BarChart2 size={20} />
      </button>
      {showNav && (
        <div className="lg:hidden fixed bottom-0 left-0 right-0 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 p-4 z-30 max-h-64 overflow-y-auto">
          <div className="flex flex-wrap gap-1.5">
            {allQuestions.map((_, i) => (
              <button key={i} onClick={() => { setCurrentIdx(i); setShowNav(false) }}
                className={`w-8 h-8 text-xs font-semibold rounded transition ${navColor(qStatus(i), i === currentIdx)}`}>
                {i + 1}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Submit confirmation modal */}
      {showConfirm && (
        <div className="fixed inset-0 bg-black/50 z-40 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl p-6 max-w-sm w-full">
            <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-2">Submit test?</h2>
            <div className="text-sm text-gray-500 dark:text-gray-400 space-y-1 mb-5">
              <p>Answered: <strong className="text-gray-800 dark:text-white">{answered}/{total}</strong></p>
              <p>Unattempted: <strong className="text-gray-800 dark:text-white">{total - answered}</strong></p>
              <p>Flagged for review: <strong className="text-gray-800 dark:text-white">{flagged.size}</strong></p>
              <p>Time remaining: <strong className={timerColor}>{fmtTime(secsLeft)}</strong></p>
            </div>
            <div className="flex gap-3">
              <button onClick={() => setShowConfirm(false)}
                className="flex-1 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-700 transition">
                Back to test
              </button>
              <button onClick={() => onSubmit(answers, Array.from(flagged), false)}
                className="flex-1 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-bold transition">
                Submit now
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Results view ──────────────────────────────────────────────────────────────

function ResultView({
  result, paper, onRestart,
}: {
  result: { score: number; max_score: number; score_pct: number; rank_estimate_pct: number; timed_out: boolean; section_scores: SectionScore[] }
  paper: Paper | null
  onRestart: () => void
}) {
  const [showReview, setShowReview] = useState(false)
  const [reviewSec, setReviewSec] = useState(0)

  const passed = result.score_pct >= 40
  // allQs used for review rendering below

  return (
    <div className="max-w-2xl mx-auto space-y-5">
      {result.timed_out && (
        <div className="bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-700 rounded-xl p-3 text-sm text-orange-800 dark:text-orange-200 flex items-center gap-2">
          <Clock size={16} /> Test auto-submitted — time ran out.
        </div>
      )}

      {/* Score card */}
      <div className={`rounded-xl shadow-lg p-6 text-center ${passed ? 'bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-700' : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700'}`}>
        <div className={`text-5xl font-black mb-1 ${scoreColor(result.score_pct)}`}>
          {result.score_pct.toFixed(1)}%
        </div>
        <p className="text-gray-600 dark:text-gray-300 text-sm mb-1">
          Score: <strong>{result.score}</strong> / {result.max_score} marks
        </p>
        <p className="text-gray-500 dark:text-gray-400 text-xs">
          Estimated rank: Top {(100 - result.rank_estimate_pct).toFixed(0)} percentile
        </p>
        <p className={`mt-2 text-base font-bold ${passed ? 'text-emerald-600' : 'text-red-600'}`}>
          {passed ? '🎉 Above passing threshold' : '📚 Below passing threshold — more practice needed'}
        </p>
      </div>

      {/* Section breakdown */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-5">
        <h2 className="text-base font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <BarChart2 size={16} /> Section Breakdown
        </h2>
        <div className="space-y-4">
          {result.section_scores.map((sec) => {
            const pct = sec.max_score > 0 ? (sec.score / sec.max_score) * 100 : 0
            return (
              <div key={sec.name}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="font-medium text-gray-800 dark:text-gray-200">{sec.name}</span>
                  <span className={`font-bold ${scoreColor(pct)}`}>{sec.score}/{sec.max_score} ({pct.toFixed(0)}%)</span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 mb-1">
                  <div className={`h-2 rounded-full ${pct >= 60 ? 'bg-emerald-500' : pct >= 40 ? 'bg-amber-400' : 'bg-red-500'}`}
                    style={{ width: `${Math.max(pct, 0)}%` }} />
                </div>
                <div className="flex gap-4 text-xs text-gray-400">
                  <span className="text-emerald-600">✓ {sec.correct} correct</span>
                  <span className="text-red-500">✗ {sec.wrong} wrong</span>
                  <span>— {sec.unattempted} skipped</span>
                  <span>Accuracy: {sec.accuracy_pct}%</span>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Paper review */}
      {paper && (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-base font-bold text-gray-900 dark:text-white">Review Answers</h2>
            <button onClick={() => setShowReview(!showReview)}
              className="text-xs text-primary font-medium hover:underline">
              {showReview ? 'Hide' : 'Show review'}
            </button>
          </div>
          {showReview && (
            <>
              <div className="flex gap-1 mb-4 overflow-x-auto">
                {paper.sections.map((s, i) => (
                  <button key={s.name} onClick={() => setReviewSec(i)}
                    className={`flex-shrink-0 text-xs px-3 py-1 rounded-lg font-medium ${reviewSec === i ? 'bg-indigo-600 text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300'}`}>
                    {s.name}
                  </button>
                ))}
              </div>
              <div className="space-y-4">
                {(() => {
                  let gStart = 0
                  for (let si = 0; si < reviewSec; si++) gStart += paper.sections[si].count
                  return paper.sections[reviewSec]?.questions.map((q, qi) => {
                    const correct = q.correct_index
                    return (
                      <div key={q.question_id} className="border border-gray-200 dark:border-gray-700 rounded-xl p-4">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-xs text-gray-400">Q{gStart + qi + 1}</span>
                          <span className={`text-xs font-medium ${diffColor(q.difficulty)}`}>{q.difficulty}</span>
                          <span className="text-xs text-gray-400">· {q.topic}</span>
                        </div>
                        <p className="text-sm text-gray-900 dark:text-white mb-3">{q.question_text_en}</p>
                        <div className="space-y-1">
                          {q.options.map((opt, oi) => (
                            <div key={oi} className={`text-xs px-3 py-2 rounded-lg ${
                              oi === correct
                                ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-200 font-semibold'
                                : 'text-gray-600 dark:text-gray-400'
                            }`}>
                              <span className="font-bold mr-1">{String.fromCharCode(65 + oi)}.</span> {opt}
                            </div>
                          ))}
                        </div>
                        {q.explanation_en && (
                          <p className="mt-2 text-xs text-gray-500 dark:text-gray-400 bg-blue-50 dark:bg-blue-900/20 rounded-lg p-2">
                            💡 {q.explanation_en}
                          </p>
                        )}
                      </div>
                    )
                  })
                })()}
              </div>
            </>
          )}
        </div>
      )}

      <div className="flex gap-3">
        <Link to="/progress" className="flex-1 text-center py-2.5 border border-gray-300 dark:border-gray-600 rounded-xl text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-700 transition">
          View Progress →
        </Link>
        <button onClick={onRestart} className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-sm font-bold transition">
          Back to Mock Tests
        </button>
      </div>
    </div>
  )
}

// ── Page orchestrator ─────────────────────────────────────────────────────────

type View = 'landing' | 'test' | 'result'

export default function MockTestPage() {
  const student = useAuthStore((s) => s.student)
  const examKey = student?.exam_target ?? ''

  const [view, setView] = useState<View>('landing')
  const [status, setStatus] = useState<any>(null)
  const [history, setHistory] = useState<HistoryEntry[]>([])
  const [paper, setPaper] = useState<Paper | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [answers, setAnswers] = useState<number[]>([])
  const [flagged, setFlagged] = useState<number[]>([])
  const [secsLeft, setSecsLeft] = useState(0)
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const loadStatus = async () => {
    if (!examKey) return
    try {
      const [s, h] = await Promise.all([
        api.getMockStatus(examKey),
        api.getMockHistory(),
      ])
      setStatus(s.data)
      setHistory(h.data.history ?? [])
    } catch { /* non-critical */ }
  }

  useEffect(() => { loadStatus() }, [examKey])

  const startTest = async () => {
    setLoading(true); setError('')
    try {
      const res = await api.startMockSession(examKey)
      const d = res.data
      setSessionId(d.session_id)
      setPaper(d.paper)
      setAnswers(d.answers)
      setFlagged(d.flagged ?? [])
      setSecsLeft(d.seconds_remaining)
      setView('test')
    } catch (e: any) {
      setError(e.response?.data?.detail ?? 'Failed to start test')
    }
    setLoading(false)
  }

  const resumeTest = async () => {
    if (!status?.active_session_id) return
    setLoading(true); setError('')
    try {
      const res = await api.getMockSession(status.active_session_id)
      const d = res.data
      setSessionId(d.session_id)
      setPaper(d.paper)
      setAnswers(d.answers)
      setFlagged(d.flagged ?? [])
      setSecsLeft(d.seconds_remaining)
      setView('test')
    } catch (e: any) {
      setError(e.response?.data?.detail ?? 'Failed to resume')
    }
    setLoading(false)
  }

  const submitTest = async (finalAnswers: number[], finalFlagged: number[], timedOut: boolean) => {
    if (!sessionId) return
    try {
      const res = await api.submitMock(sessionId, finalAnswers, finalFlagged, timedOut)
      setResult(res.data)
      setView('result')
      loadStatus()
    } catch {
      setError('Submission failed — please try again.')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
      </div>
    )
  }

  if (view === 'test' && paper && sessionId) {
    return (
      <TestView
        paper={paper}
        sessionId={sessionId}
        initialAnswers={answers}
        initialFlagged={flagged}
        initialSecsLeft={secsLeft}
        onSubmit={submitTest}
      />
    )
  }

  if (view === 'result' && result) {
    return <ResultView result={result} paper={paper} onRestart={() => { setView('landing'); loadStatus() }} />
  }

  return (
    <div>
      {error && (
        <div className="max-w-2xl mx-auto mb-4 bg-red-50 dark:bg-red-900/20 border border-red-200 rounded-xl p-3 text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      )}
      <LandingView
        status={status}
        history={history}
        onStart={startTest}
        onResume={resumeTest}
        activeSessionId={status?.active_session_id ?? null}
        secsRemaining={status?.seconds_remaining ?? null}
      />
    </div>
  )
}
