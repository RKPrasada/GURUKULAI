import { useState, useRef, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'
import api from '@/services/api'
import MarkdownRenderer from '@/components/MarkdownRenderer'
import { Search, MessageSquare, ExternalLink, CheckCircle, Calendar, Save, X } from 'lucide-react'

interface Message {
  id: string
  text: string
  timestamp: string
  sender: 'user' | 'assistant'
  driveUrl?: string
  videos?: Array<{ title: string; url: string; thumbnail?: string }>
  cardData?: any
}

const getDisplayText = (data: any): string => {
  if (typeof data?.notes === 'string') return data.notes
  if (typeof data?.response === 'string') return data.response
  if (typeof data?.summary === 'string') return data.summary
  if (data?._card_type === 'plan_card' || data?._card_type === 'schedule_card' || data?.pending_action) return ''
  return 'No response received.'
}

const getScheduleData = (cardData: any) => cardData?.plan || cardData?.schedule || {}

const getScheduleItems = (cardData: any) => {
  const scheduleData = getScheduleData(cardData)
  return scheduleData.plan || scheduleData.schedule || scheduleData.modules || []
}

const formatDuration = (session: any): string => {
  const minutes = session?.duration_minutes || (session?.duration_hours ? session.duration_hours * 60 : 0)
  return minutes ? `${minutes}m` : '•'
}

export default function StudyPage() {
  const student = useAuthStore((state) => state.student)
  const [searchParams] = useSearchParams()
  const initialTopic = searchParams.get('topic') || ''
  
  const [searchQuery, setSearchQuery] = useState(initialTopic)
  const [messages, setMessages] = useState<Message[]>([])
  const [newMessage, setNewMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [sendingMessage, setSendingMessage] = useState(false)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  
  // Track if we've already done the initial search to prevent duplicate fetches
  const hasSearchedRef = useRef(false)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (initialTopic && !hasSearchedRef.current) {
      hasSearchedRef.current = true
      
      const fetchInitialTopic = async () => {
        setLoading(true)
        try {
          const response = await api.sendMessage(initialTopic)
          const userMsg: Message = {
            id: Date.now().toString(),
            text: initialTopic,
            timestamp: new Date().toISOString(),
            sender: 'user',
          }
          const text = getDisplayText(response.data)
          const assistantMsg: Message = {
            id: (Date.now() + 1).toString(),
            text,
            timestamp: new Date().toISOString(),
            sender: 'assistant',
            driveUrl: response.data.drive_url,
            videos: response.data.youtube_videos,
            cardData: response.data,
          }
          setMessages([userMsg, assistantMsg])
        } catch (err: any) {
          console.error('Search failed:', err)
        } finally {
          setLoading(false)
        }
      }
      
      fetchInitialTopic()
    }
  }, [initialTopic])

  const addAssistantMessage = (data: any, query: string) => {
    const userMsg: Message = {
      id: Date.now().toString(),
      text: query,
      timestamp: new Date().toISOString(),
      sender: 'user',
    }
    const text = getDisplayText(data)
    const assistantMsg: Message = {
      id: (Date.now() + 1).toString(),
      text,
      timestamp: new Date().toISOString(),
      sender: 'assistant',
      driveUrl: data.drive_url,
      videos: data.youtube_videos,
      cardData: data,
    }
    setMessages((prev) => [...prev, userMsg, assistantMsg])
  }

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!searchQuery.trim()) return
    setLoading(true)
    const query = searchQuery
    setSearchQuery('')
    try {
      const response = await api.sendMessage(query)
      addAssistantMessage(response.data, query)
    } catch (err: any) {
      console.error('Search failed:', err)
      setMessages((prev) => [
        ...prev,
        { id: Date.now().toString(), text: query, timestamp: new Date().toISOString(), sender: 'user' },
        { id: (Date.now() + 1).toString(), text: 'Sorry, something went wrong. Please try again.', timestamp: new Date().toISOString(), sender: 'assistant' },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newMessage.trim()) return
    setSendingMessage(true)
    const query = newMessage
    setNewMessage('')
    try {
      const response = await api.sendMessage(query)
      addAssistantMessage(response.data, query)
    } catch (err: any) {
      console.error('Message failed:', err)
      setMessages((prev) => [
        ...prev,
        { id: Date.now().toString(), text: query, timestamp: new Date().toISOString(), sender: 'user' },
        { id: (Date.now() + 1).toString(), text: 'Sorry, something went wrong.', timestamp: new Date().toISOString(), sender: 'assistant' },
      ])
    } finally {
      setSendingMessage(false)
    }
  }

  const handleTopicClick = async (topic: string) => {
    setSearchQuery('')
    setLoading(true)
    try {
      const response = await api.sendMessage(topic)
      addAssistantMessage(response.data, topic)
    } catch (err: any) {
      console.error('Topic click failed:', err)
      setMessages((prev) => [
        ...prev,
        { id: Date.now().toString(), text: topic, timestamp: new Date().toISOString(), sender: 'user' },
        { id: (Date.now() + 1).toString(), text: 'Sorry, something went wrong.', timestamp: new Date().toISOString(), sender: 'assistant' },
      ])
    } finally {
      setLoading(false)
    }
  }

  const updateMessageCard = (messageId: string, updater: (cardData: any) => any) => {
    setMessages((prev) =>
      prev.map((msg) => {
        if (msg.id !== messageId) return msg
        const cardData = updater(msg.cardData || {})
        return {
          ...msg,
          cardData,
          driveUrl: cardData.drive_url || msg.driveUrl,
        }
      })
    )
  }

  const handleConfirmPending = async (messageId: string, token: string) => {
    setActionLoading(token)
    try {
      const response = await api.confirmSessionAction(token)
      const result = response.data.result
      updateMessageCard(messageId, (cardData) => ({
        ...cardData,
        pending_action: undefined,
        drive_url: result?.url,
        drive_file_id: result?.file_id,
        action_status: 'saved',
      }))
    } catch (err) {
      console.error('Action confirmation failed:', err)
      updateMessageCard(messageId, (cardData) => ({
        ...cardData,
        action_status: 'failed',
      }))
    } finally {
      setActionLoading(null)
    }
  }

  const handleCancelPending = async (messageId: string, token: string) => {
    setActionLoading(token)
    try {
      await api.cancelSessionAction(token)
      updateMessageCard(messageId, (cardData) => ({
        ...cardData,
        pending_action: undefined,
        action_status: 'cancelled',
      }))
    } catch (err) {
      console.error('Action cancellation failed:', err)
    } finally {
      setActionLoading(null)
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Left Panel */}
      <div className="lg:col-span-1">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 sticky top-6">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">📚 Study Materials</h2>

          <form onSubmit={handleSearch} className="mb-6">
            <div className="relative">
              <input
                type="text"
                placeholder="Search topics..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 focus:ring-2 focus:ring-primary focus:border-transparent outline-none pr-10"
              />
              <button
                type="submit"
                disabled={loading}
                className="absolute right-2 top-2 text-primary hover:text-primary/80 disabled:opacity-50"
              >
                <Search size={20} />
              </button>
            </div>
          </form>

          <div className="mb-6">
            <button
              onClick={() => handleTopicClick("Generate my full syllabus schedule")}
              className="w-full flex items-center justify-center gap-2 bg-primary/10 hover:bg-primary/20 text-primary font-semibold py-3 px-4 rounded-lg transition"
            >
              <Calendar size={20} />
              Generate My Schedule
            </button>
          </div>

          {student?.weakness_map && student.weakness_map.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Recommended Topics</h3>
              <div className="space-y-2">
                {student.weakness_map
                  .slice()
                  .sort((a, b) => a.score_pct - b.score_pct)
                  .slice(0, 6)
                  .map((w) => (
                    <button
                      key={`${w.subject}_${w.topic}`}
                      onClick={() => handleTopicClick(w.topic)}
                      className="w-full text-left p-3 bg-gray-50 dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600 rounded-lg transition"
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="font-medium text-gray-900 dark:text-white text-sm">{w.topic}</div>
                          <div className="text-xs text-gray-500 dark:text-gray-400">{w.subject}</div>
                        </div>
                        <span
                          className={`text-xs font-bold ${
                            w.score_pct >= 0.6 ? 'text-green-600' : 'text-red-500'
                          }`}
                        >
                          {(w.score_pct * 100).toFixed(0)}%
                        </span>
                      </div>
                    </button>
                  ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Right Panel — Chat */}
      <div className="lg:col-span-2">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg overflow-hidden flex flex-col h-[600px]">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.length === 0 ? (
              <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
                <div className="text-center">
                  <MessageSquare size={48} className="mx-auto mb-3 opacity-30" />
                  <p className="font-medium">Ask about any topic to get study notes</p>
                  <p className="text-sm mt-1">Or click a recommended topic on the left</p>
                </div>
              </div>
            ) : (
              messages.map((msg) => (
                <div key={msg.id} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                  {msg.sender === 'user' ? (
                    <div className="max-w-xs lg:max-w-md px-4 py-2 rounded-lg bg-primary text-white">
                      <p className="text-sm">{msg.text}</p>
                    </div>
                  ) : (
                    <div className="max-w-full w-full">
                      {msg.text && (
                        <div className="bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg p-4 mb-3">
                          <MarkdownRenderer content={msg.text} />
                        </div>
                      )}
                      
                      {msg.cardData?._card_type === 'naga_interaction_card' ? (
                        <div className="bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 rounded-lg p-4">
                          <div className="flex items-center gap-3 text-green-700 dark:text-green-400">
                            <CheckCircle size={24} />
                            <div>
                              <p className="font-semibold text-sm">Request Sent to NAGA</p>
                              <p className="text-xs">{msg.cardData.message || 'Processing your request...'}</p>
                            </div>
                          </div>
                        </div>
                      ) : msg.cardData?._card_type === 'schedule_card' || msg.cardData?._card_type === 'plan_card' ? (
                        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden shadow-sm">
                          <div className="bg-primary/10 px-4 py-3 border-b border-primary/20">
                            <h3 className="font-bold text-primary dark:text-primary-light flex items-center gap-2">
                              <Calendar size={18} />
                              {getScheduleData(msg.cardData).plan_type === 'adaptive' ? 'Adaptive Study Plan' : 'Study Schedule'}
                            </h3>
                            <div className="flex gap-4 mt-1 text-xs text-gray-600 dark:text-gray-400">
                              <span>Total Hours: {getScheduleData(msg.cardData).total_hours || 0}</span>
                              <span>Target: {getScheduleData(msg.cardData).exam_target || getScheduleData(msg.cardData).exam || 'General'}</span>
                            </div>
                          </div>
                          <div className="divide-y divide-gray-100 dark:divide-gray-700 max-h-[400px] overflow-y-auto">
                            {getScheduleItems(msg.cardData).map((day: any, i: number) => (
                              <details key={i} className="group p-4 bg-gray-50 dark:bg-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-800 cursor-pointer">
                                <summary className="font-medium text-sm text-gray-900 dark:text-white flex justify-between items-center outline-none">
                                  <span>{day.day ? `Day ${day.day}` : day.month || day.week || day.title || `Phase ${i+1}`} {day.focus ? ` - ${day.focus}` : ''} {day.date ? ` - ${day.date}` : ''}</span>
                                  <span className="text-gray-400 group-open:rotate-180 transition-transform">▼</span>
                                </summary>
                                <div className="mt-3 space-y-3 pl-2">
                                  {day.days ? (
                                    day.days.map((d: any, dayIndex: number) => (
                                      <div key={dayIndex} className="rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 p-3">
                                        <div className="text-xs font-bold text-gray-700 dark:text-gray-300 mb-2">{d.label || `Day ${d.day || dayIndex + 1}`}</div>
                                        <div className="space-y-2">
                                          {(d.sessions || []).map((s: any, j: number) => (
                                            <div key={j} className="grid grid-cols-[52px_52px_1fr] gap-2 text-sm items-start">
                                              <span className="text-gray-500">{s.time || '--:--'}</span>
                                              <span className="text-gray-500">{formatDuration(s)}</span>
                                              <span className="text-gray-800 dark:text-gray-200">
                                                <span className="font-medium">{s.topic || s.name || s.title}</span>
                                                {s.activity ? <span className="block text-xs text-gray-500 dark:text-gray-400">{s.activity}</span> : null}
                                              </span>
                                            </div>
                                          ))}
                                        </div>
                                      </div>
                                    ))
                                  ) : (
                                    (day.sessions || day.topics || [day]).map((s: any, j: number) => (
                                      <div key={j} className="grid grid-cols-[52px_52px_1fr] gap-2 text-sm items-start">
                                        <span className="text-gray-500">{s.time || ''}</span>
                                        <span className="text-gray-500">{formatDuration(s)}</span>
                                        <span className="text-gray-800 dark:text-gray-200">
                                          <span className="font-medium">{s.topic || s.name || s.title || s}</span>
                                          {s.activity ? <span className="block text-xs text-gray-500 dark:text-gray-400">{s.activity}</span> : null}
                                        </span>
                                      </div>
                                    ))
                                  )}
                                </div>
                              </details>
                            ))}
                          </div>
                        </div>
                      ) : null}

                      {msg.cardData?.pending_action && (
                        <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4 mt-2">
                          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                            <div>
                              <p className="font-semibold text-sm text-amber-900 dark:text-amber-100">Confirm action</p>
                              <p className="text-xs text-amber-800 dark:text-amber-200 mt-1">
                                {msg.cardData.pending_action.description}
                              </p>
                            </div>
                            <div className="flex gap-2">
                              <button
                                type="button"
                                disabled={actionLoading === msg.cardData.pending_action.token}
                                onClick={() => handleConfirmPending(msg.id, msg.cardData.pending_action.token)}
                                className="inline-flex items-center gap-1.5 bg-primary hover:bg-primary/90 disabled:bg-gray-400 text-white text-xs font-semibold px-3 py-2 rounded-lg transition"
                              >
                                <Save size={14} />
                                Save
                              </button>
                              <button
                                type="button"
                                disabled={actionLoading === msg.cardData.pending_action.token}
                                onClick={() => handleCancelPending(msg.id, msg.cardData.pending_action.token)}
                                className="inline-flex items-center gap-1.5 bg-white dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200 border border-gray-300 dark:border-gray-600 text-xs font-semibold px-3 py-2 rounded-lg transition"
                              >
                                <X size={14} />
                                Skip
                              </button>
                            </div>
                          </div>
                        </div>
                      )}

                      {msg.cardData?.action_status === 'saved' && (
                        <div className="mt-2 text-xs text-green-700 dark:text-green-400 font-medium">
                          Notes saved successfully.
                        </div>
                      )}

                      {msg.cardData?.action_status === 'cancelled' && (
                        <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                          Save skipped.
                        </div>
                      )}

                      {msg.cardData?.action_status === 'failed' && (
                        <div className="mt-2 text-xs text-red-600 dark:text-red-400">
                          Could not complete that action. Please try again.
                        </div>
                      )}
                      
                      {msg.videos && msg.videos.length > 0 && (
                        <div className="bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg p-4 mt-2">
                          <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-2">📺 Related Videos</p>
                          <div className="space-y-1">
                            {msg.videos.map((v, i) => (
                              <a
                                key={i}
                                href={v.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-2 text-xs text-primary hover:underline"
                              >
                                <ExternalLink size={12} />
                                {v.title}
                              </a>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {msg.driveUrl && (
                        <div className="mt-2">
                          <a
                            href={msg.driveUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-xs text-primary hover:underline bg-gray-50 dark:bg-gray-700 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-600"
                          >
                            <ExternalLink size={12} /> Saved to Drive
                          </a>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))
            )}
            {(loading || sendingMessage) && (
              <div className="flex justify-start">
                <div className="bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg px-4 py-2">
                  <div className="flex gap-1 items-center">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="border-t border-gray-200 dark:border-gray-700 p-4">
            <form onSubmit={handleSendMessage} className="flex gap-2">
              <input
                type="text"
                placeholder="Ask a question about any topic..."
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 focus:ring-2 focus:ring-primary focus:border-transparent outline-none"
              />
              <button
                type="submit"
                disabled={sendingMessage || loading}
                className="bg-primary hover:bg-primary/90 disabled:bg-gray-400 text-white font-semibold py-2 px-4 rounded-lg transition"
              >
                {sendingMessage ? '⏳' : '→'}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}
