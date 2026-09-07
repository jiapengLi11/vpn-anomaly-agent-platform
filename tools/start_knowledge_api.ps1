param([string]$Python = "")
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path $PSScriptRoot -Parent
if (-not $Python) { $Python = Join-Path $projectRoot '.venv\Scripts\python.exe' }
if (-not (Test-Path -LiteralPath $Python)) { throw 'Create .venv and install backend/requirements.txt first, or pass -Python with an installed interpreter.' }
if (-not $env:DS_API_KEY -and -not $env:DEEPSEEK_API_KEY) {
    $secureKey = Read-Host 'DeepSeek API Key (hidden input)' -AsSecureString
    $env:DS_API_KEY = [System.Net.NetworkCredential]::new('', $secureKey).Password
}
if (-not $env:DS_MODEL -and -not $env:DEEPSEEK_MODEL) { $env:DS_MODEL = 'deepseek-v4-flash' }
if ((-not $env:DS_API_KEY -and -not $env:DEEPSEEK_API_KEY) -or (-not $env:DS_MODEL -and -not $env:DEEPSEEK_MODEL)) { throw 'API key and model ID are required.' }
& $Python -m uvicorn traffic_agent.api:app --app-dir (Join-Path $projectRoot 'backend') --host 127.0.0.1 --port 8090
