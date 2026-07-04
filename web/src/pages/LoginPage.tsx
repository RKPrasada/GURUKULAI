import { FormEvent, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'
import api from '@/services/api'
import AuthForm, { FormInput } from '@/components/AuthForm'

export default function LoginPage() {
  const navigate = useNavigate()
  const login = useAuthStore((state) => state.login)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const response = await api.login(username, password)
      const { access_token, ...student } = response.data
      login(student, access_token)
      if (student.username === 'naga') {
        navigate('/naga')
      } else {
        navigate('/')
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthForm title="Welcome Back!" onSubmit={handleSubmit} loading={loading} error={error}>
      <FormInput
        label="Username"
        placeholder="Enter your username"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        required
      />
      <FormInput
        label="Password"
        type="password"
        placeholder="Enter your password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />

      <div className="text-center">
        <Link to="/forgot-password" className="text-sm text-primary hover:underline">
          🔐 Forgot password?
        </Link>
      </div>

      <div className="text-center pt-4">
        <p className="text-gray-600 dark:text-gray-400">
          Don't have an account?{' '}
          <Link to="/register" className="text-primary hover:underline font-semibold">
            Register here
          </Link>
        </p>
      </div>
    </AuthForm>
  )
}
