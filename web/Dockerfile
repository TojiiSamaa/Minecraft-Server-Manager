# =============================================================================
# Web Dashboard - Multi-stage Dockerfile
# Next.js 14 avec mode standalone pour production optimisée
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Base - Image Node.js commune
# -----------------------------------------------------------------------------
FROM node:20-alpine AS base

# Activer corepack pour pnpm (optionnel mais recommandé)
RUN corepack enable

# Installer les dépendances système nécessaires
RUN apk add --no-cache \
    libc6-compat \
    curl \
    && rm -rf /var/cache/apk/*

WORKDIR /app

# -----------------------------------------------------------------------------
# Stage 2: Dependencies - Installation des dépendances
# -----------------------------------------------------------------------------
FROM base AS deps

# Fichiers de configuration des dépendances
COPY package.json package-lock.json* yarn.lock* pnpm-lock.yaml* ./

# Installation des dépendances selon le gestionnaire de paquets disponible
RUN \
    if [ -f yarn.lock ]; then \
        yarn --frozen-lockfile; \
    elif [ -f package-lock.json ]; then \
        npm ci; \
    elif [ -f pnpm-lock.yaml ]; then \
        corepack enable pnpm && pnpm i --frozen-lockfile; \
    else \
        npm install; \
    fi

# -----------------------------------------------------------------------------
# Stage 3: Development - Configuration pour le développement
# -----------------------------------------------------------------------------
FROM base AS development

# Variables d'environnement pour le développement
ENV NODE_ENV=development \
    NEXT_TELEMETRY_DISABLED=1

# Copier les dépendances installées
COPY --from=deps /app/node_modules ./node_modules

# Copier le code source
COPY . .

# Créer un utilisateur non-root
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs \
    && chown -R nextjs:nodejs /app

USER nextjs

# Port de développement
EXPOSE 3000

# Variables d'environnement Next.js
ENV PORT=3000 \
    HOSTNAME="0.0.0.0"

# Commande de développement avec hot-reload
CMD ["npm", "run", "dev"]

# -----------------------------------------------------------------------------
# Stage 4: Builder - Compilation de l'application
# -----------------------------------------------------------------------------
FROM base AS builder

# Variables d'environnement pour le build
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

WORKDIR /app

# Copier les dépendances
COPY --from=deps /app/node_modules ./node_modules

# Copier tout le code source
COPY . .

# Variables d'environnement de build (peuvent être override)
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_WS_URL
ARG NEXT_PUBLIC_APP_NAME="Minecraft Dashboard"

ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL} \
    NEXT_PUBLIC_WS_URL=${NEXT_PUBLIC_WS_URL} \
    NEXT_PUBLIC_APP_NAME=${NEXT_PUBLIC_APP_NAME}

# Build de l'application en mode standalone
RUN \
    if [ -f yarn.lock ]; then \
        yarn build; \
    elif [ -f package-lock.json ]; then \
        npm run build; \
    elif [ -f pnpm-lock.yaml ]; then \
        corepack enable pnpm && pnpm build; \
    else \
        npm run build; \
    fi

# -----------------------------------------------------------------------------
# Stage 5: Production - Image finale optimisée
# -----------------------------------------------------------------------------
FROM base AS production

# Variables d'environnement pour la production
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

WORKDIR /app

# Créer un utilisateur non-root pour la sécurité
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

# Copier les fichiers publics
COPY --from=builder /app/public ./public

# Configurer les permissions pour le cache de prérendu
RUN mkdir .next \
    && chown nextjs:nodejs .next

# Copier le build standalone
# Le mode standalone inclut uniquement les fichiers nécessaires
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Passer à l'utilisateur non-root
USER nextjs

# Port d'exposition
EXPOSE 3000

# Variables d'environnement runtime
ENV PORT=3000 \
    HOSTNAME="0.0.0.0"

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:3000/api/health || exit 1

# Commande de production - utilise le serveur standalone
CMD ["node", "server.js"]
