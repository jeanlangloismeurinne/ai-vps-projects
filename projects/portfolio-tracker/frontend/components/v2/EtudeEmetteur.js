// La société mise à l'étude, sur la page de l'émetteur (M2 B12, M3 K12) : le bouton « mettre à
// l'étude », l'état du dossier et le geste qui vous revient, ce que la collecte a trouvé ou pas, les
// documents lus et les pièces. Tout vient de GET /v2/emetteurs/{e}/etude ; les gestes ne lancent
// rien : la tâche de fond fait avancer le dossier à son passage suivant.
import { Fragment, useState, useEffect, useCallback } from 'react'
import { Card, CardHeader, CardBody, Badge, KeyValue, Dl, EmptyState, MotifLigne } from './index'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

const INPUT = 'w-full rounded-lg bg-gray-950 border border-gray-700 px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-emerald-600'
const BTN = 'px-3 py-1.5 text-xs font-semibold rounded-lg bg-emerald-700 hover:bg-emerald-600 text-white disabled:opacity-50'
const LIEN = 'text-xs text-sky-400 hover:text-sky-300'

// Les pas du dossier, dits comme on les dit dans un fonds (affichage seulement).
const PAS = {
  fiche_emetteur: "fiche de l'émetteur",
  collecte: 'collecte des documents',
  evaluation_des_sources: 'évaluation des sources rencontrées',
  lecture: 'mise en lecture',
}
const pas = p => PAS[p] || p
const usd = v => `${Number(v || 0).toFixed(2)} $`

function detailDe(data, code) {
  const d = data && data.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d)) return d.map(x => x.msg).join(' ; ')
  return `Refusé (code ${code}).`
}

function Titre({ children }) {
  return <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">{children}</h2>
}

function Tableau({ entetes, children }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-gray-800">
      <table className="w-full text-xs">
        <thead className="bg-gray-900 text-gray-400">
          <tr>{entetes.map(h => <th key={h} className="py-2 px-3 text-left font-medium">{h}</th>)}</tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  )
}

function Adresse({ url }) {
  if (!url) return <span className="text-gray-500">—</span>
  const href = /^https?:\/\//.test(url) ? url : `https://${url}`
  return <a href={href} target="_blank" rel="noreferrer" className="font-mono text-sky-400 hover:text-sky-300 break-all">{url}</a>
}

// ── Mettre à l'étude ─────────────────────────────────────────────────────────────────────────

function MettreALEtude({ emetteur, onFait }) {
  const [motif, setMotif] = useState('')
  const [err, setErr] = useState(null)
  const [busy, setBusy] = useState(false)

  async function soumettre(e) {
    e.preventDefault()
    setBusy(true); setErr(null)
    try {
      const r = await fetch(`${API}/v2/emetteurs/${encodeURIComponent(emetteur)}/etude`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ motif }),
      })
      const data = await r.json().catch(() => ({}))
      if (!r.ok) { setErr(detailDe(data, r.status)); return }
      onFait()
    } catch (_) {
      setErr('Le serveur ne répond pas.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card>
      <CardHeader title="Cette société n'est pas à l'étude"
        subtitle="La mettre à l'étude ouvre son dossier : le système collecte ses derniers comptes, les met en lecture, et revient vers vous pour valider ce qu'il a trouvé." />
      <CardBody>
        <form onSubmit={soumettre} className="flex flex-col sm:flex-row gap-3 sm:items-end">
          <label className="block space-y-1 flex-1">
            <span className="text-xs text-gray-400">Pourquoi l&apos;étudier (obligatoire)</span>
            <input className={INPUT} value={motif} onChange={e => setMotif(e.target.value)} required />
          </label>
          <button type="submit" className={BTN} disabled={busy}>Mettre à l&apos;étude</button>
        </form>
        {err && <p className="text-xs text-red-400 mt-2">{err}</p>}
      </CardBody>
    </Card>
  )
}

// ── Le dossier et le geste qui vous revient ──────────────────────────────────────────────────

function Geste({ emetteur, chemin, corps, libelle, onFait }) {
  const [err, setErr] = useState(null)
  const [busy, setBusy] = useState(false)

  async function faire() {
    setBusy(true); setErr(null)
    try {
      const r = await fetch(`${API}/v2/emetteurs/${encodeURIComponent(emetteur)}/etude/${chemin}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(corps || {}),
      })
      const data = await r.json().catch(() => ({}))
      if (!r.ok) { setErr(detailDe(data, r.status)); return }
      onFait()
    } catch (_) {
      setErr('Le serveur ne répond pas.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <span className="inline-flex flex-col gap-1">
      <button type="button" className={BTN} disabled={busy} onClick={faire}>{libelle}</button>
      {err && <span className="text-xs text-red-400">{err}</span>}
    </span>
  )
}

function Attente({ x, emetteur, onFait }) {
  if (x.motif === 'acte_humain') {
    return (
      <li className="space-y-1">
        <p className="text-gray-200"><Badge variant="amber">votre décision</Badge> {x.libelle || x.acte}</p>
        <p className="text-xs text-gray-500">Vérifiez plus bas les documents trouvés et ceux qui manquent, avec leur raison, puis validez.</p>
        <Geste emetteur={emetteur} chemin="acte" corps={{ cle: x.cle }} libelle={x.libelle || 'Valider'} onFait={onFait} />
      </li>
    )
  }
  if (x.motif === 'echec_repete') {
    return (
      <li className="space-y-1">
        <p className="text-gray-200"><Badge variant="red">échec répété</Badge> {pas(x.pas)} a échoué deux fois{x.detail ? ` : ${x.detail}` : ''}</p>
        <Geste emetteur={emetteur} chemin="relance" corps={{ pas: x.pas }} libelle="Réessayer" onFait={onFait} />
      </li>
    )
  }
  return (
    <li className="text-gray-300"><Badge variant="sky">en cours</Badge> {pas(x.pas)}{x.detail ? ` — ${x.detail}` : ''}</li>
  )
}

function Dossier({ vue, emetteur, onFait }) {
  const { etude, etat, passages, intervalle_min } = vue
  const a = etat.arret
  const depense = etat.depense.modeles_usd + etat.depense.web_usd
  let statut
  if (!a) statut = <Badge variant="sky">en cours</Badge>
  else if (a.motif === 'parcours_termine') statut = <Badge variant="emerald">à jour</Badge>
  else if (a.motif === 'pause_depense') statut = <Badge variant="amber">en pause de dépense</Badge>
  else if (a.motif === 'attente') statut = <Badge variant="sky">travail en cours</Badge>
  else statut = <Badge variant="amber">attend une décision</Badge>

  return (
    <Card>
      <CardHeader title="Le dossier"
        subtitle={`Mis à l'étude le ${etude.mise_le} par ${etude.par} — ${etude.motif}`} action={statut} />
      <CardBody className="space-y-4">
        <Dl cols={3}>
          <KeyValue label="Étapes faites" value={etat.faits.length ? etat.faits.map(pas).join(', ') : 'aucune'} />
          <KeyValue label="Dépense"
            value={`${usd(depense)} (modèles ${usd(etat.depense.modeles_usd)}, recherches ${usd(etat.depense.web_usd)})`} />
          <KeyValue label="Coût restant estimé" value={a ? usd(a.cout_restant_estime_usd) : '—'}
            note={a && a.ratio_constate != null ? `dépensé / estimé jusqu'ici : ${a.ratio_constate.toFixed(2)}` : null} />
        </Dl>
        {a && a.motif === 'pause_depense' && (
          <div className="space-y-2 text-sm">
            <p className="text-gray-300">Le dossier a consommé son palier de dépense ({a.detail}). Il ne lance plus rien de payant tant que vous ne l&apos;autorisez pas.</p>
            <Geste emetteur={emetteur} chemin="pause" libelle="Autoriser un palier de dépense de plus" onFait={onFait} />
          </div>
        )}
        {a && a.motif === 'parcours_termine' && (
          <p className="text-sm text-gray-400">Rien d&apos;autre à faire pour l&apos;instant : les étapes suivantes de l&apos;analyse s&apos;ajouteront au dossier quand elles seront construites.</p>
        )}
        {a && a.attentes && a.attentes.length > 0 && (
          <ul className="space-y-3 text-sm">
            {a.attentes.map((x, i) => <Attente key={`${x.pas}-${i}`} x={x} emetteur={emetteur} onFait={onFait} />)}
          </ul>
        )}
        {etat.reserves.length > 0 && (
          <ul className="text-xs text-amber-300 space-y-0.5">
            {etat.reserves.map(([p, m], i) => <li key={i}>Réserve — {pas(p)} : {m}</li>)}
          </ul>
        )}
        <p className="text-[11px] text-gray-600">Le système repasse sur le dossier toutes les {intervalle_min} minutes ; un geste prend effet au passage suivant.</p>
        {passages.length > 0 && (
          <details className="rounded-lg border border-gray-800">
            <summary className="px-3 py-2 text-xs text-gray-400 cursor-pointer">Derniers passages ({passages.length})</summary>
            <ul className="px-3 pb-3 text-xs text-gray-400 space-y-2">
              {passages.map((p, i) => (
                <li key={i}>
                  <span className="text-gray-300">{p.le}</span>
                  {p.issue === 'interrompu' && <Badge variant="red" className="ml-2">interrompu</Badge>}
                  {p.payant_suspendu && <Badge variant="amber" className="ml-2">rien de payant lancé</Badge>}
                  {p.collectes.length > 0 && <span> · {p.collectes.length} collecte(s) relevée(s)</span>}
                  {p.sources.length > 0 && <span> · {p.sources.length} source(s) évaluée(s)</span>}
                  {p.lectures.length > 0 && <span> · {p.lectures.length} document(s) mis en lecture</span>}
                  {p.detail && <span className="block text-amber-300">{p.detail}</span>}
                </li>
              ))}
            </ul>
          </details>
        )}
      </CardBody>
    </Card>
  )
}

// ── La collecte : trouvés, introuvables, dépense ─────────────────────────────────────────────

function Collecte({ col }) {
  const genres = col.referentiel.genres || {}
  const raisons = col.referentiel.raisons || {}
  const enCours = col.travaux.filter(t => t.statut === 'lancee')
  const echouees = col.travaux.filter(t => t.statut === 'echouee')
  const rencontrees = col.sources_rencontrees || []
  return (
    <section className="space-y-3">
      <Titre>Documents demandés</Titre>
      {col.reponses.length === 0 && enCours.length === 0 && echouees.length === 0 ? (
        <EmptyState title="Rien n'a encore été demandé" description="La collecte part au premier passage après la mise à l'étude." />
      ) : (
        <Tableau entetes={['Document demandé', 'Résultat', 'Origine', 'Publié le', 'Faits au', 'Source au jour de la collecte']}>
          {col.reponses.map((rep, i) => {
            const g = genres[rep.demande.genre]
            const libelle = (g && g.libelle) || rep.demande.genre
            if (rep.indisponibilite) {
              const ind = rep.indisponibilite
              return (
                <Fragment key={`r${i}`}>
                  <tr className="border-t border-gray-800 align-top">
                    <td className="py-2 px-3 text-gray-200">{libelle}</td>
                    <td className="py-2 px-3"><Badge variant="red">introuvable</Badge></td>
                    <td colSpan={4} className="py-2 px-3 text-gray-300">{raisons[ind.raison] || ind.raison}</td>
                  </tr>
                  <MotifLigne colSpan={6} motif={[ind.detail, ...(ind.essais || []).map(e => `${e[0]} : ${e[1]}`)].filter(Boolean).join(' · ')} />
                </Fragment>
              )
            }
            return rep.documents.map((d, j) => (
              <Fragment key={`r${i}-${j}`}>
                <tr className="border-t border-gray-800 align-top">
                  <td className="py-2 px-3 text-gray-200">{j === 0 ? libelle : ''}</td>
                  <td className="py-2 px-3"><Badge variant="emerald">trouvé</Badge></td>
                  <td className="py-2 px-3"><Adresse url={d.provenance.adresse} /></td>
                  <td className="py-2 px-3 text-gray-400 whitespace-nowrap">{d.provenance.publie_le || 'non dit'}</td>
                  <td className="py-2 px-3 text-gray-400 whitespace-nowrap">{d.provenance.faits_au || 'non dit'}</td>
                  <td className="py-2 px-3">
                    <Badge variant={d.qualification.admise ? 'emerald' : 'amber'}>
                      {d.qualification.admise ? `admise · ${d.qualification.niveau}` : 'non admise'}
                    </Badge>
                  </td>
                </tr>
                {(d.provenance.mention || !d.qualification.admise) && (
                  <MotifLigne colSpan={6} motif={[d.provenance.mention, d.qualification.admise ? '' : d.qualification.motif].filter(Boolean).join(' · ')} />
                )}
              </Fragment>
            ))
          })}
          {enCours.map(t => (
            <tr key={t.cle} className="border-t border-gray-800 align-top">
              <td className="py-2 px-3 text-gray-200">{(genres[t.demande.genre] || {}).libelle || t.demande.genre}</td>
              <td className="py-2 px-3"><Badge variant="sky">en cours</Badge></td>
              <td colSpan={4} className="py-2 px-3 text-gray-500">{t.essais ? `${t.essais} essai(s)` : 'pas encore relevée'}</td>
            </tr>
          ))}
          {echouees.map(t => (
            <tr key={t.cle} className="border-t border-gray-800 align-top">
              <td className="py-2 px-3 text-gray-200">{(genres[t.demande.genre] || {}).libelle || t.demande.genre}</td>
              <td className="py-2 px-3"><Badge variant="red">en échec</Badge></td>
              <td colSpan={4} className="py-2 px-3 text-gray-300">{t.motif}</td>
            </tr>
          ))}
        </Tableau>
      )}
      <p className="text-xs text-gray-500">
        Dépense de collecte : {usd(col.depense.modeles_usd + col.depense.web_usd)} (modèles {usd(col.depense.modeles_usd)}, recherches {usd(col.depense.web_usd)}).
        {rencontrees.length > 0 && ` Sources inconnues rencontrées : ${rencontrees.map(s => `${s.source} (${s.issue || s.statut})`).join(', ')} — leur sort se suit dans le registre des sources.`}
      </p>
    </section>
  )
}

// ── Les documents lus et leurs lignes ────────────────────────────────────────────────────────

function Lignes({ emetteur, empreinte, debut, fin, surligne }) {
  const [res, setRes] = useState(undefined)
  useEffect(() => {
    const q = new URLSearchParams({ debut: String(debut) })
    if (fin) q.set('fin', String(fin))
    fetch(`${API}/v2/emetteurs/${encodeURIComponent(emetteur)}/lectures/${empreinte}?${q}`)
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(setRes)
      .catch(() => setRes(null))
  }, [emetteur, empreinte, debut, fin])
  if (res === undefined) return <p className="text-xs text-gray-500 px-3 py-2">Chargement…</p>
  if (res === null) return <p className="text-xs text-gray-500 px-3 py-2">Texte indisponible.</p>
  return (
    <div className="max-h-96 overflow-auto bg-gray-950 rounded-lg border border-gray-800 text-[11px] font-mono">
      {res.lignes.map((l, i) => {
        const n = res.debut + i
        const vise = surligne && n >= surligne[0] && n <= surligne[1]
        return (
          <div key={n} className={`flex gap-3 px-2 ${vise ? 'bg-amber-900/30' : ''}`}>
            <span className="text-gray-600 select-none w-12 text-right shrink-0">{n}</span>
            <span className="text-gray-300 whitespace-pre-wrap break-words">{l}</span>
          </div>
        )
      })}
      {res.debut + res.lignes.length - 1 < res.nb_lignes && (
        <p className="px-2 py-1 text-gray-600">… {res.nb_lignes - (res.debut + res.lignes.length - 1)} lignes de plus</p>
      )}
    </div>
  )
}

function DocumentsLus({ con, genres, emetteur }) {
  const [ouvert, setOuvert] = useState(null)
  return (
    <section className="space-y-3">
      <Titre>Documents lus</Titre>
      {con.lectures.length === 0 && con.a_lire.length === 0 ? (
        <p className="text-sm text-gray-500">Aucun document collecté pour l&apos;instant.</p>
      ) : (
        <Tableau entetes={['Document', 'Origine', 'Publié le', 'Lecture', '']}>
          {con.lectures.map(l => (
            <Fragment key={l.empreinte}>
              <tr className="border-t border-gray-800 align-top">
                <td className="py-2 px-3 text-gray-200">{(genres[l.genre] || {}).libelle || l.genre}</td>
                <td className="py-2 px-3"><Adresse url={l.adresse} /></td>
                <td className="py-2 px-3 text-gray-400 whitespace-nowrap">{l.publie_le || 'non dit'}</td>
                <td className="py-2 px-3">
                  {l.statut === 'lue' && <Badge variant="emerald">{l.nb_lignes} lignes</Badge>}
                  {l.statut === 'sans_objet' && <Badge variant="gray">sans objet</Badge>}
                  {l.statut === 'impossible' && <Badge variant="red">lecture impossible</Badge>}
                </td>
                <td className="py-2 px-3">
                  {l.statut === 'lue' && (
                    <button type="button" className={LIEN} onClick={() => setOuvert(ouvert === l.empreinte ? null : l.empreinte)}>
                      {ouvert === l.empreinte ? 'fermer' : 'lire'}
                    </button>
                  )}
                </td>
              </tr>
              {l.statut !== 'lue' && <MotifLigne colSpan={5} motif={[con.raisons[l.raison] || l.raison, l.detail].filter(Boolean).join(' · ')} />}
              {ouvert === l.empreinte && (
                <tr><td colSpan={5} className="px-3 pb-3"><Lignes emetteur={emetteur} empreinte={l.empreinte} debut={1} /></td></tr>
              )}
            </Fragment>
          ))}
          {con.a_lire.map(e => (
            <tr key={e} className="border-t border-gray-800">
              <td colSpan={5} className="py-2 px-3 text-gray-500">Un document attend sa lecture (au prochain passage) · <span className="font-mono">{e.slice(0, 12)}</span></td>
            </tr>
          ))}
        </Tableau>
      )}
    </section>
  )
}

// ── Les pièces ───────────────────────────────────────────────────────────────────────────────

function Pieces({ con, genres, emetteur }) {
  const [ouvert, setOuvert] = useState(null)
  return (
    <section className="space-y-3">
      <Titre>Pièces</Titre>
      {con.pieces.length === 0 ? (
        <p className="text-sm text-gray-500">Aucune pièce citée pour l&apos;instant : les pièces viendront avec l&apos;analyse, chacune vérifiée mot pour mot contre son document.</p>
      ) : (
        <div className="space-y-3">
          {con.pieces.map(p => {
            const v = p.valeur
            return (
              <Card key={p.identifiant}>
                <CardBody className="space-y-2">
                  <blockquote className="text-sm text-gray-200 border-l-2 border-gray-700 pl-3 whitespace-pre-wrap">{p.extrait}</blockquote>
                  <p className="text-xs text-gray-400">
                    {(genres[p.genre] || {}).libelle || p.genre} · {p.publie_le || 'date de publication non dite'} ·
                    {p.ligne_debut === p.ligne_fin ? ` ligne ${p.ligne_debut}` : ` lignes ${p.ligne_debut}–${p.ligne_fin}`}
                    {p.autres_lignes.length > 0 && ` (même texte aussi lignes ${p.autres_lignes.join(', ')})`}
                    {p.periode ? ` · période : ${p.periode}` : ' · période non précisée'}
                    {` · citée le ${p.cite_le} par ${p.auteur}`}
                  </p>
                  <p className="text-xs">
                    {v.revoquee_le
                      ? <Badge variant="red">source révoquée le {v.revoquee_le}</Badge>
                      : <Badge variant={v.admise ? 'emerald' : 'amber'}>{v.admise ? `source admise · ${v.niveau}` : 'source non admise'}</Badge>}
                    <span className="ml-2 text-gray-500">{v.revoquee_le ? v.motif_revocation : v.motif}</span>
                  </p>
                  <button type="button" className={LIEN} onClick={() => setOuvert(ouvert === p.identifiant ? null : p.identifiant)}>
                    {ouvert === p.identifiant ? 'fermer' : 'voir dans le document'}
                  </button>
                  {ouvert === p.identifiant && (
                    <Lignes emetteur={emetteur} empreinte={p.empreinte} debut={Math.max(1, p.ligne_debut - 5)}
                      fin={p.ligne_fin + 5} surligne={[p.ligne_debut, p.ligne_fin]} />
                  )}
                </CardBody>
              </Card>
            )
          })}
        </div>
      )}
    </section>
  )
}

// ── La section entière ───────────────────────────────────────────────────────────────────────

export default function EtudeEmetteur({ emetteur }) {
  const [vue, setVue] = useState(undefined) // undefined : en cours ; null : indisponible
  const [err, setErr] = useState(null)

  const charger = useCallback(() => {
    fetch(`${API}/v2/emetteurs/${encodeURIComponent(emetteur)}/etude`)
      .then(async r => {
        const data = await r.json().catch(() => ({}))
        if (!r.ok) throw new Error(detailDe(data, r.status))
        return data
      })
      .then(d => { setVue(d); setErr(null) })
      .catch(e => { setVue(null); setErr(e.message) })
  }, [emetteur])

  useEffect(() => { setVue(undefined); charger() }, [charger])

  return (
    <section className="space-y-4">
      <Titre>Étude de la société</Titre>
      {vue === undefined && <p className="text-sm text-gray-500">Chargement…</p>}
      {vue === null && <p className="text-sm text-gray-500">Étude indisponible{err ? ` : ${err}` : '.'}</p>}
      {vue && !vue.etude.etude && <MettreALEtude emetteur={emetteur} onFait={charger} />}
      {vue && vue.etude.etude && (
        <>
          <Dossier vue={vue.etude} emetteur={emetteur} onFait={charger} />
          <Collecte col={vue.collecte} />
          <DocumentsLus con={vue.connaissance} genres={vue.collecte.referentiel.genres || {}} emetteur={emetteur} />
          <Pieces con={vue.connaissance} genres={vue.collecte.referentiel.genres || {}} emetteur={emetteur} />
        </>
      )}
    </section>
  )
}
