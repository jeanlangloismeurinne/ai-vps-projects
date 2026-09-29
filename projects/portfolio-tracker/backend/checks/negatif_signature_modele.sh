#!/usr/bin/env bash
# TEST NÉGATIF de `check_signature_modele.py` (capacité 4 bis, migration 051) — BIDIRECTIONNEL.
#
#   bash checks/negatif_signature_modele.sh
#
# SATISFIABILITÉ — le check non muté est VERT : **43 vérifications OK, 0 échec** (mesuré avant toute
# mutation). DISCRIMINATION — une mutation par garde, et c'est l'assert VISÉ qui rougit.
#
# ⚠️ LES MUTATIONS QUI COMPTENT VRAIMENT : celles qui feraient afficher au comité une valorisation qu'il
# n'a pas signée (une proposition prise pour la signée, la plus ancienne signature prise pour la
# dernière) ou qui cacheraient qu'un modèle signé ne tient plus contre le dossier du jour.
set -u
cd "$(dirname "$0")/.." || exit 1

G="app/valorisation/signature.py"
S="app/contracts/signature_modele_schema.py"

CHECK="checks/check_signature_modele.py"
NET=none

mutations=(
  # ── Ce que le comité voit ──────────────────────────────────────────────────────────────────
  "$G¦    return None if any(d.modele_id == derniere.id for d in pv) else derniere¦    return derniere¦la version signée n'est plus en attente"
  "$G¦    derniere = max(versions, key=lambda v: v.version)¦    derniere = min(versions, key=lambda v: v.version)¦seule v3 est en attente"
  "$G¦    return max(signees, key=lambda d: d.id) if signees else None¦    return min(signees, key=lambda d: d.id) if signees else None¦une signature plus récente remplace"
  "$G¦    signees = [d for d in pv if d.action == \"signer\"]¦    signees = list(pv)¦v3 écartée → la v1 signée reste la référence"
  "$G¦        f, motif = _juger(v.modele, dossier)¦        f, motif = fourchette_de(evaluer_modele(v.modele)), None¦une pièce du tableau remplacée depuis"
  "$G¦            f = fourchette_de(ev) if ev.bas <= ev.central <= ev.haut else None¦            f = None¦la mécanique tourne encore"
  "$G¦            fourchette=f if motif is None else None,¦            fourchette=f,¦une proposition qui ne tient pas"
  "$G¦        proces_verbal=sorted(pv, key=lambda d: d.id, reverse=True),¦        proces_verbal=sorted(pv, key=lambda d: d.id),¦le PV est servi le plus récent d'abord"
  "$G¦\"aucun_modele_propose\" if not versions else \"aucun_modele_signe\"¦\"aucun_modele_propose\"¦toutes les versions écartées"
  # ── L'écart entre versions ─────────────────────────────────────────────────────────────────
  "$G¦                              for c in communes if avant[c].valeur != apres[c].valeur],¦                              for c in communes],¦l'écart dit la seule ligne changée"
  "$G¦        origines_changees=[c for c in communes if avant[c].origine != apres[c].origine],¦        origines_changees=[],¦même chiffre, autre source"
  "$G¦        segments_ajoutes=sorted(seg_apres - seg_avant),¦        segments_ajoutes=[],¦un produit lancé"
  "$G¦        forme_changee=signee.fourchette != proposee.fourchette,¦        forme_changee=False,¦changement de forme"
  # ── Les réponses reprenables ───────────────────────────────────────────────────────────────
  "$G¦            for r in reponses if reponse_tient(r) and r.servie.reponse is not None}¦            for r in reponses if r.verdict == \"acquitte\" and r.servie.reponse is not None}¦PÉRIMÉE par un fait publié depuis"
  "$G¦            for r in reponses if reponse_tient(r) and r.servie.reponse is not None}¦            for r in reponses if reponse_tient(r)}¦ne porte aucun chiffre"
  # ── Le contrat ─────────────────────────────────────────────────────────────────────────────
  "$S¦        if (self.action == \"signer\") != (self.fourchette is not None):¦        if self.action == \"signer\" and self.fourchette is None:¦écarter AVEC une fourchette"
  "$S¦        if not self.bas <= self.central <= self.haut:¦        if not self.bas <= self.haut:¦croisée (bas > central)"
  "$S¦        if (self.modele.ticker_id, self.modele.version) != (self.ticker_id, self.version):¦        if self.modele.ticker_id != self.ticker_id:¦une ligne v2 qui porte le modèle v1"
  "$S¦        if self.signable != (self.motif_refus is None):¦        if False:¦malgré un motif de refus"
  "$S¦        if self.etat != attendu:¦        if False:¦sans version signée est refusé"
  "$G¦                chiffres={c.id: (c.valeur, c.unite) for c in r.servie.reponse.chiffres_cles})¦                chiffres={})¦apporte son ENCADRÉ"
)

source "$(dirname "$0")/_negatif.sh"
run_mutations
