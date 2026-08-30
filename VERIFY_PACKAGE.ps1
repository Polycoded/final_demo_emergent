$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

$required = @(
    "package.json",
    "package-lock.json",
    "index.html",
    "run-demo.bat",
    "src/App.jsx",
    "src/liveRuntime.js",
    "src/main.jsx",
    "src/styles.css",
    "public/feeds/feed-a-clear.mp4",
    "public/feeds/feed-b-degraded.mp4",
    "public/feeds/feed-c-temporal.mp4",
    "backend/pyproject.toml",
    "backend/app/main.py",
    "backend/app/v2_driver.py",
    "backend/app/v2_scheduler.py",
    "backend/models/yolox_tiny.onnx",
    "backend/assets/scenarios/feed-a-clear.avi",
    "backend/assets/scenarios/feed-b-degraded.avi",
    "backend/assets/scenarios/feed-c-temporal.avi",
    "backend/checkpoints/router-review1-v2.joblib",
    "evidence/reports/review1-results.json",
    "evidence/reports/provenance.json",
    "docs/FINAL_ELIMINATION_REVIEW.md",
    "PITCH.md"
)

$missing = $required | Where-Object { -not (Test-Path -LiteralPath (Join-Path $root $_)) }
if ($missing) { throw "Missing required files:`n$($missing -join "`n")" }

$expectedRouterHash = "A098669583C43B93796F0D0FED1D1581183BADA5C3852DEF14CBE74239DC8509"
$actualRouterHash = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $root "backend/checkpoints/router-review1-v2.joblib")).Hash
if ($actualRouterHash -ne $expectedRouterHash) { throw "Router checkpoint hash mismatch." }

$forbidden = Get-ChildItem -LiteralPath $root -Recurse -Force -File | Where-Object {
    $_.Name -match '\.(db|db-shm|db-wal|log|jsonl|pyc)$' -or
    $_.FullName -match '[\\/](node_modules|dist|__pycache__|\.pytest_cache|\.ruff_cache)[\\/]'
}
if ($forbidden) { throw "Generated or forbidden files found:`n$($forbidden.FullName -join "`n")" }

$fileCount = (Get-ChildItem -LiteralPath $root -Recurse -Force -File).Count
$size = [math]::Round(((Get-ChildItem -LiteralPath $root -Recurse -Force -File | Measure-Object Length -Sum).Sum / 1MB), 2)
Write-Host "PASS: final-round package is complete."
Write-Host "Files: $fileCount"
Write-Host "Size: $size MB"
Write-Host "Router SHA-256: $actualRouterHash"
