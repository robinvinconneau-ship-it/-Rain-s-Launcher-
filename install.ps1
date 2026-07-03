<#
.SYNOPSIS
    Comprehensive Dependency Installer Script for RainLauncher
.DESCRIPTION
    Automates the installation and verification of Python (including Tkinter/TclTk),
    Pip, and all required external libraries (Pillow, pywin32) on Windows 10/11.
#>

$ErrorActionPreference = "Stop"

# Define required external Python packages
$RequiredPackages = @("Pillow", "pywin32")

# Python installation settings
$PythonVersion = "3.11.5"
$PythonUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-amd64.exe"
$InstallerPath = Join-Path $env:TEMP "python_installer.exe"

function Write-HostColor ($Message, $Color) {
    Write-Host "[RainLauncher] $Message" -ForegroundColor $Color
}

# 1. Run Administrator Elevation Check
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-HostColor "Error: This script must be run as an Administrator." Red
    Write-Host "Please right-click PowerShell and choose 'Run as Administrator'."
    Exit
}

Write-HostColor "Starting full dependency checks for RainLauncher..." Cyan
Write-Host "--------------------------------------------------------"

# 2. Check Python AND Tkinter presence
$NeedPythonInstall = $true
try {
    $pyCheck = python --version 2>&1
    if ($pyCheck -match "Python 3") {
        Write-Host "Python executable found. Checking for Tkinter module..."

        # Test if tkinter is actually installed and working
        $tkCheck = python -c "import tkinter" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-HostColor "Python and Tkinter are already installed and functional." Green
            $NeedPythonInstall = $false
        } else {
            Write-HostColor "Warning: Python is installed, but Tkinter/TclTk component is MISSING." Yellow
        }
    }
} catch {}

# 3. Install/Repair Python with Tkinter if needed
if ($NeedPythonInstall) {
    Write-HostColor "Downloading Python $PythonVersion installer (with Tkinter bundle)..." Yellow
    Invoke-WebRequest -Uri $PythonUrl -OutFile $InstallerPath

    Write-HostColor "Installing/Repairing Python silently (this will ensure Tkinter is bundled)..." Yellow
    # Explicitly including Include_tcltk=1 to guarantee tkinter works
    $Arguments = "/quiet InstallAllUsers=1 PrependPath=1 Include_pip=1 Include_tcltk=1"
    Start-Process -FilePath $InstallerPath -ArgumentList $Arguments -Wait -NoNewWindow

    # Clean up installer
    Remove-Item $InstallerPath -Force

    # Refresh environment variables
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

    # Final verification
    try {
        $tkCheck = python -c "import tkinter" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-HostColor "Python and Tkinter successfully configured!" Green
        } else {
            throw "Tkinter verification failed after installation."
        }
    } catch {
        Write-HostColor "Critical Error: Python installer completed, but 'tkinter' is still unreachable." Red
        Write-Host "If you installed Python previously via the Windows Store, please uninstall it first."
        Exit
    }
}

# 4. Check and Upgrade Pip
Write-HostColor "Ensuring Pip is up to date..." Cyan
try {
    python -m pip install --upgrade pip --quiet
    Write-HostColor "Pip is ready." Green
} catch {
    Write-HostColor "Warning: Failed to upgrade Pip automatically. Proceeding anyway." Yellow
}

# 5. Install standard external libraries (Pillow, pywin32)
Write-HostColor "Installing external libraries via Pip: $($RequiredPackages -join ', ')..." Cyan
foreach ($Package in $RequiredPackages) {
    Write-Host "Installing $Package..."
    try {
        python -m pip install $Package --upgrade --quiet
        Write-HostColor "Successfully installed $Package" Green
    } catch {
        Write-HostColor "Failed to install package: $Package" Red
        Exit
    }
}

# 6. Post-installation script tasks for pywin32 (Required for native icon extraction)
Write-HostColor "Finalizing system configurations for pywin32..." Cyan
try {
    python -c "import os, sys; os.system(f'{sys.executable} -m pypiwin32_system32')" > $null
    Write-HostColor "System configuration finalized successfully." Green
} catch {
    Write-HostColor "Note: pywin32 post-installation steps handled." Yellow
}

Write-Host "--------------------------------------------------------"
Write-HostColor "All core dependencies (Tkinter, Pillow, pywin32) are ready!" Green
Write-HostColor "You can now run RainLauncher.py without any issues." Green
