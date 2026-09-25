---
id: principes-fondateurs-v3
status: actif
created: 2026-09-25
project: portfolio-tracker
role: >
  Les principes de CONDUITE du chantier V3, posés par l'utilisateur. À lire au début de CHAQUE
  conversation sur portfolio-tracker, avant le fichier de reprise. Ils disent comment on DÉCIDE et
  comment on DEMANDE ; la constitution technique reste `principe-directeur.md`.
---

# Principes fondateurs — V3

> **Lu à chaque reprise, avant `00-REPRISE.md`.** Ces deux principes s'appliquent à toute
> décision et à toute question adressée à l'utilisateur pendant la construction de la V3.
> En cas de doute entre une bonne pratique technique et ces principes, **ce sont eux qui
> tranchent la façon de poser le problème** ; la technique décide seulement de la façon de
> l'implémenter.

## 1. Toute demande d'arbitrage se formule en termes MÉTIER

On pose à l'utilisateur les questions qu'un gérant ou un comité d'investissement se pose, jamais
des questions d'ingénieur ni de spécification fonctionnelle.

- **Pas de jargon technique** dans la question : ni nom de table, de champ, de fonction, de
  migration, ni « état », « enum », « nullable », « endpoint ». Le technique reste dans le code et
  dans les notes d'implémentation.
- **Pas non plus de jargon fonctionnel abstrait** (« quel comportement du module X ? »). On décrit
  la **situation d'investissement** et ses conséquences concrètes.
- Chaque option présentée dit **ce qu'elle change pour le fonds** : quelle information le comité
  verrait, quelle décision elle permettrait ou empêcherait, quel risque d'erreur elle crée.
- Illustrer par **un cas réel du portefeuille** (RVMD, NVDA, MSFT…) plutôt que par un schéma de
  données.

**Exemple.**
- ❌ « Faut-il exclure `sans_objet` du dénominateur de `qualite_info` ou le compter à 0 ? »
- ✅ « Pour une biotech sans chiffre d'affaires, la question "le capital employé rapporte-t-il plus
  que son coût ?" n'a pas d'objet. Est-ce que ça doit faire baisser la note de qualité du dossier,
  ou est-ce qu'on retire simplement cette question de la note ? »

## 2. Chaque décision s'éclaire par la pratique d'un VRAI fonds d'investissement

Avant de trancher — ou de proposer des options — on se demande : **comment un fonds
d'investissement réel (gérant, analystes, comité, contrôle des risques, middle-office) traite-t-il
cette situation ?** Et on s'en sert pour orienter la conception.

- **Chercher l'équivalent dans le métier** : qui, dans un fonds, porterait cette responsabilité
  (analyste, gérant, comité, risk, back-office) ? Quel document ou quelle procédure l'encadre
  (note d'analyse, mémo de comité, procès-verbal, piste d'audit, valorisation au dernier cours
  coté) ?
- **Écrire cette référence explicitement** dans la proposition : « un fonds ferait X, parce que Y ».
  Si on s'en écarte, dire pourquoi (contrainte du système, coût, périmètre actuel).
- **Quand la pratique varie d'un fonds à l'autre**, présenter les deux ou trois pratiques
  courantes, avec leur logique, et recommander celle qui correspond au style du fonds (investissement
  fondamental, long terme, concentré).
- Ce qu'un vrai fonds **n'automatiserait jamais** (admettre une nouvelle source, décider qu'un fait
  est remplacé, prendre la décision d'investissement) reste un acte humain dans le système.

**Arbitrages déjà rendus de cette façon** (pour le ton et le niveau, pas pour être relus en détail) :
- *Le cours coté et sa date* (2026-09-23, conv. #81) : quand le dernier cours manque, un fonds
  **valorise au dernier cours coté et note cette date** ; il ne laisse pas une ligne sans valeur.
- *Les deux dates d'une pièce* (2026-09-23, conv. #79) : on retient la date du **dernier fait
  constaté**, pas celle du dernier document reçu ; une prévision de la direction est une
  information du jour où elle est **annoncée**.
- *La note de qualité d'un dossier* (2026-09-25, conv. #82) : une question sans objet **sort** de
  la note ; une information périmée ne fonde pas une décision du jour mais **reste archivée** ; la
  solidité des sources est affichée **à côté** de la note, jamais fondue dedans.

## Comment les appliquer en pratique

1. **Avant d'écrire une question à l'utilisateur** : la relire en se demandant si un membre du
   comité d'investissement la comprendrait sans connaître le code. Sinon, la reformuler.
2. **Dans toute proposition de conception** : une ligne « Ce que ferait un vrai fonds », avant les
   options.
3. **Consigner les arbitrages rendus** dans le fichier de reprise et, s'ils sont durables, dans une
   convention du `CLAUDE.md` projet — en rappelant la **logique de fonds** qui les a fondés, pas
   seulement la règle technique qui en résulte.
