"""Utilitaires pour masquer les donnees sensibles dans les logs."""
import re
from urllib.parse import urlparse, urlunparse
from typing import Any, Dict


# Patterns pour detecter les donnees sensibles
SENSITIVE_PATTERNS = [
    (re.compile(r'(password["\']?\s*[:=]\s*["\']?)[^"\'\s]+', re.IGNORECASE), r'\1****'),
    (re.compile(r'(token["\']?\s*[:=]\s*["\']?)[^"\'\s]+', re.IGNORECASE), r'\1****'),
    (re.compile(r'(secret["\']?\s*[:=]\s*["\']?)[^"\'\s]+', re.IGNORECASE), r'\1****'),
    (re.compile(r'(api_key["\']?\s*[:=]\s*["\']?)[^"\'\s]+', re.IGNORECASE), r'\1****'),
    (re.compile(r'(authorization["\']?\s*[:=]\s*["\']?)[^"\'\s]+', re.IGNORECASE), r'\1****'),
]

# Cles connues comme sensibles dans les dictionnaires
SENSITIVE_KEYS = {
    'password', 'passwd', 'pwd', 'secret', 'token', 'api_key', 'apikey',
    'authorization', 'auth', 'credentials', 'private_key', 'privatekey',
    'access_token', 'refresh_token', 'client_secret', 'database_url',
    'redis_url', 'rcon_password', 'discord_token', 'nextauth_secret',
}


def sanitize_url(url: str) -> str:
    """
    Masque les credentials dans une URL.

    Exemple:
        postgresql://user:password123@localhost/db
        -> postgresql://user:****@localhost/db
    """
    if not url:
        return url

    try:
        parsed = urlparse(url)
        if parsed.password:
            # Reconstruire le netloc avec le mot de passe masque
            if parsed.username:
                netloc = f"{parsed.username}:****@{parsed.hostname}"
            else:
                netloc = f"****@{parsed.hostname}"

            if parsed.port:
                netloc += f":{parsed.port}"

            return urlunparse(parsed._replace(netloc=netloc))
        return url
    except Exception:
        # Si le parsing echoue, retourner l'URL telle quelle
        return url


def sanitize_string(text: str) -> str:
    """
    Masque les donnees sensibles dans une chaine de caracteres.
    """
    if not text:
        return text

    result = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        result = pattern.sub(replacement, result)

    return result


def sanitize_dict(data: Dict[str, Any], depth: int = 0, max_depth: int = 10) -> Dict[str, Any]:
    """
    Masque recursivement les donnees sensibles dans un dictionnaire.
    """
    if depth > max_depth:
        return data

    result = {}
    for key, value in data.items():
        key_lower = key.lower()

        # Masquer les valeurs des cles sensibles
        if key_lower in SENSITIVE_KEYS:
            if isinstance(value, str) and value:
                result[key] = "****"
            elif value is not None:
                result[key] = "****"
            else:
                result[key] = value

        # Traiter les URLs
        elif 'url' in key_lower and isinstance(value, str):
            result[key] = sanitize_url(value)

        # Recursion pour les dictionnaires imbriques
        elif isinstance(value, dict):
            result[key] = sanitize_dict(value, depth + 1, max_depth)

        # Recursion pour les listes
        elif isinstance(value, list):
            result[key] = [
                sanitize_dict(item, depth + 1, max_depth) if isinstance(item, dict)
                else sanitize_url(item) if isinstance(item, str) and 'url' in key_lower
                else item
                for item in value
            ]

        # Masquer les chaines qui ressemblent a des secrets
        elif isinstance(value, str):
            result[key] = sanitize_string(value)

        else:
            result[key] = value

    return result


def sanitize_for_logging(value: Any) -> Any:
    """
    Point d'entree principal pour sanitizer n'importe quelle valeur pour les logs.
    """
    if isinstance(value, str):
        # Verifier si c'est une URL
        if '://' in value:
            return sanitize_url(value)
        return sanitize_string(value)

    elif isinstance(value, dict):
        return sanitize_dict(value)

    elif isinstance(value, (list, tuple)):
        return [sanitize_for_logging(item) for item in value]

    return value


class SanitizedLoggerAdapter:
    """
    Adaptateur de logger qui sanitize automatiquement les messages.

    Usage:
        logger = SanitizedLoggerAdapter(logging.getLogger(__name__))
        logger.info("Connexion DB: %s", database_url)  # URL sera masquee
    """

    def __init__(self, logger):
        self.logger = logger

    def _sanitize_args(self, args):
        return tuple(sanitize_for_logging(arg) for arg in args)

    def debug(self, msg, *args, **kwargs):
        self.logger.debug(msg, *self._sanitize_args(args), **kwargs)

    def info(self, msg, *args, **kwargs):
        self.logger.info(msg, *self._sanitize_args(args), **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.logger.warning(msg, *self._sanitize_args(args), **kwargs)

    def error(self, msg, *args, **kwargs):
        self.logger.error(msg, *self._sanitize_args(args), **kwargs)

    def critical(self, msg, *args, **kwargs):
        self.logger.critical(msg, *self._sanitize_args(args), **kwargs)

    def exception(self, msg, *args, **kwargs):
        self.logger.exception(msg, *self._sanitize_args(args), **kwargs)
