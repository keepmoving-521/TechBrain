param(
    [switch]$BackendOnly,
    [switch]$FrontendOnly
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")

function Invoke-BackendChecks {
    Write-Host "==> Backend: ruff check"
    Push-Location (Join-Path $Root "backend")
    try {
        python -m ruff check .

        Write-Host "==> Backend: ruff format --check"
        python -m ruff format --check .

        Write-Host "==> Backend: pytest with coverage"
        python -m pytest --cov=techbrain --cov-report=term-missing
    }
    finally {
        Pop-Location
    }
}

function Invoke-FrontendChecks {
    Write-Host "==> Frontend: pnpm check"
    Push-Location (Join-Path $Root "frontend")
    try {
        pnpm check
    }
    finally {
        Pop-Location
    }
}

if (-not $FrontendOnly) {
    Invoke-BackendChecks
}

if (-not $BackendOnly) {
    Invoke-FrontendChecks
}

Write-Host "All quality checks passed."
