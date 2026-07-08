import { useEffect, useState } from 'react'
import api from '@/services/api'
import { Upload, Loader2, CheckCircle, AlertTriangle, RefreshCw, FileText } from 'lucide-react'

interface SyllabusTopic { name: string; subtopics: string[] }
interface SyllabusSubject { name: string; topics: SyllabusTopic[] }

const EXAMS = [
  { key: 'rrb_ntpc', label: 'RRB NTPC' },
  { key: 'rrb_alp', label: 'RRB ALP' },
  { key: 'rrb_group_d', label: 'RRB Group D' },
  { key: 'rrb_technician', label: 'RRB Technician' },
  { key: 'rrb_je', label: 'RRB JE' },
  { key: 'nda', label: 'NDA' },
  { key: 'jee', label: 'JEE Mains' },
  { key: 'neet', label: 'NEET' },
]

interface UploadResult {
  notes_saved: boolean
  notes_chars: number
  questions_extracted: number
  questions_added: number
  message: string
}

export default function NagaContentUpload() {
  const [exam, setExam] = useState('')
  const [subjects, setSubjects] = useState<SyllabusSubject[]>([])
  const [subject, setSubject] = useState('')
  const [topic, setTopic] = useState('')
  const [subtopic, setSubtopic] = useState('')
  const [file, setFile] = useState<File | null>(null)

  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [retryable, setRetryable] = useState(false)
  const [result, setResult] = useState<UploadResult | null>(null)

  // Load syllabus tree when exam changes
  useEffect(() => {
    if (!exam) { setSubjects([]); return }
    setSubject(''); setTopic(''); setSubtopic('')
    api.getNagaSyllabus(exam)
      .then(res => setSubjects(res.data.subjects || []))
      .catch(() => setSubjects([]))
  }, [exam])

  const subjectObj = subjects.find(s => s.name === subject)
  const topicObj = subjectObj?.topics.find(t => t.name === topic)

  const canUpload = exam && subject && topic && file && !uploading

  const doUpload = async () => {
    if (!file || !canUpload) return
    setUploading(true); setError(''); setRetryable(false); setResult(null)
    try {
      const res = await api.uploadNagaContent(file, exam, subject, topic, subtopic)
      setResult(res.data)
    } catch (err: any) {
      const status = err.response?.status
      setError(err.response?.data?.detail || 'Upload failed. Please try again.')
      // 503 = LLM rate-limited / transient → retry the same file
      setRetryable(status === 503)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6 space-y-5 max-w-2xl">
      <div>
        <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <Upload size={18} className="text-primary" /> Upload Notes &amp; Questions
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Upload a PDF or DOCX for one subtopic. Gurukul AI extracts study notes and
          practice questions and publishes them (auto-approved).
        </p>
      </div>

      {/* Selectors */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <label className="text-sm">
          <span className="block font-medium text-gray-700 dark:text-gray-300 mb-1">Exam</span>
          <select value={exam} onChange={e => setExam(e.target.value)}
            className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white">
            <option value="">Select exam…</option>
            {EXAMS.map(e => <option key={e.key} value={e.key}>{e.label}</option>)}
          </select>
        </label>

        <label className="text-sm">
          <span className="block font-medium text-gray-700 dark:text-gray-300 mb-1">Subject</span>
          <select value={subject} disabled={!subjects.length}
            onChange={e => { setSubject(e.target.value); setTopic(''); setSubtopic('') }}
            className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white disabled:opacity-50">
            <option value="">Select subject…</option>
            {subjects.map(s => <option key={s.name} value={s.name}>{s.name}</option>)}
          </select>
        </label>

        <label className="text-sm">
          <span className="block font-medium text-gray-700 dark:text-gray-300 mb-1">Topic</span>
          <select value={topic} disabled={!subjectObj}
            onChange={e => { setTopic(e.target.value); setSubtopic('') }}
            className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white disabled:opacity-50">
            <option value="">Select topic…</option>
            {(subjectObj?.topics || []).map(t => <option key={t.name} value={t.name}>{t.name}</option>)}
          </select>
        </label>

        <label className="text-sm">
          <span className="block font-medium text-gray-700 dark:text-gray-300 mb-1">Subtopic <span className="text-gray-400">(optional)</span></span>
          <select value={subtopic} disabled={!topicObj}
            onChange={e => setSubtopic(e.target.value)}
            className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white disabled:opacity-50">
            <option value="">Whole topic</option>
            {(topicObj?.subtopics || []).map(st => <option key={st} value={st}>{st}</option>)}
          </select>
        </label>
      </div>

      {/* File input */}
      <label className="block">
        <span className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Document (PDF, DOCX, TXT, MD)</span>
        <input type="file" accept=".pdf,.docx,.txt,.md"
          onChange={e => { setFile(e.target.files?.[0] || null); setResult(null); setError('') }}
          className="block w-full text-sm text-gray-600 dark:text-gray-300 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-primary/10 file:text-primary file:font-semibold hover:file:bg-primary/20" />
        {file && (
          <span className="inline-flex items-center gap-1 text-xs text-gray-500 mt-1">
            <FileText size={12} /> {file.name} ({Math.round(file.size / 1024)} KB)
          </span>
        )}
      </label>

      {/* Action */}
      <button onClick={doUpload} disabled={!canUpload}
        className="w-full bg-primary hover:bg-primary/90 disabled:bg-gray-300 dark:disabled:bg-gray-600 text-white font-semibold py-2.5 rounded-lg transition flex items-center justify-center gap-2">
        {uploading
          ? <><Loader2 size={16} className="animate-spin" /> Extracting… (this can take up to a minute)</>
          : <><Upload size={16} /> Extract &amp; Publish</>}
      </button>

      {/* Error with Retry */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <p className="flex items-center gap-2 text-sm font-semibold text-red-700 dark:text-red-300">
            <AlertTriangle size={15} /> {error}
          </p>
          {retryable && (
            <button onClick={doUpload} disabled={uploading}
              className="mt-3 inline-flex items-center gap-2 bg-red-600 hover:bg-red-700 text-white text-sm font-semibold px-4 py-1.5 rounded-lg transition">
              <RefreshCw size={14} /> Retry
            </button>
          )}
        </div>
      )}

      {/* Success */}
      {result && (
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
          <p className="flex items-center gap-2 text-sm font-semibold text-green-700 dark:text-green-300 mb-2">
            <CheckCircle size={15} /> {result.message}
          </p>
          <ul className="text-xs text-gray-600 dark:text-gray-400 space-y-0.5">
            <li>Notes: {result.notes_saved ? `saved (${result.notes_chars} chars)` : 'none found'}</li>
            <li>Questions: {result.questions_added} added{result.questions_extracted !== result.questions_added ? ` (${result.questions_extracted} extracted, duplicates skipped)` : ''}</li>
          </ul>
        </div>
      )}
    </div>
  )
}
