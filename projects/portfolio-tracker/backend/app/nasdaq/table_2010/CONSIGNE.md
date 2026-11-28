# Mission : relever le BPA dilué publié à l'époque, exercices 2010 à 2020

Tu fais une RECHERCHE documentaire, pas une analyse. Pour chaque société de ton lot et chaque exercice
2010, 2011, …, 2020, relève le **bénéfice net par action DILUÉ (part du groupe, IFRS)** tel qu'il a été
publié **dans les comptes de CET exercice** (communiqué des résultats annuels de l'exercice N, publié
début N+1, ou document de référence / rapport annuel / URD de l'exercice N).

## Règles (strictes)

1. **Le chiffre de l'exercice N vient du document de l'exercice N**, jamais du comparatif d'un document
   ultérieur (un comparatif est retraité : divisions, attributions gratuites, normes). Si seul un comparatif
   est trouvable, prends-le mais mets `"from_comparative": true` et le document d'où il vient.
2. **Dilué, IFRS, résultat net part du groupe** (activités poursuivies ET abandonnées incluses). Pas le BPA
   « courant », « ajusté », « récurrent », « hors éléments exceptionnels » (Pernod Ricard, Kering, Safran,
   Sanofi mettent l'ajusté en avant : prends l'IFRS). Si seul le BPA de base existe, prends-le avec
   `"basis": "base"`. Une perte s'écrit en négatif.
3. **Source = un document de la société** (site de la société, AMF, info-financiere.fr, ou une copie
   archive.org d'un document de la société). Les agrégateurs (Zonebourse/MarketScreener, Boursorama,
   macrotrends, Yahoo, Wikipédia…) sont INTERDITS comme source ; tu peux t'en servir pour trouver un lien. Exception : le PDF même d'un document de la société
   hébergé ailleurs (miroir, archive) est admis — `url` pointe alors sur ce PDF, et `note` le dit.
4. **Copie un extrait littéral** du document (≤ 200 caractères) qui contient le chiffre, tel qu'il
   apparaît (virgule décimale française comprise). C'est vérifié par programme : le nombre doit figurer
   dans l'extrait.
5. **N'invente rien, n'estime rien.** Introuvable après des recherches raisonnables (≈ 4 essais) →
   `"eps": null` et `"why"` dit ce que tu as essayé. Un trou honnête vaut mieux qu'un chiffre douteux.
6. Prédécesseurs : avant une fusion ou un changement de nom, relève la société dont les actions sont
   devenues celles d'aujourd'hui (Essilor International pour EssilorLuxottica avant 2018 ; GDF Suez pour
   Engie ; Unibail-Rodamco ; Peugeot SA pour Stellantis avant 2021 ; Technip, etc.) et écris son nom dans
   `"entity"`.
7. Exercice décalé (Pernod Ricard clôt au 30 juin) : `fy_end` = la vraie date de clôture.

## Sortie

Écris UN fichier JSON (chemin donné dans ta consigne), valide, de cette forme :

```json
{
  "AI.PA": [
    {"fy_end": "2019-12-31", "eps": 5.12, "cur": "EUR", "basis": "dilué", "entity": "Air Liquide",
     "published": "2020-02-14", "doc": "Communiqué résultats annuels 2019",
     "url": "https://…", "excerpt": "Bénéfice net par action dilué 5,12 €", "from_comparative": false,
     "note": null}
  ]
}
```

- `published` = date de publication du document lu (AAAA-MM-JJ ; à défaut le mois, AAAA-MM).
- `cur` = devise du chiffre publié (USD pour ArcelorMittal, STMicroelectronics…).
- `note` = toute particularité utile (changement de norme, retraitement signalé, scission, BPA « des
  activités poursuivies » seulement…). Une ligne par exercice 2010 à 2020, 11 lignes par société,
  même quand `eps` est null.

Avant de terminer : relis ton fichier avec `python3 -c "import json;d=json.load(open('…'));print({k:len(v) for k,v in d.items()})"`
et, pour chaque ligne, vérifie que le nombre figure dans l'extrait. Ta réponse finale : le nombre de
lignes trouvées / nulles par société, et les cas douteux en une ligne chacun. Pas de résumé de méthode.
