#!/bin/bash

# Backup script for database and uploads
# Usage:
#   ./backup.sh
#   ./backup.sh --dry-run
#   ./backup.sh --verify backups/YYYYMMDD_HHMMSS

set -euo pipefail

usage() {
	cat <<'EOF'
Usage: ./backup.sh [options]

Options:
	--dry-run             Check backup prerequisites without writing a backup.
	--verify BACKUP_DIR   Validate backup archive, uploads directory, and manifest.
	-h, --help            Show this help.
EOF
}

verify_backup() {
	local backup_dir="$1"

	test -d "$backup_dir" || { echo "Backup directory not found: $backup_dir" >&2; exit 1; }
	test -s "$backup_dir/database.sql.gz" || { echo "Missing database.sql.gz" >&2; exit 1; }
	test -d "$backup_dir/uploads" || { echo "Missing uploads directory" >&2; exit 1; }
	test -s "$backup_dir/manifest.txt" || { echo "Missing manifest.txt" >&2; exit 1; }
	gzip -t "$backup_dir/database.sql.gz"

	echo "✅ Backup verification passed: $backup_dir"
}

DRY_RUN=0
VERIFY_DIR=""

while [[ $# -gt 0 ]]; do
	case "$1" in
		--dry-run)
			DRY_RUN=1
			shift
			;;
		--verify)
			VERIFY_DIR="${2:?Missing backup directory}"
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

if [[ -n "$VERIFY_DIR" ]]; then
	verify_backup "$VERIFY_DIR"
	exit 0
fi

echo "📦 Checking backup prerequisites..."
docker compose config >/tmp/sris-backup-compose-config.txt

if [[ "$DRY_RUN" == "1" ]]; then
	docker compose ps postgres >/dev/null || true
	docker compose ps backend >/dev/null || true
	echo "✅ Backup dry-run passed"
	exit 0
fi

docker compose ps postgres >/dev/null
docker compose ps backend >/dev/null

BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "📦 Starting backup process..."

echo "🗄️  Backing up database..."
docker compose exec -T postgres pg_dump -U "${POSTGRES_USER:-postgres}" sris_db | gzip > "$BACKUP_DIR/database.sql.gz"
echo "✅ Database backup complete"

echo "📁 Backing up uploads..."
docker compose cp backend:/app/uploads "$BACKUP_DIR/uploads"
echo "✅ Uploads backup complete"

cat > "$BACKUP_DIR/manifest.txt" << EOF
Backup Date: $(date)
Environment: ${ENVIRONMENT:-development}
Database: sris_db
Files: uploads/

Contents:
- database.sql.gz: PostgreSQL database dump
- uploads/: User uploaded files
EOF

verify_backup "$BACKUP_DIR"

echo ""
echo "✅ Backup completed successfully!"
echo "📂 Backup location: $BACKUP_DIR"
echo ""
echo "To restore into a disposable environment first:"
echo "  Database: gunzip -c database.sql.gz | docker compose exec -T postgres psql -U \${POSTGRES_USER:-postgres} sris_db"
echo "  Files: docker compose cp uploads backend:/app/uploads"
