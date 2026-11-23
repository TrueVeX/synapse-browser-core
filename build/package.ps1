# Package a finished build: the installer, and a portable zip made from the
# installer's payload archive. Writes SHA-256 sums next to them.
param(
  [Parameter(Mandatory = $true)][string]$Root,
  [Parameter(Mandatory = $true)][string]$Dest
)
$ErrorActionPreference = 'Stop'
$Out = Join-Path $Root 'src\out\Static'
New-Item -ItemType Directory -Force $Dest | Out-Null

$setup = Join-Path $Out 'mini_installer.exe'
Copy-Item $setup (Join-Path $Dest 'SYNAPSE-Browser-Setup.exe')

# mini_installer packs the browser into chrome.7z (Chromium's name for it).
$payload = Get-ChildItem $Out -Filter '*.7z' | Where-Object { $_.Name -match '^(chrome|brave)\.7z$' } | Select-Object -First 1
if (-not $payload) { throw "installer payload (chrome.7z) not found in $Out" }
$tmp = Join-Path $env:RUNNER_TEMP 'portable'
Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
7z x -y "-o$tmp" $payload.FullName | Out-Null
$bin = Get-ChildItem $tmp -Directory | Select-Object -First 1   # Chrome-bin
Rename-Item $bin.FullName (Join-Path $tmp 'SYNAPSE')
Push-Location $tmp
7z a -tzip -mx=7 (Join-Path $Dest 'SYNAPSE-Browser-Windows-x64.zip') 'SYNAPSE' | Out-Null
Pop-Location

Get-ChildItem $Dest -File | ForEach-Object {
  $h = (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower()
  "$h  $($_.Name)" | Out-File -Append -Encoding ascii (Join-Path $Dest 'SHA256SUMS.txt')
  "{0}  {1:N1} MB  {2}" -f $_.Name, ($_.Length / 1MB), $h
}
