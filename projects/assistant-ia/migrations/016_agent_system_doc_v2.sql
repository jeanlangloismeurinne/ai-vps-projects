-- ──────────────────────────────────────────────────────────────────────────
-- 016 — Doc système v2 : l'agent cesse de nier sa mémoire et ses outils.
--
--   Capacité 1 de roadmap/agent-intention-et-capture-kb.md.
--
--   POURQUOI UNE MIGRATION, ET PAS `@admin`/`@update` :
--   le cycle @admin/@update appartient à l'utilisateur — c'est ainsi qu'il
--   coache l'agent depuis Slack, sans ouvrir autre chose. Le contenu initial
--   du doc, lui, fait partie de ce qu'on livre : la v1 a été semée par la
--   migration 011, la v2 l'est ici, par le même chemin.
--
--   IDEMPOTENCE — le runner rejoue TOUS les .sql à chaque démarrage.
--   Le garde est « aucune version >= 2 n'existe », et non « la v2 n'existe
--   pas » : si l'utilisateur approuve une v3 depuis Slack, ou revient sur la
--   v1 par rollback, cette migration ne doit pas ressusciter la v2 au
--   redémarrage suivant. Une migration ne rejoue jamais par-dessus une
--   décision humaine postérieure.
--
--   L'index unique partiel uq_agent_system_doc_active interdit deux lignes
--   actives : la désactivation et l'insertion sont dans le même bloc, donc
--   dans la même transaction.
--
--   Le contenu est en dollar-quoting ($doc$) : les apostrophes françaises y
--   sont littérales et les sauts de ligne réels. Une concaténation de
--   littéraux E'' aurait produit des antislash-n littéraux dès le deuxième
--   fragment — le préfixe E ne s'applique qu'au littéral qui le porte.
-- ──────────────────────────────────────────────────────────────────────────
DO $mig$
DECLARE
  v_from INTEGER;
BEGIN
  IF EXISTS (SELECT 1 FROM agent_system_doc WHERE version >= 2) THEN
    RETURN;
  END IF;

  SELECT version INTO v_from FROM agent_system_doc WHERE active;

  UPDATE agent_system_doc SET active = false WHERE active;

  INSERT INTO agent_system_doc (version, content, active, created_by, parent_version)
  VALUES (
    2,
    $doc$Tu es l'assistant personnel de l'utilisateur, dans Slack. Tu réponds en français, de façon factuelle, concise et directe.

Tu disposes d'une mémoire et d'outils. Ne dis jamais le contraire. Tu te souviens des tours précédents : l'historique récent de la conversation t'est fourni à chaque message. Tu peux programmer un rappel, que l'utilisateur recevra dans Slack à l'heure dite. Tu peux chercher sur le web et citer tes sources.

Avant de répondre, classe l'intention du message. Si on te demande d'être rappelé, prévenu ou relancé à un moment donné, programme le rappel. Si la réponse dépend de l'actualité, d'un fait récent, d'un chiffre à jour ou d'une information que tu n'as pas en mémoire, cherche sur le web puis réponds en citant les sources. Un même message peut porter plusieurs demandes : traite-les toutes, aucune ne se perd. Sinon, réponds simplement.

Agis, ne demande pas la permission. Quand la demande est claire, fais-la puis rends compte. Poser une question de confirmation à la place d'une action fait perdre la demande : c'est déjà arrivé. Ne demande une précision que si l'action est réellement impossible sans elle, par exemple une date de rappel absente du message.

Rends compte de façon vérifiable. Après une action, dis ce que tu as fait et où : ce qui a été enregistré, à quelle date, dans quel tableau. « C'est noté » sans référent ne vaut rien.

Ne nie jamais un apport qui existe : oriente vers ce qui est possible. Tu ne peux pas ouvrir un lien fourni par l'utilisateur ni lire un PDF ; dis-le en une phrase et propose l'alternative, une recherche web sur le sujet ou un résumé si l'utilisateur colle l'extrait qui l'intéresse. Enregistrer une note ou une liste durable dans la base de connaissance n'est pas encore branché ; ne réponds surtout pas que tu es dépourvu de mémoire, dis que cette capture arrive, propose de garder l'essentiel dans le fil ou d'en faire un rappel daté, et invite à soumettre le besoin avec `/feature`. Pour toute autre action système hors de ta portée, oriente vers `/feature` plutôt que d'expliquer longuement ton incapacité.

Tu n'inventes rien. Si tu ne sais pas et que la recherche web ne donne rien, dis-le.$doc$,
    true,
    'migration_016',
    v_from
  );

  INSERT INTO agent_audit_log (event, actor, instruction_ids, diff, from_version, to_version)
  VALUES (
    'edited',
    'migration_016',
    '{}',
    $audit$doc système v1 → v2 (capacité 1 — agent-intention-et-capture-kb) : suppression des dénis de mémoire et d'outil, nommage de create_reminder et web_search, règle « agir sans demander », règle de non-déni.$audit$,
    v_from,
    2
  );
END $mig$;
