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

  // Real-time API hook (OpenAI via WebSocket)
  const { isConnected, sendAudio, endAudio, isAISpeaking } = useRealtimeAPI(
    interviewStarted && useRealtime ? sessionId : null,
    (message) => {
      // Handle real-time messages from OpenAI
      setMessages((prev) => [...prev, message])
    },
    (error) => {
      console.error('OpenAI API error:', error)
      const errorMsg = error || 'Unknown error occurred'
      alert(`OpenAI API Error: ${errorMsg}`)
    }
  )

  const handleStartInterview = async () => {
    if (!sessionId) return

    try {
      // Mark interview as started - OpenAI will handle the greeting
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
      
      // Start microphone capture for real-time audio processing
      if (useRealtime) {
        // Wait a bit for WebSocket to be ready, then start audio
        setTimeout(() => {
          startRealtimeAudio().catch(err => {
            console.error('Error starting audio capture:', err)
          })
        }, 1000)
      }
    } catch (error) {
      console.error('Error starting interview:', error)
      alert(`Error starting interview: ${error.message}`)
    }
  }

  const startRealtimeAudio = async () => {
    try {
      console.log('[Realtime] Starting audio capture...')
      
      // Wait for WebSocket connection (up to 5 seconds)
      let retries = 0
      const maxRetries = 20
      console.log(`[Realtime] Waiting for WebSocket connection (isConnected: ${isConnected})...`)
      while (!isConnected && retries < maxRetries) {
        await new Promise(resolve => setTimeout(resolve, 250))
        retries++
        if (retries % 4 === 0) {
          console.log(`[Realtime] Still waiting for connection... (${retries * 250}ms elapsed)`)
        }
      }
      
      if (!isConnected) {
        console.warn('[Realtime] WebSocket not connected after waiting, but starting audio capture anyway')
        console.log('[Realtime] Will start sending audio when connection is ready')
        console.log('[Realtime] Note: Audio chunks will be queued until WebSocket connects')
        console.log('[Realtime] The sendAudio function will check WebSocket state directly')
      } else {
        console.log('[Realtime] WebSocket connected, starting microphone...')
      }
      
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          sampleRate: 16000,  // OpenAI Whisper uses 16kHz
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        }
      })
      
      console.log('[OpenAI] Microphone access granted')
      audioStreamRef.current = stream
      
      // Create audio context for processing
      const audioContext = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: 16000,  // OpenAI Whisper uses 16kHz
      })
      realtimeAudioContextRef.current = audioContext
      
      const source = audioContext.createMediaStreamSource(stream)
      const processor = audioContext.createScriptProcessor(4096, 1, 1)
      
      // Buffer to collect audio chunks locally
      const audioBuffer = []
      let audioChunkCount = 0
      const SILENCE_THRESHOLD = 0.015  // RMS threshold for silence (adjust as needed)
      const MIN_SPEECH_DURATION = 0.3  // Minimum speech duration in seconds
      const SILENCE_CHUNKS_THRESHOLD = 6  // Number of silent chunks before considering silence (~1.5 seconds at 16kHz)
      let speechStartTime = null
      let isSpeaking = false
      let consecutiveSilenceChunks = 0
      let isWaitingForResponse = false  // Track if we're waiting for AI response
      
      processor.onaudioprocess = (e) => {
        // Pause microphone input while AI is speaking or waiting for response
        if ((isAISpeaking && isAISpeaking()) || isWaitingForResponse) {
          // Log occasionally to show we're waiting
          if (audioChunkCount % 200 === 0) {
            console.log('[Realtime] AI is speaking or processing, microphone paused...')
          }
          return  // Don't process microphone input while AI is speaking or processing
        }
        
        const inputData = e.inputBuffer.getChannelData(0)
        
        // Calculate RMS (Root Mean Square) to detect audio level
        let sum = 0
        for (let i = 0; i < inputData.length; i++) {
          sum += inputData[i] * inputData[i]
        }
        const rms = Math.sqrt(sum / inputData.length)
        const currentTime = Date.now() / 1000
        
        // Detect speech (audio level above threshold)
        if (rms > SILENCE_THRESHOLD) {
          consecutiveSilenceChunks = 0
          
          if (!isSpeaking) {
            isSpeaking = true
            speechStartTime = currentTime
            audioBuffer.length = 0  // Clear buffer for new speech
            console.log('[Realtime] Speech detected, buffering audio locally')
          }
          
          // Convert Float32 to PCM16 and add to buffer (don't send yet)
          const pcm16 = new Int16Array(inputData.length)
          for (let i = 0; i < inputData.length; i++) {
            const s = Math.max(-1, Math.min(1, inputData[i]))
            pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF
          }
          
          // Add to local buffer instead of sending immediately
          audioBuffer.push(pcm16.buffer)
          audioChunkCount++
          
          // Log occasionally
          if (audioChunkCount % 50 === 0) {
            const totalSize = audioBuffer.reduce((sum, chunk) => sum + chunk.byteLength, 0)
            console.log(`[Realtime] Buffering audio: ${audioBuffer.length} chunks (${totalSize} bytes)`)
          }
          
        } else {
          // Silence detected
          consecutiveSilenceChunks++
          
          if (isSpeaking) {
            // Check if we had enough speech duration
            const speechDuration = currentTime - speechStartTime
            
            if (speechDuration >= MIN_SPEECH_DURATION) {
              // Check if we've had enough consecutive silence chunks
              if (consecutiveSilenceChunks >= SILENCE_CHUNKS_THRESHOLD) {
                // User finished speaking - send all buffered audio at once
                const totalSize = audioBuffer.reduce((sum, chunk) => sum + chunk.byteLength, 0)
                console.log(`[Realtime] Speech ended (${speechDuration.toFixed(2)}s), sending complete audio: ${audioBuffer.length} chunks (${totalSize} bytes)`)
                
                // Send all buffered chunks at once
                if (sendAudio && audioBuffer.length > 0) {
                  isWaitingForResponse = true  // Block further input until response received
                  
                  // Send all chunks sequentially
                  audioBuffer.forEach((chunk, index) => {
                    try {
                      sendAudio(chunk)
                      if (index === 0) {
                        console.log(`[Realtime] Started sending ${audioBuffer.length} buffered chunks`)
                      }
                    } catch (err) {
                      console.error('[Realtime] Error sending audio chunk:', err)
                    }
                  })
                  
                  // Send end_audio signal after all chunks are sent
                  setTimeout(() => {
                    if (endAudio) {
                      endAudio()
                      console.log('[Realtime] Sent end_audio signal, waiting for AI response...')
                    }
                  }, 100)  // Small delay to ensure all chunks are sent first
                }
                
                // Reset state
                isSpeaking = false
                speechStartTime = null
                consecutiveSilenceChunks = 0
                audioBuffer.length = 0
              }
            } else if (consecutiveSilenceChunks >= SILENCE_CHUNKS_THRESHOLD) {
              // Speech too short, discard
              console.log(`[Realtime] Speech too short (${speechDuration.toFixed(2)}s), discarding`)
              isSpeaking = false
              speechStartTime = null
              consecutiveSilenceChunks = 0
              audioBuffer.length = 0
            }
          }
        }
      }
      
      source.connect(processor)
      processor.connect(audioContext.destination)
      audioProcessorRef.current = processor
      
      setIsListening(true)
      console.log('[Realtime] Audio streaming started')
      console.log('[Realtime] Audio context sample rate:', audioContext.sampleRate)
      console.log('[Realtime] Processor buffer size:', processor.bufferSize)
      console.log('[Realtime] sendAudio function available:', !!sendAudio)
      console.log('[Realtime] isConnected state:', isConnected)
      
      // Listen for AI response completion to resume microphone input
      const handleAIResponseComplete = () => {
        console.log('[Realtime] AI response complete, resuming microphone input')
        isWaitingForResponse = false
      }
      
      window.addEventListener('aiResponseComplete', handleAIResponseComplete)
      
      // Store cleanup function
      const cleanup = () => {
        window.removeEventListener('aiResponseComplete', handleAIResponseComplete)
      }
      
      // Store cleanup in a way that can be called later
      if (audioProcessorRef.current) {
        audioProcessorRef.current._cleanup = cleanup
      }
      
    } catch (error) {
      console.error('Error starting real-time audio:', error)
      alert(`Error accessing microphone: ${error.message}`)
    }
  }

  const stopRealtimeAudio = () => {
    // Send end_audio message to OpenAI
    if (endAudio) {
      endAudio()
    }
    
    // Cleanup event listener
    if (audioProcessorRef.current && audioProcessorRef.current._cleanup) {
      audioProcessorRef.current._cleanup()
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
    console.log('[OpenAI] Audio streaming stopped')
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
  
  // Resume audio context on user interaction (browser autoplay policy)
  useEffect(() => {
    const handleUserInteraction = async () => {
      // Resume audio context when user interacts (click, touch, etc.)
      if (realtimeAudioContextRef.current && realtimeAudioContextRef.current.state === 'suspended') {
        try {
          await realtimeAudioContextRef.current.resume()
          console.log('[App] Audio context resumed after user interaction')
        } catch (err) {
          console.error('[App] Error resuming audio context:', err)
        }
      }
    }
    
    // Add event listeners for user interaction
    window.addEventListener('click', handleUserInteraction, { once: true })
    window.addEventListener('touchstart', handleUserInteraction, { once: true })
    
    return () => {
      window.removeEventListener('click', handleUserInteraction)
      window.removeEventListener('touchstart', handleUserInteraction)
    }
  }, [])
  
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

