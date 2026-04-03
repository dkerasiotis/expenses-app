#!/bin/bash
# backup-expenses.sh — Ημερήσιο snapshot & backup βάσης εξόδων
# Εκτελείται μέσω cron

set -e

DATASET="criticaldata/expenses-app"
BACKUP_DIR="/criticaldata/backups/expenses"
RETENTION_DAYS=30
DATE=$(date +%Y-%m-%d)

# 1. ZFS Snapshot
SNAP="${DATASET}@daily-${DATE}"
if ! zfs list -t snapshot "${SNAP}" &>/dev/null; then
    zfs snapshot "${SNAP}"
    echo "[$(date)] Snapshot created: ${SNAP}"
fi

# 2. Backup αντίγραφο SQLite
mkdir -p "${BACKUP_DIR}"
cp /criticaldata/expenses-app/expenses.db "${BACKUP_DIR}/expenses-${DATE}.db"
echo "[$(date)] Backup saved: ${BACKUP_DIR}/expenses-${DATE}.db"

# 3. Καθαρισμός παλιών snapshots (>30 ημέρες)
zfs list -t snapshot -o name -H -r "${DATASET}" | while read snap; do
    snap_date=$(echo "$snap" | grep -oP '\d{4}-\d{2}-\d{2}' || true)
    if [ -n "$snap_date" ]; then
        snap_epoch=$(date -d "$snap_date" +%s 2>/dev/null || echo 0)
        cutoff_epoch=$(date -d "-${RETENTION_DAYS} days" +%s)
        if [ "$snap_epoch" -lt "$cutoff_epoch" ] && [ "$snap_epoch" -gt 0 ]; then
            zfs destroy "$snap"
            echo "[$(date)] Old snapshot removed: $snap"
        fi
    fi
done

# 4. Καθαρισμός παλιών backup αρχείων (>30 ημέρες)
find "${BACKUP_DIR}" -name "expenses-*.db" -mtime +${RETENTION_DAYS} -delete
echo "[$(date)] Cleanup complete"
