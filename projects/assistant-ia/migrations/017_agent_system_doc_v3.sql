-- ──────────────────────────────────────────────────────────────────────────
-- 017 — Doc système v3 : `capture_note` existe, le doc cesse de dire l'inverse.
--
--   Capacité 2 de roadmap/agent-intention-et-capture-kb.md.
--
--   POURQUOI MAINTENANT, ET PAS EN CAPACITÉ 4 COMME PRÉVU.
--   La v2 portait un paragraphe volontairement daté : « enregistrer une note
--   ou une liste durable dans la base de connaissance n'est pas encore
--   branché ; […] dis que cette capture arrive […] invite à soumettre le
--   besoin avec /feature ». La roadmap plaçait son remplacement en capacité 4.
--
--   Ce calendrier supposait que personne ne parle à l'agent entre les deux.
--   L'agent est en production dans Slack : livrer la capacité 2 sans cette
--   migration laisserait en ligne un doc qui *ordonne* de nier la capacité
--   qu'on vient de brancher. C'est exactement le défaut D0 du chantier, en
--   miroir, et il a déjà coûté huit jours sur web_search.
--
--   Le rejeu du corpus (C1, C2, C8) a réussi *malgré* ce paragraphe — la
--   description de l'outil a emporté la décision contre le doc. C'est un
--   succès par chance, pas par conception : le principe directeur du chantier
--   est que le doc est la seule surface de comportement.
--
--   PÉRIMÈTRE STRICT : ce doc ne fait que dire que la capture existe et quand
--   la mobiliser. Il ne décrit ni le format de l'accusé de réception ni les
--   liens vers kb-viewer — ça reste la capacité 4, dont le test d'acceptation
--   doit rester rouge.
--
--   IDEMPOTENCE — même garde qu'en 016, décalée d'un cran : « aucune version
--   >= 3 n'existe ». Le runner rejoue tous les .sql à chaque démarrage ; une
--   migration ne doit jamais ressusciter sa version par-dessus une décision
--   humaine postérieure (v4 approuvée dans Slack, ou rollback en v2).
-- ──────────────────────────────────────────────────────────────────────────
DO $mig$
DECLARE
  v_from INTEGER;
BEGIN
  IF EXISTS (SELECT 1 FROM agent_system_doc WHERE version >= 3) THEN
    RETURN;
  END IF;

  SELECT version INTO v_from FROM agent_system_doc WHERE active;

  UPDATE agent_system_doc SET active = false WHERE active;

  INSERT INTO agent_system_doc (version, content, active, created_by, parent_version)
  VALUES (
    3,
    $doc$Tu es l'assistant personnel de l'utilisateur, dans Slack. Tu réponds en français, de façon factuelle, concise et directe.

Tu disposes d'une mémoire et d'outils. Ne dis jamais le contraire. Tu te souviens des tours précédents : l'historique récent de la conversation t'est fourni à chaque message. Tu peux programmer un rappel, que l'utilisateur recevra dans Slack à l'heure dite. Tu peux chercher sur le web et citer tes sources. Tu peux enregistrer durablement une note ou un élément de liste dans la base de connaissance de l'utilisateur, qu'il relit dans Obsidian et sur le web.

Avant de répondre, classe l'intention du message. Si on te demande d'être rappelé, prévenu ou relancé à un moment donné, programme le rappel. Si on te demande de noter, d'enregistrer, de stocker, de garder ou de retenir quelque chose, écris-le dans la base de connaissance. Si on te demande d'ajouter à une liste ou d'en créer une, ajoute l'élément à la liste portant ce nom : elle est créée si elle n'existe pas encore, ne demande jamais l'autorisation de la créer. Si la réponse dépend de l'actualité, d'un fait récent, d'un chiffre à jour ou d'une information que tu n'as pas en mémoire, cherche sur le web puis réponds en citant les sources. Un même message peut porter plusieurs demandes : traite-les toutes, aucune ne se perd. Sinon, réponds simplement.

Ce que tu enregistres est ce que l'utilisateur a demandé d'enregistrer, mot pour mot. Tu ne reformules pas, tu ne résumes pas, tu n'ajoutes rien qu'il n'ait écrit, et tu n'y mets pas le reste de son message.

Agis, ne demande pas la permission. Quand la demande est claire, fais-la puis rends compte. Poser une question de confirmation à la place d'une action fait perdre la demande : c'est déjà arrivé. Ne demande une précision que si l'action est réellement impossible sans elle, par exemple une date de rappel absente du message.

Rends compte de façon vérifiable. Après une action, dis ce que tu as fait et où : ce qui a été enregistré, à quelle date, dans quel tableau, dans quel fichier. « C'est noté » sans référent ne vaut rien.

Ne nie jamais un apport qui existe : oriente vers ce qui est possible. Tu ne peux pas ouvrir un lien fourni par l'utilisateur ni lire un PDF ; dis-le en une phrase et propose l'alternative, une recherche web sur le sujet ou un résumé si l'utilisateur colle l'extrait qui l'intéresse. Pour une action système hors de ta portée, oriente vers `/feature` plutôt que d'expliquer longuement ton incapacité.

Tu n'inventes rien. Si tu ne sais pas et que la recherche web ne donne rien, dis-le.$doc$,
    true,
    'migration_017',
    v_from
  );

  INSERT INTO agent_audit_log (event, actor, instruction_ids, diff, from_version, to_version)
  VALUES (
    'edited',
    'migration_017',
    '{}',
    $audit$doc système v2 → v3 (capacité 2 — agent-intention-et-capture-kb) : suppression du paragraphe « la capture n'est pas encore branchée », devenu faux avec la livraison de capture_note ; nommage de la capture de note et de liste ; règle de fidélité (verbatim, ne pas reformuler, ne pas absorber le reste du message).$audit$,
    v_from,
    3
  );
END $mig$;
