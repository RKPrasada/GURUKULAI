import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'
import api from '@/services/api'
import {
  Calendar, ChevronRight, ChevronLeft, Clock, BookOpen,
  FlaskConical, RotateCcw, CheckCircle2, AlertCircle,
  Loader2, Flame, Target,
} from 'lucide-react'

// ── Types ──────────────────────────────────────────────────────────────────────

interface SessionBlock {
  block_id: string
  start_hour: number
  duration_hours: number
  subject: string
  topic: string
  session_type: 'study' | 'practice' | 'mock' | 'revision' | 'rest'
  priority: 1 | 2 | 3
  completed: boolean
  rescheduled: boolean
}

interface DayPlan {
  day_date: string
  day_of_week: string
  blocks: SessionBlock[]
  total_hours: number
  is_rest_day: boolean
}

interface WeekPlan {
  week_number: number
  start_date: string
  end_date: string
  theme: string
  days: DayPlan[]
  total_hours: number
}

interface StudyPlan {
  plan_id: string
  student_id: string
  exam_target: string
  status: string
  duration_months: number
  start_date: string
  end_date: string
  exam_date?: string
  weeks: WeekPlan[]
  weak_topics: string[]
  diagnostic_score: number
  total_study_hours: number
}

// ── Helpers ────────────────────────────────────────────────────────────────────

const SESSION_STYLES: Record<string, { bg: string; text: string; icon: React.ReactNode; label: string }> = {
  study:    { bg: 'bg-blue-100 dark:bg-blue-900/40',    text: 'text-blue-700 dark:text-blue-300',    icon: <BookOpen size={13}/>,    label: 'Study' },
  practice: { bg: 'bg-violet-100 dark:bg-violet-900/40', text: 'text-violet-700 dark:text-violet-300', icon: <FlaskConical size={13}/>, label: 'Practice' },
  mock:     { bg: 'bg-red-100 dark:bg-red-900/40',      text: 'text-red-700 dark:text-red-300',      icon: <Target size={13}/>,      label: 'Mock Test' },
  revision: { bg: 'bg-amber-100 dark:bg-amber-900/40',  text: 'text-amber-700 dark:text-amber-300',  icon: <RotateCcw size={13}/>,   label: 'Revision' },
  rest:     { bg: 'bg-gray-100 dark:bg-gray-700',       text: 'text-gray-500 dark:text-gray-400',    icon: <Clock size={13}/>,       label: 'Rest' },
}

const PRIORITY_BORDER: Record<number, string> = {
  1: 'border-l-2 border-blue-300 dark:border-blue-700',
  2: 'border-l-2 border-amber-400 dark:border-amber-600',
  3: 'border-l-4 border-red-500 dark:border-red-600',
}

const fmt12h = (hour: number) => {
  const h = hour % 12 || 12
  return `${h}:00 ${hour < 12 ? 'AM' : 'PM'}`
}

const fmtDate = (iso: string) =>
  new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })

const fmtFullDate = (iso: string) =>
  new Date(iso).toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long' })

const today = () => new Date().toISOString().slice(0, 10)

const weekProgress = (week: WeekPlan): number => {
  const allBlocks = week.days.flatMap((d) => d.blocks)
  if (!allBlocks.length) return 0
  return Math.round((allBlocks.filter((b) => b.completed).length / allBlocks.length) * 100)
}

const isCurrentWeek = (week: WeekPlan): boolean => {
  const t = today()
  return week.start_date <= t && t <= week.end_date
}

const isToday = (dayDate: string): boolean => dayDate === today()

// ── Sub-components ─────────────────────────────────────────────────────────────

function BlockCard({ block, onToggleDone }: { block: SessionBlock; onToggleDone: () => void }) {
  const s = SESSION_STYLES[block.session_type] ?? SESSION_STYLES.study
  return (
    <div className={`flex gap-3 rounded-lg p-3 ${s.bg} ${PRIORITY_BORDER[block.priority]} transition`}>
      <div className="shrink-0 pt-0.5">
        <span className={s.text}>{s.icon}</span>
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className={`text-xs font-bold uppercase tracking-wide ${s.text}`}>{s.label}</span>
          <span className="text-xs text-gray-400">{fmt12h(block.start_hour)} — {fmt12h(block.start_hour + block.duration_hours)}</span>
          {block.priority === 3 && <Flame size={12} className="text-red-500" aria-label="Critical weak area"/>}
          {block.priority === 2 && <AlertCircle size={12} className="text-amber-500" aria-label="Weak area"/>}
          {block.rescheduled && <span className="text-xs text-gray-400 italic">rescheduled</span>}
        </div>
        {block.topic ? (
          <p className="text-sm font-medium text-gray-900 dark:text-white truncate mt-0.5">{block.topic}</p>
        ) : null}
        {block.subject ? (
          <p className="text-xs text-gray-500 dark:text-gray-400">{block.subject}</p>
        ) : null}
      </div>
      <button
        onClick={onToggleDone}
        title={block.completed ? 'Mark incomplete' : 'Mark complete'}
        className="shrink-0 self-start mt-0.5"
      >
        <CheckCircle2
          size={18}
          className={block.completed ? 'text-green-500' : 'text-gray-300 dark:text-gray-600 hover:text-green-400 transition'}
        />
      </button>
    </div>
  )
}

function DayTimeline({ day, onToggleDone }: {
  day: DayPlan
  onToggleDone: (blockId: string) => void
}) {
  if (day.is_rest_day) {
    return (
      <div className="text-center py-8 text-gray-400 dark:text-gray-500">
        <Clock size={32} className="mx-auto mb-2 opacity-40" />
        <p className="font-medium">Rest Day</p>
        <p className="text-sm">Take a break — you've earned it.</p>
      </div>
    )
  }
  const done = day.blocks.filter((b) => b.completed).length
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-gray-500">{day.blocks.length} sessions · {day.total_hours}h</span>
        <span className="text-xs text-green-600 font-medium">{done}/{day.blocks.length} done</span>
      </div>
      {day.blocks.map((block) => (
        <BlockCard key={block.block_id} block={block} onToggleDone={() => onToggleDone(block.block_id)} />
      ))}
    </div>
  )
}

function WeekCard({ week, active, onClick }: { week: WeekPlan; active: boolean; onClick: () => void }) {
  const pct = weekProgress(week)
  const current = isCurrentWeek(week)
  return (
    <button
      onClick={onClick}
      className={`w-full text-left rounded-xl border p-4 transition ${
        active
          ? 'border-primary bg-primary/5 dark:bg-primary/10'
          : current
          ? 'border-amber-400 bg-amber-50 dark:bg-amber-900/20'
          : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-primary/40'
      }`}
    >
      <div className="flex items-center justify-between mb-2">
        <div>
          <span className={`text-xs font-bold uppercase tracking-wide ${current ? 'text-amber-600' : 'text-gray-500 dark:text-gray-400'}`}>
            {current ? '▶ Current — ' : ''}Week {week.week_number}
          </span>
          <p className="text-sm font-semibold text-gray-900 dark:text-white">{fmtDate(week.start_date)} – {fmtDate(week.end_date)}</p>
        </div>
        <ChevronRight size={16} className={`${active ? 'text-primary' : 'text-gray-400'}`} />
      </div>
      {week.theme && <p className="text-xs text-gray-500 dark:text-gray-400 mb-2 truncate">Focus: {week.theme}</p>}
      <div className="flex items-center gap-3">
        <div className="flex-1 h-1.5 rounded-full bg-gray-200 dark:bg-gray-600">
          <div
            className={`h-full rounded-full transition-all ${pct === 100 ? 'bg-green-500' : 'bg-primary'}`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className="text-xs text-gray-500 shrink-0">{pct}% · {week.total_hours}h</span>
      </div>
    </button>
  )
}

function DayGrid({ week, selectedDay, onSelectDay }: {
  week: WeekPlan
  selectedDay: string | null
  onSelectDay: (date: string) => void
}) {
  return (
    <div className="grid grid-cols-7 gap-1">
      {week.days.map((day) => {
        const sel = selectedDay === day.day_date
        const tod = isToday(day.day_date)
        const done = day.blocks.filter((b) => b.completed).length
        const total = day.blocks.length
        return (
          <button
            key={day.day_date}
            onClick={() => onSelectDay(day.day_date)}
            className={`flex flex-col items-center p-2 rounded-lg transition text-center ${
              sel
                ? 'bg-primary text-white shadow'
                : tod
                ? 'bg-amber-100 dark:bg-amber-900/30 border border-amber-400'
                : day.is_rest_day
                ? 'bg-gray-50 dark:bg-gray-700/50 text-gray-400'
                : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 hover:border-primary/40'
            }`}
          >
            <span className={`text-xs font-bold ${sel ? 'text-white/80' : 'text-gray-400 dark:text-gray-500'}`}>
              {day.day_of_week.slice(0, 3)}
            </span>
            <span className={`text-sm font-bold mt-0.5 ${sel ? 'text-white' : 'text-gray-900 dark:text-white'}`}>
              {new Date(day.day_date).getDate()}
            </span>
            {day.is_rest_day ? (
              <span className="text-xs mt-1 opacity-50">Rest</span>
            ) : (
              <span className={`text-xs mt-1 ${sel ? 'text-white/80' : done === total && total > 0 ? 'text-green-600' : 'text-gray-400'}`}>
                {done}/{total}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}

// ── No-plan views ──────────────────────────────────────────────────────────────

function GenerateView({ diagnosticDone, onGenerate, generating }: {
  diagnosticDone: boolean
  onGenerate: (examDate: string) => void
  generating: boolean
}) {
  const navigate = useNavigate()
  const [examDate, setExamDate] = useState('')

  if (!diagnosticDone) {
    return (
      <div className="max-w-md mx-auto text-center py-16 space-y-4">
        <AlertCircle size={40} className="text-amber-500 mx-auto" />
        <h2 className="text-lg font-bold text-gray-900 dark:text-white">Complete the diagnostic first</h2>
        <p className="text-gray-500 text-sm">Dabbu needs your diagnostic results to build a personalised study plan.</p>
        <button onClick={() => navigate('/diagnostic')}
          className="bg-primary text-white font-semibold px-6 py-2 rounded-xl hover:bg-primary/90 transition">
          Go to Diagnostic
        </button>
      </div>
    )
  }

  return (
    <div className="max-w-md mx-auto text-center py-12 space-y-5">
      <div className="w-16 h-16 rounded-2xl bg-violet-100 dark:bg-violet-900/30 flex items-center justify-center mx-auto">
        <Calendar size={32} className="text-violet-600 dark:text-violet-400" />
      </div>
      <h2 className="text-xl font-bold text-gray-900 dark:text-white">Build your study plan</h2>
      <p className="text-sm text-gray-500 dark:text-gray-400">
        Dabbu will create a day-by-day schedule tailored to your weak areas and exam timeline.
        NAGA reviews it before it goes live.
      </p>
      <div className="text-left space-y-1">
        <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
          Exam date <span className="text-gray-400 font-normal">(optional — helps Dabbu set the right pace)</span>
        </label>
        <input
          type="date"
          value={examDate}
          onChange={(e) => setExamDate(e.target.value)}
          min={new Date().toISOString().slice(0, 10)}
          className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary"
        />
      </div>
      <button
        onClick={() => onGenerate(examDate)}
        disabled={generating}
        className="w-full flex items-center justify-center gap-2 bg-primary hover:bg-primary/90 disabled:opacity-60 text-white font-semibold py-2.5 rounded-xl transition"
      >
        {generating ? <><Loader2 size={16} className="animate-spin" />Asking Dabbu…</> : 'Generate My Study Plan'}
      </button>
    </div>
  )
}

function ProposedView({ plan }: { plan: StudyPlan }) {
  return (
    <div className="max-w-md mx-auto text-center py-12 space-y-5">
      <div className="w-16 h-16 rounded-2xl bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center mx-auto">
        <Loader2 size={32} className="text-amber-600 dark:text-amber-400 animate-spin" />
      </div>
      <h2 className="text-xl font-bold text-gray-900 dark:text-white">Awaiting NAGA's approval</h2>
      <p className="text-sm text-gray-500 dark:text-gray-400">
        Dabbu has built your study plan. NAGA is reviewing it — you'll get a notification as soon as it's approved.
      </p>
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 text-left space-y-2">
        <Row label="Exam" value={plan.exam_target.toUpperCase().replace(/_/g, ' ')} />
        <Row label="Duration" value={`${plan.duration_months} months`} />
        <Row label="Total hours" value={`${plan.total_study_hours?.toFixed(0)}h`} />
        <Row label="Weak topics" value={`${plan.weak_topics.length} identified`} />
        {plan.exam_date && <Row label="Exam date" value={fmtDate(plan.exam_date)} />}
      </div>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-gray-500 dark:text-gray-400">{label}</span>
      <span className="font-medium text-gray-900 dark:text-white">{value}</span>
    </div>
  )
}

// ── Main page ──────────────────────────────────────────────────────────────────

export default function StudyPlanPage() {
  const student = useAuthStore((s) => s.student)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [activePlan, setActivePlan] = useState<StudyPlan | null>(null)
  const [proposedPlan, setProposedPlan] = useState<StudyPlan | null>(null)
  const [error, setError] = useState('')
  const [rediagMsg, setRediagMsg] = useState('')

  // Navigation state
  const [selectedWeekNum, setSelectedWeekNum] = useState<number | null>(null)
  const [selectedDay, setSelectedDay] = useState<string | null>(null)

  // Local completion tracking (client-side; persisted back via API in next iteration)
  const [completions, setCompletions] = useState<Set<string>>(new Set())

  useEffect(() => {
    loadPlans()
  }, [])

  const loadPlans = async () => {
    setLoading(true)
    try {
      const [activeRes, proposedRes] = await Promise.all([
        api.getDabbuActivePlan(),
        api.getDabbuProposedPlan(),
      ])
      const a: StudyPlan | null = activeRes.data.plan
      const p: StudyPlan | null = proposedRes.data.plan
      setActivePlan(a)
      setProposedPlan(p)

      // Auto-select current week
      if (a) {
        const t = today()
        const cur = a.weeks.find((w) => w.start_date <= t && t <= w.end_date)
        setSelectedWeekNum(cur?.week_number ?? a.weeks[0]?.week_number ?? 1)
        setSelectedDay(t)
      }

      // Check for re-diagnostic suggestion (background, non-blocking)
      if (a && student?.diagnostic_done) {
        api.checkProgress().then((res) => {
          if (res.data.suggested) setRediagMsg(res.data.reason ?? '')
        }).catch(() => {})
      }
    } catch {
      setError('Could not load your study plan.')
    }
    setLoading(false)
  }

  const handleGenerate = async (examDate: string) => {
    setGenerating(true)
    setError('')
    try {
      const res = await api.generateDabbuPlan(examDate || undefined)
      setProposedPlan(res.data.plan)
      if (res.data.rediagnostic_suggested) setRediagMsg(res.data.rediagnostic_suggested)
    } catch (e: any) {
      setError(e.response?.data?.detail ?? 'Failed to generate study plan.')
    }
    setGenerating(false)
  }

  const toggleDone = (blockId: string) => {
    setCompletions((prev) => {
      const next = new Set(prev)
      next.has(blockId) ? next.delete(blockId) : next.add(blockId)
      return next
    })
  }

  // Merge local completions into plan data
  const enrichPlan = (plan: StudyPlan): StudyPlan => ({
    ...plan,
    weeks: plan.weeks.map((w) => ({
      ...w,
      days: w.days.map((d) => ({
        ...d,
        blocks: d.blocks.map((b) => ({
          ...b,
          completed: completions.has(b.block_id) || b.completed,
        })),
      })),
    })),
  })

  if (loading) {
    return (
      <div className="flex items-center justify-center h-48">
        <Loader2 size={28} className="animate-spin text-primary" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-md mx-auto py-12 text-center">
        <p className="text-red-500 text-sm mb-4">{error}</p>
        <button onClick={loadPlans} className="text-primary text-sm underline">Try again</button>
      </div>
    )
  }

  // ── No plan yet ──
  if (!activePlan && !proposedPlan) {
    return (
      <div className="max-w-xl mx-auto">
        <h1 className="text-xl font-bold text-gray-900 dark:text-white mb-1">Study Plan</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">Dabbu builds your personalised day-by-day schedule.</p>
        <GenerateView
          diagnosticDone={!!student?.diagnostic_done}
          onGenerate={handleGenerate}
          generating={generating}
        />
      </div>
    )
  }

  // ── Proposed / awaiting NAGA ──
  if (!activePlan && proposedPlan) {
    return (
      <div className="max-w-xl mx-auto">
        <h1 className="text-xl font-bold text-gray-900 dark:text-white mb-1">Study Plan</h1>
        <ProposedView plan={proposedPlan} />
      </div>
    )
  }

  // ── Active plan — main view ──
  const plan = enrichPlan(activePlan!)
  const selectedWeek = plan.weeks.find((w) => w.week_number === selectedWeekNum) ?? plan.weeks[0]
  const selectedDayData = selectedWeek?.days.find((d) => d.day_date === selectedDay) ?? null

  const totalDays = Math.round(
    (new Date(plan.end_date).getTime() - new Date(plan.start_date).getTime()) / 86400000
  )
  const elapsedDays = Math.max(
    0,
    Math.round((Date.now() - new Date(plan.start_date).getTime()) / 86400000)
  )
  const overallPct = Math.min(100, Math.round((elapsedDays / totalDays) * 100))

  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-gray-900 dark:text-white">Study Plan</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {plan.exam_target.toUpperCase().replace(/_/g, ' ')} · {plan.duration_months} months · {plan.total_study_hours?.toFixed(0)}h total
          {plan.exam_date ? ` · Exam: ${fmtDate(plan.exam_date)}` : ''}
        </p>
      </div>

      {/* Re-diagnostic nudge */}
      {rediagMsg && (
        <div className="flex gap-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-xl p-4">
          <AlertCircle size={18} className="text-amber-600 shrink-0 mt-0.5" />
          <div className="flex-1 text-sm">
            <span className="font-semibold text-amber-800 dark:text-amber-300">Dabbu recommends a re-diagnostic · </span>
            <span className="text-amber-700 dark:text-amber-400">{rediagMsg}</span>
          </div>
          <button onClick={() => setRediagMsg('')} className="text-amber-500 hover:text-amber-700 text-lg leading-none">×</button>
        </div>
      )}

      {/* Overall progress bar */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex justify-between text-sm mb-2">
          <span className="text-gray-600 dark:text-gray-400">Overall progress</span>
          <span className="font-semibold text-gray-900 dark:text-white">{overallPct}%</span>
        </div>
        <div className="h-2 rounded-full bg-gray-200 dark:bg-gray-600">
          <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${overallPct}%` }} />
        </div>
        <div className="flex justify-between text-xs text-gray-400 mt-1">
          <span>{fmtDate(plan.start_date)}</span>
          <span>{fmtDate(plan.end_date)}</span>
        </div>
      </div>

      {/* Three-column layout: week list | day grid + timeline */}
      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-4">
        {/* Week list */}
        <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
          <h2 className="text-xs font-bold uppercase tracking-wide text-gray-500 dark:text-gray-400 px-1">
            {plan.weeks.length} Weeks
          </h2>
          {plan.weeks.map((w) => (
            <WeekCard
              key={w.week_number}
              week={w}
              active={w.week_number === selectedWeekNum}
              onClick={() => {
                setSelectedWeekNum(w.week_number)
                // auto-select today if it's in this week, else first day
                const t = today()
                const dayInWeek = w.days.find((d) => d.day_date === t)
                setSelectedDay(dayInWeek?.day_date ?? w.days[0]?.day_date ?? null)
              }}
            />
          ))}
        </div>

        {/* Day grid + timeline */}
        {selectedWeek && (
          <div className="space-y-4">
            {/* Week header */}
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-bold text-gray-900 dark:text-white">
                  Week {selectedWeek.week_number}
                  {selectedWeek.theme ? ` — ${selectedWeek.theme}` : ''}
                </h2>
                <p className="text-xs text-gray-500">{fmtDate(selectedWeek.start_date)} – {fmtDate(selectedWeek.end_date)} · {selectedWeek.total_hours}h</p>
              </div>
              <div className="flex gap-1">
                <button
                  onClick={() => setSelectedWeekNum((n) => Math.max(1, (n ?? 1) - 1))}
                  disabled={(selectedWeekNum ?? 1) <= 1}
                  className="p-1.5 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-30"
                ><ChevronLeft size={16} /></button>
                <button
                  onClick={() => setSelectedWeekNum((n) => Math.min(plan.weeks.length, (n ?? 1) + 1))}
                  disabled={(selectedWeekNum ?? 1) >= plan.weeks.length}
                  className="p-1.5 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-30"
                ><ChevronRight size={16} /></button>
              </div>
            </div>

            {/* Day selector grid */}
            <DayGrid
              week={selectedWeek}
              selectedDay={selectedDay}
              onSelectDay={setSelectedDay}
            />

            {/* Day timeline */}
            {selectedDayData && (
              <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
                <h3 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                  <Calendar size={16} className="text-primary" />
                  {fmtFullDate(selectedDayData.day_date)}
                  {isToday(selectedDayData.day_date) && (
                    <span className="bg-amber-100 text-amber-700 text-xs font-bold px-2 py-0.5 rounded-full">Today</span>
                  )}
                </h3>
                <DayTimeline
                  day={selectedDayData}
                  onToggleDone={toggleDone}
                />
              </div>
            )}
          </div>
        )}
      </div>

      {/* Weak topics summary */}
      {plan.weak_topics.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <h3 className="text-sm font-bold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
            <Flame size={14} className="text-red-500" /> Priority Topics (given extra slots)
          </h3>
          <div className="flex flex-wrap gap-2">
            {plan.weak_topics.map((t) => (
              <span key={t} className="text-xs bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 border border-red-200 dark:border-red-800 px-2 py-1 rounded-full">
                {t}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
