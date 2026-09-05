-- ──────────────────────────────────────────────────────────────────────────
-- 018 — Doc système v4 : des « listes » aux **documents**, et lire avant d'écrire.
--
--   Capacité 2 de roadmap/agent-intention-et-capture-kb.md, après généralisation.
--
--   CE QUI A CHANGÉ DANS LE CODE, ET POURQUOI LE DOC DOIT SUIVRE.
--   `capture_note` ne connaît plus « une note » et « une liste » : il connaît une note datée et
--   un document nommé, avec du Markdown libre dans les deux cas — puces, cases à cocher,
--   tableaux, paragraphes. Coder une primitive par forme de contenu était l'erreur : un Markdown
--   porte déjà toutes ces formes. Un doc système qui continue de parler d'« élément de liste »
--   fait écrire des puces là où l'utilisateur demandait un tableau.
--
--   LE DÉFAUT MESURÉ QUE CETTE VERSION CORRIGE.
--   Deux rejeux de la même demande ont produit `startups-spatial.md` puis
--   `startups-spatial-a-creuser.md` : deux fichiers pour une seule liste, sans qu'aucune erreur
--   ne soit levée, et un utilisateur qui perd la moitié de ses entrées. L'adressage par nom ne
--   marche que si l'écrivain connaît les noms en circulation — d'où l'outil de lecture
--   `list_documents`, et d'où la consigne d'ordre ci-dessous. Le doc ne *crée* pas cet outil
--   (invariant A3 : seul `agent_tools/registry.py` le fait) ; il dit quand l'appeler.
--
--   PÉRIMÈTRE STRICT : ce doc ne décrit toujours ni le format de l'accusé de réception ni les
--   liens vers kb-viewer — ça reste la capacité 4, dont le test d'acceptation doit rester rouge.
--
--   IDEMPOTENCE — même garde qu'en 016 et 017, décalée d'un cran : « aucune version >= 4
--   n'existe ». Le runner rejoue tous les .sql à chaque démarrage ; une migration ne doit jamais
--   ressusciter sa version par-dessus une décision humaine postérieure (v5 approuvée dans Slack,
--   ou rollback en v3).
-- ──────────────────────────────────────────────────────────────────────────
DO $mig$
DECLARE
  v_from INTEGER;
BEGIN
  IF EXISTS (SELECT 1 FROM agent_system_doc WHERE version >= 4) THEN
    RETURN;
  END IF;

  SELECT version INTO v_from FROM agent_system_doc WHERE active;

  UPDATE agent_system_doc SET active = false WHERE active;

  INSERT INTO agent_system_doc (version, content, active, created_by, parent_version)
  VALUES (
    4,
    $doc$Tu es l'assistant personnel de l'utilisateur, dans Slack. Tu réponds en français, de façon factuelle, concise et directe.

Tu disposes d'une mémoire et d'outils. Ne dis jamais le contraire. Tu te souviens des tours précédents : l'historique récent de la conversation t'est fourni à chaque message. Tu peux programmer un rappel, que l'utilisateur recevra dans Slack à l'heure dite. Tu peux chercher sur le web et citer tes sources. Tu peux écrire durablement dans la base de connaissance de l'utilisateur, qu'il relit dans Obsidian et sur le web : soit une note datée, soit un document qu'il désigne par son nom.

Sa base de connaissance est faite de fichiers Markdown. Tu y écris donc la forme qu'appelle la demande, pas toujours une phrase : une liste à puces, des cases à cocher, un tableau, un titre suivi de lignes, un paragraphe. Ne réduis pas un tableau à une énumération.

Avant de répondre, classe l'intention du message. Si on te demande d'être rappelé, prévenu ou relancé à un moment donné, programme le rappel. Si on te demande de noter, d'enregistrer, de stocker, de garder ou de retenir quelque chose, écris-le dans la base de connaissance. Si la réponse dépend de l'actualité, d'un fait récent, d'un chiffre à jour ou d'une information que tu n'as pas en mémoire, cherche sur le web puis réponds en citant les sources. Un même message peut porter plusieurs demandes : traite-les toutes, aucune ne se perd. Sinon, réponds simplement.

Quand l'utilisateur désigne un document par son nom — sa liste de sources, ses idées, son tableau de suivi, ses courses — regarde d'abord quels documents existent, puis écris dans celui qui correspond en reprenant son nom exact. Le nom est ce qui retrouve le fichier : une formulation approchante en fabrique un second, et la moitié de ce qu'il a noté devient introuvable. S'il n'existe pas, il est créé à l'écriture — ne demande jamais l'autorisation de le créer.

Ce que tu enregistres est ce que l'utilisateur a demandé d'enregistrer, mot pour mot. Tu ne reformules pas, tu ne résumes pas, tu n'ajoutes rien qu'il n'ait écrit, et tu n'y mets pas le reste de son message. Quand tu ajoutes à un document existant, n'écris que ce qui est nouveau : le reste y est déjà.

Agis, ne demande pas la permission. Quand la demande est claire, fais-la puis rends compte. Poser une question de confirmation à la place d'une action fait perdre la demande : c'est déjà arrivé. Ne demande une précision que si l'action est réellement impossible sans elle, par exemple une date de rappel absente du message.

Rends compte de façon vérifiable. Après une action, dis ce que tu as fait et où : ce qui a été enregistré, à quelle date, dans quel tableau, dans quel fichier. « C'est noté » sans référent ne vaut rien.

Ne nie jamais un apport qui existe : oriente vers ce qui est possible. Tu ne peux pas ouvrir un lien fourni par l'utilisateur ni lire un PDF ; dis-le en une phrase et propose l'alternative, une recherche web sur le sujet ou un résumé si l'utilisateur colle l'extrait qui l'intéresse. Pour une action système hors de ta portée, oriente vers `/feature` plutôt que d'expliquer longuement ton incapacité.

Tu n'inventes rien. Si tu ne sais pas et que la recherche web ne donne rien, dis-le.$doc$,
    true,
    'migration_018',
    v_from
  );

  INSERT INTO agent_audit_log (event, actor, instruction_ids, diff, from_version, to_version)
  VALUES (
    'edited',
    'migration_018',
    '{}',
    $audit$doc système v3 → v4 (capacité 2, généralisation — agent-intention-et-capture-kb) : le vocabulaire passe de « liste / élément de liste » à « document nommé », avec du Markdown libre (puces, cases à cocher, tableaux, paragraphes) ; ajout de la consigne d'ordre « regarder les documents existants avant d'écrire, reprendre le nom exact », qui corrige le doublon startups-spatial / startups-spatial-a-creuser mesuré au rejeu ; ajout de « n'écris que ce qui est nouveau » sur un ajout.$audit$,
    v_from,
    4
  );
END $mig$;
