import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'
import api from '@/services/api'
import { ChevronRight, CheckCircle, XCircle, Trophy, AlertTriangle, BookOpen } from 'lucide-react'

interface Question {
  question_id: string
  subject: string
  topic: string
  question_text_en: string
  question_text_hi: string
  options: string[]
  correct_index: number
  difficulty: number
  explanation_en?: string
}

interface DiagnosticSession {
  session_id: string
  questions: Question[]
  current_index: number
}

interface WeaknessEntry {
  subject: string
  topic: string
  score_pct: number
  attempts: number
}

interface DiagnosticResult {
  total_correct: number
  total_questions: number
  score_pct: number
  weakness_map: WeaknessEntry[]
  next_steps: string
  summary: string
  questions: Question[]
  answers: { [question_id: string]: number }
}

// ─── Results Screen ───────────────────────────────────────────────────────────
function ResultsScreen({ result, onContinue }: { result: DiagnosticResult; onContinue: () => void }) {
  const pct = Math.round(result.score_pct * 100)
  const scoreColor = pct >= 70 ? 'text-green-600' : pct >= 40 ? 'text-yellow-600' : 'text-red-600'
  const scoreBg = pct >= 70 ? 'bg-green-50 border-green-200' : pct >= 40 ? 'bg-yellow-50 border-yellow-200' : 'bg-red-50 border-red-200'

  const weakAreas = result.weakness_map
    .filter((w) => w.score_pct < 0.6)
    .sort((a, b) => a.score_pct - b.score_pct)
    .slice(0, 6)

  return (
    <div className="max-w-3xl mx-auto space-y-6 pb-12">
      {/* Score Banner */}
      <div className={`rounded-xl border-2 p-6 text-center ${scoreBg} dark:bg-gray-800 dark:border-gray-700`}>
        <Trophy className={`mx-auto mb-2 ${scoreColor}`} size={40} />
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-1">Diagnostic Complete</h2>
        <p className={`text-5xl font-extrabold ${scoreColor} my-3`}>{pct}%</p>
        <p className="text-gray-700 dark:text-gray-300 text-lg">
          {result.total_correct} correct out of {result.total_questions} questions
        </p>
        <p className="mt-3 text-sm text-gray-600 dark:text-gray-400 italic">{result.next_steps}</p>
      </div>

      {/* Weak Areas */}
      {weakAreas.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-5">
          <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2 mb-4">
            <AlertTriangle size={20} className="text-orange-500" />
            Topics Needing Focus
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {weakAreas.map((w, i) => (
              <div key={i} className="flex items-center gap-3 bg-orange-50 dark:bg-orange-900/20 rounded-lg p-3">
                <div className="flex-shrink-0 w-10 h-10 rounded-full bg-orange-100 dark:bg-orange-900/40 flex items-center justify-center">
                  <span className="text-sm font-bold text-orange-700 dark:text-orange-400">
                    {Math.round(w.score_pct * 100)}%
                  </span>
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-800 dark:text-gray-200">{w.topic}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">{w.subject}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Question-by-Question Review */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-5">
        <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2 mb-5">
          <BookOpen size={20} className="text-primary" />
          Answer Review
        </h3>
        <div className="space-y-6">
          {result.questions.map((q, qi) => {
            const userAnswer = result.answers[q.question_id]
            const answered = userAnswer !== undefined
            const correct = answered && userAnswer === q.correct_index

            return (
              <div key={q.question_id} className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
                {/* Question header */}
                <div className={`flex items-start gap-3 p-4 ${correct ? 'bg-green-50 dark:bg-green-900/20' : answered ? 'bg-red-50 dark:bg-red-900/20' : 'bg-gray-50 dark:bg-gray-700/40'}`}>
                  <div className="flex-shrink-0 mt-0.5">
                    {correct ? (
                      <CheckCircle size={20} className="text-green-600 dark:text-green-400" />
                    ) : answered ? (
                      <XCircle size={20} className="text-red-600 dark:text-red-400" />
                    ) : (
                      <div className="w-5 h-5 rounded-full border-2 border-gray-400" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-semibold text-gray-500 dark:text-gray-400">Q{qi + 1}</span>
                      <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full">
                        {q.subject} → {q.topic}
                      </span>
                    </div>
                    <p className="text-gray-900 dark:text-white font-medium">{q.question_text_en}</p>
                  </div>
                </div>

                {/* Options */}
                <div className="p-4 space-y-2">
                  {q.options.map((opt, oi) => {
                    const isCorrect = oi === q.correct_index
                    const isUserPick = answered && oi === userAnswer
                    const isWrongPick = isUserPick && !isCorrect

                    let cls = 'border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/30 text-gray-700 dark:text-gray-300'
                    if (isCorrect) cls = 'border-green-500 bg-green-50 dark:bg-green-900/30 text-green-800 dark:text-green-200 font-semibold'
                    if (isWrongPick) cls = 'border-red-500 bg-red-50 dark:bg-red-900/30 text-red-800 dark:text-red-200 font-semibold'

                    return (
                      <div key={oi} className={`flex items-center gap-3 p-3 rounded-lg border-2 ${cls}`}>
                        <div className="flex-shrink-0">
                          {isCorrect ? (
                            <CheckCircle size={18} className="text-green-600 dark:text-green-400" />
                          ) : isWrongPick ? (
                            <XCircle size={18} className="text-red-600 dark:text-red-400" />
                          ) : (
                            <div className="w-4 h-4 rounded-full border border-gray-300 dark:border-gray-600" />
                          )}
                        </div>
                        <span className="text-sm">{opt}</span>
                        {isCorrect && (
                          <span className="ml-auto text-xs font-bold text-green-700 dark:text-green-400 whitespace-nowrap">✓ Correct</span>
                        )}
                        {isWrongPick && (
                          <span className="ml-auto text-xs font-bold text-red-700 dark:text-red-400 whitespace-nowrap">✗ Your answer</span>
                        )}
                      </div>
                    )
                  })}

                  {/* Explanation */}
                  {q.explanation_en && (
                    <div className="mt-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
                      <p className="text-xs font-semibold text-blue-700 dark:text-blue-400 mb-1">Explanation</p>
                      <p className="text-sm text-blue-800 dark:text-blue-200">{q.explanation_en}</p>
                    </div>
                  )}

                  {/* Skipped notice */}
                  {!answered && (
                    <p className="text-xs text-gray-500 dark:text-gray-400 italic mt-1">Not attempted</p>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Continue Button */}
      <button
        onClick={onContinue}
        className="w-full bg-primary hover:bg-primary/90 text-white font-bold py-3 px-6 rounded-xl transition text-lg"
      >
        Continue to Study Plan →
      </button>
    </div>
  )
}

// ─── Main Diagnostic Page ─────────────────────────────────────────────────────
export default function DiagnosticPage() {
  const navigate = useNavigate()
  const updateStudent = useAuthStore((state) => state.updateStudent)
  const [session, setSession] = useState<DiagnosticSession | null>(null)
  const [selectedAnswers, setSelectedAnswers] = useState<{ [key: string]: number }>({})
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<DiagnosticResult | null>(null)

  useEffect(() => {
    initDiagnostic()
  }, [])

  const initDiagnostic = async () => {
    try {
      const response = await api.startDiagnostic()
      setSession({ ...response.data, current_index: 0 })
      setLoading(false)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start diagnostic')
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-primary mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400">Loading diagnostic test...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-red-800 dark:text-red-100 mb-2">Error</h2>
        <p className="text-red-700 dark:text-red-200 mb-4">{error}</p>
        <button
          onClick={() => navigate('/')}
          className="bg-primary hover:bg-primary/90 text-white font-semibold py-2 px-4 rounded-lg"
        >
          Back to Home
        </button>
      </div>
    )
  }

  // Show results screen after submission
  if (result) {
    return (
      <ResultsScreen
        result={result}
        onContinue={() => navigate('/')}
      />
    )
  }

  if (!session) return null

  const current = session.questions[session.current_index]
  const progress = ((session.current_index + 1) / session.questions.length) * 100
  const isAnswered = current.question_id in selectedAnswers
  const selectedIndex = selectedAnswers[current.question_id]
  const answeredCount = Object.keys(selectedAnswers).length

  const handleSelectAnswer = (optionIndex: number) => {
    setSelectedAnswers({ ...selectedAnswers, [current.question_id]: optionIndex })
  }

  const handleNext = async () => {
    if (session.current_index === session.questions.length - 1) {
      await submitDiagnostic()
    } else {
      setSession({ ...session, current_index: session.current_index + 1 })
    }
  }

  const submitDiagnostic = async () => {
    setSubmitting(true)
    try {
      const response = await api.submitDiagnostic(session.session_id, selectedAnswers)
      updateStudent({
        ...useAuthStore.getState().student!,
        diagnostic_done: true,
        weakness_map: response.data.weakness_map,
      })
      // Show results instead of navigating away
      setResult({
        ...response.data,
        questions: session.questions,
        answers: selectedAnswers,
      })
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to submit diagnostic')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      {/* Progress Bar */}
      <div className="mb-6">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">
            Question {session.current_index + 1} of {session.questions.length}
          </span>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {answeredCount}/{session.questions.length} answered
          </span>
        </div>
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
          <div
            className="bg-primary h-2 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Question Card */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-8 mb-6">
        <div className="mb-6">
          <div className="inline-block px-3 py-1 bg-primary/10 text-primary text-xs font-semibold rounded-full mb-3">
            {current.subject} → {current.topic}
          </div>
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4 leading-relaxed">
            {current.question_text_en}
          </h2>
        </div>

        {/* Options */}
        <div className="space-y-3 mb-8">
          {current.options.map((option, index) => (
            <button
              key={index}
              onClick={() => handleSelectAnswer(index)}
              className={`w-full text-left p-4 border-2 rounded-lg transition ${
                selectedIndex === index
                  ? 'border-primary bg-primary/5'
                  : 'border-gray-200 dark:border-gray-700 hover:border-primary/50'
              }`}
            >
              <div className="flex items-center gap-4">
                <div
                  className={`flex-shrink-0 w-6 h-6 rounded-full border-2 flex items-center justify-center text-sm font-bold ${
                    selectedIndex === index
                      ? 'border-primary bg-primary text-white'
                      : 'border-gray-300 dark:border-gray-600 text-gray-400'
                  }`}
                >
                  {selectedIndex === index ? <CheckCircle size={16} /> : String.fromCharCode(65 + index)}
                </div>
                <span className="text-gray-800 dark:text-gray-200">{option}</span>
              </div>
            </button>
          ))}
        </div>

        {/* Navigation */}
        <div className="flex gap-4">
          {session.current_index > 0 && (
            <button
              onClick={() => setSession({ ...session, current_index: session.current_index - 1 })}
              className="flex-1 py-2 px-4 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition"
            >
              ← Previous
            </button>
          )}
          <button
            onClick={handleNext}
            disabled={!isAnswered || submitting}
            className="flex-1 bg-primary hover:bg-primary/90 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-semibold py-2 px-4 rounded-lg transition flex items-center justify-center gap-2"
          >
            {session.current_index === session.questions.length - 1 ? (
              submitting ? (
                <><span className="animate-spin">⏳</span> Submitting...</>
              ) : (
                'Submit Test'
              )
            ) : (
              <>Next <ChevronRight size={18} /></>
            )}
          </button>
        </div>
      </div>

      {/* Question Map (mini navigator) */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
        <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-3">Question Navigator</p>
        <div className="flex flex-wrap gap-2">
          {session.questions.map((q, i) => {
            const isAnsweredQ = q.question_id in selectedAnswers
            const isCurrent = i === session.current_index
            return (
              <button
                key={i}
                onClick={() => setSession({ ...session, current_index: i })}
                className={`w-8 h-8 rounded text-xs font-bold transition ${
                  isCurrent
                    ? 'bg-primary text-white ring-2 ring-primary ring-offset-1'
                    : isAnsweredQ
                    ? 'bg-green-100 dark:bg-green-900/40 text-green-800 dark:text-green-300'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                }`}
              >
                {i + 1}
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
