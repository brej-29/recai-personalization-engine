param(
    [switch]$SkipTrain
)

Write-Host "[RUN_LOCAL] Starting local RecAI stack (Postgres + Redis + API)..." -ForegroundColor Cyan

# Detect docker compose vs docker-compose
$composeCmd = $null
try {
    docker compose version *> $null
    if ($LASTEXITCODE -eq 0) {
        $composeCmd = "docker compose"
    }
} catch {
    # Ignore, we'll try docker-compose next
}

if (-not $composeCmd) {
    try {
        docker-compose --version *> $null
        if ($LASTEXITCODE -eq 0) {
            $composeCmd = "docker-compose"
        }
    } catch {
        # ignore
    }
}

if (-not $composeCmd) {
    Write-Error "[RUN_LOCAL] Neither 'docker compose' nor 'docker-compose' is available. Install Docker Desktop and try again."
    exit 1
}

Write-Host "[RUN_LOCAL] Using '$composeCmd'"

# Ensure .env exists
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Write-Host "[RUN_LOCAL] .env not found, copying from .env.example"
        Copy-Item ".env.example" ".env"
    } else {
        Write-Error "[RUN_LOCAL] .env and .env.example are missing. Create a .env file first."
        exit 1
    }
}

Write-Host "[RUN_LOCAL] Bringing up Postgres + Redis..."
& $composeCmd up -d postgres redis

Write-Host "[RUN_LOCAL] Applying database migrations (alembic upgrade head)..." -ForegroundColor Yellow
try {
    alembic upgrade head
} catch {
    Write-Warning "[RUN_LOCAL] Alembic migrations failed. Check DATABASE_URL and Postgres status."
}

Write-Host "[RUN_LOCAL] Downloading MovieLens 1M dataset (if needed)..." -ForegroundColor Yellow
python scripts/download_movielens_1m.py

if (-not (Test-Path "data")) {
    New-Item -ItemType Directory -Path "data" | Out-Null
}

$seedMarker = "data/.seeded"
Write-Host "[RUN_LOCAL] Seeding database (idempotent via marker file)..." -ForegroundColor Yellow
if (-not (Test-Path $seedMarker)) {
    python scripts/seed_db.py
    New-Item -ItemType File -Path $seedMarker | Out-Null
    Write-Host "[RUN_LOCAL] Database seeded. Marker created at $seedMarker."
} else {
    Write-Host "[RUN_LOCAL] $seedMarker exists; skipping seed_db.py."
    Write-Host "[RUN_LOCAL] To re-seed, delete the marker and reset DB volumes (see context/RUN_LOCAL.md)."
}

if (-not $SkipTrain) {
    if (-not (Test-Path "artifacts")) {
        New-Item -ItemType Directory -Path "artifacts" | Out-Null
    }

    Write-Host "[RUN_LOCAL] Training content-based model (if needed)..." -ForegroundColor Yellow
    if (-not (Test-Path "artifacts/content_tfidf.pkl")) {
        try {
            python -m app.training.train --model content
            Write-Host "[RUN_LOCAL] Content-based model trained."
        } catch {
            Write-Warning "[RUN_LOCAL] Content model training failed; API will still work with popular strategy."
        }
    } else {
        Write-Host "[RUN_LOCAL] artifacts/content_tfidf.pkl exists; skipping content training."
    }

    Write-Host "[RUN_LOCAL] Training MF model (if needed)..." -ForegroundColor Yellow
    if (-not (Test-Path "artifacts/mf_als.pkl")) {
        try {
            python -m app.training.train --model mf
            Write-Host "[RUN_LOCAL] MF model trained."
        } catch {
            Write-Warning "[RUN_LOCAL] MF model training failed; API will still work with popular strategy."
        }
    } else {
        Write-Host "[RUN_LOCAL] artifacts/mf_als.pkl exists; skipping MF training."
    }
} else {
    Write-Host "[RUN_LOCAL] -SkipTrain provided; skipping model training." -ForegroundColor Yellow
}

$port = $env:PORT
if (-not $port) {
    $port = "8000"
}

Write-Host "[RUN_LOCAL] Starting API with Uvicorn on http://127.0.0.1:$port ..." -ForegroundColor Green
uvicorn app.main:app --reload --host 0.0.0.0 --port $port