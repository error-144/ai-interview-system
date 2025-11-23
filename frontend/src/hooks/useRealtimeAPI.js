import { useEffect, useRef, useState } from 'react'

export function useRealtimeAPI(sessionId, onMessage, onError) {
  const wsRef = useRef(null)
  const audioContextRef = useRef(null)
  const audioQueueRef = useRef([])
  const isPlayingRef = useRef(false)
  const [isConnected, setIsConnected] = useState(false)
  const currentAudioChunksRef = useRef([])
  const isReceivingAudioRef = useRef(false)
  const isAISpeakingRef = useRef(false)  // Track when AI is speaking
  
  // Store callbacks in refs to avoid re-creating connections when they change
  const onMessageRef = useRef(onMessage)
  const onErrorRef = useRef(onError)
  
  // Update refs when callbacks change
  useEffect(() => {
    onMessageRef.current = onMessage
    onErrorRef.current = onError
  }, [onMessage, onError])

  useEffect(() => {
    if (!sessionId) {
      // Clean up if sessionId becomes null
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
      setIsConnected(false)
      return
    }
    
    // Prevent multiple connections for the same sessionId
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      console.log('[OpenAI] WebSocket already connected, skipping new connection')
      return
    }

    // Connect to OpenAI WebSocket endpoint
    const connectToOpenAI = async () => {
      try {
        // Get OpenAI WebSocket URL from backend
        const response = await fetch(`/api/openai-websocket-url/${sessionId}`)
        if (!response.ok) {
          throw new Error(`Failed to get WebSocket URL: ${response.statusText}`)
        }
        
        const { ws_url } = await response.json()
        
        if (!ws_url) {
          throw new Error('Missing WebSocket URL')
        }
        
        console.log('[OpenAI] Connecting to:', ws_url)
        console.log('[OpenAI] Session ID:', sessionId)
        
        // Connect to OpenAI WebSocket endpoint
        const ws = new WebSocket(ws_url)
        wsRef.current = ws
        
        // Log WebSocket state changes
        console.log('[OpenAI] WebSocket created, initial state:', ws.readyState)

        ws.onopen = () => {
          console.log('[OpenAI] WebSocket connected')
          setIsConnected(true)
          
          // Initialize audio context for playback
          audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)({
            sampleRate: 24000, // ElevenLabs TTS uses 24kHz
          })
          
          // Resume audio context if suspended (browser autoplay policy)
          if (audioContextRef.current.state === 'suspended') {
            audioContextRef.current.resume().then(() => {
              console.log('[OpenAI] Audio context resumed on connect')
            }).catch(err => {
              console.error('[OpenAI] Error resuming audio context:', err)
            })
          }
          
          // Send a ping to confirm connection is working
          try {
            ws.send(JSON.stringify({ type: "ping" }))
            console.log('[OpenAI] Sent initial ping to confirm connection')
          } catch (err) {
            console.error('[OpenAI] Error sending initial ping:', err)
          }
          
          // Log WebSocket state
          console.log('[OpenAI] WebSocket readyState after open:', ws.readyState, '(should be 1 = OPEN)')
        }

        ws.onmessage = async (event) => {
          try {
            // Check if message is binary (audio) or text (JSON)
            if (event.data instanceof Blob || event.data instanceof ArrayBuffer) {
              // Binary audio data from OpenAI TTS
              const audioData = await event.data.arrayBuffer()
              if (isReceivingAudioRef.current) {
                currentAudioChunksRef.current.push(audioData)
                // Log occasionally
                if (currentAudioChunksRef.current.length % 10 === 0) {
                  console.log(`[OpenAI] Received ${currentAudioChunksRef.current.length} audio chunks`)
                }
              } else {
                // Legacy: direct playback (shouldn't happen with audio_start/audio_end)
                console.warn('[OpenAI] Received audio without audio_start marker')
                audioQueueRef.current.push(audioData)
                playAudioQueue()
              }
            } else {
              // JSON message
              const data = JSON.parse(event.data)
              const msgType = data.type
              
              console.log('[OpenAI] Received message:', msgType)
              
              if (msgType === 'audio_start') {
                // Start receiving audio chunks
                console.log('[OpenAI] Audio stream started - AI is speaking')
                isReceivingAudioRef.current = true
                isAISpeakingRef.current = true
                currentAudioChunksRef.current = []
              } else if (msgType === 'audio_end') {
                // End of audio - add to queue and play
                console.log(`[OpenAI] Audio stream ended, ${currentAudioChunksRef.current.length} chunks received`)
                isReceivingAudioRef.current = false
                // Note: isAISpeakingRef will be set to false after playback finishes
                if (currentAudioChunksRef.current.length > 0) {
                  const totalSize = currentAudioChunksRef.current.reduce((sum, chunk) => sum + chunk.byteLength, 0)
                  console.log(`[OpenAI] Queuing audio: ${totalSize} bytes (queue length: ${audioQueueRef.current.length})`)
                  // Combine all chunks into a single ArrayBuffer for this audio stream
                  const combinedSize = currentAudioChunksRef.current.reduce((sum, chunk) => sum + chunk.byteLength, 0)
                  const combinedBuffer = new Uint8Array(combinedSize)
                  let offset = 0
                  for (const chunk of currentAudioChunksRef.current) {
                    combinedBuffer.set(new Uint8Array(chunk), offset)
                    offset += chunk.byteLength
                  }
                  // Add combined audio to queue
                  audioQueueRef.current.push(combinedBuffer.buffer)
                  // Try to play (will queue if already playing)
                  playAudioQueue()
                  currentAudioChunksRef.current = []
                } else {
                  console.warn('[OpenAI] No audio chunks received before audio_end')
                }
              } else if (msgType === 'transcript') {
                // User's speech was transcribed
                if (data.content && onMessageRef.current) {
                  onMessageRef.current({
                    role: data.role || 'user',
                    content: data.content
                  })
                }
              } else if (msgType === 'next_question') {
                // AI response/question - signal that processing is complete
                console.log('[OpenAI] Next question received, AI response processing complete')
                if (data.content && onMessageRef.current) {
                  onMessageRef.current({
                    role: data.role || 'assistant',
                    content: data.content
                  })
                }
                // Signal that we can resume listening (will be set after audio playback)
              } else if (msgType === 'interview_completed') {
                // Interview completed - send message with feedback data
                if (data.message && onMessageRef.current) {
                  onMessageRef.current({
                    role: 'assistant',
                    content: data.message,
                    interviewCompleted: true,
                    overallScore: data.overall_score,
                    overallFeedback: data.overall_feedback
                  })
                }
              } else if (msgType === 'error') {
                const errorMsg = data.message || 'Unknown error occurred'
                console.error('[OpenAI] Error:', errorMsg)
                if (onErrorRef.current) {
                  onErrorRef.current(errorMsg)
                }
              } else if (msgType === 'pong') {
                // Keep-alive response
                console.log('[OpenAI] Pong received')
              }
            }
          } catch (error) {
            console.error('[OpenAI] Error parsing message:', error, event.data)
            if (onErrorRef.current) {
              onErrorRef.current(`Failed to parse message: ${error.message}`)
            }
          }
        }

        ws.onerror = (error) => {
          console.error('[OpenAI] WebSocket error:', error)
          console.error('[OpenAI] WebSocket error details:', {
            readyState: ws.readyState,
            url: ws.url
          })
          setIsConnected(false)
        }

        ws.onclose = (event) => {
          console.log('[OpenAI] WebSocket closed', event.code, event.reason)
          console.log('[OpenAI] Close event details:', {
            code: event.code,
            reason: event.reason,
            wasClean: event.wasClean
          })
          setIsConnected(false)
          wsRef.current = null  // Clear ref when closed
          if (event.code !== 1000 && event.code !== 1001 && onErrorRef.current) {
            const reason = event.reason || 'Connection closed unexpectedly'
            onErrorRef.current(`OpenAI connection closed: ${reason} (code: ${event.code})`)
          }
        }
      } catch (error) {
        console.error('[OpenAI] Error connecting:', error)
        if (onErrorRef.current) {
          onErrorRef.current(`Failed to connect to OpenAI: ${error.message}`)
        }
      }
    }
    
    connectToOpenAI()

    return () => {
      console.log('[OpenAI] Cleaning up WebSocket connection')
      // Only close if WebSocket is still open
      if (wsRef.current) {
        if (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING) {
          wsRef.current.close(1000, 'Component unmounting')
        }
        wsRef.current = null
      }
      if (audioContextRef.current) {
        audioContextRef.current.close()
        audioContextRef.current = null
      }
    }
  }, [sessionId])  // Only depend on sessionId, not callbacks

  const playAudioQueue = async () => {
    // If already playing, just return - audio will be queued and played after current finishes
    if (isPlayingRef.current) {
      console.log('[OpenAI] Audio already playing, queuing for later')
      return
    }

    // If no audio in queue, return
    if (audioQueueRef.current.length === 0) {
      return
    }

    isPlayingRef.current = true
    const audioContext = audioContextRef.current

    // Process one complete audio stream at a time
    // Find the end of the current audio stream (all chunks until next audio_start)
    const combinedChunks = []
    
    // Take all chunks from queue (they're already combined per audio stream)
    while (audioQueueRef.current.length > 0) {
      combinedChunks.push(audioQueueRef.current.shift())
    }

    const combinedAudio = new Uint8Array(
      combinedChunks.reduce((acc, chunk) => acc + chunk.byteLength, 0)
    )
    let offset = 0
    for (const chunk of combinedChunks) {
      combinedAudio.set(new Uint8Array(chunk), offset)
      offset += chunk.byteLength
    }

    try {
      console.log(`[OpenAI] Decoding ${combinedAudio.length} bytes of MP3 audio`)
      
      // Ensure audio context is running (browser autoplay policy)
      if (audioContext.state === 'suspended') {
        console.log('[OpenAI] Audio context suspended, resuming...')
        try {
          await audioContext.resume()
          console.log('[OpenAI] Audio context resumed')
        } catch (err) {
          console.error('[OpenAI] Error resuming audio context:', err)
          // If we can't resume, reset the flag anyway after a timeout
          setTimeout(() => {
            isAISpeakingRef.current = false
            console.log('[OpenAI] AI speaking flag reset (audio context resume failed)')
          }, 2000)
        }
      }
      
      // Decode MP3 audio data
      const audioBuffer = await audioContext.decodeAudioData(combinedAudio.buffer)
      console.log(`[OpenAI] Audio decoded: ${audioBuffer.duration.toFixed(2)}s, ${audioBuffer.sampleRate}Hz`)
      
      // Play audio
      const source = audioContext.createBufferSource()
      source.buffer = audioBuffer
      source.connect(audioContext.destination)
      
      console.log('[OpenAI] Starting audio playback')
      
      // Set a timeout fallback to reset isAISpeaking if audio doesn't finish
      const audioDuration = audioBuffer.duration * 1000 // Convert to milliseconds
      const timeoutId = setTimeout(() => {
        console.warn('[OpenAI] Audio playback timeout, resetting isAISpeaking flag')
        isAISpeakingRef.current = false
      }, audioDuration + 1000) // Add 1 second buffer
      
      await new Promise((resolve) => {
        source.onended = () => {
          console.log('[OpenAI] Audio playback finished')
          clearTimeout(timeoutId)
          resolve()
        }
        source.onerror = (error) => {
          console.error('[OpenAI] Audio playback error:', error)
          clearTimeout(timeoutId)
          resolve()
        }
        try {
          source.start(0)
        } catch (err) {
          console.error('[OpenAI] Error starting audio source:', err)
          clearTimeout(timeoutId)
          resolve()
        }
      })
    } catch (error) {
      console.error('[OpenAI] Error playing audio:', error)
      console.error('[OpenAI] Audio context state:', audioContext?.state)
      console.error('[OpenAI] Audio data length:', combinedAudio.length)
      // Reset flag on error so microphone can resume
      isAISpeakingRef.current = false
    }

    // Mark as not playing
    isPlayingRef.current = false
    
    // Mark AI as finished speaking only if queue is empty
    if (audioQueueRef.current.length === 0) {
      isAISpeakingRef.current = false
      console.log('[OpenAI] AI finished speaking, microphone can resume')
      // Dispatch custom event to signal that AI response is complete
      window.dispatchEvent(new CustomEvent('aiResponseComplete'))
    }

    // Check if there's more audio in queue and play it
    if (audioQueueRef.current.length > 0) {
      console.log(`[OpenAI] More audio in queue (${audioQueueRef.current.length} chunks), continuing playback`)
      // Use setTimeout to avoid recursion issues
      setTimeout(() => {
        playAudioQueue()
      }, 100)
    }
  }

  const sendAudio = (audioData) => {
    if (!wsRef.current) {
      // Log occasionally to avoid spam
      if (Math.random() < 0.01) { // 1% chance to log
        console.warn('[OpenAI] sendAudio: WebSocket ref is null')
      }
      return
    }
    
    const readyState = wsRef.current.readyState
    if (readyState !== WebSocket.OPEN) {
      // Log occasionally to avoid spam
      if (Math.random() < 0.01) { // 1% chance to log
        const stateNames = {
          [WebSocket.CONNECTING]: 'CONNECTING',
          [WebSocket.OPEN]: 'OPEN',
          [WebSocket.CLOSING]: 'CLOSING',
          [WebSocket.CLOSED]: 'CLOSED'
        }
        console.warn(`[OpenAI] sendAudio: WebSocket not open (state: ${stateNames[readyState] || readyState})`)
      }
      return
    }
    
    // Send binary audio data (PCM16, 16kHz)
    try {
      if (audioData instanceof Int16Array) {
        wsRef.current.send(audioData.buffer)
      } else if (audioData instanceof ArrayBuffer) {
        wsRef.current.send(audioData)
      } else {
        console.warn('[OpenAI] Invalid audio data format:', typeof audioData, audioData?.constructor?.name)
      }
    } catch (error) {
      console.error('[OpenAI] Error sending audio:', error)
    }
  }

  const endAudio = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: "end_audio"
      }))
    }
  }

  return {
    isConnected,
    sendAudio,
    endAudio,
    isAISpeaking: () => isAISpeakingRef.current,  // Function to check if AI is speaking
  }
}

