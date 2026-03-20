#!/bin/sh
# migrate_add_pending.sh
# Εκτελέστε αυτό το script αν έχετε ήδη τρέξει προηγούμενη έκδοση
# και θέλετε να προσθέσετε τη δυνατότητα εκκρεμών πληρωμών.
#
# Χρήση:
#   docker compose exec expenses sh /app/migrate_add_pending.sh
#   ή τοπικά: sqlite3 /path/to/expenses.db < migrate_add_pending.sql

echo "==> Προσθήκη στήλης is_pending στον πίνακα expenses..."
sqlite3 "${DB_PATH:-/data/expenses.db}" \
  "ALTER TABLE expenses ADD COLUMN is_pending INTEGER DEFAULT 0;" 2>/dev/null \
  && echo "    ✓ Επιτυχία!" \
  || echo "    ℹ️  Η στήλη υπάρχει ήδη (OK)"

echo "==> Επαλήθευση..."
sqlite3 "${DB_PATH:-/data/expenses.db}" \
  "SELECT COUNT(*) || ' εγγραφές, ' || SUM(is_pending) || ' εκκρεμείς' FROM expenses;"
echo "==> Ολοκληρώθηκε."
