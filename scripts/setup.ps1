param([string]$Python)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $root
if (-not $Python) {
    $candidates = @((Join-Path $root '.venv/Scripts/python.exe'))
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $candidates += (& py -3.12 -c 'import sys; print(sys.executable)' 2>$null)
    }
    foreach ($key in @('HKCU:\Software\Python\PythonCore\3.12\InstallPath', 'HKLM:\Software\Python\PythonCore\3.12\InstallPath')) {
        if (Test-Path $key) { $candidates += (Join-Path (Get-Item $key).GetValue('') 'python.exe') }
    }
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) {
            $version = & $candidate -c 'import sys; print("%s.%s" % sys.version_info[:2])'
            if ($LASTEXITCODE -eq 0 -and $version -eq '3.12') { $Python = $candidate; break }
        }
    }
}
if (-not $Python) { throw 'Install Python 3.12 from python.org, or supply -Python C:/path/to/python.exe.' }
$version = & $Python -c 'import sys; print("%s.%s" % sys.version_info[:2])'
if ($LASTEXITCODE -ne 0 -or $version -ne '3.12') { throw 'Setup requires Python 3.12.' }
$venv = Join-Path $root '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $venv)) {
    & $Python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the virtual environment.' }
}
& $venv -m pip install -r requirements-lock.txt --disable-pip-version-check
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& $venv -m pip install --no-deps -e . --disable-pip-version-check
if ($LASTEXITCODE -ne 0) { throw 'Package installation failed.' }
& $venv -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Installed dependencies are inconsistent.' }
New-Item -ItemType Directory -Force -Path local | Out-Null
$config = @{mcpServers = @{kselect = @{command = $venv; args = @('-m', 'cli_anything.kselect.server')}}}
$config | ConvertTo-Json -Depth 5 | Set-Content -Encoding utf8 local/mcp.json
& $venv -m cli_anything.kselect --json capabilities
if ($LASTEXITCODE -ne 0) { throw 'CLI verification failed.' }
Write-Host 'Setup complete. Merge local/mcp.json into your MCP client configuration and reconnect.'
