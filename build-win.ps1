param(
    [switch]$Clean,
    # target architecture: 32 or 64. 64 is the default and simply uses whatever
    # Python is on PATH.  To build a 32‑bit exe you must invoke the 32‑bit
    # interpreter (e.g. via the py launcher with -3-32) or run this script on a
    # 32-bit Windows machine. PyInstaller cannot cross‑compile.
    [ValidateSet('32','64')]
    [string]$Arch = '64'
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$distExe = Join-Path $projectRoot "dist\SpriteLite.exe"
Set-Location $projectRoot

function Get-PythonLauncher {
    # Use the py launcher to select the right bitness if requested.
    if ($Arch -eq '32') {
        if (Get-Command py -ErrorAction SilentlyContinue) {
            # "-3-32" forces 32‑bit Python 3 if installed
            return @("py", "-3-32","-m")
        }
        # fall through to warning below
    }

    if (Get-Command py -ErrorAction SilentlyContinue) {
        return @("py", "-m")
    }

    if (Get-Command python -ErrorAction SilentlyContinue) {
        Write-Warning "Could not locate the py launcher; ensure you are using a $Arch-bit interpreter."
        return @("python", "-m")
    }

    throw "Python was not found on PATH. Install Python or activate your virtual environment first."
}

if ($Clean) {
    foreach ($path in @("build", "dist", "SpriteLite.spec")) {
        if (Test-Path $path) {
            Remove-Item $path -Recurse -Force
        }
    }
}

$pythonLauncher = Get-PythonLauncher

Write-Host "Installing build dependencies..." -ForegroundColor Cyan
& $pythonLauncher[0] $pythonLauncher[1] pip install -r requirements.txt pyinstaller

Write-Host "Building SpriteLite.exe for $Arch-bit Windows..." -ForegroundColor Cyan
# PyInstaller will create an executable matching the Python interpreter's
# architecture. To get a 32‑bit build you _must_ run this script with a 32‑bit
# interpreter (use "py -3-32" or run on a 32-bit Windows 7 machine).
& $pythonLauncher[0] $pythonLauncher[1] PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --onefile `
    --name SpriteLite `
    --icon icon.ico `
    --add-data "icons;icons" `
    --add-data "icon.ico;." `
    main.py

if (-not (Test-Path $distExe)) {
    throw "Build finished but the executable was not found at $distExe"
}

Write-Host "Build complete: $distExe" -ForegroundColor Green