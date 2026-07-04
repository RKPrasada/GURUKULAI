import { FormEvent, ReactNode } from 'react'

interface AuthFormProps {
  title: string
  onSubmit: (e: FormEvent) => void
  loading?: boolean
  children: ReactNode
  error?: string
  success?: string
}

export default function AuthForm({
  title,
  onSubmit,
  loading = false,
  children,
  error,
  success,
}: AuthFormProps) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 px-4">
      <div className="w-full max-w-md bg-white dark:bg-gray-800 rounded-lg shadow-md p-8">
        <div className="text-center mb-8">
          <h1 className="text-4xl mb-2">📚</h1>
          <h2 className="text-3xl font-bold text-primary mb-1">Gurukul AI</h2>
          <p className="text-gray-500 dark:text-gray-400 text-sm mb-4">
            AI Tutor for Indian Competitive Exams
          </p>

          {/* Sanskrit shloka — Hitopadesha 1.1 */}
          <div className="mx-auto mb-5 px-4 py-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700/40 rounded-xl">
            <p
              className="text-sm font-medium text-amber-900 dark:text-amber-200 leading-loose tracking-wide"
              lang="sa"
            >
              विद्या ददाति विनयं विनयाद् याति पात्रताम् ।
              <br />
              पात्रत्वात् धनमाप्नोति धनाद्धर्मं ततः सुखम् ॥
            </p>
            <p className="text-[10px] text-amber-600 dark:text-amber-400 mt-1.5 italic leading-snug">
              Knowledge gives humility; humility, worthiness; worthiness, prosperity;
              prosperity, virtue; virtue, happiness.
            </p>
            <p className="text-[10px] text-amber-400 dark:text-amber-500 mt-0.5">— Hitopadesha</p>
          </div>

          <h3 className="text-xl font-semibold text-gray-800 dark:text-gray-100">{title}</h3>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-100 rounded-lg text-sm">
            ❌ {error}
          </div>
        )}

        {success && (
          <div className="mb-4 p-3 bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-100 rounded-lg text-sm">
            ✅ {success}
          </div>
        )}

        <form onSubmit={onSubmit} className="space-y-4">
          {children}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-primary hover:bg-primary/90 disabled:bg-gray-400 text-white font-semibold py-2 px-4 rounded-lg transition"
          >
            {loading ? '⏳ Processing...' : 'Submit'}
          </button>
        </form>
      </div>
    </div>
  )
}

export function FormInput({
  label,
  type = 'text',
  placeholder,
  required = false,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement> & {
  label: string
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      <input
        type={type}
        placeholder={placeholder}
        required={required}
        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-primary focus:border-transparent outline-none"
        {...props}
      />
    </div>
  )
}

export function FormSelect({
  label,
  options,
  required = false,
  ...props
}: React.SelectHTMLAttributes<HTMLSelectElement> & {
  label: string
  options: { value: string; label: string }[]
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      <select
        required={required}
        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent outline-none"
        {...props}
      >
        <option value="">Select an option</option>
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  )
}
