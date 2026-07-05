import { useState, useRef, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'
import api from '@/services/api'
import MarkdownRenderer from '@/components/MarkdownRenderer'
import {
  Search, BookOpen, ExternalLink, CheckCircle, Save, X,
  Loader2, Lightbulb, ChevronRight, BarChart2,
} from 'lucide-react'

interface Message {
  id: string
  topic: string
  timestamp: string
  notes?: string
  videos?: Array<{ title: string; url: string; thumbnail?: string }>
  pendingAction?: { token: string; description: string }
  driveUrl?: string
  actionStatus?: 'saved' | 'cancelled' | 'failed'
  loading?: boolean
  error?: string
}

const LOADING_PHRASES = [
  'Looking up the concept…',
  'Generating study notes…',
  'Preparing solved examples…',
  'Checking exam tips…',
]

function NoteCard({ msg, onConfirm, onCancel, actionLoading }: {
  msg: Message
  onConfirm: (token: string) => void
  onCancel: (token: string) => void
  actionLoading: string | null
}) {
  if (msg.loading) {
    return (
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-5 space-y-3 animate-pulse">
        <div className="flex items-center gap-3 mb-2">
          <Loader2 size={18} className="text-primary animate-spin shrink-0" />
          <span className="text-sm font-medium text-primary">
            {LOADING_PHRASES[Math.floor(Date.now() / 1000) % LOADING_PHRASES.length]}
          </span>
        </div>
        <div className="h-3 bg-gray-100 dark:bg-gray-700 rounded w-3/4" />
        <div className="h-3 bg-gray-100 dark:bg-gray-700 rounded w-1/2" />
        <div className="h-3 bg-gray-100 dark:bg-gray-700 rounded w-5/6" />
      </div>
    )
  }

  if (msg.error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4 text-sm text-red-700 dark:text-red-300">
        {msg.error}
      </div>
    )
  }

  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden shadow-sm">
      {/* Header */}
      <div className="flex items-center gap-3 bg-primary/5 dark:bg-primary/10 border-b border-primary/10 px-4 py-3">
        <BookOpen size={16} className="text-primary shrink-0" />
        <h3 className="font-semibold text-primary text-sm truncate flex-1">{msg.topic}</h3>
        <span className="text-xs text-gray-400 shrink-0">
          {new Date(msg.timestamp).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>

      {/* Notes */}
      {msg.notes && (
        <div className="p-5">
          <MarkdownRenderer content={msg.notes} />
        </div>
      )}

      {/* Drive save prompt */}
      {msg.pendingAction && msg.actionStatus !== 'saved' && msg.actionStatus !== 'cancelled' && (
        <div className="mx-4 mb-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg p-3">
          <div className="flex flex-col sm:flex-row sm:items-center gap-3">
            <div className="flex-1">
              <p className="text-xs font-semibold text-amber-800 dark:text-amber-200">
                {msg.pendingAction.description}
              </p>
            </div>
            <div className="flex gap-2 shrink-0">
              <button
                disabled={actionLoading === msg.pendingAction.token}
                onClick={() => onConfirm(msg.pendingAction!.token)}
                className="inline-flex items-center gap-1 bg-primary text-white text-xs font-semibold px-3 py-1.5 rounded-lg hover:bg-primary/90 disabled:opacity-50 transition"
              >
                <Save size={12} /> Save to Drive
              </button>
              <button
                disabled={actionLoading === msg.pendingAction.token}
                onClick={() => onCancel(msg.pendingAction!.token)}
                className="inline-flex items-center gap-1 border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 text-xs font-semibold px-3 py-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 transition"
              >
                <X size={12} /> Skip
              </button>
            </div>
          </div>
        </div>
      )}
      {msg.actionStatus === 'saved' && (
        <p className="px-4 pb-3 text-xs text-green-600 dark:text-green-400 flex items-center gap-1">
          <CheckCircle size={12} /> Notes saved to Google Drive
        </p>
      )}

      {/* Videos */}
      {msg.videos && msg.videos.length > 0 && (
        <div className="border-t border-gray-100 dark:border-gray-700 px-4 py-3">
          <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-2 flex items-center gap-1">
            📺 Related Videos
          </p>
          <div className="space-y-1.5">
            {msg.videos.map((v, i) => (
              <a
                key={i}
                href={v.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 text-xs text-primary hover:underline"
              >
                <ExternalLink size={11} className="shrink-0" />
                {v.title}
              </a>
            ))}
          </div>
        </div>
      )}
      {msg.driveUrl && (
        <div className="border-t border-gray-100 dark:border-gray-700 px-4 py-2">
          <a href={msg.driveUrl} target="_blank" rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs text-primary hover:underline">
            <ExternalLink size={11} /> Saved to Drive
          </a>
        </div>
      )}
    </div>
  )
}

export default function StudyPage() {
  const student = useAuthStore((s) => s.student)
  const [searchParams] = useSearchParams()
  const initialTopic = searchParams.get('topic') || ''

  const [query, setQuery] = useState(initialTopic)
  const [messages, setMessages] = useState<Message[]>([])
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const hasSearchedRef = useRef(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const fetchNotes = async (topic: string) => {
    const id = Date.now().toString()
    setMessages((prev) => [...prev, {
      id, topic, timestamp: new Date().toISOString(), loading: true,
    }])
    try {
      const res = await api.getStudyNotes(topic)
      const d = res.data
      setMessages((prev) => prev.map((m) => m.id !== id ? m : {
        id, topic, timestamp: new Date().toISOString(),
        notes: d.notes,
        videos: d.youtube_videos,
        pendingAction: d.pending_action,
        driveUrl: d.drive_url,
      }))
    } catch (err: any) {
      const detail = err.response?.data?.detail
      setMessages((prev) => prev.map((m) => m.id !== id ? m : {
        id, topic, timestamp: new Date().toISOString(),
        error: detail || 'Could not load notes. Please try again.',
      }))
    }
  }

  useEffect(() => {
    if (initialTopic && !hasSearchedRef.current) {
      hasSearchedRef.current = true
      fetchNotes(initialTopic)
    }
  }, [initialTopic])

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    const t = query.trim()
    if (!t) return
    setQuery('')
    fetchNotes(t)
  }

  const handleTopicClick = (topic: string) => {
    setQuery('')
    fetchNotes(topic)
  }

  const updateMsg = (id: string, patch: Partial<Message>) => {
    setMessages((prev) => prev.map((m) => m.id === id ? { ...m, ...patch } : m))
  }

  const handleConfirm = async (msgId: string, token: string) => {
    setActionLoading(token)
    try {
      const res = await api.confirmSessionAction(token)
      const result = res.data.result
      updateMsg(msgId, {
        pendingAction: undefined,
        driveUrl: result?.url,
        actionStatus: 'saved',
      })
    } catch {
      updateMsg(msgId, { actionStatus: 'failed' })
    } finally {
      setActionLoading(null)
    }
  }

  const handleCancel = async (msgId: string, token: string) => {
    setActionLoading(token)
    try {
      await api.cancelSessionAction(token)
      updateMsg(msgId, { pendingAction: undefined, actionStatus: 'cancelled' })
    } catch {
      // ignore
    } finally {
      setActionLoading(null)
    }
  }

  const weakness = student?.weakness_map ?? []
  const sortedWeakness = [...weakness].sort((a, b) => a.score_pct - b.score_pct)

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-6">
      {/* ── Left Panel ── */}
      <div className="lg:col-span-1">
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 sticky top-6 space-y-5">
          <div>
            <h2 className="text-base font-bold text-gray-900 dark:text-white flex items-center gap-2 mb-3">
              <BookOpen size={16} className="text-primary" /> Study Materials
            </h2>
            <form onSubmit={handleSearch} className="flex gap-2">
              <input
                type="text"
                placeholder="Enter any topic…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="flex-1 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-primary focus:border-transparent outline-none"
              />
              <button
                type="submit"
                disabled={!query.trim()}
                className="p-2 bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-40 transition"
              >
                <Search size={16} />
              </button>
            </form>
            <p className="text-xs text-gray-400 mt-1.5">
              Get conceptual notes + solved examples for any syllabus topic.
            </p>
          </div>

          {/* Recommended topics from weakness_map */}
          {sortedWeakness.length > 0 && (
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-2 flex items-center gap-1">
                <BarChart2 size={12} /> Focus areas
              </h3>
              <div className="space-y-1">
                {sortedWeakness.slice(0, 7).map((w) => (
                  <button
                    key={`${w.subject}_${w.topic}`}
                    onClick={() => handleTopicClick(w.topic)}
                    className="w-full text-left px-3 py-2.5 bg-gray-50 dark:bg-gray-700/60 hover:bg-primary/5 dark:hover:bg-primary/10 rounded-lg transition group flex items-center gap-2"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{w.topic}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{w.subject}</p>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <span className={`text-xs font-bold ${w.score_pct >= 0.6 ? 'text-green-600' : w.score_pct >= 0.4 ? 'text-amber-500' : 'text-red-500'}`}>
                        {Math.round(w.score_pct * 100)}%
                      </span>
                      <ChevronRight size={12} className="text-gray-300 group-hover:text-primary transition" />
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Quick tips */}
          <div className="bg-amber-50 dark:bg-amber-900/20 rounded-lg p-3">
            <div className="flex items-start gap-2">
              <Lightbulb size={14} className="text-amber-500 mt-0.5 shrink-0" />
              <p className="text-xs text-amber-800 dark:text-amber-200">
                Each topic gives you: concept → formulas → 3 solved problems → exam tips.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* ── Right Panel — Notes ── */}
      <div className="space-y-4">
        {messages.length === 0 ? (
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-12 text-center">
            <BookOpen size={40} className="mx-auto mb-3 text-gray-300 dark:text-gray-600" />
            <h3 className="font-semibold text-gray-700 dark:text-gray-300 mb-1">No topic selected yet</h3>
            <p className="text-sm text-gray-400 dark:text-gray-500 max-w-xs mx-auto">
              Search for any topic or click a Focus Area on the left to get concept notes and solved examples.
            </p>
            {sortedWeakness.length > 0 && (
              <div className="mt-6 flex flex-wrap gap-2 justify-center">
                {sortedWeakness.slice(0, 4).map((w) => (
                  <button
                    key={`${w.subject}_${w.topic}`}
                    onClick={() => handleTopicClick(w.topic)}
                    className="text-xs px-3 py-1.5 bg-primary/10 text-primary font-medium rounded-full hover:bg-primary/20 transition"
                  >
                    {w.topic}
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : (
          messages.map((msg) => (
            <NoteCard
              key={msg.id}
              msg={msg}
              actionLoading={actionLoading}
              onConfirm={(token) => handleConfirm(msg.id, token)}
              onCancel={(token) => handleCancel(msg.id, token)}
            />
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
