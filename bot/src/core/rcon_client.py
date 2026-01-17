"""
Client RCON asynchrone pour Minecraft.

Ce module implémente le protocole Source RCON pour communiquer
avec un serveur Minecraft de manière asynchrone.

Le protocole RCON utilise des paquets TCP avec la structure suivante:
- 4 bytes: taille du paquet (little-endian, n'inclut pas ces 4 bytes)
- 4 bytes: ID de requête (little-endian)
- 4 bytes: type de paquet (little-endian)
- N bytes: payload (chaîne ASCII null-terminated)
- 1 byte: padding nul

Types de paquets:
- 3: SERVERDATA_AUTH (authentification)
- 2: SERVERDATA_AUTH_RESPONSE / SERVERDATA_EXECCOMMAND
- 0: SERVERDATA_RESPONSE_VALUE
"""

import asyncio
import struct
import logging
from typing import Optional, List, Tuple
from dataclasses import dataclass
from enum import IntEnum
import threading
from contextlib import asynccontextmanager


# Configuration du logger
logger = logging.getLogger(__name__)


class RCONPacketType(IntEnum):
    """Types de paquets RCON."""
    SERVERDATA_RESPONSE_VALUE = 0
    SERVERDATA_EXECCOMMAND = 2
    SERVERDATA_AUTH_RESPONSE = 2
    SERVERDATA_AUTH = 3


class RCONError(Exception):
    """Exception de base pour les erreurs RCON."""
    pass


class RCONConnectionError(RCONError):
    """Erreur de connexion RCON."""
    pass


class RCONAuthenticationError(RCONError):
    """Erreur d'authentification RCON."""
    pass


class RCONTimeoutError(RCONError):
    """Erreur de timeout RCON."""
    pass


class RCONCommandError(RCONError):
    """Erreur lors de l'exécution d'une commande RCON."""
    pass


@dataclass
class RCONPacket:
    """Représente un paquet RCON."""
    request_id: int
    packet_type: int
    payload: str

    def encode(self) -> bytes:
        """Encode le paquet en bytes pour l'envoi."""
        payload_bytes = self.payload.encode('utf-8') + b'\x00\x00'
        packet_body = struct.pack('<ii', self.request_id, self.packet_type) + payload_bytes
        packet_size = len(packet_body)
        return struct.pack('<i', packet_size) + packet_body

    @classmethod
    def decode(cls, data: bytes) -> 'RCONPacket':
        """Décode les bytes reçus en paquet RCON."""
        if len(data) < 10:
            raise RCONError("Paquet RCON trop court")

        request_id, packet_type = struct.unpack('<ii', data[:8])
        # Le payload se termine par deux bytes nuls
        payload = data[8:-2].decode('utf-8', errors='replace')

        return cls(request_id=request_id, packet_type=packet_type, payload=payload)


class RCONClient:
    """
    Client RCON asynchrone pour Minecraft.

    Ce client est thread-safe et supporte la reconnexion automatique.

    Exemple d'utilisation:
        async with RCONClient('localhost', 25575, 'password') as client:
            response = await client.execute('list')
            print(response)
    """

    def __init__(
        self,
        host: str,
        port: int,
        password: str,
        timeout: float = 10.0,
        auto_reconnect: bool = True,
        max_reconnect_attempts: int = 3,
        reconnect_delay: float = 5.0
    ):
        """
        Initialise le client RCON.

        Args:
            host: Adresse du serveur Minecraft
            port: Port RCON (défaut Minecraft: 25575)
            password: Mot de passe RCON configuré dans server.properties
            timeout: Timeout pour les opérations en secondes
            auto_reconnect: Activer la reconnexion automatique
            max_reconnect_attempts: Nombre maximum de tentatives de reconnexion
            reconnect_delay: Délai entre les tentatives de reconnexion en secondes
        """
        self.host = host
        self.port = port
        self.password = password
        self.timeout = timeout
        self.auto_reconnect = auto_reconnect
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_delay = reconnect_delay

        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._request_id: int = 0
        self._lock = asyncio.Lock()
        self._thread_lock = threading.Lock()
        self._connected = False
        self._authenticated = False

    @property
    def is_connected(self) -> bool:
        """Retourne True si le client est connecté et authentifié."""
        return self._connected and self._authenticated

    def _next_request_id(self) -> int:
        """Génère un nouvel ID de requête unique."""
        with self._thread_lock:
            self._request_id = (self._request_id + 1) % 2147483647
            return self._request_id

    async def connect(self) -> None:
        """
        Établit la connexion au serveur RCON et s'authentifie.

        Raises:
            RCONConnectionError: Si la connexion échoue
            RCONAuthenticationError: Si l'authentification échoue
        """
        async with self._lock:
            await self._connect_internal()

    async def _connect_internal(self) -> None:
        """Connexion interne sans lock."""
        if self._connected:
            return

        logger.info(f"Connexion au serveur RCON {self.host}:{self.port}...")

        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.timeout
            )
            self._connected = True
            logger.info("Connexion TCP établie")
        except asyncio.TimeoutError:
            raise RCONConnectionError(f"Timeout lors de la connexion à {self.host}:{self.port}")
        except OSError as e:
            raise RCONConnectionError(f"Impossible de se connecter à {self.host}:{self.port}: {e}")

        # Authentification
        await self._authenticate()

    async def _authenticate(self) -> None:
        """Authentifie le client auprès du serveur RCON."""
        logger.debug("Authentification RCON en cours...")

        auth_id = self._next_request_id()
        packet = RCONPacket(
            request_id=auth_id,
            packet_type=RCONPacketType.SERVERDATA_AUTH,
            payload=self.password
        )

        try:
            await self._send_packet(packet)
            response = await self._receive_packet()

            # Le serveur peut envoyer un paquet vide avant la réponse d'auth
            if response.packet_type == RCONPacketType.SERVERDATA_RESPONSE_VALUE:
                response = await self._receive_packet()

            if response.request_id == -1:
                self._connected = False
                raise RCONAuthenticationError("Mot de passe RCON incorrect")

            if response.request_id != auth_id:
                self._connected = False
                raise RCONAuthenticationError("ID de réponse d'authentification invalide")

            self._authenticated = True
            logger.info("Authentification RCON réussie")

        except (RCONError, asyncio.TimeoutError) as e:
            self._connected = False
            self._authenticated = False
            if isinstance(e, asyncio.TimeoutError):
                raise RCONTimeoutError("Timeout lors de l'authentification")
            raise

    async def disconnect(self) -> None:
        """Ferme la connexion au serveur RCON."""
        async with self._lock:
            await self._disconnect_internal()

    async def _disconnect_internal(self) -> None:
        """Déconnexion interne sans lock."""
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception as e:
                logger.debug(f"Erreur lors de la fermeture de la connexion: {e}")
            finally:
                self._writer = None
                self._reader = None
                self._connected = False
                self._authenticated = False
                logger.info("Déconnecté du serveur RCON")

    async def _send_packet(self, packet: RCONPacket) -> None:
        """Envoie un paquet au serveur."""
        if not self._writer:
            raise RCONConnectionError("Non connecté au serveur")

        data = packet.encode()
        # Ne jamais logger le payload d'authentification (contient le mot de passe)
        if packet.packet_type == RCONPacketType.SERVERDATA_AUTH:
            logger.debug(f"Envoi paquet auth: id={packet.request_id}")
        else:
            logger.debug(f"Envoi paquet: id={packet.request_id}, type={packet.packet_type}, payload={packet.payload[:50]}...")

        try:
            self._writer.write(data)
            await asyncio.wait_for(self._writer.drain(), timeout=self.timeout)
        except asyncio.TimeoutError:
            raise RCONTimeoutError("Timeout lors de l'envoi du paquet")
        except OSError as e:
            self._connected = False
            self._authenticated = False
            raise RCONConnectionError(f"Erreur d'envoi: {e}")

    async def _receive_packet(self) -> RCONPacket:
        """Reçoit un paquet du serveur."""
        if not self._reader:
            raise RCONConnectionError("Non connecté au serveur")

        try:
            # Lire la taille du paquet (4 bytes)
            size_data = await asyncio.wait_for(
                self._reader.readexactly(4),
                timeout=self.timeout
            )
            packet_size = struct.unpack('<i', size_data)[0]

            if packet_size < 10 or packet_size > 4096:
                raise RCONError(f"Taille de paquet invalide: {packet_size}")

            # Lire le reste du paquet
            packet_data = await asyncio.wait_for(
                self._reader.readexactly(packet_size),
                timeout=self.timeout
            )

            packet = RCONPacket.decode(packet_data)
            logger.debug(f"Reçu paquet: id={packet.request_id}, type={packet.packet_type}, payload={packet.payload[:100]}...")
            return packet

        except asyncio.TimeoutError:
            raise RCONTimeoutError("Timeout lors de la réception du paquet")
        except asyncio.IncompleteReadError:
            self._connected = False
            self._authenticated = False
            raise RCONConnectionError("Connexion fermée par le serveur")
        except OSError as e:
            self._connected = False
            self._authenticated = False
            raise RCONConnectionError(f"Erreur de réception: {e}")

    async def _reconnect(self) -> bool:
        """
        Tente de se reconnecter au serveur.

        Returns:
            True si la reconnexion a réussi, False sinon
        """
        for attempt in range(1, self.max_reconnect_attempts + 1):
            logger.info(f"Tentative de reconnexion {attempt}/{self.max_reconnect_attempts}...")

            try:
                await self._disconnect_internal()
                await asyncio.sleep(self.reconnect_delay)
                await self._connect_internal()
                logger.info("Reconnexion réussie")
                return True
            except RCONError as e:
                logger.warning(f"Échec de reconnexion: {e}")

        logger.error("Échec de toutes les tentatives de reconnexion")
        return False

    async def execute(self, command: str) -> str:
        """
        Exécute une commande RCON sur le serveur.

        Args:
            command: La commande Minecraft à exécuter

        Returns:
            La réponse du serveur

        Raises:
            RCONError: En cas d'erreur
        """
        async with self._lock:
            return await self._execute_internal(command)

    async def _execute_internal(self, command: str, retry: bool = True) -> str:
        """Exécution interne de commande sans lock."""
        if not self.is_connected:
            if self.auto_reconnect and retry:
                if not await self._reconnect():
                    raise RCONConnectionError("Impossible de se reconnecter au serveur")
            else:
                raise RCONConnectionError("Non connecté au serveur")

        request_id = self._next_request_id()
        packet = RCONPacket(
            request_id=request_id,
            packet_type=RCONPacketType.SERVERDATA_EXECCOMMAND,
            payload=command
        )

        logger.info(f"Exécution commande RCON: {command}")

        try:
            await self._send_packet(packet)

            # Collecter toutes les réponses (pour les commandes longues)
            responses: List[str] = []

            while True:
                response = await self._receive_packet()

                if response.request_id != request_id:
                    logger.warning(f"ID de réponse inattendu: {response.request_id} != {request_id}")
                    continue

                responses.append(response.payload)

                # Vérifier s'il y a plus de données à lire
                # En pratique, Minecraft envoie généralement une seule réponse
                if self._reader and self._reader.at_eof():
                    break

                # Petit délai pour voir s'il y a d'autres paquets
                try:
                    await asyncio.wait_for(asyncio.sleep(0.1), timeout=0.2)
                    if not self._reader or self._reader.at_eof():
                        break
                except asyncio.TimeoutError:
                    pass

                # Sortir après le premier paquet pour éviter les blocages
                break

            result = ''.join(responses)
            logger.debug(f"Réponse commande: {result}")
            return result

        except RCONConnectionError:
            self._connected = False
            self._authenticated = False
            if self.auto_reconnect and retry:
                if await self._reconnect():
                    return await self._execute_internal(command, retry=False)
            raise
        except RCONTimeoutError:
            if self.auto_reconnect and retry:
                self._connected = False
                self._authenticated = False
                if await self._reconnect():
                    return await self._execute_internal(command, retry=False)
            raise

    # ==========================================================================
    # Méthodes de commodité pour les commandes Minecraft courantes
    # ==========================================================================

    async def list_players(self) -> Tuple[int, int, List[str]]:
        """
        Récupère la liste des joueurs en ligne.

        Returns:
            Tuple (joueurs_en_ligne, max_joueurs, liste_noms)
        """
        response = await self.execute("list")

        # Format typique: "There are X of a max of Y players online: player1, player2"
        # ou "There are X/Y players online: player1, player2"
        players: List[str] = []
        online = 0
        max_players = 0

        try:
            if "of a max of" in response:
                # Format: "There are X of a max of Y players online: ..."
                parts = response.split("of a max of")
                online = int(parts[0].split()[-1])
                rest = parts[1].split("players online:")
                max_players = int(rest[0].strip())
                if len(rest) > 1 and rest[1].strip():
                    players = [p.strip() for p in rest[1].split(",") if p.strip()]
            elif "/" in response:
                # Format alternatif: "There are X/Y players online: ..."
                import re
                match = re.search(r'(\d+)/(\d+)', response)
                if match:
                    online = int(match.group(1))
                    max_players = int(match.group(2))
                if ":" in response:
                    player_list = response.split(":")[-1].strip()
                    if player_list:
                        players = [p.strip() for p in player_list.split(",") if p.strip()]
        except (ValueError, IndexError) as e:
            logger.warning(f"Impossible de parser la réponse 'list': {response}, erreur: {e}")

        return online, max_players, players

    async def say(self, message: str) -> str:
        """
        Envoie un message à tous les joueurs.

        Args:
            message: Le message à envoyer

        Returns:
            Réponse du serveur
        """
        # Échapper les caractères spéciaux
        safe_message = message.replace('"', '\\"')
        return await self.execute(f'say {safe_message}')

    async def tell(self, player: str, message: str) -> str:
        """
        Envoie un message privé à un joueur.

        Args:
            player: Nom du joueur
            message: Le message à envoyer

        Returns:
            Réponse du serveur
        """
        safe_message = message.replace('"', '\\"')
        return await self.execute(f'tell {player} {safe_message}')

    async def kick(self, player: str, reason: str = "Kicked by administrator") -> str:
        """
        Expulse un joueur du serveur.

        Args:
            player: Nom du joueur à expulser
            reason: Raison de l'expulsion

        Returns:
            Réponse du serveur
        """
        safe_reason = reason.replace('"', '\\"')
        return await self.execute(f'kick {player} {safe_reason}')

    async def ban(self, player: str, reason: str = "Banned by administrator") -> str:
        """
        Bannit un joueur du serveur.

        Args:
            player: Nom du joueur à bannir
            reason: Raison du bannissement

        Returns:
            Réponse du serveur
        """
        safe_reason = reason.replace('"', '\\"')
        return await self.execute(f'ban {player} {safe_reason}')

    async def ban_ip(self, ip_or_player: str, reason: str = "Banned by administrator") -> str:
        """
        Bannit une adresse IP.

        Args:
            ip_or_player: Adresse IP ou nom du joueur dont l'IP sera bannie
            reason: Raison du bannissement

        Returns:
            Réponse du serveur
        """
        safe_reason = reason.replace('"', '\\"')
        return await self.execute(f'ban-ip {ip_or_player} {safe_reason}')

    async def pardon(self, player: str) -> str:
        """
        Retire le bannissement d'un joueur.

        Args:
            player: Nom du joueur à gracier

        Returns:
            Réponse du serveur
        """
        return await self.execute(f'pardon {player}')

    async def pardon_ip(self, ip: str) -> str:
        """
        Retire le bannissement d'une adresse IP.

        Args:
            ip: Adresse IP à gracier

        Returns:
            Réponse du serveur
        """
        return await self.execute(f'pardon-ip {ip}')

    async def whitelist_add(self, player: str) -> str:
        """
        Ajoute un joueur à la whitelist.

        Args:
            player: Nom du joueur à ajouter

        Returns:
            Réponse du serveur
        """
        return await self.execute(f'whitelist add {player}')

    async def whitelist_remove(self, player: str) -> str:
        """
        Retire un joueur de la whitelist.

        Args:
            player: Nom du joueur à retirer

        Returns:
            Réponse du serveur
        """
        return await self.execute(f'whitelist remove {player}')

    async def whitelist_list(self) -> List[str]:
        """
        Récupère la liste des joueurs dans la whitelist.

        Returns:
            Liste des noms de joueurs
        """
        response = await self.execute('whitelist list')

        # Format: "There are X whitelisted players: player1, player2"
        # ou "There are no whitelisted players"
        if "no whitelisted" in response.lower():
            return []

        if ":" in response:
            player_list = response.split(":")[-1].strip()
            return [p.strip() for p in player_list.split(",") if p.strip()]

        return []

    async def whitelist_on(self) -> str:
        """Active la whitelist."""
        return await self.execute('whitelist on')

    async def whitelist_off(self) -> str:
        """Désactive la whitelist."""
        return await self.execute('whitelist off')

    async def whitelist_reload(self) -> str:
        """Recharge la whitelist depuis le fichier."""
        return await self.execute('whitelist reload')

    async def op(self, player: str) -> str:
        """
        Donne le statut opérateur à un joueur.

        Args:
            player: Nom du joueur

        Returns:
            Réponse du serveur
        """
        return await self.execute(f'op {player}')

    async def deop(self, player: str) -> str:
        """
        Retire le statut opérateur d'un joueur.

        Args:
            player: Nom du joueur

        Returns:
            Réponse du serveur
        """
        return await self.execute(f'deop {player}')

    async def gamemode(self, player: str, mode: str) -> str:
        """
        Change le mode de jeu d'un joueur.

        Args:
            player: Nom du joueur
            mode: Mode de jeu (survival, creative, adventure, spectator)

        Returns:
            Réponse du serveur
        """
        return await self.execute(f'gamemode {mode} {player}')

    async def tp(self, player: str, target_or_coords: str) -> str:
        """
        Téléporte un joueur.

        Args:
            player: Nom du joueur à téléporter
            target_or_coords: Joueur cible ou coordonnées "x y z"

        Returns:
            Réponse du serveur
        """
        return await self.execute(f'tp {player} {target_or_coords}')

    async def give(self, player: str, item: str, count: int = 1) -> str:
        """
        Donne un objet à un joueur.

        Args:
            player: Nom du joueur
            item: ID de l'objet (ex: "minecraft:diamond")
            count: Quantité

        Returns:
            Réponse du serveur
        """
        return await self.execute(f'give {player} {item} {count}')

    async def time_set(self, time: str) -> str:
        """
        Change l'heure du jeu.

        Args:
            time: Heure (day, night, noon, midnight, ou nombre de ticks)

        Returns:
            Réponse du serveur
        """
        return await self.execute(f'time set {time}')

    async def weather(self, weather_type: str, duration: Optional[int] = None) -> str:
        """
        Change la météo.

        Args:
            weather_type: Type de météo (clear, rain, thunder)
            duration: Durée en secondes (optionnel)

        Returns:
            Réponse du serveur
        """
        cmd = f'weather {weather_type}'
        if duration is not None:
            cmd += f' {duration}'
        return await self.execute(cmd)

    async def difficulty(self, difficulty: str) -> str:
        """
        Change la difficulté du jeu.

        Args:
            difficulty: Difficulté (peaceful, easy, normal, hard)

        Returns:
            Réponse du serveur
        """
        return await self.execute(f'difficulty {difficulty}')

    async def seed(self) -> str:
        """
        Récupère la seed du monde.

        Returns:
            La seed du monde
        """
        return await self.execute('seed')

    async def save_all(self, flush: bool = False) -> str:
        """
        Sauvegarde le monde.

        Args:
            flush: Si True, force l'écriture immédiate sur disque

        Returns:
            Réponse du serveur
        """
        cmd = 'save-all'
        if flush:
            cmd += ' flush'
        return await self.execute(cmd)

    async def save_on(self) -> str:
        """Active la sauvegarde automatique."""
        return await self.execute('save-on')

    async def save_off(self) -> str:
        """Désactive la sauvegarde automatique."""
        return await self.execute('save-off')

    async def stop(self) -> str:
        """
        Arrête le serveur proprement.

        Returns:
            Réponse du serveur
        """
        logger.warning("Commande d'arrêt du serveur envoyée")
        return await self.execute('stop')

    # ==========================================================================
    # Context Manager
    # ==========================================================================

    async def __aenter__(self) -> 'RCONClient':
        """Entre dans le context manager et établit la connexion."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Sort du context manager et ferme la connexion."""
        await self.disconnect()


@asynccontextmanager
async def create_rcon_client(
    host: str,
    port: int,
    password: str,
    **kwargs
) -> RCONClient:
    """
    Crée un client RCON avec gestion automatique de la connexion.

    Exemple:
        async with create_rcon_client('localhost', 25575, 'password') as client:
            await client.say("Hello!")

    Args:
        host: Adresse du serveur
        port: Port RCON
        password: Mot de passe RCON
        **kwargs: Arguments supplémentaires pour RCONClient

    Yields:
        Instance de RCONClient connectée
    """
    client = RCONClient(host, port, password, **kwargs)
    try:
        await client.connect()
        yield client
    finally:
        await client.disconnect()


# =============================================================================
# Exemple d'utilisation
# =============================================================================

async def main():
    """Exemple d'utilisation du client RCON."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Configuration - à adapter selon votre serveur
    HOST = "localhost"
    PORT = 25575
    PASSWORD = "your_rcon_password"

    try:
        async with RCONClient(HOST, PORT, PASSWORD) as client:
            # Liste des joueurs
            online, max_players, players = await client.list_players()
            print(f"Joueurs: {online}/{max_players}")
            if players:
                print(f"En ligne: {', '.join(players)}")

            # Envoyer un message
            await client.say("Bot RCON connecté!")

            # Sauvegarder le monde
            response = await client.save_all()
            print(f"Sauvegarde: {response}")

    except RCONAuthenticationError:
        print("Erreur: Mot de passe RCON incorrect")
    except RCONConnectionError as e:
        print(f"Erreur de connexion: {e}")
    except RCONError as e:
        print(f"Erreur RCON: {e}")


if __name__ == "__main__":
    asyncio.run(main())
