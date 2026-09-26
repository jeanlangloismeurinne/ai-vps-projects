# Chantier dans `newsletter-summary` : alias de transmission

Ce chantier se fait **dans le projet `newsletter-summary`**, avant le lot 1 de
strategic-intelligence (ticket L1-05). Il est décrit ici parce qu'il n'existe que pour ce projet ;
il sera recopié dans la roadmap de newsletter-summary au moment de l'exécuter.

## 1. Constat (lecture du code le 2026-09-26)

Un alias de newsletter-summary a aujourd'hui **une seule action** : faire résumer le courriel
par DeepInfra puis envoyer une réponse (digest ou réponse à l'expéditeur). Les différences entre
alias tiennent dans des colonnes (`frequency`, `recipient`, `open_senders`, `allowed_senders`,
`presentation`), pas dans le code — c'est la bonne base.

Tel quel, un alias `terrain@` enverrait les notes de l'utilisateur à un LLM externe et les
recopierait dans un courriel : contraire à D3.

## 2. Évolution demandée

Ajouter à `Alias` une **action** :

| Colonne | Valeurs | Défaut |
|---|---|---|
| `action` | `summarize` (comportement actuel) · `forward` | `summarize` |
| `forward_target` | identifiant de destination (`strategic-intelligence:veille`, `strategic-intelligence:terrain`) | NULL |
| `ack` | `none` · `receipt` (accusé sans reprise du contenu) | `none` |

Comportement de `forward` :
1. Contrôles existants inchangés : correspondance exacte de l'adresse, liste des expéditeurs
   autorisés (vide = personne), statuts, plafond journalier.
2. **Aucun appel LLM, aucune écriture dans la KB de newsletter-summary.**
3. Récupération du corps complet par le chemin existant (gateway `/v1/inbound/email/:id`,
   le webhook Resend ne porte pas le corps), pièces jointes comprises.
4. `POST` vers strategic-intelligence (réseau interne `coolify`, jamais par Internet) :
   `/internal/inbound/email` avec en-tête `X-Internal-Api-Key`, corps JSON
   `{alias, message_id, from, to, subject, received_at, html, text, attachments:[{filename, content_type, base64}]}`.
   Réponse `202` = pris en charge ; tout autre code = nouvelle tentative (3 fois), puis `failed`
   avec erreur nommée.
5. `ack = receipt` : un courriel « Note reçue le … » **sans reprise du contenu ni de l'objet**.
6. Le courriel n'est pas conservé en clair dans newsletter-summary au-delà de la transmission
   réussie (statut `forwarded`, corps purgé).

## 3. Les deux alias

| Alias | `action` | Expéditeurs | Accusé | Côté strategic-intelligence |
|---|---|---|---|---|
| `veille@` | `forward` → `strategic-intelligence:veille` | **ouvert** (les newsletters viennent d'expéditeurs variés) ; plafond journalier dédié | aucun | gabarit `newsletter_email`, `green`, une instance par expéditeur créée en `pending` |
| `terrain@` | `forward` → `strategic-intelligence:terrain` | **adresses de l'utilisateur uniquement** | `receipt` | gabarit `field_note_email`, `red`, chiffré à l'arrivée |

Le flux newsletter personnel existant (alias par défaut) n'est **pas** modifié et n'alimente pas
strategic-intelligence (D8).

## 4. Points à vérifier au moment du chantier

- L'hypothèse « Resend accepte n'importe quel local-part » n'est pas encore vérifiée en
  production (mémoire du projet) : envoyer un vrai courriel à `veille@` et `terrain@` avant de
  conclure.
- Plafond du gateway (60 courriels/jour pour le client newsletter-summary) : `forward` n'envoie
  qu'un accusé pour `terrain@` ; aucun envoi pour `veille@`. Pas d'effet sur le digest existant.
- Tests : un courriel `terrain@` d'un expéditeur non autorisé est `rejected` sans transmission ;
  un courriel `forward` ne déclenche aucun appel DeepInfra (vérifié par le journal du client).
