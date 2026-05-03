import React, { useRef, useState } from 'react'

export default function ChatInput({ onSend, disabled }) {
  const [text, setText] = useState('')
  const taRef = useRef(null)

  const submit = (e) => {
    e?.preventDefault?.()
    if (!text.trim()) return
    onSend?.(text)
    setText('')
    // restore height
    if (taRef.current) {
      taRef.current.style.height = 'auto'
    }
  }

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  const autoResize = (el) => {
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 160) + 'px'
  }

  return (
    <form className="chatinput" onSubmit={submit}>
      <textarea
        ref={taRef}
        rows={1}
        placeholder={disabled ? 'Connecting to server…' : 'Ask a question… (Shift+Enter for newline)'}
        value={text}
        onChange={(e) => { setText(e.target.value); if (taRef.current) autoResize(taRef.current) }}
        onKeyDown={onKeyDown}
        disabled={disabled}
        aria-label="Message input"
      />
      <button className="btn btn--primary" type="submit" disabled={disabled || !text.trim()} aria-label="Send message">
        Send
      </button>
    </form>
  )
}
