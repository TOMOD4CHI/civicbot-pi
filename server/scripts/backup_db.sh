#!/usr/bin/env bash
# =============================================================
#  Pothole Pi - back up the detections database and photos.
#     bash server/scripts/backup_db.sh                -> server/backups/
#     bash server/scripts/backup_db.sh /media/usb     -> other folder
#  Safe while the server is running (uses SQLite's online backup).
# =============================================================
set -euo pipefail
SERVER_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${1:-$SERVER_DIR/backups}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="$DEST/potholepi-$STAMP"
mkdir -p "$OUT"

"$SERVER_DIR/.venv/bin/python" - "$SERVER_DIR/data/potholepi.db" "$OUT/potholepi.db" <<'EOF'
import sqlite3, sys
src, dst = sqlite3.connect(sys.argv[1]), sqlite3.connect(sys.argv[2])
src.backup(dst)
n = dst.execute("SELECT COUNT(*) FROM detections").fetchone()[0]
print(f"   {n} detections")
EOF
cp -r "$SERVER_DIR/data/images" "$OUT/" 2>/dev/null || true
tar -czf "$OUT.tar.gz" -C "$DEST" "potholepi-$STAMP" && rm -rf "$OUT"
echo "Backup: $OUT.tar.gz"
