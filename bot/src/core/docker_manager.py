"""
Docker Manager - Gestionnaire Docker pour contrôler le container Minecraft.

Ce module fournit une interface asynchrone pour gérer le cycle de vie
du container Docker Minecraft, incluant le monitoring et les health checks.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

import docker
from docker.errors import APIError, DockerException, NotFound
from docker.models.containers import Container

logger = logging.getLogger(__name__)


class ContainerState(Enum):
    """États possibles du container Docker."""

    RUNNING = "running"
    STOPPED = "stopped"
    PAUSED = "paused"
    RESTARTING = "restarting"
    EXITED = "exited"
    DEAD = "dead"
    CREATED = "created"
    REMOVING = "removing"
    UNKNOWN = "unknown"


@dataclass
class ContainerStatus:
    """Statut détaillé du container."""

    state: ContainerState
    health: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    exit_code: Optional[int] = None
    error: Optional[str] = None
    restart_count: int = 0

    @property
    def is_running(self) -> bool:
        """Vérifie si le container est en cours d'exécution."""
        return self.state == ContainerState.RUNNING

    @property
    def is_healthy(self) -> bool:
        """Vérifie si le container est en bonne santé."""
        return self.is_running and self.health in (None, "healthy")


@dataclass
class ContainerStats:
    """Statistiques de ressources du container."""

    cpu_percent: float = 0.0
    memory_usage: int = 0
    memory_limit: int = 0
    memory_percent: float = 0.0
    network_rx_bytes: int = 0
    network_tx_bytes: int = 0
    block_read_bytes: int = 0
    block_write_bytes: int = 0
    pids: int = 0
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def memory_usage_mb(self) -> float:
        """Retourne l'utilisation mémoire en Mo."""
        return self.memory_usage / (1024 * 1024)

    @property
    def memory_limit_mb(self) -> float:
        """Retourne la limite mémoire en Mo."""
        return self.memory_limit / (1024 * 1024)


class DockerError(Exception):
    """Exception de base pour les erreurs Docker."""
    pass


class ContainerNotFoundError(DockerError):
    """Le container n'a pas été trouvé."""
    pass


class DockerConnectionError(DockerError):
    """Erreur de connexion au daemon Docker."""
    pass


class ContainerOperationError(DockerError):
    """Erreur lors d'une opération sur le container."""
    pass


# Type alias pour les callbacks d'événements
StateChangeCallback = Callable[[ContainerState, ContainerState], None]


class DockerManager:
    """
    Gestionnaire Docker pour contrôler le container Minecraft.

    Cette classe fournit une interface asynchrone pour gérer le cycle de vie
    du container Docker, avec support pour les événements et le monitoring.

    Attributes:
        project_name: Nom du projet (utilisé pour le nom du container)
        container_name: Nom complet du container

    Example:
        ```python
        manager = DockerManager(project_name="myserver")
        await manager.connect()

        status = await manager.get_status()
        if not status.is_running:
            await manager.start()

        # Écouter les changements d'état
        def on_state_change(old_state, new_state):
            print(f"État changé: {old_state} -> {new_state}")

        manager.add_state_listener(on_state_change)
        ```
    """

    def __init__(
        self,
        project_name: str = "minecraft",
        container_suffix: str = "minecraft",
        docker_base_url: Optional[str] = None,
    ):
        """
        Initialise le gestionnaire Docker.

        Args:
            project_name: Nom du projet (sera converti en minuscules)
            container_suffix: Suffixe du nom du container
            docker_base_url: URL du socket Docker (None pour auto-détection)
        """
        self._project_name = project_name.lower()
        self._container_suffix = container_suffix
        self._docker_base_url = docker_base_url

        self._client: Optional[docker.DockerClient] = None
        self._container: Optional[Container] = None
        self._connected = False
        self._current_state: ContainerState = ContainerState.UNKNOWN

        # Listeners pour les événements de changement d'état
        self._state_listeners: list[StateChangeCallback] = []

        # Task de monitoring
        self._monitor_task: Optional[asyncio.Task] = None
        self._monitoring = False

        # Lock pour les opérations thread-safe
        self._lock = asyncio.Lock()

    @property
    def container_name(self) -> str:
        """Retourne le nom complet du container."""
        return f"{self._project_name}-{self._container_suffix}"

    @property
    def project_name(self) -> str:
        """Retourne le nom du projet."""
        return self._project_name

    @property
    def is_connected(self) -> bool:
        """Vérifie si la connexion Docker est établie."""
        return self._connected and self._client is not None

    @property
    def current_state(self) -> ContainerState:
        """Retourne l'état actuel du container."""
        return self._current_state

    async def connect(self) -> None:
        """
        Établit la connexion au daemon Docker.

        Raises:
            DockerConnectionError: Si la connexion échoue
        """
        async with self._lock:
            if self._connected:
                return

            try:
                loop = asyncio.get_event_loop()

                # Création du client Docker dans un executor
                if self._docker_base_url:
                    self._client = await loop.run_in_executor(
                        None,
                        lambda: docker.DockerClient(base_url=self._docker_base_url)
                    )
                else:
                    self._client = await loop.run_in_executor(
                        None,
                        docker.from_env
                    )

                # Test de la connexion
                await loop.run_in_executor(None, self._client.ping)

                self._connected = True
                logger.info("Connexion Docker établie avec succès")

                # Récupération du container
                await self._refresh_container()

            except DockerException as e:
                self._connected = False
                self._client = None
                raise DockerConnectionError(
                    f"Impossible de se connecter au daemon Docker: {e}"
                ) from e

    async def disconnect(self) -> None:
        """Ferme la connexion Docker proprement."""
        async with self._lock:
            await self.stop_monitoring()

            if self._client:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._client.close)
                self._client = None

            self._container = None
            self._connected = False
            self._current_state = ContainerState.UNKNOWN

            logger.info("Connexion Docker fermée")

    async def _refresh_container(self) -> Optional[Container]:
        """
        Rafraîchit la référence au container.

        Returns:
            Le container si trouvé, None sinon
        """
        if not self._client:
            return None

        try:
            loop = asyncio.get_event_loop()
            self._container = await loop.run_in_executor(
                None,
                lambda: self._client.containers.get(self.container_name)
            )
            return self._container
        except NotFound:
            self._container = None
            return None
        except APIError as e:
            logger.error(f"Erreur API Docker lors de la récupération du container: {e}")
            return None

    def _ensure_connected(self) -> None:
        """Vérifie que la connexion est établie."""
        if not self.is_connected:
            raise DockerConnectionError("Non connecté au daemon Docker")

    async def get_status(self) -> ContainerStatus:
        """
        Récupère le statut détaillé du container.

        Returns:
            ContainerStatus avec l'état actuel du container

        Raises:
            DockerConnectionError: Si non connecté
            ContainerNotFoundError: Si le container n'existe pas
        """
        self._ensure_connected()

        container = await self._refresh_container()
        if not container:
            raise ContainerNotFoundError(
                f"Container '{self.container_name}' non trouvé"
            )

        loop = asyncio.get_event_loop()

        # Recharger les attributs du container
        await loop.run_in_executor(None, container.reload)

        attrs = container.attrs
        state_info = attrs.get("State", {})

        # Parser l'état
        state_str = state_info.get("Status", "unknown").lower()
        try:
            state = ContainerState(state_str)
        except ValueError:
            state = ContainerState.UNKNOWN

        # Parser les dates
        started_at = None
        finished_at = None

        if state_info.get("StartedAt"):
            try:
                started_at = datetime.fromisoformat(
                    state_info["StartedAt"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        if state_info.get("FinishedAt"):
            try:
                finished_at = datetime.fromisoformat(
                    state_info["FinishedAt"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        # Health check status
        health_info = state_info.get("Health", {})
        health_status = health_info.get("Status") if health_info else None

        # Mettre à jour l'état actuel et notifier si changement
        old_state = self._current_state
        self._current_state = state

        if old_state != state:
            await self._notify_state_change(old_state, state)

        return ContainerStatus(
            state=state,
            health=health_status,
            started_at=started_at,
            finished_at=finished_at,
            exit_code=state_info.get("ExitCode"),
            error=state_info.get("Error"),
            restart_count=attrs.get("RestartCount", 0),
        )

    async def start(self) -> bool:
        """
        Démarre le container.

        Returns:
            True si le container a été démarré avec succès

        Raises:
            DockerConnectionError: Si non connecté
            ContainerNotFoundError: Si le container n'existe pas
            ContainerOperationError: Si le démarrage échoue
        """
        self._ensure_connected()

        container = await self._refresh_container()
        if not container:
            raise ContainerNotFoundError(
                f"Container '{self.container_name}' non trouvé"
            )

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, container.start)

            logger.info(f"Container '{self.container_name}' démarré")

            # Attendre que le container soit running
            await self._wait_for_state(ContainerState.RUNNING, timeout=30)

            return True

        except APIError as e:
            raise ContainerOperationError(
                f"Échec du démarrage du container: {e}"
            ) from e

    async def stop(self, timeout: int = 30) -> bool:
        """
        Arrête le container proprement.

        Args:
            timeout: Temps d'attente avant force kill (secondes)

        Returns:
            True si le container a été arrêté avec succès

        Raises:
            DockerConnectionError: Si non connecté
            ContainerNotFoundError: Si le container n'existe pas
            ContainerOperationError: Si l'arrêt échoue
        """
        self._ensure_connected()

        container = await self._refresh_container()
        if not container:
            raise ContainerNotFoundError(
                f"Container '{self.container_name}' non trouvé"
            )

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: container.stop(timeout=timeout)
            )

            logger.info(f"Container '{self.container_name}' arrêté")
            return True

        except APIError as e:
            raise ContainerOperationError(
                f"Échec de l'arrêt du container: {e}"
            ) from e

    async def restart(self, timeout: int = 30) -> bool:
        """
        Redémarre le container.

        Args:
            timeout: Temps d'attente pour l'arrêt avant force kill

        Returns:
            True si le container a été redémarré avec succès

        Raises:
            DockerConnectionError: Si non connecté
            ContainerNotFoundError: Si le container n'existe pas
            ContainerOperationError: Si le redémarrage échoue
        """
        self._ensure_connected()

        container = await self._refresh_container()
        if not container:
            raise ContainerNotFoundError(
                f"Container '{self.container_name}' non trouvé"
            )

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: container.restart(timeout=timeout)
            )

            logger.info(f"Container '{self.container_name}' redémarré")

            # Attendre que le container soit running
            await self._wait_for_state(ContainerState.RUNNING, timeout=60)

            return True

        except APIError as e:
            raise ContainerOperationError(
                f"Échec du redémarrage du container: {e}"
            ) from e

    async def get_logs(
        self,
        lines: int = 100,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        timestamps: bool = False,
    ) -> str:
        """
        Récupère les derniers logs du container.

        Args:
            lines: Nombre de lignes à récupérer
            since: Récupérer les logs depuis cette date
            until: Récupérer les logs jusqu'à cette date
            timestamps: Inclure les timestamps

        Returns:
            Les logs du container en tant que chaîne de caractères

        Raises:
            DockerConnectionError: Si non connecté
            ContainerNotFoundError: Si le container n'existe pas
        """
        self._ensure_connected()

        container = await self._refresh_container()
        if not container:
            raise ContainerNotFoundError(
                f"Container '{self.container_name}' non trouvé"
            )

        loop = asyncio.get_event_loop()

        kwargs: dict[str, Any] = {
            "tail": lines,
            "timestamps": timestamps,
            "stdout": True,
            "stderr": True,
        }

        if since:
            kwargs["since"] = since
        if until:
            kwargs["until"] = until

        logs_bytes = await loop.run_in_executor(
            None,
            lambda: container.logs(**kwargs)
        )

        if isinstance(logs_bytes, bytes):
            return logs_bytes.decode("utf-8", errors="replace")
        return str(logs_bytes)

    async def get_stats(self, stream: bool = False) -> ContainerStats:
        """
        Récupère les statistiques de ressources du container.

        Args:
            stream: Si False, retourne un snapshot unique

        Returns:
            ContainerStats avec les métriques actuelles

        Raises:
            DockerConnectionError: Si non connecté
            ContainerNotFoundError: Si le container n'existe pas
        """
        self._ensure_connected()

        container = await self._refresh_container()
        if not container:
            raise ContainerNotFoundError(
                f"Container '{self.container_name}' non trouvé"
            )

        loop = asyncio.get_event_loop()

        stats_data = await loop.run_in_executor(
            None,
            lambda: container.stats(stream=stream)
        )

        return self._parse_stats(stats_data)

    def _parse_stats(self, stats_data: dict) -> ContainerStats:
        """Parse les données brutes de stats en ContainerStats."""
        # CPU
        cpu_delta = (
            stats_data.get("cpu_stats", {}).get("cpu_usage", {}).get("total_usage", 0) -
            stats_data.get("precpu_stats", {}).get("cpu_usage", {}).get("total_usage", 0)
        )
        system_delta = (
            stats_data.get("cpu_stats", {}).get("system_cpu_usage", 0) -
            stats_data.get("precpu_stats", {}).get("system_cpu_usage", 0)
        )

        num_cpus = len(
            stats_data.get("cpu_stats", {}).get("cpu_usage", {}).get("percpu_usage", [1])
        ) or 1

        cpu_percent = 0.0
        if system_delta > 0 and cpu_delta > 0:
            cpu_percent = (cpu_delta / system_delta) * num_cpus * 100.0

        # Mémoire
        memory_stats = stats_data.get("memory_stats", {})
        memory_usage = memory_stats.get("usage", 0)
        memory_limit = memory_stats.get("limit", 1)

        # Soustraire le cache si disponible
        cache = memory_stats.get("stats", {}).get("cache", 0)
        memory_usage = max(0, memory_usage - cache)

        memory_percent = (memory_usage / memory_limit) * 100.0 if memory_limit > 0 else 0.0

        # Réseau
        networks = stats_data.get("networks", {})
        rx_bytes = sum(net.get("rx_bytes", 0) for net in networks.values())
        tx_bytes = sum(net.get("tx_bytes", 0) for net in networks.values())

        # Block I/O
        blkio_stats = stats_data.get("blkio_stats", {})
        io_service_bytes = blkio_stats.get("io_service_bytes_recursive", []) or []

        read_bytes = sum(
            entry.get("value", 0)
            for entry in io_service_bytes
            if entry.get("op", "").lower() == "read"
        )
        write_bytes = sum(
            entry.get("value", 0)
            for entry in io_service_bytes
            if entry.get("op", "").lower() == "write"
        )

        # PIDs
        pids = stats_data.get("pids_stats", {}).get("current", 0)

        return ContainerStats(
            cpu_percent=round(cpu_percent, 2),
            memory_usage=memory_usage,
            memory_limit=memory_limit,
            memory_percent=round(memory_percent, 2),
            network_rx_bytes=rx_bytes,
            network_tx_bytes=tx_bytes,
            block_read_bytes=read_bytes,
            block_write_bytes=write_bytes,
            pids=pids,
        )

    async def health_check(self) -> tuple[bool, str]:
        """
        Effectue un health check du container.

        Returns:
            Tuple (is_healthy, message) avec le statut et un message descriptif
        """
        try:
            status = await self.get_status()

            if not status.is_running:
                return False, f"Container non running (état: {status.state.value})"

            if status.health == "unhealthy":
                return False, "Container signalé comme unhealthy"

            if status.health == "starting":
                return True, "Container en cours de démarrage (health check en attente)"

            # Vérifier les stats pour s'assurer que le container répond
            try:
                stats = await self.get_stats()
                if stats.memory_usage > 0:
                    return True, f"Container healthy (CPU: {stats.cpu_percent}%, RAM: {stats.memory_percent}%)"
            except Exception as e:
                logger.warning(f"Impossible de récupérer les stats: {e}")

            return True, "Container running"

        except ContainerNotFoundError:
            return False, f"Container '{self.container_name}' non trouvé"
        except DockerConnectionError as e:
            return False, f"Erreur de connexion Docker: {e}"
        except Exception as e:
            return False, f"Erreur lors du health check: {e}"

    async def _wait_for_state(
        self,
        target_state: ContainerState,
        timeout: float = 30,
        poll_interval: float = 0.5,
    ) -> bool:
        """
        Attend que le container atteigne un état spécifique.

        Args:
            target_state: L'état cible à attendre
            timeout: Temps maximum d'attente en secondes
            poll_interval: Intervalle entre les vérifications

        Returns:
            True si l'état a été atteint, False si timeout
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            try:
                status = await self.get_status()
                if status.state == target_state:
                    return True
            except Exception:
                pass

            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                return False

            await asyncio.sleep(poll_interval)

    def add_state_listener(self, callback: StateChangeCallback) -> None:
        """
        Ajoute un listener pour les changements d'état.

        Args:
            callback: Fonction appelée lors d'un changement d'état
                     Signature: callback(old_state, new_state)
        """
        if callback not in self._state_listeners:
            self._state_listeners.append(callback)

    def remove_state_listener(self, callback: StateChangeCallback) -> None:
        """
        Supprime un listener de changement d'état.

        Args:
            callback: Le callback à supprimer
        """
        if callback in self._state_listeners:
            self._state_listeners.remove(callback)

    async def _notify_state_change(
        self,
        old_state: ContainerState,
        new_state: ContainerState,
    ) -> None:
        """Notifie tous les listeners d'un changement d'état."""
        logger.info(
            f"État du container changé: {old_state.value} -> {new_state.value}"
        )

        for callback in self._state_listeners:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(old_state, new_state)
                else:
                    callback(old_state, new_state)
            except Exception as e:
                logger.error(f"Erreur dans le listener d'état: {e}")

    async def start_monitoring(
        self,
        interval: float = 5.0,
        health_check: bool = True,
    ) -> None:
        """
        Démarre le monitoring continu du container.

        Args:
            interval: Intervalle entre les vérifications (secondes)
            health_check: Effectuer des health checks périodiques
        """
        if self._monitoring:
            return

        self._monitoring = True
        self._monitor_task = asyncio.create_task(
            self._monitor_loop(interval, health_check)
        )
        logger.info("Monitoring du container démarré")

    async def stop_monitoring(self) -> None:
        """Arrête le monitoring du container."""
        self._monitoring = False

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None

        logger.info("Monitoring du container arrêté")

    async def _monitor_loop(
        self,
        interval: float,
        health_check: bool,
    ) -> None:
        """Boucle de monitoring interne."""
        while self._monitoring:
            try:
                # Récupérer le statut (déclenche les notifications si changement)
                await self.get_status()

                # Health check optionnel
                if health_check:
                    is_healthy, message = await self.health_check()
                    if not is_healthy:
                        logger.warning(f"Health check échoué: {message}")

            except ContainerNotFoundError:
                logger.warning(f"Container '{self.container_name}' non trouvé")
            except DockerConnectionError as e:
                logger.error(f"Perte de connexion Docker: {e}")
            except Exception as e:
                logger.error(f"Erreur de monitoring: {e}")

            await asyncio.sleep(interval)

    async def execute_command(
        self,
        command: str | list[str],
        workdir: Optional[str] = None,
        environment: Optional[dict[str, str]] = None,
        user: str = "",
        detach: bool = False,
    ) -> tuple[int, str]:
        """
        Exécute une commande dans le container.

        Args:
            command: Commande à exécuter (string ou liste)
            workdir: Répertoire de travail
            environment: Variables d'environnement
            user: Utilisateur pour l'exécution
            detach: Exécuter en arrière-plan

        Returns:
            Tuple (exit_code, output)

        Raises:
            DockerConnectionError: Si non connecté
            ContainerNotFoundError: Si le container n'existe pas
            ContainerOperationError: Si l'exécution échoue
        """
        self._ensure_connected()

        container = await self._refresh_container()
        if not container:
            raise ContainerNotFoundError(
                f"Container '{self.container_name}' non trouvé"
            )

        try:
            loop = asyncio.get_event_loop()

            kwargs: dict[str, Any] = {
                "cmd": command,
                "detach": detach,
            }

            if workdir:
                kwargs["workdir"] = workdir
            if environment:
                kwargs["environment"] = environment
            if user:
                kwargs["user"] = user

            result = await loop.run_in_executor(
                None,
                lambda: container.exec_run(**kwargs)
            )

            if detach:
                return 0, ""

            exit_code = result.exit_code
            output = result.output.decode("utf-8", errors="replace") if result.output else ""

            return exit_code, output

        except APIError as e:
            raise ContainerOperationError(
                f"Échec de l'exécution de la commande: {e}"
            ) from e

    async def __aenter__(self) -> "DockerManager":
        """Support du context manager async."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Ferme la connexion à la sortie du context manager."""
        await self.disconnect()


# Exemple d'utilisation
async def main():
    """Exemple d'utilisation du DockerManager."""
    # Configuration avec le nom du projet
    project_name = "{{PROJECT_NAME_LOWER}}"

    async with DockerManager(project_name=project_name) as manager:
        print(f"Container: {manager.container_name}")

        # Récupérer le statut
        try:
            status = await manager.get_status()
            print(f"État: {status.state.value}")
            print(f"Running: {status.is_running}")
            print(f"Healthy: {status.is_healthy}")

            if status.is_running:
                # Récupérer les stats
                stats = await manager.get_stats()
                print(f"CPU: {stats.cpu_percent}%")
                print(f"RAM: {stats.memory_usage_mb:.1f} MB / {stats.memory_limit_mb:.1f} MB")

                # Récupérer les logs
                logs = await manager.get_logs(lines=10)
                print(f"Derniers logs:\n{logs}")

            # Health check
            is_healthy, message = await manager.health_check()
            print(f"Health: {message}")

        except ContainerNotFoundError:
            print(f"Container non trouvé")
        except DockerConnectionError as e:
            print(f"Erreur Docker: {e}")


if __name__ == "__main__":
    asyncio.run(main())
