#Requires -Version 5.1
# Script d'installation interactif pour le projet Minecraft Bot
# Encoding: UTF-8
# Version: 3.0.0 - Installation automatique des dependances avec retry, verification complete et logging ameliore

param(
    [switch]$Force,
    [switch]$SkipDependencies,
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"

# ============================================================================
# CONFIGURATION GLOBALE
# ============================================================================

$Global:ScriptDir = $null
$Global:LogDir = $null
$Global:LogFile = $null
$Global:StartTime = Get-Date
$Global:MinDiskSpaceGB = 10
$Global:MaxRetries = 3

# URLs d'aide pour les dependances
$Global:HelpUrls = @{
    "Docker"        = "https://docs.docker.com/desktop/install/windows-install/"
    "DockerCompose" = "https://docs.docker.com/compose/install/"
    "Git"           = "https://git-scm.com/download/win"
    "PowerShell"    = "https://learn.microsoft.com/en-us/powershell/scripting/install/installing-powershell-on-windows"
    "Winget"        = "https://learn.microsoft.com/en-us/windows/package-manager/winget/"
    "Chocolatey"    = "https://chocolatey.org/install"
}

# Dependances a verifier/installer
$Global:Dependencies = @(
    @{
        Name           = "PowerShell 5.1+"
        WingetId       = $null
        ChocolateyId   = $null
        VerifyCommand  = { $PSVersionTable.PSVersion.Major -ge 5 -and ($PSVersionTable.PSVersion.Major -gt 5 -or $PSVersionTable.PSVersion.Minor -ge 1) }
        HelpUrl        = "https://learn.microsoft.com/en-us/powershell/scripting/install/installing-powershell-on-windows"
        Optional       = $false
        CanAutoInstall = $false
    },
    @{
        Name           = "Git"
        WingetId       = "Git.Git"
        ChocolateyId   = "git"
        VerifyCommand  = { $null -ne (Get-Command git -ErrorAction SilentlyContinue) }
        HelpUrl        = "https://git-scm.com/download/win"
        Optional       = $false
        CanAutoInstall = $true
    },
    @{
        Name           = "Docker Desktop"
        WingetId       = "Docker.DockerDesktop"
        ChocolateyId   = "docker-desktop"
        VerifyCommand  = { $null -ne (Get-Command docker -ErrorAction SilentlyContinue) }
        HelpUrl        = "https://docs.docker.com/desktop/install/windows-install/"
        Optional       = $false
        CanAutoInstall = $true
        RequiresReboot = $true
    },
    @{
        Name           = "Docker Compose v2"
        WingetId       = $null
        ChocolateyId   = $null
        VerifyCommand  = {
            try {
                $result = & docker compose version 2>&1
                return $result -match "v2\."
            } catch {
                return $false
            }
        }
        HelpUrl        = "https://docs.docker.com/compose/install/"
        Optional       = $false
        CanAutoInstall = $false
        DependsOn      = "Docker Desktop"
    }
)

# Liste des fichiers attendus apres installation
$Global:ExpectedFiles = @(
    @{ Path = ".env"; Type = "env"; Required = $true; Description = "Variables d'environnement" }
    @{ Path = ".env.example"; Type = "env"; Required = $true; Description = "Template des variables" }
    @{ Path = "docker-compose.yml"; Type = "yaml"; Required = $true; Description = "Configuration Docker Compose" }
    @{ Path = ".gitignore"; Type = "text"; Required = $true; Description = "Fichiers ignores par Git" }
    @{ Path = "README.md"; Type = "text"; Required = $false; Description = "Documentation" }
    @{ Path = "bot\package.json"; Type = "json"; Required = $true; Description = "Dependencies du bot" }
    @{ Path = "bot\src\index.js"; Type = "js"; Required = $true; Description = "Point d'entree du bot" }
    @{ Path = "docker\bot\Dockerfile"; Type = "dockerfile"; Required = $true; Description = "Dockerfile du bot" }
    @{ Path = "docker\api\Dockerfile"; Type = "dockerfile"; Required = $true; Description = "Dockerfile de l'API" }
    @{ Path = "docker\web\Dockerfile"; Type = "dockerfile"; Required = $true; Description = "Dockerfile du web" }
)

# Ports a verifier
$Global:RequiredPorts = @(
    @{ Port = 3000; Service = "Web Dashboard" }
    @{ Port = 5432; Service = "PostgreSQL" }
    @{ Port = 6379; Service = "Redis" }
    @{ Port = 25565; Service = "Minecraft" }
    @{ Port = 25575; Service = "RCON" }
)

# ============================================================================
# FONCTIONS DE LOGGING
# ============================================================================

function Initialize-Logging {
    $Global:ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    if ([string]::IsNullOrEmpty($Global:ScriptDir)) {
        $Global:ScriptDir = Get-Location
    }

    $Global:LogDir = Join-Path $Global:ScriptDir "logs"

    if (-not (Test-Path $Global:LogDir)) {
        New-Item -ItemType Directory -Path $Global:LogDir -Force | Out-Null
    }

    $timestamp = Get-Date -Format "yyyy-MM-dd-HHmmss"
    $Global:LogFile = Join-Path $Global:LogDir "setup-$timestamp.log"

    # Creer le fichier de log avec header
    $header = @"
================================================================================
  MINECRAFT BOT SETUP - LOG FILE
  Date: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
  PowerShell Version: $($PSVersionTable.PSVersion)
  OS: $([System.Environment]::OSVersion.VersionString)
  User: $env:USERNAME
  Computer: $env:COMPUTERNAME
================================================================================

"@
    Set-Content -Path $Global:LogFile -Value $header -Encoding UTF8
}

function Write-Log {
    param(
        [string]$Message,
        [ValidateSet("INFO", "WARN", "ERROR", "SUCCESS", "DEBUG")]
        [string]$Level = "INFO",
        [switch]$NoConsole
    )

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"

    # Ecrire dans le fichier de log (utilise Tee-Object pour ecriture simultanee)
    if ($Global:LogFile -and (Test-Path (Split-Path $Global:LogFile -Parent))) {
        Add-Content -Path $Global:LogFile -Value $logEntry -Encoding UTF8
    }

    # Afficher dans la console
    if (-not $NoConsole) {
        $color = switch ($Level) {
            "INFO"    { "Cyan" }
            "SUCCESS" { "Green" }
            "WARN"    { "Yellow" }
            "ERROR"   { "Red" }
            "DEBUG"   { "Gray" }
            default   { "White" }
        }

        $prefix = switch ($Level) {
            "INFO"    { "[*]" }
            "SUCCESS" { "[+]" }
            "WARN"    { "[!]" }
            "ERROR"   { "[-]" }
            "DEBUG"   { "[.]" }
            default   { "[>]" }
        }

        Write-Host "  $prefix " -ForegroundColor $color -NoNewline
        Write-Host $Message
    }
}

function Write-LogAndTee {
    param(
        [string]$Message,
        [ValidateSet("INFO", "WARN", "ERROR", "SUCCESS", "DEBUG")]
        [string]$Level = "INFO"
    )

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"

    # Couleur pour la console
    $color = switch ($Level) {
        "INFO"    { "Cyan" }
        "SUCCESS" { "Green" }
        "WARN"    { "Yellow" }
        "ERROR"   { "Red" }
        "DEBUG"   { "Gray" }
        default   { "White" }
    }

    $prefix = switch ($Level) {
        "INFO"    { "[*]" }
        "SUCCESS" { "[+]" }
        "WARN"    { "[!]" }
        "ERROR"   { "[-]" }
        "DEBUG"   { "[.]" }
        default   { "[>]" }
    }

    # Utiliser Tee-Object pour afficher ET logger simultanement
    $output = "  $prefix $Message"
    $output | Tee-Object -FilePath $Global:LogFile -Append | ForEach-Object {
        Write-Host "  $prefix " -ForegroundColor $color -NoNewline
        Write-Host $Message
    }

    # Aussi ecrire le format complet dans le log
    Add-Content -Path $Global:LogFile -Value $logEntry -Encoding UTF8
}

# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

function Show-Header {
    Clear-Host
    Write-Host ""
    Write-Host "  ███╗   ███╗██╗███╗   ██╗███████╗ ██████╗██████╗  █████╗ ███████╗████████╗" -ForegroundColor Cyan
    Write-Host "  ████╗ ████║██║████╗  ██║██╔════╝██╔════╝██╔══██╗██╔══██╗██╔════╝╚══██╔══╝" -ForegroundColor Cyan
    Write-Host "  ██╔████╔██║██║██╔██╗ ██║█████╗  ██║     ██████╔╝███████║█████╗     ██║   " -ForegroundColor Cyan
    Write-Host "  ██║╚██╔╝██║██║██║╚██╗██║██╔══╝  ██║     ██╔══██╗██╔══██║██╔══╝     ██║   " -ForegroundColor Cyan
    Write-Host "  ██║ ╚═╝ ██║██║██║ ╚████║███████╗╚██████╗██║  ██║██║  ██║██║        ██║   " -ForegroundColor Cyan
    Write-Host "  ╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝        ╚═╝   " -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  ██████╗  ██████╗ ████████╗    ███████╗███████╗████████╗██╗   ██╗██████╗  " -ForegroundColor Magenta
    Write-Host "  ██╔══██╗██╔═══██╗╚══██╔══╝    ██╔════╝██╔════╝╚══██╔══╝██║   ██║██╔══██╗ " -ForegroundColor Magenta
    Write-Host "  ██████╔╝██║   ██║   ██║       ███████╗█████╗     ██║   ██║   ██║██████╔╝ " -ForegroundColor Magenta
    Write-Host "  ██╔══██╗██║   ██║   ██║       ╚════██║██╔══╝     ██║   ██║   ██║██╔═══╝  " -ForegroundColor Magenta
    Write-Host "  ██████╔╝╚██████╔╝   ██║       ███████║███████╗   ██║   ╚██████╔╝██║      " -ForegroundColor Magenta
    Write-Host "  ╚═════╝  ╚═════╝    ╚═╝       ╚══════╝╚══════╝   ╚═╝    ╚═════╝ ╚═╝      " -ForegroundColor Magenta
    Write-Host ""
    Write-Host "  ==========================================================================" -ForegroundColor DarkGray
    Write-Host "              Installation Interactive v3.0 - Windows                       " -ForegroundColor Yellow
    Write-Host "  ==========================================================================" -ForegroundColor DarkGray
    Write-Host ""
}

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "  === $Title ===" -ForegroundColor Yellow
    Write-Host ""
    Write-Log "--- SECTION: $Title ---" -Level "INFO" -NoConsole
}

function Get-SecurePassword {
    param([int]$Length = 32)

    $chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
    $password = ""
    $random = New-Object System.Security.Cryptography.RNGCryptoServiceProvider
    $bytes = New-Object byte[]($Length)
    $random.GetBytes($bytes)

    for ($i = 0; $i -lt $Length; $i++) {
        $password += $chars[$bytes[$i] % $chars.Length]
    }

    return $password
}

function Get-SecurePasswordAlphanumeric {
    param([int]$Length = 32)

    $chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    $password = ""
    $random = New-Object System.Security.Cryptography.RNGCryptoServiceProvider
    $bytes = New-Object byte[]($Length)
    $random.GetBytes($bytes)

    for ($i = 0; $i -lt $Length; $i++) {
        $password += $chars[$bytes[$i] % $chars.Length]
    }

    return $password
}

function Get-NextAuthSecret {
    $bytes = New-Object byte[](32)
    $random = New-Object System.Security.Cryptography.RNGCryptoServiceProvider
    $random.GetBytes($bytes)
    return [Convert]::ToBase64String($bytes)
}

function Get-HexKey {
    param([int]$Bytes = 32)

    $byteArray = New-Object byte[]($Bytes)
    $random = New-Object System.Security.Cryptography.RNGCryptoServiceProvider
    $random.GetBytes($byteArray)
    return [BitConverter]::ToString($byteArray).Replace("-", "").ToLower()
}

function Read-ValidatedInput {
    param(
        [string]$Prompt,
        [string]$Default = "",
        [switch]$Required,
        [string]$Pattern = "",
        [string]$PatternError = "Format invalide",
        [switch]$IsSecret
    )

    while ($true) {
        Write-Host "  [?] " -ForegroundColor Magenta -NoNewline

        if ($Default -ne "") {
            Write-Host "$Prompt " -NoNewline
            Write-Host "[$Default]" -ForegroundColor DarkGray -NoNewline
            Write-Host ": " -NoNewline
        } else {
            Write-Host "${Prompt}: " -NoNewline
        }

        if ($IsSecret) {
            $secureInput = Read-Host -AsSecureString
            $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureInput)
            $value = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
            [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BSTR)
        } else {
            $value = Read-Host
        }

        # Utiliser la valeur par defaut si vide
        if ([string]::IsNullOrWhiteSpace($value) -and $Default -ne "") {
            $value = $Default
        }

        # Validation: requis
        if ($Required -and [string]::IsNullOrWhiteSpace($value)) {
            Write-Log "Cette valeur est requise." "ERROR"
            continue
        }

        # Validation: pattern
        if ($Pattern -ne "" -and $value -ne "" -and $value -notmatch $Pattern) {
            Write-Log $PatternError "ERROR"
            continue
        }

        return $value
    }
}

function Test-DirectoryWritable {
    param([string]$Path)

    try {
        $testFile = Join-Path $Path ".write_test_$(Get-Random)"
        [System.IO.File]::WriteAllText($testFile, "test")
        Remove-Item $testFile -Force
        return $true
    } catch {
        return $false
    }
}

function Open-HelpUrl {
    param([string]$Url)

    try {
        Write-Log "Ouverture de l'URL d'aide: $Url" "INFO"
        Start-Process $Url
        return $true
    } catch {
        Write-Log "Impossible d'ouvrir le navigateur: $($_.Exception.Message)" "WARN"
        return $false
    }
}

# ============================================================================
# VERIFICATION DES PREREQUIS SYSTEME
# ============================================================================

function Test-DiskSpace {
    param(
        [string]$Path,
        [int]$MinimumGB = 10
    )

    try {
        $drive = (Get-Item $Path).PSDrive.Name
        $driveInfo = Get-PSDrive -Name $drive
        $freeSpaceGB = [math]::Round($driveInfo.Free / 1GB, 2)

        Write-Log "Espace disque disponible sur ${drive}: : $freeSpaceGB GB" "INFO"

        if ($freeSpaceGB -lt $MinimumGB) {
            Write-Log "Espace disque insuffisant! Minimum requis: $MinimumGB GB, Disponible: $freeSpaceGB GB" "ERROR"
            return @{ Success = $false; FreeSpaceGB = $freeSpaceGB; RequiredGB = $MinimumGB }
        }

        Write-Log "Espace disque suffisant ($freeSpaceGB GB >= $MinimumGB GB)" "SUCCESS"
        return @{ Success = $true; FreeSpaceGB = $freeSpaceGB; RequiredGB = $MinimumGB }
    } catch {
        Write-Log "Impossible de verifier l'espace disque: $($_.Exception.Message)" "WARN"
        return @{ Success = $true; FreeSpaceGB = -1; RequiredGB = $MinimumGB; Error = $_.Exception.Message }
    }
}

function Test-PortAvailable {
    param([int]$Port)

    try {
        $connection = New-Object System.Net.Sockets.TcpClient
        $connection.Connect("127.0.0.1", $Port)
        $connection.Close()
        return $false  # Port est utilise
    } catch {
        return $true  # Port est disponible
    }
}

function Test-AllPorts {
    Write-Section "Verification des ports requis"

    $report = @{
        Available = @()
        InUse = @()
    }

    foreach ($portSpec in $Global:RequiredPorts) {
        $available = Test-PortAvailable -Port $portSpec.Port

        if ($available) {
            $report.Available += $portSpec
            Write-Log "Port $($portSpec.Port) ($($portSpec.Service)): DISPONIBLE" "SUCCESS"
        } else {
            $report.InUse += $portSpec
            Write-Log "Port $($portSpec.Port) ($($portSpec.Service)): EN UTILISATION" "WARN"
        }
    }

    return $report
}

function Test-DockerRunning {
    try {
        $result = & docker info 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Docker Desktop est en cours d'execution" "SUCCESS"
            return $true
        } else {
            Write-Log "Docker Desktop n'est pas en cours d'execution" "WARN"
            return $false
        }
    } catch {
        Write-Log "Impossible de communiquer avec Docker: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

function Test-DockerComposeV2 {
    try {
        $result = & docker compose version 2>&1
        if ($LASTEXITCODE -eq 0 -and $result -match "v2\.") {
            $version = ($result -split " ")[-1]
            Write-Log "Docker Compose v2 detecte: $version" "SUCCESS"
            return $true
        } else {
            Write-Log "Docker Compose v2 non detecte" "WARN"
            return $false
        }
    } catch {
        Write-Log "Erreur lors de la verification de Docker Compose: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

# ============================================================================
# FONCTIONS D'INSTALLATION DES DEPENDANCES
# ============================================================================

function Test-WingetAvailable {
    try {
        $wingetPath = Get-Command winget -ErrorAction SilentlyContinue
        if ($null -ne $wingetPath) {
            Write-Log "Winget detecte: $($wingetPath.Source)" "DEBUG" -NoConsole
            return $true
        }
        return $false
    } catch {
        return $false
    }
}

function Test-ChocolateyAvailable {
    try {
        $chocoPath = Get-Command choco -ErrorAction SilentlyContinue
        if ($null -ne $chocoPath) {
            Write-Log "Chocolatey detecte: $($chocoPath.Source)" "DEBUG" -NoConsole
            return $true
        }
        return $false
    } catch {
        return $false
    }
}

function Install-Chocolatey {
    Write-Log "Installation de Chocolatey..." "INFO"

    try {
        Set-ExecutionPolicy Bypass -Scope Process -Force
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
        Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

        # Rafraichir l'environnement
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

        if (Test-ChocolateyAvailable) {
            Write-Log "Chocolatey installe avec succes" "SUCCESS"
            return $true
        }
    } catch {
        Write-Log "Echec de l'installation de Chocolatey: $($_.Exception.Message)" "ERROR"
    }

    return $false
}

function Install-PackageManager {
    Write-Log "Verification des gestionnaires de paquets..." "INFO"

    $hasWinget = Test-WingetAvailable
    $hasChocolatey = Test-ChocolateyAvailable

    if ($hasWinget) {
        Write-Log "Winget est disponible" "SUCCESS"
        return @{ Available = $true; Manager = "winget" }
    }

    if ($hasChocolatey) {
        Write-Log "Chocolatey est disponible" "SUCCESS"
        return @{ Available = $true; Manager = "chocolatey" }
    }

    Write-Log "Aucun gestionnaire de paquets disponible" "WARN"
    Write-Host ""
    Write-Host "  Aucun gestionnaire de paquets n'est installe (winget ou chocolatey)." -ForegroundColor Yellow
    Write-Host "  Voulez-vous installer Chocolatey automatiquement? (recommande)" -ForegroundColor Yellow
    Write-Host ""

    $install = Read-Host "  Installer Chocolatey? (O/n)"

    if ($install -eq "" -or $install -eq "o" -or $install -eq "O") {
        if (Install-Chocolatey) {
            return @{ Available = $true; Manager = "chocolatey" }
        }
    }

    Write-Log "Installation manuelle requise" "WARN"
    Write-Host ""
    Write-Host "  Pour installer un gestionnaire de paquets:" -ForegroundColor Cyan
    Write-Host "    - Winget (Windows 10/11): $($Global:HelpUrls['Winget'])" -ForegroundColor Gray
    Write-Host "    - Chocolatey: $($Global:HelpUrls['Chocolatey'])" -ForegroundColor Gray
    Write-Host ""

    return @{ Available = $false; Manager = $null }
}

function Install-WithRetry {
    param(
        [string]$Name,
        [string]$WingetId,
        [string]$ChocolateyId,
        [scriptblock]$VerifyCommand,
        [string]$HelpUrl,
        [int]$MaxAttempts = 3,
        [switch]$RequiresReboot,
        [switch]$CanAutoInstall
    )

    Write-Log "Verification de $Name..." "INFO"

    # Etape 1: Verifier si deja installe
    try {
        $isInstalled = & $VerifyCommand
        if ($isInstalled) {
            Write-Log "$Name est deja installe et fonctionnel" "SUCCESS"
            return @{ Success = $true; AlreadyInstalled = $true; NeedsReboot = $false }
        }
    } catch {
        Write-Log "Erreur lors de la verification de $Name : $($_.Exception.Message)" "DEBUG" -NoConsole
    }

    Write-Log "$Name n'est pas installe ou non fonctionnel" "WARN"

    # Si l'installation automatique n'est pas possible
    if (-not $CanAutoInstall) {
        Write-Log "$Name ne peut pas etre installe automatiquement" "WARN"
        Write-Log "Veuillez installer $Name manuellement: $HelpUrl" "ERROR"

        Write-Host ""
        Write-Host "  ┌────────────────────────────────────────────────────────────────────────┐" -ForegroundColor Yellow
        Write-Host "  │ INSTALLATION MANUELLE REQUISE                                          │" -ForegroundColor Yellow
        Write-Host "  │                                                                        │" -ForegroundColor Yellow
        Write-Host "  │ Dependance: $($Name.PadRight(55))│" -ForegroundColor Yellow
        Write-Host "  │ URL: $($HelpUrl.PadRight(63))│" -ForegroundColor Yellow
        Write-Host "  └────────────────────────────────────────────────────────────────────────┘" -ForegroundColor Yellow
        Write-Host ""

        $openBrowser = Read-Host "  Ouvrir l'URL dans le navigateur? (O/n)"
        if ($openBrowser -eq "" -or $openBrowser -eq "o" -or $openBrowser -eq "O") {
            Open-HelpUrl -Url $HelpUrl
        }

        return @{ Success = $false; AlreadyInstalled = $false; NeedsReboot = $false; ManualRequired = $true }
    }

    # Detecter les gestionnaires de paquets disponibles
    $hasWinget = Test-WingetAvailable
    $hasChocolatey = Test-ChocolateyAvailable

    if (-not $hasWinget -and -not $hasChocolatey) {
        $pmResult = Install-PackageManager
        if (-not $pmResult.Available) {
            Write-Log "Impossible d'installer $Name sans gestionnaire de paquets" "ERROR"
            return @{ Success = $false; AlreadyInstalled = $false; NeedsReboot = $false }
        }
        $hasWinget = Test-WingetAvailable
        $hasChocolatey = Test-ChocolateyAvailable
    }

    # Etape 2-4: Tentatives d'installation avec retry (3 tentatives)
    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        Write-Log "=== Tentative d'installation $attempt/$MaxAttempts pour $Name ===" "INFO"

        $installSuccess = $false

        # Essayer avec winget d'abord
        if ($hasWinget -and -not [string]::IsNullOrEmpty($WingetId)) {
            Write-Log "Installation via winget: $WingetId" "INFO"
            try {
                $process = Start-Process -FilePath "winget" -ArgumentList "install", "--id", $WingetId, "--silent", "--accept-package-agreements", "--accept-source-agreements" -Wait -PassThru -NoNewWindow
                if ($process.ExitCode -eq 0) {
                    $installSuccess = $true
                    Write-Log "Commande winget executee avec succes (code: 0)" "SUCCESS"
                } else {
                    Write-Log "Winget a retourne le code: $($process.ExitCode)" "WARN"
                }
            } catch {
                Write-Log "Erreur winget: $($_.Exception.Message)" "WARN"
            }
        }

        # Si winget a echoue, essayer chocolatey
        if (-not $installSuccess -and $hasChocolatey -and -not [string]::IsNullOrEmpty($ChocolateyId)) {
            Write-Log "Installation via Chocolatey: $ChocolateyId" "INFO"
            try {
                $process = Start-Process -FilePath "choco" -ArgumentList "install", $ChocolateyId, "-y", "--no-progress" -Wait -PassThru -NoNewWindow
                if ($process.ExitCode -eq 0) {
                    $installSuccess = $true
                    Write-Log "Commande Chocolatey executee avec succes (code: 0)" "SUCCESS"
                } else {
                    Write-Log "Chocolatey a retourne le code: $($process.ExitCode)" "WARN"
                }
            } catch {
                Write-Log "Erreur Chocolatey: $($_.Exception.Message)" "WARN"
            }
        }

        # Rafraichir les variables d'environnement
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

        # Pause pour laisser le temps a l'installation de se finaliser
        Write-Log "Attente de finalisation de l'installation..." "INFO"
        Start-Sleep -Seconds 3

        # Etape 3: Verifier que l'installation a reussi
        try {
            $isNowInstalled = & $VerifyCommand
            if ($isNowInstalled) {
                Write-Log "$Name installe et verifie avec succes (tentative $attempt)" "SUCCESS"

                if ($RequiresReboot) {
                    Write-Log "$Name peut necessiter un redemarrage pour fonctionner correctement" "WARN"
                    return @{ Success = $true; AlreadyInstalled = $false; NeedsReboot = $true }
                }

                return @{ Success = $true; AlreadyInstalled = $false; NeedsReboot = $false }
            }
        } catch {
            Write-Log "Verification post-installation echouee: $($_.Exception.Message)" "DEBUG" -NoConsole
        }

        if ($attempt -lt $MaxAttempts) {
            Write-Log "Installation non verifiee, nouvelle tentative dans 5 secondes..." "WARN"
            Start-Sleep -Seconds 5
        }
    }

    # Etape 5: Apres 3 echecs, logger l'erreur et ouvrir automatiquement l'URL d'aide
    Write-Log "==========================================================" "ERROR"
    Write-Log "ECHEC: Installation de $Name apres $MaxAttempts tentatives" "ERROR"
    Write-Log "==========================================================" "ERROR"

    Write-Host ""
    Write-Host "  ┌────────────────────────────────────────────────────────────────────────┐" -ForegroundColor Red
    Write-Host "  │ ECHEC APRES 3 TENTATIVES - INSTALLATION MANUELLE REQUISE              │" -ForegroundColor Red
    Write-Host "  │                                                                        │" -ForegroundColor Red
    Write-Host "  │ Dependance: $($Name.PadRight(55))│" -ForegroundColor Red
    Write-Host "  │ URL: $($HelpUrl.PadRight(63))│" -ForegroundColor Red
    Write-Host "  │                                                                        │" -ForegroundColor Red
    Write-Host "  │ Ouverture automatique de l'URL d'aide dans le navigateur...           │" -ForegroundColor Red
    Write-Host "  └────────────────────────────────────────────────────────────────────────┘" -ForegroundColor Red
    Write-Host ""

    # Ouvrir automatiquement l'URL d'aide dans le navigateur
    Write-Log "Ouverture automatique de l'URL d'aide: $HelpUrl" "INFO"
    Open-HelpUrl -Url $HelpUrl

    return @{ Success = $false; AlreadyInstalled = $false; NeedsReboot = $false }
}

function Test-AllDependencies {
    Write-Section "Verification de toutes les dependances"

    $results = @{
        Passed = @()
        Failed = @()
        NeedsReboot = $false
        Details = @()
    }

    foreach ($dep in $Global:Dependencies) {
        $detail = @{
            Name = $dep.Name
            Status = "UNKNOWN"
            Installed = $false
            Error = $null
        }

        try {
            $isInstalled = & $dep.VerifyCommand
            if ($isInstalled) {
                Write-Log "$($dep.Name): OK" "SUCCESS"
                $detail.Status = "OK"
                $detail.Installed = $true
                $results.Passed += $dep.Name
            } else {
                Write-Log "$($dep.Name): NON INSTALLE" "WARN"
                $detail.Status = "NOT_INSTALLED"
                $results.Failed += $dep.Name
            }
        } catch {
            Write-Log "$($dep.Name): ERREUR - $($_.Exception.Message)" "ERROR"
            $detail.Status = "ERROR"
            $detail.Error = $_.Exception.Message
            $results.Failed += $dep.Name
        }

        $results.Details += $detail
    }

    return $results
}

function Install-AllDependencies {
    Write-Section "Installation des dependances manquantes"

    $results = @{
        Success = @()
        Failed = @()
        NeedsReboot = $false
        Skipped = @()
    }

    foreach ($dep in $Global:Dependencies) {
        # Verifier si la dependance depend d'une autre
        if ($dep.DependsOn) {
            $parentInstalled = $results.Success -contains $dep.DependsOn
            $parentFailed = $results.Failed -contains $dep.DependsOn

            if ($parentFailed) {
                Write-Log "$($dep.Name) ignore car $($dep.DependsOn) a echoue" "WARN"
                $results.Skipped += $dep.Name
                continue
            }
        }

        $result = Install-WithRetry `
            -Name $dep.Name `
            -WingetId $dep.WingetId `
            -ChocolateyId $dep.ChocolateyId `
            -VerifyCommand $dep.VerifyCommand `
            -HelpUrl $dep.HelpUrl `
            -MaxAttempts $Global:MaxRetries `
            -RequiresReboot:$dep.RequiresReboot `
            -CanAutoInstall:$dep.CanAutoInstall

        if ($result.Success) {
            $results.Success += $dep.Name
            if ($result.NeedsReboot) {
                $results.NeedsReboot = $true
            }
        } else {
            if ($dep.Optional) {
                Write-Log "$($dep.Name) est optionnel, continuation..." "WARN"
                $results.Skipped += "$($dep.Name) (optionnel)"
            } else {
                $results.Failed += $dep.Name
            }
        }
    }

    # Rapport des dependances
    Write-Host ""
    Write-Log "=== Rapport d'installation des dependances ===" "INFO"

    if ($results.Success.Count -gt 0) {
        Write-Log "Dependances OK: $($results.Success -join ', ')" "SUCCESS"
    }

    if ($results.Skipped.Count -gt 0) {
        Write-Log "Dependances ignorees: $($results.Skipped -join ', ')" "WARN"
    }

    if ($results.Failed.Count -gt 0) {
        Write-Log "Dependances ECHEC: $($results.Failed -join ', ')" "ERROR"

        if (-not $Force) {
            Write-Host ""
            Write-Host "  Certaines dependances critiques n'ont pas pu etre installees." -ForegroundColor Red
            Write-Host "  Voulez-vous continuer quand meme? (non recommande)" -ForegroundColor Yellow
            Write-Host ""
            $continue = Read-Host "  Continuer? (o/N)"
            if ($continue -ne "o" -and $continue -ne "O") {
                Write-Log "Installation annulee par l'utilisateur" "ERROR"
                exit 1
            }
        }
    }

    if ($results.NeedsReboot) {
        Write-Host ""
        Write-Host "  ┌────────────────────────────────────────────────────────────────────────┐" -ForegroundColor Yellow
        Write-Host "  │ ATTENTION: Un redemarrage peut etre necessaire                        │" -ForegroundColor Yellow
        Write-Host "  │ Certaines dependances (comme Docker) necessitent un redemarrage.      │" -ForegroundColor Yellow
        Write-Host "  │ Si des erreurs surviennent, redemarrez votre PC et relancez ce script.│" -ForegroundColor Yellow
        Write-Host "  └────────────────────────────────────────────────────────────────────────┘" -ForegroundColor Yellow
        Write-Host ""
    }

    return $results.Failed.Count -eq 0
}

# ============================================================================
# FONCTIONS DE VERIFICATION DES FICHIERS
# ============================================================================

function Test-YamlSyntax {
    param([string]$FilePath)

    try {
        $content = Get-Content $FilePath -Raw -ErrorAction Stop

        # Verification basique de syntaxe YAML
        $lines = $content -split "`n"
        $lineNumber = 0
        $errors = @()

        foreach ($line in $lines) {
            $lineNumber++

            if ([string]::IsNullOrWhiteSpace($line) -or $line.Trim().StartsWith("#")) {
                continue
            }

            # Verifier les tabs (YAML n'aime pas les tabs)
            if ($line -match "`t") {
                $errors += "Ligne $lineNumber : Tabulation detectee (utiliser des espaces)"
            }

            # Verifier les espaces avant les deux-points
            if ($line -match "\s+:") {
                # C'est OK si c'est dans une chaine
            }

            # Verifier l'indentation (doit etre multiple de 2)
            $indent = ($line -replace '[^\s].*', '').Length
            if ($indent -gt 0 -and $indent % 2 -ne 0) {
                $errors += "Ligne $lineNumber : Indentation impaire ($indent espaces)"
            }
        }

        if ($errors.Count -gt 0) {
            foreach ($err in $errors) {
                Write-Log "YAML Warning: $err" "DEBUG" -NoConsole
            }
        }

        return $true
    } catch {
        Write-Log "Erreur lecture YAML $FilePath : $($_.Exception.Message)" "DEBUG" -NoConsole
        return $false
    }
}

function Test-JsonSyntax {
    param([string]$FilePath)

    try {
        $content = Get-Content $FilePath -Raw -ErrorAction Stop
        $null = $content | ConvertFrom-Json -ErrorAction Stop
        return $true
    } catch {
        Write-Log "Erreur JSON $FilePath : $($_.Exception.Message)" "DEBUG" -NoConsole
        return $false
    }
}

function Test-EnvSyntax {
    param([string]$FilePath)

    try {
        $content = Get-Content $FilePath -ErrorAction Stop
        $lineNumber = 0
        $errors = @()

        foreach ($line in $content) {
            $lineNumber++

            # Ignorer les lignes vides et les commentaires
            if ([string]::IsNullOrWhiteSpace($line) -or $line.Trim().StartsWith("#")) {
                continue
            }

            # Verifier le format KEY=VALUE
            if ($line -notmatch '^[A-Za-z_][A-Za-z0-9_]*=.*$') {
                $errors += "Ligne $lineNumber : Format invalide"
            }
        }

        if ($errors.Count -gt 0) {
            foreach ($err in $errors) {
                Write-Log "ENV Error: $err" "DEBUG" -NoConsole
            }
            return $false
        }

        return $true
    } catch {
        Write-Log "Erreur lecture ENV $FilePath : $($_.Exception.Message)" "DEBUG" -NoConsole
        return $false
    }
}

function Test-FileSyntax {
    param(
        [string]$FilePath,
        [string]$Type
    )

    switch ($Type) {
        "yaml" { return Test-YamlSyntax -FilePath $FilePath }
        "json" { return Test-JsonSyntax -FilePath $FilePath }
        "env"  { return Test-EnvSyntax -FilePath $FilePath }
        default { return $true }
    }
}

function Test-AllFiles {
    param([string]$BaseDir)

    Write-Section "Verification des fichiers crees"

    $report = @{
        Total = 0
        Found = 0
        Missing = 0
        SyntaxOK = 0
        SyntaxError = 0
        Details = @()
        FileList = @()
    }

    foreach ($fileSpec in $Global:ExpectedFiles) {
        $report.Total++
        $fullPath = Join-Path $BaseDir $fileSpec.Path

        $fileStatus = @{
            Path = $fileSpec.Path
            FullPath = $fullPath
            Exists = $false
            SyntaxOK = $false
            Required = $fileSpec.Required
            Description = $fileSpec.Description
            Status = "MISSING"
            Size = 0
        }

        if (Test-Path $fullPath) {
            $fileStatus.Exists = $true
            $report.Found++

            # Obtenir la taille du fichier
            $fileInfo = Get-Item $fullPath
            $fileStatus.Size = $fileInfo.Length

            # Verifier la syntaxe
            $syntaxOK = Test-FileSyntax -FilePath $fullPath -Type $fileSpec.Type
            $fileStatus.SyntaxOK = $syntaxOK

            if ($syntaxOK) {
                $report.SyntaxOK++
                $fileStatus.Status = "OK"
                Write-Log "Fichier OK: $($fileSpec.Path) ($($fileStatus.Size) bytes)" "SUCCESS"
            } else {
                $report.SyntaxError++
                $fileStatus.Status = "SYNTAX_ERROR"
                Write-Log "Erreur de syntaxe: $($fileSpec.Path)" "ERROR"
            }

            $report.FileList += $fullPath
        } else {
            $report.Missing++

            if ($fileSpec.Required) {
                Write-Log "Fichier MANQUANT (requis): $($fileSpec.Path)" "ERROR"
            } else {
                Write-Log "Fichier manquant (optionnel): $($fileSpec.Path)" "WARN"
            }
        }

        $report.Details += $fileStatus
    }

    return $report
}

# ============================================================================
# RAPPORT FINAL
# ============================================================================

function Save-FinalReport {
    param(
        [hashtable]$FileReport,
        [hashtable]$PortReport,
        [hashtable]$DiskReport,
        [hashtable]$DependencyReport,
        [bool]$DockerOK,
        [bool]$DockerComposeOK,
        [string]$ProjectName
    )

    $reportPath = Join-Path $Global:LogDir "verification-report-$(Get-Date -Format 'yyyy-MM-dd-HHmmss').txt"

    $reportContent = @"
================================================================================
RAPPORT DE VERIFICATION COMPLET - $ProjectName
Date: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
================================================================================

=== DEPENDANCES ===
$(if ($DependencyReport) {
    $DependencyReport.Details | ForEach-Object { "  - $($_.Name): $($_.Status)" } | Out-String
} else {
    "  Non verifie"
})

=== ESPACE DISQUE ===
Requis: $($DiskReport.RequiredGB) GB
Disponible: $($DiskReport.FreeSpaceGB) GB
Status: $(if ($DiskReport.Success) { "OK" } else { "INSUFFISANT" })

=== FICHIERS ===
Total attendus: $($FileReport.Total)
Trouves: $($FileReport.Found)
Manquants: $($FileReport.Missing)
Syntaxe OK: $($FileReport.SyntaxOK)
Erreurs syntaxe: $($FileReport.SyntaxError)

Details:
$($FileReport.Details | ForEach-Object { "  - $($_.Path): $($_.Status) $(if ($_.Size -gt 0) { "($($_.Size) bytes)" })" } | Out-String)

Liste des fichiers crees:
$($FileReport.FileList | ForEach-Object { "  - $_" } | Out-String)

=== PORTS ===
Disponibles: $($PortReport.Available.Count)
En utilisation: $($PortReport.InUse.Count)

Disponibles:
$($PortReport.Available | ForEach-Object { "  - Port $($_.Port) ($($_.Service))" } | Out-String)

En utilisation:
$($PortReport.InUse | ForEach-Object { "  - Port $($_.Port) ($($_.Service))" } | Out-String)

=== DOCKER ===
Docker Desktop: $(if ($DockerOK) { "EN COURS D'EXECUTION" } else { "NON DISPONIBLE" })
Docker Compose v2: $(if ($DockerComposeOK) { "OK" } else { "NON DISPONIBLE" })

=== RESUME ===
Fichiers requis manquants: $(($FileReport.Details | Where-Object { $_.Status -eq "MISSING" -and $_.Required } | Measure-Object).Count)
Erreurs de syntaxe: $($FileReport.SyntaxError)
Ports en conflit: $($PortReport.InUse.Count)
Docker operationnel: $(if ($DockerOK -and $DockerComposeOK) { "OUI" } else { "NON" })

================================================================================
FIN DU RAPPORT
================================================================================
"@

    Set-Content -Path $reportPath -Value $reportContent -Encoding UTF8
    Write-Log "Rapport complet sauvegarde: $reportPath" "INFO"

    return $reportPath
}

function Show-FinalSummary {
    param(
        [hashtable]$FileReport,
        [hashtable]$PortReport,
        [hashtable]$DiskReport,
        [bool]$DockerOK,
        [bool]$DockerComposeOK,
        [string]$ProjectName,
        [string]$ScriptDir
    )

    Write-Host ""
    Write-Host "  ==========================================================================" -ForegroundColor Cyan
    Write-Host "                        RAPPORT DE VERIFICATION FINALE                      " -ForegroundColor Cyan
    Write-Host "  ==========================================================================" -ForegroundColor Cyan
    Write-Host ""

    # Section Espace Disque
    Write-Host "  ESPACE DISQUE" -ForegroundColor Yellow
    Write-Host "  -------------" -ForegroundColor Yellow

    if ($DiskReport.Success) {
        Write-Host "    [OK]   " -ForegroundColor Green -NoNewline
    } else {
        Write-Host "    [ERR]  " -ForegroundColor Red -NoNewline
    }
    Write-Host "$($DiskReport.FreeSpaceGB) GB disponible (minimum: $($DiskReport.RequiredGB) GB)"

    Write-Host ""

    # Section Fichiers
    Write-Host "  FICHIERS CREES ($($FileReport.Found)/$($FileReport.Total))" -ForegroundColor Yellow
    Write-Host "  --------" -ForegroundColor Yellow

    foreach ($file in $FileReport.Details) {
        $statusColor = switch ($file.Status) {
            "OK" { "Green" }
            "SYNTAX_ERROR" { "Red" }
            "MISSING" { if ($file.Required) { "Red" } else { "Yellow" } }
            default { "White" }
        }

        $statusIcon = switch ($file.Status) {
            "OK" { "[OK]  " }
            "SYNTAX_ERROR" { "[ERR] " }
            "MISSING" { "[---] " }
            default { "[???] " }
        }

        Write-Host "    $statusIcon" -ForegroundColor $statusColor -NoNewline
        Write-Host "$($file.Path)" -NoNewline

        if ($file.Size -gt 0) {
            Write-Host " ($($file.Size) bytes)" -ForegroundColor DarkGray
        } else {
            Write-Host ""
        }
    }

    Write-Host ""

    # Section Ports
    Write-Host "  PORTS" -ForegroundColor Yellow
    Write-Host "  -----" -ForegroundColor Yellow

    foreach ($port in $Global:RequiredPorts) {
        $isAvailable = $PortReport.Available | Where-Object { $_.Port -eq $port.Port }

        if ($isAvailable) {
            Write-Host "    [OK]   " -ForegroundColor Green -NoNewline
        } else {
            Write-Host "    [BUSY] " -ForegroundColor Yellow -NoNewline
        }
        Write-Host "Port $($port.Port) - $($port.Service)"
    }

    Write-Host ""

    # Section Docker
    Write-Host "  DOCKER" -ForegroundColor Yellow
    Write-Host "  ------" -ForegroundColor Yellow

    if ($DockerOK) {
        Write-Host "    [OK]   " -ForegroundColor Green -NoNewline
        Write-Host "Docker Desktop est operationnel"
    } else {
        Write-Host "    [WARN] " -ForegroundColor Yellow -NoNewline
        Write-Host "Docker Desktop n'est pas en cours d'execution"
    }

    if ($DockerComposeOK) {
        Write-Host "    [OK]   " -ForegroundColor Green -NoNewline
        Write-Host "Docker Compose v2 est disponible"
    } else {
        Write-Host "    [WARN] " -ForegroundColor Yellow -NoNewline
        Write-Host "Docker Compose v2 non detecte"
    }

    Write-Host ""
    Write-Host "  ==========================================================================" -ForegroundColor Cyan

    # Resume global
    $allFilesOK = ($FileReport.Missing -eq 0 -or ($FileReport.Details | Where-Object { $_.Status -eq "MISSING" -and $_.Required } | Measure-Object).Count -eq 0) -and $FileReport.SyntaxError -eq 0
    $criticalPortsOK = $PortReport.InUse.Count -eq 0
    $dockerFullyOK = $DockerOK -and $DockerComposeOK

    $overallStatus = $allFilesOK -and $dockerFullyOK -and $DiskReport.Success

    if ($overallStatus) {
        Write-Host ""
        Write-Host "    STATUS GLOBAL: " -NoNewline
        Write-Host "PRET" -ForegroundColor Green
        Write-Host ""
    } else {
        Write-Host ""
        Write-Host "    STATUS GLOBAL: " -NoNewline
        Write-Host "VERIFICATION REQUISE" -ForegroundColor Yellow
        Write-Host ""

        if (-not $DiskReport.Success) {
            Write-Host "    - Espace disque insuffisant" -ForegroundColor Red
        }
        if (-not $allFilesOK) {
            Write-Host "    - Certains fichiers sont manquants ou ont des erreurs" -ForegroundColor Yellow
        }
        if (-not $DockerOK) {
            Write-Host "    - Docker Desktop n'est pas en cours d'execution" -ForegroundColor Yellow
        }
        if (-not $DockerComposeOK) {
            Write-Host "    - Docker Compose v2 n'est pas disponible" -ForegroundColor Yellow
        }
        if (-not $criticalPortsOK) {
            Write-Host "    - Certains ports sont deja utilises" -ForegroundColor Yellow
        }
    }

    Write-Host ""
    Write-Host "  ==========================================================================" -ForegroundColor Cyan
}

# ============================================================================
# SCRIPT PRINCIPAL
# ============================================================================

try {
    # Initialiser le logging
    $scriptPath = $MyInvocation.MyCommand.Path
    if ([string]::IsNullOrEmpty($scriptPath)) {
        $Global:ScriptDir = Get-Location
    } else {
        $Global:ScriptDir = Split-Path -Parent $scriptPath
    }

    $Global:LogDir = Join-Path $Global:ScriptDir "logs"

    if (-not (Test-Path $Global:LogDir)) {
        New-Item -ItemType Directory -Path $Global:LogDir -Force | Out-Null
    }

    $timestamp = Get-Date -Format "yyyy-MM-dd-HHmmss"
    $Global:LogFile = Join-Path $Global:LogDir "setup-$timestamp.log"

    # Creer le fichier de log avec header
    $header = @"
================================================================================
  MINECRAFT BOT SETUP - LOG FILE
  Date: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
  PowerShell Version: $($PSVersionTable.PSVersion)
  OS: $([System.Environment]::OSVersion.VersionString)
  User: $env:USERNAME
  Computer: $env:COMPUTERNAME
  Script Version: 3.0.0
================================================================================

"@
    Set-Content -Path $Global:LogFile -Value $header -Encoding UTF8

    # Afficher le header
    Show-Header

    Write-Log "Demarrage du script d'installation v3.0" "INFO"
    Write-Log "Repertoire de travail: $Global:ScriptDir" "INFO"
    Write-Log "Fichier de log: $Global:LogFile" "INFO"

    # ========================================================================
    # VERIFICATION DES PREREQUIS SYSTEME
    # ========================================================================

    Write-Section "Verification des prerequis systeme"

    # Verifier PowerShell version
    $psVersion = $PSVersionTable.PSVersion
    if ($psVersion.Major -ge 5 -and ($psVersion.Major -gt 5 -or $psVersion.Minor -ge 1)) {
        Write-Log "PowerShell version $($psVersion.Major).$($psVersion.Minor) detecte (>= 5.1 requis)" "SUCCESS"
    } else {
        Write-Log "PowerShell version $($psVersion.Major).$($psVersion.Minor) detecte - Version 5.1+ requise!" "ERROR"
        exit 1
    }

    # Verifier les droits administrateur
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if ($isAdmin) {
        Write-Log "Execution en mode administrateur" "SUCCESS"
    } else {
        Write-Log "Execution en mode utilisateur standard (certaines installations peuvent echouer)" "WARN"
    }

    # Verifier les permissions d'ecriture
    if (-not (Test-DirectoryWritable $Global:ScriptDir)) {
        Write-Log "Impossible d'ecrire dans le repertoire. Executez en tant qu'administrateur." "ERROR"
        exit 1
    }
    Write-Log "Permissions d'ecriture OK" "SUCCESS"

    # Verifier l'espace disque (minimum 10GB)
    $diskReport = Test-DiskSpace -Path $Global:ScriptDir -MinimumGB $Global:MinDiskSpaceGB

    if (-not $diskReport.Success) {
        Write-Host ""
        Write-Host "  ATTENTION: Espace disque insuffisant!" -ForegroundColor Red
        Write-Host "  Requis: $($Global:MinDiskSpaceGB) GB, Disponible: $($diskReport.FreeSpaceGB) GB" -ForegroundColor Red
        Write-Host ""

        if (-not $Force) {
            $continue = Read-Host "  Continuer quand meme? (o/N)"
            if ($continue -ne "o" -and $continue -ne "O") {
                Write-Log "Installation annulee: espace disque insuffisant" "ERROR"
                exit 1
            }
        }
    }

    # ========================================================================
    # VERIFICATION ET INSTALLATION DES DEPENDANCES
    # ========================================================================

    $dependencyReport = $null

    if (-not $SkipDependencies) {
        # D'abord verifier l'etat actuel
        $dependencyReport = Test-AllDependencies

        # Si des dependances manquent, tenter l'installation
        if ($dependencyReport.Failed.Count -gt 0) {
            Write-Host ""
            Write-Host "  Dependances manquantes detectees: $($dependencyReport.Failed -join ', ')" -ForegroundColor Yellow
            Write-Host ""

            $installDeps = Read-Host "  Tenter l'installation automatique? (O/n)"
            if ($installDeps -eq "" -or $installDeps -eq "o" -or $installDeps -eq "O") {
                $dependenciesOK = Install-AllDependencies

                if (-not $dependenciesOK -and -not $Force) {
                    Write-Log "Certaines dependances critiques n'ont pas pu etre installees" "ERROR"
                    Write-Log "Utilisez -Force pour continuer malgre les erreurs" "INFO"
                }
            }
        }
    } else {
        Write-Log "Installation des dependances ignoree (-SkipDependencies)" "WARN"
    }

    # ========================================================================
    # VERIFICATION DES PORTS
    # ========================================================================

    $portReport = Test-AllPorts

    if ($portReport.InUse.Count -gt 0) {
        Write-Host ""
        Write-Host "  ATTENTION: Certains ports requis sont deja utilises:" -ForegroundColor Yellow
        foreach ($port in $portReport.InUse) {
            Write-Host "    - Port $($port.Port) ($($port.Service))" -ForegroundColor Yellow
        }
        Write-Host ""
        Write-Host "  Ces services devront etre arretes avant de lancer Docker Compose." -ForegroundColor Yellow
        Write-Host ""
    }

    # ========================================================================
    # COLLECTE DES INFORMATIONS
    # ========================================================================

    Write-Section "Configuration du projet"

    # Nom du projet
    $PROJECT_NAME = Read-ValidatedInput `
        -Prompt "Nom du projet (ex: MyServer)" `
        -Default "MinecraftServer" `
        -Required `
        -Pattern "^[a-zA-Z][a-zA-Z0-9_-]*$" `
        -PatternError "Le nom doit commencer par une lettre et ne contenir que des lettres, chiffres, tirets et underscores"

    $PROJECT_NAME_LOWER = $PROJECT_NAME.ToLower()
    $PROJECT_NAME_UPPER = $PROJECT_NAME.ToUpper()

    Write-Log "Projet: $PROJECT_NAME" "SUCCESS"

    Write-Section "Configuration Discord"

    # Discord Token
    $DISCORD_TOKEN = Read-ValidatedInput `
        -Prompt "Discord Bot Token" `
        -Required `
        -Pattern "^[A-Za-z0-9_\.\-]+$" `
        -PatternError "Token Discord invalide" `
        -IsSecret

    Write-Log "Token Discord configure" "SUCCESS"

    # Discord Guild ID
    $DISCORD_GUILD_ID = Read-ValidatedInput `
        -Prompt "Discord Guild ID (Server ID)" `
        -Required `
        -Pattern "^\d{17,20}$" `
        -PatternError "L'ID doit etre un nombre de 17-20 chiffres"

    Write-Log "Guild ID: $DISCORD_GUILD_ID" "SUCCESS"

    # Discord Client ID
    $DISCORD_CLIENT_ID = Read-ValidatedInput `
        -Prompt "Discord Client ID (Application ID)" `
        -Required `
        -Pattern "^\d{17,20}$" `
        -PatternError "L'ID doit etre un nombre de 17-20 chiffres"

    Write-Log "Client ID: $DISCORD_CLIENT_ID" "SUCCESS"

    # Discord Client Secret
    $DISCORD_CLIENT_SECRET = Read-ValidatedInput `
        -Prompt "Discord Client Secret" `
        -Required `
        -IsSecret

    Write-Log "Client Secret configure" "SUCCESS"

    # ========================================================================
    # GENERATION DES SECRETS
    # ========================================================================

    Write-Section "Generation des secrets securises"

    Write-Log "Generation des mots de passe cryptographiquement securises..." "INFO"

    $RCON_PASSWORD = Get-SecurePasswordAlphanumeric -Length 32
    Write-Log "RCON_PASSWORD genere (32 caracteres alphanumeriques)" "SUCCESS"

    $POSTGRES_PASSWORD = Get-SecurePasswordAlphanumeric -Length 32
    Write-Log "POSTGRES_PASSWORD genere (32 caracteres alphanumeriques)" "SUCCESS"

    $REDIS_PASSWORD = Get-SecurePasswordAlphanumeric -Length 32
    Write-Log "REDIS_PASSWORD genere (32 caracteres alphanumeriques)" "SUCCESS"

    $NEXTAUTH_SECRET = Get-NextAuthSecret
    Write-Log "NEXTAUTH_SECRET genere (base64, 32 bytes)" "SUCCESS"

    $INTERNAL_API_KEY = Get-HexKey -Bytes 32
    Write-Log "INTERNAL_API_KEY genere (hex, 32 bytes)" "SUCCESS"

    # ========================================================================
    # CREATION DE LA STRUCTURE DE DOSSIERS
    # ========================================================================

    Write-Section "Creation de la structure de dossiers"

    $directories = @(
        "bot",
        "bot\src",
        "bot\src\commands",
        "bot\src\events",
        "bot\src\utils",
        "web",
        "web\src",
        "web\src\app",
        "web\src\components",
        "web\public",
        "api",
        "api\src",
        "api\src\routes",
        "api\src\middleware",
        "database",
        "database\migrations",
        "database\seeds",
        "minecraft",
        "minecraft\plugins",
        "minecraft\config",
        "minecraft\worlds",
        "docker",
        "docker\bot",
        "docker\web",
        "docker\api",
        "scripts",
        "logs",
        "backups",
        "config",
        "templates"
    )

    $createdDirs = @()

    foreach ($dir in $directories) {
        $fullPath = Join-Path $Global:ScriptDir $dir
        if (-not (Test-Path $fullPath)) {
            New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
            Write-Log "Cree: $dir" "SUCCESS"
            $createdDirs += $fullPath
        } else {
            Write-Log "Existe: $dir" "INFO"
        }
    }

    # ========================================================================
    # CREATION DES FICHIERS DE CONFIGURATION
    # ========================================================================

    Write-Section "Creation des fichiers de configuration"

    # Fichier .env principal
    $envContent = @"
# ============================================================================
# Configuration $PROJECT_NAME - Genere automatiquement le $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
# ============================================================================

# Projet
PROJECT_NAME=$PROJECT_NAME
PROJECT_NAME_LOWER=$PROJECT_NAME_LOWER
NODE_ENV=production

# ============================================================================
# Discord Configuration
# ============================================================================
DISCORD_TOKEN=$DISCORD_TOKEN
DISCORD_GUILD_ID=$DISCORD_GUILD_ID
DISCORD_CLIENT_ID=$DISCORD_CLIENT_ID
DISCORD_CLIENT_SECRET=$DISCORD_CLIENT_SECRET

# ============================================================================
# Minecraft RCON
# ============================================================================
RCON_HOST=minecraft
RCON_PORT=25575
RCON_PASSWORD=$RCON_PASSWORD

# ============================================================================
# PostgreSQL Database
# ============================================================================
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=${PROJECT_NAME_LOWER}_db
POSTGRES_USER=${PROJECT_NAME_LOWER}_user
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
DATABASE_URL=postgresql://${PROJECT_NAME_LOWER}_user:${POSTGRES_PASSWORD}@postgres:5432/${PROJECT_NAME_LOWER}_db

# ============================================================================
# Redis Cache
# ============================================================================
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=$REDIS_PASSWORD
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379

# ============================================================================
# NextAuth (Web Dashboard)
# ============================================================================
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=$NEXTAUTH_SECRET

# ============================================================================
# API Configuration
# ============================================================================
API_HOST=0.0.0.0
API_PORT=3001
INTERNAL_API_KEY=$INTERNAL_API_KEY

# ============================================================================
# Minecraft Server
# ============================================================================
MINECRAFT_VERSION=1.20.4
MINECRAFT_TYPE=PAPER
MINECRAFT_MEMORY=2G
MINECRAFT_PORT=25565
"@

    $envPath = Join-Path $Global:ScriptDir ".env"
    Set-Content -Path $envPath -Value $envContent -Encoding UTF8
    Write-Log "Cree: .env" "SUCCESS"

    # Fichier .env.example (sans les secrets)
    $envExampleContent = @"
# ============================================================================
# Configuration $PROJECT_NAME - Template
# ============================================================================

# Projet
PROJECT_NAME=$PROJECT_NAME
PROJECT_NAME_LOWER=$PROJECT_NAME_LOWER
NODE_ENV=production

# ============================================================================
# Discord Configuration
# ============================================================================
DISCORD_TOKEN=your_discord_bot_token_here
DISCORD_GUILD_ID=your_guild_id_here
DISCORD_CLIENT_ID=your_client_id_here
DISCORD_CLIENT_SECRET=your_client_secret_here

# ============================================================================
# Minecraft RCON
# ============================================================================
RCON_HOST=minecraft
RCON_PORT=25575
RCON_PASSWORD=generate_secure_password

# ============================================================================
# PostgreSQL Database
# ============================================================================
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=${PROJECT_NAME_LOWER}_db
POSTGRES_USER=${PROJECT_NAME_LOWER}_user
POSTGRES_PASSWORD=generate_secure_password
DATABASE_URL=postgresql://${PROJECT_NAME_LOWER}_user:PASSWORD@postgres:5432/${PROJECT_NAME_LOWER}_db

# ============================================================================
# Redis Cache
# ============================================================================
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=generate_secure_password
REDIS_URL=redis://:PASSWORD@redis:6379

# ============================================================================
# NextAuth (Web Dashboard)
# ============================================================================
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=generate_base64_secret

# ============================================================================
# API Configuration
# ============================================================================
API_HOST=0.0.0.0
API_PORT=3001
INTERNAL_API_KEY=generate_hex_key

# ============================================================================
# Minecraft Server
# ============================================================================
MINECRAFT_VERSION=1.20.4
MINECRAFT_TYPE=PAPER
MINECRAFT_MEMORY=2G
MINECRAFT_PORT=25565
"@

    $envExamplePath = Join-Path $Global:ScriptDir ".env.example"
    Set-Content -Path $envExamplePath -Value $envExampleContent -Encoding UTF8
    Write-Log "Cree: .env.example" "SUCCESS"

    # docker-compose.yml
    $dockerComposeContent = @"
# ============================================================================
# Docker Compose - $PROJECT_NAME
# Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
# ============================================================================
version: '3.8'

services:
  # ==========================================================================
  # Minecraft Server
  # ==========================================================================
  minecraft:
    image: itzg/minecraft-server:latest
    container_name: ${PROJECT_NAME_LOWER}-minecraft
    environment:
      EULA: "TRUE"
      TYPE: `${MINECRAFT_TYPE:-PAPER}
      VERSION: `${MINECRAFT_VERSION:-1.20.4}
      MEMORY: `${MINECRAFT_MEMORY:-2G}
      ENABLE_RCON: "true"
      RCON_PASSWORD: `${RCON_PASSWORD}
      RCON_PORT: 25575
    ports:
      - "`${MINECRAFT_PORT:-25565}:25565"
      - "25575:25575"
    volumes:
      - ./minecraft/worlds:/data/worlds
      - ./minecraft/plugins:/data/plugins
      - ./minecraft/config:/data/config
    restart: unless-stopped
    networks:
      - ${PROJECT_NAME_LOWER}-network

  # ==========================================================================
  # PostgreSQL Database
  # ==========================================================================
  postgres:
    image: postgres:15-alpine
    container_name: ${PROJECT_NAME_LOWER}-postgres
    environment:
      POSTGRES_DB: `${POSTGRES_DB}
      POSTGRES_USER: `${POSTGRES_USER}
      POSTGRES_PASSWORD: `${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/migrations:/docker-entrypoint-initdb.d
    ports:
      - "5432:5432"
    restart: unless-stopped
    networks:
      - ${PROJECT_NAME_LOWER}-network

  # ==========================================================================
  # Redis Cache
  # ==========================================================================
  redis:
    image: redis:7-alpine
    container_name: ${PROJECT_NAME_LOWER}-redis
    command: redis-server --requirepass `${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    restart: unless-stopped
    networks:
      - ${PROJECT_NAME_LOWER}-network

  # ==========================================================================
  # Discord Bot
  # ==========================================================================
  bot:
    build:
      context: ./bot
      dockerfile: ../docker/bot/Dockerfile
    container_name: ${PROJECT_NAME_LOWER}-bot
    env_file:
      - .env
    depends_on:
      - postgres
      - redis
      - minecraft
    restart: unless-stopped
    networks:
      - ${PROJECT_NAME_LOWER}-network

  # ==========================================================================
  # API Backend
  # ==========================================================================
  api:
    build:
      context: ./api
      dockerfile: ../docker/api/Dockerfile
    container_name: ${PROJECT_NAME_LOWER}-api
    env_file:
      - .env
    ports:
      - "`${API_PORT:-3001}:3001"
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
    networks:
      - ${PROJECT_NAME_LOWER}-network

  # ==========================================================================
  # Web Dashboard
  # ==========================================================================
  web:
    build:
      context: ./web
      dockerfile: ../docker/web/Dockerfile
    container_name: ${PROJECT_NAME_LOWER}-web
    env_file:
      - .env
    ports:
      - "3000:3000"
    depends_on:
      - api
    restart: unless-stopped
    networks:
      - ${PROJECT_NAME_LOWER}-network

# ============================================================================
# Networks
# ============================================================================
networks:
  ${PROJECT_NAME_LOWER}-network:
    driver: bridge

# ============================================================================
# Volumes
# ============================================================================
volumes:
  postgres_data:
  redis_data:
"@

    $dockerComposePath = Join-Path $Global:ScriptDir "docker-compose.yml"
    Set-Content -Path $dockerComposePath -Value $dockerComposeContent -Encoding UTF8
    Write-Log "Cree: docker-compose.yml" "SUCCESS"

    # .gitignore
    $gitignoreContent = @"
# ============================================================================
# $PROJECT_NAME - Git Ignore
# ============================================================================

# Environment
.env
.env.local
.env.*.local
*.local

# Dependencies
node_modules/
vendor/

# Build outputs
dist/
build/
.next/
out/

# Logs
logs/
*.log
npm-debug.log*

# Runtime data
pids/
*.pid
*.seed

# IDE
.idea/
.vscode/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Minecraft
minecraft/worlds/
minecraft/plugins/*.jar
minecraft/logs/

# Database
*.sql
*.dump

# Backups
backups/

# Secrets
*.pem
*.key
credentials.json
"@

    $gitignorePath = Join-Path $Global:ScriptDir ".gitignore"
    Set-Content -Path $gitignorePath -Value $gitignoreContent -Encoding UTF8
    Write-Log "Cree: .gitignore" "SUCCESS"

    # Dockerfile pour le bot
    $dockerfileBotContent = @"
FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

CMD ["node", "src/index.js"]
"@

    $dockerfileBotPath = Join-Path $Global:ScriptDir "docker\bot\Dockerfile"
    Set-Content -Path $dockerfileBotPath -Value $dockerfileBotContent -Encoding UTF8
    Write-Log "Cree: docker/bot/Dockerfile" "SUCCESS"

    # Dockerfile pour l'API
    $dockerfileApiContent = @"
FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

EXPOSE 3001

CMD ["node", "src/index.js"]
"@

    $dockerfileApiPath = Join-Path $Global:ScriptDir "docker\api\Dockerfile"
    Set-Content -Path $dockerfileApiPath -Value $dockerfileApiContent -Encoding UTF8
    Write-Log "Cree: docker/api/Dockerfile" "SUCCESS"

    # Dockerfile pour le web
    $dockerfileWebContent = @"
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

COPY --from=builder /app/next.config.js ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000

CMD ["node", "server.js"]
"@

    $dockerfileWebPath = Join-Path $Global:ScriptDir "docker\web\Dockerfile"
    Set-Content -Path $dockerfileWebPath -Value $dockerfileWebContent -Encoding UTF8
    Write-Log "Cree: docker/web/Dockerfile" "SUCCESS"

    # Package.json pour le bot
    $packageBotContent = @"
{
  "name": "${PROJECT_NAME_LOWER}-bot",
  "version": "1.0.0",
  "description": "Discord Bot for $PROJECT_NAME",
  "main": "src/index.js",
  "scripts": {
    "start": "node src/index.js",
    "dev": "nodemon src/index.js"
  },
  "dependencies": {
    "discord.js": "^14.14.1",
    "dotenv": "^16.3.1",
    "pg": "^8.11.3",
    "redis": "^4.6.12",
    "rcon-client": "^4.2.4"
  },
  "devDependencies": {
    "nodemon": "^3.0.2"
  }
}
"@

    $packageBotPath = Join-Path $Global:ScriptDir "bot\package.json"
    Set-Content -Path $packageBotPath -Value $packageBotContent -Encoding UTF8
    Write-Log "Cree: bot/package.json" "SUCCESS"

    # Index.js placeholder pour le bot
    $indexBotContent = @"
// ============================================================================
// $PROJECT_NAME Discord Bot
// Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
// ============================================================================

require('dotenv').config();
const { Client, GatewayIntentBits, Collection } = require('discord.js');

const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent,
        GatewayIntentBits.GuildMembers,
    ]
});

client.commands = new Collection();

client.once('ready', () => {
    console.log(\`[${PROJECT_NAME}] Bot connecte en tant que \${client.user.tag}\`);
});

client.on('interactionCreate', async interaction => {
    if (!interaction.isChatInputCommand()) return;
    // Command handling here
});

client.login(process.env.DISCORD_TOKEN);
"@

    $indexBotPath = Join-Path $Global:ScriptDir "bot\src\index.js"
    Set-Content -Path $indexBotPath -Value $indexBotContent -Encoding UTF8
    Write-Log "Cree: bot/src/index.js" "SUCCESS"

    # README.md
    $readmeContent = @"
# $PROJECT_NAME

## Description
Projet Minecraft avec Bot Discord, Dashboard Web et API.

## Installation
L'installation a ete effectuee via le script ``setup.ps1``.

## Demarrage

``````powershell
# Demarrer tous les services
docker compose up -d

# Voir les logs
docker compose logs -f

# Arreter les services
docker compose down
``````

## Services

| Service   | Port  | Description              |
|-----------|-------|--------------------------|
| Minecraft | 25565 | Serveur Minecraft        |
| RCON      | 25575 | Console Minecraft        |
| Web       | 3000  | Dashboard                |
| API       | 3001  | Backend API              |
| PostgreSQL| 5432  | Base de donnees          |
| Redis     | 6379  | Cache                    |

## Structure

``````
$PROJECT_NAME/
├── bot/                # Discord Bot
├── web/                # Dashboard Next.js
├── api/                # Backend API
├── minecraft/          # Serveur Minecraft
├── database/           # Migrations et seeds
├── docker/             # Dockerfiles
├── config/             # Configuration
├── logs/               # Logs
└── backups/            # Sauvegardes
``````

---
Genere le $(Get-Date -Format "yyyy-MM-dd") par setup.ps1 v3.0
"@

    $readmePath = Join-Path $Global:ScriptDir "README.md"
    Set-Content -Path $readmePath -Value $readmeContent -Encoding UTF8
    Write-Log "Cree: README.md" "SUCCESS"

    # ========================================================================
    # VERIFICATION POST-INSTALLATION
    # ========================================================================

    Write-Section "Verification post-installation"

    # Verifier tous les fichiers
    $fileReport = Test-AllFiles -BaseDir $Global:ScriptDir

    # Verifier Docker
    $dockerOK = Test-DockerRunning
    $dockerComposeOK = Test-DockerComposeV2

    # Sauvegarder le rapport complet
    $reportPath = Save-FinalReport `
        -FileReport $fileReport `
        -PortReport $portReport `
        -DiskReport $diskReport `
        -DependencyReport $dependencyReport `
        -DockerOK $dockerOK `
        -DockerComposeOK $dockerComposeOK `
        -ProjectName $PROJECT_NAME

    # ========================================================================
    # RESUME FINAL
    # ========================================================================

    Write-Host ""
    Write-Host "  ==========================================================================" -ForegroundColor Green
    Write-Host "                         INSTALLATION TERMINEE !                            " -ForegroundColor Green
    Write-Host "  ==========================================================================" -ForegroundColor Green
    Write-Host ""

    Write-Section "Resume du projet"
    Write-Host "  Nom du projet     : " -NoNewline; Write-Host $PROJECT_NAME -ForegroundColor Cyan
    Write-Host "  Repertoire        : " -NoNewline; Write-Host $Global:ScriptDir -ForegroundColor Cyan
    Write-Host "  Guild ID          : " -NoNewline; Write-Host $DISCORD_GUILD_ID -ForegroundColor Cyan
    Write-Host "  Client ID         : " -NoNewline; Write-Host $DISCORD_CLIENT_ID -ForegroundColor Cyan
    Write-Host "  Fichier de log    : " -NoNewline; Write-Host $Global:LogFile -ForegroundColor Cyan

    Write-Section "Mots de passe generes (CONSERVEZ-LES !)"
    Write-Host ""
    Write-Host "  ┌────────────────────────────────────────────────────────────────────────┐" -ForegroundColor DarkGray
    Write-Host "  │ " -ForegroundColor DarkGray -NoNewline
    Write-Host "RCON_PASSWORD     " -ForegroundColor Yellow -NoNewline
    Write-Host ": $RCON_PASSWORD" -ForegroundColor White -NoNewline
    Write-Host " │" -ForegroundColor DarkGray
    Write-Host "  │ " -ForegroundColor DarkGray -NoNewline
    Write-Host "POSTGRES_PASSWORD " -ForegroundColor Yellow -NoNewline
    Write-Host ": $POSTGRES_PASSWORD" -ForegroundColor White -NoNewline
    Write-Host " │" -ForegroundColor DarkGray
    Write-Host "  │ " -ForegroundColor DarkGray -NoNewline
    Write-Host "REDIS_PASSWORD    " -ForegroundColor Yellow -NoNewline
    Write-Host ": $REDIS_PASSWORD" -ForegroundColor White -NoNewline
    Write-Host " │" -ForegroundColor DarkGray
    Write-Host "  └────────────────────────────────────────────────────────────────────────┘" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  NEXTAUTH_SECRET   : " -NoNewline; Write-Host $NEXTAUTH_SECRET -ForegroundColor DarkYellow
    Write-Host "  INTERNAL_API_KEY  : " -NoNewline; Write-Host $INTERNAL_API_KEY -ForegroundColor DarkYellow
    Write-Host ""

    # Afficher le rapport de verification finale
    Show-FinalSummary `
        -FileReport $fileReport `
        -PortReport $portReport `
        -DiskReport $diskReport `
        -DockerOK $dockerOK `
        -DockerComposeOK $dockerComposeOK `
        -ProjectName $PROJECT_NAME `
        -ScriptDir $Global:ScriptDir

    Write-Section "Prochaines etapes"
    Write-Host ""
    Write-Host "  1. " -ForegroundColor Cyan -NoNewline
    Write-Host "Naviguer vers le repertoire du projet:" -ForegroundColor White
    Write-Host "     cd `"$Global:ScriptDir`"" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  2. " -ForegroundColor Cyan -NoNewline
    Write-Host "Demarrer les services Docker:" -ForegroundColor White
    Write-Host "     docker compose up -d" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  3. " -ForegroundColor Cyan -NoNewline
    Write-Host "Verifier les logs:" -ForegroundColor White
    Write-Host "     docker compose logs -f" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  4. " -ForegroundColor Cyan -NoNewline
    Write-Host "Acceder aux services:" -ForegroundColor White
    Write-Host "     - Minecraft : localhost:25565" -ForegroundColor Gray
    Write-Host "     - Dashboard : http://localhost:3000" -ForegroundColor Gray
    Write-Host "     - API       : http://localhost:3001" -ForegroundColor Gray
    Write-Host ""

    Write-Section "Fichiers de log et rapports"
    Write-Host "  Log d'installation  : " -NoNewline; Write-Host $Global:LogFile -ForegroundColor Cyan
    Write-Host "  Rapport verification: " -NoNewline; Write-Host $reportPath -ForegroundColor Cyan
    Write-Host ""

    # Liste des fichiers crees
    Write-Section "Fichiers crees"
    Write-Host ""
    foreach ($file in $fileReport.FileList) {
        Write-Host "  - $file" -ForegroundColor Gray
    }
    Write-Host ""

    # Duree totale
    $duration = (Get-Date) - $Global:StartTime
    Write-Log "Installation terminee en $($duration.TotalSeconds.ToString('F2')) secondes" "SUCCESS"

    Write-Host "  ==========================================================================" -ForegroundColor Green
    Write-Host "           Bonne chance avec votre projet $PROJECT_NAME !                   " -ForegroundColor Green
    Write-Host "  ==========================================================================" -ForegroundColor Green
    Write-Host ""

} catch {
    Write-Host ""
    Write-Log "Une erreur s'est produite: $($_.Exception.Message)" "ERROR"
    Write-Host "  Ligne: $($_.InvocationInfo.ScriptLineNumber)" -ForegroundColor Red

    if ($Global:LogFile -and (Test-Path $Global:LogFile)) {
        Write-Host "  Consultez le fichier de log: $Global:LogFile" -ForegroundColor Yellow
    }

    Write-Host ""
    exit 1
}
