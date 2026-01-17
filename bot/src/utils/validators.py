"""Validateurs pour les entrees utilisateur."""
import re
from typing import Optional

# Pattern pour les noms Minecraft valides
MINECRAFT_USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_]{3,16}$')

# Commandes RCON dangereuses interdites
DANGEROUS_COMMANDS = [
    'stop', 'save-off', 'debug', 'jvm', 'perf',
    'publish', 'pardon-ip', 'setidletimeout'
]

# Caracteres interdits dans les commandes RCON
FORBIDDEN_CHARS = [';', '&', '|', '$', '`', '\n', '\r', '\x00']


def validate_minecraft_username(username: str) -> bool:
    """Valide qu'un nom respecte le format Minecraft (3-16 chars alphanumeriques + _)."""
    return bool(MINECRAFT_USERNAME_PATTERN.match(username))


def sanitize_rcon_input(value: str, max_length: int = 256) -> str:
    """Sanitize une entree avant envoi RCON."""
    # Retirer les caracteres interdits
    for char in FORBIDDEN_CHARS:
        value = value.replace(char, '')
    # Retirer les caracteres de controle
    value = re.sub(r'[\x00-\x1f\x7f]', '', value)
    # Limiter la longueur
    return value[:max_length].strip()


def is_dangerous_command(command: str) -> bool:
    """Verifie si une commande est potentiellement dangereuse."""
    cmd_lower = command.lower().split()[0] if command.split() else ''
    return cmd_lower in DANGEROUS_COMMANDS


def validate_rcon_command(command: str) -> tuple[bool, Optional[str]]:
    """
    Valide une commande RCON.
    Retourne (is_valid, error_message).
    """
    if not command or not command.strip():
        return False, "La commande ne peut pas etre vide"

    command = command.strip()

    # Verifier les caracteres interdits
    for char in FORBIDDEN_CHARS:
        if char in command:
            return False, f"Caractere interdit detecte: {repr(char)}"

    # Verifier la longueur
    if len(command) > 1000:
        return False, "Commande trop longue (max 1000 caracteres)"

    return True, None
