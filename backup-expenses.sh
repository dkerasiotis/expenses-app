#!/bin/bash
set -e

DB_PATH="/home/dimitris/expenses-app/data/expenses.db"
BACKUP_DIR="/home/dimitris/expenses-app/data/backups"
REMOTE_USER="dimitris"
REMOTE_HOST="192.168.2.108"
REMOTE_DIR="/criticaldata/backups/expenses"
RETENTION_DAYS=30
DATE=$(date +%Y-%m-%d)
BACKUP_FILE="${BACKUP_DIR}/expenses-${DATE}.db"

mkdir -p "${BACKUP_DIR}"

# Safe hot backup (δεν χρειάζεται να σταματήσει το container)
sqlite3 "${DB_PATH}" ".backup '${BACKUP_FILE}'"
echo "[$(date)] Backup created: ${BACKUP_FILE}"

# Αντιγραφή στο παλιό μηχάνημα
rsync -az --remove-source-files "${BACKUP_FILE}" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/"
echo "[$(date)] Synced to ${REMOTE_HOST}:${REMOTE_DIR}"

# Καθαρισμός παλιών backups στο παλιό μηχάνημα (>30 ημέρες)
ssh "${REMOTE_USER}@${REMOTE_HOST}" "find ${REMOTE_DIR} -name 'expenses-*.db' -mtime +${RETENTION_DAYS} -delete"
echo "[$(date)] Cleanup complete (retention: ${RETENTION_DAYS} days)"
