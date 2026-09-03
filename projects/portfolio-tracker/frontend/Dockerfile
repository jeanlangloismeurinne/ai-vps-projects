FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .

# Les NEXT_PUBLIC_* sont inlinés par Next.js AU BUILD, pas lus au runtime : sans elles ici, tout
# le frontend appellerait le défaut `http://localhost:8050` depuis le navigateur — panne totale et
# silencieuse. Fournies en build args par docker-compose.yml (qui les lit dans `.env`).
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_DUST_STREAMING
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_DUST_STREAMING=$NEXT_PUBLIC_DUST_STREAMING

RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN apk add --no-cache curl
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 8051
ENV PORT=8051
CMD ["node", "server.js"]
