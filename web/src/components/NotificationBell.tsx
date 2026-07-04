import { useEffect, useState } from 'react'
import { Bell, X, CheckCheck } from 'lucide-react'
import api from '@/services/api'

interface Notification {
  notification_id: string
  type: string
  title: string
  body: string
  read: boolean
  data: Record<string, string>
  created_at: string
}

export default function NotificationBell() {
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [open, setOpen] = useState(false)

  const unread = notifications.filter((n) => !n.read).length

  const load = async () => {
    try {
      const res = await api.getNotifications()
      setNotifications(res.data)
    } catch {
      // silent fail
    }
  }

  useEffect(() => {
    load()
    const interval = setInterval(load, 30000) // poll every 30s
    return () => clearInterval(interval)
  }, [])

  const markRead = async (id: string) => {
    await api.markNotificationRead(id)
    setNotifications((prev) => prev.map((n) => n.notification_id === id ? { ...n, read: true } : n))
  }

  const markAll = async () => {
    await api.markAllNotificationsRead()
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })))
  }

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="relative p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
        title="Notifications"
      >
        <Bell size={20} className="text-gray-600 dark:text-gray-300" />
        {unread > 0 && (
          <span className="absolute top-1 right-1 bg-red-500 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center font-bold">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 z-50">
          <div className="flex justify-between items-center px-4 py-3 border-b border-gray-200 dark:border-gray-700">
            <h3 className="font-semibold text-gray-900 dark:text-white">Notifications</h3>
            <div className="flex gap-2">
              {unread > 0 && (
                <button onClick={markAll} className="text-xs text-primary hover:underline flex items-center gap-1">
                  <CheckCheck size={14} /> Mark all read
                </button>
              )}
              <button onClick={() => setOpen(false)}>
                <X size={18} className="text-gray-500" />
              </button>
            </div>
          </div>

          <div className="max-h-80 overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="text-center py-8 text-gray-500 text-sm">No notifications</div>
            ) : (
              notifications.map((n) => (
                <div
                  key={n.notification_id}
                  onClick={() => !n.read && markRead(n.notification_id)}
                  className={`px-4 py-3 border-b border-gray-100 dark:border-gray-700 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 ${
                    !n.read ? 'bg-blue-50 dark:bg-blue-900/20' : ''
                  }`}
                >
                  <div className="flex justify-between items-start gap-2">
                    <p className="text-sm font-semibold text-gray-900 dark:text-white">{n.title}</p>
                    {!n.read && <span className="flex-shrink-0 w-2 h-2 bg-blue-500 rounded-full mt-1" />}
                  </div>
                  <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5 line-clamp-2">{n.body}</p>
                  <p className="text-xs text-gray-400 mt-1">
                    {new Date(n.created_at).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}
