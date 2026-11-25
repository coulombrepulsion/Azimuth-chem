<#
.SYNOPSIS
Install Azimuth. Contract: docs/setup/INSTALLATION.md.
.DESCRIPTION
Uses a platform lock, verifies assets, preserves existing environments.
.PARAMETER PythonBin
Python executable path; "auto" (default): py -3.13, py -3.12, python, python3 - the first 64-bit Python 3.12 or 3.13
(0.91.58: a colleague without Python 3.13 got "No runtime installed that matches 3.13").
.PARAMETER PythonVersion
0.91.61: the python.org release installed for this user when no Python 3.12 or 3.13 is found (an installer
python-3.13*-amd64.exe next to this file is taken first, without internet).
.PARAMETER OfflineBundle
Wheel directory used with NoDownload, or populated for later offline use.
.EXAMPLE
.\setup.ps1
.\setup.ps1 -PythonBin "C:\Python313\python.exe"
#>
param([string]$PythonBin = "auto", [switch]$NoDownload,
      [switch]$SkipVenv, [switch]$Debug, [string]$OfflineBundle = "",
      [string]$PythonVersion = "3.13.17")
$ErrorActionPreference = "Continue"
function Stop-WithError([string]$Text) { throw "$Text. Log: setup-log.txt; see docs/setup/TROUBLESHOOTING.md; retry -Debug." }
$script:Step = ""
function Run-Python([string[]]$Arguments) {
    if (-not (Get-Command $script:Executable -ErrorAction SilentlyContinue)) {
        Stop-WithError "Python not found ($script:Executable): install Python 3.13 (64-bit) from https://www.python.org/downloads/windows/, ticking "Add python.exe to PATH""
    }
    & $script:Executable @script:Prefix @Arguments
    if ($LASTEXITCODE -ne 0) { Stop-WithError "Step '$script:Step' failed (code $LASTEXITCODE); the lines above say why" }
}
# 0.222.35: pip of this computer may take its packages from a mirror (pip.ini: index-url) that does not answer -
# then the same installation once more from the official index (Windows check 2026-11-24: pypi.tuna.tsinghua.edu.cn
# timed out five times, "No matching distribution found for contourpy==1.4.0")
function Pip-Install([string[]]$Arguments) {
    & $script:Executable @script:Prefix -m pip install @Arguments
    if ($LASTEXITCODE -eq 0) { return }
    Write-Host "[setup] pip failed with the package index of this computer; trying again with https://pypi.org/simple"
    Run-Python (@("-m", "pip", "install", "--index-url", "https://pypi.org/simple") + $Arguments)
}
$oldEncoding = [Console]::OutputEncoding
$oldOutput = $OutputEncoding
$oldLocation = Get-Location
try {
    [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
    $OutputEncoding = [Console]::OutputEncoding
    Set-Location $PSScriptRoot -ErrorAction Stop
    # 0.85.1: everything printed goes to setup-log.txt too, and a failure names its step
    try { Start-Transcript -Path (Join-Path $PSScriptRoot "setup-log.txt") -Force | Out-Null } catch {}
    Get-ChildItem -File -Filter *.ps1 | Unblock-File
    if ($Debug) { Set-PSDebug -Trace 1 }
    # 0.91.58: any 64-bit Python 3.12 or 3.13 (NumPy 2.5 needs 3.12+; 3.13 is the tested one, with the hashed lock);
    # a Conda Python is fine for the .venv (it was a question that stopped the setup)
    $check = "import struct,sys; sys.exit(0 if (3,12) <= sys.version_info[:2] <= (3,13) and struct.calcsize('P') == 8 else 1)"
    $script:Executable = $null
    $script:Prefix = @()
    if ($PythonBin -and $PythonBin -ne "auto" -and $PythonBin -ne "py -3.13") {
        $candidates = @(,@($PythonBin))
    } else {
        $candidates = @(@("py", "-3.13"), @("py", "-3.12"), @("python"), @("python3"))
        # 0.91.61: the usual folders of python.org (a Python installed without "Add python.exe to PATH")
        foreach ($root in @((Join-Path $env:LOCALAPPDATA "Programs\Python"), $env:ProgramFiles)) {
            foreach ($v in @("Python313", "Python312")) {
                $path = Join-Path $root "$v\python.exe"
                if (Test-Path $path) { $candidates += ,@($path) }
            }
        }
    }
    function Find-Python {
        foreach ($candidate in $candidates) {
            $exe = $candidate[0]
            $pre = @($candidate | Select-Object -Skip 1)
            if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) { continue }
            & $exe @pre -c $check 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) { $script:Executable = $exe; $script:Prefix = $pre; return }
        }
    }
    Find-Python
    Write-Host "[setup] 1/6 Python checks (Python 3.12 or 3.13, 64-bit; 3.13 tested)"
    $script:Step = "1/6 Python 3.12 or 3.13 (64-bit)"
    if (-not $script:Executable) {
        # 0.91.61: no suitable Python - install Python 3.13 for this user only (no administrator rights): the installer
        # lying next to this file (python-3.13*-amd64.exe, for a computer without internet) or downloaded from
        # python.org; it must carry a valid signature of the Python Software Foundation
        $installer = Get-ChildItem -File -Path $PSScriptRoot -Filter "python-3.13*-amd64.exe" -ErrorAction SilentlyContinue |
            Sort-Object Name -Descending | Select-Object -First 1
        if ($installer) {
            $installer = $installer.FullName
            Write-Host "[setup] No Python 3.12 or 3.13: installing Python from $installer"
        } else {
            $url = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-amd64.exe"
            $installer = Join-Path $env:TEMP "python-$PythonVersion-amd64.exe"
            Write-Host "[setup] No Python 3.12 or 3.13: downloading Python $PythonVersion (about 30 MB) from $url"
            try {
                [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
                $progress = $ProgressPreference
                $ProgressPreference = "SilentlyContinue"
                Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing
                $ProgressPreference = $progress
            } catch {
                Stop-WithError "Cannot download Python ($($_.Exception.Message)). Download python-$PythonVersion-amd64.exe from https://www.python.org/downloads/windows/ by hand and put it next to setup.ps1, or install it"
            }
        }
        $signature = Get-AuthenticodeSignature $installer
        if ($signature.Status -ne "Valid" -or $signature.SignerCertificate.Subject -notmatch "Python Software Foundation") {
            Stop-WithError "The Python installer $installer has no valid signature of the Python Software Foundation ($($signature.Status)); delete it and run again"
        }
        Write-Host "[setup] Installing Python for this user (a minute or two; no administrator rights needed)"
        $target = Join-Path $env:LOCALAPPDATA "Programs\Python\Python313"
        $process = Start-Process -FilePath $installer -Wait -PassThru -ArgumentList @(
            "/quiet", "InstallAllUsers=0", "PrependPath=1", "Include_test=0", "Include_launcher=0", "Shortcuts=0",
            "TargetDir=`"$target`"")
        if ($process.ExitCode -ne 0) {
            Stop-WithError "The Python installer stopped with code $($process.ExitCode). Install Python 3.13 (64-bit) from https://www.python.org/downloads/windows/ by hand, ticking 'Add python.exe to PATH', then run this file again"
        }
        $candidates = @(,@((Join-Path $target "python.exe")))
        Find-Python
        if (-not $script:Executable) {
            Stop-WithError "Python was installed to $target but does not start. Install Python 3.13 (64-bit) from https://www.python.org/downloads/windows/ by hand, then run this file again"
        }
    }
    Run-Python @("-c", "import sys; print('[setup] Python', sys.version.split()[0], sys.executable)")
    Write-Host "[setup] 2/6 Environment"
    $script:Step = "2/6 environment .venv"
    if (-not $SkipVenv) {
        if (-not (Test-Path ".venv")) { Run-Python @("-m", "venv", ".venv") }
        $script:Executable = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
        $script:Prefix = @()
    }
    Write-Host "[setup] 3/6 Windows x64 lock"
    $script:Step = "3/6 Windows x64 (64-bit Python needed)"
    Run-Python @("-c", "import platform,struct,sys; sys.exit(0 if platform.system() == 'Windows' and platform.machine().lower() in ('amd64','x86_64') and struct.calcsize('P') == 8 else 1)")
    $lock = "requirements-lock-win-amd64.txt"
    # 0.91.58: the hashed lock holds the wheels of Python 3.13; another version takes requirements.txt (same versions)
    & $script:Executable @script:Prefix -c "import sys; sys.exit(0 if sys.version_info[:2] == (3,13) else 1)" 2>$null | Out-Null
    $tested = ($LASTEXITCODE -eq 0)
    Write-Host "[setup] 4/6 Dependencies"
    $script:Step = "4/6 dependencies (pip; internet needed)"
    if ($NoDownload) {
        if (-not $OfflineBundle) { Stop-WithError "NoDownload requires OfflineBundle DIRECTORY" }
        Run-Python @("-m", "pip", "install", "--no-index", "--find-links", $OfflineBundle, "--require-hashes", "-r", $lock)
    } elseif ($tested) {
        if ($OfflineBundle) { Run-Python @("-m", "pip", "download", "--only-binary=:all:", "--require-hashes", "-r", $lock, "-d", $OfflineBundle) }
        Pip-Install @("--require-hashes", "-r", $lock)
    } else {
        Write-Host "[setup] Python is not 3.13: the libraries of requirements.txt (the same versions, without the hashes)"
        Pip-Install @("--only-binary=:all:", "-r", "requirements.txt")
    }
    Write-Host "[setup] 5/6 Teaching assets are bundled"
    Write-Host "[setup] 6/6 Verification"
    $script:Step = "6/6 verification (verify_install.py: see its [FAIL] line)"
    # 0.91.62: the lines of the verification are shown and logged even when its output is not caught by the transcript
    Remove-Item -ErrorAction SilentlyContinue (Join-Path $PSScriptRoot "verify-log.txt")
    & $script:Executable @script:Prefix "verify_install.py"
    $verified = $LASTEXITCODE
    $report = Join-Path $PSScriptRoot "verify-log.txt"
    if (Test-Path $report) { Get-Content $report | ForEach-Object { Write-Host "[verify] $_" } }
    if ($verified -ne 0) { Stop-WithError "Step '$script:Step' failed (code $verified): see the [verify] [FAIL] line above" }
    Run-Python @("-m", "pip", "freeze") | Out-File -Encoding ascii "requirements-frozen.txt"
    Write-Host "[setup] Ready. Open Launch-Windows.bat."
} catch {
    Write-Host ("[setup] FAIL: " + $_.Exception.Message)
    exit 1
} finally {
    Set-PSDebug -Off
    try { Stop-Transcript | Out-Null } catch {}
    [Console]::OutputEncoding = $oldEncoding
    $OutputEncoding = $oldOutput
    Set-Location $oldLocation
}
