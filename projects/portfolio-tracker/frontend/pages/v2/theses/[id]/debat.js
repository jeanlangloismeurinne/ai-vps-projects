import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/router'
import {
  Card, CardHeader, CardBody,
  Badge, KeyValue, Section, Dl,
  EmptyState, ErrorState,
} from '../../../../components/v2'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

// ── Utilitaires ───────────────────────────────────────────────────────────────

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' })
}

function fmtDatetime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('fr-FR', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function fmtPct(val) {
  if (val == null) return '—'
  return `${Number(val).toFixed(1)} %`
}

function fmtCost(val) {
  if (val == null) return '—'
  return `${Number(val).toFixed(4)} $`
}

// ── Statuts de débat ──────────────────────────────────────────────────────────
const DEBATE_STATUS_VARIANT = {
  open:            'amber',
  closed_pass:     'gray',
  closed_monitor:  'sky',
  closed_proceed:  'emerald',
}
const DEBATE_STATUS_LABEL = {
  open:            'Ouvert',
  closed_pass:     'Clos — sortie',
  closed_monitor:  'Clos — surveillance',
  closed_proceed:  'Clos — maintien',
}

// ── Valeur de seuil_franchi (chaîne, jamais booléen) ─────────────────────────
function SeuilFranchi({ valeur }) {
  // valeur est une CHAÎNE : "invalidation" | "alerte" | "aucun"
  // Ne jamais traiter comme un booléen
  if (valeur === 'invalidation') {
    return <Badge variant="red">Invalidation franchie</Badge>
  }
  if (valeur === 'alerte') {
    return <Badge variant="amber">Alerte franchie</Badge>
  }
  if (valeur === 'aucun') {
    return <Badge variant="gray">Aucun seuil franchi</Badge>
  }
  return <span className="text-amber-600 italic">— valeur inattendue : {String(valeur)}</span>
}

// ── Bloc : hypothèse sous tension ────────────────────────────────────────────
function HypotheseSousTension({ h }) {
  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900/30 p-4 space-y-3">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs font-mono text-gray-400">{h.hypothese_id ?? '— champ absent'}</span>
        <SeuilFranchi valeur={h.seuil_franchi} />
      </div>
      <Dl cols={3}>
        <KeyValue
          label="Valeur observée"
          value={h.valeur_observee != null ? h.valeur_observee : <span className="text-amber-600 italic">— champ absent</span>}
        />
        <KeyValue
          label="Seuil d'alerte"
          locked
          value={h.seuil_alerte != null ? h.seuil_alerte : <span className="text-amber-600 italic">— champ absent</span>}
        />
        <KeyValue
          label="Seuil d'invalidation"
          locked
          value={h.seuil_invalidation != null ? h.seuil_invalidation : <span className="text-amber-600 italic">— champ absent</span>}
        />
      </Dl>
      {h.observation != null && (
        <p className="text-xs text-gray-400">{h.observation}</p>
      )}
      {Array.isArray(h.source_entry_refs) && h.source_entry_refs.length > 0 && (
        <div>
          <div className="text-[10px] text-gray-600 uppercase tracking-wide mb-1">Sources</div>
          <div className="flex flex-wrap gap-1">
            {h.source_entry_refs.map((ref, i) => (
              <span key={i} className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-400 border border-gray-700">
                #{ref.entry_id}{ref.version != null ? ` v${ref.version}` : ''}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Bloc : cas contre maintien ────────────────────────────────────────────────
function CasContreMaintien({ cas }) {
  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900/30 p-4 space-y-3">
      <p className="text-sm font-medium text-gray-200">
        {cas.titre != null ? cas.titre : <span className="text-amber-600 italic">— champ absent</span>}
      </p>
      {cas.explication != null && (
        <p className="text-xs text-gray-400">{cas.explication}</p>
      )}
      <Dl cols={2}>
        <KeyValue
          label="Probabilité"
          value={cas.probabilite != null ? fmtPct(cas.probabilite * 100) : <span className="text-amber-600 italic">— champ absent</span>}
        />
      </Dl>
      {/* Base rate — objet imbriqué */}
      <div className="text-xs text-gray-500 space-y-0.5 border border-gray-800 rounded-md px-3 py-2">
        <div className="text-[10px] text-gray-600 uppercase tracking-wide mb-1.5">Base rate · figé</div>
        {cas.base_rate != null ? (
          <>
            <div>
              Taux :{' '}
              {cas.base_rate.taux != null
                ? <span className="text-gray-300">{fmtPct(cas.base_rate.taux * 100)}</span>
                : <span className="text-amber-600 italic">— champ absent</span>}
            </div>
            <div>
              Classe de référence :{' '}
              {cas.base_rate.reference_class != null && cas.base_rate.reference_class !== ''
                ? <span className="text-gray-300">{cas.base_rate.reference_class}</span>
                : <span className="text-amber-600 italic">— champ absent</span>}
            </div>
            <div>
              Ajustement :{' '}
              {cas.base_rate.ajustement != null
                ? <span className="text-gray-300">{cas.base_rate.ajustement}</span>
                : <span className="text-gray-600 italic">aucun ajustement (null volontaire)</span>}
            </div>
          </>
        ) : (
          <span className="text-amber-600 italic">— objet base_rate absent</span>
        )}
      </div>
      {Array.isArray(cas.source_entry_refs) && cas.source_entry_refs.length > 0 && (
        <div>
          <div className="text-[10px] text-gray-600 uppercase tracking-wide mb-1">Sources</div>
          <div className="flex flex-wrap gap-1">
            {cas.source_entry_refs.map((ref, i) => (
              <span key={i} className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-400 border border-gray-700">
                #{ref.entry_id}{ref.version != null ? ` v${ref.version}` : ''}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Bloc : bandeau divergence agent / investisseur ───────────────────────────
// Arbitrage 4 : visible SANS clic — bandeau ambre si divergence, sobre si coïncidence
function DivergenceBandeau({ debate }) {
  const status = debate.status
  const suggeree = debate.resolution_suggeree
  const closedStatuses = ['closed_pass', 'closed_monitor', 'closed_proceed']

  if (!closedStatuses.includes(status)) return null

  const diverge = status !== suggeree

  if (diverge) {
    return (
      <div className="rounded-xl border border-amber-700/50 bg-amber-950/20 px-4 py-4 space-y-3">
        <div className="flex items-center gap-2">
          <span className="text-amber-400 text-base">⚠</span>
          <p className="text-sm font-semibold text-amber-300">Divergence agent / investisseur</p>
        </div>
        <div className="flex items-center gap-4 flex-wrap">
          <div>
            <div className="text-[10px] text-amber-700 uppercase tracking-wide mb-1">L'agent suggérait</div>
            <Badge variant="amber">{DEBATE_STATUS_LABEL[suggeree] || suggeree}</Badge>
          </div>
          <div className="text-amber-800 text-lg">→</div>
          <div>
            <div className="text-[10px] text-amber-700 uppercase tracking-wide mb-1">L'investisseur a clôturé</div>
            <Badge variant={DEBATE_STATUS_VARIANT[status] || 'gray'}>{DEBATE_STATUS_LABEL[status] || status}</Badge>
          </div>
        </div>
        {debate.closure_note != null && debate.closure_note !== '' && (
          <div className="border-t border-amber-800/40 pt-3">
            <div className="text-[10px] text-amber-700 uppercase tracking-wide mb-1">Note de clôture</div>
            <p className="text-xs text-amber-200/80 italic">{debate.closure_note}</p>
          </div>
        )}
        <p className="text-xs text-amber-600/80 border-t border-amber-800/30 pt-2">
          La clôture est l'acte souverain de l'investisseur. Cette divergence est conservée en ligne
          telle quelle — elle constitue la matière du post-mortem.
        </p>
      </div>
    )
  }

  // Coïncidence : sobre
  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900/30 px-4 py-3 flex items-center gap-2">
      <span className="text-emerald-500 text-sm">✓</span>
      <p className="text-xs text-gray-400">
        L'investisseur a clôturé sur{' '}
        <span className="text-gray-200">{DEBATE_STATUS_LABEL[status] || status}</span>,
        en accord avec la résolution suggérée par l'agent.
      </p>
    </div>
  )
}

// ── Bloc : garde-fou anti-complaisance ────────────────────────────────────────
function GardeFouBlock({ debate }) {
  const invalidationFranchie = debate.invalidation_franchie
  const resolutionSuggeree = debate.resolution_suggeree

  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900/30 px-4 py-4 space-y-2">
      <h4 className="text-xs font-semibold text-gray-300 uppercase tracking-wide">
        Garde-fou anti-complaisance
      </h4>
      <div className="flex items-center gap-4 flex-wrap">
        <div>
          <div className="text-[10px] text-gray-600 uppercase tracking-wide mb-1">Invalidation franchie</div>
          {invalidationFranchie === true ? (
            <Badge variant="red">Oui — seuil d'invalidation franchi</Badge>
          ) : invalidationFranchie === false ? (
            <Badge variant="gray">Non</Badge>
          ) : (
            <span className="text-amber-600 italic text-xs">— champ absent</span>
          )}
        </div>
        <div>
          <div className="text-[10px] text-gray-600 uppercase tracking-wide mb-1">Résolution suggérée</div>
          <Badge variant={DEBATE_STATUS_VARIANT[resolutionSuggeree] || 'gray'}>
            {DEBATE_STATUS_LABEL[resolutionSuggeree] || resolutionSuggeree || '—'}
          </Badge>
        </div>
      </div>
      <p className="text-xs text-gray-500 border-t border-gray-800 pt-2">
        Contrainte système : quand une invalidation est franchie, l'agent ne{' '}
        <span className="font-medium text-gray-400">peut pas</span> suggérer{' '}
        <code className="text-[10px] bg-gray-800 px-1 rounded">closed_proceed</code>.
        Ce CHECK est vérifié en base de données à chaque écriture.
        {invalidationFranchie === true && resolutionSuggeree !== 'closed_proceed' && (
          <span className="text-emerald-500 ml-1">
            ✓ La contrainte s'est exercée ici : l'invalidation franchie a exclu{' '}
            <code className="text-[10px] bg-gray-800 px-1 rounded">closed_proceed</code>.
          </span>
        )}
      </p>
    </div>
  )
}

// ── Bloc : knowledge_refs ─────────────────────────────────────────────────────
function KnowledgeRefs({ refs }) {
  if (!Array.isArray(refs) || refs.length === 0) return null
  return (
    <Section title={`Knowledge refs (${refs.length}) — snapshot figé`}>
      <p className="text-xs text-gray-600 bg-gray-900/50 border border-gray-800 rounded-lg px-3 py-2">
        Ce snapshot des entrées de connaissance utilisées est figé au moment du débat.
        Il rend le débat auditable : la connaissance disponible à l'instant T est conservée telle quelle,
        indépendamment des versions ultérieures.
      </p>
      <div className="space-y-2">
        {refs.map((ref, i) => (
          <div key={i} className="rounded-lg border border-gray-800 bg-gray-900/30 p-3 space-y-2">
            <Dl cols={4}>
              <KeyValue label="Entry ID" value={ref.entry_id != null ? `#${ref.entry_id}` : <span className="text-amber-600 italic">— champ absent</span>} />
              <KeyValue label="Version" value={ref.entry_version != null ? `v${ref.entry_version}` : <span className="text-amber-600 italic">— champ absent</span>} />
              <KeyValue label="Fiabilité à l'usage" value={ref.reliability_at_use != null ? ref.reliability_at_use.toFixed(2) : <span className="text-amber-600 italic">— champ absent</span>} />
              <KeyValue label="Champ couvert" value={ref.field_path != null ? ref.field_path : <span className="text-gray-600 italic">null — non renseigné</span>} />
            </Dl>
            {ref.content_snapshot != null && (
              <details className="mt-1">
                <summary className="text-[10px] text-gray-500 cursor-pointer hover:text-gray-300 select-none">
                  Contenu du snapshot (cliquer pour déplier)
                </summary>
                <pre className="mt-2 text-[10px] text-gray-400 whitespace-pre-wrap break-words font-mono bg-gray-900 border border-gray-800 rounded p-2 max-h-64 overflow-y-auto">
                  {ref.content_snapshot}
                </pre>
              </details>
            )}
          </div>
        ))}
      </div>
    </Section>
  )
}

// ── Bloc : détail d'un débat sélectionné ─────────────────────────────────────
function DebateDetail({ debate, onClose, onCloseDebate, thesisId }) {
  const [closeResolution, setCloseResolution] = useState('closed_pass')
  const [closeNote, setCloseNote] = useState('')
  const [closing, setClosing] = useState(false)
  const [closeErr, setCloseErr] = useState(null)

  const cj = debate.challenge_json || {}
  const isOpen = debate.status === 'open'

  async function handleClose() {
    const isDivergent = closeResolution !== debate.resolution_suggeree
    if (isDivergent) {
      const confirmed = window.confirm(
        `Vous choisissez "${DEBATE_STATUS_LABEL[closeResolution] || closeResolution}", ` +
        `alors que l'agent suggérait "${DEBATE_STATUS_LABEL[debate.resolution_suggeree] || debate.resolution_suggeree}".\n\n` +
        `Cette divergence est légitime et sera conservée en ligne comme matière du post-mortem. Confirmer ?`
      )
      if (!confirmed) return
    } else {
      const confirmed = window.confirm(`Clôturer ce débat avec la résolution "${DEBATE_STATUS_LABEL[closeResolution] || closeResolution}" ?`)
      if (!confirmed) return
    }

    setClosing(true)
    setCloseErr(null)
    try {
      const res = await fetch(`${API}/v2/debates/${debate.id}/close`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resolution: closeResolution, note: closeNote }),
      })
      if (!res.ok) {
        const d = await res.json().catch(() => ({}))
        throw new Error(d.detail || `Erreur ${res.status}`)
      }
      onCloseDebate()
    } catch (e) {
      setCloseErr(String(e))
    } finally {
      setClosing(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Bouton retour à la liste */}
      <button
        onClick={onClose}
        className="text-xs text-gray-500 hover:text-gray-300 flex items-center gap-1"
      >
        ← Retour à la liste des débats
      </button>

      {/* En-tête du débat */}
      <Card>
        <CardHeader
          title={`Débat #${debate.id}`}
          subtitle={fmtDatetime(debate.created_at)}
          action={
            <Badge variant={DEBATE_STATUS_VARIANT[debate.status] || 'gray'}>
              {DEBATE_STATUS_LABEL[debate.status] || debate.status}
            </Badge>
          }
        />
        <CardBody className="space-y-4">
          <Dl cols={3}>
            <KeyValue label="ID" value={debate.id != null ? `#${debate.id}` : '—'} />
            <KeyValue label="Créé le" value={fmtDatetime(debate.created_at)} />
            <KeyValue label="Statut" value={DEBATE_STATUS_LABEL[debate.status] || debate.status || '—'} />
            <KeyValue
              label="Session de suivi déclenchante"
              value={debate.monitoring_session_v2_id != null
                ? `Session #${debate.monitoring_session_v2_id}`
                : <span className="text-gray-600 italic">déclenché manuellement</span>}
            />
            <KeyValue label="Modèle" value={debate.model_used ?? '—'} />
            <KeyValue label="Tokens in" value={debate.tokens_in != null ? debate.tokens_in.toLocaleString('fr-FR') : '—'} />
            <KeyValue label="Tokens out" value={debate.tokens_out != null ? debate.tokens_out.toLocaleString('fr-FR') : '—'} />
            <KeyValue label="Coût" value={fmtCost(debate.cost_usd)} />
            {debate.closed_at && (
              <KeyValue label="Clôturé le" value={fmtDatetime(debate.closed_at)} />
            )}
          </Dl>
        </CardBody>
      </Card>

      {/* Garde-fou anti-complaisance */}
      <GardeFouBlock debate={debate} />

      {/* Divergence agent / investisseur (arbitrage 4) */}
      <DivergenceBandeau debate={debate} />

      {/* challenge_json — corps du débat */}
      {cj && (
        <Section title="Corps du débat (challenge_json)">

          {/* Hypothèses sous tension */}
          {Array.isArray(cj.hypotheses_sous_tension) && cj.hypotheses_sous_tension.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
                Hypothèses sous tension ({cj.hypotheses_sous_tension.length})
              </h4>
              <p className="text-xs text-gray-600 bg-gray-900/50 border border-gray-800 rounded-lg px-3 py-2">
                Les seuils (<code className="text-[10px]">seuil_alerte</code>,{' '}
                <code className="text-[10px]">seuil_invalidation</code>) sont{' '}
                <strong className="text-gray-400">figés au validate</strong> et ne peuvent pas être
                modifiés par l'agent. Le champ{' '}
                <code className="text-[10px]">seuil_franchi</code> est une chaîne (
                <code className="text-[10px]">"invalidation"</code> /{' '}
                <code className="text-[10px]">"alerte"</code> /{' '}
                <code className="text-[10px]">"aucun"</code>) —{' '}
                <strong className="text-gray-400">redérivée par le système</strong> depuis{' '}
                <code className="text-[10px]">valeur_observee</code>, jamais reprise de la déclaration du modèle.
              </p>
              {cj.hypotheses_sous_tension.map((h, i) => (
                <HypotheseSousTension key={h.hypothese_id || i} h={h} />
              ))}
            </div>
          )}

          {/* Cas contre maintien */}
          {Array.isArray(cj.cas_contre_maintien) && cj.cas_contre_maintien.length > 0 && (
            <div className="space-y-3 mt-4">
              <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
                Cas contre le maintien ({cj.cas_contre_maintien.length})
              </h4>
              {cj.cas_contre_maintien.map((cas, i) => (
                <CasContreMaintien key={i} cas={cas} />
              ))}
            </div>
          )}

          {/* Biais à surveiller */}
          {Array.isArray(cj.biais_a_surveiller) && cj.biais_a_surveiller.length > 0 && (
            <div className="mt-4 space-y-2">
              <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
                Biais à surveiller
              </h4>
              <div className="flex flex-wrap gap-2">
                {cj.biais_a_surveiller.map((b, i) => (
                  <span key={i} className="font-mono text-xs px-2 py-0.5 rounded bg-amber-950/30 text-amber-400 border border-amber-800/40">
                    {b}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Coût d'opportunité */}
          {cj.cout_opportunite != null && (
            <div className="mt-4 space-y-1">
              <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Coût d'opportunité</h4>
              <p className="text-sm text-gray-300">{cj.cout_opportunite}</p>
            </div>
          )}

          {/* Résolution rationale */}
          {cj.resolution_rationale != null && (
            <div className="mt-4 space-y-1">
              <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Raisonnement de résolution</h4>
              <p className="text-sm text-gray-300">{cj.resolution_rationale}</p>
            </div>
          )}
        </Section>
      )}

      {/* Knowledge refs (détail seulement) */}
      {Array.isArray(debate.knowledge_refs) && (
        <KnowledgeRefs refs={debate.knowledge_refs} />
      )}

      {/* Blocs audit repliables */}
      <Section title="Audit — données brutes">
        <div className="space-y-3">
          {debate.context_sent != null && (
            <details className="rounded-lg border border-gray-800 overflow-hidden">
              <summary className="px-4 py-3 text-xs text-gray-400 cursor-pointer hover:text-gray-200 select-none bg-gray-900/50">
                context_sent — contexte envoyé au modèle
              </summary>
              <pre className="px-4 py-3 text-[10px] text-gray-500 whitespace-pre-wrap break-words font-mono bg-black/20 max-h-96 overflow-y-auto">
                {debate.context_sent}
              </pre>
            </details>
          )}
          {debate.raw_content != null && (
            <details className="rounded-lg border border-gray-800 overflow-hidden">
              <summary className="px-4 py-3 text-xs text-gray-400 cursor-pointer hover:text-gray-200 select-none bg-gray-900/50">
                raw_content — sortie brute du modèle
              </summary>
              <pre className="px-4 py-3 text-[10px] text-gray-500 whitespace-pre-wrap break-words font-mono bg-black/20 max-h-96 overflow-y-auto">
                {debate.raw_content}
              </pre>
            </details>
          )}
          {debate.prompt_snapshot != null && (
            <details className="rounded-lg border border-gray-800 overflow-hidden">
              <summary className="px-4 py-3 text-xs text-gray-400 cursor-pointer hover:text-gray-200 select-none bg-gray-900/50">
                prompt_snapshot — prompt système utilisé
              </summary>
              <pre className="px-4 py-3 text-[10px] text-gray-500 whitespace-pre-wrap break-words font-mono bg-black/20 max-h-96 overflow-y-auto">
                {debate.prompt_snapshot}
              </pre>
            </details>
          )}
        </div>
      </Section>

      {/* Clôture du débat (si ouvert) */}
      {isOpen && (
        <Card>
          <CardHeader title="Clôturer ce débat" subtitle="Aucun appel modèle — votre décision souveraine" />
          <CardBody className="space-y-4">
            <div className="space-y-2">
              <label className="text-xs text-gray-400">Résolution</label>
              <div className="flex gap-2 flex-wrap">
                {[
                  { value: 'closed_pass', label: 'Sortie / abandon' },
                  { value: 'closed_monitor', label: 'Maintien sous surveillance' },
                  { value: 'closed_proceed', label: 'Maintien confiant' },
                ].map(opt => (
                  <button
                    key={opt.value}
                    onClick={() => setCloseResolution(opt.value)}
                    className={`px-3 py-1.5 rounded-lg text-xs border transition-colors ${
                      closeResolution === opt.value
                        ? 'border-emerald-600 bg-emerald-900/30 text-emerald-300'
                        : 'border-gray-700 bg-gray-900/30 text-gray-400 hover:border-gray-600'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
              {debate.resolution_suggeree && closeResolution !== debate.resolution_suggeree && (
                <p className="text-xs text-amber-500">
                  Vous divergez de la résolution suggérée par l'agent (
                  {DEBATE_STATUS_LABEL[debate.resolution_suggeree] || debate.resolution_suggeree}).
                  Cette divergence est légitime et sera conservée en ligne.
                </p>
              )}
            </div>
            <div className="space-y-1">
              <label className="text-xs text-gray-400">Note de clôture (optionnelle)</label>
              <textarea
                value={closeNote}
                onChange={e => setCloseNote(e.target.value)}
                rows={3}
                placeholder="Motif de la décision, contexte particulier…"
                className="w-full rounded-lg border border-gray-700 bg-gray-900 text-sm text-gray-200 px-3 py-2 placeholder-gray-600 focus:outline-none focus:border-emerald-600 resize-none"
              />
            </div>
            {closeErr && (
              <ErrorState detail={closeErr} />
            )}
            <button
              onClick={handleClose}
              disabled={closing}
              className="px-4 py-2 rounded-lg bg-emerald-700 hover:bg-emerald-600 disabled:opacity-50 text-sm text-white font-medium transition-colors"
            >
              {closing ? 'Clôture en cours…' : 'Confirmer la clôture'}
            </button>
          </CardBody>
        </Card>
      )}
    </div>
  )
}

// ── Formulaire : lancer un débat ─────────────────────────────────────────────
function LancerDebatForm({ thesisId, onSuccess }) {
  const [motif, setMotif] = useState('')
  const [sessionId, setSessionId] = useState('')
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState(null)

  async function handleSubmit() {
    const confirmed = window.confirm(
      'Lancer un débat de conviction est un appel modèle facturé. Confirmer ?'
    )
    if (!confirmed) return

    setLoading(true)
    setErr(null)
    try {
      const body = { motif }
      if (sessionId.trim() !== '') {
        const parsed = parseInt(sessionId, 10)
        if (!isNaN(parsed)) body.monitoring_session_v2_id = parsed
      }
      const res = await fetch(`${API}/v2/theses/${thesisId}/debate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const d = await res.json().catch(() => ({}))
        throw new Error(d.detail || `Erreur ${res.status}`)
      }
      onSuccess()
    } catch (e) {
      setErr(String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card>
      <CardHeader
        title="Lancer un débat"
        subtitle="⚠ Appel modèle facturé"
      />
      <CardBody className="space-y-4">
        <div className="space-y-1">
          <label className="text-xs text-gray-400">Motif du débat</label>
          <textarea
            value={motif}
            onChange={e => setMotif(e.target.value)}
            rows={3}
            placeholder="Décrivez le contexte ou la question qui motive ce débat…"
            className="w-full rounded-lg border border-gray-700 bg-gray-900 text-sm text-gray-200 px-3 py-2 placeholder-gray-600 focus:outline-none focus:border-emerald-600 resize-none"
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs text-gray-400">ID session de suivi déclenchante (optionnel)</label>
          <input
            type="number"
            value={sessionId}
            onChange={e => setSessionId(e.target.value)}
            placeholder="ex: 11"
            className="w-full rounded-lg border border-gray-700 bg-gray-900 text-sm text-gray-200 px-3 py-2 placeholder-gray-600 focus:outline-none focus:border-emerald-600"
          />
        </div>
        <p className="text-xs text-gray-600">
          La résolution suggérée et les seuils sont produits sous contrainte par l'agent et relus
          depuis la thèse figée — ils ne sont pas saisissables.
        </p>
        {err && <ErrorState detail={err} />}
        <button
          onClick={handleSubmit}
          disabled={loading || !motif.trim()}
          className="px-4 py-2 rounded-lg bg-emerald-700 hover:bg-emerald-600 disabled:opacity-50 text-sm text-white font-medium transition-colors"
        >
          {loading ? 'Lancement en cours…' : 'Lancer un débat (appel modèle facturé)'}
        </button>
      </CardBody>
    </Card>
  )
}

// ── Page principale ───────────────────────────────────────────────────────────
export default function DebatPage() {
  const router = useRouter()
  const { id } = router.query

  // Données thèse (ticker, statut)
  const [thesis, setThesis] = useState(null)
  const [thesisErr, setThesisErr] = useState(null)
  const [thesisLoading, setThesisLoading] = useState(true)

  // Liste des débats
  const [debates, setDebates] = useState(null)
  const [debatesErr, setDebatesErr] = useState(null)
  const [debatesLoading, setDebatesLoading] = useState(true)

  // Débat sélectionné (détail)
  const [selectedDebate, setSelectedDebate] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailErr, setDetailErr] = useState(null)

  // Affichage formulaire
  const [showForm, setShowForm] = useState(false)

  function loadThesis() {
    if (!id) return
    setThesisLoading(true)
    fetch(`${API}/v2/theses/${id}`)
      .then(r => r.ok ? r.json() : r.json().then(d => Promise.reject(d.detail || `Erreur ${r.status}`)))
      .then(d => { setThesis(d); setThesisLoading(false) })
      .catch(e => { setThesisErr(String(e)); setThesisLoading(false) })
  }

  function loadDebates() {
    if (!id) return
    setDebatesLoading(true)
    fetch(`${API}/v2/theses/${id}/debate`)
      .then(r => {
        if (r.status === 404) return []
        if (!r.ok) return r.json().then(d => Promise.reject(d.detail || `Erreur ${r.status}`))
        return r.json()
      })
      .then(d => { setDebates(Array.isArray(d) ? d : []); setDebatesLoading(false) })
      .catch(e => { setDebatesErr(String(e)); setDebatesLoading(false) })
  }

  useEffect(() => {
    loadThesis()
    loadDebates()
  }, [id])

  async function loadDebateDetail(debate) {
    setDetailLoading(true)
    setDetailErr(null)
    setSelectedDebate(null)
    try {
      const res = await fetch(`${API}/v2/debates/${debate.id}`)
      if (!res.ok) {
        const d = await res.json().catch(() => ({}))
        throw new Error(d.detail || `Erreur ${res.status}`)
      }
      const data = await res.json()
      setSelectedDebate(data)
    } catch (e) {
      setDetailErr(String(e))
    } finally {
      setDetailLoading(false)
    }
  }

  function handleCloseDebate() {
    // Recharge la liste et revient à la vue liste
    loadDebates()
    setSelectedDebate(null)
  }

  // ── Rendu ─────────────────────────────────────────────────────────────────
  const titre = thesis
    ? (thesis.ticker_symbol || thesis.ticker_id || `Thèse #${id}`)
    : `Thèse #${id}`

  return (
    <div className="space-y-6">
      {/* Fil d'Ariane */}
      <div className="flex items-center gap-2 text-xs text-gray-500 flex-wrap">
        <Link href="/v2/theses" className="hover:text-gray-300">Thèses V2</Link>
        <span>›</span>
        <Link href={`/v2/theses/${id}`} className="hover:text-gray-300">{titre}</Link>
        <span>›</span>
        <span className="text-gray-300">Débat de conviction</span>
      </div>

      {/* Titre */}
      <div className="flex items-center gap-3 flex-wrap">
        <h1 className="text-2xl font-bold text-white">{titre}</h1>
        <span className="text-gray-600">›</span>
        <span className="text-lg font-semibold text-gray-300">Débat de conviction</span>
        {thesis && (
          <Badge variant={thesis.status === 'active' ? 'active' : 'gray'}>
            {thesis.status || '—'}
          </Badge>
        )}
      </div>

      {thesisErr && <ErrorState detail={thesisErr} />}

      {/* Vue détail d'un débat */}
      {selectedDebate && (
        <DebateDetail
          debate={selectedDebate}
          onClose={() => setSelectedDebate(null)}
          onCloseDebate={handleCloseDebate}
          thesisId={id}
        />
      )}

      {/* Vue liste + formulaire */}
      {!selectedDebate && (
        <>
          {/* Erreur chargement détail */}
          {detailLoading && (
            <div className="py-6 text-center text-sm text-gray-500">Chargement du débat…</div>
          )}
          {detailErr && <ErrorState detail={detailErr} />}

          {/* Liste des débats */}
          {debatesLoading && (
            <div className="py-6 text-center text-sm text-gray-500">Chargement…</div>
          )}
          {debatesErr && <ErrorState detail={debatesErr} />}

          {!debatesLoading && !debatesErr && debates && debates.length === 0 && (
            <EmptyState
              title="Aucun débat de conviction"
              description="Un débat soumet la conviction de MAINTIEN au test le plus dur : l'agent y joue l'avocat du diable. Il se déclenche depuis une revue de suivi (monitoring mode 2/3/6) ou manuellement."
            />
          )}

          {!debatesLoading && !debatesErr && debates && debates.length > 0 && (
            <Section title={`Débats (${debates.length}) — du plus récent au plus ancien`}>
              <div className="space-y-3">
                {debates.map(debate => (
                  <button
                    key={debate.id}
                    onClick={() => loadDebateDetail(debate)}
                    className="w-full text-left rounded-xl border border-gray-800 bg-gray-900/50 hover:border-gray-700 transition-colors overflow-hidden"
                  >
                    <div className="px-4 py-3 space-y-2">
                      <div className="flex items-center gap-3 flex-wrap">
                        <span className="text-xs font-mono text-gray-400">#{debate.id}</span>
                        <Badge variant={DEBATE_STATUS_VARIANT[debate.status] || 'gray'}>
                          {DEBATE_STATUS_LABEL[debate.status] || debate.status}
                        </Badge>
                        {debate.invalidation_franchie === true && (
                          <Badge variant="red">Invalidation franchie</Badge>
                        )}
                        {debate.resolution_suggeree && debate.status !== 'open' && debate.status !== debate.resolution_suggeree && (
                          <Badge variant="amber">Divergence</Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-4 flex-wrap text-xs text-gray-500">
                        <span>{fmtDatetime(debate.created_at)}</span>
                        {debate.monitoring_session_v2_id != null && (
                          <span>Session #{debate.monitoring_session_v2_id}</span>
                        )}
                        {debate.model_used && (
                          <span className="font-mono">{debate.model_used}</span>
                        )}
                        {debate.cost_usd != null && (
                          <span>{fmtCost(debate.cost_usd)}</span>
                        )}
                      </div>
                      {debate.resolution_suggeree && (
                        <div className="text-xs text-gray-600">
                          Résolution suggérée : {DEBATE_STATUS_LABEL[debate.resolution_suggeree] || debate.resolution_suggeree}
                        </div>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            </Section>
          )}

          {/* Formulaire lancer un débat */}
          {!showForm ? (
            <button
              onClick={() => setShowForm(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-700 bg-gray-900/50 hover:border-emerald-700 text-sm text-gray-300 transition-colors"
            >
              <span className="text-emerald-500">+</span>
              Lancer un débat (appel modèle facturé)
            </button>
          ) : (
            <>
              <LancerDebatForm
                thesisId={id}
                onSuccess={() => {
                  setShowForm(false)
                  loadDebates()
                }}
              />
              <button
                onClick={() => setShowForm(false)}
                className="text-xs text-gray-600 hover:text-gray-400"
              >
                Annuler
              </button>
            </>
          )}
        </>
      )}
    </div>
  )
}
