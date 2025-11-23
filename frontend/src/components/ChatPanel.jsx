import { useState, useRef, useEffect } from 'react'
import { FaMicrophone, FaPaperPlane, FaExpand } from 'react-icons/fa'
import './ChatPanel.css'

function ChatPanel({
  messages,
  onSendMessage,
  timer,
  interviewStarted,
  interviewCompleted,
  onStartRecording,
  onStopRecording,
  isRecording,
  overallFeedback,
  overallScore,
}) {
  const [inputText, setInputText] = useState('')
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSubmit = (e) => {
    e.preventDefault()
    if (inputText.trim() && !interviewCompleted) {
      onSendMessage(inputText)
      setInputText('')
    }
  }

  const handleMicClick = () => {
    if (isRecording) {
      onStopRecording()
    } else {
      onStartRecording()
    }
  }

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <div className="chat-header-left">
          <h2>Welcome to AI Interview</h2>
          <button className="expand-button">
            <FaExpand />
          </button>
        </div>
        <div className="chat-timer">{timer}</div>
      </div>

      <div className="chat-messages">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`message ${message.role === 'assistant' ? 'message-interviewer' : 'message-user'}`}
          >
            <div className="message-content">
              <div className="message-role">
                {message.role === 'assistant' ? 'Interviewer' : 'You'}
              </div>
              <div className="message-text">{message.content}</div>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {interviewStarted && !interviewCompleted && (
        <div className="chat-input-container">
          <form onSubmit={handleSubmit} className="chat-input-form">
            <input
              ref={inputRef}
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Start typing or use the mic button to record your response."
              className="chat-input"
              disabled={isRecording}
            />
            <button
              type="button"
              className={`mic-button ${isRecording ? 'recording' : ''}`}
              onClick={handleMicClick}
              title={isRecording ? 'Stop recording' : 'Start recording'}
            >
              <FaMicrophone />
            </button>
            <button type="submit" className="send-button" disabled={!inputText.trim()}>
              <FaPaperPlane />
            </button>
          </form>
        </div>
      )}

      {interviewCompleted && (
        <div className="interview-completed">
          <div className="feedback-container">
            <h3>Interview Feedback</h3>
            
            {overallScore !== null && (
              <div className="score-section">
                <div className="score-display">
                  <span className="score-label">Overall Score:</span>
                  <span className="score-value">{overallScore.toFixed(1)}/10</span>
                </div>
              </div>
            )}
            
            {overallFeedback && (
              <div className="feedback-content">
                {overallFeedback.overall_feedback && (
                  <div className="feedback-section">
                    <h4>Overall Assessment</h4>
                    <p>{overallFeedback.overall_feedback}</p>
                  </div>
                )}
                
                {overallFeedback.key_strengths && overallFeedback.key_strengths.length > 0 && (
                  <div className="feedback-section">
                    <h4>Key Strengths</h4>
                    <ul>
                      {overallFeedback.key_strengths.map((strength, index) => (
                        <li key={index}>{strength}</li>
                      ))}
                    </ul>
                  </div>
                )}
                
                {overallFeedback.areas_for_improvement && overallFeedback.areas_for_improvement.length > 0 && (
                  <div className="feedback-section areas-for-improvement">
                    <h4>Areas for Improvement</h4>
                    <ul>
                      {overallFeedback.areas_for_improvement.map((area, index) => (
                        <li key={index}>{area}</li>
                      ))}
                    </ul>
                  </div>
                )}
                
                {overallFeedback.recommendation && (
                  <div className="feedback-section">
                    <h4>Recommendation</h4>
                    <p>{overallFeedback.recommendation}</p>
                  </div>
                )}
              </div>
            )}
            
            {!overallFeedback && (
              <p>Interview completed! Thank you for your time.</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default ChatPanel

