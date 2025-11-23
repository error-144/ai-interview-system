import { useEffect, useRef, useState } from 'react'
import { FaMicrophone } from 'react-icons/fa'
import './VideoPanel.css'

function VideoPanel({ candidateName, isListening, interviewStarted }) {
  const userVideoRef = useRef(null)
  const [stream, setStream] = useState(null)

  useEffect(() => {
    if (interviewStarted) {
      // Access user's camera
      navigator.mediaDevices
        .getUserMedia({ video: true, audio: false })
        .then((mediaStream) => {
          if (userVideoRef.current) {
            userVideoRef.current.srcObject = mediaStream
            setStream(mediaStream)
          }
        })
        .catch((error) => {
          console.error('Error accessing camera:', error)
        })
    }

    return () => {
      if (stream) {
        stream.getTracks().forEach((track) => track.stop())
      }
    }
  }, [interviewStarted])

  return (
    <div className="video-panel">
      <div className="video-container">
        <div className="video-feed user-video">
          <video ref={userVideoRef} autoPlay playsInline muted />
          <div className="video-overlay">
            <div className="video-label user-label">{candidateName || 'You'}</div>
            {isListening && (
              <div className="video-status listening">
                <FaMicrophone />
                <span>Listening...</span>
              </div>
            )}
          </div>
        </div>

        <div className="video-feed interviewer-video">
          <div className="interviewer-placeholder">
            <div className="interviewer-avatar">
              <div className="avatar-circle">
                <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <circle cx="50" cy="50" r="50" fill="#e0e7ff" />
                  <circle cx="50" cy="40" r="18" fill="#667eea" />
                  <path
                    d="M25 75C25 65 35 60 50 60C65 60 75 65 75 75V85H25V75Z"
                    fill="#667eea"
                  />
                </svg>
              </div>
            </div>
          </div>
          <div className="video-overlay">
            <div className="video-label interviewer-label">
              <FaMicrophone />
              <span>Interviewer</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default VideoPanel

