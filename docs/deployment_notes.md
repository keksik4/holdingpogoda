# Deployment Notes

Production deployment for **Pogoda w Łodzi** uses two Vercel projects:

- Frontend: Next.js project `pogoda-w-lodzi`
- Backend: FastAPI serverless project `pogoda-w-lodzi-api`

This split is more reliable for the current repository than forcing the full monorepo into one Vercel project. The frontend can move through Vercel previews independently, while the backend keeps a minimal public API contract.

## Production URLs

- Frontend: https://pogoda-w-lodzi.vercel.app
- Backend API: https://pogoda-w-lodzi-api.vercel.app

## Local Development

Backend:

```bat
cd C:\AI\welcome-to-airlines
run_backend_windows.bat
```

Frontend:

```bat
cd C:\AI\welcome-to-airlines
run_frontend_windows.bat
```

Local frontend environment:

```text
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## Vercel Environment Variables

Frontend project:

```text
NEXT_PUBLIC_API_BASE_URL=https://pogoda-w-lodzi-api.vercel.app
```

Backend project:

```text
APP_NAME=Pogoda w Łodzi
APP_ENV=vercel
DEMO_MODE=true
DATABASE_URL=sqlite:////tmp/pogoda-w-lodzi.db
DEFAULT_CITY=Lodz
DEFAULT_LATITUDE=51.7592
DEFAULT_LONGITUDE=19.4560
DEFAULT_TIMEZONE=Europe/Warsaw
MET_NO_USER_AGENT=pogoda-w-lodzi-vercel/0.1 contact@example.com
API_TIMEOUT_SECONDS=20
OPENWEATHER_API_KEY=
OPENMETEO_BASE_URL=https://api.open-meteo.com/v1/forecast
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
CORS_ORIGIN_REGEX=https://.*\.vercel\.app
```

The current deployments were created with these values. For future Vercel redeploys, store them in Vercel Project Settings or pass them again with the CLI.

## Backend Packaging

The deployment package in `backend_vercel/` contains:

- `api/index.py` as the Vercel Python entrypoint
- a copied `backend/` package with the minimal public API contract
- source data needed by the venue endpoints
- `requirements.txt` with only the dependencies needed by the public API

Before redeploying the backend after source changes, sync the backend package:

```powershell
cd C:\AI\welcome-to-airlines
Remove-Item -LiteralPath backend_vercel\backend -Recurse -Force
Copy-Item -Recurse -Path backend -Destination backend_vercel\backend
```

Then deploy:

```bat
cd C:\AI\welcome-to-airlines\backend_vercel
vercel.cmd deploy . --yes --prod
```

## CORS

The backend allows local development origins and Vercel domains through:

- exact local origins in `CORS_ORIGINS`
- Vercel preview/production domains through `CORS_ORIGIN_REGEX`

This is intentionally broad enough for Vercel preview deployments. For a locked production environment, replace the regex with exact production frontend domains.

## Data And Storage Limitations

The deployed backend is a proof-of-concept API. It uses bundled CSV/source data and deterministic calibrated attendance. SQLite is configured to `/tmp` for serverless compatibility, which means it is not durable across instances.

Current production limitations:

- weather cache is best-effort and not durable on Vercel
- raw provider payload storage is not durable on Vercel
- calibrated attendance is demo/estimated, not internal gate data
- Google Trends is a relative signal only where available
- venue images are served from frontend public assets

Before production use, move durable data to a hosted database and object storage, add scheduled weather refresh jobs, and replace calibrated demo attendance with internal attendance/ticketing data.
