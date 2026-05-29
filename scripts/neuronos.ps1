param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]] $Command
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$env:PYTHONPATH = Join-Path $Root "backend"
if (-not $env:NEURONOS_DATA_DIR) {
  $env:NEURONOS_DATA_DIR = "D:\NeuronOS\data"
}
if (-not $env:OLLAMA_MODELS) {
  $env:OLLAMA_MODELS = "D:\Ollama\models"
}
if (-not $env:OLLAMA_MODEL) {
  $env:OLLAMA_MODEL = "gemma3:1b"
}
if (-not $env:OLLAMA_FALLBACK_MODEL) {
  $env:OLLAMA_FALLBACK_MODEL = "gemma4:e2b"
}
if (-not $env:HF_HOME) {
  $env:HF_HOME = "D:\NeuronOS\hf-cache"
}
if (-not $env:NEURONOS_WHISPER_MODEL) {
  $env:NEURONOS_WHISPER_MODEL = "tiny.en"
}
if (-not $env:NEURONOS_WHISPER_BEAM_SIZE) {
  $env:NEURONOS_WHISPER_BEAM_SIZE = "3"
}
New-Item -ItemType Directory -Force -Path $env:NEURONOS_DATA_DIR | Out-Null
New-Item -ItemType Directory -Force -Path $env:OLLAMA_MODELS | Out-Null
New-Item -ItemType Directory -Force -Path $env:HF_HOME | Out-Null

if ($Command.Count -gt 0) {
  uv run --extra dev --extra voice python -m neuronos.cli @Command
  exit $LASTEXITCODE
}

$backend = Start-Process -FilePath "uv" `
  -ArgumentList @("run", "--extra", "dev", "--extra", "voice", "uvicorn", "neuronos.main:app", "--app-dir", "backend", "--host", "127.0.0.1", "--port", "8000") `
  -WorkingDirectory $Root `
  -WindowStyle Hidden `
  -PassThru

try {
  $ready = $false
  foreach ($attempt in 1..20) {
    try {
      $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" -TimeoutSec 1
      if ($health.status -eq "ok") {
        $ready = $true
        break
      }
    } catch {
      Start-Sleep -Milliseconds 500
    }
  }
  if (-not $ready) {
    throw "Backend did not become ready on http://127.0.0.1:8000."
  }

  if (Get-Command cargo -ErrorAction SilentlyContinue) {
    npm run tauri dev
  } else {
    Write-Host "Rust/Cargo is not installed, so opening the local assistant dev shell instead."
    npm run dev -- --host 127.0.0.1 --port 1420 --strictPort
  }
}
finally {
  Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
}
