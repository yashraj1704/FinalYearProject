import React, { useEffect, useMemo, useRef, useState } from 'react'
import ChatBox from './components/ChatBox'
import ChatInput from './components/ChatInput'

const WS_URL = 'ws://localhost:8000/chat'

export default function App() {
  const wsRef = useRef(null)
  const [connected, setConnected] = useState(false)
  const [messages, setMessages] = useState([
    { id: 'sys-1', role: 'assistant', content: 'Hello! I\'m your AI assistant. How can I help you today?' },
  ])
  const [isTyping, setIsTyping] = useState(false)
  const [typingEffect, setTypingEffect] = useState(false)
  const [uploadedFiles, setUploadedFiles] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [voiceTranscript, setVoiceTranscript] = useState('')
  const [isListening, setIsListening] = useState(false)
  const [voiceSupported, setVoiceSupported] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [isReindexing, setIsReindexing] = useState(false)
  const [uploadStatus, setUploadStatus] = useState('')
  const [suggestions, setSuggestions] = useState([
    "What are the main topics covered?",
    "Summarize key findings",
    "What are the important concepts?",
    "Explain the methodology used",
    "What conclusions can be drawn?"
  ])
  const [showSuggestions, setShowSuggestions] = useState(true)
  const [selectedDocument, setSelectedDocument] = useState(null)
  const [currentTheme, setCurrentTheme] = useState('dark')
  const fileInputRef = useRef(null)
  const messagesEndRef = useRef(null)
  const streamRef = useRef({ id: null })

  const themes = {
    dark: {
      name: 'Dark Space',
      primary: '#0f0f23',
      secondary: '#1a1b3a',
      accent: '#6366f1',
      text: '#ffffff',
      muted: '#9ca3af',
      panel: 'rgba(26, 27, 58, 0.95)',
      gradient1: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
      gradient2: 'linear-gradient(135deg, #ec4899, #f43f5e)',
      gradient3: 'linear-gradient(135deg, #4facfe, #00f2fe)',
      gradient4: 'linear-gradient(135deg, #10b981, #14b8a6)'
    },
    ocean: {
      name: 'Ocean Blue',
      primary: '#0f172a',
      secondary: '#1e293b',
      accent: '#0ea5e9',
      text: '#f1f5f9',
      muted: '#64748b',
      panel: 'rgba(30, 41, 59, 0.95)',
      gradient1: 'linear-gradient(135deg, #0ea5e9, #0284c7)',
      gradient2: 'linear-gradient(135deg, #06b6d4, #0891b2)',
      gradient3: 'linear-gradient(135deg, #0e7490, #155e75)',
      gradient4: 'linear-gradient(135deg, #14b8a6, #10b981)'
    },
    sunset: {
      name: 'Sunset Orange',
      primary: '#1a0f0f',
      secondary: '#2d1810',
      accent: '#f97316',
      text: '#fff7ed',
      muted: '#d4a574',
      panel: 'rgba(45, 24, 16, 0.95)',
      gradient1: 'linear-gradient(135deg, #f97316, #ea580c)',
      gradient2: 'linear-gradient(135deg, #fb923c, #fdba74)',
      gradient3: 'linear-gradient(135deg, #fed7aa, #fbbf24)',
      gradient4: 'linear-gradient(135deg, #a16207, #dc2626)'
    },
    forest: {
      name: 'Forest Green',
      primary: '#0a1f0f',
      secondary: '#14532d',
      accent: '#16a34a',
      text: '#ecfdf5',
      muted: '#6b7280',
      panel: 'rgba(20, 83, 45, 0.95)',
      gradient1: 'linear-gradient(135deg, #16a34a, #15803d)',
      gradient2: 'linear-gradient(135deg, #22c55e, #16a34a)',
      gradient3: 'linear-gradient(135deg, #84cc16, #65a30d)',
      gradient4: 'linear-gradient(135deg, #065f46, #047857)'
    },
    purple: {
      name: 'Royal Purple',
      primary: '#1a0f2a',
      secondary: '#2e1065',
      accent: '#9333ea',
      text: '#faf5ff',
      muted: '#a78bfa',
      panel: 'rgba(46, 16, 101, 0.95)',
      gradient1: 'linear-gradient(135deg, #9333ea, #7c3aed)',
      gradient2: 'linear-gradient(135deg, #a855f7, #9333ea)',
      gradient3: 'linear-gradient(135deg, #c084fc, #a855f7)',
      gradient4: 'linear-gradient(135deg, #e879f9, #c084fc)'
    }
  }

  // Load existing documents on mount
  useEffect(() => {
    loadDocuments()
    checkVoiceSupport()
  }, [])

  // Apply theme to document root
  useEffect(() => {
    const root = document.documentElement
    const theme = themes[currentTheme]
    
    // Apply CSS custom properties
    Object.entries(theme).forEach(([key, value]) => {
      if (key !== 'name') {
        root.style.setProperty(`--theme-${key}`, value)
      }
    })
    
    // Update meta theme-color
    const metaTheme = document.querySelector('meta[name="theme-color"]')
    if (metaTheme) {
      metaTheme.content = theme.primary
    }
  }, [currentTheme])

  const switchTheme = (themeName) => {
    setCurrentTheme(themeName)
    // Save to localStorage
    localStorage.setItem('chatbot-theme', themeName)
  }

  // Load saved theme on mount
  useEffect(() => {
    const savedTheme = localStorage.getItem('chatbot-theme')
    if (savedTheme && themes[savedTheme]) {
      setCurrentTheme(savedTheme)
    }
  }, [])

  const checkVoiceSupport = () => {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      setVoiceSupported(true)
    }
  }

  const startVoiceRecognition = () => {
    if (!voiceSupported) {
      alert('Voice recognition is not supported in your browser. Please try Chrome, Edge, or Safari.')
      return
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    const recognition = new SpeechRecognition()

    recognition.continuous = false
    recognition.interimResults = false
    recognition.lang = 'en-US'
    recognition.maxAlternatives = 1
    recognition.interimResults = false

    recognition.onstart = () => {
      setIsListening(true)
      console.log('Voice recognition started')
    }

    recognition.onresult = (event) => {
      const transcript = Array.from(event.results)
        .map(result => result[0].transcript)
        .join('')
        .toLowerCase()
      
      if (transcript.trim()) {
        console.log('Voice transcript:', transcript)
        sendQuestion(transcript)
        
        // Add voice output to messages
        setMessages(prev => [...prev, {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: `🎤 **Voice Input Detected**: "${transcript}"`
        }])
      }
    }

    recognition.onerror = (event) => {
      console.error('Speech recognition error:', event.error)
      setIsListening(false)
      
      // Add error message
      setMessages(prev => [...prev, {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: `❌ **Voice Error**: ${event.error}. Please try again.`
      }])
    }

    recognition.onend = () => {
      setIsListening(false)
      console.log('Voice recognition ended')
    }

    recognition.start()
  }

  const loadDocuments = async () => {
    try {
      const response = await fetch('http://localhost:8000/documents')
      if (response.ok) {
        const data = await response.json()
        setUploadedFiles(data.documents.map(doc => ({
          name: doc.name,
          size: doc.size,
          uploadTime: new Date(doc.modified * 1000).toLocaleTimeString()
        })))
      }
    } catch (error) {
      console.error('Error loading documents:', error)
    }
  }

  useEffect(() => {
    const ws = new WebSocket(WS_URL)
    wsRef.current = ws

    ws.onopen = () => setConnected(true)
    ws.onclose = () => { setConnected(false); setIsTyping(false); streamRef.current.id = null }
    ws.onerror = () => { setConnected(false); setIsTyping(false); streamRef.current.id = null }

    ws.onmessage = (event) => {
      const token = event.data
      if (token === '__END__') {
        streamRef.current.id = null
        setIsTyping(false)
        setTypingEffect(false)
        return
      }
      if (token === '__ERROR__') {
        streamRef.current.id = null
        setIsTyping(false)
        setTypingEffect(false)
        setMessages((prev) => ([...prev, { id: crypto.randomUUID(), role: 'assistant', content: 'An error occurred.' }]))
        return
      }
      
      // Start typing effect on first token
      if (!streamRef.current.id) {
        setTypingEffect(true)
        setTimeout(() => setTypingEffect(false), 500) // Stop effect after 500ms
      }
      
      // Ensure a single assistant bubble is used during streaming
      setMessages((prev) => {
        const currentId = streamRef.current.id
        if (currentId && prev[prev.length - 1]?.id === currentId) {
          const copy = prev.slice()
          copy[copy.length - 1] = {
            ...copy[copy.length - 1],
            content: copy[copy.length - 1].content + token,
          }
          return copy
        }
        const id = currentId || crypto.randomUUID()
        if (!currentId) streamRef.current.id = id
        return [...prev, { id, role: 'assistant', content: token.trim() }]
      })
    }

    return () => {
      ws.close()
    }
  }, [])

  const sendQuestion = (text) => {
    if (!text?.trim()) return
    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: 'user', content: text }])
    setIsTyping(true)
    setTypingEffect(true)
    setShowSuggestions(false) // Hide suggestions after sending
    streamRef.current.id = null
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ question: text }))
    }
  }

  const handleSuggestionClick = (suggestion) => {
    sendQuestion(suggestion)
  }

  const handleDocumentClick = (file) => {
    setSelectedDocument(selectedDocument?.name === file.name ? null : file)
  }

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  const handleFileUpload = async (event) => {
    const file = event.target.files[0]
    if (!file) return

    console.log('Uploading file:', file.name, file.type, file.size)
    setIsLoading(true)
    setIsUploading(true)
    setUploadStatus('📤 Uploading...')

    // Check file type
    const allowedTypes = ['application/pdf', 'text/plain', 'text/markdown']
    if (!allowedTypes.includes(file.type) && !file.name.endsWith('.md')) {
      setUploadStatus('❌ Please upload PDF, TXT, or MD files only.')
      setIsLoading(false)
      setIsUploading(false)
      setTimeout(() => setUploadStatus(''), 3000)
      return
    }

    // Check file size (10MB limit)
    if (file.size > 10 * 1024 * 1024) {
      setUploadStatus('❌ File size must be less than 10MB.')
      setIsLoading(false)
      setIsUploading(false)
      setTimeout(() => setUploadStatus(''), 3000)
      return
    }

    const formData = new FormData()
    formData.append('file', file)

    try {
      console.log('Sending upload request...')
      const response = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        body: formData,
      })

      console.log('Upload response status:', response.status)
      
      if (response.ok) {
        const result = await response.json()
        console.log('Upload result:', result)
        
        // Reload documents list
        await loadDocuments()
        
        setUploadStatus(`✅ Successfully uploaded "${file.name}"`)
        setMessages(prev => [...prev, {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: `✅ Successfully uploaded "${file.name}". ${result.reindexed ? 'Document has been indexed and is ready for questions.' : 'Document saved. Indexing in progress...'}`
        }])
      } else {
        const errorText = await response.text()
        console.error('Upload failed:', errorText)
        throw new Error(`Upload failed: ${response.status}`)
      }
    } catch (error) {
      console.error('Upload error:', error)
      setUploadStatus(`❌ Failed to upload "${file.name}". Error: ${error.message}. Please try again.`)
      setMessages(prev => [...prev, {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: `❌ Failed to upload "${file.name}". Error: ${error.message}. Please try again.`
      }])
    } finally {
      setIsLoading(false)
      setIsUploading(false)
      setTimeout(() => setUploadStatus(''), 3000)
    }

    // Clear the file input
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const deleteDocument = async (filename) => {
    if (!confirm(`Are you sure you want to delete "${filename}"?`)) {
      return
    }

    try {
      const response = await fetch(`http://localhost:8000/documents/${filename}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        const result = await response.json()
        await loadDocuments()
        setMessages(prev => [...prev, {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: `✅ ${result.message}`
        }])
      } else {
        throw new Error('Delete failed')
      }
    } catch (error) {
      setMessages(prev => [...prev, {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: `❌ Failed to delete "${filename}". Please try again.`
      }])
    }
  }

  const manualReindex = async () => {
    setIsLoading(true)
    setIsReindexing(true)
    try {
      const response = await fetch('http://localhost:8000/reindex', {
        method: 'POST'
      })

      if (response.ok) {
        const result = await response.json()
        setMessages(prev => [...prev, {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: result.success ? '✅ Re-indexing completed successfully.' : '⚠️ Re-indexing completed with some issues.'
        }])
      } else {
        throw new Error('Re-index failed')
      }
    } catch (error) {
      setMessages(prev => [...prev, {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: `❌ Failed to re-index documents.`
      }])
    } finally {
      setIsLoading(false)
      setIsReindexing(false)
    }
  }

  const clearChat = () => {
    setMessages([
      { id: 'sys-1', role: 'assistant', content: 'Hi! Ask me about your documents.\n\nYou can upload PDF or text files using the Upload button above.' },
    ])
  }

  const triggerFileUpload = () => {
    if (!isLoading) {
      console.log('Upload button clicked')
      fileInputRef.current?.click()
    }
  }

  return (
    <div className="app">
      <header className="app__header">
        <div className="brand">
          <div className="brand__logo">AI</div>
          <div className="brand__name">Document Assistant</div>
        </div>
        <div className="header-actions">
          <div className="theme-switcher">
            <button 
              className="theme-btn"
              onClick={() => {
                const themeKeys = Object.keys(themes)
                const currentIndex = themeKeys.indexOf(currentTheme)
                const nextIndex = (currentIndex + 1) % themeKeys.length
                switchTheme(themeKeys[nextIndex])
              }}
              title={`Current theme: ${themes[currentTheme].name}. Click to switch theme.`}
            >
              <span className="theme-icon">🎨</span>
              <span className="theme-name">{themes[currentTheme].name}</span>
            </button>
            <div className="theme-dropdown">
              {Object.entries(themes).map(([key, theme]) => (
                <button
                  key={key}
                  className={`theme-option ${key === currentTheme ? 'active' : ''}`}
                  onClick={() => switchTheme(key)}
                  title={`Switch to ${theme.name} theme`}
                >
                  <div className="theme-preview" style={{background: theme.gradient1}}></div>
                  <span>{theme.name}</span>
                </button>
              ))}
            </div>
          </div>
          <button 
            className={`voice-btn ${isListening ? 'listening' : ''}`}
            onClick={startVoiceRecognition}
            disabled={!voiceSupported || isListening || isLoading}
            title={voiceSupported ? "Click to speak your question" : "Voice not supported"}
          >
            {isListening ? (
              <>
                <span className="voice-icon">🎤</span>
                <span className="voice-text">Listening...</span>
              </>
            ) : (
              <>
                <span className="voice-icon">🎤</span>
                <span className="voice-text">Voice</span>
              </>
            )}
          </button>
          <button className="clear-btn" onClick={clearChat} title="Clear chat">
            🗑️ Clear
          </button>
          <span className={connected ? 'status status--ok' : 'status status--down'}>
            <span className="dot"></span>
            {connected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </header>

      <div className="app__content">
        {/* Left Sidebar - Documents */}
        <aside className="sidebar">
          <div className="sidebar__header">
            <h2>📚 Documents</h2>
            <button 
              className="upload-btn"
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
            >
              {isUploading ? '⏳ Uploading...' : '📤 Upload'}
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.txt,.md"
              onChange={handleFileUpload}
              disabled={isUploading}
              style={{ display: 'none' }}
            />
          </div>

          {uploadStatus && (
            <div className="upload-status">{uploadStatus}</div>
          )}

          <div className="documents-list">
            {uploadedFiles.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">📄</div>
                <p>No documents uploaded yet</p>
                <small>Upload PDF, TXT, or MD files to get started</small>
              </div>
            ) : (
              uploadedFiles.map((file, index) => (
                <div 
                  key={index} 
                  className={`document-item ${selectedDocument?.name === file.name ? 'selected' : ''}`}
                  onClick={() => handleDocumentClick(file)}
                >
                  <div className="document-info">
                    <div className="document-icon">
                      {file.name.endsWith('.pdf') ? '📕' : file.name.endsWith('.txt') ? '📄' : '📝'}
                    </div>
                    <div className="document-details">
                      <div className="document-name">{file.name}</div>
                      <div className="document-meta">
                        {formatFileSize(file.size)} • {file.uploadTime}
                      </div>
                    </div>
                  </div>
                  <button 
                    className="delete-btn" 
                    onClick={(e) => {
                      e.stopPropagation()
                      deleteDocument(file.name)
                    }}
                    title="Delete document"
                    disabled={isLoading}
                  >
                    🗑️
                  </button>
                </div>
              ))
            )}
          </div>

          {selectedDocument && (
            <div className="document-preview">
              <div className="preview-header">
                <span>📄 {selectedDocument.name}</span>
                <button 
                  className="close-preview"
                  onClick={() => setSelectedDocument(null)}
                  title="Close preview"
                >
                  ✕
                </button>
              </div>
              <div className="preview-content">
                <p>📊 <strong>File Size:</strong> {formatFileSize(selectedDocument.size)}</p>
                <p>⏰ <strong>Upload Time:</strong> {selectedDocument.uploadTime}</p>
                <p>📝 <strong>Type:</strong> {selectedDocument.name.endsWith('.pdf') ? 'PDF Document' : selectedDocument.name.endsWith('.txt') ? 'Text File' : 'Markdown File'}</p>
                <div className="preview-actions">
                  <button 
                    className="ask-about-doc-btn"
                    onClick={() => {
                      const question = `Tell me about the document "${selectedDocument.name}"`
                      sendQuestion(question)
                    }}
                    disabled={isLoading || isTyping}
                  >
                    🤖 Ask About This Document
                  </button>
                </div>
              </div>
            </div>
          )}

          {uploadedFiles.length > 0 && (
            <div className="sidebar__footer">
              <button 
                className="reindex-btn"
                onClick={manualReindex}
                disabled={isReindexing}
              >
                {isReindexing ? '🔄 Re-indexing...' : '🔄 Re-index Documents'}
              </button>
            </div>
          )}
        </aside>

        {/* Main Chat Area */}
        <main className="app__main">
          {voiceTranscript && (
            <div className="voice-transcript">
              <div className="voice-transcript-header">
                <span className="voice-transcript-icon">🎤</span>
                <span className="voice-transcript-text">Voice Input: "{voiceTranscript}"</span>
                <button 
                  className="voice-transcript-clear"
                  onClick={() => setVoiceTranscript('')}
                  title="Clear voice transcript"
                >
                  ✕
                </button>
              </div>
            </div>
          )}
          <ChatBox messages={messages} typing={isTyping} typingEffect={typingEffect} />
        </main>
      </div>

      <footer className="app__footer">
        {showSuggestions && uploadedFiles.length > 0 && (
          <div className="suggestions-container">
            <div className="suggestions-header">
              <span>💡 Quick Questions:</span>
              <button 
                className="suggestions-toggle"
                onClick={() => setShowSuggestions(false)}
                title="Hide suggestions"
              >
                ✕
              </button>
            </div>
            <div className="suggestions-grid">
              {suggestions.map((suggestion, index) => (
                <button
                  key={index}
                  className="suggestion-chip"
                  onClick={() => handleSuggestionClick(suggestion)}
                  disabled={isLoading || isTyping}
                  title="Click to ask this question"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}
        <div className="input-container">
          <ChatInput onSend={sendQuestion} disabled={!connected || isLoading} />
          {!showSuggestions && uploadedFiles.length > 0 && (
            <button 
              className="show-suggestions-btn"
              onClick={() => setShowSuggestions(true)}
              title="Show quick questions"
            >
              💡
            </button>
          )}
        </div>
      </footer>
    </div>
  )
}
