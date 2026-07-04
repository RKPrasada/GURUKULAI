import { useEffect, useState } from 'react'
import api from '@/services/api'
import { Plus, Trash2, Edit2, Save, X } from 'lucide-react'

interface Channel {
  channel_id: string
  name: string
  description: string
  priority: number
}

interface ChannelsByExam {
  [exam: string]: Channel[]
}

export default function AdminPage() {
  const [channels, setChannels] = useState<ChannelsByExam>({})
  const [loading, setLoading] = useState(true)
  const [selectedExam, setSelectedExam] = useState('rrb_ntpc')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editData, setEditData] = useState<Partial<Channel>>({})
  const [newChannel, setNewChannel] = useState<Partial<Channel>>({
    channel_id: '',
    name: '',
    description: '',
    priority: 1,
  })
  const [showNewForm, setShowNewForm] = useState(false)
  const [message, setMessage] = useState('')

  const exams = ['rrb_ntpc', 'jee', 'neet', 'nda']

  useEffect(() => {
    loadChannels()
  }, [])

  const loadChannels = async () => {
    try {
      const response = await api.listYouTubeChannels()
      setChannels(response.data)
    } catch (err: any) {
      setMessage(`Error loading channels: ${err.response?.data?.detail || err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleAddChannel = async () => {
    if (!newChannel.channel_id || !newChannel.name) {
      setMessage('Channel ID and name are required')
      return
    }
    try {
      await api.addYouTubeChannel(selectedExam, {
        channel_id: newChannel.channel_id || '',
        name: newChannel.name || '',
        description: newChannel.description || '',
        priority: newChannel.priority || 1,
      })
      setMessage('Channel added successfully')
      setNewChannel({ channel_id: '', name: '', description: '', priority: 1 })
      setShowNewForm(false)
      await loadChannels()
    } catch (err: any) {
      setMessage(`Error adding channel: ${err.response?.data?.detail || err.message}`)
    }
  }

  const handleUpdateChannel = async (channelId: string) => {
    try {
      await api.updateYouTubeChannel(selectedExam, channelId, {
        channel_id: editData.channel_id || '',
        name: editData.name || '',
        description: editData.description || '',
        priority: editData.priority || 1,
      })
      setMessage('Channel updated successfully')
      setEditingId(null)
      await loadChannels()
    } catch (err: any) {
      setMessage(`Error updating channel: ${err.response?.data?.detail || err.message}`)
    }
  }

  const handleDeleteChannel = async (channelId: string) => {
    if (!window.confirm('Delete this channel?')) return
    try {
      await api.deleteYouTubeChannel(selectedExam, channelId)
      setMessage('Channel deleted successfully')
      await loadChannels()
    } catch (err: any) {
      setMessage(`Error deleting channel: ${err.response?.data?.detail || err.message}`)
    }
  }

  const currentChannels = channels[selectedExam] || []

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 mb-6">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">⚙️ Admin Panel</h1>
        <p className="text-gray-600 dark:text-gray-400">Manage YouTube channels for exam preparation</p>
      </div>

      {message && (
        <div
          className={`mb-4 p-4 rounded-lg ${
            message.includes('Error')
              ? 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-100'
              : 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-100'
          }`}
        >
          {message}
        </div>
      )}

      {/* Exam Selector */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Select Exam</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {exams.map((exam) => (
            <button
              key={exam}
              onClick={() => setSelectedExam(exam)}
              className={`p-3 rounded-lg font-semibold transition ${
                selectedExam === exam
                  ? 'bg-primary text-white'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
              }`}
            >
              {exam.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Channels List */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Channels for {selectedExam.toUpperCase()}
          </h2>
          <button
            onClick={() => setShowNewForm(!showNewForm)}
            className="flex items-center gap-2 bg-primary hover:bg-primary/90 text-white font-semibold py-2 px-4 rounded-lg transition"
          >
            <Plus size={18} /> Add Channel
          </button>
        </div>

        {/* New Channel Form */}
        {showNewForm && (
          <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg mb-6 space-y-3">
            <input
              type="text"
              placeholder="Channel ID (e.g., UCsVPl8agR3CchT3-AjKZ-Iw)"
              value={newChannel.channel_id || ''}
              onChange={(e) => setNewChannel({ ...newChannel, channel_id: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
            />
            <input
              type="text"
              placeholder="Channel Name"
              value={newChannel.name || ''}
              onChange={(e) => setNewChannel({ ...newChannel, name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
            />
            <input
              type="text"
              placeholder="Description"
              value={newChannel.description || ''}
              onChange={(e) => setNewChannel({ ...newChannel, description: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
            />
            <input
              type="number"
              placeholder="Priority (lower = higher priority)"
              value={newChannel.priority || 1}
              onChange={(e) => setNewChannel({ ...newChannel, priority: parseInt(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
            />
            <div className="flex gap-2">
              <button
                onClick={handleAddChannel}
                className="flex-1 bg-green-500 hover:bg-green-600 text-white font-semibold py-2 rounded-lg transition"
              >
                Save
              </button>
              <button
                onClick={() => setShowNewForm(false)}
                className="flex-1 bg-gray-400 hover:bg-gray-500 text-white font-semibold py-2 rounded-lg transition"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Channels Table */}
        {loading ? (
          <div className="text-center py-8 text-gray-500">Loading...</div>
        ) : currentChannels.length === 0 ? (
          <div className="text-center py-8 text-gray-500">No channels configured yet</div>
        ) : (
          <div className="space-y-3">
            {currentChannels.map((channel) => (
              <div
                key={channel.channel_id}
                className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:bg-gray-50 dark:hover:bg-gray-700 transition"
              >
                {editingId === channel.channel_id ? (
                  <div className="space-y-3">
                    <input
                      type="text"
                      value={editData.name || ''}
                      onChange={(e) => setEditData({ ...editData, name: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                    />
                    <input
                      type="text"
                      value={editData.description || ''}
                      onChange={(e) => setEditData({ ...editData, description: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                    />
                    <input
                      type="number"
                      value={editData.priority || 1}
                      onChange={(e) => setEditData({ ...editData, priority: parseInt(e.target.value) })}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                    />
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleUpdateChannel(channel.channel_id)}
                        className="flex items-center gap-1 bg-green-500 hover:bg-green-600 text-white font-semibold py-2 px-4 rounded-lg transition"
                      >
                        <Save size={16} /> Save
                      </button>
                      <button
                        onClick={() => setEditingId(null)}
                        className="flex items-center gap-1 bg-gray-400 hover:bg-gray-500 text-white font-semibold py-2 px-4 rounded-lg transition"
                      >
                        <X size={16} /> Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <h3 className="font-semibold text-gray-900 dark:text-white">{channel.name}</h3>
                      <p className="text-sm text-gray-600 dark:text-gray-400">{channel.description}</p>
                      <div className="text-xs text-gray-500 mt-2 font-mono">{channel.channel_id}</div>
                      <div className="text-xs text-gray-500 mt-1">Priority: {channel.priority}</div>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => {
                          setEditingId(channel.channel_id)
                          setEditData(channel)
                        }}
                        className="flex items-center gap-1 bg-blue-500 hover:bg-blue-600 text-white py-2 px-3 rounded-lg transition"
                      >
                        <Edit2 size={16} /> Edit
                      </button>
                      <button
                        onClick={() => handleDeleteChannel(channel.channel_id)}
                        className="flex items-center gap-1 bg-red-500 hover:bg-red-600 text-white py-2 px-3 rounded-lg transition"
                      >
                        <Trash2 size={16} /> Delete
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
