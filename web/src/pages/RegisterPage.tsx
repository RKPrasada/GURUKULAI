import { FormEvent, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'
import api from '@/services/api'
import AuthForm, { FormInput, FormSelect } from '@/components/AuthForm'

const TRADE_OPTIONS = [
  { value: '', label: 'Select Trade' },
  { value: 'Electrician', label: 'Electrician' },
  { value: 'Fitter', label: 'Fitter' },
  { value: 'Mechanic (Motor Vehicle)', label: 'Mechanic (Motor Vehicle)' },
  { value: 'Electronics', label: 'Electronics' },
  { value: 'Instrument Mechanic', label: 'Instrument Mechanic' },
  { value: 'Welder', label: 'Welder' },
  { value: 'Carpenter', label: 'Carpenter' },
  { value: 'Painter', label: 'Painter' },
  { value: 'Plumber', label: 'Plumber' },
  { value: 'Turner', label: 'Turner' },
  { value: 'Machinist', label: 'Machinist' },
  { value: 'Wireman', label: 'Wireman' },
  { value: 'Draughtsman (Civil)', label: 'Draughtsman (Civil)' },
  { value: 'Draughtsman (Mechanical)', label: 'Draughtsman (Mechanical)' },
  { value: 'Refrigeration & AC', label: 'Refrigeration & AC' },
]

const DISCIPLINE_OPTIONS = [
  { value: '', label: 'Select Discipline' },
  { value: 'Civil', label: 'Civil Engineering' },
  { value: 'Electrical', label: 'Electrical Engineering' },
  { value: 'Mechanical', label: 'Mechanical Engineering' },
  { value: 'Electronics', label: 'Electronics & Communication' },
]

export default function RegisterPage() {
  const navigate = useNavigate()
  const login = useAuthStore((state) => state.login)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirm_password: '',
    full_name: '',
    exam_target: '',
    preferred_language: 'en',
    exam_date: '',
    trade: '',
    engineering_discipline: '',
  })

  const showTrade = formData.exam_target === 'rrb_alp' || formData.exam_target === 'rrb_technician'
  const showDiscipline = formData.exam_target === 'rrb_je'

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: value,
      // Clear conditional fields when exam changes
      ...(name === 'exam_target' ? { trade: '', engineering_discipline: '' } : {}),
    }))
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')

    if (formData.password !== formData.confirm_password) {
      setError('Passwords do not match')
      return
    }

    if (showTrade && !formData.trade) {
      setError('Please select your ITI trade')
      return
    }

    if (showDiscipline && !formData.engineering_discipline) {
      setError('Please select your engineering discipline')
      return
    }

    setLoading(true)

    try {
      const response = await api.register(formData)
      const { access_token, ...student } = response.data
      login(student, access_token)
      navigate('/')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthForm title="Create Account" onSubmit={handleSubmit} loading={loading} error={error}>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <FormInput
          label="Username"
          placeholder="3+ characters"
          name="username"
          value={formData.username}
          onChange={handleChange}
          required
        />
        <FormInput
          label="Full Name"
          placeholder="Your full name"
          name="full_name"
          value={formData.full_name}
          onChange={handleChange}
          required
        />
      </div>

      <FormInput
        label="Email"
        type="email"
        placeholder="your@email.com"
        name="email"
        value={formData.email}
        onChange={handleChange}
        required
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <FormSelect
          label="Target Exam"
          name="exam_target"
          value={formData.exam_target}
          onChange={handleChange}
          required
          options={[
            { value: 'rrb_alp', label: 'RRB ALP' },
            { value: 'rrb_group_d', label: 'RRB Group D' },
            { value: 'rrb_ntpc', label: 'RRB NTPC' },
            { value: 'rrb_technician', label: 'RRB Technician' },
            { value: 'rrb_je', label: 'RRB JE' },
            { value: 'nda', label: 'NDA' },
            { value: 'jee', label: 'JEE' },
            { value: 'neet', label: 'NEET' },
          ]}
        />
        <FormSelect
          label="Language"
          name="preferred_language"
          value={formData.preferred_language}
          onChange={handleChange}
          options={[
            { value: 'en', label: 'English' },
            { value: 'hi', label: 'हिंदी' },
          ]}
        />
      </div>

      {/* ITI Trade — required for RRB ALP and RRB Technician */}
      {showTrade && (
        <FormSelect
          label="ITI Trade"
          name="trade"
          value={formData.trade}
          onChange={handleChange}
          required
          options={TRADE_OPTIONS}
        />
      )}

      {/* Engineering Discipline — required for RRB JE */}
      {showDiscipline && (
        <FormSelect
          label="Engineering Discipline"
          name="engineering_discipline"
          value={formData.engineering_discipline}
          onChange={handleChange}
          required
          options={DISCIPLINE_OPTIONS}
        />
      )}

      <FormInput
        label="Target Exam Date"
        type="date"
        name="exam_date"
        value={formData.exam_date}
        onChange={handleChange}
        placeholder=""
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <FormInput
          label="Password"
          type="password"
          placeholder="8+ characters"
          name="password"
          value={formData.password}
          onChange={handleChange}
          required
        />
        <FormInput
          label="Confirm Password"
          type="password"
          placeholder="Confirm password"
          name="confirm_password"
          value={formData.confirm_password}
          onChange={handleChange}
          required
        />
      </div>

      <div className="text-center pt-4">
        <p className="text-gray-600 dark:text-gray-400">
          Already have an account?{' '}
          <Link to="/login" className="text-primary hover:underline font-semibold">
            Login here
          </Link>
        </p>
      </div>
    </AuthForm>
  )
}
