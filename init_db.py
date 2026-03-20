#!/usr/bin/env python3
"""
init_db.py — Αρχικοποίηση βάσης δεδομένων από Excel αρχείο.

Εκτελείται αυτόματα από entrypoint.sh ΜΟΝΟ αν η βάση είναι κενή.
Χειροκίνητη χρήση:
    python init_db.py /path/to/exoda.xlsx
"""
import sqlite3, sys, os, re

DB_PATH = os.environ.get('DB_PATH', '/data/expenses.db')

CAT_NORMALIZE = {
    'καφές':'Καφές', 'Ρούχα':'Ρούχα/Παπούτσια',
    'Μπουκάλες':'Μπουκάλες αερίου', 'Αγορές':'Αγορές Internet',
}

SKIP_EXACT = {
    'κενό','Σύνολα','Υπόλοιπο προηγούμενου','Υπόλοιπο Λογαριασμού',
    'Έσοδα','Σκλαβενίτης προπληρωμένη','Διάφορα','Έξοδοι',
    'Σύνολο','Διόρθωση Ισολογισμού','Αποταμίευση','nan','None','2.5','',
}
SKIP_CONTAINS = [
    'Λογαριασμός','Υπόλοιπ','Σκλαβ','Διόρθωση','Αποταμί',
    'Βιβλίο Δικτατορίας','Φαλτάιτς','Καλημεριάνοι','Έξοδα δουλ',
    'Κηροζίνη','Θες γάλα','Κούκος','Σοκολάτα','έξοδα Οχημάτων','Σύνολ',
]

def skip(name):
    n = str(name).strip()
    if not n or n in SKIP_EXACT: return True
    for s in SKIP_CONTAINS:
        if s in n: return True
    if re.match(r'^\d{2}/\d{4}', n): return True
    return False

def norm(name):
    return CAT_NORMALIZE.get(str(name).strip(), str(name).strip())

def is_income(name):
    n = str(name).strip()
    return 'Έσοδ' in n or 'έσοδ' in n

def create_schema(conn):
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS persons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS income_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER,
            category_id INTEGER NOT NULL,
            expense_date DATE NOT NULL,
            amount REAL NOT NULL,
            notes TEXT DEFAULT '',
            is_pending INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (person_id) REFERENCES persons(id),
            FOREIGN KEY (category_id) REFERENCES categories(id)
        );
        CREATE TABLE IF NOT EXISTS income (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER,
            person_id INTEGER,
            income_date DATE NOT NULL,
            amount REAL NOT NULL,
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES income_categories(id),
            FOREIGN KEY (person_id) REFERENCES persons(id)
        );
        CREATE INDEX IF NOT EXISTS idx_exp_date ON expenses(expense_date);
        CREATE INDEX IF NOT EXISTS idx_exp_cat  ON expenses(category_id);
        CREATE INDEX IF NOT EXISTS idx_inc_date ON income(income_date);
        CREATE INDEX IF NOT EXISTS idx_inc_cat  ON income(category_id);
    ''')

def import_excel(path, conn):
    try:
        import pandas as pd
    except ImportError:
        print("pandas not installed — skipping Excel import"); return 0, 0

    xl = pd.ExcelFile(path)
    all_cats = set()
    exp_records = []
    inc_records = []

    for sheet in xl.sheet_names:
        try:
            df = pd.read_excel(path, sheet_name=sheet, header=None)
        except Exception as e:
            print(f"  Skip '{sheet}': {e}"); continue
        if df.shape[0] < 2 or df.shape[1] < 3: continue
        n = df.shape[1]

        for ri in range(1, df.shape[0]):
            raw = str(df.iloc[ri, 0]).strip()
            if skip(raw): continue

            # Income row
            if is_income(raw):
                for ci in range(1, n-1):
                    dv = df.iloc[0, ci]
                    av = df.iloc[ri, ci]
                    if pd.isna(av): continue
                    try:
                        amt = float(av)
                        if amt <= 0: continue
                        dt = pd.to_datetime(dv)
                        if dt.year < 2000 or dt.year > 2035: continue
                        inc_records.append((dt.strftime('%Y-%m-%d'), amt))
                    except: continue
                continue

            cat = norm(raw)
            all_cats.add(cat)
            for ci in range(1, n-1):
                dv = df.iloc[0, ci]; av = df.iloc[ri, ci]
                if pd.isna(av): continue
                try:
                    amt = float(av)
                    if amt <= 0: continue
                    dt = pd.to_datetime(dv)
                    if dt.year < 2000 or dt.year > 2035: continue
                    exp_records.append((cat, dt.strftime('%Y-%m-%d'), amt))
                except: continue

    c = conn.cursor()
    # Insert expense categories
    for cat in sorted(all_cats):
        c.execute('INSERT OR IGNORE INTO categories(name) VALUES(?)', (cat,))
    # Insert default income category
    c.execute("INSERT OR IGNORE INTO income_categories(name) VALUES('Έσοδα')")
    conn.commit()

    cat_map = {r[1]:r[0] for r in c.execute('SELECT id,name FROM categories')}
    inc_cat_id = c.execute("SELECT id FROM income_categories WHERE name='Έσοδα'").fetchone()[0]

    exp_batch = [(None, cat_map[cat], ds, amt, '') for cat,ds,amt in exp_records if cat in cat_map]
    inc_batch = [(inc_cat_id, None, ds, amt, '') for ds,amt in inc_records]

    c.executemany('INSERT INTO expenses(person_id,category_id,expense_date,amount,notes)VALUES(?,?,?,?,?)', exp_batch)
    c.executemany('INSERT INTO income(category_id,person_id,income_date,amount,notes)VALUES(?,?,?,?,?)', inc_batch)
    conn.commit()
    return len(exp_batch), len(inc_batch)

def main():
    os.makedirs(os.path.dirname(DB_PATH) or '.', exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    create_schema(conn)

    n_exp = conn.execute('SELECT COUNT(*) FROM expenses').fetchone()[0]
    n_inc = conn.execute('SELECT COUNT(*) FROM income').fetchone()[0]
    if n_exp > 0 or n_inc > 0:
        print(f"Βάση υπάρχει ήδη: {n_exp} έξοδα, {n_inc} έσοδα. Παράλειψη.")
        conn.close(); return

    xlsx = None
    if len(sys.argv) > 1: xlsx = sys.argv[1]
    else:
        for c in ['/data/exoda.xlsx','/data/έξοδα.xlsx','/app/exoda.xlsx']:
            if os.path.exists(c): xlsx = c; break

    if xlsx and os.path.exists(xlsx):
        print(f"Εισαγωγή από: {xlsx}")
        ne, ni = import_excel(xlsx, conn)
        print(f"Ολοκληρώθηκε: {ne} έξοδα, {ni} έσοδα.")
    else:
        print("Δεν βρέθηκε Excel — κενή βάση δημιουργήθηκε.")
        print("Για εισαγωγή: python init_db.py /path/to/exoda.xlsx")
    conn.close()

if __name__ == '__main__':
    main()
