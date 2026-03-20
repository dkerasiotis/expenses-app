#!/bin/sh
# entrypoint.sh - Εκτελείται κάθε φορά που ξεκινά το container

set -e

DB_PATH="${DB_PATH:-/data/expenses.db}"

# Αρχικοποίηση βάσης (αν δεν υπάρχει ή είναι κενή)
echo "==> Έλεγχος βάσης δεδομένων..."
python /app/init_db.py

# Εκκίνηση εφαρμογής με gunicorn
echo "==> Εκκίνηση εφαρμογής..."
exec gunicorn \
  --bind 0.0.0.0:5000 \
  --workers 2 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  app:app
