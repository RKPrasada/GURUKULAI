import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'
import api from '@/services/api'
import { ChevronRight, Clock, CheckCircle, Zap, Loader2 } from 'lucide-react'

interface Question {
  question_id: string
  subject: string
  topic: string
  question_text_en: string
  question_text_hi: string
  options: string[]
  correct_index: number
  difficulty: number
  explanation_en: string
  explanation_hi: string | null
}

interface TestState {
  session_id: string
  total: number
  current_question: Question
  answered: number
  score: number
  session_complete: boolean
  correct?: boolean
  correct_index?: number
  explanation_en?: string
}

export default function TestPage() {
  const navigate = useNavigate()
  const updateStudent = useAuthStore((state) => state.updateStudent)
  const student = useAuthStore((state) => state.student)
  const [difficulty, setDifficulty] = useState('adaptive')
  const [testState, setTestState] = useState<TestState | null>(null)
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [showDifficultySelect, setShowDifficultySelect] = useState(true)
  const [showFeedback, setShowFeedback] = useState(false)

  const startAssessment = async () => {
    setLoading(true)
    try {
      const response = await api.startAssessment(difficulty)
      const data = response.data
      setTestState({
        session_id: data.session_id,
        total: data.total,
        current_question: data.first_question,
        answered: 0,
        score: 0,
        session_complete: false,
      })
      setShowDifficultySelect(false)
    } catch (err: any) {
      console.error('Failed to start assessment:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmitAnswer = async () => {
    if (selectedIndex === null || !testState) return
    setSubmitting(true)
    try {
      const response = await api.submitAnswer(
        testState.session_id,
        testState.current_question.question_id,
        selectedIndex
      )
      const data = response.data
      setTestState({
        ...testState,
        answered: data.answered,
        score: data.score,
        session_complete: data.session_complete,
        correct: data.correct,
        correct_index: data.correct_index,
        explanation_en: data.explanation_en,
        current_question: data.next_question || testState.current_question,
      })
      setShowFeedback(true)
    } catch (err: any) {
      console.error('Failed to submit answer:', err)
    } finally {
      setSubmitting(false)
    }
  }

  const handleNext = () => {
    if (testState?.session_complete) {
      updateStudent({
        ...student!,
        total_questions_attempted: (student?.total_questions_attempted || 0) + testState.total,
      })
      navigate('/progress')
    } else {
      setSelectedIndex(null)
      setShowFeedback(false)
    }
  }

  if (showDifficultySelect) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">🎯 Practice Test</h1>
          <p className="text-gray-600 dark:text-gray-400 mb-8">
            Choose a difficulty level and test your knowledge
          </p>

          <div className="space-y-3 mb-8">
            {[
              { value: 'easy', label: 'Easy', desc: 'Fundamental concepts' },
              { value: 'medium', label: 'Medium', desc: 'Balanced difficulty' },
              { value: 'hard', label: 'Hard', desc: 'Advanced topics' },
              { value: 'adaptive', label: 'Adaptive', desc: 'Matches your level' },
            ].map((opt) => (
              <button
                key={opt.value}
                onClick={() => setDifficulty(opt.value)}
                className={`w-full text-left p-4 border-2 rounded-lg transition ${
                  difficulty === opt.value ? 'border-primary bg-primary/5' : 'border-gray-200 dark:border-gray-700'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-white">{opt.label}</h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">{opt.desc}</p>
                  </div>
                  <div
                    className={`w-5 h-5 rounded-full border-2 ${
                      difficulty === opt.value ? 'border-primary bg-primary' : 'border-gray-300'
                    }`}
                  ></div>
                </div>
              </button>
            ))}
          </div>

          <button
            onClick={startAssessment}
            disabled={loading}
            className="w-full bg-primary hover:bg-primary/90 disabled:bg-gray-400 text-white font-semibold py-3 px-6 rounded-lg transition flex items-center justify-center gap-2"
          >
            {loading
              ? <><Loader2 size={16} className="animate-spin" /> Generating questions…</>
              : <><span>Start Test</span> <Zap size={20} /></>
            }
          </button>
        </div>
      </div>
    )
  }

  if (!testState) return null

  if (testState.session_complete && showFeedback) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-8 text-center">
          <div className="text-6xl mb-4">🎉</div>
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">Test Complete!</h2>
          <p className="text-xl text-gray-700 dark:text-gray-300 mb-2">
            Score: {testState.score} / {testState.total}
          </p>
          <p className="text-gray-600 dark:text-gray-400 mb-8">
            Accuracy: {((testState.score / testState.total) * 100).toFixed(0)}%
          </p>
          <button
            onClick={handleNext}
            className="bg-primary hover:bg-primary/90 text-white font-semibold py-3 px-8 rounded-lg transition"
          >
            View Progress →
          </button>
        </div>
      </div>
    )
  }

  const q = testState.current_question
  const progress = testState.total > 0 ? (testState.answered / testState.total) * 100 : 0

  if (!q) {
    return (
      <div className="max-w-2xl mx-auto text-center p-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg">
        <h2 className="text-xl font-bold text-red-500 mb-4">No Questions Available</h2>
        <p className="text-gray-600 dark:text-gray-400 mb-6">We couldn't generate questions for this topic at this difficulty level. Please try a different topic or difficulty.</p>
        <button
          onClick={() => { setTestState(null); setShowDifficultySelect(true); }}
          className="bg-primary hover:bg-primary/90 text-white font-semibold py-2 px-6 rounded-lg transition"
        >
          Go Back
        </button>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-6">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">
            Question {testState.answered + 1} of {testState.total}
          </span>
          <div className="flex items-center gap-1 text-sm text-gray-600 dark:text-gray-400">
            <Clock size={16} />
            {Math.ceil((testState.total - testState.answered) * 1.2)} min
          </div>
        </div>
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
          <div
            className="bg-primary h-2 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          ></div>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-8 mb-6">
        <div className="mb-6">
          <div className="inline-block px-3 py-1 bg-secondary/10 text-secondary text-xs font-semibold rounded-full mb-3">
            {q.subject} · {q.topic}
          </div>
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">{q.question_text_en}</h2>
        </div>

        <div className="space-y-3 mb-8">
          {q.options.map((option, index) => {
            let cls = 'border-gray-200 dark:border-gray-700'
            if (showFeedback) {
              if (index === testState.correct_index) cls = 'border-green-500 bg-green-50 dark:bg-green-900/20'
              else if (index === selectedIndex) cls = 'border-red-500 bg-red-50 dark:bg-red-900/20'
            } else if (selectedIndex === index) {
              cls = 'border-primary bg-primary/5'
            }

            return (
              <button
                key={index}
                disabled={showFeedback}
                onClick={() => setSelectedIndex(index)}
                className={`w-full text-left p-4 border-2 rounded-lg transition ${cls} disabled:cursor-default`}
              >
                <div className="flex items-start gap-4">
                  <div
                    className={`flex-shrink-0 w-6 h-6 rounded-full border-2 flex items-center justify-center ${
                      selectedIndex === index ? 'border-primary bg-primary text-white' : 'border-gray-300'
                    }`}
                  >
                    {selectedIndex === index && <CheckCircle size={20} />}
                  </div>
                  <span className="text-gray-800 dark:text-gray-200">{option}</span>
                </div>
              </button>
            )
          })}
        </div>

        {showFeedback && testState.explanation_en && (
          <div className={`p-4 rounded-lg mb-6 ${testState.correct ? 'bg-green-50 dark:bg-green-900/20 border border-green-200' : 'bg-red-50 dark:bg-red-900/20 border border-red-200'}`}>
            <p className="font-semibold text-gray-900 dark:text-white mb-1">
              {testState.correct ? '✅ Correct!' : '❌ Incorrect'}
            </p>
            <p className="text-sm text-gray-700 dark:text-gray-300">{testState.explanation_en}</p>
          </div>
        )}

        <div className="flex justify-end">
          {!showFeedback ? (
            <button
              onClick={handleSubmitAnswer}
              disabled={selectedIndex === null || submitting}
              className="bg-primary hover:bg-primary/90 disabled:bg-gray-400 text-white font-semibold py-2 px-6 rounded-lg transition flex items-center gap-2"
            >
              {submitting
                ? <><Loader2 size={15} className="animate-spin" /> Checking…</>
                : <><span>Submit</span> <ChevronRight size={18} /></>
              }
            </button>
          ) : (
            <button
              onClick={handleNext}
              className="bg-primary hover:bg-primary/90 text-white font-semibold py-2 px-6 rounded-lg transition flex items-center gap-2"
            >
              {testState.session_complete ? 'Finish' : <><span>Next</span> <ChevronRight size={18} /></>}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
