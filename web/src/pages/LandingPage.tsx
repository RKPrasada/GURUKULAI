import { useNavigate } from 'react-router-dom'
import { useState } from 'react'
import api from '@/services/api'
import { useAuthStore } from '@/store/auth'

const exams = [
  { id: 'rrb_ntpc', label: 'RRB NTPC', desc: 'Railway Non-Technical Popular Categories' },
  { id: 'nda', label: 'NDA', desc: 'National Defence Academy' },
  { id: 'jee', label: 'JEE', desc: 'Joint Entrance Examination' },
  { id: 'neet', label: 'NEET', desc: 'National Eligibility cum Entrance Test' },
]

const features = [
  {
    icon: '🎯',
    title: '100-Question Diagnostic',
    desc: 'Full exam-pattern paper. Pinpoints weak topics — not just "weak in Maths" but "weak in Number System".',
  },
  {
    icon: '🧠',
    title: 'Adaptive Practice',
    desc: 'MCQ difficulty adjusts to your level in real time. Harder when you improve, easier when you struggle.',
  },
  {
    icon: '🇮🇳',
    title: 'Hindi + English',
    desc: 'Study in your language. Switch between English and Hindi — every explanation, every question.',
  },
  {
    icon: '👨‍🏫',
    title: 'NAGA Human Mentor',
    desc: 'Real mentor for live doubt sessions, group classes, and 1-to-1 meetings via Google Meet.',
  },
  {
    icon: '📅',
    title: 'Smart Study Plan',
    desc: '7-day spaced repetition schedule built from your weakness map. Sent to Google Calendar.',
  },
  {
    icon: '🔒',
    title: 'Safe & Private',
    desc: 'Injection detection, PII scrubbing, tamper-evident audit log. Your data stays yours.',
  },
]

const stats = [
  { value: '12M+', label: 'Students appear for RRB/NDA/JEE/NEET yearly' },
  { value: '₹0', label: 'Cost to use Gurukul AI' },
  { value: '100Q', label: 'Full diagnostic paper per exam' },
  { value: '4 Exams', label: 'RRB NTPC · NDA · JEE · NEET' },
]

export default function LandingPage() {
  const navigate = useNavigate()
  const login = useAuthStore((s) => s.login)
  const [demoLoading, setDemoLoading] = useState(false)
  const [selectedExam, setSelectedExam] = useState('rrb_ntpc')

  const handleDemo = async () => {
    setDemoLoading(true)
    try {
      const res = await api.demoLogin(selectedExam, 'en', 'Demo Student')
      const { access_token, ...student } = res.data
      login(student, access_token)
      navigate('/')
    } catch {
      navigate('/register')
    } finally {
      setDemoLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-white dark:bg-gray-950 text-gray-900 dark:text-white">

      {/* Nav */}
      <nav className="fixed top-0 inset-x-0 z-50 bg-white/80 dark:bg-gray-950/80 backdrop-blur border-b border-gray-100 dark:border-gray-800">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-2xl">📚</span>
            <span className="text-xl font-bold text-primary">Gurukul AI</span>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/login')}
              className="text-sm font-medium text-gray-600 dark:text-gray-300 hover:text-primary transition"
            >
              Log in
            </button>
            <button
              onClick={() => navigate('/register')}
              className="text-sm font-semibold bg-primary text-white px-4 py-2 rounded-lg hover:bg-primary/90 transition"
            >
              Get started free
            </button>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="pt-32 pb-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 bg-primary/10 text-primary text-sm font-medium px-4 py-1.5 rounded-full mb-6">
            <span>🏆</span> Kaggle Agents for Good 2026
          </div>

          <h1 className="text-5xl sm:text-6xl font-extrabold leading-tight mb-6">
            Crack{' '}
            <span className="text-primary">RRB · NDA · JEE · NEET</span>
            <br />
            with your personal AI tutor
          </h1>

          <p className="text-xl text-gray-600 dark:text-gray-300 max-w-2xl mx-auto mb-4">
            Bilingual (English + Hindi) adaptive AI tutor that finds exactly where you're weak,
            then fixes it — topic by topic.
          </p>
          <p className="text-lg text-gray-500 dark:text-gray-400 mb-10">
            Private coaching costs ₹5,000–₹20,000/month. Gurukul AI is free.
          </p>

          {/* Demo launcher */}
          <div className="bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-2xl p-6 max-w-md mx-auto mb-6">
            <p className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
              Try it now — no account needed
            </p>
            <div className="grid grid-cols-2 gap-2 mb-4">
              {exams.map((e) => (
                <button
                  key={e.id}
                  onClick={() => setSelectedExam(e.id)}
                  className={`px-3 py-2 rounded-lg text-sm font-medium border transition ${
                    selectedExam === e.id
                      ? 'bg-primary text-white border-primary'
                      : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-600 hover:border-primary'
                  }`}
                >
                  {e.label}
                </button>
              ))}
            </div>
            <button
              onClick={handleDemo}
              disabled={demoLoading}
              className="w-full bg-secondary hover:bg-secondary/90 disabled:bg-gray-400 text-white font-bold py-3 px-6 rounded-xl text-base transition"
            >
              {demoLoading ? '⏳ Starting...' : `▶ Start ${exams.find(e => e.id === selectedExam)?.label} Demo`}
            </button>
          </div>

          <p className="text-sm text-gray-400">
            Or{' '}
            <button onClick={() => navigate('/register')} className="text-primary hover:underline font-medium">
              create a free account
            </button>{' '}
            to save your progress
          </p>
        </div>
      </section>

      {/* Stats */}
      <section className="py-12 bg-primary">
        <div className="max-w-5xl mx-auto px-6 grid grid-cols-2 sm:grid-cols-4 gap-8 text-center">
          {stats.map((s) => (
            <div key={s.label}>
              <div className="text-3xl font-extrabold text-white mb-1">{s.value}</div>
              <div className="text-sm text-purple-200">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="py-20 px-6 bg-gray-50 dark:bg-gray-900">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-4">How Gurukul AI works</h2>
          <p className="text-center text-gray-500 dark:text-gray-400 mb-14">
            Three steps from sign-up to a personalised study plan
          </p>
          <div className="grid sm:grid-cols-3 gap-8">
            {[
              {
                step: '01',
                title: 'Take the diagnostic',
                desc: '100 questions, full exam pattern. Takes ~45 minutes. Gurukul AI maps every topic to a score — "Number System 18%", "Algebra 62%".',
              },
              {
                step: '02',
                title: 'Study your weak spots',
                desc: 'AI-generated study notes in English or Hindi. Practice MCQs at your current level. Wrong answers get explained immediately.',
              },
              {
                step: '03',
                title: 'Track and improve',
                desc: 'Weekly study plan auto-sent to Google Calendar. Progress digest to your email. Ask NAGA for live classes when you\'re stuck.',
              },
            ].map((item) => (
              <div key={item.step} className="relative bg-white dark:bg-gray-800 rounded-2xl p-8 shadow-sm">
                <div className="text-5xl font-extrabold text-primary/10 mb-4">{item.step}</div>
                <h3 className="text-lg font-bold mb-2">{item.title}</h3>
                <p className="text-gray-500 dark:text-gray-400 text-sm leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 px-6">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-4">Everything you need to clear the exam</h2>
          <p className="text-center text-gray-500 dark:text-gray-400 mb-14">
            Built specifically for Indian competitive exams, not generic tutoring
          </p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((f) => (
              <div
                key={f.title}
                className="bg-gray-50 dark:bg-gray-900 border border-gray-100 dark:border-gray-800 rounded-2xl p-6 hover:border-primary/40 transition"
              >
                <div className="text-3xl mb-3">{f.icon}</div>
                <h3 className="font-bold text-base mb-2">{f.title}</h3>
                <p className="text-sm text-gray-500 dark:text-gray-400 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* NAGA section */}
      <section className="py-20 px-6 bg-gray-50 dark:bg-gray-900">
        <div className="max-w-4xl mx-auto flex flex-col sm:flex-row items-center gap-12">
          <div className="flex-1">
            <div className="inline-flex items-center gap-2 bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400 text-sm font-medium px-3 py-1 rounded-full mb-4">
              Human in the loop
            </div>
            <h2 className="text-3xl font-bold mb-4">Meet NAGA — your human mentor</h2>
            <p className="text-gray-500 dark:text-gray-400 mb-6 leading-relaxed">
              AI tutors are great for practice. But some doubts need a real teacher.
              NAGA is a named human mentor built into Gurukul AI who can answer questions,
              run live group classes on Google Meet, and take 1-to-1 sessions.
            </p>
            <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-300">
              {[
                'Post a doubt — NAGA reviews and answers within 24h',
                'Join live group classes — get Meet link in-app',
                'Request 1-to-1 sessions for complex topics',
                'Real-time notifications when NAGA replies',
              ].map((item) => (
                <li key={item} className="flex items-start gap-2">
                  <span className="text-primary mt-0.5">✓</span> {item}
                </li>
              ))}
            </ul>
          </div>
          <div className="flex-shrink-0 bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-6 w-full sm:w-72">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-primary flex items-center justify-center text-white font-bold text-lg">N</div>
              <div>
                <div className="font-semibold text-sm">NAGA</div>
                <div className="text-xs text-green-500 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500 inline-block"></span>
                  Mentor · Online
                </div>
              </div>
            </div>
            <div className="bg-primary/10 rounded-xl p-3 text-sm text-gray-700 dark:text-gray-300 mb-3">
              Great question! For Number System problems involving LCM, always start by prime factorising both numbers...
            </div>
            <div className="bg-gray-100 dark:bg-gray-700 rounded-xl p-3 text-sm text-gray-500 text-right">
              Why is LCM of 12 and 18 equal to 36?
            </div>
            <div className="mt-4 pt-4 border-t border-gray-100 dark:border-gray-700 text-xs text-gray-400 text-center">
              Upcoming class: Number System — Tomorrow 7 PM
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-6 bg-primary">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="text-3xl font-extrabold text-white mb-4">
            Start your free diagnostic today
          </h2>
          <p className="text-purple-200 mb-8">
            100 questions. Full exam pattern. Topic-level weakness map. Takes 45 minutes.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <button
              onClick={handleDemo}
              disabled={demoLoading}
              className="bg-white text-primary font-bold py-3 px-8 rounded-xl hover:bg-gray-50 transition"
            >
              {demoLoading ? '⏳ Starting...' : '▶ Try demo — no signup'}
            </button>
            <button
              onClick={() => navigate('/register')}
              className="bg-white/10 border border-white/30 text-white font-bold py-3 px-8 rounded-xl hover:bg-white/20 transition"
            >
              Create free account
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 px-6 border-t border-gray-100 dark:border-gray-800">
        <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-gray-400">
          <div className="flex items-center gap-2">
            <span>📚</span>
            <span className="font-semibold text-gray-600 dark:text-gray-300">Gurukul AI</span>
            <span>· AI Tutor for Indian Competitive Exams</span>
          </div>
          <div className="flex items-center gap-6">
            <a
              href="https://github.com/rkprasada/gurukul-ai"
              target="_blank"
              rel="noreferrer"
              className="hover:text-primary transition"
            >
              GitHub
            </a>
            <span>MIT License</span>
            <span>Kaggle Agents for Good 2026</span>
          </div>
        </div>
      </footer>
    </div>
  )
}
