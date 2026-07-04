import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'
import {
  LogOut, Key, Menu, X,
  Home, Target, BookOpen, PenLine, ClipboardList, BarChart3,
  MessagesSquare, CalendarDays,
  LayoutDashboard, Settings, HelpCircle, MessageSquarePlus,
} from 'lucide-react'
import { useState } from 'react'
import NotificationBell from '@/components/NotificationBell'

const EXAM_LABEL: Record<string, string> = {
  rrb_ntpc: 'RRB NTPC',
  rrb_alp: 'RRB ALP',
  rrb_group_d: 'RRB Group D',
  rrb_technician: 'RRB Technician',
  rrb_je: 'RRB JE',
  nda: 'NDA',
  jee: 'JEE Mains',
  neet: 'NEET',
}

interface NavItem {
  to: string
  icon: React.ReactNode
  label: string
  badge?: string
}

function NavLink({ to, icon, label, badge, onClick }: NavItem & { onClick?: () => void }) {
  const navigate = useNavigate()
  const location = useLocation()
  const active = location.pathname === to

  return (
    <button
      onClick={() => { navigate(to); onClick?.() }}
      className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${
        active
          ? 'bg-primary text-white shadow-sm'
          : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/60'
      }`}
    >
      <span className={active ? 'text-white' : 'text-gray-400 dark:text-gray-500'}>{icon}</span>
      <span className="flex-1 text-left">{label}</span>
      {badge && (
        <span className={`text-xs px-1.5 py-0.5 rounded-full font-semibold ${
          active ? 'bg-white/20 text-white' : 'bg-primary/10 text-primary'
        }`}>{badge}</span>
      )}
    </button>
  )
}

function SidebarContent({ student, onNavigate }: { student: any; onNavigate?: () => void }) {
  const isNaga = student?.user_id === 'naga'
  const examLabel = EXAM_LABEL[student?.exam_target] ?? student?.exam_target?.toUpperCase()

  return (
    <div className="flex flex-col h-full">
      {/* User card */}
      <div className="px-4 py-4 border-b border-gray-200 dark:border-gray-700 mb-2">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
            <span className="text-primary font-bold text-base">
              {student?.full_name?.[0]?.toUpperCase() ?? '?'}
            </span>
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-gray-900 dark:text-white truncate">
              {student?.full_name}
            </p>
            {examLabel && (
              <span className="inline-block text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full mt-0.5 font-medium">
                {examLabel}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Nav items */}
      <nav className="flex-1 px-3 space-y-1 overflow-y-auto">
        {isNaga ? (
          <>
            <NavLink to="/"        icon={<Home size={18}/>}          label="Home"             onClick={onNavigate} />
            <NavLink to="/naga"    icon={<LayoutDashboard size={18}/>} label="Mentor Dashboard" onClick={onNavigate} />
            <NavLink to="/questions" icon={<HelpCircle size={18}/>}  label="Questions"        onClick={onNavigate} />
            <NavLink to="/classes" icon={<CalendarDays size={18}/>}  label="Classes"          onClick={onNavigate} />
            <NavLink to="/admin"   icon={<Settings size={18}/>}      label="Admin"            onClick={onNavigate} />
          </>
        ) : (
          <>
            {/* ── Study tools ── */}
            <NavLink to="/"           icon={<Home size={18}/>}          label="Home"          onClick={onNavigate} />
            <NavLink to="/diagnostic" icon={<Target size={18}/>}        label="Diagnostics"   onClick={onNavigate}
              badge={!student?.diagnostic_done ? 'Start' : undefined} />
            <NavLink to="/study-plan" icon={<CalendarDays size={18}/>}    label="Study Plan"    onClick={onNavigate} />
            <NavLink to="/study"      icon={<BookOpen size={18}/>}       label="AI Tutor"      onClick={onNavigate} />
            <NavLink to="/test"       icon={<PenLine size={18}/>}        label="Practice Test" onClick={onNavigate} />
            <NavLink to="/mock-test"  icon={<ClipboardList size={18}/>} label="Mock Test"     onClick={onNavigate} />
            <NavLink to="/progress"   icon={<BarChart3 size={18}/>}     label="Progress"      onClick={onNavigate} />

            {/* ── Mentorship ── */}
            <div className="pt-3 mt-2 border-t border-gray-200 dark:border-gray-700">
              <p className="px-4 pb-1 text-[10px] font-bold uppercase tracking-widest text-gray-400 dark:text-gray-500">
                Mentorship
              </p>
              <NavLink to="/questions" icon={<MessagesSquare size={18}/>}  label="Ask NAGA" onClick={onNavigate} />
              <NavLink to="/classes"   icon={<CalendarDays size={18}/>}    label="Classes"  onClick={onNavigate} />
            </div>

            {/* ── Account ── */}
            <div className="pt-3 mt-2 border-t border-gray-200 dark:border-gray-700">
              <p className="px-4 pb-1 text-[10px] font-bold uppercase tracking-widest text-gray-400 dark:text-gray-500">
                Account
              </p>
              <NavLink to="/settings" icon={<Settings size={18}/>}         label="Settings"    onClick={onNavigate} />
              <NavLink to="/feedback" icon={<MessageSquarePlus size={18}/>} label="Feedback"   onClick={onNavigate} />
              <NavLink to="/help"     icon={<HelpCircle size={18}/>}       label="Help & Contact" onClick={onNavigate} />
            </div>
          </>
        )}
      </nav>
    </div>
  )
}

export default function Layout() {
  const student = useAuthStore((state) => state.student)
  const logout = useAuthStore((state) => state.logout)
  const navigate = useNavigate()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [showChangePw, setShowChangePw] = useState(false)

  const handleLogout = () => { logout(); navigate('/login') }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex flex-col">
      {/* ── Top header bar ── */}
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 z-20 sticky top-0">
        <div className="flex items-center justify-between px-4 h-14">
          {/* Logo */}
          <div className="flex items-center gap-2">
            {/* Mobile hamburger */}
            <button
              className="md:hidden p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 mr-1"
              onClick={() => setMobileOpen(!mobileOpen)}
            >
              {mobileOpen ? <X size={22} /> : <Menu size={22} />}
            </button>
            <span className="text-xl">📚</span>
            <span className="text-lg font-bold text-primary tracking-tight">Gurukul AI</span>
          </div>

          {/* Right controls */}
          <div className="flex items-center gap-1">
            <span className="hidden sm:block text-sm text-gray-500 dark:text-gray-400 mr-2">
              {student?.full_name}
            </span>
            <NotificationBell />
            <button
              onClick={() => setShowChangePw(!showChangePw)}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
              title="Change Password"
            >
              <Key size={18} className="text-gray-500 dark:text-gray-400" />
            </button>
            <button
              onClick={handleLogout}
              className="p-2 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg"
              title="Logout"
            >
              <LogOut size={18} className="text-red-500" />
            </button>
          </div>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* ── Desktop sidebar ── */}
        <aside className="hidden md:flex flex-col w-56 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 shrink-0 sticky top-14 h-[calc(100vh-3.5rem)] overflow-y-auto">
          <SidebarContent student={student} />
        </aside>

        {/* ── Mobile drawer overlay ── */}
        {mobileOpen && (
          <>
            <div
              className="fixed inset-0 bg-black/40 z-30 md:hidden"
              onClick={() => setMobileOpen(false)}
            />
            <aside className="fixed top-14 left-0 bottom-0 w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 z-40 md:hidden overflow-y-auto shadow-xl">
              <SidebarContent student={student} onNavigate={() => setMobileOpen(false)} />
            </aside>
          </>
        )}

        {/* ── Main content ── */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6">
          <div className="max-w-4xl mx-auto">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
