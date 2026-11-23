# One stage of the chained SYNAPSE (Brave Core) Windows build.
#
# Stage 1 downloads Brave Core and Chromium, applies the SYNAPSE branding and
# starts compiling. Every later stage resumes the same build folder (restored
# from the previous stage's artifact by the workflow) and compiles until its
# deadline. The workflow saves the folder again if the build is not finished.
#
# Writes "finished=true|false" to $env:GITHUB_OUTPUT.
param(
  [Parameter(Mandatory = $true)][string]$Root,          # e.g. C:\s  (short path: Windows path limits)
  [Parameter(Mandatory = $true)][datetime]$Deadline,    # stop compiling at this time (UTC)
  [switch]$Fresh
)
$ErrorActionPreference = 'Stop'
$BraveTag = (Get-Content "$PSScriptRoot\..\BRAVE_VERSION" -Raw).Trim()
$Src = Join-Path $Root 'src'
$Brave = Join-Path $Src 'brave'
$Config = 'Static'
$Out = Join-Path $Src "out\$Config"
$Target = 'mini_installer'

# Build settings. Static = optimised, not a component build, no Brave updater.
$Gn = @(
  'use_siso:false',             # classic ninja: safe to stop and resume
  'symbol_level:0', 'blink_symbol_level:0', 'v8_symbol_level:0',
  'dcheck_always_on:false',
  'treat_warnings_as_errors:false',
  # Brave services that need Brave's servers are left out of SYNAPSE.
  'enable_brave_rewards:false', 'enable_brave_wallet:false',
  'enable_brave_vpn_v1:false', 'enable_brave_vpn_v2:false',
  'enable_ai_chat:false', 'enable_brave_news:false', 'enable_tor:false'
)

function Log($m) { Write-Host "[$(Get-Date -Format HH:mm:ss)] $m" }
function Disk { Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Used -ne $null } | ForEach-Object { Log ("{0}: {1:N1} GB free" -f $_.Name, ($_.Free / 1GB)) } }

$env:DEPOT_TOOLS_WIN_TOOLCHAIN = '0'
$env:GYP_MSVS_VERSION = '2022'
$vs = & "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe" -latest -property installationPath
$env:vs2022_install = $vs
Log "Visual Studio: $vs"
Disk

if ($Fresh) {
  New-Item -ItemType Directory -Force $Src | Out-Null
  Log "Cloning brave-core $BraveTag"
  git clone --quiet --depth 1 --branch $BraveTag https://github.com/brave/brave-core.git $Brave
  if ($LASTEXITCODE) { throw "clone failed" }
  Push-Location $Brave
  Log "Downloading Chromium and dependencies (shallow)"
  pnpm run init --no-history --target_arch=x64
  if ($LASTEXITCODE) { throw "init failed" }
  Pop-Location
  Log "Applying SYNAPSE branding"
  python "$PSScriptRoot\..\branding\apply_branding.py" $Src
  if ($LASTEXITCODE) { throw "branding failed" }
  Disk
  $size = (Get-ChildItem $Root -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
  Log ("Source tree: {0:N1} GB" -f ($size / 1GB))
}

# Generate the build files (no-op when nothing changed) and compile until the deadline.
Push-Location $Brave
$gnArgs = $Gn | ForEach-Object { "--gn=$_" }
$buildArgs = @('run', 'build', $Config, '--target_arch=x64', "--target=$Target") + $gnArgs
Log ("pnpm " + ($buildArgs -join ' '))
$p = Start-Process -FilePath 'pnpm.cmd' -ArgumentList $buildArgs -NoNewWindow -PassThru
$null = $p.Handle  # keeps ExitCode readable after the process ends
$finished = $false
$stopped = $false
while (-not $p.HasExited) {
  if ((Get-Date).ToUniversalTime() -ge $Deadline.ToUniversalTime()) {
    Log "Deadline reached: stopping the compiler; the next stage resumes from here"
    taskkill /T /F /PID $p.Id | Out-Null
    Get-Process ninja, clang-cl, lld-link -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 10
    $stopped = $true
    break
  }
  Start-Sleep -Seconds 30
}
if (-not $stopped) {
  $p.WaitForExit()
  if ($p.ExitCode -ne 0) { throw "build failed with exit code $($p.ExitCode)" }
  if (-not (Test-Path (Join-Path $Out 'mini_installer.exe'))) { throw "build ended but mini_installer.exe is missing" }
  $finished = $true
}
Pop-Location
Disk
Log "finished=$finished"
"finished=$($finished.ToString().ToLower())" | Out-File -Append -Encoding utf8 $env:GITHUB_OUTPUT
