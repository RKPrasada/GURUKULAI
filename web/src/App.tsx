import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/auth'
import LandingPage from './pages/LandingPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import ForgotPasswordPage from './pages/ForgotPasswordPage'
import HomePage from './pages/HomePage'
import DiagnosticPage from './pages/DiagnosticPage'
import StudyPage from './pages/StudyPage'
import StudyPlanPage from './pages/StudyPlanPage'
import TestPage from './pages/TestPage'
import ProgressPage from './pages/ProgressPage'
import AdminPage from './pages/AdminPage'
import QuestionsPage from './pages/QuestionsPage'
import ClassesPage from './pages/ClassesPage'
import NagaDashboard from './pages/NagaDashboard'
import MockTestPage from './pages/MockTestPage'
import SettingsPage from './pages/SettingsPage'
import FeedbackPage from './pages/FeedbackPage'
import HelpPage from './pages/HelpPage'
import Layout from './components/Layout'

function App() {
  const student = useAuthStore((state) => state.student)

  return (
    <BrowserRouter>
      <Routes>
        {/* Landing page — always public */}
        <Route path="/landing" element={<LandingPage />} />

        {/* Auth routes */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />

        {student ? (
          /* Authenticated: app routes */
          <Route element={<Layout />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/diagnostic" element={<DiagnosticPage />} />
            <Route path="/study" element={<StudyPage />} />
            <Route path="/study-plan" element={<StudyPlanPage />} />
            <Route path="/test" element={<TestPage />} />
            <Route path="/progress" element={<ProgressPage />} />
            <Route path="/admin" element={<AdminPage />} />
            <Route path="/questions" element={<QuestionsPage />} />
            <Route path="/classes" element={<ClassesPage />} />
            <Route path="/naga" element={<NagaDashboard />} />
            <Route path="/mock-test"  element={<MockTestPage />} />
            <Route path="/settings"   element={<SettingsPage />} />
            <Route path="/feedback"   element={<FeedbackPage />} />
            <Route path="/help"       element={<HelpPage />} />
          </Route>
        ) : (
          /* Unauthenticated: / shows landing, everything else → landing */
          <>
            <Route path="/" element={<LandingPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </>
        )}
      </Routes>
    </BrowserRouter>
  )
}

export default App
