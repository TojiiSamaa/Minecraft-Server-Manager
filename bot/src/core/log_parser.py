"""
Minecraft NeoForge Log Parser
=============================
Parser de logs pour serveur Minecraft NeoForge avec surveillance en temps réel.

Format de log NeoForge: [HH:mm:ss] [Thread/LEVEL] [Namespace]: Message
"""

import asyncio
import re
from dataclasses import dataclass, field
from datetime import datetime, time
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Coroutine, Optional

import aiofiles
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent


class EventType(Enum):
    """Types d'événements Minecraft détectables."""
    PLAYER_JOIN = auto()
    PLAYER_LEAVE = auto()
    PLAYER_DEATH = auto()
    PLAYER_ACHIEVEMENT = auto()
    PLAYER_CHAT = auto()
    SERVER_STARTING = auto()
    SERVER_STARTED = auto()
    SERVER_STOPPING = auto()
    ERROR = auto()
    WARNING = auto()
    UNKNOWN = auto()


@dataclass
class LogEvent:
    """Représente un événement de log parsé."""
    timestamp: time
    event_type: EventType
    data: dict[str, Any] = field(default_factory=dict)
    raw_line: str = ""
    thread: str = ""
    level: str = ""
    namespace: str = ""

    @property
    def datetime_today(self) -> datetime:
        """Retourne un datetime avec la date d'aujourd'hui."""
        today = datetime.now().date()
        return datetime.combine(today, self.timestamp)


# Type pour les handlers async
EventHandler = Callable[[LogEvent], Coroutine[Any, Any, None]]


class DeathMessagePatterns:
    """Patterns regex pour tous les messages de mort Minecraft."""

    # Patterns de base - {player} représente le joueur mort, {killer} l'attaquant
    PATTERNS: list[tuple[str, dict[str, str]]] = [
        # Morts par entités
        (r"(\w+) was slain by (.+)", {"player": 1, "killer": 2}),
        (r"(\w+) was shot by (.+)", {"player": 1, "killer": 2}),
        (r"(\w+) was fireballed by (.+)", {"player": 1, "killer": 2}),
        (r"(\w+) was pummeled by (.+)", {"player": 1, "killer": 2}),
        (r"(\w+) was killed by (.+)", {"player": 1, "killer": 2}),
        (r"(\w+) got finished off by (.+)", {"player": 1, "killer": 2}),
        (r"(\w+) was impaled by (.+)", {"player": 1, "killer": 2}),
        (r"(\w+) was skewered by (.+)", {"player": 1, "killer": 2}),

        # Morts par entités avec items
        (r"(\w+) was slain by (.+) using (.+)", {"player": 1, "killer": 2, "weapon": 3}),
        (r"(\w+) was shot by (.+) using (.+)", {"player": 1, "killer": 2, "weapon": 3}),
        (r"(\w+) was killed by (.+) using (.+)", {"player": 1, "killer": 2, "weapon": 3}),

        # Morts PvP
        (r"(\w+) was killed by (\w+)", {"player": 1, "killer": 2}),
        (r"(\w+) was shot by (\w+)", {"player": 1, "killer": 2}),

        # Explosions
        (r"(\w+) was blown up by (.+)", {"player": 1, "killer": 2}),
        (r"(\w+) was killed by \[Intentional Game Design\]", {"player": 1, "cause": "bed_explosion"}),
        (r"(\w+) blew up", {"player": 1, "cause": "explosion"}),

        # Chutes
        (r"(\w+) hit the ground too hard", {"player": 1, "cause": "fall"}),
        (r"(\w+) fell from a high place", {"player": 1, "cause": "fall"}),
        (r"(\w+) fell off a ladder", {"player": 1, "cause": "fall_ladder"}),
        (r"(\w+) fell off some vines", {"player": 1, "cause": "fall_vines"}),
        (r"(\w+) fell off some weeping vines", {"player": 1, "cause": "fall_weeping_vines"}),
        (r"(\w+) fell off some twisting vines", {"player": 1, "cause": "fall_twisting_vines"}),
        (r"(\w+) fell off scaffolding", {"player": 1, "cause": "fall_scaffolding"}),
        (r"(\w+) fell while climbing", {"player": 1, "cause": "fall_climbing"}),
        (r"(\w+) was doomed to fall by (.+)", {"player": 1, "killer": 2, "cause": "fall_attack"}),
        (r"(\w+) was doomed to fall by (.+) using (.+)", {"player": 1, "killer": 2, "weapon": 3, "cause": "fall_attack"}),
        (r"(\w+) fell too far and was finished by (.+)", {"player": 1, "killer": 2, "cause": "fall_finished"}),
        (r"(\w+) fell too far and was finished by (.+) using (.+)", {"player": 1, "killer": 2, "weapon": 3, "cause": "fall_finished"}),

        # Feu et lave
        (r"(\w+) went up in flames", {"player": 1, "cause": "fire"}),
        (r"(\w+) walked into fire whilst fighting (.+)", {"player": 1, "killer": 2, "cause": "fire_combat"}),
        (r"(\w+) burned to death", {"player": 1, "cause": "fire"}),
        (r"(\w+) was burnt to a crisp whilst fighting (.+)", {"player": 1, "killer": 2, "cause": "fire_combat"}),
        (r"(\w+) tried to swim in lava", {"player": 1, "cause": "lava"}),
        (r"(\w+) tried to swim in lava to escape (.+)", {"player": 1, "killer": 2, "cause": "lava_escape"}),

        # Noyade
        (r"(\w+) drowned", {"player": 1, "cause": "drowning"}),
        (r"(\w+) drowned whilst trying to escape (.+)", {"player": 1, "killer": 2, "cause": "drowning_escape"}),

        # Suffocation
        (r"(\w+) suffocated in a wall", {"player": 1, "cause": "suffocation"}),
        (r"(\w+) was squished too much", {"player": 1, "cause": "squish"}),
        (r"(\w+) was squashed by (.+)", {"player": 1, "killer": 2, "cause": "squash"}),
        (r"(\w+) was killed trying to hurt (.+)", {"player": 1, "killer": 2, "cause": "thorns"}),

        # Void
        (r"(\w+) fell out of the world", {"player": 1, "cause": "void"}),
        (r"(\w+) didn't want to live in the same world as (.+)", {"player": 1, "killer": 2, "cause": "void_escape"}),

        # Foudre
        (r"(\w+) was struck by lightning", {"player": 1, "cause": "lightning"}),
        (r"(\w+) was struck by lightning whilst fighting (.+)", {"player": 1, "killer": 2, "cause": "lightning_combat"}),

        # Magie et potions
        (r"(\w+) was killed by magic", {"player": 1, "cause": "magic"}),
        (r"(\w+) was killed by magic whilst trying to escape (.+)", {"player": 1, "killer": 2, "cause": "magic_escape"}),
        (r"(\w+) was killed by (.+) using magic", {"player": 1, "killer": 2, "cause": "magic"}),
        (r"(\w+) froze to death", {"player": 1, "cause": "freeze"}),
        (r"(\w+) was frozen to death by (.+)", {"player": 1, "killer": 2, "cause": "freeze"}),

        # Wither et Dragon
        (r"(\w+) withered away", {"player": 1, "cause": "wither"}),
        (r"(\w+) withered away whilst fighting (.+)", {"player": 1, "killer": 2, "cause": "wither_combat"}),
        (r"(\w+) was roasted in dragon breath", {"player": 1, "cause": "dragon_breath"}),
        (r"(\w+) was roasted in dragon breath by (.+)", {"player": 1, "killer": 2, "cause": "dragon_breath"}),

        # Cactus
        (r"(\w+) was pricked to death", {"player": 1, "cause": "cactus"}),
        (r"(\w+) walked into a cactus whilst trying to escape (.+)", {"player": 1, "killer": 2, "cause": "cactus_escape"}),

        # Faim
        (r"(\w+) starved to death", {"player": 1, "cause": "starvation"}),
        (r"(\w+) starved to death whilst fighting (.+)", {"player": 1, "killer": 2, "cause": "starvation_combat"}),

        # Autres
        (r"(\w+) died", {"player": 1, "cause": "generic"}),
        (r"(\w+) died because of (.+)", {"player": 1, "killer": 2, "cause": "generic"}),
        (r"(\w+) was killed", {"player": 1, "cause": "generic"}),
        (r"(\w+) was poked to death by a sweet berry bush", {"player": 1, "cause": "sweet_berry"}),
        (r"(\w+) was poked to death by a sweet berry bush whilst trying to escape (.+)", {"player": 1, "killer": 2, "cause": "sweet_berry_escape"}),
        (r"(\w+) was stung to death", {"player": 1, "cause": "bee"}),
        (r"(\w+) was stung to death by (.+)", {"player": 1, "killer": 2, "cause": "bee"}),
        (r"(\w+) discovered the floor was lava", {"player": 1, "cause": "magma_block"}),
        (r"(\w+) walked on danger zone due to (.+)", {"player": 1, "killer": 2, "cause": "magma_block"}),
        (r"(\w+) experienced kinetic energy", {"player": 1, "cause": "elytra_crash"}),
        (r"(\w+) experienced kinetic energy whilst trying to escape (.+)", {"player": 1, "killer": 2, "cause": "elytra_crash"}),
        (r"(\w+) left the confines of this world", {"player": 1, "cause": "void"}),
        (r"(\w+) was obliterated by a sonically-charged shriek", {"player": 1, "cause": "sonic_boom"}),
        (r"(\w+) was obliterated by a sonically-charged shriek whilst trying to escape (.+)", {"player": 1, "killer": 2, "cause": "sonic_boom"}),
    ]

    @classmethod
    def compile_patterns(cls) -> list[tuple[re.Pattern, dict[str, str]]]:
        """Compile tous les patterns regex."""
        return [(re.compile(pattern, re.IGNORECASE), groups) for pattern, groups in cls.PATTERNS]


class MinecraftLogParser:
    """Parser de logs Minecraft NeoForge avec support async."""

    # Pattern principal pour parser une ligne de log NeoForge
    # Format: [HH:mm:ss] [Thread/LEVEL] [Namespace]: Message
    LOG_PATTERN = re.compile(
        r"\[(\d{2}:\d{2}:\d{2})\]\s+"  # Timestamp [HH:mm:ss]
        r"\[([^/\]]+)/([A-Z]+)\]\s+"   # [Thread/LEVEL]
        r"\[([^\]]+)\]:\s+"            # [Namespace]:
        r"(.+)$"                        # Message
    )

    # Patterns pour les événements spécifiques
    PLAYER_JOIN_PATTERNS = [
        re.compile(r"(\w+)\[/[\d.:]+\] logged in with entity id \d+"),
        re.compile(r"(\w+) joined the game"),
        re.compile(r"UUID of player (\w+) is"),
    ]

    PLAYER_LEAVE_PATTERNS = [
        re.compile(r"(\w+) left the game"),
        re.compile(r"(\w+) lost connection:"),
        re.compile(r"Disconnecting (\w+):"),
    ]

    PLAYER_CHAT_PATTERN = re.compile(r"<(\w+)>\s+(.+)")

    ADVANCEMENT_PATTERNS = [
        re.compile(r"(\w+) has made the advancement \[(.+)\]"),
        re.compile(r"(\w+) has completed the challenge \[(.+)\]"),
        re.compile(r"(\w+) has reached the goal \[(.+)\]"),
    ]

    SERVER_PATTERNS = {
        EventType.SERVER_STARTING: [
            re.compile(r"Starting minecraft server"),
            re.compile(r"Starting Minecraft server"),
        ],
        EventType.SERVER_STARTED: [
            re.compile(r"Done \([\d.]+s\)! For help, type"),
            re.compile(r"Server started"),
        ],
        EventType.SERVER_STOPPING: [
            re.compile(r"Stopping server"),
            re.compile(r"Stopping the server"),
        ],
    }

    def __init__(self):
        """Initialise le parser."""
        self._handlers: dict[EventType, list[EventHandler]] = {event_type: [] for event_type in EventType}
        self._global_handlers: list[EventHandler] = []
        self._death_patterns = DeathMessagePatterns.compile_patterns()
        self._running = False
        self._observer: Optional[Observer] = None
        self._file_position: int = 0

    def register_handler(self, event_type: EventType, handler: EventHandler) -> None:
        """
        Enregistre un handler pour un type d'événement spécifique.

        Args:
            event_type: Type d'événement à écouter
            handler: Fonction async à appeler lors de l'événement
        """
        self._handlers[event_type].append(handler)

    def register_global_handler(self, handler: EventHandler) -> None:
        """
        Enregistre un handler global appelé pour tous les événements.

        Args:
            handler: Fonction async à appeler pour tous les événements
        """
        self._global_handlers.append(handler)

    def unregister_handler(self, event_type: EventType, handler: EventHandler) -> bool:
        """
        Retire un handler enregistré.

        Args:
            event_type: Type d'événement
            handler: Handler à retirer

        Returns:
            True si le handler a été retiré, False sinon
        """
        try:
            self._handlers[event_type].remove(handler)
            return True
        except ValueError:
            return False

    def parse_line(self, line: str) -> Optional[LogEvent]:
        """
        Parse une ligne de log et retourne un LogEvent si valide.

        Args:
            line: Ligne de log brute

        Returns:
            LogEvent si la ligne est valide, None sinon
        """
        line = line.strip()
        if not line:
            return None

        match = self.LOG_PATTERN.match(line)
        if not match:
            return None

        timestamp_str, thread, level, namespace, message = match.groups()

        try:
            timestamp = datetime.strptime(timestamp_str, "%H:%M:%S").time()
        except ValueError:
            return None

        # Déterminer le type d'événement et extraire les données
        event_type, data = self._classify_message(message, level)

        return LogEvent(
            timestamp=timestamp,
            event_type=event_type,
            data=data,
            raw_line=line,
            thread=thread,
            level=level,
            namespace=namespace
        )

    def _classify_message(self, message: str, level: str) -> tuple[EventType, dict[str, Any]]:
        """
        Classifie un message et extrait les données pertinentes.

        Args:
            message: Message de log
            level: Niveau de log (INFO, WARN, ERROR, etc.)

        Returns:
            Tuple (EventType, données extraites)
        """
        data: dict[str, Any] = {"message": message}

        # Vérifier ERROR/WARNING d'abord
        if level == "ERROR":
            return EventType.ERROR, data
        if level in ("WARN", "WARNING"):
            return EventType.WARNING, data

        # Vérifier les événements serveur
        for event_type, patterns in self.SERVER_PATTERNS.items():
            for pattern in patterns:
                if pattern.search(message):
                    return event_type, data

        # Vérifier les connexions joueur
        for pattern in self.PLAYER_JOIN_PATTERNS:
            match = pattern.search(message)
            if match:
                data["player"] = match.group(1)
                return EventType.PLAYER_JOIN, data

        # Vérifier les déconnexions joueur
        for pattern in self.PLAYER_LEAVE_PATTERNS:
            match = pattern.search(message)
            if match:
                data["player"] = match.group(1)
                return EventType.PLAYER_LEAVE, data

        # Vérifier les messages de chat
        chat_match = self.PLAYER_CHAT_PATTERN.match(message)
        if chat_match:
            data["player"] = chat_match.group(1)
            data["chat_message"] = chat_match.group(2)
            return EventType.PLAYER_CHAT, data

        # Vérifier les succès/advancements
        for pattern in self.ADVANCEMENT_PATTERNS:
            match = pattern.search(message)
            if match:
                data["player"] = match.group(1)
                data["advancement"] = match.group(2)
                return EventType.PLAYER_ACHIEVEMENT, data

        # Vérifier les messages de mort
        death_data = self._parse_death_message(message)
        if death_data:
            data.update(death_data)
            return EventType.PLAYER_DEATH, data

        return EventType.UNKNOWN, data

    def _parse_death_message(self, message: str) -> Optional[dict[str, Any]]:
        """
        Parse un message de mort Minecraft.

        Args:
            message: Message à analyser

        Returns:
            Dictionnaire avec les données de mort ou None
        """
        for pattern, group_mapping in self._death_patterns:
            match = pattern.match(message)
            if match:
                result: dict[str, Any] = {}
                for key, group_idx in group_mapping.items():
                    if isinstance(group_idx, int):
                        try:
                            result[key] = match.group(group_idx)
                        except IndexError:
                            pass
                    else:
                        result[key] = group_idx
                return result
        return None

    async def _dispatch_event(self, event: LogEvent) -> None:
        """
        Dispatch un événement à tous les handlers enregistrés.

        Args:
            event: Événement à dispatcher
        """
        # Appeler les handlers globaux
        for handler in self._global_handlers:
            try:
                await handler(event)
            except Exception as e:
                print(f"Erreur dans handler global: {e}")

        # Appeler les handlers spécifiques
        for handler in self._handlers[event.event_type]:
            try:
                await handler(event)
            except Exception as e:
                print(f"Erreur dans handler {event.event_type}: {e}")

    async def parse_file(self, log_path: str | Path) -> list[LogEvent]:
        """
        Parse un fichier de log complet.

        Args:
            log_path: Chemin vers le fichier de log

        Returns:
            Liste des événements parsés
        """
        events: list[LogEvent] = []
        path = Path(log_path)

        if not path.exists():
            raise FileNotFoundError(f"Fichier de log non trouvé: {path}")

        async with aiofiles.open(path, mode='r', encoding='utf-8', errors='replace') as f:
            async for line in f:
                event = self.parse_line(line)
                if event:
                    events.append(event)
                    await self._dispatch_event(event)

        return events

    async def _read_new_lines(self, log_path: Path) -> None:
        """
        Lit les nouvelles lignes du fichier de log.

        Args:
            log_path: Chemin vers le fichier de log
        """
        try:
            async with aiofiles.open(log_path, mode='r', encoding='utf-8', errors='replace') as f:
                await f.seek(self._file_position)
                async for line in f:
                    event = self.parse_line(line)
                    if event:
                        await self._dispatch_event(event)
                self._file_position = await f.tell()
        except Exception as e:
            print(f"Erreur lors de la lecture du fichier: {e}")

    async def watch_log(
        self,
        log_path: str | Path,
        poll_interval: float = 0.5,
        from_beginning: bool = False
    ) -> None:
        """
        Surveille un fichier de log en continu (style tail -f).

        Args:
            log_path: Chemin vers le fichier latest.log
            poll_interval: Intervalle de vérification en secondes
            from_beginning: Si True, parse le fichier depuis le début
        """
        path = Path(log_path)

        if not path.exists():
            raise FileNotFoundError(f"Fichier de log non trouvé: {path}")

        self._running = True

        # Initialiser la position
        if from_beginning:
            self._file_position = 0
        else:
            self._file_position = path.stat().st_size

        # Configuration du watcher watchdog
        event_queue: asyncio.Queue[bool] = asyncio.Queue()
        loop = asyncio.get_event_loop()

        class LogFileHandler(FileSystemEventHandler):
            def on_modified(self, event: FileModifiedEvent) -> None:
                if not event.is_directory and Path(event.src_path).name == path.name:
                    loop.call_soon_threadsafe(event_queue.put_nowait, True)

        handler = LogFileHandler()
        self._observer = Observer()
        self._observer.schedule(handler, str(path.parent), recursive=False)
        self._observer.start()

        try:
            # Lire les nouvelles lignes immédiatement si from_beginning
            if from_beginning:
                await self._read_new_lines(path)

            while self._running:
                try:
                    # Attendre une modification ou timeout
                    await asyncio.wait_for(event_queue.get(), timeout=poll_interval)
                except asyncio.TimeoutError:
                    pass

                # Vérifier s'il y a de nouvelles données
                if path.exists():
                    current_size = path.stat().st_size
                    if current_size > self._file_position:
                        await self._read_new_lines(path)
                    elif current_size < self._file_position:
                        # Le fichier a été tronqué (rotation de log)
                        self._file_position = 0
                        await self._read_new_lines(path)
        finally:
            self._observer.stop()
            self._observer.join()

    def stop_watching(self) -> None:
        """Arrête la surveillance du fichier de log."""
        self._running = False
        if self._observer:
            self._observer.stop()

    def on(self, event_type: EventType):
        """
        Décorateur pour enregistrer un handler.

        Exemple:
            @parser.on(EventType.PLAYER_JOIN)
            async def on_player_join(event: LogEvent):
                print(f"Joueur connecté: {event.data['player']}")

        Args:
            event_type: Type d'événement à écouter

        Returns:
            Décorateur
        """
        def decorator(func: EventHandler) -> EventHandler:
            self.register_handler(event_type, func)
            return func
        return decorator

    def on_all(self, func: EventHandler) -> EventHandler:
        """
        Décorateur pour enregistrer un handler global.

        Exemple:
            @parser.on_all
            async def on_any_event(event: LogEvent):
                print(f"Événement: {event.event_type}")

        Args:
            func: Fonction handler async

        Returns:
            La même fonction (pour chaînage)
        """
        self.register_global_handler(func)
        return func


# Exemple d'utilisation
async def main():
    """Exemple d'utilisation du parser."""
    parser = MinecraftLogParser()

    # Enregistrer des handlers avec décorateurs
    @parser.on(EventType.PLAYER_JOIN)
    async def on_player_join(event: LogEvent):
        print(f"[+] Joueur connecté: {event.data.get('player')}")

    @parser.on(EventType.PLAYER_LEAVE)
    async def on_player_leave(event: LogEvent):
        print(f"[-] Joueur déconnecté: {event.data.get('player')}")

    @parser.on(EventType.PLAYER_DEATH)
    async def on_player_death(event: LogEvent):
        player = event.data.get('player', 'Unknown')
        cause = event.data.get('cause', 'unknown')
        killer = event.data.get('killer')
        if killer:
            print(f"[X] {player} a été tué par {killer}")
        else:
            print(f"[X] {player} est mort ({cause})")

    @parser.on(EventType.PLAYER_CHAT)
    async def on_chat(event: LogEvent):
        player = event.data.get('player')
        message = event.data.get('chat_message')
        print(f"[Chat] <{player}> {message}")

    @parser.on(EventType.SERVER_STARTED)
    async def on_server_started(event: LogEvent):
        print("[Server] Serveur démarré!")

    @parser.on(EventType.ERROR)
    async def on_error(event: LogEvent):
        print(f"[ERROR] {event.data.get('message')}")

    # Exemple de surveillance
    log_path = Path("logs/latest.log")
    if log_path.exists():
        print("Surveillance du fichier de log...")
        await parser.watch_log(log_path, from_beginning=True)
    else:
        print(f"Fichier de log non trouvé: {log_path}")
        # Démonstration du parsing manuel
        test_lines = [
            "[12:34:56] [Server thread/INFO] [minecraft/MinecraftServer]: Steve[/127.0.0.1:12345] logged in with entity id 123",
            "[12:35:00] [Server thread/INFO] [minecraft/MinecraftServer]: <Steve> Hello everyone!",
            "[12:36:00] [Server thread/INFO] [minecraft/MinecraftServer]: Steve was slain by Zombie",
            "[12:37:00] [Server thread/INFO] [minecraft/MinecraftServer]: Steve has made the advancement [Stone Age]",
            "[12:38:00] [Server thread/INFO] [minecraft/MinecraftServer]: Steve left the game",
        ]
        print("\nDémonstration avec des lignes de test:")
        for line in test_lines:
            event = parser.parse_line(line)
            if event:
                await parser._dispatch_event(event)


if __name__ == "__main__":
    asyncio.run(main())
