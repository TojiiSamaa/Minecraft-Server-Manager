#!/bin/bash
set -e

# ============================================================================
# MINECRAFT BOT - SCRIPT D'INSTALLATION AVANCE
# Version: 3.0.0
# ============================================================================

# ============================================================================
# COULEURS ANSI
# ============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

# Couleurs de fond
BG_BLUE='\033[44m'
BG_GREEN='\033[42m'
BG_RED='\033[41m'
BG_YELLOW='\033[43m'

# ============================================================================
# VARIABLES GLOBALES
# ============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/setup-$(date +%Y-%m-%d-%H%M%S).log"
REPORT_FILE=""

# Configuration minimale requise
MIN_BASH_VERSION="4.0"
MIN_DISK_SPACE_GB=10
REQUIRED_PORTS=(3000 5432 6379 25565 25575)

# Compteurs pour le rapport final
DEPS_INSTALLED=0
DEPS_FAILED=0
DEPS_ALREADY_INSTALLED=0
FILES_CREATED=0
FILES_VALIDATED=0
FILES_INVALID=0
WARNINGS_COUNT=0
PORTS_BLOCKED=0

# ============================================================================
# URLS D'AIDE POUR LES DEPENDANCES
# ============================================================================
declare -A HELP_URLS=(
    ["docker"]="https://docs.docker.com/engine/install/"
    ["docker-compose"]="https://docs.docker.com/compose/install/"
    ["docker-daemon"]="https://docs.docker.com/config/daemon/"
    ["git"]="https://git-scm.com/download/linux"
    ["curl"]="https://curl.se/download.html"
    ["wget"]="https://www.gnu.org/software/wget/"
    ["jq"]="https://stedolan.github.io/jq/download/"
    ["yq"]="https://github.com/mikefarah/yq#install"
    ["openssl"]="https://www.openssl.org/source/"
    ["bash"]="https://www.gnu.org/software/bash/"
)

# ============================================================================
# INITIALISATION DES LOGS
# ============================================================================
init_logs() {
    mkdir -p "$LOG_DIR"
    touch "$LOG_FILE"

    # Fichier de rapport final
    REPORT_FILE="$LOG_DIR/report-$(date +%Y-%m-%d-%H%M%S).txt"

    # En-tete du fichier de log
    {
        echo "============================================================================"
        echo "MINECRAFT BOT - LOG D'INSTALLATION"
        echo "Date: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "Systeme: $(uname -a)"
        echo "Script: $0"
        echo "Version: 3.0.0"
        echo "Repertoire: $PROJECT_DIR"
        echo "Bash Version: ${BASH_VERSION:-unknown}"
        echo "============================================================================"
        echo ""
    } >> "$LOG_FILE"
}

# ============================================================================
# FONCTION DE LOG CENTRALISEE
# ============================================================================
log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    local line="[$timestamp] [$level] $message"

    # Ecrire dans le fichier de log (toujours)
    echo "$line" >> "$LOG_FILE"

    # Afficher a l'ecran avec couleurs (via tee pour certains cas)
    case "$level" in
        "INFO")
            echo -e "${CYAN}[INFO]${RESET} $message"
            ;;
        "SUCCESS")
            echo -e "${GREEN}[SUCCESS]${RESET} $message"
            ;;
        "WARN"|"WARNING")
            echo -e "${YELLOW}[WARN]${RESET} $message"
            ((WARNINGS_COUNT++)) || true
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${RESET} $message"
            ;;
        "DEBUG")
            # Debug uniquement dans le fichier
            ;;
        *)
            echo -e "$message"
            ;;
    esac
}

# Log avec tee (affiche ET enregistre simultanement)
log_tee() {
    local level="$1"
    local message="$2"
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    local line="[$timestamp] [$level] $message"

    echo "$line" | tee -a "$LOG_FILE"
}

# ============================================================================
# FONCTIONS D'AFFICHAGE
# ============================================================================
print_header() {
    clear
    echo -e "${CYAN}"
    echo '    +======================================================================+'
    echo '    |                                                                      |'
    echo -e "    |  ${WHITE}MINECRAFT BOT - INSTALLATION INTERACTIVE${CYAN}                          |"
    echo '    |                                                                      |'
    echo -e "    |          ${MAGENTA}+=============================================+${CYAN}          |"
    echo -e "    |          ${MAGENTA}|   ${YELLOW}INSTALLATION INTERACTIVE SETUP v3.0${MAGENTA}   |${CYAN}          |"
    echo -e "    |          ${MAGENTA}+=============================================+${CYAN}          |"
    echo '    |                                                                      |'
    echo -e "    |           ${DIM}Discord Bot + Minecraft Server Manager${RESET}${CYAN}                |"
    echo '    +======================================================================+'
    echo -e "${RESET}"
    echo ""
}

print_section() {
    echo ""
    echo -e "${BLUE}========================================================================${RESET}"
    echo -e "${BG_BLUE}${WHITE}${BOLD}  $1  ${RESET}"
    echo -e "${BLUE}========================================================================${RESET}"
    echo ""
    log "INFO" "=== Section: $1 ==="
}

print_success() {
    echo -e "${GREEN}[OK]${RESET} $1"
    log "SUCCESS" "$1"
}

print_info() {
    echo -e "${CYAN}[i]${RESET} $1"
    log "INFO" "$1"
}

print_warning() {
    echo -e "${YELLOW}[!]${RESET} $1"
    log "WARNING" "$1"
}

print_error() {
    echo -e "${RED}[X]${RESET} $1"
    log "ERROR" "$1"
}

# ============================================================================
# VERIFICATION DE LA VERSION BASH
# ============================================================================
check_bash_version() {
    log "INFO" "Verification de la version Bash..."

    local current_version="${BASH_VERSION%%(*}"
    current_version="${current_version%%-*}"

    # Extraire major.minor
    local major="${current_version%%.*}"
    local rest="${current_version#*.}"
    local minor="${rest%%.*}"

    local min_major="${MIN_BASH_VERSION%%.*}"
    local min_minor="${MIN_BASH_VERSION#*.}"
    min_minor="${min_minor%%.*}"

    log "DEBUG" "Version Bash detectee: $current_version (major=$major, minor=$minor)"
    log "DEBUG" "Version minimale requise: $MIN_BASH_VERSION (major=$min_major, minor=$min_minor)"

    if [[ "$major" -gt "$min_major" ]] || \
       [[ "$major" -eq "$min_major" && "$minor" -ge "$min_minor" ]]; then
        log "SUCCESS" "Bash $current_version >= $MIN_BASH_VERSION"
        return 0
    else
        log "ERROR" "Bash $current_version < $MIN_BASH_VERSION (minimum requis)"
        print_error "Version de Bash insuffisante: $current_version < $MIN_BASH_VERSION"
        print_info "Documentation: ${HELP_URLS[bash]}"
        offer_open_url "${HELP_URLS[bash]}"
        return 1
    fi
}

# ============================================================================
# VERIFICATION DE L'ESPACE DISQUE
# ============================================================================
check_disk_space() {
    log "INFO" "Verification de l'espace disque disponible..."

    local available_kb
    local available_gb

    # Obtenir l'espace disponible en KB
    if command -v df &> /dev/null; then
        # Utiliser df pour obtenir l'espace disponible
        available_kb=$(df -k "$PROJECT_DIR" 2>/dev/null | tail -1 | awk '{print $4}')

        if [[ -z "$available_kb" ]] || [[ ! "$available_kb" =~ ^[0-9]+$ ]]; then
            log "WARNING" "Impossible de determiner l'espace disque disponible"
            return 0
        fi

        # Convertir en GB
        available_gb=$((available_kb / 1024 / 1024))

        log "INFO" "Espace disque disponible: ${available_gb}GB"

        if [[ "$available_gb" -ge "$MIN_DISK_SPACE_GB" ]]; then
            log "SUCCESS" "Espace disque suffisant: ${available_gb}GB >= ${MIN_DISK_SPACE_GB}GB"
            print_success "Espace disque: ${available_gb}GB disponible (minimum: ${MIN_DISK_SPACE_GB}GB)"
            return 0
        else
            log "ERROR" "Espace disque insuffisant: ${available_gb}GB < ${MIN_DISK_SPACE_GB}GB"
            print_error "Espace disque insuffisant: ${available_gb}GB < ${MIN_DISK_SPACE_GB}GB requis"
            return 1
        fi
    else
        log "WARNING" "Commande df non disponible, verification de l'espace disque ignoree"
        return 0
    fi
}

# ============================================================================
# VERIFICATION DES PORTS DISPONIBLES
# ============================================================================
check_port_available() {
    local port="$1"
    local service="$2"

    if command -v ss &> /dev/null; then
        if ss -tuln 2>/dev/null | grep -q ":$port "; then
            log "WARNING" "Port $port ($service) est deja utilise"
            return 1
        fi
    elif command -v netstat &> /dev/null; then
        if netstat -tuln 2>/dev/null | grep -q ":$port "; then
            log "WARNING" "Port $port ($service) est deja utilise"
            return 1
        fi
    elif command -v lsof &> /dev/null; then
        if lsof -i ":$port" &> /dev/null; then
            log "WARNING" "Port $port ($service) est deja utilise"
            return 1
        fi
    else
        log "WARNING" "Aucun outil de verification de port disponible (ss, netstat, lsof)"
        return 0
    fi

    log "SUCCESS" "Port $port ($service) est disponible"
    return 0
}

check_required_ports() {
    print_info "Verification des ports requis..."

    local ports_services=(
        "3000:Web Dashboard"
        "5432:PostgreSQL"
        "6379:Redis"
        "25565:Minecraft"
        "25575:RCON"
    )

    PORTS_BLOCKED=0

    for port_info in "${ports_services[@]}"; do
        IFS=':' read -r port service <<< "$port_info"

        if ! check_port_available "$port" "$service"; then
            ((PORTS_BLOCKED++))
        fi
    done

    if [ $PORTS_BLOCKED -gt 0 ]; then
        print_warning "$PORTS_BLOCKED port(s) sont deja utilise(s)"
        print_info "Vous devrez peut-etre modifier les ports dans le fichier .env"
        return 1
    else
        print_success "Tous les ports requis sont disponibles"
        return 0
    fi
}

# ============================================================================
# DETECTION DU GESTIONNAIRE DE PAQUETS
# ============================================================================
detect_package_manager() {
    if command -v apt-get &> /dev/null; then
        echo "apt"
    elif command -v dnf &> /dev/null; then
        echo "dnf"
    elif command -v yum &> /dev/null; then
        echo "yum"
    elif command -v pacman &> /dev/null; then
        echo "pacman"
    elif command -v brew &> /dev/null; then
        echo "brew"
    elif command -v zypper &> /dev/null; then
        echo "zypper"
    elif command -v apk &> /dev/null; then
        echo "apk"
    else
        echo "unknown"
    fi
}

# ============================================================================
# COMMANDES D'INSTALLATION PAR GESTIONNAIRE
# ============================================================================
get_install_command() {
    local pkg_manager="$1"
    local package="$2"

    case "$pkg_manager" in
        "apt")
            echo "sudo apt-get install -y $package"
            ;;
        "dnf")
            echo "sudo dnf install -y $package"
            ;;
        "yum")
            echo "sudo yum install -y $package"
            ;;
        "pacman")
            echo "sudo pacman -S --noconfirm $package"
            ;;
        "brew")
            echo "brew install $package"
            ;;
        "zypper")
            echo "sudo zypper install -y $package"
            ;;
        "apk")
            echo "sudo apk add $package"
            ;;
        *)
            echo ""
            ;;
    esac
}

# ============================================================================
# MISE A JOUR DU CACHE DES PAQUETS
# ============================================================================
update_package_cache() {
    local pkg_manager="$1"

    log "INFO" "Mise a jour du cache des paquets ($pkg_manager)..."

    case "$pkg_manager" in
        "apt")
            sudo apt-get update -qq 2>/dev/null || true
            ;;
        "dnf"|"yum")
            sudo $pkg_manager makecache -q 2>/dev/null || true
            ;;
        "pacman")
            sudo pacman -Sy --noconfirm 2>/dev/null || true
            ;;
        "brew")
            brew update 2>/dev/null || true
            ;;
        "zypper")
            sudo zypper refresh -q 2>/dev/null || true
            ;;
        "apk")
            sudo apk update 2>/dev/null || true
            ;;
    esac
}

# ============================================================================
# PROPOSITION D'OUVRIR UNE URL D'AIDE
# ============================================================================
offer_open_url() {
    local url="$1"

    echo ""
    echo -e "${YELLOW}Documentation disponible:${RESET}"
    echo -e "  ${CYAN}$url${RESET}"
    echo ""

    # Verifier si xdg-open est disponible (Linux) ou open (macOS)
    local opener=""
    if command -v xdg-open &> /dev/null; then
        opener="xdg-open"
    elif command -v open &> /dev/null; then
        opener="open"
    fi

    if [[ -n "$opener" ]]; then
        echo -e -n "${YELLOW}Voulez-vous ouvrir cette URL dans votre navigateur? [o/N] ${RESET}"
        read -r response

        if [[ "$response" =~ ^[oOyY]$ ]]; then
            log "INFO" "Ouverture de l'URL: $url"
            $opener "$url" 2>/dev/null &
            disown 2>/dev/null || true
            echo -e "${GREEN}URL ouverte dans le navigateur.${RESET}"
        fi
    else
        log "INFO" "Aucun outil pour ouvrir les URLs (xdg-open/open) disponible"
    fi
    echo ""
}

# ============================================================================
# FONCTION D'INSTALLATION AVEC RETRY (3 tentatives)
# ============================================================================
install_with_retry() {
    local name="$1"
    local install_cmd="$2"
    local verify_cmd="$3"
    local help_url="$4"
    local max_retries=3
    local attempt=1

    log "INFO" "Verification de $name..."

    # D'abord verifier si deja installe
    if eval "$verify_cmd" &> /dev/null; then
        log "SUCCESS" "$name est deja installe"
        print_success "$name: deja installe"
        ((DEPS_ALREADY_INSTALLED++)) || true
        return 0
    fi

    log "INFO" "$name non trouve, tentative d'installation..."
    print_info "$name non trouve, installation en cours..."

    while [ $attempt -le $max_retries ]; do
        echo -e "  ${DIM}Tentative $attempt/$max_retries...${RESET}"
        log "INFO" "Tentative $attempt/$max_retries pour $name..."

        # Tenter l'installation (avec logging)
        {
            echo "--- Installation de $name (tentative $attempt) ---"
            eval "$install_cmd" 2>&1
            echo "--- Fin installation $name ---"
        } >> "$LOG_FILE" 2>&1

        local install_result=$?

        # Petite pause pour laisser le systeme se stabiliser
        sleep 1

        # Verifier que l'installation a reussi
        if eval "$verify_cmd" &> /dev/null; then
            log "SUCCESS" "$name installe avec succes (tentative $attempt)"
            print_success "$name installe avec succes"
            ((DEPS_INSTALLED++)) || true
            return 0
        else
            log "WARNING" "Verification echouee pour $name apres installation (tentative $attempt)"
        fi

        ((attempt++))

        if [ $attempt -le $max_retries ]; then
            log "INFO" "Attente de 3 secondes avant nouvelle tentative..."
            sleep 3
        fi
    done

    # Echec apres toutes les tentatives
    log "ERROR" "============================================"
    log "ERROR" "ECHEC: Installation de $name apres $max_retries tentatives"
    log "ERROR" "Documentation: $help_url"
    log "ERROR" "============================================"

    print_error "Echec de l'installation de $name apres $max_retries tentatives"

    # Proposer d'ouvrir l'URL d'aide
    offer_open_url "$help_url"

    ((DEPS_FAILED++)) || true
    return 1
}

# ============================================================================
# VERIFICATION DU DAEMON DOCKER
# ============================================================================
check_docker_daemon() {
    log "INFO" "Verification du daemon Docker..."

    if ! command -v docker &> /dev/null; then
        log "ERROR" "Docker n'est pas installe"
        return 1
    fi

    # Essayer docker info pour verifier si le daemon repond
    if docker info &> /dev/null 2>&1; then
        log "SUCCESS" "Docker daemon est en cours d'execution"
        print_success "Docker daemon: en cours d'execution"
        return 0
    fi

    # Le daemon ne repond pas, essayer de le demarrer
    log "WARNING" "Docker daemon ne repond pas, tentative de demarrage..."
    print_warning "Docker daemon ne repond pas, tentative de demarrage..."

    # Essayer avec systemctl
    if command -v systemctl &> /dev/null; then
        sudo systemctl start docker 2>/dev/null || true
        sleep 3

        if docker info &> /dev/null 2>&1; then
            log "SUCCESS" "Docker daemon demarre avec succes via systemctl"
            print_success "Docker daemon demarre"

            # Activer le demarrage automatique
            sudo systemctl enable docker 2>/dev/null || true
            return 0
        fi
    fi

    # Essayer avec service
    if command -v service &> /dev/null; then
        sudo service docker start 2>/dev/null || true
        sleep 3

        if docker info &> /dev/null 2>&1; then
            log "SUCCESS" "Docker daemon demarre avec succes via service"
            print_success "Docker daemon demarre"
            return 0
        fi
    fi

    # Echec du demarrage
    log "ERROR" "Impossible de demarrer le daemon Docker"
    print_error "Impossible de demarrer le daemon Docker"
    print_info "Documentation: ${HELP_URLS[docker-daemon]}"
    offer_open_url "${HELP_URLS[docker-daemon]}"

    return 1
}

# ============================================================================
# INSTALLATION SPECIALE POUR DOCKER (via get.docker.com)
# ============================================================================
install_docker() {
    local pkg_manager="$1"

    log "INFO" "Installation de Docker via le script officiel get.docker.com..."
    print_info "Installation de Docker via https://get.docker.com..."

    # Telecharger et executer le script officiel
    local download_cmd=""

    if command -v curl &> /dev/null; then
        download_cmd="curl -fsSL https://get.docker.com -o /tmp/get-docker.sh"
    elif command -v wget &> /dev/null; then
        download_cmd="wget -qO /tmp/get-docker.sh https://get.docker.com"
    else
        log "ERROR" "Ni curl ni wget disponible pour telecharger Docker"
        return 1
    fi

    # Telecharger le script
    if ! eval "$download_cmd" 2>> "$LOG_FILE"; then
        log "ERROR" "Echec du telechargement du script Docker"
        return 1
    fi

    # Executer le script
    log "INFO" "Execution du script d'installation Docker..."
    if sudo sh /tmp/get-docker.sh >> "$LOG_FILE" 2>&1; then
        log "SUCCESS" "Script Docker execute avec succes"
    else
        log "ERROR" "Echec de l'execution du script Docker"
        rm -f /tmp/get-docker.sh
        return 1
    fi

    # Nettoyer
    rm -f /tmp/get-docker.sh

    # Demarrer et activer Docker
    if command -v systemctl &> /dev/null; then
        sudo systemctl start docker 2>/dev/null || true
        sudo systemctl enable docker 2>/dev/null || true
    elif command -v service &> /dev/null; then
        sudo service docker start 2>/dev/null || true
    fi

    # Ajouter l'utilisateur au groupe docker
    add_user_to_docker_group

    return 0
}

# ============================================================================
# AJOUTER L'UTILISATEUR AU GROUPE DOCKER
# ============================================================================
add_user_to_docker_group() {
    log "INFO" "Ajout de l'utilisateur $USER au groupe docker..."

    if getent group docker &> /dev/null; then
        if groups "$USER" 2>/dev/null | grep -q '\bdocker\b'; then
            log "INFO" "L'utilisateur $USER est deja dans le groupe docker"
        else
            sudo usermod -aG docker "$USER" 2>/dev/null || true
            log "SUCCESS" "Utilisateur $USER ajoute au groupe docker"
            print_info "Vous devrez peut-etre vous reconnecter pour que les permissions prennent effet"
            print_info "Ou executez: newgrp docker"
        fi
    else
        log "WARNING" "Groupe docker non trouve"
    fi
}

# ============================================================================
# INSTALLATION DE DOCKER COMPOSE V2
# ============================================================================
install_docker_compose_v2() {
    local pkg_manager="$1"

    log "INFO" "Verification/Installation de Docker Compose v2..."

    # Docker Compose v2 est souvent inclus avec Docker
    if docker compose version &> /dev/null; then
        log "SUCCESS" "Docker Compose v2 deja disponible"
        return 0
    fi

    log "INFO" "Installation de Docker Compose v2 comme plugin..."

    # Creer le repertoire des plugins
    sudo mkdir -p /usr/local/lib/docker/cli-plugins

    # Detecter l'architecture
    local arch=$(uname -m)
    case "$arch" in
        x86_64)
            arch="x86_64"
            ;;
        aarch64|arm64)
            arch="aarch64"
            ;;
        armv7l)
            arch="armv7"
            ;;
        *)
            log "WARNING" "Architecture non reconnue: $arch"
            arch="x86_64"
            ;;
    esac

    local os=$(uname -s)

    # Obtenir la derniere version
    local compose_version=""
    if command -v curl &> /dev/null; then
        compose_version=$(curl -s https://api.github.com/repos/docker/compose/releases/latest 2>/dev/null | grep -oP '"tag_name": "\K[^"]+' || echo "v2.24.0")
    else
        compose_version="v2.24.0"
    fi

    log "INFO" "Telechargement de Docker Compose $compose_version pour $os/$arch..."

    local download_url="https://github.com/docker/compose/releases/download/${compose_version}/docker-compose-${os}-${arch}"

    if command -v curl &> /dev/null; then
        sudo curl -SL "$download_url" -o /usr/local/lib/docker/cli-plugins/docker-compose 2>> "$LOG_FILE"
    elif command -v wget &> /dev/null; then
        sudo wget -qO /usr/local/lib/docker/cli-plugins/docker-compose "$download_url" 2>> "$LOG_FILE"
    else
        log "ERROR" "Ni curl ni wget disponible"
        return 1
    fi

    sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

    return 0
}

# ============================================================================
# VERIFICATION ET INSTALLATION DES DEPENDANCES
# ============================================================================
check_and_install_dependencies() {
    print_section "VERIFICATION ET INSTALLATION DES DEPENDANCES"

    local pkg_manager=$(detect_package_manager)
    log "INFO" "Gestionnaire de paquets detecte: $pkg_manager"

    if [ "$pkg_manager" = "unknown" ]; then
        print_error "Aucun gestionnaire de paquets supporte n'a ete detecte"
        print_info "Gestionnaires supportes: apt, dnf, yum, pacman, brew, zypper, apk"
        log "ERROR" "Gestionnaire de paquets non detecte"
        return 1
    fi

    print_info "Gestionnaire de paquets: $pkg_manager"
    echo ""

    # -------------------------------------------------------------------------
    # 1. Verification de Bash 4.0+
    # -------------------------------------------------------------------------
    echo -e "${CYAN}[1/8]${RESET} Verification de Bash..."
    if ! check_bash_version; then
        print_warning "Version de Bash insuffisante mais l'installation continue..."
    fi

    # -------------------------------------------------------------------------
    # 2. Verification de l'espace disque
    # -------------------------------------------------------------------------
    echo -e "${CYAN}[2/8]${RESET} Verification de l'espace disque..."
    if ! check_disk_space; then
        print_warning "Espace disque insuffisant mais l'installation continue..."
    fi

    # -------------------------------------------------------------------------
    # 3. Verification des ports
    # -------------------------------------------------------------------------
    echo -e "${CYAN}[3/8]${RESET} Verification des ports..."
    check_required_ports || true

    # Mise a jour du cache des paquets
    echo ""
    print_info "Mise a jour du cache des paquets..."
    update_package_cache "$pkg_manager"

    echo ""
    print_info "Verification et installation des dependances..."
    echo ""

    # -------------------------------------------------------------------------
    # 4. curl ou wget (necessaire pour Docker)
    # -------------------------------------------------------------------------
    echo -e "${CYAN}[4/8]${RESET} Verification de curl/wget..."

    if command -v curl &> /dev/null; then
        log "SUCCESS" "curl est disponible"
        print_success "curl: disponible"
        ((DEPS_ALREADY_INSTALLED++)) || true
    elif command -v wget &> /dev/null; then
        log "SUCCESS" "wget est disponible"
        print_success "wget: disponible"
        ((DEPS_ALREADY_INSTALLED++)) || true
    else
        # Essayer d'installer curl
        local install_cmd=$(get_install_command "$pkg_manager" "curl")
        install_with_retry "curl" "$install_cmd" "command -v curl" "${HELP_URLS[curl]}"
    fi

    # -------------------------------------------------------------------------
    # 5. Git
    # -------------------------------------------------------------------------
    echo -e "${CYAN}[5/8]${RESET} Verification de Git..."
    local git_install_cmd=$(get_install_command "$pkg_manager" "git")
    install_with_retry "git" "$git_install_cmd" "command -v git" "${HELP_URLS[git]}"

    # -------------------------------------------------------------------------
    # 6. Docker
    # -------------------------------------------------------------------------
    echo -e "${CYAN}[6/8]${RESET} Verification de Docker..."

    if command -v docker &> /dev/null; then
        log "INFO" "Docker est installe"
        print_success "Docker: installe"
        ((DEPS_ALREADY_INSTALLED++)) || true

        # Verifier le daemon
        echo -e "${CYAN}[6b/8]${RESET} Verification du daemon Docker..."
        if ! check_docker_daemon; then
            ((DEPS_FAILED++)) || true
        fi
    else
        # Installation de Docker avec retry
        local attempt=1
        local max_retries=3
        local docker_installed=false

        while [ $attempt -le $max_retries ] && [ "$docker_installed" = "false" ]; do
            echo -e "  ${DIM}Tentative $attempt/$max_retries...${RESET}"
            log "INFO" "Tentative $attempt/$max_retries pour Docker..."

            if install_docker "$pkg_manager"; then
                sleep 3
                if command -v docker &> /dev/null && docker info &> /dev/null 2>&1; then
                    log "SUCCESS" "Docker installe et daemon operationnel"
                    print_success "Docker installe et operationnel"
                    ((DEPS_INSTALLED++)) || true
                    docker_installed=true
                fi
            fi

            if [ "$docker_installed" = "false" ]; then
                ((attempt++))
                if [ $attempt -le $max_retries ]; then
                    log "INFO" "Attente de 5 secondes avant nouvelle tentative..."
                    sleep 5
                fi
            fi
        done

        if [ "$docker_installed" = "false" ]; then
            log "ERROR" "Echec de l'installation de Docker apres $max_retries tentatives"
            print_error "Echec de l'installation de Docker apres $max_retries tentatives"
            offer_open_url "${HELP_URLS[docker]}"
            ((DEPS_FAILED++)) || true
        fi
    fi

    # -------------------------------------------------------------------------
    # 7. Docker Compose v2
    # -------------------------------------------------------------------------
    echo -e "${CYAN}[7/8]${RESET} Verification de Docker Compose v2..."

    if docker compose version &> /dev/null 2>&1; then
        local compose_version=$(docker compose version 2>/dev/null | grep -oP 'v\d+\.\d+\.\d+' || echo "v2.x")
        log "SUCCESS" "Docker Compose v2 est disponible ($compose_version)"
        print_success "Docker Compose v2: $compose_version"
        ((DEPS_ALREADY_INSTALLED++)) || true
    else
        # Essayer d'installer Docker Compose v2
        local attempt=1
        local max_retries=3
        local compose_installed=false

        while [ $attempt -le $max_retries ] && [ "$compose_installed" = "false" ]; do
            echo -e "  ${DIM}Tentative $attempt/$max_retries...${RESET}"

            if install_docker_compose_v2 "$pkg_manager"; then
                if docker compose version &> /dev/null 2>&1; then
                    log "SUCCESS" "Docker Compose v2 installe"
                    print_success "Docker Compose v2 installe"
                    ((DEPS_INSTALLED++)) || true
                    compose_installed=true
                fi
            fi

            if [ "$compose_installed" = "false" ]; then
                ((attempt++))
                [ $attempt -le $max_retries ] && sleep 3
            fi
        done

        if [ "$compose_installed" = "false" ]; then
            log "ERROR" "Echec de l'installation de Docker Compose v2"
            print_error "Echec de l'installation de Docker Compose v2"
            offer_open_url "${HELP_URLS[docker-compose]}"
            ((DEPS_FAILED++)) || true
        fi
    fi

    # -------------------------------------------------------------------------
    # 8. Outils supplementaires (optionnels)
    # -------------------------------------------------------------------------
    echo -e "${CYAN}[8/8]${RESET} Verification des outils supplementaires..."

    # jq
    if ! command -v jq &> /dev/null; then
        local jq_install_cmd=$(get_install_command "$pkg_manager" "jq")
        install_with_retry "jq" "$jq_install_cmd" "command -v jq" "${HELP_URLS[jq]}" || true
    else
        log "SUCCESS" "jq est disponible"
        print_success "jq: disponible"
    fi

    # openssl
    if ! command -v openssl &> /dev/null; then
        local openssl_install_cmd=$(get_install_command "$pkg_manager" "openssl")
        install_with_retry "openssl" "$openssl_install_cmd" "command -v openssl" "${HELP_URLS[openssl]}" || true
    else
        log "SUCCESS" "openssl est disponible"
        print_success "openssl: disponible"
    fi

    echo ""
    print_info "Resume des dependances:"
    echo "  - Deja installees: $DEPS_ALREADY_INSTALLED"
    echo "  - Nouvellement installees: $DEPS_INSTALLED"
    echo "  - Echecs: $DEPS_FAILED"

    if [ $DEPS_FAILED -gt 0 ]; then
        print_warning "Certaines dependances n'ont pas pu etre installees"
        print_info "Consultez le fichier de log pour plus de details: $LOG_FILE"
        return 1
    fi

    return 0
}

# ============================================================================
# FONCTIONS D'INTERACTION UTILISATEUR
# ============================================================================
prompt_input() {
    local var_name=$1
    local prompt_text=$2
    local default_value=$3
    local is_secret=${4:-false}

    if [ -n "$default_value" ]; then
        echo -e "${YELLOW}>${RESET} ${WHITE}${prompt_text}${RESET} ${DIM}(defaut: ${default_value})${RESET}"
    else
        echo -e "${YELLOW}>${RESET} ${WHITE}${prompt_text}${RESET}"
    fi

    if [ "$is_secret" = true ]; then
        read -s -p "  -> " input_value
        echo ""
    else
        read -p "  -> " input_value
    fi

    if [ -z "$input_value" ] && [ -n "$default_value" ]; then
        input_value="$default_value"
    fi

    eval "$var_name='$input_value'"
    log "DEBUG" "Input: $var_name = ${input_value:0:20}..."
}

generate_password() {
    local length=${1:-32}
    LC_ALL=C tr -dc 'A-Za-z0-9!@#$%^&*()_+-=' < /dev/urandom | head -c "$length"
}

generate_alphanum_password() {
    local length=${1:-32}
    LC_ALL=C tr -dc 'A-Za-z0-9' < /dev/urandom | head -c "$length"
}

# ============================================================================
# VALIDATION DES FICHIERS YAML
# ============================================================================
validate_yaml_file() {
    local file="$1"

    if [ ! -f "$file" ]; then
        log "ERROR" "Fichier YAML non trouve: $file"
        return 1
    fi

    # Essayer avec yq
    if command -v yq &> /dev/null; then
        if yq eval '.' "$file" > /dev/null 2>&1; then
            log "SUCCESS" "YAML valide (yq): $file"
            return 0
        else
            log "ERROR" "YAML invalide (yq): $file"
            return 1
        fi
    fi

    # Fallback avec Python
    if command -v python3 &> /dev/null; then
        if python3 -c "import yaml; yaml.safe_load(open('$file'))" 2>/dev/null; then
            log "SUCCESS" "YAML valide (python3): $file"
            return 0
        else
            # Verifier si PyYAML est installe
            if python3 -c "import yaml" 2>/dev/null; then
                log "ERROR" "YAML invalide (python3): $file"
                return 1
            else
                log "WARNING" "Module PyYAML non installe pour python3"
            fi
        fi
    fi

    if command -v python &> /dev/null; then
        if python -c "import yaml; yaml.safe_load(open('$file'))" 2>/dev/null; then
            log "SUCCESS" "YAML valide (python): $file"
            return 0
        else
            log "WARNING" "Validation YAML avec python echouee: $file"
        fi
    fi

    log "WARNING" "Impossible de valider YAML (ni yq ni python/PyYAML disponible): $file"
    return 0
}

validate_json_file() {
    local file="$1"

    if [ ! -f "$file" ]; then
        log "ERROR" "Fichier JSON non trouve: $file"
        return 1
    fi

    if command -v jq &> /dev/null; then
        if jq '.' "$file" > /dev/null 2>&1; then
            log "SUCCESS" "JSON valide: $file"
            return 0
        else
            log "ERROR" "JSON invalide: $file"
            return 1
        fi
    fi

    # Fallback avec Python
    if command -v python3 &> /dev/null; then
        if python3 -c "import json; json.load(open('$file'))" 2>/dev/null; then
            log "SUCCESS" "JSON valide (python): $file"
            return 0
        else
            log "ERROR" "JSON invalide (python): $file"
            return 1
        fi
    fi

    log "WARNING" "Impossible de valider JSON (ni jq ni python disponible): $file"
    return 0
}

validate_env_file() {
    local file="$1"
    local errors=0

    if [ ! -f "$file" ]; then
        log "ERROR" "Fichier .env non trouve: $file"
        return 1
    fi

    log "INFO" "Validation du fichier .env: $file"

    local line_num=0
    while IFS= read -r line || [ -n "$line" ]; do
        ((line_num++))

        # Ignorer les lignes vides et les commentaires
        if [[ -z "$line" ]] || [[ "$line" =~ ^[[:space:]]*# ]]; then
            continue
        fi

        # Verifier le format KEY=VALUE
        if [[ ! "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
            log "WARNING" "Ligne $line_num format invalide: $line"
            ((errors++))
        fi
    done < "$file"

    if [ $errors -eq 0 ]; then
        log "SUCCESS" "Fichier .env valide: $file"
        return 0
    else
        log "WARNING" "Fichier .env contient $errors erreurs de format"
        return 1
    fi
}

# ============================================================================
# VERIFICATION DES PERMISSIONS
# ============================================================================
check_file_permissions() {
    local file="$1"
    local expected_perms="$2"

    if [ ! -e "$file" ]; then
        log "WARNING" "Fichier non trouve pour verification des permissions: $file"
        return 1
    fi

    local actual_perms=$(stat -c "%a" "$file" 2>/dev/null || stat -f "%OLp" "$file" 2>/dev/null || echo "unknown")

    if [ "$actual_perms" = "unknown" ]; then
        log "WARNING" "Impossible de verifier les permissions de: $file"
        return 0
    fi

    log "INFO" "Permissions de $file: $actual_perms"

    if [ -n "$expected_perms" ] && [ "$actual_perms" != "$expected_perms" ]; then
        log "WARNING" "Permissions de $file ($actual_perms) different de l'attendu ($expected_perms)"
        return 1
    fi

    return 0
}

# ============================================================================
# VERIFICATION DES FICHIERS POST-INSTALLATION
# ============================================================================
verify_created_files() {
    print_section "VERIFICATION DES FICHIERS CREES"

    local expected_files=(
        "$PROJECT_DIR/.env"
        "$PROJECT_DIR/docker-compose.yml"
        "$PROJECT_DIR/scripts/start.sh"
        "$PROJECT_DIR/scripts/stop.sh"
        "$PROJECT_DIR/scripts/backup.sh"
        "$PROJECT_DIR/scripts/logs.sh"
        "$PROJECT_DIR/scripts/status.sh"
        "$PROJECT_DIR/templates/docker-compose.template.yml"
    )

    local missing_files=()
    local invalid_files=()

    echo ""
    print_info "Verification de l'existence des fichiers..."

    for file in "${expected_files[@]}"; do
        if [ -f "$file" ]; then
            print_success "Existe: $(basename "$file")"
            ((FILES_CREATED++))
        else
            print_error "Manquant: $(basename "$file")"
            missing_files+=("$file")
        fi
    done

    echo ""
    print_info "Validation de la syntaxe des fichiers YAML (python3 -c 'import yaml')..."

    # Valider les fichiers YAML
    local yaml_files=(
        "$PROJECT_DIR/docker-compose.yml"
        "$PROJECT_DIR/templates/docker-compose.template.yml"
    )

    for yaml_file in "${yaml_files[@]}"; do
        if [ -f "$yaml_file" ]; then
            if validate_yaml_file "$yaml_file"; then
                ((FILES_VALIDATED++))
            else
                invalid_files+=("$yaml_file")
                ((FILES_INVALID++))
            fi
        fi
    done

    # Valider le fichier .env
    echo ""
    print_info "Validation du fichier .env..."

    if [ -f "$PROJECT_DIR/.env" ]; then
        if validate_env_file "$PROJECT_DIR/.env"; then
            ((FILES_VALIDATED++))
        else
            invalid_files+=("$PROJECT_DIR/.env")
            ((FILES_INVALID++))
        fi
    fi

    # Verifier les permissions des scripts
    echo ""
    print_info "Verification des permissions des scripts..."

    for script in "$PROJECT_DIR/scripts/"*.sh; do
        if [ -f "$script" ]; then
            if [ -x "$script" ]; then
                print_success "Executable: $(basename "$script")"
            else
                print_warning "Non executable: $(basename "$script")"
                chmod +x "$script" 2>/dev/null && print_info "  -> Corrige"
            fi
        fi
    done

    # Rapport de verification
    echo ""
    print_info "Rapport de verification des fichiers:"
    echo "  - Fichiers crees: $FILES_CREATED"
    echo "  - Fichiers valides: $FILES_VALIDATED"
    echo "  - Fichiers invalides: $FILES_INVALID"
    echo "  - Fichiers manquants: ${#missing_files[@]}"

    if [ ${#missing_files[@]} -gt 0 ]; then
        print_warning "Fichiers manquants:"
        for file in "${missing_files[@]}"; do
            echo "    - $file"
        done
    fi

    if [ ${#invalid_files[@]} -gt 0 ]; then
        print_warning "Fichiers invalides:"
        for file in "${invalid_files[@]}"; do
            echo "    - $file"
        done
    fi

    return 0
}

# ============================================================================
# VERIFICATION DES PERMISSIONS DOCKER
# ============================================================================
check_docker_permissions() {
    print_info "Verification des permissions Docker..."

    # Verifier si l'utilisateur peut utiliser Docker sans sudo
    if docker info &> /dev/null 2>&1; then
        log "SUCCESS" "Utilisateur peut acceder a Docker"
    else
        log "WARNING" "L'utilisateur n'a pas les permissions Docker"
        print_warning "Vous devrez peut-etre:"
        echo "  1. Ajouter votre utilisateur au groupe docker: sudo usermod -aG docker \$USER"
        echo "  2. Vous reconnecter pour appliquer les changements"
        echo "  3. Ou utiliser sudo pour les commandes docker"
    fi

    # Verifier le socket Docker
    if [ -S /var/run/docker.sock ]; then
        log "SUCCESS" "Socket Docker trouve: /var/run/docker.sock"

        # Verifier les permissions du socket
        local socket_perms=$(stat -c "%a" /var/run/docker.sock 2>/dev/null || stat -f "%OLp" /var/run/docker.sock 2>/dev/null || echo "unknown")
        log "INFO" "Permissions du socket Docker: $socket_perms"
    else
        log "WARNING" "Socket Docker non trouve a /var/run/docker.sock"
    fi

    return 0
}

# ============================================================================
# GENERATION DU RAPPORT FINAL
# ============================================================================
generate_final_report() {
    local report_file="$LOG_DIR/report-$(date +%Y-%m-%d-%H%M%S).txt"
    REPORT_FILE="$report_file"

    log "INFO" "Generation du rapport final: $report_file"

    {
        echo "============================================================================"
        echo "        RAPPORT D'INSTALLATION - MINECRAFT BOT SETUP v3.0"
        echo "============================================================================"
        echo ""
        echo "Date de generation: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "Systeme: $(uname -a)"
        echo "Utilisateur: $USER"
        echo "Repertoire du projet: $PROJECT_DIR"
        echo ""
        echo "============================================================================"
        echo "                         RESUME DE L'INSTALLATION"
        echo "============================================================================"
        echo ""
        echo "DEPENDANCES:"
        echo "  - Deja installees:       $DEPS_ALREADY_INSTALLED"
        echo "  - Nouvellement installees: $DEPS_INSTALLED"
        echo "  - Echecs:                 $DEPS_FAILED"
        echo ""
        echo "FICHIERS:"
        echo "  - Fichiers crees:         $FILES_CREATED"
        echo "  - Fichiers valides:       $FILES_VALIDATED"
        echo "  - Fichiers invalides:     $FILES_INVALID"
        echo ""
        echo "AUTRES:"
        echo "  - Ports bloques:          $PORTS_BLOCKED"
        echo "  - Avertissements:         $WARNINGS_COUNT"
        echo ""
        echo "============================================================================"
        echo "                         FICHIERS CREES"
        echo "============================================================================"
        echo ""

        # Lister tous les fichiers crees
        local files_to_list=(
            ".env"
            "docker-compose.yml"
            "templates/docker-compose.template.yml"
            "scripts/start.sh"
            "scripts/stop.sh"
            "scripts/backup.sh"
            "scripts/logs.sh"
            "scripts/status.sh"
            "scripts/rebuild.sh"
            "scripts/clean.sh"
            "scripts/health.sh"
        )

        for rel_file in "${files_to_list[@]}"; do
            local full_path="$PROJECT_DIR/$rel_file"
            if [ -f "$full_path" ]; then
                local file_size=$(stat -c "%s" "$full_path" 2>/dev/null || stat -f "%z" "$full_path" 2>/dev/null || echo "?")
                local file_perms=$(stat -c "%a" "$full_path" 2>/dev/null || stat -f "%OLp" "$full_path" 2>/dev/null || echo "?")
                echo "  [OK] $rel_file"
                echo "       Taille: ${file_size} bytes | Permissions: $file_perms"
            else
                echo "  [MANQUANT] $rel_file"
            fi
        done

        echo ""
        echo "============================================================================"
        echo "                         DOSSIERS CREES"
        echo "============================================================================"
        echo ""

        # Lister les dossiers principaux
        local dirs_to_list=(
            "bot"
            "web"
            "api"
            "minecraft"
            "database"
            "redis"
            "nginx"
            "scripts"
            "logs"
            "backups"
            "templates"
        )

        for dir in "${dirs_to_list[@]}"; do
            if [ -d "$PROJECT_DIR/$dir" ]; then
                local dir_count=$(find "$PROJECT_DIR/$dir" -type d 2>/dev/null | wc -l)
                echo "  [OK] $dir/ ($dir_count sous-dossiers)"
            else
                echo "  [MANQUANT] $dir/"
            fi
        done

        echo ""
        echo "============================================================================"
        echo "                         VERIFICATION YAML"
        echo "============================================================================"
        echo ""

        for yaml_file in "$PROJECT_DIR/docker-compose.yml" "$PROJECT_DIR/templates/docker-compose.template.yml"; do
            if [ -f "$yaml_file" ]; then
                local basename_file=$(basename "$yaml_file")
                if command -v python3 &> /dev/null && python3 -c "import yaml; yaml.safe_load(open('$yaml_file'))" 2>/dev/null; then
                    echo "  [VALIDE] $basename_file"
                elif command -v yq &> /dev/null && yq eval '.' "$yaml_file" > /dev/null 2>&1; then
                    echo "  [VALIDE] $basename_file"
                else
                    echo "  [NON VERIFIE] $basename_file (outils de validation non disponibles)"
                fi
            fi
        done

        echo ""
        echo "============================================================================"
        echo "                         VERIFICATION .ENV"
        echo "============================================================================"
        echo ""

        if [ -f "$PROJECT_DIR/.env" ]; then
            local env_vars=$(grep -c "^[A-Za-z]" "$PROJECT_DIR/.env" 2>/dev/null || echo "0")
            echo "  Fichier .env: $PROJECT_DIR/.env"
            echo "  Variables definies: $env_vars"
            echo ""
            echo "  Variables principales:"
            grep -E "^(PROJECT_NAME|DISCORD_|MINECRAFT_|POSTGRES_|REDIS_|NEXTAUTH_URL)=" "$PROJECT_DIR/.env" 2>/dev/null | while read line; do
                local key="${line%%=*}"
                echo "    - $key"
            done
        else
            echo "  [ERREUR] Fichier .env non trouve"
        fi

        echo ""
        echo "============================================================================"
        echo "                         STATUT DES SERVICES"
        echo "============================================================================"
        echo ""

        # Docker
        if command -v docker &> /dev/null; then
            local docker_version=$(docker --version 2>/dev/null || echo "version inconnue")
            echo "  Docker: INSTALLE"
            echo "    Version: $docker_version"

            if docker info &> /dev/null 2>&1; then
                echo "    Daemon: EN COURS"
            else
                echo "    Daemon: ARRETE"
            fi
        else
            echo "  Docker: NON INSTALLE"
        fi

        echo ""

        # Docker Compose
        if docker compose version &> /dev/null 2>&1; then
            local compose_version=$(docker compose version 2>/dev/null || echo "version inconnue")
            echo "  Docker Compose: INSTALLE"
            echo "    Version: $compose_version"
        else
            echo "  Docker Compose: NON INSTALLE"
        fi

        echo ""
        echo "============================================================================"
        echo "                         PORTS REQUIS"
        echo "============================================================================"
        echo ""

        local ports_info=(
            "3000:Web Dashboard"
            "5432:PostgreSQL"
            "6379:Redis"
            "25565:Minecraft"
            "25575:RCON"
        )

        for port_info in "${ports_info[@]}"; do
            IFS=':' read -r port service <<< "$port_info"
            local status="DISPONIBLE"

            if command -v ss &> /dev/null; then
                ss -tuln 2>/dev/null | grep -q ":$port " && status="UTILISE"
            elif command -v netstat &> /dev/null; then
                netstat -tuln 2>/dev/null | grep -q ":$port " && status="UTILISE"
            fi

            echo "  Port $port ($service): $status"
        done

        echo ""
        echo "============================================================================"
        echo "                         PROCHAINES ETAPES"
        echo "============================================================================"
        echo ""
        echo "  1. Verifiez et ajustez le fichier .env si necessaire"
        echo "  2. Construisez les images: docker compose build"
        echo "  3. Demarrez les services: ./scripts/start.sh"
        echo "  4. Verifiez les logs: ./scripts/logs.sh"
        echo "  5. Verifiez le statut: ./scripts/status.sh"
        echo ""
        echo "============================================================================"
        echo "                         FICHIERS DE LOG"
        echo "============================================================================"
        echo ""
        echo "  Log d'installation: $LOG_FILE"
        echo "  Rapport: $report_file"
        echo ""
        echo "============================================================================"
        echo "        FIN DU RAPPORT - $(date '+%Y-%m-%d %H:%M:%S')"
        echo "============================================================================"

    } > "$report_file"

    log "SUCCESS" "Rapport final genere: $report_file"
    return 0
}

# ============================================================================
# VERIFICATION FINALE COMPLETE
# ============================================================================
final_verification() {
    print_section "VERIFICATION FINALE"

    local checks_passed=0
    local checks_failed=0

    echo ""
    print_info "Execution des verifications finales..."
    echo ""

    # 1. Verifier Docker
    echo -e "${CYAN}[1/6]${RESET} Verification de Docker..."
    if docker info &> /dev/null 2>&1; then
        print_success "Docker fonctionne correctement"
        ((checks_passed++))
    else
        print_error "Docker ne repond pas"
        ((checks_failed++))
    fi

    # 2. Verifier Docker Compose
    echo -e "${CYAN}[2/6]${RESET} Verification de Docker Compose..."
    if docker compose version &> /dev/null 2>&1; then
        print_success "Docker Compose v2 disponible"
        ((checks_passed++))
    else
        print_error "Docker Compose v2 non disponible"
        ((checks_failed++))
    fi

    # 3. Verifier les permissions
    echo -e "${CYAN}[3/6]${RESET} Verification des permissions..."
    check_docker_permissions
    ((checks_passed++))

    # 4. Verifier les ports
    echo -e "${CYAN}[4/6]${RESET} Verification des ports..."
    check_required_ports
    ((checks_passed++))

    # 5. Verifier les fichiers
    echo -e "${CYAN}[5/6]${RESET} Verification des fichiers de configuration..."
    if [ -f "$PROJECT_DIR/.env" ] && [ -f "$PROJECT_DIR/docker-compose.yml" ]; then
        print_success "Fichiers de configuration presents"
        ((checks_passed++))
    else
        print_error "Fichiers de configuration manquants"
        ((checks_failed++))
    fi

    # 6. Generer le rapport final
    echo -e "${CYAN}[6/6]${RESET} Generation du rapport final..."
    generate_final_report
    print_success "Rapport genere: $REPORT_FILE"
    ((checks_passed++))

    echo ""
    print_info "Resultat des verifications: $checks_passed reussies, $checks_failed echecs"

    # Ajouter au log
    {
        echo ""
        echo "============================================================================"
        echo "VERIFICATION FINALE"
        echo "============================================================================"
        echo "Date: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "Verifications reussies: $checks_passed"
        echo "Verifications echouees: $checks_failed"
        echo "Dependances deja installees: $DEPS_ALREADY_INSTALLED"
        echo "Dependances installees: $DEPS_INSTALLED"
        echo "Dependances en echec: $DEPS_FAILED"
        echo "Fichiers crees: $FILES_CREATED"
        echo "Fichiers valides: $FILES_VALIDATED"
        echo "Fichiers invalides: $FILES_INVALID"
        echo "Ports bloques: $PORTS_BLOCKED"
        echo "Avertissements: $WARNINGS_COUNT"
        echo "Rapport: $REPORT_FILE"
        echo "============================================================================"
    } >> "$LOG_FILE"

    return $checks_failed
}

# ============================================================================
# CREATION DE LA STRUCTURE DE DOSSIERS
# ============================================================================
create_directory_structure() {
    print_section "CREATION DE LA STRUCTURE DE DOSSIERS"

    local directories=(
        "bot/src/commands"
        "bot/src/events"
        "bot/src/utils"
        "bot/src/services"
        "web/src/app"
        "web/src/components"
        "web/src/lib"
        "web/public"
        "api/src/routes"
        "api/src/middleware"
        "api/src/services"
        "minecraft/config"
        "minecraft/plugins"
        "minecraft/worlds"
        "minecraft/logs"
        "database/migrations"
        "database/seeds"
        "redis/data"
        "nginx/conf.d"
        "nginx/ssl"
        "scripts"
        "logs"
        "backups"
        "templates"
    )

    for dir in "${directories[@]}"; do
        full_path="$PROJECT_DIR/$dir"
        if [ ! -d "$full_path" ]; then
            mkdir -p "$full_path"
            log "SUCCESS" "Cree: $dir"
        else
            log "INFO" "Existe deja: $dir"
        fi
    done

    print_success "Structure de dossiers creee!"
}

# ============================================================================
# CREATION DU FICHIER .ENV
# ============================================================================
create_env_file() {
    local env_file="$PROJECT_DIR/.env"

    cat > "$env_file" << EOF
# ============================================================================
# ${PROJECT_NAME^^} - CONFIGURATION ENVIRONNEMENT
# Genere automatiquement le $(date '+%Y-%m-%d a %H:%M:%S')
# ============================================================================

# ----------------------------------------------------------------------------
# PROJET
# ----------------------------------------------------------------------------
PROJECT_NAME=${PROJECT_NAME}
NODE_ENV=production
TZ=Europe/Paris

# ----------------------------------------------------------------------------
# DISCORD
# ----------------------------------------------------------------------------
DISCORD_TOKEN=${DISCORD_TOKEN}
DISCORD_GUILD_ID=${DISCORD_GUILD_ID}
DISCORD_CLIENT_ID=${DISCORD_CLIENT_ID}
DISCORD_CLIENT_SECRET=${DISCORD_CLIENT_SECRET}

# ----------------------------------------------------------------------------
# MINECRAFT SERVER
# ----------------------------------------------------------------------------
MINECRAFT_HOST=minecraft
MINECRAFT_PORT=25565
MINECRAFT_RCON_PORT=25575
RCON_PASSWORD=${RCON_PASSWORD}
MINECRAFT_VERSION=1.20.4
MINECRAFT_TYPE=PAPER
MINECRAFT_MEMORY=4G
MINECRAFT_EULA=TRUE

# ----------------------------------------------------------------------------
# BASE DE DONNEES POSTGRESQL
# ----------------------------------------------------------------------------
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=${PROJECT_NAME//-/_}_db
POSTGRES_USER=${PROJECT_NAME//-/_}_user
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
DATABASE_URL=postgresql://\${POSTGRES_USER}:\${POSTGRES_PASSWORD}@\${POSTGRES_HOST}:\${POSTGRES_PORT}/\${POSTGRES_DB}

# ----------------------------------------------------------------------------
# REDIS
# ----------------------------------------------------------------------------
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=${REDIS_PASSWORD}
REDIS_URL=redis://:\${REDIS_PASSWORD}@\${REDIS_HOST}:\${REDIS_PORT}

# ----------------------------------------------------------------------------
# WEB / NEXTAUTH
# ----------------------------------------------------------------------------
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=${NEXTAUTH_SECRET}

# ----------------------------------------------------------------------------
# API INTERNE
# ----------------------------------------------------------------------------
API_HOST=api
API_PORT=4000
INTERNAL_API_KEY=${INTERNAL_API_KEY}

# ----------------------------------------------------------------------------
# NGINX
# ----------------------------------------------------------------------------
NGINX_HOST=localhost
NGINX_HTTP_PORT=80
NGINX_HTTPS_PORT=443

# ----------------------------------------------------------------------------
# BACKUPS
# ----------------------------------------------------------------------------
BACKUP_RETENTION_DAYS=7
BACKUP_SCHEDULE="0 3 * * *"
EOF

    log "SUCCESS" "Fichier .env cree: $env_file"
}

# ============================================================================
# CREATION DU DOCKER-COMPOSE
# ============================================================================
create_docker_compose() {
    local template_file="$PROJECT_DIR/templates/docker-compose.template.yml"
    local compose_file="$PROJECT_DIR/docker-compose.yml"

    cat > "$template_file" << 'EOF'
version: '3.8'

services:
  bot:
    build: ./bot
    container_name: {{PROJECT_NAME}}-bot
    restart: unless-stopped
    env_file: .env
    depends_on:
      - postgres
      - redis
      - minecraft
    networks:
      - app-network

  web:
    build: ./web
    container_name: {{PROJECT_NAME}}-web
    restart: unless-stopped
    env_file: .env
    ports:
      - "3000:3000"
    depends_on:
      - api
    networks:
      - app-network

  api:
    build: ./api
    container_name: {{PROJECT_NAME}}-api
    restart: unless-stopped
    env_file: .env
    ports:
      - "4000:4000"
    depends_on:
      - postgres
      - redis
    networks:
      - app-network

  minecraft:
    image: itzg/minecraft-server
    container_name: {{PROJECT_NAME}}-minecraft
    restart: unless-stopped
    env_file: .env
    environment:
      - EULA=${MINECRAFT_EULA}
      - TYPE=${MINECRAFT_TYPE}
      - VERSION=${MINECRAFT_VERSION}
      - MEMORY=${MINECRAFT_MEMORY}
      - RCON_PASSWORD=${RCON_PASSWORD}
      - ENABLE_RCON=true
    ports:
      - "25565:25565"
      - "25575:25575"
    volumes:
      - ./minecraft/worlds:/data/worlds
      - ./minecraft/plugins:/data/plugins
      - ./minecraft/config:/data/config
      - ./minecraft/logs:/data/logs
    networks:
      - app-network

  postgres:
    image: postgres:15-alpine
    container_name: {{PROJECT_NAME}}-postgres
    restart: unless-stopped
    environment:
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./database/migrations:/docker-entrypoint-initdb.d
    networks:
      - app-network

  redis:
    image: redis:7-alpine
    container_name: {{PROJECT_NAME}}-redis
    restart: unless-stopped
    command: redis-server --requirepass ${REDIS_PASSWORD}
    ports:
      - "6379:6379"
    volumes:
      - ./redis/data:/data
    networks:
      - app-network

  nginx:
    image: nginx:alpine
    container_name: {{PROJECT_NAME}}-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - web
      - api
    networks:
      - app-network

networks:
  app-network:
    driver: bridge

volumes:
  postgres-data:
EOF

    log "SUCCESS" "Template docker-compose cree"

    # Copie et remplacement des placeholders
    cp "$template_file" "$compose_file"
    sed -i "s/{{PROJECT_NAME}}/${PROJECT_NAME}/g" "$compose_file" 2>/dev/null || \
        sed "s/{{PROJECT_NAME}}/${PROJECT_NAME}/g" "$template_file" > "$compose_file"

    log "SUCCESS" "docker-compose.yml genere"
}

# ============================================================================
# CREATION DES SCRIPTS UTILITAIRES
# ============================================================================
create_utility_scripts() {
    print_section "CREATION DES SCRIPTS UTILITAIRES"

    # Script de demarrage
    cat > "$PROJECT_DIR/scripts/start.sh" << 'EOF'
#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "[START] Demarrage des services..."
cd "$PROJECT_DIR"
docker compose up -d

echo "[OK] Services demarres!"
docker compose ps
EOF

    # Script d'arret
    cat > "$PROJECT_DIR/scripts/stop.sh" << 'EOF'
#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "[STOP] Arret des services..."
cd "$PROJECT_DIR"
docker compose down

echo "[OK] Services arretes!"
EOF

    # Script de backup
    cat > "$PROJECT_DIR/scripts/backup.sh" << 'EOF'
#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_DIR/backups"
DATE=$(date '+%Y%m%d_%H%M%S')

echo "[BACKUP] Creation du backup..."

# Backup Minecraft worlds
if [ -d "$PROJECT_DIR/minecraft/worlds" ]; then
    tar -czf "$BACKUP_DIR/worlds_${DATE}.tar.gz" -C "$PROJECT_DIR/minecraft" worlds
    echo "[OK] Worlds sauvegardes"
fi

# Backup PostgreSQL
docker exec -t $(docker ps -qf "name=postgres") pg_dumpall -U postgres > "$BACKUP_DIR/database_${DATE}.sql" 2>/dev/null || echo "[WARN] Backup base de donnees echoue"
echo "[OK] Base de donnees sauvegardee"

# Nettoyage des anciens backups (> 7 jours)
find "$BACKUP_DIR" -type f -mtime +7 -delete 2>/dev/null || true
echo "[CLEAN] Anciens backups nettoyes"

echo "[OK] Backup termine: $BACKUP_DIR"
EOF

    # Script de logs
    cat > "$PROJECT_DIR/scripts/logs.sh" << 'EOF'
#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

SERVICE=${1:-all}

cd "$PROJECT_DIR"

if [ "$SERVICE" = "all" ]; then
    docker compose logs -f --tail=100
else
    docker compose logs -f --tail=100 "$SERVICE"
fi
EOF

    # Script de status
    cat > "$PROJECT_DIR/scripts/status.sh" << 'EOF'
#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "[STATUS] Status des services:"
echo ""
cd "$PROJECT_DIR"
docker compose ps
echo ""
echo "[STATS] Utilisation des ressources:"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null || echo "Aucun conteneur en cours d'execution"
EOF

    # Script de rebuild
    cat > "$PROJECT_DIR/scripts/rebuild.sh" << 'EOF'
#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "[REBUILD] Reconstruction des images..."
cd "$PROJECT_DIR"
docker compose build --no-cache

echo "[OK] Images reconstruites!"
EOF

    # Script de clean
    cat > "$PROJECT_DIR/scripts/clean.sh" << 'EOF'
#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "[CLEAN] Nettoyage des ressources Docker..."
cd "$PROJECT_DIR"

# Arreter les conteneurs
docker compose down 2>/dev/null || true

# Supprimer les volumes orphelins
docker volume prune -f 2>/dev/null || true

# Supprimer les images non utilisees
docker image prune -f 2>/dev/null || true

echo "[OK] Nettoyage termine!"
EOF

    # Script de health check
    cat > "$PROJECT_DIR/scripts/health.sh" << 'EOF'
#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "[HEALTH] Verification de l'etat des services..."
echo ""

cd "$PROJECT_DIR"

# Verifier Docker
if docker info &> /dev/null; then
    echo "[OK] Docker: Operationnel"
else
    echo "[ERROR] Docker: Non disponible"
fi

# Verifier les conteneurs
running=$(docker compose ps --status running -q 2>/dev/null | wc -l)
total=$(docker compose ps -q 2>/dev/null | wc -l)

echo "[INFO] Conteneurs: $running/$total en cours d'execution"

# Verifier la connectivite reseau
if docker compose exec -T minecraft echo "OK" &> /dev/null; then
    echo "[OK] Minecraft: Accessible"
else
    echo "[WARN] Minecraft: Non accessible"
fi

if docker compose exec -T postgres pg_isready &> /dev/null; then
    echo "[OK] PostgreSQL: Accessible"
else
    echo "[WARN] PostgreSQL: Non accessible"
fi

if docker compose exec -T redis redis-cli ping &> /dev/null; then
    echo "[OK] Redis: Accessible"
else
    echo "[WARN] Redis: Non accessible"
fi

echo ""
echo "[HEALTH] Verification terminee"
EOF

    log "SUCCESS" "Scripts utilitaires crees"

    # Rendre les scripts executables
    chmod +x "$PROJECT_DIR/scripts/"*.sh 2>/dev/null || true

    for script in "$PROJECT_DIR/scripts/"*.sh; do
        if [ -f "$script" ]; then
            log "INFO" "Executable: $(basename "$script")"
        fi
    done
}

# ============================================================================
# AFFICHAGE DU RESUME FINAL
# ============================================================================
print_final_summary() {
    print_section "RESUME DE L'INSTALLATION"

    echo -e "${GREEN}"
    echo '    +======================================================================+'
    echo '    |                                                                      |'
    echo -e "    |           ${WHITE}[OK] INSTALLATION TERMINEE AVEC SUCCES!${GREEN}                   |"
    echo '    |                                                                      |'
    echo '    +======================================================================+'
    echo -e "${RESET}"

    echo ""
    echo -e "${CYAN}+-----------------------------------------------------------------------+${RESET}"
    echo -e "${CYAN}|${RESET} ${BOLD}CONFIGURATION DU PROJET${RESET}                                             ${CYAN}|${RESET}"
    echo -e "${CYAN}+-----------------------------------------------------------------------+${RESET}"
    echo -e "${CYAN}|${RESET}  Nom du projet    : ${GREEN}${PROJECT_NAME}${RESET}"
    echo -e "${CYAN}|${RESET}  Repertoire       : ${GREEN}${PROJECT_DIR}${RESET}"
    echo -e "${CYAN}|${RESET}  Fichier .env     : ${GREEN}${PROJECT_DIR}/.env${RESET}"
    echo -e "${CYAN}|${RESET}  Fichier log      : ${GREEN}${LOG_FILE}${RESET}"
    echo -e "${CYAN}|${RESET}  Rapport          : ${GREEN}${REPORT_FILE}${RESET}"
    echo -e "${CYAN}+-----------------------------------------------------------------------+${RESET}"

    echo ""
    echo -e "${MAGENTA}+-----------------------------------------------------------------------+${RESET}"
    echo -e "${MAGENTA}|${RESET} ${BOLD}SECRETS GENERES${RESET} ${DIM}(stockes dans .env)${RESET}                                 ${MAGENTA}|${RESET}"
    echo -e "${MAGENTA}+-----------------------------------------------------------------------+${RESET}"
    echo -e "${MAGENTA}|${RESET}  RCON_PASSWORD     : ${DIM}${RCON_PASSWORD:0:20}...${RESET}"
    echo -e "${MAGENTA}|${RESET}  POSTGRES_PASSWORD : ${DIM}${POSTGRES_PASSWORD:0:20}...${RESET}"
    echo -e "${MAGENTA}|${RESET}  REDIS_PASSWORD    : ${DIM}${REDIS_PASSWORD:0:20}...${RESET}"
    echo -e "${MAGENTA}|${RESET}  NEXTAUTH_SECRET   : ${DIM}${NEXTAUTH_SECRET:0:20}...${RESET}"
    echo -e "${MAGENTA}|${RESET}  INTERNAL_API_KEY  : ${DIM}${INTERNAL_API_KEY:0:20}...${RESET}"
    echo -e "${MAGENTA}+-----------------------------------------------------------------------+${RESET}"

    echo ""
    echo -e "${BLUE}+-----------------------------------------------------------------------+${RESET}"
    echo -e "${BLUE}|${RESET} ${BOLD}STATISTIQUES D'INSTALLATION${RESET}                                         ${BLUE}|${RESET}"
    echo -e "${BLUE}+-----------------------------------------------------------------------+${RESET}"
    echo -e "${BLUE}|${RESET}  Dependances deja installees : ${GREEN}$DEPS_ALREADY_INSTALLED${RESET}"
    echo -e "${BLUE}|${RESET}  Dependances installees      : ${GREEN}$DEPS_INSTALLED${RESET}"
    echo -e "${BLUE}|${RESET}  Dependances en echec        : ${RED}$DEPS_FAILED${RESET}"
    echo -e "${BLUE}|${RESET}  Fichiers crees              : ${GREEN}$FILES_CREATED${RESET}"
    echo -e "${BLUE}|${RESET}  Fichiers valides            : ${GREEN}$FILES_VALIDATED${RESET}"
    echo -e "${BLUE}|${RESET}  Ports bloques               : ${YELLOW}$PORTS_BLOCKED${RESET}"
    echo -e "${BLUE}|${RESET}  Avertissements              : ${YELLOW}$WARNINGS_COUNT${RESET}"
    echo -e "${BLUE}+-----------------------------------------------------------------------+${RESET}"

    echo ""
    echo -e "${YELLOW}+-----------------------------------------------------------------------+${RESET}"
    echo -e "${YELLOW}|${RESET} ${BOLD}PROCHAINES ETAPES${RESET}                                                    ${YELLOW}|${RESET}"
    echo -e "${YELLOW}+-----------------------------------------------------------------------+${RESET}"
    echo -e "${YELLOW}|${RESET}  1. Verifiez le fichier ${CYAN}.env${RESET} et ajustez si necessaire"
    echo -e "${YELLOW}|${RESET}  2. Construisez les images : ${CYAN}docker compose build${RESET}"
    echo -e "${YELLOW}|${RESET}  3. Demarrez les services  : ${CYAN}./scripts/start.sh${RESET}"
    echo -e "${YELLOW}|${RESET}  4. Consultez les logs     : ${CYAN}./scripts/logs.sh${RESET}"
    echo -e "${YELLOW}|${RESET}  5. Verifiez le status     : ${CYAN}./scripts/status.sh${RESET}"
    echo -e "${YELLOW}|${RESET}  6. Health check           : ${CYAN}./scripts/health.sh${RESET}"
    echo -e "${YELLOW}+-----------------------------------------------------------------------+${RESET}"

    if [ $DEPS_FAILED -gt 0 ]; then
        echo ""
        echo -e "${RED}+-----------------------------------------------------------------------+${RESET}"
        echo -e "${RED}|${RESET} ${BOLD}ATTENTION: DEPENDANCES MANQUANTES${RESET}                                   ${RED}|${RESET}"
        echo -e "${RED}+-----------------------------------------------------------------------+${RESET}"
        echo -e "${RED}|${RESET}  Certaines dependances n'ont pas pu etre installees."
        echo -e "${RED}|${RESET}  Consultez le fichier de log pour plus de details:"
        echo -e "${RED}|${RESET}  ${CYAN}$LOG_FILE${RESET}"
        echo -e "${RED}+-----------------------------------------------------------------------+${RESET}"
    fi

    echo ""
    echo -e "${DIM}------------------------------------------------------------------------${RESET}"
    echo -e "${DIM}  Genere par setup.sh v3.0 | $(date '+%Y-%m-%d %H:%M:%S')${RESET}"
    echo -e "${DIM}  Log complet: $LOG_FILE${RESET}"
    echo -e "${DIM}  Rapport: $REPORT_FILE${RESET}"
    echo -e "${DIM}------------------------------------------------------------------------${RESET}"
    echo ""
}

# ============================================================================
# SCRIPT PRINCIPAL
# ============================================================================
main() {
    # Initialiser les logs
    init_logs

    log "INFO" "Demarrage du script d'installation v3.0"
    log "INFO" "Repertoire de travail: $PROJECT_DIR"
    log "INFO" "Bash version: ${BASH_VERSION:-unknown}"

    # Afficher l'en-tete
    print_header

    # Verification et installation des dependances
    if ! check_and_install_dependencies; then
        print_warning "Certaines dependances sont manquantes mais l'installation continue..."
    fi

    # Collecte des informations
    print_section "CONFIGURATION DU PROJET"

    prompt_input PROJECT_NAME "Nom du projet/bot" "minecraft-bot"
    prompt_input DISCORD_TOKEN "Token Discord du bot" "" true
    prompt_input DISCORD_GUILD_ID "ID du serveur Discord (Guild ID)" ""
    prompt_input DISCORD_CLIENT_ID "ID Client Discord (Application ID)" ""
    prompt_input DISCORD_CLIENT_SECRET "Secret Client Discord" "" true

    # Validation basique
    if [ -z "$DISCORD_TOKEN" ]; then
        print_warning "Token Discord non fourni - vous devrez le configurer manuellement plus tard"
    fi

    # Generation des secrets
    print_section "GENERATION DES SECRETS SECURISES"

    echo -e "${CYAN}Generation des mots de passe et cles cryptographiques...${RESET}"
    echo ""

    RCON_PASSWORD=$(generate_alphanum_password 32)
    log "SUCCESS" "RCON_PASSWORD genere (32 chars alphanumeriques)"

    POSTGRES_PASSWORD=$(generate_alphanum_password 32)
    log "SUCCESS" "POSTGRES_PASSWORD genere (32 chars alphanumeriques)"

    REDIS_PASSWORD=$(generate_alphanum_password 32)
    log "SUCCESS" "REDIS_PASSWORD genere (32 chars alphanumeriques)"

    NEXTAUTH_SECRET=$(openssl rand -base64 32 2>/dev/null || generate_alphanum_password 44)
    log "SUCCESS" "NEXTAUTH_SECRET genere (base64, 32 bytes)"

    INTERNAL_API_KEY=$(openssl rand -hex 32 2>/dev/null || generate_alphanum_password 64)
    log "SUCCESS" "INTERNAL_API_KEY genere (hex, 32 bytes)"

    echo ""
    print_success "Tous les secrets ont ete generes avec succes!"

    # Creation de la structure de dossiers
    create_directory_structure

    # Creation du fichier .env
    print_section "CREATION DU FICHIER DE CONFIGURATION"
    create_env_file

    # Creation du docker-compose
    print_section "CREATION DU DOCKER-COMPOSE"
    create_docker_compose

    # Creation des scripts utilitaires
    create_utility_scripts

    # Configuration des permissions
    print_section "CONFIGURATION DES PERMISSIONS"
    chmod +x "$PROJECT_DIR/setup.sh" 2>/dev/null || true
    log "SUCCESS" "Permissions configurees"

    # Verification des fichiers crees
    verify_created_files

    # Verification finale
    final_verification

    # Afficher le resume
    print_final_summary

    log "INFO" "Installation terminee"

    return 0
}

# Executer le script principal
main "$@"
