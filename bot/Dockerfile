# =============================================================================
# Bot Discord - Multi-stage Dockerfile
# Python 3.12 avec accès Docker socket pour la gestion des conteneurs
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Base - Image commune pour dev et prod
# -----------------------------------------------------------------------------
FROM python:3.12-slim as base

# Variables d'environnement Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Dépendances système nécessaires
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Pour Docker CLI
    curl \
    gnupg \
    lsb-release \
    ca-certificates \
    # Pour les builds Python
    gcc \
    libffi-dev \
    # Pour PostgreSQL
    libpq-dev \
    # Pour git operations
    git \
    # Utilitaires
    procps \
    && rm -rf /var/lib/apt/lists/*

# Installation de Docker CLI (pour communiquer avec le Docker daemon)
RUN install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
    $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin \
    && rm -rf /var/lib/apt/lists/*

# Création de l'utilisateur non-root
RUN groupadd --gid 1000 botuser \
    && useradd --uid 1000 --gid 1000 --shell /bin/bash --create-home botuser \
    # Ajouter au groupe docker pour accès au socket
    && groupadd -f docker \
    && usermod -aG docker botuser

WORKDIR /app

# -----------------------------------------------------------------------------
# Stage 2: Dependencies - Installation des dépendances Python
# -----------------------------------------------------------------------------
FROM base as dependencies

# Copier les fichiers de dépendances
COPY requirements.txt pyproject.toml ./

# Installation des dépendances Python
RUN pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.txt

# -----------------------------------------------------------------------------
# Stage 3: Development - Configuration pour le développement
# -----------------------------------------------------------------------------
FROM dependencies as development

# Variables d'environnement pour le développement
ENV ENVIRONMENT=development \
    DEBUG=true \
    LOG_LEVEL=DEBUG

# Installation des dépendances de développement supplémentaires
RUN pip install \
    pytest \
    pytest-asyncio \
    pytest-cov \
    black \
    isort \
    flake8 \
    mypy \
    ipython \
    debugpy

# Copier le code source
COPY --chown=botuser:botuser . .

# Créer les répertoires nécessaires
RUN mkdir -p /app/logs /app/data /app/backups \
    && chown -R botuser:botuser /app

# Port pour le debugger Python
EXPOSE 5678

# Changer vers l'utilisateur non-root
USER botuser

# Commande de développement avec rechargement automatique
CMD ["python", "-m", "debugpy", "--listen", "0.0.0.0:5678", "-m", "src.main"]

# -----------------------------------------------------------------------------
# Stage 4: Production - Image optimisée pour la production
# -----------------------------------------------------------------------------
FROM dependencies as production

# Variables d'environnement pour la production
ENV ENVIRONMENT=production \
    DEBUG=false \
    LOG_LEVEL=INFO

# Copier uniquement le code source nécessaire
COPY --chown=botuser:botuser src/ ./src/
COPY --chown=botuser:botuser templates/ ./templates/

# Créer les répertoires nécessaires
RUN mkdir -p /app/logs /app/data /app/backups \
    && chown -R botuser:botuser /app

# Nettoyage des fichiers inutiles
RUN find /app -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true \
    && find /app -type f -name "*.pyc" -delete 2>/dev/null || true \
    && find /app -type f -name "*.pyo" -delete 2>/dev/null || true

# Changer vers l'utilisateur non-root
USER botuser

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import asyncio; from src.core.health import check_health; asyncio.run(check_health())" || exit 1

# Commande de production
CMD ["python", "-m", "src.main"]
