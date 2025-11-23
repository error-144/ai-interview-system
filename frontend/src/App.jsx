import { useState, useEffect, useRef } from 'react'
import ChatPanel from './components/ChatPanel'
import VideoPanel from './components/VideoPanel'
import UploadResume from './components/UploadResume'
import { useRealtimeAPI } from './hooks/useRealtimeAPI'
import './App.css'

function App() {
  const [sessionId, setSessionId] = useState(null)
  const [candidateName, setCandidateName] = useState('')
  const [messages, setMessages] = useState([])
  const [interviewStarted, setInterviewStarted] = useState(false)
  const [interviewCompleted, setInterviewCompleted] = useState(false)
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [maxQuestions, setMaxQuestions] = useState(5)
  const [isRecording, setIsRecording] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [useRealtime, setUseRealtime] = useState(true) // Enable real-time by default
  const [timer, setTimer] = useState(0)
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])
  const timerIntervalRef = useRef(null)
  const audioStreamRef = useRef(null)
  const audioProcessorRef = useRef(null)
  const realtimeAudioContextRef = useRef(null)

  useEffect(() => {
    if (interviewStarted && !interviewCompleted) {
      timerIntervalRef.current = setInterval(() => {
        setTimer((prev) => prev + 1)
      }, 1000)
    } else {
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current)
      }
    }

    return () => {
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current)
      }
    }
  }, [interviewStarted, interviewCompleted])

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
  }

  const handleResumeUpload = (data) => {
    setSessionId(data.session_id)
    setCandidateName(data.name)
    setMaxQuestions(data.max_questions || 5)
  }

  // Real-time API hook (Speechmatics Flow API via WebSocket proxy)
  const { isConnected, sendAudio, endAudio } = useRealtimeAPI(
    interviewStarted && useRealtime ? sessionId : null,
    (message) => {
      // Handle real-time messages from Flow API
      setMessages((prev) => [...prev, message])
    },
    (error) => {
      console.error('Flow API error:', error)
      const errorMsg = error || 'Unknown error occurred'
      alert(`Flow API Error: ${errorMsg}`)
    }
  )

  const handleStartInterview = async () => {
    if (!sessionId) return

    try {
      // Mark interview as started - Speechmatics agent will handle the greeting
      const response = await fetch('/api/start-interview', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ session_id: sessionId }),
      })

      const data = await response.json()
      setInterviewStarted(true)
      setCurrentQuestionIndex(1)
      
      // LiveKit handles audio automatically when connected
      // No need to manually start audio streaming
    } catch (error) {
      console.error('Error starting interview:', error)
      alert(`Error starting interview: ${error.message}`)
    }
  }

  const startRealtimeAudio = async () => {
    try {
      console.log('[Realtime] Starting audio capture...')
      
      // Wait for WebSocket connection
      let retries = 0
      while (!isConnected && retries < 10) {
        await new Promise(resolve => setTimeout(resolve, 500))
        retries++
      }
      
      if (!isConnected) {
        console.warn('[Realtime] WebSocket not connected yet, but starting audio capture anyway')
      }
      
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          sampleRate: 16000,  // Speechmatics Flow uses 16kHz
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        }
      })
      
      console.log('[Speechmatics] Microphone access granted')
      audioStreamRef.current = stream
      
      // Create audio context for processing
      const audioContext = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: 16000,  // Speechmatics Flow uses 16kHz
      })
      realtimeAudioContextRef.current = audioContext
      
      const source = audioContext.createMediaStreamSource(stream)
      const processor = audioContext.createScriptProcessor(4096, 1, 1)
      
      processor.onaudioprocess = (e) => {
        if (!isConnected) return
        
        const inputData = e.inputBuffer.getChannelData(0)
        // Convert Float32 to PCM16
        const pcm16 = new Int16Array(inputData.length)
        for (let i = 0; i < inputData.length; i++) {
          const s = Math.max(-1, Math.min(1, inputData[i]))
          pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF
        }
        
        // Send audio chunks directly to Speechmatics Flow via WebSocket proxy
        if (sendAudio) {
          sendAudio(pcm16.buffer)
        }
      }
      
      source.connect(processor)
      processor.connect(audioContext.destination)
      audioProcessorRef.current = processor
      
      setIsListening(true)
      console.log('[Realtime] Audio streaming started')
      
    } catch (error) {
      console.error('Error starting real-time audio:', error)
      alert(`Error accessing microphone: ${error.message}`)
    }
  }

  const stopRealtimeAudio = () => {
    // Send AudioEnded message to Flow API
    if (endAudio) {
      endAudio()
    }
    
    if (audioStreamRef.current) {
      audioStreamRef.current.getTracks().forEach(track => track.stop())
      audioStreamRef.current = null
    }
    if (audioProcessorRef.current) {
      audioProcessorRef.current.disconnect()
      audioProcessorRef.current = null
    }
    if (realtimeAudioContextRef.current) {
      realtimeAudioContextRef.current.close()
      realtimeAudioContextRef.current = null
    }
    setIsListening(false)
    console.log('[Flow API] Audio streaming stopped')
  }

  const startRecording = async () => {
    // If using real-time API, it's already streaming
    if (useRealtime && interviewStarted) {
      return
    }
    
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream)
      mediaRecorderRef.current = mediaRecorder
      audioChunksRef.current = []

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' })
        await processAudio(audioBlob)
        stream.getTracks().forEach((track) => track.stop())
      }

      mediaRecorder.start()
      setIsRecording(true)
      setIsListening(true)
    } catch (error) {
      console.error('Error accessing microphone:', error)
      alert('Please allow microphone access to record your answer')
    }
  }

  const stopRecording = () => {
    if (useRealtime && interviewStarted) {
      stopRealtimeAudio()
      return
    }
    
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
      setIsListening(false)
    }
  }
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopRealtimeAudio()
    }
  }, [])

  const processAudio = async (audioBlob) => {
    try {
      // Transcribe audio
      const formData = new FormData()
      formData.append('file', audioBlob, 'recording.wav')
      formData.append('session_id', sessionId)
      formData.append('question_index', currentQuestionIndex)

      const transcribeResponse = await fetch('/api/transcribe-audio', {
        method: 'POST',
        body: formData,
      })

      const transcribeData = await transcribeResponse.json()
      const transcript = transcribeData.transcript

      // Add user message
      const userMessage = { role: 'user', content: transcript }
      setMessages((prev) => [...prev, userMessage])

      // Process answer
      const processResponse = await fetch('/api/process-answer', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          transcript: transcript,
          question_index: currentQuestionIndex,
        }),
      })

      const processData = await processResponse.json()

      // Add feedback message (optional, can be shown in UI)
      if (processData.feedback) {
        // You can add feedback to messages if needed
      }

      if (processData.interview_completed) {
        setInterviewCompleted(true)
        if (processData.thanks_message) {
          setMessages((prev) => [
            ...prev,
            { role: 'assistant', content: processData.thanks_message },
          ])
        }
      } else if (processData.next_question) {
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: processData.next_question },
        ])
        setCurrentQuestionIndex(processData.question_index)
      }
    } catch (error) {
      console.error('Error processing audio:', error)
      alert('Error processing your answer. Please try again.')
    }
  }

  const handleSendMessage = async (text) => {
    if (!text.trim() || !sessionId) return

    // Add user message
    const userMessage = { role: 'user', content: text }
    setMessages((prev) => [...prev, userMessage])

    try {
      // Process answer
      const processResponse = await fetch('/api/process-answer', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          transcript: text,
          question_index: currentQuestionIndex,
        }),
      })

      const processData = await processResponse.json()

      if (processData.interview_completed) {
        setInterviewCompleted(true)
        if (processData.thanks_message) {
          setMessages((prev) => [
            ...prev,
            { role: 'assistant', content: processData.thanks_message },
          ])
        }
      } else if (processData.next_question) {
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: processData.next_question },
        ])
        setCurrentQuestionIndex(processData.question_index)
      }
    } catch (error) {
      console.error('Error sending message:', error)
      alert('Error sending your message. Please try again.')
    }
  }

  if (!sessionId || !interviewStarted) {
    return (
      <div className="app">
        <UploadResume 
          onResumeUpload={handleResumeUpload} 
          onStartInterview={handleStartInterview}
          sessionId={sessionId}
        />
      </div>
    )
  }

  return (
    <div className="app">
      <div className="app-container">
        <ChatPanel
          messages={messages}
          onSendMessage={handleSendMessage}
          timer={formatTime(timer)}
          interviewStarted={interviewStarted}
          interviewCompleted={interviewCompleted}
          onStartRecording={startRecording}
          onStopRecording={stopRecording}
          isRecording={isRecording}
        />
        <VideoPanel
          candidateName={candidateName}
          isListening={isListening}
          interviewStarted={interviewStarted}
        />
      </div>
    </div>
  )
}

export default App

