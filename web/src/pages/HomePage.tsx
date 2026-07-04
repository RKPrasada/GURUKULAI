import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'
import {
  Target, BookOpen, PenLine, ClipboardList,
  MessagesSquare, CalendarDays, BarChart3,
  Flame, CheckCircle2, AlertTriangle, ChevronRight,
} from 'lucide-react'

const EXAM_LABEL: Record<string, string> = {
  rrb_ntpc: 'RRB NTPC',
  rrb_alp: 'RRB ALP',
  rrb_group_d: 'RRB Group D',
  nda: 'NDA',
  jee: 'JEE Mains',
  neet: 'NEET',
}

interface Section {
  to: string
  icon: React.ReactNode
  title: string
  description: string
  color: string
  locked?: boolean
}

function SectionCard({ section, onClick }: { section: Section; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`relative w-full text-left bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-5 hover:shadow-md transition-all group overflow-hidden ${
        section.locked ? 'opacity-60 cursor-default' : 'hover:-translate-y-0.5'
      }`}
    >
      {/* color accent bar */}
      <div className={`absolute top-0 left-0 right-0 h-1 ${section.color} rounded-t-xl`} />

      <div className="flex items-start gap-4 mt-1">
        <div className={`p-2.5 rounded-lg ${section.color.replace('bg-', 'bg-').replace('-500', '-100')} dark:bg-gray-700`}>
          <span className={section.color.replace('bg-', 'text-')}>{section.icon}</span>
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-gray-900 dark:text-white text-sm">{section.title}</h3>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 leading-relaxed">{section.description}</p>
        </div>
        {!section.locked && (
          <ChevronRight size={16} className="text-gray-300 dark:text-gray-600 group-hover:text-primary transition-colors mt-0.5 flex-shrink-0" />
        )}
      </div>
    </button>
  )
}

export default function HomePage() {
  const navigate = useNavigate()
  const student = useAuthStore((s) => s.student)

  const examLabel = EXAM_LABEL[student?.exam_target ?? ''] ?? student?.exam_target?.toUpperCase() ?? ''
  const isHindi = student?.preferred_language === 'hi'
  const diagnosticDone = student?.diagnostic_done ?? false

  const totalAttempted = student?.total_questions_attempted ?? 0
  const streakDays = student?.study_streak_days ?? 0
  const avgAccuracy =
    student?.weakness_map && student.weakness_map.length > 0
      ? Math.round(
          (student.weakness_map.reduce((s, w) => s + w.score_pct, 0) / student.weakness_map.length) * 100
        )
      : null

  const weakAreas = (student?.weakness_map ?? [])
    .filter((w) => w.score_pct < 0.5)
    .sort((a, b) => a.score_pct - b.score_pct)
    .slice(0, 4)

  const sections: Section[] = [
    {
      to: '/diagnostic',
      icon: <Target size={20} />,
      title: isHindi ? 'डायग्नोस्टिक टेस्ट' : 'Diagnostics',
      description: isHindi
        ? 'अपनी कमजोरियों को समझें और अनुकूलित अध्ययन योजना बनाएं'
        : 'Identify weak areas and build a personalised study plan',
      color: 'bg-violet-500',
    },
    {
      to: '/study',
      icon: <BookOpen size={20} />,
      title: isHindi ? 'अध्ययन योजना' : 'Study Plan',
      description: isHindi
        ? 'AI द्वारा तैयार नोट्स, वीडियो और विषय-वार सामग्री'
        : 'AI-curated notes, videos and topic content',
      color: 'bg-blue-500',
    },
    {
      to: '/test',
      icon: <PenLine size={20} />,
      title: isHindi ? 'प्रैक्टिस टेस्ट' : 'Practice Test',
      description: isHindi
        ? 'अनुकूलित कठिनाई स्तर पर प्रश्न, तुरंत प्रतिक्रिया के साथ'
        : 'Adaptive questions at your level with instant feedback',
      color: 'bg-emerald-500',
    },
    {
      to: '/mock-test',
      icon: <ClipboardList size={20} />,
      title: isHindi ? 'मॉक टेस्ट' : 'Mock Test',
      description: isHindi
        ? 'परीक्षा से पहले पूरा पेपर, समय-सीमा और नेगेटिव मार्किंग के साथ'
        : 'Full exam simulation with time limit and negative marking',
      color: 'bg-indigo-500',
    },
  ]

  return (
    <div className="space-y-6">
      {/* Welcome banner */}
      <div className="bg-gradient-to-br from-primary to-primary/70 rounded-2xl p-6 text-white">
        <p className="text-sm font-medium opacity-80 mb-1">{examLabel} Preparation</p>
        <h1 className="text-2xl font-bold mb-1">
          {isHindi
            ? `नमस्ते, ${student?.full_name?.split(' ')[0]} 👋`
            : `Hello, ${student?.full_name?.split(' ')[0]} 👋`}
        </h1>
        <p className="text-sm opacity-75">
          {isHindi ? 'Gurukul AI में आपका स्वागत है' : 'Welcome to Gurukul AI'}
        </p>
      </div>

      {/* Sanskrit shloka — Hitopadesha 1.1 */}
      <div className="flex items-start gap-3 bg-amber-50 dark:bg-amber-900/20 border-l-4 border-amber-400 dark:border-amber-500 rounded-r-xl px-4 py-3">
        <span className="text-amber-400 text-xl leading-none mt-0.5 flex-shrink-0">॥</span>
        <div className="min-w-0">
          <p
            className="text-sm font-medium text-amber-900 dark:text-amber-200 leading-loose tracking-wide"
            lang="sa"
          >
            विद्या ददाति विनयं विनयाद् याति पात्रताम् ।&nbsp;
            पात्रत्वात् धनमाप्नोति धनाद्धर्मं ततः सुखम् ॥
          </p>
          <p className="text-[11px] text-amber-600 dark:text-amber-400 mt-0.5 italic">
            Knowledge → Humility → Worthiness → Prosperity → Virtue → Happiness
            <span className="not-italic ml-2 text-amber-400 dark:text-amber-500">— Hitopadesha</span>
          </p>
        </div>
      </div>

      {/* Diagnostic CTA — only if not done */}
      {!diagnosticDone && (
        <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-xl p-5 flex items-start gap-4">
          <AlertTriangle size={22} className="text-amber-500 flex-shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <p className="font-semibold text-amber-900 dark:text-amber-100 text-sm">
              {isHindi ? 'डायग्नोस्टिक टेस्ट अभी तक नहीं दिया' : 'Diagnostic not completed yet'}
            </p>
            <p className="text-xs text-amber-700 dark:text-amber-300 mt-0.5">
              {isHindi
                ? 'पहले यह टेस्ट दें ताकि आपकी अध्ययन योजना व्यक्तिगत हो सके।'
                : 'Take the diagnostic first to personalise your study plan and question difficulty.'}
            </p>
          </div>
          <button
            onClick={() => navigate('/diagnostic')}
            className="flex-shrink-0 bg-amber-500 hover:bg-amber-600 text-white text-xs font-bold px-4 py-2 rounded-lg transition"
          >
            Start →
          </button>
        </div>
      )}

      {/* Stats row — only after diagnostic */}
      {diagnosticDone && (
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-4 text-center">
            <p className="text-2xl font-bold text-gray-900 dark:text-white">{totalAttempted}</p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Questions</p>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-4 text-center">
            <div className="flex items-center justify-center gap-1">
              <Flame size={16} className="text-orange-500" />
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{streakDays}</p>
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Day streak</p>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-4 text-center">
            {avgAccuracy !== null ? (
              <>
                <p className={`text-2xl font-bold ${avgAccuracy >= 70 ? 'text-green-600' : avgAccuracy >= 40 ? 'text-yellow-600' : 'text-red-500'}`}>
                  {avgAccuracy}%
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Avg accuracy</p>
              </>
            ) : (
              <>
                <p className="text-2xl font-bold text-gray-400">—</p>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Avg accuracy</p>
              </>
            )}
          </div>
        </div>
      )}

      {/* Main sections grid */}
      <div>
        <h2 className="text-xs font-bold uppercase tracking-widest text-gray-400 dark:text-gray-500 mb-3">
          {isHindi ? 'अध्ययन उपकरण' : 'Study Tools'}
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {sections.map((s) => (
            <SectionCard key={s.to} section={s} onClick={() => navigate(s.to)} />
          ))}
        </div>
      </div>

      {/* Mentorship section */}
      <div>
        <h2 className="text-xs font-bold uppercase tracking-widest text-gray-400 dark:text-gray-500 mb-3">
          Mentorship
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <SectionCard
            section={{
              to: '/questions',
              icon: <MessagesSquare size={20} />,
              title: 'Ask NAGA',
              description: 'Post doubts and get expert answers from your mentor',
              color: 'bg-teal-500',
            }}
            onClick={() => navigate('/questions')}
          />
          <SectionCard
            section={{
              to: '/classes',
              icon: <CalendarDays size={20} />,
              title: 'Classes',
              description: 'Join live sessions and review recorded classes',
              color: 'bg-pink-500',
            }}
            onClick={() => navigate('/classes')}
          />
        </div>
      </div>

      {/* Weak areas — only after diagnostic */}
      {diagnosticDone && weakAreas.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <BarChart3 size={18} className="text-primary" />
              {isHindi ? 'कमज़ोर विषय' : 'Focus Areas'}
            </h2>
            <button
              onClick={() => navigate('/study')}
              className="text-xs text-primary font-medium hover:underline"
            >
              Study now →
            </button>
          </div>
          <div className="space-y-2">
            {weakAreas.map((w) => {
              const pct = Math.round(w.score_pct * 100)
              return (
                <div key={`${w.subject}-${w.topic}`} className="flex items-center gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-xs font-medium text-gray-700 dark:text-gray-300 truncate">
                        {w.topic}
                        <span className="text-gray-400 dark:text-gray-500 font-normal"> · {w.subject}</span>
                      </span>
                      <span className={`text-xs font-bold ml-2 flex-shrink-0 ${pct < 30 ? 'text-red-500' : 'text-yellow-600'}`}>
                        {pct}%
                      </span>
                    </div>
                    <div className="h-1.5 bg-gray-100 dark:bg-gray-700 rounded-full">
                      <div
                        className={`h-1.5 rounded-full ${pct < 30 ? 'bg-red-400' : 'bg-yellow-400'}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Diagnostic done indicator */}
      {diagnosticDone && (
        <div className="flex items-center gap-2 text-xs text-green-600 dark:text-green-400">
          <CheckCircle2 size={14} />
          <span>Diagnostic complete · Personalised recommendations active</span>
        </div>
      )}
    </div>
  )
}
