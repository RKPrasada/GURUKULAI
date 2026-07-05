import { FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '@/services/api'
import AuthForm, { FormInput } from '@/components/AuthForm'
import { KeyRound, Mail, CheckCircle2 } from 'lucide-react'

export default function ForgotPasswordPage() {
  const navigate = useNavigate()
  const [step, setStep] = useState<1 | 2 | 3>(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [email, setEmail] = useState('')
  const [resetToken, setResetToken] = useState('')
  const [userId, setUserId] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  const handleEmailSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await api.forgotPassword(email)
      setResetToken(res.data.reset_token)
      setUserId(res.data.user_id)
      setStep(2)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Could not find an account with that email.')
    } finally {
      setLoading(false)
    }
  }

  const handleResetSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }
    setLoading(true)
    try {
      await api.resetPassword(userId, resetToken, newPassword, confirmPassword)
      setStep(3)
      setTimeout(() => navigate('/login'), 2500)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Reset failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  // Success screen — no form needed
  if (step === 3) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 px-4">
        <div className="w-full max-w-md bg-white dark:bg-gray-800 rounded-lg shadow-md p-10 text-center">
          <CheckCircle2 size={56} className="text-green-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">Password reset!</h2>
          <p className="text-gray-500 dark:text-gray-400 text-sm mb-6">
            Your password has been updated. Redirecting to login…
          </p>
          <Link
            to="/login"
            className="inline-block bg-primary text-white font-semibold px-6 py-2 rounded-lg hover:bg-primary/90 transition"
          >
            Go to Login
          </Link>
        </div>
      </div>
    )
  }

  return (
    <AuthForm
      title={step === 1 ? 'Reset your password' : 'Set new password'}
      onSubmit={step === 1 ? handleEmailSubmit : handleResetSubmit}
      loading={loading}
      error={error}
    >
      {step === 1 ? (
        <>
          <div className="flex items-center gap-3 mb-5 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg">
            <Mail size={18} className="text-blue-500 shrink-0" />
            <p className="text-sm text-blue-800 dark:text-blue-200">
              Enter the email address you registered with. We'll generate a reset token for you.
            </p>
          </div>
          <FormInput
            label="Email address"
            type="email"
            placeholder="your@email.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <div className="text-center pt-2">
            <Link to="/login" className="text-sm text-primary hover:underline">
              ← Back to Login
            </Link>
          </div>
        </>
      ) : (
        <>
          <div className="flex items-center gap-3 mb-5 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded-lg">
            <KeyRound size={18} className="text-green-600 shrink-0" />
            <p className="text-sm text-green-800 dark:text-green-200">
              Token verified for <strong>{email}</strong>. Choose your new password below.
            </p>
          </div>
          <FormInput
            label="New Password"
            type="password"
            placeholder="At least 8 characters"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
          />
          <FormInput
            label="Confirm New Password"
            type="password"
            placeholder="Repeat your new password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
          />
          <div className="text-center pt-2">
            <button
              type="button"
              onClick={() => { setStep(1); setError('') }}
              className="text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
            >
              ← Use a different email
            </button>
          </div>
        </>
      )}
    </AuthForm>
  )
}
