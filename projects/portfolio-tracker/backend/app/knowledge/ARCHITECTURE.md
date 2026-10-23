# `knowledge/` — base de connaissance & sources de données

> **Cible** (spec : `roadmap/V3/doctrine-trois-axes.md`, `03-spec-frameworks.md` §5/§1.7).
> **Réalisé** : prouvé par les `check_*.py` cités ci-dessous — les exécuter, ne pas croire cette prose.

## Rôle

La couche 3 : la base de connaissance (`knowledge_entries`, versionnée append-only) + les **8 feeds
déterministes** qui l'alimentent + la recherche vectorielle. C'est ici qu'on **ajoute une source de
données**.

## Ajouter une source de données — le contrat

Une source est un **objet standard** : elle règle son interface avec la base, rien d'autre.

1. **Émettre par le passage obligé.** Écrire `<x>_feed.py` qui appelle
   `service.store_knowledge(conn, *, ticker_id, entry_type, content, source_type, …)`. **Jamais
   d'INSERT direct.** Le `reliability_score`/`tier` sont **CALCULÉS** par `store_knowledge`, jamais
   fournis par l'appelant (§6.3, #50).
2. **S'inscrire nominativement.** Déclarer le domaine de la source dans `source_registry.py` — le
   standing est accordé pour un **couple (source × nature)** (#52). L'admission est un **acte humain**,
   jamais une promotion automatique, pas même par corroboration.
3. **La nature se dérive, ne se déclare pas.** Un fait à recette déterministe (un `metric` structuré)
   est `mesure` ; `store_knowledge` l'arbitre via `derive_nature` (détenteur unique, #51). Le feed ne
   passe que `nature_declaree`.
4. **Formats et datation par les détenteurs uniques.** Montants via `units.py` (#46) ; un flux se date
   par son exercice, un poste de bilan par un instant, un ratio par ses postes (#42) ; l'identité d'un
   fait est ce qu'il mesure (#43) ; *calculé / non calculable / absent* sont **trois états** (#44).
5. **Plan-dérivé (v3).** Un producteur ne collecte que ce que le **plan** réclame, jamais « tout ce
   qu'il sait faire » (#61) — ex. `run_edgar_feed(metrics=…)`.
6. **Jamais recombiner les axes en scalaire** (#50) ; l'actualité se **calcule à la lecture** (#53).

## Fichiers

| Fichier | Rôle |
|---|---|
| `service.py` | `store_knowledge` (passage obligé), scoring, versionnement A1 |
| `source_registry.py` | Registre nominatif des sources admises (#52) |
| `edgar_feed.py` · `financials_feed.py` · `valuation_feed.py` · `base_rate_corpus.py` | Feeds financiers déterministes |
| `material_events.py` · `staleness.py` · `actualite.py` | Événements matériels & péremption (axe actualité) |
| `evenements.py` | Ce qu'un événement ROUVRE (#89) : type d'un dépôt par sa FORME (`a_qualifier` quand la forme ne décide pas) et ancre PAR QUESTION — le dernier fait d'un type qui la rouvre, filtré par `frameworks.types_qui_rouvrent` |
| `websearch.py` · `document_search.py` · `embeddings.py` | Recherche web + sélection de passages + embeddings bge-m3 1024d |
| `units.py` | Détenteur unique du format des montants (#46) |
| `datation.py` | Détenteur unique de la datation d'une pièce : portée fermée (`constatee`/`prospective`/`indatable`), **deux dates nommées** (fait, document), `source_date` DÉRIVÉE (#79). Moitié ÉCRITURE de ce dont `actualite.py` est la moitié LECTURE |
| `edgar_facts.py` · `synthesis_feed.py` | Extraction EDGAR · synthèses grounded |
| `appariement_feed.py` | Exécute une formule d'appariement sur les concepts XBRL **déjà lus** — produit un fait calculé, sa provenance concept par concept et son tier dérivé (#72) |
| `socle_comptes.py` · `socle_comptes.yaml` · `socle_comptes_emetteurs.yaml` | Le **socle des comptes** (#115) : compte de résultat, bilan et flux reconstitués au format maison depuis `companyfacts`, cinq exercices + douze mois glissants + dernier bilan, bouclés (un écart se publie), reclassements d'analyste propres à l'émetteur. Pur ; le gabarit est une DONNÉE |
| `ratios_maison.py` | Les **ratios maison** (capacité 4 bis, gabarit 1.1.0) : rendement du capital employé (capital MOYEN de l'exercice, taux d'impôt borné), conversion du résultat en trésorerie (rapport des sommes sur trois exercices), capital par point de croissance, pente du rendement — définitions écrites une fois, lues par le code dans le socle, recalculées à la lecture (seule leur VERSION est persistée, dans l'empreinte) ; lus par l'encadré de qf_1/qf_2/qf_3/qf_5 (`ChiffreDuSocle.ratio`). Pur |
| `socle_feed.py` | Publie le socle comme UNE pièce du dossier (`metric = socle_comptes`), versionnée à chaque nouveau dépôt, idempotente ; jointe d'office aux frameworks `lit_le_socle` |
| `ventilation_publiee.yaml` · `app/contracts/ventilation_schema.py` | Lot M2 (roadmap V3 `11`) : le référentiel des AXES de ventilation que le fonds relève (secteurs, activités, géographie, clients) — axe XBRL, règle de raccord, qualificateurs neutres/admis. DONNÉE, contrat pydantic strict (préfixe `us-gaap:`/`srt:` exigé : garde de réplicabilité au chargement) |
| `ventilation_xbrl.py` | Le lecteur XBRL PUR (lot M2) : `lire_instance`/`lire_etiquettes`/`lire_hierarchie` — l'instance d'un dépôt (faits dimensionnés par axe/membre), ses étiquettes (`terseLabel` > `verboseLabel` > `label`), la hiérarchie des membres (`definitionLink`, conflits rendus). Agnostique au conteneur : lit aussi bien un `.xsd` qui embarque labels/définitions (mesuré sur RVMD) qu'un `_lab.xml`/`_def.xml` séparé. Aucun réseau |
| `ventilation.py` | Le relevé et le raccord PURS (lot M2) : classe un fait sur l'axe qu'il porte (après retrait des qualificateurs neutres ; un axe en trop → sous-détail), le rattache à une ligne du gabarit maison (détenteur unique des concepts, #46), relève BRUT, par dépôt (cumuls de tous les membres, dates des flux, totaux des cumuls) — raccords et douze mois se calculent dans `perimetre.vue_servie` (#142) ; `rendre_ventilation` ne rend que la vue. Trois constats (`ventilee`/`secteur_unique`/`sans_ventilation`), jamais un échec |
| `ventilation_feed.py` | Publie la ventilation comme UNE pièce du dossier (`metric = ventilation_publiee`), calquée sur `socle_feed.py` : famille lue au référentiel du classeur (`modele_entreprise.famille_par_archetype` via l'archétype en vigueur, `read_archetype`) — une famille sans gabarit (bancaire, 1.0.0) refuse NOMMÉ à la PUBLICATION, la fonction pure reste exécutable. Aucune jointure aux frameworks en M2 (seul l'outil l'appelle) |
| `explorateur.py` | Lot B4f (roadmap V3 `16-lot-B4f-explorateur.md`) : le DÉTENTEUR UNIQUE de l'accès du modèle au dossier au-delà de la matière — `table_des_matieres`/`ouvrir_note`/`ouvrir_piece`/`rechercher` (exécuteurs, purs côté rendu), `etat_piece` (en vigueur / remplacée, jamais stocké), `pieces_citables_effectif` (§3 : matière ∪ pièces ouvertes), `JournalExploration`. Branché sur l'architecte (`app/modele_entreprise/architecte.py`, interrupteur `acces_au_dossier`) ; brique commune pour les branchements ultérieurs (analystes, valorisation) |
| `perimetre.py` | Lot P1 (roadmap V3 `14-lot-P1-perimetre.md`) : le détenteur UNIQUE des changements de DÉCOUPAGE et de PÉRIMÈTRE — régimes par axe (§2.1), transitions typées par les MONTANTS (`detail_ajoute`/`renommage`/`regroupement`/`scission`/`meme_nom_contenu_change`/`rupture`/`axe_apparu`/`axe_disparu`, recherche de partition BORNÉE, §2.2), la chronique (série comparable dans le régime de référence, origine `publie`/`passage` = addition vérifiée ; plus aucune répartition par hypothèse depuis le 2026-10-23, §7 bis, #142), la VUE SERVIE `vue_servie` (seul point d'entrée des lecteurs : série de référence, découpage antérieur tel que publié, raccords, douze mois sur la série, chroniques), l'invariant de l'agrégat (§2.3ter), le prédicat des douze mois glissants (régime cohérent ou retraitement cohérent, §2.4), l'ordre des périodes par la date de FIN (`ordre_des_periodes`, détenteur unique, §2.5), `premier_niveau_de` (détenteur unique partagé avec `ventilation.py`/`structure.py`), `identifier_jumeau_candidat`/`regime_a_change` (le dépôt jumeau, §5) et le signal d'acquisition significative (§4bis). Pur, aucun ticker ni seuil calé sur un cas réel — la tolérance est celle de `socle_comptes.tolerance_bouclage` |

## Cible → garde (réalisé)

| Invariant cible | Garant |
|---|---|
| Score/tier calculés, jamais fournis ; passage obligé | `check_provenance.py`, `check_synthesis_feed.py` |
| Nature dérivée (`metric` structuré ⟹ `mesure`) | `check_entry_nature.py` §7 (état persisté) |
| Datation : deux dates nommées, `source_date` dérivée, confusion fait/document INEXPRIMABLE (#79) | `check_datation.py` + `negatif_datation.sh` |
| L'exemple de sortie des consignes `search-worker`/`ingestion-agent` se valide contre `ProducedEntry`, au fichier ET en base (#121 — l'exemple portait `source_date` après la 045) | `check_prompts_exemples.py` (négatif : rejoué sur les fichiers d'avant correction et la base d'avant la 054, puis d'avant la 055 — `extraits`, #126) |
| Registre : standing par couple (source × nature) | `check_source_registry.py` |
| Feeds financiers : identité #43, datation #42, 3 états #44 | `check_edgar_feed.py`, `check_financials_feed.py`, `check_valuation_feed.py`, `check_base_rate_corpus.py` |
| Un ratio valide un CALCUL, jamais sa SIGNIFICATION : conversion FCF et ROIC ne se publient pas quand l'émetteur n'a ni bénéfice ni exploitation — le refus est PUBLIÉ (il supersede la ligne fausse), et « intrant absent » ne se confond pas avec « ratio non défini » | `check_financials_feed.py` §6 + `negatif_financials_feed.sh` |
| Le socle des comptes : périodes lues par leurs détenteurs, recette choisie période par période, un écart de bouclage PUBLIÉ jamais absorbé, jamais de zéro fabriqué, reclassement propre à l'émetteur motivé et sourcé, texte tamponné `mesure` (#115) | `check_socle_comptes.py` + `negatif_socle_comptes.sh` ; la publication (une pièce courante, idempotente, remplacée par un dépôt neuf, jointe au dossier) : `check_socle_persist.py` |
| La ventilation publiée (lot M2, roadmap V3 `11`) : classement d'un fait sur UN axe (qualificateurs neutres retirés, un axe en trop → sous-détail), raccord au total publié jamais recalculé ailleurs, douze mois glissants par l'identité d'`appariement_feed` (jamais un repli sur l'exercice), jamais de zéro fabriqué (`xsi:nil` ignoré), réplicabilité (aucun ticker/membre propre dans le code livré) | `check_ventilation_publiee.py` + `negatif_ventilation_publiee.sh` (fixtures NVDA/RVMD/JPM, copiées du réel) ; la publication (pièce courante, idempotente, remplacée, famille bancaire refusée NOMMÉ) : `check_ventilation_persist.py` + `negatif_ventilation_persist.sh` |
| Les ratios maison : capital moyen (jamais celui du seul jour de clôture), impôt négatif borné, capital négatif ⟹ aucun rendement, une perte ne se convertit pas, trois issues nommées jamais un zéro, version dans l'empreinte, texte tamponné `mesure` | `check_ratios_maison.py` + `negatif_ratios_maison.sh` ; capital employé, participations NVDA et bilan d'ouverture chez `check_socle_comptes.py` §12 ; [U] (ratio inconnu, unité) chez `check_frameworks_definitions.py` |
| Une formule d'appariement s'EXÉCUTE sur le dépôt : 4 refus nommés, ancre commune par cadrage, tier dérivé du déterminisme (#67/#72) | `check_appariement_feed.py` + `negatif_appariement_feed.sh` (le câblage amont est chez `check_collecte_executor.py` §11) |
| Actualité calculée à la lecture, jamais persistée | `check_actualite.py`, `check_material_events.py` |
| Une note flash ne remplace que la part `a_qualifier` d'un dépôt ; illisible, elle le laisse rouvert ; l'horloge la reçoit en paramètre REQUIS (#90) | `check_evenements.py` §7 + `negatif_evenements.sh` ; l'agent chez `check_note_flash.py` |
| Chaque question a sa propre horloge : un fait ne rouvre que les questions dont le référentiel déclare son type (#89) | `check_evenements.py` + `negatif_evenements.sh` ; le référentiel ([Q]/[R]) chez `check_frameworks_definitions.py` |
| Une pièce citée reste valable dans la DURÉE DE VIE de l'ingrédient qu'elle fonde (chiffre courant · historique qui se complète · description annuelle · jugement), sous l'interrupteur `fraicheur_par_duree_de_vie` (règle de fraîcheur, 2026-10-16, `duree_de_vie.py`) ; SUJET PAR SUJET (point 15, interrupteur `fraicheur_par_sujet`) : sur un même ingrédient seule la pièce la plus récente juge, les remplacées sont citées comme contexte ; une pièce non rattachée est son propre sujet | `check_duree_de_vie.py` + `negatif_duree_de_vie.sh` ; le référentiel (durée et cadence requises) chez `check_frameworks_definitions.py` |
| Un communiqué de résultats se LIT : non lu il rouvre large ; lu, il garde `resultats` et ajoute ce qu'il annonce de plus ; un communiqué mixte est scindé (comptes à leur clôture, annonces à leur date) | `check_evenements.py` §10 + `negatif_evenements.sh` ; la liste des dépôts à lire chez `check_note_flash_branchement.py` |
| Format des montants (détenteur unique) | `check_edgar_feed.py` §11, `check_financials_feed.py` §9 |
| search-worker ne qualifie pas sa propre source | `check_search_worker.py` |
| Une fiche du collecteur ne dit que ce que son document écrit : extraits littéraux vérifiés contre le texte rapporté par les outils (`citation.py`, détenteur unique partagé avec la note flash), lecture du collecteur rangée à part en interprétation B- (#126) | `check_search_worker.py` §11 + `negatif_search_worker.sh` |
| `fetch_url` : deux chemins, le domaine décide (live) | `check_fetch_live.py`, `check_fetch_relevance.py` |
| Le périmètre : régimes, transitions typées par les montants (recherche bornée), chronique (origine publie/passage), vue servie (#142), invariant de l'agrégat, prédicat des douze mois, ordre des périodes par la FIN, aucun autre module ne recalcule un premier niveau par période ni ne compare deux dépôts | `check_perimetre.py` + `negatif_perimetre.sh` (catalogue fictif `checks/fixtures/perimetre/`, plus un cas RÉEL figé NVDA) |
| Listing lisible des entries | `check_knowledge_entries_listing.py` |
| L'explorateur du dossier (lot B4f, roadmap V3 `16-lot-B4f-explorateur.md`) : état d'une pièce au jour de la lecture (en vigueur / remplacée, jamais stocké, #53), table des matières paginée, note en vigueur avec ses pièces, pièce ouverte (passages par `select_relevant` au-delà de 6000 caractères, #134), `rechercher` délégué à `query_knowledge` (détenteur unique, #22/#46, jamais une seconde fusion de signaux), citations = matière ∪ pièces ouvertes (`pieces_citables_effectif`), portée fermée sur le ticker (aucun `ticker_id` en argument du modèle, comme `make_query_knowledge_executor`) | `check_explorateur.py` (cas FICTIFS, aucun nom réel) + `negatif_explorateur.sh` |
