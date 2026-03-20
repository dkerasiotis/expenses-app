# Οικιακά Έξοδα

Εφαρμογή διαχείρισης **εσόδων & εξόδων** νοικοκυριού, χτισμένη με Flask, SQLite και Docker.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Flask](https://img.shields.io/badge/Flask-3.0-green)
![Docker](https://img.shields.io/badge/Docker-Ready-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Χαρακτηριστικά

### Dashboard
- Συνολικά έξοδα και έσοδα (ολικά, ετήσια, μηνιαία)
- Top 8 κατηγορίες εξόδων ανά έτος
- Γραφήματα μηνιαίων τάσεων (Chart.js)
- Πρόσφατες συναλλαγές και εκκρεμείς πληρωμές

### Διαχείριση Εξόδων
- Προσθήκη / Επεξεργασία / Διαγραφή εξόδων
- Φιλτράρισμα ανά άτομο, κατηγορία, έτος, μήνα ή εύρος ημερομηνιών
- Σελιδοποίηση (50 εγγραφές/σελίδα)
- Σημείωση εξόδου ως "Εκκρεμές" (ακόμα δεν πληρώθηκε)
- Πεδίο σημειώσεων

### Διαχείριση Εσόδων
- Προσθήκη / Επεξεργασία / Διαγραφή εσόδων
- Φιλτράρισμα ανά κατηγορία, άτομο, έτος, μήνα ή εύρος ημερομηνιών
- Ξεχωριστές κατηγορίες εσόδων
- Σελιδοποίηση (50 εγγραφές/σελίδα)

### Κατηγορίες & Άτομα
- Διαχείριση κατηγοριών εξόδων και εσόδων (προσθήκη/μετονομασία/διαγραφή)
- Διαχείριση ατόμων (προσθήκη/μετονομασία/διαγραφή)
- Προστασία από διαγραφή κατηγοριών/ατόμων με συσχετισμένες εγγραφές

### 7 Αναφορές (Reports)
1. **Ισοζύγιο** — Μηνιαίο & ετήσιο balance εσόδων/εξόδων
2. **Μηνιαία Αναφορά** — Μηνιαία σύνολα και ανάλυση ανά κατηγορία
3. **Ετήσια Αναφορά** — Ετήσια σύνολα με ανάλυση κατηγοριών
4. **Ανά Κατηγορία** — Στατιστικά κατηγορίας (πλήθος, μέσος, min/max, τάσεις)
5. **Ανά Άτομο** — Ανάλυση εξόδων ανά άτομο με κατανομή κατηγοριών
6. **Τάσεις** — Συγκρίσεις μεταξύ ετών, top κατηγορίες, μηνιαίοι μέσοι όροι
7. **Σύγκριση Ετών** — Παράθεση δύο ετών ανά μήνα και κατηγορία

### API
- Token-based REST endpoint (`/api/pending`) για εκκρεμείς πληρωμές
- Επιστρέφει JSON με πλήθος, σύνολο και λίστα εκκρεμών

### Ασφάλεια
- Προστασία με κωδικό πρόσβασης
- Persistent sessions (30 ημέρες)
- Token-based API authentication

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Flask 3.0.3 (Python 3.12) |
| Database | SQLite |
| Server | Gunicorn (2 workers) |
| Frontend | Jinja2 + Bootstrap 5.3.2 |
| Charts | Chart.js |
| Icons | Bootstrap Icons |
| Container | Docker + Docker Compose |

---

## Εγκατάσταση

### Προαπαιτούμενα
- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/install/)

### Βήμα 1: Κλωνοποίηση

```bash
git clone https://github.com/dimitris-nik/expenses-app.git
cd expenses-app
```

### Βήμα 2: Ρύθμιση μεταβλητών περιβάλλοντος

```bash
cp .env.example .env
```

Επεξεργαστείτε το αρχείο `.env` και ορίστε τις τιμές σας:

```env
# Flask secret key - δημιουργήστε με: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=your-random-secret-key

# Κωδικός πρόσβασης εφαρμογής
APP_PASSWORD=your-strong-password

# API token για το /api/pending endpoint
API_TOKEN=your-random-api-token
```

### Βήμα 3: Εκκίνηση

```bash
docker compose up --build -d
```

Η εφαρμογή θα είναι διαθέσιμη στο: **http://localhost:5000**

---

## Εισαγωγή Δεδομένων από Excel (Προαιρετικό)

Αν έχετε ιστορικά δεδομένα σε μορφή Excel:

```bash
mkdir -p data
cp /path/to/exoda.xlsx data/exoda.xlsx
docker compose up --build -d
```

Το `init_db.py` θα ανιχνεύσει αυτόματα το αρχείο και θα εισάγει τα δεδομένα στη βάση.

Για εισαγωγή μετά την πρώτη εκκίνηση (μόνο αν η βάση είναι κενή):
```bash
docker compose exec expenses python init_db.py /data/exoda.xlsx
```

---

## Χρήσιμες Εντολές

```bash
# Προβολή logs
docker compose logs -f

# Σταμάτημα
docker compose down

# Επανεκκίνηση μετά από αλλαγές
docker compose up --build -d
```

---

## Τοπική Εκτέλεση (χωρίς Docker)

```bash
# Δημιουργία virtual environment
python3 -m venv venv
source venv/bin/activate

# Εγκατάσταση εξαρτήσεων
pip install -r requirements.txt

# Ρύθμιση μεταβλητών (προαιρετικό)
export SECRET_KEY="your-secret-key"
export APP_PASSWORD="your-password"
export DB_PATH="./expenses.db"

# Αρχικοποίηση βάσης
python init_db.py

# Εκκίνηση
python app.py
```

---

## Δομή Project

```
expenses-app/
├── app.py                  # Κύρια εφαρμογή Flask
├── init_db.py              # Αρχικοποίηση βάσης & εισαγωγή Excel
├── entrypoint.sh           # Docker entrypoint
├── Dockerfile              # Docker image configuration
├── docker-compose.yml      # Docker Compose configuration
├── requirements.txt        # Python dependencies
├── .env.example            # Παράδειγμα μεταβλητών περιβάλλοντος
├── templates/              # 20 Jinja2 HTML templates
│   ├── base.html           # Base layout με sidebar navigation
│   ├── login.html          # Σελίδα σύνδεσης
│   ├── index.html          # Dashboard
│   ├── expenses.html       # Λίστα εξόδων
│   ├── income.html         # Λίστα εσόδων
│   ├── categories.html     # Διαχείριση κατηγοριών εξόδων
│   ├── income_categories.html  # Διαχείριση κατηγοριών εσόδων
│   ├── persons.html        # Διαχείριση ατόμων
│   ├── pending_expenses.html   # Εκκρεμείς πληρωμές
│   └── report_*.html       # 7 αναφορές
└── static/
    └── favicon.svg         # Favicon
```

---

## Μεταβλητές Περιβάλλοντος

| Μεταβλητή | Περιγραφή | Προεπιλογή |
|-----------|-----------|-----------|
| `DB_PATH` | Διαδρομή βάσης SQLite | `/data/expenses.db` (Docker) / `./expenses.db` (local) |
| `SECRET_KEY` | Flask session secret key | `expenses-secret-2024` |
| `APP_PASSWORD` | Κωδικός σύνδεσης | `expenses2024` |
| `API_TOKEN` | Token για API endpoint | _(κενό)_ |

---

## API

### GET `/api/pending`

Επιστρέφει τα εκκρεμή έξοδα σε JSON.

**Παράμετροι:**
- `token` (required) — API token

**Παράδειγμα:**
```bash
curl "http://localhost:5000/api/pending?token=YOUR_API_TOKEN"
```

**Απάντηση:**
```json
{
  "count": 3,
  "total": 150.50,
  "items": [
    {
      "id": 1,
      "category": "Λογαριασμοί",
      "amount": 85.00,
      "date": "2024-01-15",
      "notes": "ΔΕΗ"
    }
  ]
}
```

---

## License

MIT
