import { useState, useEffect, useRef } from 'react'

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 px-4 py-3">
      <div className="flex gap-1">
        <span className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
        <span className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
        <span className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
      </div>
      <span className="text-xs text-gray-500 ml-2">Agent en train de répondre…</span>
    </div>
  )
}

export default function AgentChat({ messages = [], onSend, isLoading = false, disabled = false, placeholder = 'Votre message…' }) {
  const [input, setInput] = useState('')
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  const handleSend = () => {
    const text = input.trim()
    if (!text || isLoading || disabled) return
    setInput('')
    onSend(text)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto space-y-3 p-4 min-h-0">
        {messages.length === 0 && !isLoading && (
          <div className="text-center text-gray-600 text-sm py-8">
            En attente de la première réponse de l&apos;agent…
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'user' && (
              <div className="max-w-[85%] rounded-xl px-4 py-3 text-sm whitespace-pre-wrap bg-indigo-700 text-white">
                {msg.content}
              </div>
            )}
            {msg.role === 'error' && (
              <div className="max-w-[85%] rounded-xl px-4 py-3 text-sm whitespace-pre-wrap bg-red-900/40 text-red-300 border border-red-800">
                <span className="font-medium">⚠ </span>{msg.content}
              </div>
            )}
            {msg.role === 'streaming' && (
              <div className="max-w-[85%] rounded-xl px-4 py-3 text-sm bg-gray-800 text-gray-200 border border-gray-700">
                {msg.chainOfThought ? (
                  <div className="text-xs text-gray-600 italic mb-2 pb-2 border-b border-gray-700/50 whitespace-pre-wrap">
                    {msg.chainOfThought}
                  </div>
                ) : null}
                <span className="whitespace-pre-wrap">{msg.content}</span>
                <span className="inline-block w-0.5 h-3.5 bg-indigo-400 animate-pulse ml-0.5 align-text-bottom" />
              </div>
            )}
            {msg.role === 'assistant' && (
              <div className="max-w-[85%] rounded-xl px-4 py-3 text-sm bg-gray-800 text-gray-200 border border-gray-700">
                {msg.chainOfThought ? (
                  <details className="mb-2 pb-2 border-b border-gray-700/50">
                    <summary className="text-xs text-gray-500 cursor-pointer select-none hover:text-gray-400 list-none flex items-center gap-1">
                      <span>&#9656;</span> Raisonnement
                    </summary>
                    <div className="mt-1 text-xs text-gray-600 italic whitespace-pre-wrap">{msg.chainOfThought}</div>
                  </details>
                ) : null}
                <span className="whitespace-pre-wrap">{msg.content}</span>
              </div>
            )}
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-800 border border-gray-700 rounded-xl">
              <TypingIndicator />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="border-t border-gray-700 p-3">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled || isLoading}
            placeholder={disabled ? 'Agent hors sync — interaction impossible' : placeholder}
            rows={2}
            className="flex-1 bg-gray-800 border border-gray-700 text-white text-sm rounded-lg px-3 py-2 placeholder-gray-600 focus:border-indigo-500 focus:outline-none resize-none disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading || disabled}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white text-sm rounded-lg font-medium transition-colors self-end"
          >
            {isLoading ? '…' : 'Envoyer'}
          </button>
        </div>
        <p className="text-xs text-gray-600 mt-1">Entrée pour envoyer · Shift+Entrée pour nouvelle ligne</p>
      </div>
    </div>
  )
}
