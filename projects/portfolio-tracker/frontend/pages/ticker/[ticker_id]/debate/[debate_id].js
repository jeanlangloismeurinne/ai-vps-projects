import React, { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/router'
import Link from 'next/link'
import AgentChat from '../../../../components/AgentChat'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

const POSITION_STYLES = {
  PASS: { cls: 'bg-red-900/50 border-red-700 text-red-300', label: 'PASS maintenu' },
  MONITOR: { cls: 'bg-yellow-900/50 border-yellow-700 text-yellow-300', label: 'MONITOR' },
  PROCEED: { cls: 'bg-emerald-900/50 border-emerald-700 text-emerald-300', label: 'PROCEED' },
}

export default function DebatePage() {
  const router = useRouter()
  const { ticker_id, debate_id } = router.query

  const [debate, setDebate] = useState(null)
  const [messages, setMessages] = useState([])
  const [agentPosition, setAgentPosition] = useState('PASS')
  const [isLoading, setIsLoading] = useState(false)
  const [pageLoading, setPageLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [error, setError] = useState('')
  const initialMessageSent = useRef(false)

  useEffect(() => {
    if (!debate_id || !ticker_id) return
    const init = async () => {
      setPageLoading(true)
      try {
        const [dRes, mRes] = await Promise.all([
          fetch(`${API}/debates/${debate_id}`),
          fetch(`${API}/debates/${debate_id}/messages`),
        ])
        if (dRes.ok) {
          const d = await dRes.json()
          setDebate(d)
          setAgentPosition(d.current_position || d.agent_position || 'PASS')
        }
        if (mRes.ok) {
          const msgs = await mRes.json()
          setMessages(msgs)
        }
      } catch (e) {
        setError('Erreur de chargement')
      }
      setPageLoading(false)
    }
    init()
  }, [debate_id, ticker_id])

  // Send initial message if no messages
  useEffect(() => {
    if (!debate?.id || initialMessageSent.current || messages.length > 0) return
    initialMessageSent.current = true
    sendInitialMessage()
  }, [debate?.id, messages.length])

  const sendInitialMessage = async () => {
    setIsLoading(true)
    try {
      const conviction_note = debate?.conviction_note || ''
      const content = `[mode: conviction_challenge]\n\nConviction de l'investisseur :\n${conviction_note}\n\nAnalyse les arguments et donne ta position actuelle.`
      const res = await fetch(`${API}/debates/${debate.id}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: 'user', content }),
      })
      if (res.ok) {
        const data = await res.json()
        setMessages([
          { role: 'user', content: '(Note de conviction initiale envoyée)' },
          { role: 'assistant', content: data.content || data.message || '' },
        ])
        if (data.agent_position) setAgentPosition(data.agent_position)
      }
    } catch {}
    setIsLoading(false)
  }

  const sendMessage = async (text) => {
    if (!debate?.id) return
    setMessages(prev => [...prev, { role: 'user', content: text }])
    setIsLoading(true)
    try {
      const res = await fetch(`${API}/debates/${debate.id}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: 'user', content: text }),
      })
      if (res.ok) {
        const data = await res.json()
        setMessages(prev => [...prev, { role: 'assistant', content: data.content || data.message || '' }])
        if (data.agent_position) setAgentPosition(data.agent_position)
      }
    } catch {}
    setIsLoading(false)
  }

  const handleClose = async (type) => {
    setActionLoading(true)
    try {
      if (type === 'close_position' || type === 'reduce') {
        await fetch(`${API}/debates/${debate.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ outcome: type }),
        })
        router.push(`/ticker/${ticker_id}/decision/${debate.thesis_id}`)
      } else if (type === 'maintain_override') {
        await fetch(`${API}/debates/${debate.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ outcome: 'maintain_override' }),
        })
        router.push(`/ticker/${ticker_id}`)
      } else if (type === 'new_thesis') {
        router.push(`/ticker/${ticker_id}/opportunity/new?source=debate_proceed`)
      } else if (type === 'back_no_thesis') {
        router.push(`/ticker/${ticker_id}`)
      } else if (type === 'back_monitor') {
        router.push(`/ticker/${ticker_id}`)
      }
    } catch (e) {
      setError(e.message)
    }
    setActionLoading(false)
  }

  if (pageLoading) return <div className="text-center py-16 text-gray-500">Chargement…</div>

  const posStyle = POSITION_STYLES[agentPosition] || POSITION_STYLES.PASS

  return (
    <div className="space-y-4">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-gray-600">
        <Link href="/portfolio" className="hover:text-gray-400">Portefeuille</Link>
        <span>/</span>
        <Link href={`/ticker/${ticker_id}`} className="hover:text-gray-400">{ticker_id}</Link>
        <span>/</span>
        <span className="text-gray-400">Débat de conviction</span>
      </div>

      <h1 className="text-xl font-bold text-white">Débat de conviction — {ticker_id}</h1>

      {error && <div className="bg-red-900/30 border border-red-700 text-red-300 rounded-lg px-4 py-3 text-sm">{error}</div>}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4" style={{ minHeight: '60vh' }}>
        {/* Col 1 — Chat */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl flex flex-col" style={{ minHeight: '500px' }}>
          <div className="px-4 py-3 border-b border-gray-800">
            <h2 className="font-semibold text-white text-sm">Débat — Mode conviction challenge</h2>
          </div>
          <div className="flex-1 min-h-0">
            <AgentChat
              messages={messages}
              onSend={sendMessage}
              isLoading={isLoading}
              placeholder="Vos arguments pour maintenir la position…"
            />
          </div>
        </div>

        {/* Col 2 — Agent position */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 flex flex-col gap-4">
          <h2 className="font-semibold text-white">Position courante de l&apos;agent</h2>

          <div className={`border rounded-xl px-6 py-5 text-center ${posStyle.cls}`}>
            <p className="text-4xl mb-2">
              {agentPosition === 'PASS' ? '🔴' : agentPosition === 'MONITOR' ? '🟡' : '🟢'}
            </p>
            <p className="text-xl font-bold">{posStyle.label}</p>
          </div>

          <p className="text-sm text-gray-500 text-center">
            La position se met à jour après chaque échange
          </p>
        </div>
      </div>

      {/* Bottom — Clôture */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h3 className="font-semibold text-white mb-4">Clôturer le débat</h3>

        {agentPosition === 'PASS' && (
          <div className="flex flex-wrap gap-3">
            <button onClick={() => handleClose('maintain_override')} disabled={actionLoading}
              className="px-4 py-2 bg-yellow-700 hover:bg-yellow-600 disabled:opacity-50 text-white text-sm rounded-lg font-medium transition-colors">
              Maintenir malgré PASS
            </button>
            <button onClick={() => handleClose('reduce')} disabled={actionLoading}
              className="px-4 py-2 bg-orange-700 hover:bg-orange-600 disabled:opacity-50 text-white text-sm rounded-lg font-medium transition-colors">
              Réduire
            </button>
            <button onClick={() => handleClose('close_position')} disabled={actionLoading}
              className="px-4 py-2 bg-red-700 hover:bg-red-600 disabled:opacity-50 text-white text-sm rounded-lg font-medium transition-colors">
              Clôturer
            </button>
          </div>
        )}

        {agentPosition === 'MONITOR' && (
          <div className="flex flex-wrap gap-3">
            <button onClick={() => handleClose('back_monitor')} disabled={actionLoading}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-gray-200 text-sm rounded-lg font-medium transition-colors">
              Retour à la fiche ticker
            </button>
          </div>
        )}

        {agentPosition === 'PROCEED' && (
          <div className="flex flex-wrap gap-3">
            <button onClick={() => handleClose('new_thesis')} disabled={actionLoading}
              className="px-4 py-2 bg-emerald-700 hover:bg-emerald-600 disabled:opacity-50 text-white text-sm rounded-lg font-medium transition-colors">
              Construire nouvelle thèse →
            </button>
            <button onClick={() => handleClose('back_no_thesis')} disabled={actionLoading}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-gray-200 text-sm rounded-lg font-medium transition-colors">
              Retour sans nouvelle thèse
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

