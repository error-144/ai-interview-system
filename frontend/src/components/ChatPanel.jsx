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
          <p>Interview completed! Thank you for your time.</p>
        </div>
      )}
    </div>
  )
}

export default ChatPanel

