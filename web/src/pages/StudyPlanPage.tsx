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
  subtopic?: string
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
  const startLabel = fmt12h(block.start_hour)
  const endLabel   = fmt12h(block.start_hour + block.duration_hours)

  const isStudy = block.session_type === 'study' || block.session_type === 'revision'
  const isPractice = block.session_type === 'practice'
  const actionable = (isStudy || isPractice) && !!block.topic

  const notesHref = `/study?topic=${encodeURIComponent(block.subtopic || block.topic)}`
  const practiceParams = new URLSearchParams({ subject: block.subject, topic: block.topic })
  if (block.subtopic) practiceParams.set('subtopic', block.subtopic)
  const practiceHref = `/test?${practiceParams.toString()}`

  return (
    <div className="flex items-stretch gap-0 group">
      {/* Time column */}
      <div className="w-24 shrink-0 flex flex-col items-end pr-3 pt-2.5 pb-2.5">
        <span className="text-xs font-mono font-semibold text-gray-600 dark:text-gray-300 leading-tight">{startLabel}</span>
        <span className="text-xs font-mono text-gray-400 leading-tight">–{endLabel}</span>
        <span className="text-xs text-gray-400 mt-0.5">{block.duration_hours}h</span>
      </div>

      {/* Connector line */}
      <div className="flex flex-col items-center mr-3">
        <div className={`w-2.5 h-2.5 rounded-full border-2 mt-3 shrink-0 ${block.completed ? 'bg-green-500 border-green-500' : 'bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-500'}`} />
        <div className="flex-1 w-px bg-gray-200 dark:bg-gray-600 mt-0.5" />
      </div>

      {/* Session card */}
      <div className={`flex-1 mb-2 rounded-xl p-3 ${s.bg} ${PRIORITY_BORDER[block.priority]} transition`}>
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span className={`text-xs font-bold uppercase tracking-widest ${s.text}`}>{s.label}</span>
              {block.priority === 3 && <Flame size={11} className="text-red-500" aria-label="Critical weak area"/>}
              {block.priority === 2 && <AlertCircle size={11} className="text-amber-500" aria-label="Weak area"/>}
              {block.rescheduled && <span className="text-xs text-gray-400 italic">rescheduled</span>}
            </div>
            {/* Subtopic is the focus; topic + subject give context */}
            {(block.subtopic || block.topic) && (
              <p className="text-sm font-semibold text-gray-900 dark:text-white leading-tight">
                {block.subtopic || block.topic}
              </p>
            )}
            {block.subject && (
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                {block.subject}{block.subtopic && block.topic ? ` · ${block.topic}` : ''}
              </p>
            )}
            {/* Action links */}
            {actionable && (
              <div className="flex gap-3 mt-2">
                {isStudy && (
                  <a href={notesHref}
                    className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline">
                    <BookOpen size={12} /> Study notes
                  </a>
                )}
                {(isPractice || isStudy) && (
                  <a href={practiceHref}
                    className="inline-flex items-center gap-1 text-xs font-semibold text-fuchsia-600 dark:text-fuchsia-400 hover:underline">
                    <FlaskConical size={12} /> Practice
                  </a>
                )}
              </div>
            )}
          </div>
          <button
            onClick={onToggleDone}
            title={block.completed ? 'Mark incomplete' : 'Mark complete'}
            className="shrink-0 mt-0.5"
          >
            <CheckCircle2
              size={20}
              className={block.completed ? 'text-green-500' : 'text-gray-300 dark:text-gray-600 hover:text-green-400 transition'}
            />
          </button>
        </div>
      </div>
    </div>
  )
}

function DayTimeline({ day, onToggleDone }: {
  day: DayPlan
  onToggleDone: (blockId: string) => void
}) {
  if (day.is_rest_day) {
    return (
      <div className="text-center py-10 text-gray-400 dark:text-gray-500">
        <Clock size={36} className="mx-auto mb-2 opacity-30" />
        <p className="font-semibold text-gray-500 dark:text-gray-400">Rest Day</p>
        <p className="text-sm mt-1">Take a break — you've earned it.</p>
      </div>
    )
  }

  const done = day.blocks.filter((b) => b.completed).length
  const sorted = [...day.blocks].sort((a, b) => a.start_hour - b.start_hour)

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between px-1 mb-3">
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {day.blocks.length} sessions · {day.total_hours}h
          </span>
          <div className="flex gap-1">
            {sorted.map((b) => {
              const s = SESSION_STYLES[b.session_type] ?? SESSION_STYLES.study
              return (
                <span
                  key={b.block_id}
                  title={`${fmt12h(b.start_hour)} ${s.label}`}
                  className={`inline-block w-3 h-3 rounded-sm ${TYPE_BG[b.session_type] ?? 'bg-blue-600'} opacity-80`}
                />
              )
            })}
          </div>
        </div>
        <span className={`text-xs font-semibold ${done === day.blocks.length ? 'text-green-600' : 'text-gray-400'}`}>
          {done}/{day.blocks.length} done
        </span>
      </div>

      {/* Timeline */}
      <div className="relative">
        {sorted.map((block) => (
          <BlockCard key={block.block_id} block={block} onToggleDone={() => onToggleDone(block.block_id)} />
        ))}
      </div>
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
  // Show the full plan with a "pending approval" banner — don't hide it behind a spinner
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-300 dark:border-amber-700 rounded-xl px-4 py-3">
        <Loader2 size={16} className="text-amber-600 animate-spin shrink-0" />
        <div className="text-sm">
          <span className="font-semibold text-amber-800 dark:text-amber-200">Awaiting NAGA's review · </span>
          <span className="text-amber-700 dark:text-amber-300">
            Dabbu built this plan. NAGA will approve or adjust it before it goes live. You can preview it below.
          </span>
        </div>
      </div>
      <PlanFullView plan={plan} readOnly />
    </div>
  )
}

// ── Year-at-a-Glance overview ──────────────────────────────────────────────────

// Mirrors _DAILY_SLOTS in dabbu_agent.py — 5 slots per study day
const DAILY_SLOT_HOURS = [7, 9, 11, 14, 16]

const TYPE_BG: Record<string, string> = {
  study:    'bg-blue-600',
  practice: 'bg-fuchsia-600',
  mock:     'bg-red-500',
  revision: 'bg-amber-500',
  rest:     'bg-gray-200 dark:bg-gray-700',
}

const TYPE_LABEL: Record<string, string> = {
  study: 'Study (7–9, 9–11 AM)',
  practice: 'Practice (11 AM–1 PM)',
  revision: 'Revision (2–4 PM)',
  mock: 'Mock Test (4–6 PM)',
}

function YearOverview({ plan, onSelectDay }: { plan: StudyPlan; onSelectDay: (date: string) => void }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
      <h3 className="text-sm font-bold text-gray-900 dark:text-white mb-1 flex items-center gap-2">
        <Calendar size={14} className="text-primary" />
        {plan.weeks.length}-week plan at a glance
      </h3>
      <p className="text-xs text-gray-400 dark:text-gray-500 mb-3">
        Each column = one day. 5 coloured bars = 5 sessions (7 AM → 6 PM). Click any day to see its schedule.
      </p>

      {/* Day grid: grouped by week with a gap between weeks */}
      <div className="flex flex-wrap" style={{ gap: '2px 1px' }}>
        {plan.weeks.flatMap((w, wi) =>
          w.days.map((d, di) => {
            const blockBySlot = DAILY_SLOT_HOURS.map(h =>
              d.blocks.find(b => b.start_hour === h)
            )
            return (
              <button
                key={d.day_date}
                onClick={() => onSelectDay(d.day_date)}
                title={`${d.day_of_week} ${d.day_date}${d.is_rest_day ? ' — Rest' : ` — ${d.blocks.length} sessions`}`}
                className={`flex flex-col rounded-sm hover:ring-2 hover:ring-primary/50 focus:outline-none${di === 0 && wi > 0 ? ' ml-2' : ''}`}
                style={{ gap: '1px' }}
              >
                {d.is_rest_day ? (
                  <div className="w-2.5 bg-gray-200 dark:bg-gray-700 rounded-sm opacity-40" style={{ height: 17 }} />
                ) : (
                  blockBySlot.map((block, si) => (
                    <div
                      key={si}
                      className={`w-2.5 rounded-sm ${block ? (TYPE_BG[block.session_type] ?? TYPE_BG.study) : 'bg-gray-200 dark:bg-gray-600 opacity-20'} ${block?.completed ? 'opacity-100' : 'opacity-75'}`}
                      style={{ height: 3 }}
                    />
                  ))
                )}
              </button>
            )
          })
        )}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-3 text-xs text-gray-500 dark:text-gray-400">
        {Object.entries(TYPE_LABEL).map(([k, label]) => (
          <span key={k} className="flex items-center gap-1.5">
            <span className={`inline-block rounded-sm ${TYPE_BG[k]}`} style={{ width: 10, height: 6 }} />
            {label}
          </span>
        ))}
        <span className="ml-auto text-gray-400">{plan.total_study_hours?.toFixed(0)}h · {plan.weeks.length} wks</span>
      </div>
    </div>
  )
}

// ── Shared full plan view (used for both active and proposed) ──────────────────

function PlanFullView({ plan: rawPlan, readOnly = false }: { plan: StudyPlan; readOnly?: boolean }) {
  const [completions, setCompletions] = useState<Set<string>>(new Set())
  const [selectedWeekNum, setSelectedWeekNum] = useState<number | null>(() => {
    const t = today()
    const cur = rawPlan.weeks.find((w) => w.start_date <= t && t <= w.end_date)
    return cur?.week_number ?? rawPlan.weeks[0]?.week_number ?? 1
  })
  const [selectedDay, setSelectedDay] = useState<string | null>(() => {
    const t = today()
    const cur = rawPlan.weeks.find((w) => w.start_date <= t && t <= w.end_date)
    if (cur) {
      const todayEntry = cur.days.find((d) => d.day_date === t)
      // If today is a rest day, pick the next study day in this week
      if (todayEntry && !todayEntry.is_rest_day) return t
      return cur.days.find((d) => !d.is_rest_day)?.day_date ?? t
    }
    return rawPlan.weeks[0]?.days.find((d) => !d.is_rest_day)?.day_date
      ?? rawPlan.weeks[0]?.days[0]?.day_date ?? null
  })

  const enrichPlan = (p: StudyPlan): StudyPlan => ({
    ...p,
    weeks: p.weeks.map((w) => ({
      ...w,
      days: w.days.map((d) => ({
        ...d,
        blocks: d.blocks.map((b) => ({ ...b, completed: completions.has(b.block_id) || b.completed })),
      })),
    })),
  })

  const plan = enrichPlan(rawPlan)
  const selectedWeek = plan.weeks.find((w) => w.week_number === selectedWeekNum) ?? plan.weeks[0]
  const selectedDayData = selectedWeek?.days.find((d) => d.day_date === selectedDay) ?? null
  const totalDays = Math.round((new Date(plan.end_date).getTime() - new Date(plan.start_date).getTime()) / 86400000)
  const elapsedDays = Math.max(0, Math.round((Date.now() - new Date(plan.start_date).getTime()) / 86400000))
  const overallPct = Math.min(100, Math.round((elapsedDays / totalDays) * 100))

  const toggleDone = (blockId: string) => {
    if (readOnly) return
    setCompletions((prev) => { const n = new Set(prev); n.has(blockId) ? n.delete(blockId) : n.add(blockId); return n })
  }

  return (
    <div className="space-y-4">
      {/* Plan summary */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex flex-wrap items-center gap-4 mb-3">
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400">Exam</p>
            <p className="text-sm font-bold text-gray-900 dark:text-white">{plan.exam_target.toUpperCase().replace(/_/g, ' ')}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400">Duration</p>
            <p className="text-sm font-bold text-gray-900 dark:text-white">{plan.duration_months} months · {plan.weeks.length} weeks</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400">Total study</p>
            <p className="text-sm font-bold text-gray-900 dark:text-white">{plan.total_study_hours?.toFixed(0)}h</p>
          </div>
          {plan.exam_date && (
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">Exam date</p>
              <p className="text-sm font-bold text-gray-900 dark:text-white">{fmtDate(plan.exam_date)}</p>
            </div>
          )}
        </div>
        <div className="flex justify-between text-xs text-gray-400 mb-1">
          <span>Overall progress</span><span>{overallPct}%</span>
        </div>
        <div className="h-2 rounded-full bg-gray-200 dark:bg-gray-600">
          <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${overallPct}%` }} />
        </div>
        <div className="flex justify-between text-xs text-gray-400 mt-1">
          <span>{fmtDate(plan.start_date)}</span>
          <span>{fmtDate(plan.end_date)}</span>
        </div>
      </div>

      {/* Year at a glance */}
      <YearOverview plan={plan} onSelectDay={(date) => {
        const week = plan.weeks.find((w) => w.days.some((d) => d.day_date === date))
        if (week) setSelectedWeekNum(week.week_number)
        setSelectedDay(date)
        // Scroll to the day detail section
        setTimeout(() => document.getElementById('day-detail')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50)
      }} />

      {/* Week + day navigation */}
      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-4">
        <div className="space-y-2 max-h-[560px] overflow-y-auto pr-1">
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
                const t = today()
                const todayInWeek = w.days.find((d) => d.day_date === t && !d.is_rest_day)
                const firstStudyDay = w.days.find((d) => !d.is_rest_day)
                setSelectedDay(todayInWeek?.day_date ?? firstStudyDay?.day_date ?? w.days[0]?.day_date ?? null)
              }}
            />
          ))}
        </div>

        {selectedWeek && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-bold text-gray-900 dark:text-white">
                  Week {selectedWeek.week_number}{selectedWeek.theme ? ` — ${selectedWeek.theme}` : ''}
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
            <DayGrid week={selectedWeek} selectedDay={selectedDay} onSelectDay={setSelectedDay} />
            {selectedDayData && (
              <div id="day-detail" className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
                <h3 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                  <Calendar size={16} className="text-primary" />
                  {fmtFullDate(selectedDayData.day_date)}
                  {isToday(selectedDayData.day_date) && (
                    <span className="bg-amber-100 text-amber-700 text-xs font-bold px-2 py-0.5 rounded-full">Today</span>
                  )}
                </h3>
                <DayTimeline day={selectedDayData} onToggleDone={toggleDone} />
              </div>
            )}
          </div>
        )}
      </div>

      {plan.weak_topics.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <h3 className="text-sm font-bold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
            <Flame size={14} className="text-red-500" /> Priority topics (extra study slots)
          </h3>
          <div className="flex flex-wrap gap-2">
            {plan.weak_topics.map((t) => (
              <span key={t} className="text-xs bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 border border-red-200 dark:border-red-800 px-2 py-1 rounded-full">{t}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Main page ──────────────────────────────────────────────────────────────────

export default function StudyPlanPage() {
  const student = useAuthStore((s) => s.student)
  const updateStudent = useAuthStore((s) => s.updateStudent)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [activePlan, setActivePlan] = useState<StudyPlan | null>(null)
  const [proposedPlan, setProposedPlan] = useState<StudyPlan | null>(null)
  const [error, setError] = useState('')
  const [rediagMsg, setRediagMsg] = useState('')

  useEffect(() => { loadPlans() }, [])

  const loadPlans = async () => {
    setLoading(true)
    setError('')
    try {
      // Re-fetch student profile first to get fresh diagnostic_done status
      // (localStorage cache may be stale if diagnostic was done in another session)
      const [activeRes, proposedRes, studentRes] = await Promise.all([
        api.getDabbuActivePlan(),
        api.getDabbuProposedPlan(),
        student?.user_id ? api.getStudent(student.user_id).catch(() => null) : Promise.resolve(null),
      ])
      if (studentRes?.data) {
        updateStudent(studentRes.data)
      }
      setActivePlan(activeRes.data.plan ?? null)
      setProposedPlan(proposedRes.data.plan ?? null)
      if (activeRes.data.plan) {
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

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-48 gap-3">
        <Loader2 size={28} className="animate-spin text-primary" />
        <p className="text-sm text-gray-500 dark:text-gray-400">Loading your study plan…</p>
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
      <div className="space-y-4">
        <h1 className="text-xl font-bold text-gray-900 dark:text-white">Study Plan</h1>
        <ProposedView plan={proposedPlan} />
      </div>
    )
  }

  // ── Active plan ──
  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">Study Plan</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {activePlan!.exam_target.toUpperCase().replace(/_/g, ' ')} · {activePlan!.duration_months} months
            {activePlan!.exam_date ? ` · Exam: ${fmtDate(activePlan!.exam_date)}` : ''}
          </p>
        </div>
      </div>

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

      <PlanFullView plan={activePlan!} />
    </div>
  )
}
