FROM pgvector/pgvector:pg16
RUN apt-get update && apt-get -y --no-install-recommends upgrade && rm -rf /var/lib/apt/lists/*
# gosu (binaire Go non reconstruit, stdlib périmée) remplacé par setpriv (util-linux) : même contrat `gosu user cmd…`
RUN rm -f /usr/local/bin/gosu
RUN printf '#!/bin/sh\nu="$1"; shift\nexport HOME="$(getent passwd "$u" | cut -d: -f6)"\nexec setpriv --reuid="$u" --regid="$u" --init-groups -- "$@"\n' > /usr/local/bin/gosu && chmod 755 /usr/local/bin/gosu
