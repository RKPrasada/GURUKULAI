import { useEffect, useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, LineChart, Line,
} from 'recharts'
import {
  Flame, TrendingUp, Target, Award, Brain, Calendar, Clock,
  CheckSquare, AlertTriangle, ChevronDown, ChevronUp, RefreshCw,
  BookOpen, Zap,
} from 'lucide-react'
import api from '@/services/api'

// ── Types ──────────────────────────────────────────────────────────────────────

interface TopicData {
  subject: string
  topic: string
  score_pct: number
  attempts: number
  initial_score_pct: number
  target_score_pct: number
  improvement: number
  ease_factor: number
  interval_days: number
  next_review_date: string
  days_until_review: number
  overdue: boolean
  ease_label: string
}

interface Session {
  session_id: string
  date: string
  datetime: string
  session_type: string
  subject: string
  topic: string
  correct: number
  total: number
  score_pct: number
  duration_mins: number | null
}

interface CalendarDay {
  date: string
  count: number
}

interface PlanStats {
  has_plan: boolean
  completed: number
  total: number
  pct: number
  by_type?: Record<string, { done: number; total: number }>
}

interface ProgressData {
  student_id: string
  generated_at: string
  summary: {
    avg_score_pct: number
    topics_on_target: number
    topics_total: number
    overdue_reviews: number
    total_sessions: number
    streak_days: number
    plan_completion_pct: number
  }
  current_topics: TopicData[]
  topic_history: Record<string, Array<{ date: string; week: number; label: string; score_pct: number }>>
  recent_sessions: Session[]
  subject_sessions: Record<string, number>
  streak_calendar: CalendarDay[]
  plan_stats: PlanStats
  snapshots_count: number
}

// ── Helpers ────────────────────────────────────────────────────────────────────

const pct = (v: number) => `${(v * 100).toFixed(0)}%`
const scoreBg = (s: number) =>
  s >= 0.8 ? 'bg-emerald-500' : s >= 0.6 ? 'bg-yellow-400' : s >= 0.4 ? 'bg-orange-400' : 'bg-red-500'
const scoreText = (s: number) =>
  s >= 0.8 ? 'text-emerald-600' : s >= 0.6 ? 'text-yellow-600' : s >= 0.4 ? 'text-orange-500' : 'text-red-600'
const easeColor = (label: string) =>
  label === 'Hard' ? 'text-red-500' : label === 'Moderate' ? 'text-orange-400' : label === 'Good' ? 'text-blue-500' : 'text-emerald-500'

// ── Streak heatmap ─────────────────────────────────────────────────────────────

function StreakHeatmap({ calendar }: { calendar: CalendarDay[] }) {
  const weeks: CalendarDay[][] = []
  let week: CalendarDay[] = []
  for (const day of calendar) {
    week.push(day)
    if (week.length === 7) { weeks.push(week); week = [] }
  }
  if (week.length) weeks.push(week)

  const cellColor = (count: number) => {
    if (count === 0) return 'bg-gray-100 dark:bg-gray-700'
    if (count === 1) return 'bg-primary/30'
    if (count <= 3) return 'bg-primary/60'
    return 'bg-primary'
  }

  return (
    <div>
      <div className="flex gap-1 flex-wrap">
        {weeks.map((wk, wi) => (
          <div key={wi} className="flex flex-col gap-1">
            {wk.map((day) => (
              <div
                key={day.date}
                title={`${day.date}: ${day.count} session${day.count !== 1 ? 's' : ''}`}
                className={`w-3 h-3 rounded-sm ${cellColor(day.count)}`}
              />
            ))}
          </div>
        ))}
      </div>
      <div className="flex items-center gap-1.5 mt-2 text-xs text-gray-400">
        <span>Less</span>
        {['bg-gray-100 dark:bg-gray-700', 'bg-primary/30', 'bg-primary/60', 'bg-primary'].map((c, i) => (
          <div key={i} className={`w-3 h-3 rounded-sm ${c}`} />
        ))}
        <span>More</span>
      </div>
    </div>
  )
}

// ── Grouped bar chart: initial / current / target ──────────────────────────────

function TripleBarChart({ topics }: { topics: TopicData[] }) {
  const data = topics.map((t) => ({
    name: t.topic.length > 14 ? t.topic.slice(0, 13) + '…' : t.topic,
    Initial: +(t.initial_score_pct * 100).toFixed(1),
    Current: +(t.score_pct * 100).toFixed(1),
    Target: 80,
  }))

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} margin={{ top: 4, right: 8, left: -8, bottom: 60 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" angle={-40} textAnchor="end" interval={0} tick={{ fontSize: 11 }} />
        <YAxis domain={[0, 100]} unit="%" tick={{ fontSize: 11 }} />
        <Tooltip formatter={(v: number) => `${v}%`} />
        <Legend verticalAlign="top" height={24} />
        <Bar dataKey="Initial" fill="#94a3b8" radius={[3, 3, 0, 0]} />
        <Bar dataKey="Current" fill="#5C35CC" radius={[3, 3, 0, 0]} />
        <Bar dataKey="Target" fill="#10b981" radius={[3, 3, 0, 0]} opacity={0.4} />
      </BarChart>
    </ResponsiveContainer>
  )
}

// ── Topic history line chart ───────────────────────────────────────────────────

function TopicTrendChart({ history }: { history: Array<{ date: string; score_pct: number }> }) {
  const data = history.map((h) => ({
    date: h.date.slice(5),
    score: +(h.score_pct * 100).toFixed(1),
  }))
  return (
    <ResponsiveContainer width="100%" height={120}>
      <LineChart data={data} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" tick={{ fontSize: 10 }} />
        <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} />
        <Tooltip formatter={(v: number) => `${v}%`} />
        <Line type="monotone" dataKey="score" stroke="#5C35CC" strokeWidth={2} dot={{ r: 3 }} />
      </LineChart>
    </ResponsiveContainer>
  )
}

// ── SM-2 table ─────────────────────────────────────────────────────────────────

function SM2Card({ topic }: { topic: TopicData }) {
  return (
    <div className={`rounded-xl border p-3 text-sm ${
      topic.overdue
        ? 'border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-700'
        : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800'
    }`}>
      <div className="flex justify-between items-start mb-1">
        <div>
          <span className="font-semibold text-gray-900 dark:text-white text-sm">{topic.topic}</span>
          <span className="text-xs text-gray-400 ml-1">· {topic.subject}</span>
        </div>
        {topic.overdue && (
          <span className="text-xs bg-red-100 text-red-600 dark:bg-red-900/40 dark:text-red-400 font-bold px-2 py-0.5 rounded-full">
            OVERDUE {Math.abs(topic.days_until_review)}d
          </span>
        )}
        {!topic.overdue && (
          <span className="text-xs text-gray-400">
            Review in {topic.days_until_review}d
          </span>
        )}
      </div>
      <div className="grid grid-cols-3 gap-2 mt-2 text-xs">
        <div>
          <p className="text-gray-400">Ease</p>
          <p className={`font-bold ${easeColor(topic.ease_label)}`}>{topic.ease_label}</p>
          <p className="text-gray-300 text-[10px]">{topic.ease_factor.toFixed(2)}</p>
        </div>
        <div>
          <p className="text-gray-400">Interval</p>
          <p className="font-bold text-gray-700 dark:text-gray-200">{topic.interval_days}d</p>
        </div>
        <div>
          <p className="text-gray-400">Next review</p>
          <p className="font-bold text-gray-700 dark:text-gray-200">{topic.next_review_date}</p>
        </div>
      </div>
    </div>
  )
}

// ── Plan completion panel ──────────────────────────────────────────────────────

function PlanCompletionPanel({ stats }: { stats: PlanStats }) {
  if (!stats.has_plan) {
    return (
      <div className="text-sm text-gray-400">
        No active study plan yet.{' '}
        <Link to="/study-plan" className="text-primary hover:underline font-medium">Generate one →</Link>
      </div>
    )
  }

  const TYPE_COLORS: Record<string, string> = {
    STUDY: 'bg-blue-500',
    PRACTICE: 'bg-purple-500',
    MOCK: 'bg-red-500',
    REVISION: 'bg-amber-500',
    REST: 'bg-gray-300',
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
          {stats.completed} / {stats.total} blocks complete
        </span>
        <span className={`text-sm font-bold ${stats.pct >= 70 ? 'text-emerald-600' : 'text-amber-600'}`}>
          {stats.pct.toFixed(0)}%
        </span>
      </div>
      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
        <div
          className={`h-3 rounded-full transition-all ${stats.pct >= 70 ? 'bg-emerald-500' : 'bg-amber-500'}`}
          style={{ width: `${Math.min(stats.pct, 100)}%` }}
        />
      </div>
      {stats.by_type && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {Object.entries(stats.by_type)
            .filter(([k]) => k !== 'REST')
            .map(([type, counts]) => (
              <div key={type} className="bg-gray-50 dark:bg-gray-700 rounded-lg p-2 text-center">
                <div className={`h-1.5 rounded-full mb-1.5 ${TYPE_COLORS[type] ?? 'bg-gray-400'}`}
                  style={{ width: `${counts.total ? (counts.done / counts.total) * 100 : 0}%` }} />
                <p className="text-xs text-gray-400 uppercase tracking-wide">{type}</p>
                <p className="text-sm font-bold text-gray-700 dark:text-gray-200">
                  {counts.done}/{counts.total}
                </p>
              </div>
            ))}
        </div>
      )}
    </div>
  )
}

// ── Main page ──────────────────────────────────────────────────────────────────

export default function ProgressPage() {
  const [data, setData] = useState<ProgressData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [analyzing, setAnalyzing] = useState(false)
  const [analyzeResult, setAnalyzeResult] = useState<string>('')
  const [expandedTopic, setExpandedTopic] = useState<string | null>(null)
  const [activeSection, setActiveSection] = useState<'overview' | 'sm2' | 'sessions' | 'plan'>('overview')

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await api.getProgress()
      setData(res.data)
    } catch {
      setError('Could not load progress data. Make sure you have completed at least one diagnostic or practice session.')
    }
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const overdueTopics = useMemo(
    () => data?.current_topics.filter((t) => t.overdue) ?? [],
    [data],
  )

  const handleDabbuAnalyze = async () => {
    setAnalyzing(true)
    setAnalyzeResult('')
    try {
      const res = await api.triggerDabbuAnalysis()
      setAnalyzeResult(res.data.message)
    } catch {
      setAnalyzeResult('Analysis failed — try again shortly.')
    }
    setAnalyzing(false)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[40vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-yellow-900 dark:text-yellow-100 mb-2">No Progress Data Yet</h2>
        <p className="text-yellow-800 dark:text-yellow-200 mb-4">{error || 'Complete a diagnostic or practice test to start tracking.'}</p>
        <Link to="/diagnostic" className="inline-block bg-primary text-white font-semibold px-4 py-2 rounded-lg text-sm hover:bg-primary/90 transition">
          Start Diagnostic →
        </Link>
      </div>
    )
  }

  const { summary, current_topics, recent_sessions, streak_calendar, plan_stats, topic_history } = data

  // Sort topics: critical first, then by improvement ascending (least improved shown first)
  const sortedTopics = [...current_topics].sort((a, b) => a.score_pct - b.score_pct)

  return (
    <div className="space-y-6">

      {/* ── Header + Dabbu button ── */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">My Progress</h1>
        <div className="flex items-center gap-2">
          <button onClick={load} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg" title="Refresh">
            <RefreshCw size={16} className="text-gray-500" />
          </button>
          <button
            onClick={handleDabbuAnalyze}
            disabled={analyzing}
            className="flex items-center gap-2 bg-primary text-white text-sm font-semibold px-4 py-2 rounded-lg hover:bg-primary/90 disabled:opacity-50 transition"
          >
            <Zap size={14} />
            {analyzing ? 'Analysing…' : 'Ask Dabbu to Review'}
          </button>
        </div>
      </div>

      {analyzeResult && (
        <div className="bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-700 rounded-xl px-4 py-3 text-sm text-indigo-800 dark:text-indigo-200">
          <strong>Dabbu:</strong> {analyzeResult}
        </div>
      )}

      {/* ── Summary stat cards ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard icon={Award} label="Total Sessions" value={summary.total_sessions} sub="practice + mock" color="blue" />
        <StatCard icon={TrendingUp} label="Avg Accuracy" value={pct(summary.avg_score_pct)} sub={`${summary.topics_on_target}/${summary.topics_total} at target`} color="purple" />
        <StatCard icon={Flame} label="Study Streak" value={`${summary.streak_days}d`} sub="consecutive days" color="orange" />
        <StatCard icon={Brain} label="SM-2 Overdue" value={summary.overdue_reviews} sub="reviews pending" color={summary.overdue_reviews > 0 ? 'red' : 'green'} />
      </div>

      {/* ── Overdue SM-2 alert ── */}
      {overdueTopics.length > 0 && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-xl p-4 flex gap-3">
          <AlertTriangle size={18} className="text-red-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-red-700 dark:text-red-300 mb-1">
              {overdueTopics.length} review{overdueTopics.length > 1 ? 's' : ''} overdue
            </p>
            <p className="text-xs text-red-600 dark:text-red-400">
              {overdueTopics.map((t) => t.topic).join(', ')} — practice these today to prevent forgetting.
            </p>
            <Link to="/test" className="inline-block mt-2 text-xs text-red-700 dark:text-red-300 font-semibold underline">
              Go to Practice Test →
            </Link>
          </div>
        </div>
      )}

      {/* ── Section tabs ── */}
      <div className="flex gap-1 bg-gray-100 dark:bg-gray-800 rounded-xl p-1 w-fit flex-wrap">
        {([
          ['overview', BookOpen, 'Overview'],
          ['sm2', Brain, 'SM-2 Reviews'],
          ['sessions', Clock, 'Session History'],
          ['plan', CheckSquare, 'Study Plan'],
        ] as const).map(([key, Icon, label]) => (
          <button
            key={key}
            onClick={() => setActiveSection(key)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
              activeSection === key
                ? 'bg-white dark:bg-gray-700 text-primary shadow-sm'
                : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            <Icon size={14} /> {label}
          </button>
        ))}
      </div>

      {/* ── Overview section ── */}
      {activeSection === 'overview' && (
        <div className="space-y-6">

          {/* Triple bar chart */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-5">
            <h2 className="text-base font-bold text-gray-900 dark:text-white mb-1">
              Initial → Current → Target (80%)
            </h2>
            <p className="text-xs text-gray-400 mb-4">Grouped by topic. Green bars = 80% target benchmark.</p>
            {current_topics.length > 0 ? (
              <TripleBarChart topics={sortedTopics} />
            ) : (
              <p className="text-sm text-gray-400">No topic data yet.</p>
            )}
          </div>

          {/* Streak calendar */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-5">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-base font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <Calendar size={16} /> Study Activity (last 60 days)
              </h2>
              <span className="text-sm font-semibold text-orange-500 flex items-center gap-1">
                <Flame size={14} /> {summary.streak_days} day streak
              </span>
            </div>
            <StreakHeatmap calendar={streak_calendar} />
          </div>

          {/* Topic cards with expandable history */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-5">
            <h2 className="text-base font-bold text-gray-900 dark:text-white mb-4">
              Topic-by-topic Analysis
            </h2>
            <div className="space-y-3">
              {sortedTopics.map((t) => {
                const key = `${t.subject}::${t.topic}`
                const hist = topic_history[key] ?? []
                const isOpen = expandedTopic === key
                return (
                  <div key={key} className="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
                    <button
                      className="w-full flex items-center justify-between p-3 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition"
                      onClick={() => setExpandedTopic(isOpen ? null : key)}
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="text-left min-w-0">
                          <p className="font-semibold text-gray-900 dark:text-white text-sm truncate">{t.topic}</p>
                          <p className="text-xs text-gray-400">{t.subject}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3 flex-shrink-0">
                        {/* mini progress bar */}
                        <div className="hidden sm:flex items-center gap-2">
                          <span className="text-xs text-gray-400">
                            {pct(t.initial_score_pct)} →
                          </span>
                          <div className="w-24 bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                            <div className={`h-2 rounded-full ${scoreBg(t.score_pct)}`}
                              style={{ width: `${t.score_pct * 100}%` }} />
                          </div>
                          <span className={`text-sm font-bold w-10 text-right ${scoreText(t.score_pct)}`}>
                            {pct(t.score_pct)}
                          </span>
                        </div>
                        {t.improvement > 0.01 && (
                          <span className="text-xs text-emerald-600 font-semibold">
                            +{pct(t.improvement)}
                          </span>
                        )}
                        {t.improvement < -0.01 && (
                          <span className="text-xs text-red-500 font-semibold">
                            {pct(t.improvement)}
                          </span>
                        )}
                        {isOpen ? <ChevronUp size={14} className="text-gray-400" /> : <ChevronDown size={14} className="text-gray-400" />}
                      </div>
                    </button>
                    {isOpen && (
                      <div className="border-t border-gray-100 dark:border-gray-700 p-4 space-y-3 bg-gray-50 dark:bg-gray-700/30">
                        <div className="grid grid-cols-3 gap-3 text-xs">
                          <div>
                            <p className="text-gray-400">Initial</p>
                            <p className={`font-bold text-base ${scoreText(t.initial_score_pct)}`}>{pct(t.initial_score_pct)}</p>
                          </div>
                          <div>
                            <p className="text-gray-400">Current</p>
                            <p className={`font-bold text-base ${scoreText(t.score_pct)}`}>{pct(t.score_pct)}</p>
                          </div>
                          <div>
                            <p className="text-gray-400">Attempts</p>
                            <p className="font-bold text-base text-gray-700 dark:text-gray-200">{t.attempts}</p>
                          </div>
                        </div>
                        <div className="grid grid-cols-3 gap-3 text-xs">
                          <div>
                            <p className="text-gray-400">SM-2 Ease</p>
                            <p className={`font-semibold ${easeColor(t.ease_label)}`}>{t.ease_label} ({t.ease_factor.toFixed(2)})</p>
                          </div>
                          <div>
                            <p className="text-gray-400">Interval</p>
                            <p className="font-semibold text-gray-700 dark:text-gray-200">{t.interval_days} days</p>
                          </div>
                          <div>
                            <p className="text-gray-400">Next review</p>
                            <p className={`font-semibold ${t.overdue ? 'text-red-500' : 'text-gray-700 dark:text-gray-200'}`}>
                              {t.overdue ? `Overdue ${Math.abs(t.days_until_review)}d` : `In ${t.days_until_review}d`}
                            </p>
                          </div>
                        </div>
                        {hist.length >= 2 && (
                          <div>
                            <p className="text-xs text-gray-400 mb-1">Score trend</p>
                            <TopicTrendChart history={hist} />
                          </div>
                        )}
                        <Link
                          to={`/test?subject=${encodeURIComponent(t.subject)}&topic=${encodeURIComponent(t.topic)}`}
                          className="inline-block text-xs bg-primary/10 hover:bg-primary/20 text-primary font-semibold px-3 py-1.5 rounded-lg transition"
                        >
                          Practice this topic →
                        </Link>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}

      {/* ── SM-2 Reviews section ── */}
      {activeSection === 'sm2' && (
        <div className="space-y-4">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            SM-2 spaced repetition schedules your reviews so you study each topic at the optimal interval.
            <strong className="text-gray-700 dark:text-gray-200"> Ease factor</strong> below 1.8 = struggling; above 2.8 = confident.
          </p>
          {overdueTopics.length > 0 && (
            <div>
              <h3 className="text-sm font-bold text-red-600 dark:text-red-400 mb-2 flex items-center gap-1">
                <AlertTriangle size={14} /> Overdue reviews ({overdueTopics.length})
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {overdueTopics.map((t) => <SM2Card key={`${t.subject}::${t.topic}`} topic={t} />)}
              </div>
            </div>
          )}
          <div>
            <h3 className="text-sm font-bold text-gray-700 dark:text-gray-300 mb-2">All topics</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {sortedTopics.map((t) => <SM2Card key={`${t.subject}::${t.topic}`} topic={t} />)}
            </div>
          </div>
        </div>
      )}

      {/* ── Session history section ── */}
      {activeSection === 'sessions' && (
        <div className="space-y-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-5">
            <h2 className="text-base font-bold text-gray-900 dark:text-white mb-4">Recent Sessions</h2>
            {recent_sessions.length === 0 ? (
              <p className="text-sm text-gray-400">No sessions logged yet.</p>
            ) : (
              <div className="space-y-2">
                {recent_sessions.map((s) => (
                  <div key={s.session_id}
                    className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg text-sm">
                    <div>
                      <span className="font-semibold text-gray-900 dark:text-white">{s.topic}</span>
                      <span className="text-gray-400 ml-1.5 text-xs">· {s.subject}</span>
                      <span className={`ml-2 text-xs px-1.5 py-0.5 rounded-full font-medium ${
                        s.session_type === 'practice' ? 'bg-purple-100 text-purple-600' : 'bg-blue-100 text-blue-600'
                      }`}>{s.session_type}</span>
                    </div>
                    <div className="flex items-center gap-3 flex-shrink-0 text-xs text-gray-500">
                      <span>{s.date}</span>
                      {s.duration_mins != null && <span>{s.duration_mins}min</span>}
                      <span className={`font-bold ${scoreText(s.score_pct)}`}>
                        {s.correct}/{s.total} ({pct(s.score_pct)})
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
          {Object.keys(data.subject_sessions).length > 0 && (
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-5">
              <h2 className="text-base font-bold text-gray-900 dark:text-white mb-3">Sessions by Subject</h2>
              <div className="space-y-2">
                {Object.entries(data.subject_sessions)
                  .sort(([, a], [, b]) => b - a)
                  .map(([subject, count]) => (
                    <div key={subject} className="flex items-center justify-between text-sm">
                      <span className="text-gray-700 dark:text-gray-300">{subject}</span>
                      <div className="flex items-center gap-2">
                        <div className="w-32 bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                          <div className="h-1.5 rounded-full bg-primary"
                            style={{ width: `${Math.min((count / Math.max(...Object.values(data.subject_sessions))) * 100, 100)}%` }} />
                        </div>
                        <span className="text-gray-500 w-8 text-right">{count}</span>
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Study plan section ── */}
      {activeSection === 'plan' && (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <Target size={16} /> Study Plan Completion
            </h2>
            <Link to="/study-plan" className="text-xs text-primary font-medium hover:underline">
              View Plan →
            </Link>
          </div>
          <PlanCompletionPanel stats={plan_stats} />
        </div>
      )}

      {/* ── Recommendations ── */}
      <div className="bg-gradient-to-r from-primary/10 to-secondary/10 border border-primary/20 rounded-xl p-5">
        <h2 className="text-base font-bold text-gray-900 dark:text-white mb-3">
          Focus Areas
        </h2>
        <ul className="space-y-2 text-sm text-gray-700 dark:text-gray-300">
          {sortedTopics.slice(0, 3).map((t, i) => (
            <li key={i} className="flex items-start gap-2">
              <span className="text-primary font-bold mt-0.5">→</span>
              <span>
                <Link to={`/study?topic=${encodeURIComponent(t.topic)}`}
                  className="font-bold text-primary hover:underline">{t.topic}</Link>
                {' '}({t.subject}) — {pct(t.score_pct)} now
                {t.improvement > 0 ? `, up ${pct(t.improvement)} from start` : ', no improvement yet'}
                {t.overdue ? ' — SM-2 review overdue!' : ''}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

// ── StatCard ───────────────────────────────────────────────────────────────────

const COLOR_MAP: Record<string, string> = {
  blue:   'bg-blue-100 dark:bg-blue-900/30 text-blue-600',
  purple: 'bg-purple-100 dark:bg-purple-900/30 text-purple-600',
  orange: 'bg-orange-100 dark:bg-orange-900/30 text-orange-600',
  green:  'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600',
  red:    'bg-red-100 dark:bg-red-900/30 text-red-600',
}

function StatCard({
  icon: Icon, label, value, sub, color,
}: {
  icon: React.ElementType; label: string; value: string | number; sub: string; color: string
}) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-4">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white mt-0.5">{value}</p>
          <p className="text-xs text-gray-400 mt-0.5">{sub}</p>
        </div>
        <div className={`p-2 rounded-lg flex-shrink-0 ${COLOR_MAP[color] ?? COLOR_MAP.blue}`}>
          <Icon size={18} />
        </div>
      </div>
    </div>
  )
}
