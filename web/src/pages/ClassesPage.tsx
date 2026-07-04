import { useEffect, useState } from 'react'
import { useAuthStore } from '@/store/auth'
import api from '@/services/api'
import { Calendar, Clock, Users, Video, CheckCircle } from 'lucide-react'

interface ScheduledClass {
  class_id: string
  title: string
  description: string
  subject: string
  topic: string
  class_type: string
  scheduled_at: string
  duration_minutes: number
  meet_link: string
  rsvp_list: { student_id: string; name: string }[]
  target_student_id: string | null
  status: string
}

export default function ClassesPage() {
  const student = useAuthStore((s) => s.student)
  const [classes, setClasses] = useState<ScheduledClass[]>([])
  const [loading, setLoading] = useState(true)
  const [rsvping, setRsvping] = useState<string | null>(null)

  const isNaga = student?.user_id === 'naga'

  useEffect(() => { load() }, [])

  const load = async () => {
    try {
      const res = await api.listClasses()
      setClasses(res.data)
    } catch { }
    setLoading(false)
  }

  const handleRsvp = async (classId: string) => {
    setRsvping(classId)
    try {
      const res = await api.rsvpClass(classId)
      await load()
      if (res.data.meet_link && res.data.action === 'confirmed') {
        alert(`✅ RSVP confirmed!\n\nMeet link: ${res.data.meet_link}\n\nSave this link to join the class.`)
      }
    } catch { }
    setRsvping(null)
  }

  const handleCancel = async (classId: string) => {
    if (!window.confirm('Cancel this class?')) return
    try {
      await api.cancelClass(classId)
      await load()
    } catch { }
  }

  const now = new Date()
  const upcoming = classes.filter((c) => new Date(c.scheduled_at) > now && c.status === 'scheduled')
  const past = classes.filter((c) => new Date(c.scheduled_at) <= now || c.status !== 'scheduled')

  const isRsvped = (cls: ScheduledClass) =>
    cls.rsvp_list.some((r) => r.student_id === student?.user_id)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">📅 Classes & Sessions</h1>
        <p className="text-gray-600 dark:text-gray-400 text-sm">Upcoming live sessions by NAGA</p>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading classes...</div>
      ) : (
        <>
          {/* Upcoming */}
          <section>
            <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
              🔜 Upcoming ({upcoming.length})
            </h2>
            {upcoming.length === 0 ? (
              <div className="text-center py-8 text-gray-500 bg-white dark:bg-gray-800 rounded-lg shadow">
                No upcoming classes scheduled
              </div>
            ) : (
              <div className="space-y-4">
                {upcoming.map((cls) => (
                  <ClassCard
                    key={cls.class_id}
                    cls={cls}
                    isNaga={isNaga}
                    isRsvped={isRsvped(cls)}
                    rsvping={rsvping === cls.class_id}
                    onRsvp={() => handleRsvp(cls.class_id)}
                    onCancel={() => handleCancel(cls.class_id)}
                  />
                ))}
              </div>
            )}
          </section>

          {/* Past */}
          {past.length > 0 && (
            <section>
              <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
                ✅ Past Sessions ({past.length})
              </h2>
              <div className="space-y-3 opacity-70">
                {past.map((cls) => (
                  <ClassCard
                    key={cls.class_id}
                    cls={cls}
                    isNaga={isNaga}
                    isRsvped={isRsvped(cls)}
                    rsvping={false}
                    onRsvp={() => {}}
                    onCancel={() => {}}
                    past
                  />
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  )
}

function ClassCard({
  cls, isNaga, isRsvped, rsvping, onRsvp, onCancel, past = false,
}: {
  cls: ScheduledClass
  isNaga: boolean
  isRsvped: boolean
  rsvping: boolean
  onRsvp: () => void
  onCancel: () => void
  past?: boolean
}) {
  const dt = new Date(cls.scheduled_at)
  const isOneToOne = cls.class_type === 'one_to_one'

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg shadow p-6 border-l-4 ${
      cls.status === 'cancelled' ? 'border-red-400 opacity-60' :
      isOneToOne ? 'border-secondary' : 'border-primary'
    }`}>
      <div className="flex justify-between items-start">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${
              isOneToOne
                ? 'bg-secondary/10 text-secondary'
                : 'bg-primary/10 text-primary'
            }`}>
              {isOneToOne ? '👤 1-to-1' : '👥 Group Class'}
            </span>
            <span className="text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 px-2 py-0.5 rounded-full">
              {cls.subject}
            </span>
            {cls.status === 'cancelled' && (
              <span className="text-xs bg-red-100 text-red-600 px-2 py-0.5 rounded-full">Cancelled</span>
            )}
          </div>

          <h3 className="text-lg font-bold text-gray-900 dark:text-white">{cls.title}</h3>
          <p className="text-gray-600 dark:text-gray-400 text-sm mt-1">{cls.description}</p>

          <div className="flex flex-wrap gap-4 mt-3 text-sm text-gray-600 dark:text-gray-400">
            <span className="flex items-center gap-1">
              <Calendar size={14} />
              {dt.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })}
            </span>
            <span className="flex items-center gap-1">
              <Clock size={14} />
              {dt.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })} ({cls.duration_minutes} min)
            </span>
            {!isOneToOne && (
              <span className="flex items-center gap-1">
                <Users size={14} />
                {cls.rsvp_list.length} RSVP'd
              </span>
            )}
          </div>

          {cls.meet_link && (isRsvped || isNaga || isOneToOne) && (
            <a
              href={cls.meet_link}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 mt-3 text-sm bg-green-500 hover:bg-green-600 text-white py-1.5 px-4 rounded-lg transition"
            >
              <Video size={14} /> Join Google Meet
            </a>
          )}
        </div>

        {/* Actions */}
        {!past && cls.status === 'scheduled' && (
          <div className="ml-4 flex flex-col gap-2">
            {isNaga ? (
              <button
                onClick={onCancel}
                className="text-sm bg-red-100 hover:bg-red-200 text-red-600 py-1.5 px-3 rounded-lg transition"
              >
                Cancel Class
              </button>
            ) : !isOneToOne ? (
              <button
                onClick={onRsvp}
                disabled={rsvping}
                className={`text-sm font-semibold py-1.5 px-4 rounded-lg transition flex items-center gap-1 ${
                  isRsvped
                    ? 'bg-green-100 hover:bg-red-100 text-green-700 hover:text-red-600'
                    : 'bg-primary hover:bg-primary/90 text-white'
                }`}
              >
                {rsvping ? '...' : isRsvped ? <><CheckCircle size={14} /> RSVP'd</> : 'RSVP'}
              </button>
            ) : null}
          </div>
        )}
      </div>
    </div>
  )
}
