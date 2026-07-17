#!/bin/bash

# Backup script for database and uploads
# Usage: ./backup.sh

set -e

BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "📦 Starting backup process..."

# Backup PostgreSQL
echo "🗄️  Backing up database..."
docker compose exec -T postgres pg_dump -U postgres sris_db | gzip > "$BACKUP_DIR/database.sql.gz"
echo "✅ Database backup complete"

# Backup uploads
echo "📁 Backing up uploads..."
docker compose cp backend:/app/uploads "$BACKUP_DIR/uploads"
echo "✅ Uploads backup complete"

# Create backup manifest
cat > "$BACKUP_DIR/manifest.txt" << EOF
Backup Date: $(date)
Environment: ${ENVIRONMENT:-development}
Database: sris_db
Files: uploads/

Contents:
- database.sql.gz: PostgreSQL database dump
- uploads/: User uploaded files
EOF

echo ""
echo "✅ Backup completed successfully!"
echo "📂 Backup location: $BACKUP_DIR"
echo ""
echo "To restore:"
echo "  Database: gunzip -c database.sql.gz | docker compose exec -T postgres psql -U postgres sris_db"
echo "  Files: docker compose cp uploads backend:/app/uploads"
