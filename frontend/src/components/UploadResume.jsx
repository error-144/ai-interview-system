import { useState } from 'react'
import './UploadResume.css'

function UploadResume({ onResumeUpload, onStartInterview, sessionId }) {
  const [file, setFile] = useState(null)
  const [jobDescription, setJobDescription] = useState('')
  const [maxQuestions, setMaxQuestions] = useState(5)
  const [aiVoice, setAiVoice] = useState('Alex (Male)')
  const [loading, setLoading] = useState(false)
  const [sessionData, setSessionData] = useState(null)

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!file || !jobDescription.trim()) {
      alert('Please upload a resume and provide a job description')
      return
    }

    setLoading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('job_description', jobDescription)
      formData.append('max_questions', maxQuestions)
      formData.append('ai_voice', aiVoice)

      const response = await fetch('/api/upload-resume', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        // Try to get error message from response
        let errorMessage = 'Failed to upload resume'
        try {
          const errorData = await response.json()
          errorMessage = errorData.detail || errorData.message || errorMessage
        } catch (e) {
          errorMessage = `Server error: ${response.status} ${response.statusText}`
        }
        throw new Error(errorMessage)
      }

      const data = await response.json()
      
      // Validate response data
      if (!data.session_id || !data.name) {
        throw new Error('Invalid response from server. Missing required fields.')
      }
      
      setSessionData(data)
      onResumeUpload(data)
    } catch (error) {
      console.error('Error uploading resume:', error)
      // Show detailed error message to user
      const errorMessage = error.message || 'Error uploading resume. Please try again.'
      alert(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const handleStartInterview = () => {
    if (sessionData) {
      onStartInterview()
    }
  }

  return (
    <div className="upload-container">
      <div className="upload-card">
        <h1>🤖 AI Interview System</h1>
        {!sessionData ? (
          <form onSubmit={handleSubmit} className="upload-form">
            <div className="upload-form-group">
              <label htmlFor="resume">Upload Resume (PDF)</label>
              <input
                type="file"
                id="resume"
                accept=".pdf"
                onChange={handleFileChange}
                required
              />
            </div>

            <div className="upload-form-group">
              <label htmlFor="jobDescription">Job Description</label>
              <textarea
                id="jobDescription"
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
                placeholder="Paste the job description here..."
                required
              />
            </div>

            <div className="upload-form-group">
              <label htmlFor="maxQuestions">Maximum Questions</label>
              <input
                type="number"
                id="maxQuestions"
                min="1"
                max="10"
                value={maxQuestions}
                onChange={(e) => setMaxQuestions(parseInt(e.target.value))}
              />
            </div>

            <div className="upload-form-group">
              <label htmlFor="aiVoice">AI Interviewer Voice</label>
              <select
                id="aiVoice"
                value={aiVoice}
                onChange={(e) => setAiVoice(e.target.value)}
              >
                <option value="Alex (Male)">Alex (Male)</option>
                <option value="Aria (Female)">Aria (Female)</option>
                <option value="Natasha (Female)">Natasha (Female)</option>
                <option value="Sonia (Female)">Sonia (Female)</option>
              </select>
            </div>

            <button type="submit" className="upload-button" disabled={loading}>
              {loading ? 'Processing...' : 'Submit'}
            </button>
          </form>
        ) : (
          <div className="upload-success">
            <h2>Resume Processed Successfully!</h2>
            <p>Candidate: <strong>{sessionData.name}</strong></p>
            <button 
              onClick={handleStartInterview} 
              className="upload-button"
            >
              Start Interview
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default UploadResume

