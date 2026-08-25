#!/usr/bin/env bash
# Reconstruit le dossier quartz/ (gitignored) : clone Quartz épinglé + applique notre config.
# À lancer une fois sur une nouvelle machine, avant build.sh. Idempotent.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d quartz ]; then
  git clone --depth 1 --branch v4.5.1 https://github.com/jackyzha0/quartz.git quartz
  rm -rf quartz/.git
fi

CFG=quartz/quartz.config.ts
sed -i 's/pageTitle: "Quartz 4"/pageTitle: "Base de connaissance"/'                       "$CFG"
sed -i 's/locale: "en-US"/locale: "fr-FR"/'                                               "$CFG"
sed -i 's#baseUrl: "quartz.jzhao.xyz"#baseUrl: "kb.jlmvpscode.duckdns.org"#'              "$CFG"
sed -i 's#ignorePatterns: \["private", "templates", ".obsidian"\]#ignorePatterns: ["private", "templates", ".obsidian", ".git", "**/*.base"]#' "$CFG"
# analytics plausible → null (site privé, pas de tracker externe)
perl -0pi -e 's/analytics: \{\s*provider: "plausible",\s*\},/analytics: null,/s'          "$CFG"

echo "quartz/ prêt (config appliquée). Étapes suivantes : cp .env.example .env && ./gen-auth.sh && ./build.sh && docker compose up -d"
