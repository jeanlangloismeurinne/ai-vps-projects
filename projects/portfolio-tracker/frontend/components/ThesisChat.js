import { useState, useEffect, useRef } from 'react'
import DustRunViewer from './DustRunViewer'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

export default function ThesisChat({ entityType, entityId, ticker, isValidated }) {
  const [turns, setTurns] = useState([])
  const [convId, setConvId] = useState(null)
  const [input, setInput] = useState('')
  const [status, setStatus] = useState('idle')
  const [openCot, setOpenCot] = useState(null)
  const bottomRef = useRef(null)

  const historyUrl = entityType === 'watchlist'
    ? `${API}/watchlist/${entityId}/chat`
    : `${API}/positions/${entityId}/thesis-chat`

  const chatUrl = entityType === 'watchlist'
    ? `${API}/watchlist/${entityId}/chat`
    : `${API}/positions/${entityId}/thesis-chat`

  useEffect(() => {
    fetch(historyUrl)
      .then(r => r.json())
      .then(d => {
        setTurns(d.turns || [])
        setConvId(d.conversation_id)
      })
      .catch(() => {})
  }, [entityId, entityType])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [turns])

  const send = async () => {
    if (!input.trim() || status === 'waiting') return
    const msg = input.trim()
    setInput('')
    setStatus('waiting')
    setTurns(prev => [...prev, { role: 'human', content: msg }])

    const timeout = new Promise((_, rej) => setTimeout(() => rej(new Error('timeout')), 360000))
    try {
      const res = await Promise.race([
        fetch(chatUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: msg }),
        }),
        timeout,
      ])
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'error')
      setTurns(prev => [...prev, {
        role: 'agent',
        content: data.agent_response,
        chain_of_thought: data.chain_of_thought,
        conversation_id: data.conversation_id || convId,
      }])
      if (data.conversation_id) setConvId(data.conversation_id)
      setStatus('idle')
    } catch (e) {
      setStatus('error')
      setTurns(prev => [...prev, { role: 'error', content: e.message === 'timeout' ? 'Timeout (60s)' : e.message }])
    }
  }

  return (
    <div className="flex flex-col h-96">
      <div className="flex-1 overflow-y-auto space-y-3 pr-1 pb-2">
        {turns.length === 0 && (
          <p className="text-gray-500 text-sm text-center py-8">
            {isValidated ? 'Thèse validée — lecture seule' : 'Posez vos questions à l\'agent…'}
          </p>
        )}
        {turns.map((t, i) => (
          <div key={i} className={`flex ${t.role === 'human' ? 'justify-end' : 'justify-start'}`}>
            {t.role === 'human' && (
              <div className="max-w-xs lg:max-w-md bg-blue-800 text-white px-3 py-2 rounded-lg text-sm">
                {t.content}
              </div>
            )}
            {t.role === 'agent' && (
              <div className="max-w-xs lg:max-w-md space-y-1">
                <div className="bg-gray-800 text-gray-100 px-3 py-2 rounded-lg text-sm whitespace-pre-wrap">
                  {t.content}
                </div>
                {t.chain_of_thought && (
                  <button onClick={() => setOpenCot(openCot === i ? null : i)}
                    className="text-xs text-gray-500 hover:text-gray-300">
                    {openCot === i ? '▲ Masquer raisonnement' : '▼ Voir le raisonnement'}
                  </button>
                )}
                {openCot === i && t.chain_of_thought && (
                  <div className="text-xs text-gray-400 bg-gray-850 border border-gray-700 rounded p-2 whitespace-pre-wrap">
                    {t.chain_of_thought}
                  </div>
                )}
              </div>
            )}
            {t.role === 'error' && (
              <div className="bg-red-900/50 text-red-300 px-3 py-2 rounded text-sm">
                ⚠️ {t.content}
                <button onClick={() => setStatus('idle')} className="ml-2 underline text-xs">Réessayer</button>
              </div>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {isValidated ? (
        <div className="mt-2 px-3 py-2 bg-emerald-900/20 border border-emerald-800 rounded text-xs text-emerald-300 text-center">
          Thèse validée — mode lecture seule
        </div>
      ) : (
        <div className="mt-2 flex gap-2">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
            disabled={status === 'waiting'}
            placeholder={status === 'waiting' ? "L'agent analyse votre question…" : "Votre question…"}
            className="flex-1 bg-gray-800 border border-gray-700 text-gray-100 text-sm rounded px-3 py-2 placeholder-gray-500 disabled:opacity-50"
          />
          <button onClick={send} disabled={status === 'waiting' || !input.trim()}
            className="px-4 py-2 bg-blue-700 hover:bg-blue-600 text-white text-sm rounded font-medium disabled:opacity-50">
            {status === 'waiting' ? '…' : 'Envoyer'}
          </button>
        </div>
      )}
    </div>
  )
}
