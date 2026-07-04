import { useState } from 'react'
import { useAuthStore } from '@/store/auth'
import { Star, Send, CheckCircle2 } from 'lucide-react'
const CATEGORIES = ['Content Quality', 'App Experience', 'Mentor (NAGA)', 'Question Bank', 'Other']

export default function FeedbackPage() {
  const student = useAuthStore((s) => s.student)
  const [rating, setRating] = useState(0)
  const [hovered, setHovered] = useState(0)
  const [category, setCategory] = useState(CATEGORIES[0])
  const [message, setMessage] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState('')

  const submit = () => {
    if (!message.trim()) { setError('Please write your feedback before submitting.'); return }
    if (rating === 0) { setError('Please give a star rating.'); return }
    setError('')
    // Feedback endpoint to be wired in next sprint; store locally for now
    console.info('Feedback', { user_id: student?.user_id, rating, category, message })
    setSubmitted(true)
  }

  if (submitted) {
    return (
      <div className="max-w-md mx-auto text-center py-16">
        <CheckCircle2 size={48} className="text-green-500 mx-auto mb-4" />
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-2">Thank you!</h2>
        <p className="text-gray-500 dark:text-gray-400">Your feedback helps us improve Gurukul AI for every student.</p>
        <button onClick={() => { setSubmitted(false); setRating(0); setMessage('') }}
          className="mt-6 text-sm text-primary font-medium hover:underline">
          Submit another →
        </button>
      </div>
    )
  }

  return (
    <div className="max-w-xl mx-auto space-y-4">
      <h1 className="text-xl font-bold text-gray-900 dark:text-white">Share Feedback</h1>
      <p className="text-sm text-gray-500 dark:text-gray-400">
        We read every message. Your feedback shapes what we build next.
      </p>

      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-6 space-y-5">
        {/* Star rating */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Overall Rating</label>
          <div className="flex gap-1">
            {[1, 2, 3, 4, 5].map((s) => (
              <button key={s} onClick={() => setRating(s)}
                onMouseEnter={() => setHovered(s)} onMouseLeave={() => setHovered(0)}>
                <Star size={28}
                  className={`transition ${(hovered || rating) >= s ? 'text-yellow-400 fill-yellow-400' : 'text-gray-300 dark:text-gray-600'}`} />
              </button>
            ))}
          </div>
        </div>

        {/* Category */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Category</label>
          <div className="flex flex-wrap gap-2">
            {CATEGORIES.map((c) => (
              <button key={c} onClick={() => setCategory(c)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium border transition ${
                  category === c
                    ? 'bg-primary text-white border-primary'
                    : 'border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:border-primary/60'
                }`}>{c}</button>
            ))}
          </div>
        </div>

        {/* Message */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Your Feedback</label>
          <textarea
            rows={5}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Tell us what's working well or what can be better..."
            className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary resize-none"
          />
          <p className="text-xs text-gray-400 mt-1 text-right">{message.length}/500</p>
        </div>

        {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

        <button onClick={submit}
          className="w-full flex items-center justify-center gap-2 bg-primary hover:bg-primary/90 text-white font-semibold py-2.5 rounded-xl transition">
          <Send size={16} />Submit Feedback
        </button>
      </div>
    </div>
  )
}
