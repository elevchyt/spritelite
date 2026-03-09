param(
    [switch]$Clean,
    # target architecture: 32, 64, or both. PyInstaller cannot cross-compile,
    # so each build requires a matching Python interpreter to be installed.
    [ValidateSet('32','64','both')]
    [string]$Arch = 'both',
    # Use an explicit Python version per architecture so the 32-bit build can
    # target older systems like Windows 7. Python 3.9+ does not support
    # Windows 7, so the default 32-bit runtime stays on Python 3.8.
    [string]$PythonVersion64 = '3.11',
    [string]$PythonVersion32 = '3.8',
    [string]$PyInstallerVersion32 = '4.10'
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$mainScript = Join-Path $projectRoot "main.py"
$iconPath = Join-Path $projectRoot "icon.ico"
$iconsPath = Join-Path $projectRoot "icons"
Set-Location $projectRoot

function Get-PythonLauncher {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet('32','64')]
        [string]$TargetArch,
        [Parameter(Mandatory = $true)]
        [string]$PythonVersion
    )

    if (Get-Command py -ErrorAction SilentlyContinue) {
        return @("py", "-$PythonVersion-$TargetArch")
    }

    if (Get-Command python -ErrorAction SilentlyContinue) {
        Write-Warning "Could not locate the py launcher; ensure PATH points to a $TargetArch-bit Python $PythonVersion interpreter."
        return @("python")
    }

    throw "Python was not found on PATH. Install Python or activate your virtual environment first."
}

function Get-PythonBitness {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Launcher
    )

    $command = $Launcher[0]
    $args = @()
    if ($Launcher.Length -gt 1) {
        $args += $Launcher[1..($Launcher.Length - 1)]
    }
    $args += @("-c", "import struct; print(struct.calcsize('P') * 8)")

    $output = & $command @args
    if ($LASTEXITCODE -ne 0 -or -not $output) {
        $launcherText = ($Launcher -join ' ')
        throw "Unable to query the Python interpreter using '$launcherText'. Ensure the requested Python runtime is installed and available."
    }

    return ($output | Select-Object -Last 1).Trim()
}

function Invoke-Build {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet('32','64')]
        [string]$TargetArch
    )

    $pythonVersion = if ($TargetArch -eq '32') { $PythonVersion32 } else { $PythonVersion64 }
    $pyInstallerPackage = if ($TargetArch -eq '32') { "pyinstaller==$PyInstallerVersion32" } else { 'pyinstaller' }
    $pythonLauncher = Get-PythonLauncher -TargetArch $TargetArch -PythonVersion $pythonVersion
    $detectedArch = Get-PythonBitness -Launcher $pythonLauncher

    if ($detectedArch -ne $TargetArch) {
        throw "Requested a $TargetArch-bit build, but the selected Python interpreter reports $detectedArch-bit. Install Python $pythonVersion ($TargetArch-bit) or use the py launcher."
    }

    $exeName = if ($TargetArch -eq '32') { 'SpriteLite-win32' } else { 'SpriteLite' }
    $distDir = Join-Path $projectRoot "dist\win$TargetArch"
    $workDir = Join-Path $projectRoot "build\win$TargetArch"
    $specDir = Join-Path $projectRoot "build\spec\win$TargetArch"
    $distExe = Join-Path $distDir "$exeName.exe"

    Write-Host "Installing build dependencies for Python $pythonVersion ($TargetArch-bit)..." -ForegroundColor Cyan
    $pipArgs = @()
    if ($pythonLauncher.Length -gt 1) {
        $pipArgs += $pythonLauncher[1..($pythonLauncher.Length - 1)]
    }
    $pipArgs += @("-m", "pip", "install", "-r", "requirements.txt", $pyInstallerPackage)
    & $pythonLauncher[0] @pipArgs
    if ($LASTEXITCODE -ne 0) {
        throw "pip install failed for the $TargetArch-bit build with exit code $LASTEXITCODE"
    }

    Write-Host "Building SpriteLite.exe for $TargetArch-bit Windows with Python $pythonVersion and $pyInstallerPackage..." -ForegroundColor Cyan
    $pyInstallerArgs = @()
    if ($pythonLauncher.Length -gt 1) {
        $pyInstallerArgs += $pythonLauncher[1..($pythonLauncher.Length - 1)]
    }
    $pyInstallerArgs += @(
        "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--onefile",
        "--name", $exeName,
        "--icon", $iconPath,
        "--distpath", $distDir,
        "--workpath", $workDir,
        "--specpath", $specDir,
        "--add-data", "${iconsPath};icons",
        "--add-data", "${iconPath};.",
        $mainScript
    )
    & $pythonLauncher[0] @pyInstallerArgs
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed for the $TargetArch-bit build with exit code $LASTEXITCODE"
    }

    if (-not (Test-Path $distExe)) {
        throw "Build finished but the executable was not found at $distExe"
    }

    Write-Host "Build complete: $distExe" -ForegroundColor Green
}

if ($Clean) {
    foreach ($path in @("build", "dist", "SpriteLite.spec")) {
        if (Test-Path $path) {
            Remove-Item $path -Recurse -Force
        }
    }
}

if ($Arch -eq 'both') {
    foreach ($targetArch in @('64', '32')) {
        Invoke-Build -TargetArch $targetArch
    }
}
else {
    Invoke-Build -TargetArch $Arch
}