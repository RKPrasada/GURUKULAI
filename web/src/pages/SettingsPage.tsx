import { useState } from 'react'
import { useAuthStore } from '@/store/auth'
import { User, Lock, Globe, Save, CheckCircle2 } from 'lucide-react'
import api from '@/services/api'

type Tab = 'profile' | 'password' | 'language'

export default function SettingsPage() {
  const student = useAuthStore((s) => s.student)
  const updateStudent = useAuthStore((s) => s.updateStudent)
  const [tab, setTab] = useState<Tab>('profile')
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  // Profile form
  const [fullName, setFullName] = useState(student?.full_name ?? '')
  const [email, setEmail] = useState(student?.email ?? '')

  // Password form
  const [currentPw, setCurrentPw] = useState('')
  const [newPw, setNewPw] = useState('')
  const [confirmPw, setConfirmPw] = useState('')

  // Language
  const [lang, setLang] = useState<'en' | 'hi'>(
    (student?.preferred_language as 'en' | 'hi') ?? 'en'
  )

  const flash = (ok: boolean, msg?: string) => {
    if (ok) { setSaved(true); setTimeout(() => setSaved(false), 2500) }
    else setError(msg ?? 'Something went wrong')
  }

  const saveProfile = () => {
    setError('')
    // Optimistic local update — backend profile endpoint to be wired in next sprint
    updateStudent({ ...student!, full_name: fullName, email })
    flash(true)
  }

  const savePassword = async () => {
    setError('')
    if (newPw !== confirmPw) { setError('New passwords do not match'); return }
    if (newPw.length < 6) { setError('Password must be at least 6 characters'); return }
    try {
      await api.changePassword(student!.user_id, currentPw, newPw, newPw)
      setCurrentPw(''); setNewPw(''); setConfirmPw('')
      flash(true)
    } catch (e: any) { flash(false, e.response?.data?.detail ?? 'Failed to change password') }
  }

  const saveLang = () => {
    setError('')
    updateStudent({ ...student!, preferred_language: lang })
    flash(true)
  }

  const tabs: { id: Tab; icon: React.ReactNode; label: string }[] = [
    { id: 'profile',  icon: <User size={16} />,  label: 'Profile'  },
    { id: 'password', icon: <Lock size={16} />,  label: 'Password' },
    { id: 'language', icon: <Globe size={16} />, label: 'Language' },
  ]

  return (
    <div className="max-w-xl mx-auto space-y-4">
      <h1 className="text-xl font-bold text-gray-900 dark:text-white">Settings</h1>

      {/* Tab bar */}
      <div className="flex gap-1 bg-gray-100 dark:bg-gray-800 p-1 rounded-xl">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => { setTab(t.id); setError(''); setSaved(false) }}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2 text-sm font-medium rounded-lg transition ${
              tab === t.id
                ? 'bg-white dark:bg-gray-700 text-primary shadow-sm'
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
            }`}
          >
            {t.icon}{t.label}
          </button>
        ))}
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-6 space-y-4">
        {/* ── Profile ── */}
        {tab === 'profile' && (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Full Name</label>
              <input
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Exam Target</label>
              <input
                value={student?.exam_target?.toUpperCase() ?? ''}
                disabled
                className="w-full border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-sm bg-gray-50 dark:bg-gray-700/50 text-gray-500 dark:text-gray-400 cursor-not-allowed"
              />
              <p className="text-xs text-gray-400 mt-1">Contact support to change exam target</p>
            </div>
            <button onClick={saveProfile} className="flex items-center gap-2 bg-primary hover:bg-primary/90 text-white text-sm font-semibold px-5 py-2.5 rounded-lg transition">
              <Save size={15} /> Save Changes
            </button>
          </>
        )}

        {/* ── Password ── */}
        {tab === 'password' && (
          <>
            {(['Current Password', 'New Password', 'Confirm New Password'] as const).map((lbl, i) => {
              const vals = [currentPw, newPw, confirmPw]
              const setters = [setCurrentPw, setNewPw, setConfirmPw]
              return (
                <div key={lbl}>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{lbl}</label>
                  <input
                    type="password"
                    value={vals[i]}
                    onChange={(e) => setters[i](e.target.value)}
                    className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
              )
            })}
            <button onClick={savePassword} className="flex items-center gap-2 bg-primary hover:bg-primary/90 text-white text-sm font-semibold px-5 py-2.5 rounded-lg transition">
              <Lock size={15} /> Change Password
            </button>
          </>
        )}

        {/* ── Language ── */}
        {tab === 'language' && (
          <>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Choose the language for questions, explanations and the interface.
            </p>
            <div className="grid grid-cols-2 gap-3">
              {([['en', '🇬🇧', 'English', 'Questions & UI in English'], ['hi', '🇮🇳', 'हिंदी', 'प्रश्न और UI हिंदी में']] as const).map(([code, flag, name, desc]) => (
                <button
                  key={code}
                  onClick={() => setLang(code)}
                  className={`border-2 rounded-xl p-4 text-left transition ${
                    lang === code ? 'border-primary bg-primary/5' : 'border-gray-200 dark:border-gray-700 hover:border-primary/40'
                  }`}
                >
                  <div className="text-2xl mb-1">{flag}</div>
                  <p className="font-semibold text-gray-900 dark:text-white text-sm">{name}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{desc}</p>
                </button>
              ))}
            </div>
            <button onClick={saveLang} className="flex items-center gap-2 bg-primary hover:bg-primary/90 text-white text-sm font-semibold px-5 py-2.5 rounded-lg transition">
              <Save size={15} /> Save Language
            </button>
          </>
        )}

        {/* Feedback strip */}
        {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
        {saved && (
          <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
            <CheckCircle2 size={16} /> Saved successfully
          </div>
        )}
      </div>
    </div>
  )
}
