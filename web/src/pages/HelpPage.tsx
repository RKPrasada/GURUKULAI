import { Mail, Phone, MessageSquare, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react'
import { useState } from 'react'

const FAQS = [
  {
    q: 'What is the Diagnostic Test?',
    a: 'The Diagnostic Test is a placement test that identifies your strong and weak areas across all subjects. It helps Gurukul AI personalise your study plan and question difficulty. You should take it first before starting practice.',
  },
  {
    q: 'How is Practice Test different from Mock Test?',
    a: 'Practice Tests focus on specific topics and adapt to your skill level — no time pressure. Mock Tests simulate the actual exam: full paper, strict time limit, and negative marking as per the real pattern.',
  },
  {
    q: 'How do I ask NAGA a question?',
    a: 'Go to Ask NAGA from the sidebar. Type your doubt and submit — NAGA (your mentor) will reply, usually within a few hours. You can also see all answered questions posted by other students.',
  },
  {
    q: 'Can I change my exam target after registration?',
    a: 'Exam target change requires a reset of your diagnostic and study plan. Please contact us at support@gurukul-ai.app and we will update it for you.',
  },
  {
    q: 'How does the question bank grow?',
    a: 'Every time you or another student takes a test, Gurukul AI generates 20 new questions via AI and saves them to the question bank. The bank grows toward 1000 questions per exam so you always get fresh questions.',
  },
  {
    q: 'Is my data private?',
    a: 'Yes. Your progress, weakness map and answers are stored securely and are only visible to you and your assigned mentor (NAGA). We never share personal data with third parties.',
  },
]

function FAQ({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-gray-50 dark:hover:bg-gray-700/40 transition"
      >
        <span className="text-sm font-medium text-gray-800 dark:text-gray-200 pr-4">{q}</span>
        {open ? <ChevronUp size={16} className="text-gray-400 flex-shrink-0" /> : <ChevronDown size={16} className="text-gray-400 flex-shrink-0" />}
      </button>
      {open && (
        <div className="px-5 pb-4 text-sm text-gray-600 dark:text-gray-400 border-t border-gray-100 dark:border-gray-700 pt-3">
          {a}
        </div>
      )}
    </div>
  )
}

export default function HelpPage() {
  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900 dark:text-white">Help & Contact Us</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Find answers below or reach out — we're here to help.
        </p>
      </div>

      {/* Contact cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <a href="mailto:support@gurukul-ai.app"
          className="flex flex-col items-center gap-2 bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-xl p-5 hover:shadow-md transition text-center">
          <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center">
            <Mail size={18} className="text-blue-600 dark:text-blue-400" />
          </div>
          <p className="text-sm font-semibold text-gray-800 dark:text-gray-200">Email</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">support@gurukul-ai.app</p>
        </a>

        <a href="https://wa.me/919000000000" target="_blank" rel="noreferrer"
          className="flex flex-col items-center gap-2 bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-xl p-5 hover:shadow-md transition text-center">
          <div className="w-10 h-10 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center">
            <MessageSquare size={18} className="text-green-600 dark:text-green-400" />
          </div>
          <p className="text-sm font-semibold text-gray-800 dark:text-gray-200">WhatsApp</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">Chat with us</p>
        </a>

        <div className="flex flex-col items-center gap-2 bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-xl p-5 text-center">
          <div className="w-10 h-10 bg-orange-100 dark:bg-orange-900/30 rounded-full flex items-center justify-center">
            <Phone size={18} className="text-orange-600 dark:text-orange-400" />
          </div>
          <p className="text-sm font-semibold text-gray-800 dark:text-gray-200">Phone</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">Mon–Sat 9 am – 6 pm IST</p>
        </div>
      </div>

      {/* FAQ */}
      <div>
        <h2 className="text-sm font-bold uppercase tracking-widest text-gray-400 dark:text-gray-500 mb-3">
          Frequently Asked Questions
        </h2>
        <div className="space-y-2">
          {FAQS.map((f) => <FAQ key={f.q} {...f} />)}
        </div>
      </div>

      {/* Docs link */}
      <div className="flex items-center justify-center">
        <a href="https://github.com/rkprasada/gurukul-ai" target="_blank" rel="noreferrer"
          className="flex items-center gap-1.5 text-sm text-primary font-medium hover:underline">
          View on GitHub <ExternalLink size={13} />
        </a>
      </div>
    </div>
  )
}
