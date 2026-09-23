#!/usr/bin/env bash
# TEST NÉGATIF de `check_datation.py` (#79) — BIDIRECTIONNEL.
#
#   bash checks/negatif_datation.sh
#
# POURQUOI CE FICHIER EXISTE. Le lot #79 ne muscle aucune garde : il change la FORME de la réponse
# (deux dates nommées au lieu d'une case contestée, #68). Un lot de ce genre est exactement celui
# qui peut s'écrire tout entier sans rien tenir — les asserts passent parce que le contrat est neuf,
# pas parce qu'il garde quoi que ce soit. D'où les deux sens exigés
# (`feedback_acceptation_rouge_bidirectionnelle`) :
#   · SATISFIABILITÉ — le check non muté est VERT. Prouvé ci-dessous, avant toute mutation, sur la
#     vraie base (§7 en fait partie : sans `CHECK_DB_URL`, §7 sort en échec NOMMÉ, jamais en saut).
#   · DISCRIMINATION — une mutation par critère, et c'est l'assert VISÉ, nommé, qui rougit.
#
# ⚠️ LA MUTATION QUI COMPTE VRAIMENT est la n°3 : `constatee` dérivée de la date du DOCUMENT au lieu
# de celle du FAIT. C'est littéralement l'état d'avant le lot — #307 qui trie au 2026-08-05 en
# affirmant le 2026-06-30. Si cette mutation laissait le check vert, tout le reste serait du décor.
#
# ⚠️ CE QUE LES MUTATIONS 6→17 DÉSARMENT, ET COMMENT. Une garde de `valider()` ne peut pas être
# supprimée en coupant son `if` : `constatee` sans `date_du_fait` irait alors comparer `None > date`
# et tuerait le script AVANT son bilan (2ᵉ faux-vert). Chaque mutation insère donc un `return` dans
# la branche — la garde est TOLÉRANTE au lieu d'être absente, ce qui est de toute façon le mode de
# panne réel : on ne supprime pas une règle, on lui ajoute un cas d'exception.
#
# ⚠️ CE QUE LA MUTATION 11 NE PROUVE PAS. « prospective sans date d'annonce » n'a pas de ligne
# ciblable seule : son `if d.date_du_document is None:` est le JUMEAU exact de celui de `constatee`
# (même texte, même indentation), et le remplacement ne vise que la 1ʳᵉ occurrence. La mutation
# désarme donc la branche prospective ENTIÈRE. Elle prouve que la branche refuse ce cas, pas quelle
# ligne le refuse — les trois autres refus prospectifs, eux, ont leur mutation propre (10, 12, 13).
# Si le remplacement avait visé la mauvaise occurrence, le harnais le dirait : le rouge tomberait
# sur « constatee sans date du document » et pas sur l'assert visé.
set -u
cd "$(dirname "$0")/.." || exit 1

SRC="app/knowledge/datation.py"
CONTRAT="app/contracts/worker_delegation_schema.py"
GUICHET="app/knowledge/service.py"
SQL045="app/db/migrations/045_v2_datation_fait_document.sql"

CHECK="checks/check_datation.py"
NET=coolify
CHECK_DB_URL=$(grep -m1 '^DATABASE_URL=' .env | cut -d= -f2- | sed 's|postgresql+asyncpg://|postgresql://|')
export CHECK_DB_URL

# ── SATISFIABILITÉ ────────────────────────────────────────────────────────────────────────────────
# Une acceptation qui ne peut pas virer au vert n'éprouve rien. On le mesure ICI plutôt que de s'en
# remettre au souvenir d'un `run_all.sh` vert (`feedback_ligne_de_base_est_une_mesure`).
_IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
_base=$(docker run --rm --network "$NET" -v "$PWD:/app:ro" -v "$PWD/../roadmap:/roadmap:ro" \
        -w /app -e PYTHONPATH=/app --env-file checks/env.checks -e "CHECK_DB_URL=$CHECK_DB_URL" \
        "$_IMG" python "$CHECK" 2>&1); _rc=$?
if [ "$_rc" -ne 0 ] || ! printf '%s' "$_base" | grep -q 'vérifications OK'; then
  echo "  FAIL satisfiabilité — le check rougit AVANT toute mutation"
  printf '%s\n' "$_base" | grep -E 'FAIL' | head -5
  exit 1
fi
printf '  ok   satisfiabilité · %s\n\n' "$(printf '%s' "$_base" | grep -E 'vérifications OK')"

mutations=(
# ── §1 LE VOCABULAIRE EST FERMÉ ───────────────────────────────────────────────────────────────────
# 1. Le vocabulaire cesse d'être fermé : un jeton inconnu est TOLÉRÉ au lieu d'être refusé. C'est le
#    retour de « probablement constatée » — un quatrième état qui n'a ni règle de dérivation ni
#    constructeur, donc qui tombera silencieusement dans la branche `indatable`.
"$SRC¦    if d.portee not in PORTEES:¦    if d.portee not in PORTEES:\n        return  # mutation: un jeton inconnu est toléré¦un quatrième état n'existe pas"

# 2. UN JETON AJOUTÉ SANS COMPORTEMENT — le mot mort de #32. Le vocabulaire grossit, aucune fonction
#    ne sait quoi en faire, et rien ne le signale : c'est le défaut que §1 garde en générant son
#    parcours depuis `PORTEES` au lieu d'énumérer à la main.
"$SRC¦PORTEES: frozenset[str] = frozenset({\"constatee\", \"prospective\", \"indatable\"})¦PORTEES: frozenset[str] = frozenset({\"constatee\", \"prospective\", \"indatable\", \"probablement_constatee\"})  # mutation¦aucune portée du vocabulaire n'est un mot mort"

# ── §2 LA DÉRIVATION — le cœur du lot ─────────────────────────────────────────────────────────────
# 3. ⚠️ L'ÉTAT D'AVANT LE LOT, RESTAURÉ. Un constat fait foi à la date du PAPIER. #307 affirme le
#    2026-06-30 et trie au 2026-08-05 ; #309, colonne comparative, porte le tampon le plus frais du
#    dossier. Si le check restait vert ici, il ne garderait rien du tout.
"$SRC¦            return self.date_du_fait¦            return self.date_du_document  # mutation: le constat fait foi à la date du PAPIER¦un constat fait foi à la date du FAIT"
# 4. Une prévision datée de ce qu'elle VISE et non de son annonce : une guidance FY2027 émise hier
#    deviendrait une information de décembre 2027, donc la pièce la plus « fraîche » du dossier,
#    jusqu'à deux ans avant d'être vérifiable.
"$SRC¦            return self.date_du_document¦            return self.periode_visee  # mutation: une prévision daterait de ce qu'elle vise¦une prévision fait foi à la date de son ANNONCE"
# 5. Une pièce indatable se fabrique une date depuis son document : la page « gouvernance » re-servie
#    chaque trimestre gagnerait l'élection de fraîcheur contre un fait mesuré. L'absence de date est
#    le RÉSULTAT de la portée (#53), pas un trou à combler.
#    ⚠️ CETTE MUTATION EST RESTÉE VERTE au premier passage, et c'est elle qui a payé ce fichier :
#    §2 n'éprouvait `indatable` que SANS document, le seul cas où la mutation ne change rien. Le
#    cas réel — une indatable qui nomme sa source, ce que §3 autorise — n'était asserté nulle part.
#    D'où l'assert visé ci-dessous, ajouté au check : c'est le nommage du document qui discrimine.
"$SRC¦        return None  # indatable : l'absence est le résultat, pas un échec¦        return self.date_du_document  # mutation: l'indatable se fabrique une date¦elle NOMME le document d'où elle vient"

# ── §3 LES GARDES DE `valider()` — une par refus décidable ────────────────────────────────────────
# 6. Un constat sans date de fait passe. C'est la porte de service du lot : faute de case, le
#    producteur retomberait sur la date du document, et #79 serait annulé sans qu'une ligne change.
"$SRC¦        if d.date_du_fait is None:¦        if d.date_du_fait is None:\n            return  # mutation: le constat non daté est toléré¦REFUSÉ : constatee sans date du fait"
# 7. Un constat sans document. Visé par sa ligne de `raise` (UNIQUE) et non par son `if` (jumeau de
#    celui de la branche prospective) — et l'exception devient un `return`, sinon la comparaison
#    `date > None` tuerait le script avant son bilan.
"$SRC¦            raise DatationInvalide(\"constatee exige \`date_du_document\` : un constat vient d'un document\")¦            return  # mutation: le constat sans document est toléré¦REFUSÉ : constatee sans date du document"
# 8. Un document qui constate l'AVENIR. C'est la frontière entre les deux portées : sans elle, une
#    guidance se déclare `constatee` et fait foi à la date de ce qu'elle promet.
"$SRC¦        if d.date_du_fait > d.date_du_document:¦        if d.date_du_fait > d.date_du_document:\n            return  # mutation: un document constate l'avenir¦REFUSÉ : constatee dont le fait est POSTÉRIEUR au document"
# 9. L'EXCLUSIVITÉ du vocabulaire (#54), côté constat : une pièce qui porte à la fois un fait et une
#    période visée est deux choses à la fois, donc le module « réalisé vs annoncé » ne saura jamais
#    laquelle confronter.
"$SRC¦        if d.periode_visee is not None:¦        if d.periode_visee is not None:\n            return  # mutation: un constat porte une période visée¦REFUSÉ : constatee qui porte une période visée"
# 10. Une prévision sans période visée : l'annonce est datée, mais ce qu'elle promet ne l'est pas —
#     le réalisé ne pourra JAMAIS lui être confronté. La capacité du backlog naîtrait aveugle.
"$SRC¦        if d.periode_visee is None:¦        if d.periode_visee is None:\n            return  # mutation: une prévision sans période visée passe¦REFUSÉ : prospective sans période visée"
# 11. Une prévision sans date d'annonce — cf. l'avertissement d'en-tête : la branche prospective
#     entière est désarmée, faute de ligne ciblable seule.
"$SRC¦    elif d.portee == \"prospective\":¦    elif d.portee == \"prospective\":\n        return  # mutation: plus aucune garde prospective¦REFUSÉ : prospective sans date d'annonce"
# 12. Une « prévision » dont la période est DÉJÀ CLOSE à l'annonce : un résultat publié, rebaptisé
#     prévision, gagne la date du communiqué au lieu de celle de l'exercice. C'est #307 par l'autre
#     porte — le même tampon frais sur un fait ancien.
"$SRC¦        if d.periode_visee <= d.date_du_document:¦        if d.periode_visee <= d.date_du_document:\n            return  # mutation: une période close passe pour une prévision¦REFUSÉ : prospective dont la période est DÉJÀ CLOSE à l'annonce"
# 13. L'EXCLUSIVITÉ côté prévision : une prospective qui porte déjà un fait.
"$SRC¦        if d.date_du_fait is not None:¦        if d.date_du_fait is not None:\n            return  # mutation: une prévision porte déjà un fait¦REFUSÉ : prospective qui porte déjà un fait"
# 14. L'EXCLUSIVITÉ côté indatable : elle déclare n'avoir pas de date ET en fournit une. La portée
#     déclarée et le contenu déclaré se contredisent, et c'est la portée qui gagne au tri.
"$SRC¦        if d.date_du_fait is not None or d.periode_visee is not None:¦        if d.date_du_fait is not None or d.periode_visee is not None:\n            return  # mutation: l'indatable porte quand même un fait¦REFUSÉ : indatable qui porte quand même un fait"
# 15. ⚠️ LA GARDE DOIT DISCRIMINER, PAS PUNIR. Sans ce sens-là, la mutation 14 resterait verte par
#     l'autre bout : un `valider` qui refuse TOUT satisfait tous les asserts de refus. Ici
#     l'indatable ne peut plus nommer le document d'où elle vient — or le nommer est légitime et
#     utile (c'est la traçabilité), c'est seulement en DÉRIVER une date qui ne l'est pas.
"$SRC¦        if d.date_du_fait is not None or d.periode_visee is not None:¦        if d.date_du_fait is not None or d.periode_visee is not None or d.date_du_document is not None:  # mutation: l'indatable ne peut plus nommer son document¦une pièce indatable PEUT nommer son document"
# 16. Une absence MUETTE : « pas de date » sans dire pourquoi. Un silence se relit plus tard comme
#     une propriété du sujet (`feedback_rendu_est_un_producteur`) — ici, « cette société n'a pas de
#     dates » au lieu de « cette pièce n'en affirme pas ».
"$SRC¦        if not (d.motif or \"\").strip():¦        if False:  # mutation: le motif n'est plus exigé¦REFUSÉ : indatable sans motif"
# 17. Le motif d'ESPACES : la garde subsiste et ne refuse plus rien. Forme sournoise du défaut 16 —
#     le champ est rempli, le producteur passe, et la case est vide à la lecture.
"$SRC¦        if not (d.motif or \"\").strip():¦        if not (d.motif or \"\"):  # mutation: des espaces comptent pour un motif¦REFUSÉ : indatable au motif vide"

# ── §4 LE CONTRAT — ce que le modèle peut seulement ÉCRIRE ────────────────────────────────────────
# 18. LA CASE CONTESTÉE REVIENT. Tant que `source_date` est une clef admise, le modèle la remplit et
#     tout le reste du lot devient facultatif : deux chemins coexistent, l'ancien gagne.
"$CONTRAT¦    portee_temporelle: Literal[\"constatee\", \"prospective\", \"indatable\"]¦    source_date: Optional[str] = None  # mutation: la case contestée revient\n    portee_temporelle: Literal[\"constatee\", \"prospective\", \"indatable\"]¦n'a PLUS de champ \`source_date\`"
# 19. `extra=\"ignore\"` : un `source_date` résiduel n'est plus REJETÉ, il est silencieusement jeté.
#     C'est le mode de panne de #54 — le modèle croit l'avoir dit, le système ne l'a jamais reçu, et
#     personne ne l'apprend. Le retrait d'un champ n'est un retrait que si la classe est `forbid`.
"$CONTRAT¦    model_config = ConfigDict(extra=\"forbid\")¦    model_config = ConfigDict(extra=\"ignore\")  # mutation¦le contrat REJETTE une clef inconnue"
# 20. UN DÉFAUT SILENCIEUX sur la portée : une entry non datée entre en se faisant passer pour un
#     constat. « Il n'y a pas d'état par défaut » est précisément ce que le lot achète.
"$CONTRAT¦    portee_temporelle: Literal[\"constatee\", \"prospective\", \"indatable\"]¦    portee_temporelle: Literal[\"constatee\", \"prospective\", \"indatable\"] = \"constatee\"  # mutation: un défaut silencieux¦la portée est OBLIGATOIRE"
# 21. LE CHAMP QUI PARAÎT INUTILE : `periode_visee` ne sert à aucun tri aujourd'hui (la prospective
#     fait foi à son annonce), donc c'est LUI qu'un nettoyage futur retirera. Il est pourtant le
#     seul ingrédient du module « qualité des prévisions » — sans lui, la capacité naît impossible.
"$CONTRAT¦    periode_visee: Optional[str] = None¦    # periode_visee RETIRÉ (mutation) ¦…et il porte \`periode_visee\`"

# ── §5 DÉTENTEUR UNIQUE — la règle n'a qu'un domicile (#46) ───────────────────────────────────────
# 22. LE GUICHET ROUVRE SA VIEILLE PORTE. Deux entrées pour la même colonne : celle qui dérive et
#     celle qui déclare. Une règle qui a deux domiciles se corrige dans un seul.
"$GUICHET¦    datation: Datation,¦    source_date: Optional[str] = None,\n    datation: Datation,¦n'accepte PLUS \`source_date=\`"
# 23. `datation` prend une valeur par défaut : une entry non datée entre PAR OMISSION, sans qu'aucun
#     appelant ait rien écrit. C'est l'exact symétrique de 20, côté guichet.
"$GUICHET¦    datation: Datation,¦    datation: Datation = None,  # mutation: une entry non datée entre par omission¦sans valeur par défaut"
# 24. UN PRODUCTEUR REPOSE LA DATE À LA MAIN, à côté de la datation. Rien ne casse, rien ne se voit :
#     le kwarg surnuméraire serait accepté le jour où le guichet le rouvrirait (mutation 22). C'est
#     la paire 22+24 qui referme le chemin, pas l'une des deux.
"app/agents/v2/exit.py¦                    datation=constatee(date_du_fait=date.today(), date_du_document=date.today()),¦                    datation=constatee(date_du_fait=date.today(), date_du_document=date.today()),\n                    source_date=date.today(),  # mutation¦app/agents/v2/exit.py ne passe plus \`source_date=\`"
# 25. LA RÈGLE RECOPIÉE au lieu d'être importée : un `constatee` local dans le producteur. Vert
#     aujourd'hui, divergent au premier correctif de la règle — #46 en une ligne.
"app/knowledge/edgar_feed.py¦from app.knowledge.datation import constatee¦def constatee(*, date_du_fait, date_du_document):  # mutation: la règle RECOPIÉE ici\n    return (date_du_fait, date_du_document)¦app/knowledge/edgar_feed.py importe la règle"
# 26. UN PRODUCTEUR CESSE DE PASSER PAR LE GUICHET (ici : un wrapper local). Il sort alors de la
#     DÉCOUVERTE — donc des asserts qui le jugent — et c'est le recensement, et lui seul, qui le
#     voit disparaître. Sans cette contrepartie, une écriture pourrait quitter le guichet sans
#     qu'aucune ligne ne rougisse : le contrôle se serait évaporé avec son sujet.
"app/knowledge/valuation_feed.py¦                    stored = await store_knowledge(¦                    stored = await _store(  # mutation: le producteur passe par un wrapper¦recensés mais disparus : ['app/knowledge/valuation_feed.py']"
# 27. UN PRODUCTEUR CLANDESTIN — l'autre sens du recensement. Un module quelconque se met à écrire
#     dans le corpus ; il est DÉCOUVERT (donc jugé : il ne datera pas en douce) et signalé comme
#     non recensé, ce qui force une décision explicite sur sa datation au lieu d'un ajout muet.
#     C'est cette découverte qui manquait : trois producteurs réels — `curator`, `base_rate_corpus`,
#     `synthesis_feed` — ont vécu HORS de la liste écrite à la main, et le check était vert.
"app/knowledge/units.py¦def montant(v: Optional[float], devise: str = \"\", *, nd: int = 1) -> str:¦def _producteur_clandestin(conn):  # mutation: une écriture hors recensement\n    return store_knowledge(conn, datation=None)\n\n\ndef montant(v: Optional[float], devise: str = \"\", *, nd: int = 1) -> str:¦non recensés : ['app/knowledge/units.py']"

# ── §7 L'ÉTAT PERSISTÉ — le check lit-il vraiment la base ? ───────────────────────────────────────
# 27. UNE CONTRAINTE DÉCLARÉE MAIS NON POSÉE : la migration nomme une contrainte que la base ne porte
#     pas. C'est le cas de la migration ÉCRITE ET JAMAIS APPLIQUÉE — le diff est parfait, la base est
#     d'avant. §7 ne peut le voir que s'il interroge réellement `pg_constraint` ; cette mutation est
#     la seule preuve que la section mesure un état et ne relit pas un fichier.
"$SQL045¦    ADD CONSTRAINT knowledge_entries_source_date_derivee_check¦    ADD CONSTRAINT knowledge_entries_source_date_derivee_check_jamais_posee¦_jamais_posee\` de la 045 est POSÉE en base"
)

source "$(dirname "$0")/_negatif.sh"
run_mutations
