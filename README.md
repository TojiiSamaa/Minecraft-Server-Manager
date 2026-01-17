# Minecraft Server Manager

A complete solution to manage a Minecraft server with a Discord bot, web dashboard, and Docker infrastructure.

## Features

### Discord Bot (Python)
- **Server Control**: Start, stop, restart via Discord commands
- **RCON Commands**: Execute Minecraft commands directly from Discord
- **Player Management**: Whitelist, bans, operators, teleportation
- **Real-time Monitoring**: TPS, RAM, CPU with alerts
- **Notifications**: Player joins/leaves, deaths, achievements, chat relay
- **Logging**: Complete audit system with Discord + files + database

### Web Dashboard (Next.js)
- **Discord OAuth**: Secure authentication via Discord
- **Server Management**: Visual control panel
- **Live Console**: Real-time server logs
- **Configuration Editor**: Edit server.properties from the web
- **Backup Management**: Create, list, restore backups

### Infrastructure (Docker)
- **Minecraft Server**: NeoForge/Forge support for mods
- **PostgreSQL**: Persistent data storage
- **Redis**: Caching and pub/sub
- **Isolated Networks**: Secure by default

## Quick Start

### Prerequisites
- Docker & Docker Compose v2
- Git
- Discord Bot Token ([Discord Developer Portal](https://discord.com/developers/applications))

### Installation

**Windows (PowerShell)**
```powershell
cd C:\path\to\project
.\setup.ps1
```

**Linux/macOS (Bash)**
```bash
cd /path/to/project
chmod +x setup.sh
./setup.sh
```

The setup script will:
1. Check and install dependencies automatically
2. Ask for your project name and Discord credentials
3. Generate secure passwords (RCON, PostgreSQL, Redis, etc.)
4. Create all configuration files
5. Verify the installation

### Launch

```bash
docker compose up -d
```

## Project Structure

```
├── bot/                    # Discord bot (Python)
│   ├── src/
│   │   ├── core/          # Bot core (bot.py, rcon_client.py, etc.)
│   │   ├── cogs/          # Commands (server, rcon, players, etc.)
│   │   └── utils/         # Utilities (validators, permissions, etc.)
│   ├── Dockerfile
│   └── requirements.txt
├── web/                    # Web dashboard (Next.js)
│   ├── src/
│   │   ├── app/           # Next.js App Router
│   │   ├── components/    # React components
│   │   └── lib/           # Utilities
│   ├── Dockerfile
│   └── package.json
├── database/              # PostgreSQL initialization
│   └── init/              # SQL scripts (01-init, 02-tables, etc.)
├── minecraft/             # Minecraft server data
│   ├── mods/              # NeoForge mods
│   └── config/            # Server configuration
├── templates/             # Configuration templates
├── docs/                  # Complete documentation
├── logs/                  # Application logs
├── backups/               # Server backups
├── docker-compose.yml     # Production configuration
└── .env                   # Environment variables
```

## Configuration

All configuration is done via environment variables in `.env`:

| Variable | Description |
|----------|-------------|
| `PROJECT_NAME` | Your project name |
| `DISCORD_TOKEN` | Discord bot token |
| `DISCORD_GUILD_ID` | Your Discord server ID |
| `RCON_PASSWORD` | Auto-generated RCON password |
| `POSTGRES_PASSWORD` | Auto-generated database password |

See [docs/configuration.md](docs/configuration.md) for the complete list.

## Discord Commands

| Command | Description | Permission |
|---------|-------------|------------|
| `/server status` | Server status | Everyone |
| `/server start` | Start server | Admin |
| `/server stop` | Stop server | Admin |
| `/rcon execute <cmd>` | RCON command | Owner |
| `/players list` | Online players | Everyone |
| `/whitelist add <player>` | Add to whitelist | Admin |
| `/ban <player>` | Ban a player | Moderator |
| `/stats` | TPS/RAM/CPU stats | Everyone |
| `/logs view` | View recent logs | Moderator |
| `/notifications configure` | Setup notifications | Admin |

See [docs/bot/commands.md](docs/bot/commands.md) for all commands.

## Security

This project includes several security measures:

- **Input Validation**: All RCON inputs are validated and sanitized
- **Role-based Permissions**: Discord role IDs for access control
- **Network Isolation**: Internal Docker network for databases
- **SQL Roles**: PostgreSQL roles with minimal privileges
- **Sensitive Data Masking**: Passwords hidden in logs
- **Resource Limits**: CPU/RAM limits on all containers

## Documentation

Complete documentation is available in the [docs/](docs/) folder:

- [Installation Guide](docs/installation.md)
- [Configuration Reference](docs/configuration.md)
- [Bot Commands](docs/bot/commands.md)
- [Permissions System](docs/bot/permissions.md)
- [Notifications](docs/bot/notifications.md)
- [Docker Services](docs/docker/services.md)
- [Troubleshooting](docs/troubleshooting.md)

## Development

```bash
# Start in development mode
docker compose -f docker-compose.yml -f docker-compose.override.yml up

# Access services
# - Web Dashboard: http://localhost:3000
# - Adminer (DB): http://localhost:8080
# - Redis Commander: http://localhost:8081
# - Minecraft: localhost:25565
```

## Contributing

Contributions are welcome! Please read the documentation before submitting a PR.

## License

MIT License - See [LICENSE](LICENSE) for details.
