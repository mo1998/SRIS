#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_E2E=0
RUN_COMPOSE=1
RUN_LOAD_HELP=1
RUN_MIGRATIONS=1
BACKEND_ENV="sris"

usage() {
  cat <<'EOF'
Usage: scripts/release_check.sh [options]

Runs the SRIS release readiness checks from the repository root.

Options:
  --with-e2e          Run Playwright E2E smoke tests. Requires browsers installed.
  --no-compose        Skip Docker Compose config validation.
  --no-load-help      Skip load-test CLI syntax/help validation.
  --no-migrations     Skip Alembic migration validation.
  --backend-env NAME  Conda environment for backend checks. Default: sris.
  -h, --help          Show this help.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-e2e)
      RUN_E2E=1
      shift
      ;;
    --no-compose)
      RUN_COMPOSE=0
      shift
      ;;
    --no-load-help)
      RUN_LOAD_HELP=0
      shift
      ;;
    --no-migrations)
      RUN_MIGRATIONS=0
      shift
      ;;
    --backend-env)
      BACKEND_ENV="${2:?Missing environment name}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

cd "$ROOT_DIR"

echo "==> Backend tests"
DEBUG=True conda run -n "$BACKEND_ENV" python -m pytest backend/tests -q

if [[ "$RUN_MIGRATIONS" == "1" ]]; then
  echo "==> Alembic migration chain"
  migration_db="/tmp/sris-migration-check-$$.db"
  rm -f "$migration_db"
  (
    cd backend
    DEBUG=True \
      SECRET_KEY="test-secret-key-for-migration-check" \
      DATABASE_URL="sqlite:///$migration_db" \
      conda run -n "$BACKEND_ENV" python -m alembic upgrade head
  )
  rm -f "$migration_db"
fi

echo "==> Frontend unit tests"
npm --prefix frontend test -- --run

echo "==> Frontend production build"
npm --prefix frontend run build

if [[ "$RUN_LOAD_HELP" == "1" ]]; then
  echo "==> Load-test CLI syntax/help"
  python -m py_compile scripts/load_test.py
  python scripts/load_test.py --help >/tmp/sris-load-test-help.txt
fi

if [[ "$RUN_COMPOSE" == "1" ]]; then
  echo "==> Docker Compose config"
  docker compose config >/tmp/sris-compose-config.txt
  docker compose -f docker-compose.prod.yml config >/tmp/sris-compose-prod-config.txt
  ./backup.sh --dry-run
fi

if [[ "$RUN_E2E" == "1" ]]; then
  echo "==> Playwright release-candidate E2E smoke"
  npm --prefix frontend run test:e2e
else
  echo "==> Skipping Playwright E2E smoke (pass --with-e2e to enable)"
fi

echo "==> Release checks passed"
