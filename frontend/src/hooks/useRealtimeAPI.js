import { useEffect, useRef, useState } from 'react'

export function useRealtimeAPI(sessionId, onMessage, onError) {
  const wsRef = useRef(null)
  const audioContextRef = useRef(null)
  const audioQueueRef = useRef([])
  const isPlayingRef = useRef(false)
  const [isConnected, setIsConnected] = useState(false)
  const credentialsRef = useRef(null)

  useEffect(() => {
    if (!sessionId) return

    // Fetch credentials from backend
    const connectToSpeechmatics = async () => {
      try {
        // Get Speechmatics credentials from backend
        const response = await fetch(`/api/speechmatics-credentials/${sessionId}`)
        if (!response.ok) {
          throw new Error(`Failed to get credentials: ${response.statusText}`)
        }
        
        const credentials = await response.json()
        credentialsRef.current = credentials
        
        const { ws_url, api_key, agent_id, template_id } = credentials
        
        if (!ws_url || !api_key || !agent_id) {
          throw new Error('Missing Speechmatics credentials')
        }
        
        console.log('[Speechmatics] Connecting to proxy:', ws_url)
        console.log('[Speechmatics] Agent ID:', agent_id)
        console.log('[Speechmatics] Template ID:', template_id || agent_id)
        
        // Connect to backend proxy (which handles authentication)
        // Backend proxy adds Authorization header and forwards to Speechmatics
        const ws = new WebSocket(ws_url)
        wsRef.current = ws
        
        // Store template_id (preferred) or agent_id for StartConversation message
        wsRef.current._templateId = template_id || agent_id

        ws.onopen = () => {
          console.log('[Speechmatics] WebSocket connected')
          setIsConnected(true)
          
          // Initialize audio context for playback (16kHz)
          audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)({
            sampleRate: 16000,
          })
          
          // Send StartConversation message to Speechmatics Flow API
          // This initiates the conversation and the agent will start speaking
          const templateId = wsRef.current._templateId || agent_id
          const startConversationMsg = {
            message: "StartConversation",
            audio_format: {
              type: "raw",
              encoding: "pcm_s16le",
              sample_rate: 16000
            },
            conversation_config: {
              template_id: templateId
            }
          }
          
          console.log('[Speechmatics] Sending StartConversation:', startConversationMsg)
          ws.send(JSON.stringify(startConversationMsg))
        }

        ws.onmessage = async (event) => {
          try {
            // Check if message is binary (audio) or text (JSON)
            if (event.data instanceof Blob || event.data instanceof ArrayBuffer) {
              // Binary audio data from Speechmatics
              const audioData = await event.data.arrayBuffer()
              audioQueueRef.current.push(audioData)
              playAudioQueue()
            } else {
              // JSON message
              const data = JSON.parse(event.data)
              const msgType = data.message || data.type
              
              console.log('[Speechmatics] Received message:', msgType)
              
              if (msgType === 'ConversationStarted') {
                console.log('[Speechmatics] Conversation started - agent will speak first')
                // Agent will automatically start speaking if configured to do so
                // No need to send a message here, wait for ResponseStarted/ResponseCompleted
              } else if (msgType === 'AddTranscript') {
                // User's speech was transcribed
                const transcript = data.transcript || ''
                if (transcript && onMessage) {
                  onMessage({
                    role: 'user',
                    content: transcript
                  })
                }
              } else if (msgType === 'AddPartialTranscript') {
                // Partial transcript
                const partial = data.transcript || ''
                if (partial) {
                  console.log('[Speechmatics] Partial transcript:', partial)
                }
              } else if (msgType === 'ResponseCompleted') {
                // AI finished speaking - extract transcript/text
                const transcript = data.transcript || data.content || ''
                if (transcript && onMessage) {
                  onMessage({
                    role: 'assistant',
                    content: transcript
                  })
                }
              } else if (msgType === 'ResponseStarted') {
                console.log('[Speechmatics] AI response started')
              } else if (msgType === 'ResponseInterrupted') {
                console.log('[Speechmatics] AI response interrupted by user')
              } else if (msgType === 'AddPartialResponse') {
                // Partial AI response (for real-time display)
                const partial = data.transcript || data.content || ''
                if (partial) {
                  console.log('[Speechmatics] Partial AI response:', partial)
                }
              } else if (msgType === 'Error') {
                const errorMsg = data.reason || 'Unknown error occurred'
                console.error('[Speechmatics] Error:', errorMsg)
                if (onError) {
                  onError(errorMsg)
                }
              } else if (msgType === 'ConversationEnded') {
                console.log('[Speechmatics] Conversation ended')
                ws.close()
              }
            }
          } catch (error) {
            console.error('[Speechmatics] Error parsing message:', error, event.data)
            if (onError) {
              onError(`Failed to parse message: ${error.message}`)
            }
          }
        }

        ws.onerror = (error) => {
          console.error('[Speechmatics] WebSocket error:', error)
          setIsConnected(false)
        }

        ws.onclose = (event) => {
          console.log('[Speechmatics] WebSocket closed', event.code, event.reason)
          setIsConnected(false)
          if (event.code !== 1000 && event.code !== 1001 && onError) {
            const reason = event.reason || 'Connection closed unexpectedly'
            onError(`Speechmatics connection closed: ${reason} (code: ${event.code})`)
          }
        }
      } catch (error) {
        console.error('[Speechmatics] Error connecting:', error)
        if (onError) {
          onError(`Failed to connect to Speechmatics: ${error.message}`)
        }
      }
    }
    
    connectToSpeechmatics()

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
      if (audioContextRef.current) {
        audioContextRef.current.close()
      }
    }
  }, [sessionId, onMessage, onError])

  const playAudioQueue = async () => {
    if (isPlayingRef.current || audioQueueRef.current.length === 0) return

    isPlayingRef.current = true
    const audioContext = audioContextRef.current

    while (audioQueueRef.current.length > 0) {
      const audioData = audioQueueRef.current.shift()
      
      try {
        // Decode audio data (PCM16, 16kHz, mono)
        const audioBuffer = await audioContext.decodeAudioData(audioData)
        
        // Play audio
        const source = audioContext.createBufferSource()
        source.buffer = audioBuffer
        source.connect(audioContext.destination)
        
        await new Promise((resolve) => {
          source.onended = resolve
          source.start()
        })
      } catch (error) {
        console.error('[Speechmatics] Error playing audio:', error)
      }
    }

    isPlayingRef.current = false
  }

  const sendAudio = (audioData) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      // Send binary audio directly (PCM16, 16kHz)
      if (audioData instanceof Int16Array) {
        wsRef.current.send(audioData.buffer)
      } else if (audioData instanceof ArrayBuffer) {
        wsRef.current.send(audioData)
      } else {
        console.warn('[Speechmatics] Invalid audio data format')
      }
    }
  }

  const endAudio = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        message: "AudioEnded",
        last_seq_no: 0
      }))
    }
  }

  return {
    isConnected,
    sendAudio,
    endAudio,
  }
}
