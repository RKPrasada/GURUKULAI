import { FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '@/services/api'
import AuthForm, { FormInput } from '@/components/AuthForm'

export default function ForgotPasswordPage() {
  const navigate = useNavigate()
  const [step, setStep] = useState(1) // 1: email, 2: reset token
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [resetToken, setResetToken] = useState('')
  const [userId, setUserId] = useState('')

  const [email, setEmail] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  const handleEmailSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    setLoading(true)

    try {
      const response = await api.forgotPassword(email)
      setSuccess('Reset token generated!')
      setResetToken(response.data.reset_token)
      setUserId(response.data.user_id)
      setStep(2)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to send reset link')
    } finally {
      setLoading(false)
    }
  }

  const handleResetSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess('')

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    setLoading(true)

    try {
      await api.resetPassword(userId, resetToken, newPassword, confirmPassword)
      setSuccess('Password reset successful! Redirecting to login...')
      setTimeout(() => navigate('/login'), 2000)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Reset failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthForm
      title={step === 1 ? 'Reset Password' : 'Enter New Password'}
      onSubmit={step === 1 ? handleEmailSubmit : handleResetSubmit}
      loading={loading}
      error={error}
      success={success}
    >
      {step === 1 ? (
        <>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            Enter your email address and we'll send you a reset token.
          </p>
          <FormInput
            label="Email"
            type="email"
            placeholder="your@email.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <div className="text-center pt-4">
            <Link to="/login" className="text-sm text-primary hover:underline">
              Back to Login
            </Link>
          </div>
        </>
      ) : (
        <>
          <FormInput
            label="Reset Token"
            placeholder="Paste the token from your email"
            value={resetToken}
            onChange={(e) => setResetToken(e.target.value)}
            required
          />
          <FormInput
            label="New Password"
            type="password"
            placeholder="8+ characters"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
          />
          <FormInput
            label="Confirm Password"
            type="password"
            placeholder="Confirm your new password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
          />
        </>
      )}
    </AuthForm>
  )
}
