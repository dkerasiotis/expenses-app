from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session
from functools import wraps
import sqlite3
from datetime import datetime, date
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'expenses-secret-2024')
from datetime import timedelta
app.permanent_session_lifetime = timedelta(days=30)
DB_PATH = os.environ.get('DB_PATH', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'expenses.db'))

def run_migrations():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        initial_balance REAL NOT NULL DEFAULT 0
    )''')
    conn.execute("INSERT OR IGNORE INTO accounts(name, initial_balance) VALUES('Λογαριασμός 1', 0)")
    conn.execute("INSERT OR IGNORE INTO accounts(name, initial_balance) VALUES('Λογαριασμός 2', 0)")
    cols_exp = [r[1] for r in conn.execute("PRAGMA table_info(expenses)").fetchall()]
    if 'account_id' not in cols_exp:
        conn.execute('ALTER TABLE expenses ADD COLUMN account_id INTEGER REFERENCES accounts(id)')
    cols_inc = [r[1] for r in conn.execute("PRAGMA table_info(income)").fetchall()]
    if 'account_id' not in cols_inc:
        conn.execute('ALTER TABLE income ADD COLUMN account_id INTEGER REFERENCES accounts(id)')
    conn.commit(); conn.close()

run_migrations()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_persons():
    db = get_db(); rows = db.execute('SELECT * FROM persons ORDER BY name').fetchall(); db.close(); return rows

def get_categories():
    db = get_db(); rows = db.execute('SELECT * FROM categories ORDER BY name').fetchall(); db.close(); return rows

def get_income_categories():
    db = get_db(); rows = db.execute('SELECT * FROM income_categories ORDER BY name').fetchall(); db.close(); return rows

def get_accounts():
    db = get_db(); rows = db.execute('SELECT * FROM accounts ORDER BY name').fetchall(); db.close(); return rows

def get_years():
    db = get_db()
    rows = db.execute('''
        SELECT DISTINCT y FROM (
            SELECT strftime('%Y', expense_date) as y FROM expenses
            UNION
            SELECT strftime('%Y', income_date) as y FROM income
        ) ORDER BY y DESC
    ''').fetchall()
    db.close()
    return [r['y'] for r in rows]

MONTH_NAMES = ['','Ιανουάριος','Φεβρουάριος','Μάρτιος','Απρίλιος','Μάϊος','Ιούνιος',
               'Ιούλιος','Αύγουστος','Σεπτέμβριος','Οκτώβριος','Νοέμβριος','Δεκέμβριος']
MONTH_SHORT = ['','Ιαν','Φεβ','Μαρ','Απρ','Μαϊ','Ιουν','Ιουλ','Αυγ','Σεπ','Οκτ','Νοε','Δεκ']

# ─── AUTH ────────────────────────────────────────────────────────────────────

APP_PASSWORD = os.environ.get('APP_PASSWORD', 'expenses2024')

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated

@app.route('/login', methods=['GET','POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form.get('password') == APP_PASSWORD:
            session.permanent = True
            session['logged_in'] = True
            next_url = request.args.get('next') or url_for('index')
            return redirect(next_url)
        error = 'Λάθος κωδικός. Προσπαθήστε ξανά.'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ─── DASHBOARD ───────────────────────────────────────────────────────────────

@app.route('/')
@login_required
def index():
    db = get_db(); today = date.today(); yr = str(today.year); ym = today.strftime('%Y-%m')

    exp_all   = db.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE is_pending=0").fetchone()[0]
    exp_year  = db.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE is_pending=0 AND strftime('%Y',expense_date)=?", (yr,)).fetchone()[0]
    exp_month = db.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE is_pending=0 AND strftime('%Y-%m',expense_date)=?", (ym,)).fetchone()[0]

    inc_all   = db.execute('SELECT COALESCE(SUM(amount),0) FROM income').fetchone()[0]
    inc_year  = db.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE strftime('%Y',income_date)=?", (yr,)).fetchone()[0]
    inc_month = db.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE strftime('%Y-%m',income_date)=?", (ym,)).fetchone()[0]

    num_exp = db.execute('SELECT COUNT(*) FROM expenses').fetchone()[0]
    num_inc = db.execute('SELECT COUNT(*) FROM income').fetchone()[0]

    top_cats = db.execute("SELECT c.name, SUM(e.amount) as total FROM expenses e JOIN categories c ON e.category_id=c.id WHERE e.is_pending=0 AND strftime('%Y',e.expense_date)=? GROUP BY c.id ORDER BY total DESC LIMIT 8", (yr,)).fetchall()

    monthly_exp = db.execute("SELECT strftime('%m',expense_date) as m, SUM(amount) as total FROM expenses WHERE is_pending=0 AND strftime('%Y',expense_date)=? GROUP BY m ORDER BY m", (yr,)).fetchall()
    monthly_inc = db.execute("SELECT strftime('%m',income_date) as m, SUM(amount) as total FROM income WHERE strftime('%Y',income_date)=? GROUP BY m ORDER BY m", (yr,)).fetchall()

    recent_exp = db.execute("SELECT e.expense_date as dt,'expense' as type,c.name as label,p.name as person,e.amount,e.notes FROM expenses e JOIN categories c ON e.category_id=c.id LEFT JOIN persons p ON e.person_id=p.id WHERE e.is_pending=0 ORDER BY e.expense_date DESC, e.id DESC LIMIT 8").fetchall()
    pending = db.execute("SELECT e.id,e.expense_date,e.amount,e.notes,c.name as category,p.name as person FROM expenses e JOIN categories c ON e.category_id=c.id LEFT JOIN persons p ON e.person_id=p.id WHERE e.is_pending=1 ORDER BY e.expense_date ASC").fetchall()
    pending_total = sum(r['amount'] for r in pending)
    recent_inc = db.execute("SELECT i.income_date as dt,'income' as type,ic.name as label,p.name as person,i.amount,i.notes FROM income i JOIN income_categories ic ON i.category_id=ic.id LEFT JOIN persons p ON i.person_id=p.id ORDER BY i.income_date DESC, i.id DESC LIMIT 5").fetchall()

    accounts_raw = db.execute('SELECT * FROM accounts ORDER BY name').fetchall()
    account_balances = []
    for acc in accounts_raw:
        acc_inc = db.execute('SELECT COALESCE(SUM(amount),0) FROM income WHERE account_id=?', (acc['id'],)).fetchone()[0]
        acc_exp = db.execute('SELECT COALESCE(SUM(amount),0) FROM expenses WHERE account_id=? AND is_pending=0', (acc['id'],)).fetchone()[0]
        account_balances.append({'id': acc['id'], 'name': acc['name'], 'initial_balance': acc['initial_balance'], 'balance': acc['initial_balance'] + acc_inc - acc_exp})
    total_account_balance = sum(a['balance'] for a in account_balances)

    db.close()
    return render_template('index.html',
        exp_all=exp_all, exp_year=exp_year, exp_month=exp_month,
        inc_all=inc_all, inc_year=inc_year, inc_month=inc_month,
        num_exp=num_exp, num_inc=num_inc,
        top_cats=top_cats, monthly_exp=monthly_exp, monthly_inc=monthly_inc,
        recent_exp=recent_exp, recent_inc=recent_inc,
        pending=pending, pending_total=pending_total,
        account_balances=account_balances, total_account_balance=total_account_balance,
        now_str=today.isoformat(),
        current_year=today.year, month_short=MONTH_SHORT)

# ─── EXPENSES ────────────────────────────────────────────────────────────────

@app.route('/expenses')
@login_required
def expenses():
    db = get_db(); page = max(1, int(request.args.get('page',1))); per=50; off=(page-1)*per
    wp, params = [], []
    if request.args.get('person_id'):   wp.append('e.person_id=?');   params.append(request.args['person_id'])
    if request.args.get('category_id'): wp.append('e.category_id=?'); params.append(request.args['category_id'])
    if request.args.get('year'):  wp.append("strftime('%Y',e.expense_date)=?"); params.append(request.args['year'])
    if request.args.get('month'): wp.append("strftime('%m',e.expense_date)=?"); params.append(request.args['month'].zfill(2))
    if request.args.get('date_from'): wp.append('e.expense_date>=?'); params.append(request.args['date_from'])
    if request.args.get('date_to'):   wp.append('e.expense_date<=?'); params.append(request.args['date_to'])
    where = ('WHERE '+' AND '.join(wp)) if wp else ''
    total_count = db.execute(f'SELECT COUNT(*) FROM expenses e {where}', params).fetchone()[0]
    total_sum   = db.execute(f'SELECT COALESCE(SUM(e.amount),0) FROM expenses e {where}', params).fetchone()[0]
    rows = db.execute(f"SELECT e.id,e.expense_date,e.amount,e.notes,c.name as category,p.name as person FROM expenses e JOIN categories c ON e.category_id=c.id LEFT JOIN persons p ON e.person_id=p.id {where} ORDER BY e.expense_date DESC,e.id DESC LIMIT ? OFFSET ?", params+[per,off]).fetchall()
    db.close()
    return render_template('expenses.html', rows=rows, persons=get_persons(), categories=get_categories(), years=get_years(), page=page, per=per, total_count=total_count, total_sum=total_sum, total_pages=(total_count+per-1)//per, f=request.args, month_short=MONTH_SHORT[1:])

@app.route('/expenses/add', methods=['GET','POST'])
@login_required
def add_expense():
    if request.method=='POST':
        pid=request.form.get('person_id') or None; cid=request.form['category_id']
        edate=request.form['expense_date']; amt=float(request.form['amount']); notes=request.form.get('notes','')
        pending=1 if request.form.get('is_pending') else 0; aid=request.form.get('account_id') or None
        db=get_db(); db.execute('INSERT INTO expenses(person_id,category_id,expense_date,amount,notes,is_pending,account_id)VALUES(?,?,?,?,?,?,?)',(pid,cid,edate,amt,notes,pending,aid)); db.commit(); db.close()
        msg='Εκκρεμής πληρωμή καταχωρήθηκε! 🕐' if pending else 'Το έξοδο καταχωρήθηκε!'
        flash(msg,'warning' if pending else 'success'); return redirect(url_for('expenses'))
    return render_template('add_expense.html', persons=get_persons(), categories=get_categories(), accounts=get_accounts(), today=date.today().isoformat())

@app.route('/expenses/edit/<int:eid>', methods=['GET','POST'])
@login_required
def edit_expense(eid):
    db=get_db()
    if request.method=='POST':
        pid=request.form.get('person_id') or None; cid=request.form['category_id']
        edate=request.form['expense_date']; amt=float(request.form['amount']); notes=request.form.get('notes','')
        pending=1 if request.form.get('is_pending') else 0; aid=request.form.get('account_id') or None
        db.execute('UPDATE expenses SET person_id=?,category_id=?,expense_date=?,amount=?,notes=?,is_pending=?,account_id=? WHERE id=?',(pid,cid,edate,amt,notes,pending,aid,eid)); db.commit(); db.close()
        flash('Ενημερώθηκε!','success'); return redirect(url_for('expenses'))
    row=db.execute('SELECT e.*,c.name as cat_name,p.name as person_name FROM expenses e JOIN categories c ON e.category_id=c.id LEFT JOIN persons p ON e.person_id=p.id WHERE e.id=?',(eid,)).fetchone(); db.close()
    return render_template('edit_expense.html', row=row, persons=get_persons(), categories=get_categories(), accounts=get_accounts())

@app.route('/expenses/delete/<int:eid>', methods=['POST'])
@login_required
def delete_expense(eid):
    db=get_db(); db.execute('DELETE FROM expenses WHERE id=?',(eid,)); db.commit(); db.close()
    flash('Διαγράφηκε.','info'); return redirect(url_for('expenses'))

# ─── INCOME ──────────────────────────────────────────────────────────────────

@app.route('/income')
@login_required
def income():
    db = get_db(); page = max(1, int(request.args.get('page',1))); per=50; off=(page-1)*per
    wp, params = [], []
    if request.args.get('category_id'): wp.append('i.category_id=?'); params.append(request.args['category_id'])
    if request.args.get('person_id'):   wp.append('i.person_id=?');   params.append(request.args['person_id'])
    if request.args.get('year'):  wp.append("strftime('%Y',i.income_date)=?"); params.append(request.args['year'])
    if request.args.get('month'): wp.append("strftime('%m',i.income_date)=?"); params.append(request.args['month'].zfill(2))
    if request.args.get('date_from'): wp.append('i.income_date>=?'); params.append(request.args['date_from'])
    if request.args.get('date_to'):   wp.append('i.income_date<=?'); params.append(request.args['date_to'])
    where = ('WHERE '+' AND '.join(wp)) if wp else ''
    total_count = db.execute(f'SELECT COUNT(*) FROM income i {where}', params).fetchone()[0]
    total_sum   = db.execute(f'SELECT COALESCE(SUM(i.amount),0) FROM income i {where}', params).fetchone()[0]
    rows = db.execute(f"SELECT i.id,i.income_date,i.amount,i.notes,ic.name as category,p.name as person FROM income i JOIN income_categories ic ON i.category_id=ic.id LEFT JOIN persons p ON i.person_id=p.id {where} ORDER BY i.income_date DESC,i.id DESC LIMIT ? OFFSET ?", params+[per,off]).fetchall()
    db.close()
    return render_template('income.html', rows=rows, persons=get_persons(), income_categories=get_income_categories(), years=get_years(), page=page, per=per, total_count=total_count, total_sum=total_sum, total_pages=(total_count+per-1)//per, f=request.args, month_short=MONTH_SHORT[1:])

@app.route('/income/add', methods=['GET','POST'])
@login_required
def add_income():
    if request.method=='POST':
        pid=request.form.get('person_id') or None; cid=request.form['category_id']
        idate=request.form['income_date']; amt=float(request.form['amount']); notes=request.form.get('notes','')
        aid=request.form.get('account_id') or None
        db=get_db(); db.execute('INSERT INTO income(person_id,category_id,income_date,amount,notes,account_id)VALUES(?,?,?,?,?,?)',(pid,cid,idate,amt,notes,aid)); db.commit(); db.close()
        flash('Το έσοδο καταχωρήθηκε!','success'); return redirect(url_for('income'))
    return render_template('add_income.html', persons=get_persons(), income_categories=get_income_categories(), accounts=get_accounts(), today=date.today().isoformat())

@app.route('/income/edit/<int:iid>', methods=['GET','POST'])
@login_required
def edit_income(iid):
    db=get_db()
    if request.method=='POST':
        pid=request.form.get('person_id') or None; cid=request.form['category_id']
        idate=request.form['income_date']; amt=float(request.form['amount']); notes=request.form.get('notes','')
        aid=request.form.get('account_id') or None
        db.execute('UPDATE income SET person_id=?,category_id=?,income_date=?,amount=?,notes=?,account_id=? WHERE id=?',(pid,cid,idate,amt,notes,aid,iid)); db.commit(); db.close()
        flash('Ενημερώθηκε!','success'); return redirect(url_for('income'))
    row=db.execute('SELECT i.*,ic.name as cat_name,p.name as person_name FROM income i JOIN income_categories ic ON i.category_id=ic.id LEFT JOIN persons p ON i.person_id=p.id WHERE i.id=?',(iid,)).fetchone(); db.close()
    return render_template('edit_income.html', row=row, persons=get_persons(), income_categories=get_income_categories(), accounts=get_accounts())

@app.route('/income/delete/<int:iid>', methods=['POST'])
@login_required
def delete_income(iid):
    db=get_db(); db.execute('DELETE FROM income WHERE id=?',(iid,)); db.commit(); db.close()
    flash('Διαγράφηκε.','info'); return redirect(url_for('income'))

# ─── INCOME CATEGORIES ───────────────────────────────────────────────────────

@app.route('/income_categories')
@login_required
def income_categories():
    db=get_db()
    rows=db.execute('SELECT ic.id,ic.name,COUNT(i.id) as cnt,COALESCE(SUM(i.amount),0) as total,MAX(i.income_date) as last_date FROM income_categories ic LEFT JOIN income i ON ic.id=i.category_id GROUP BY ic.id ORDER BY total DESC').fetchall()
    db.close(); return render_template('income_categories.html', rows=rows)

@app.route('/income_categories/add', methods=['POST'])
@login_required
def add_income_category():
    name=request.form.get('name','').strip()
    if name:
        try: db=get_db(); db.execute('INSERT INTO income_categories(name)VALUES(?)',(name,)); db.commit(); db.close(); flash(f'Κατηγορία "{name}" προστέθηκε!','success')
        except: flash('Υπάρχει ήδη.','warning')
    return redirect(url_for('income_categories'))

@app.route('/income_categories/delete/<int:cid>', methods=['POST'])
@login_required
def delete_income_category(cid):
    db=get_db(); cnt=db.execute('SELECT COUNT(*) FROM income WHERE category_id=?',(cid,)).fetchone()[0]
    if cnt: flash(f'Δεν διαγράφεται — έχει {cnt} εγγραφές.','danger')
    else: db.execute('DELETE FROM income_categories WHERE id=?',(cid,)); db.commit(); flash('Διαγράφηκε.','info')
    db.close(); return redirect(url_for('income_categories'))

@app.route('/income_categories/rename/<int:cid>', methods=['POST'])
@login_required
def rename_income_category(cid):
    name=request.form.get('name','').strip()
    if name:
        try: db=get_db(); db.execute('UPDATE income_categories SET name=? WHERE id=?',(name,cid)); db.commit(); db.close(); flash('Ενημερώθηκε!','success')
        except: flash('Υπάρχει ήδη.','warning')
    return redirect(url_for('income_categories'))

# ─── PERSONS & EXPENSE CATEGORIES ────────────────────────────────────────────

@app.route('/persons')
@login_required
def persons():
    db=get_db()
    rows=db.execute('SELECT p.id,p.name,p.created_at,COUNT(e.id) as cnt,COALESCE(SUM(e.amount),0) as total FROM persons p LEFT JOIN expenses e ON p.id=e.person_id GROUP BY p.id ORDER BY p.name').fetchall()
    db.close(); return render_template('persons.html', rows=rows)

@app.route('/persons/add', methods=['POST'])
@login_required
def add_person():
    name=request.form.get('name','').strip()
    if name:
        try: db=get_db(); db.execute('INSERT INTO persons(name)VALUES(?)',(name,)); db.commit(); db.close(); flash(f'Άτομο "{name}" προστέθηκε!','success')
        except: flash('Υπάρχει ήδη.','warning')
    return redirect(url_for('persons'))

@app.route('/persons/delete/<int:pid>', methods=['POST'])
@login_required
def delete_person(pid):
    db=get_db(); cnt=db.execute('SELECT COUNT(*) FROM expenses WHERE person_id=?',(pid,)).fetchone()[0]
    if cnt: flash(f'Δεν διαγράφεται — έχει {cnt} έξοδα.','danger')
    else: db.execute('DELETE FROM persons WHERE id=?',(pid,)); db.commit(); flash('Διαγράφηκε.','info')
    db.close(); return redirect(url_for('persons'))

@app.route('/persons/rename/<int:pid>', methods=['POST'])
@login_required
def rename_person(pid):
    name=request.form.get('name','').strip()
    if name:
        try: db=get_db(); db.execute('UPDATE persons SET name=? WHERE id=?',(name,pid)); db.commit(); db.close(); flash('Ενημερώθηκε!','success')
        except: flash('Υπάρχει ήδη.','warning')
    return redirect(url_for('persons'))

@app.route('/categories')
@login_required
def categories():
    db=get_db()
    rows=db.execute('SELECT c.id,c.name,COUNT(e.id) as cnt,COALESCE(SUM(e.amount),0) as total,MAX(e.expense_date) as last_date FROM categories c LEFT JOIN expenses e ON c.id=e.category_id GROUP BY c.id ORDER BY total DESC').fetchall()
    db.close(); return render_template('categories.html', rows=rows)

@app.route('/categories/add', methods=['POST'])
@login_required
def add_category():
    name=request.form.get('name','').strip()
    if name:
        try: db=get_db(); db.execute('INSERT INTO categories(name)VALUES(?)',(name,)); db.commit(); db.close(); flash(f'Κατηγορία "{name}" προστέθηκε!','success')
        except: flash('Υπάρχει ήδη.','warning')
    return redirect(url_for('categories'))

@app.route('/categories/delete/<int:cid>', methods=['POST'])
@login_required
def delete_category(cid):
    db=get_db(); cnt=db.execute('SELECT COUNT(*) FROM expenses WHERE category_id=?',(cid,)).fetchone()[0]
    if cnt: flash(f'Δεν διαγράφεται — έχει {cnt} έξοδα.','danger')
    else: db.execute('DELETE FROM categories WHERE id=?',(cid,)); db.commit(); flash('Διαγράφηκε.','info')
    db.close(); return redirect(url_for('categories'))

@app.route('/categories/rename/<int:cid>', methods=['POST'])
@login_required
def rename_category(cid):
    name=request.form.get('name','').strip()
    if name:
        try: db=get_db(); db.execute('UPDATE categories SET name=? WHERE id=?',(name,cid)); db.commit(); db.close(); flash('Ενημερώθηκε!','success')
        except: flash('Υπάρχει ήδη.','warning')
    return redirect(url_for('categories'))

# ─── REPORTS ─────────────────────────────────────────────────────────────────

@app.route('/reports/monthly')
@login_required
def report_monthly():
    year=request.args.get('year',str(date.today().year)); db=get_db(); years=get_years()
    monthly_totals = db.execute("SELECT strftime('%m',expense_date) as m,SUM(amount) as total FROM expenses WHERE is_pending=0 AND strftime('%Y',expense_date)=? GROUP BY m ORDER BY m",(year,)).fetchall()
    monthly_income = db.execute("SELECT strftime('%m',income_date) as m,SUM(amount) as total FROM income WHERE strftime('%Y',income_date)=? GROUP BY m ORDER BY m",(year,)).fetchall()
    cat_monthly    = db.execute("SELECT strftime('%m',e.expense_date) as m,c.name as cat,SUM(e.amount) as total FROM expenses e JOIN categories c ON e.category_id=c.id WHERE e.is_pending=0 AND strftime('%Y',e.expense_date)=? GROUP BY m,c.id ORDER BY m,total DESC",(year,)).fetchall()
    db.close()
    return render_template('report_monthly.html', year=year, years=years, monthly_totals=monthly_totals, monthly_income=monthly_income, cat_monthly=cat_monthly, month_names=MONTH_NAMES, month_short=MONTH_SHORT)

@app.route('/reports/annual')
@login_required
def report_annual():
    db=get_db()
    annual_totals  = db.execute("SELECT strftime('%Y',expense_date) as y,SUM(amount) as total,COUNT(*) as cnt FROM expenses WHERE is_pending=0 GROUP BY y ORDER BY y").fetchall()
    annual_income  = db.execute("SELECT strftime('%Y',income_date) as y,SUM(amount) as total FROM income GROUP BY y ORDER BY y").fetchall()
    annual_by_cat  = db.execute("SELECT strftime('%Y',e.expense_date) as y,c.name,SUM(e.amount) as total FROM expenses e JOIN categories c ON e.category_id=c.id WHERE e.is_pending=0 GROUP BY y,c.id ORDER BY y,total DESC").fetchall()
    db.close()
    return render_template('report_annual.html', annual_totals=annual_totals, annual_income=annual_income, annual_by_cat=annual_by_cat)

@app.route('/reports/category')
@login_required
def report_category():
    db=get_db(); cat_id=request.args.get('category_id',''); year=request.args.get('year','')
    wp,params=[],[]
    if cat_id: wp.append('e.category_id=?'); params.append(cat_id)
    if year:   wp.append("strftime('%Y',e.expense_date)=?"); params.append(year)
    where=('WHERE '+' AND '.join(wp)) if wp else ''
    cat_totals=db.execute(f'SELECT c.id,c.name,SUM(e.amount) as total,COUNT(e.id) as cnt,AVG(e.amount) as avg,MIN(e.amount) as min_a,MAX(e.amount) as max_a,MIN(e.expense_date) as first_d,MAX(e.expense_date) as last_d FROM expenses e JOIN categories c ON e.category_id=c.id {where} GROUP BY c.id ORDER BY total DESC',params).fetchall()
    trend=[]
    if cat_id: trend=db.execute("SELECT strftime('%Y-%m',expense_date) as ym,SUM(amount) as total FROM expenses WHERE category_id=? GROUP BY ym ORDER BY ym",(cat_id,)).fetchall()
    db.close()
    return render_template('report_category.html', cat_totals=cat_totals, categories=get_categories(), years=get_years(), trend=trend, sel_category_id=cat_id, sel_year=year)

@app.route('/reports/person')
@login_required
def report_person():
    db=get_db(); person_id=request.args.get('person_id',''); year=request.args.get('year','')
    wp,params=[],[]
    if person_id: wp.append('e.person_id=?'); params.append(person_id)
    if year:      wp.append("strftime('%Y',e.expense_date)=?"); params.append(year)
    where=('WHERE '+' AND '.join(wp)) if wp else ''
    person_totals=db.execute(f'SELECT p.id,p.name,SUM(e.amount) as total,COUNT(e.id) as cnt,AVG(e.amount) as avg FROM expenses e JOIN persons p ON e.person_id=p.id {where} GROUP BY p.id ORDER BY total DESC',params).fetchall()
    cat_breakdown=[]
    if person_id: cat_breakdown=db.execute('SELECT c.name,SUM(e.amount) as total,COUNT(*) as cnt FROM expenses e JOIN categories c ON e.category_id=c.id WHERE e.person_id=? GROUP BY c.id ORDER BY total DESC',(person_id,)).fetchall()
    monthly_trend=[]
    if person_id: monthly_trend=db.execute("SELECT strftime('%Y-%m',expense_date) as ym,SUM(amount) as total FROM expenses WHERE person_id=? GROUP BY ym ORDER BY ym",(person_id,)).fetchall()
    db.close()
    return render_template('report_person.html', person_totals=person_totals, persons=get_persons(), years=get_years(), cat_breakdown=cat_breakdown, monthly_trend=monthly_trend, sel_person_id=person_id, sel_year=year)

@app.route('/reports/trends')
@login_required
def report_trends():
    db=get_db()
    yoy       = db.execute("SELECT strftime('%Y',expense_date) as y,strftime('%m',expense_date) as m,SUM(amount) as total FROM expenses WHERE is_pending=0 GROUP BY y,m ORDER BY y,m").fetchall()
    yoy_inc   = db.execute("SELECT strftime('%Y',income_date) as y,strftime('%m',income_date) as m,SUM(amount) as total FROM income GROUP BY y,m ORDER BY y,m").fetchall()
    top_cats  = db.execute('SELECT c.name,SUM(e.amount) as total,COUNT(e.id) as cnt FROM expenses e JOIN categories c ON e.category_id=c.id GROUP BY c.id ORDER BY total DESC LIMIT 10').fetchall()
    avg_monthly = db.execute("SELECT y,AVG(monthly) as avg_m,MIN(monthly) as min_m,MAX(monthly) as max_m FROM (SELECT strftime('%Y',expense_date) as y,strftime('%m',expense_date) as m,SUM(amount) as monthly FROM expenses GROUP BY y,m) GROUP BY y ORDER BY y").fetchall()
    big_days  = db.execute('SELECT expense_date,SUM(amount) as total,COUNT(*) as cnt FROM expenses GROUP BY expense_date ORDER BY total DESC LIMIT 10').fetchall()
    all_years = get_years()
    cat_growth=[]
    if len(all_years)>=2:
        yf=all_years[-1]; yl=all_years[0]
        cat_growth=db.execute("SELECT c.name,SUM(CASE WHEN strftime('%Y',e.expense_date)=? THEN e.amount ELSE 0 END) as first_y,SUM(CASE WHEN strftime('%Y',e.expense_date)=? THEN e.amount ELSE 0 END) as last_y FROM expenses e JOIN categories c ON e.category_id=c.id GROUP BY c.id HAVING first_y>0 AND last_y>0 ORDER BY last_y DESC LIMIT 12",(yf,yl)).fetchall()
    db.close()
    return render_template('report_trends.html', yoy=yoy, yoy_inc=yoy_inc, top_cats=top_cats, avg_monthly=avg_monthly, big_days=big_days, cat_growth=cat_growth, all_years=all_years, month_short=MONTH_SHORT)

@app.route('/reports/comparison')
@login_required
def report_comparison():
    db=get_db(); years=get_years(); today=date.today()
    year1=request.args.get('year1', str(today.year-1) if len(years)>1 else years[-1] if years else str(today.year-1))
    year2=request.args.get('year2', str(today.year))
    def ydata(y):   return db.execute("SELECT c.name,SUM(e.amount) as total FROM expenses e JOIN categories c ON e.category_id=c.id WHERE strftime('%Y',e.expense_date)=? GROUP BY c.id ORDER BY total DESC",(y,)).fetchall()
    def ymonth(y):  return db.execute("SELECT strftime('%m',expense_date) as m,SUM(amount) as total FROM expenses WHERE is_pending=0 AND strftime('%Y',expense_date)=? GROUP BY m ORDER BY m",(y,)).fetchall()
    def yinc(y):    return db.execute("SELECT strftime('%m',income_date) as m,SUM(amount) as total FROM income WHERE strftime('%Y',income_date)=? GROUP BY m ORDER BY m",(y,)).fetchall()
    d1=ydata(year1); d2=ydata(year2); m1=ymonth(year1); m2=ymonth(year2); i1=yinc(year1); i2=yinc(year2)
    total1=sum(r['total'] for r in d1); total2=sum(r['total'] for r in d2)
    tinc1=db.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE strftime('%Y',income_date)=?",(year1,)).fetchone()[0]
    tinc2=db.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE strftime('%Y',income_date)=?",(year2,)).fetchone()[0]
    cats1={r['name']:r['total'] for r in d1}; cats2={r['name']:r['total'] for r in d2}
    all_cats=sorted(set(list(cats1.keys())+list(cats2.keys())))
    db.close()
    return render_template('report_comparison.html', year1=year1, year2=year2, years=years, d1=d1, d2=d2, m1=m1, m2=m2, i1=i1, i2=i2, total1=total1, total2=total2, tinc1=tinc1, tinc2=tinc2, cats1=cats1, cats2=cats2, all_cats=all_cats, month_short=MONTH_SHORT)

@app.route('/reports/balance')
@login_required
def report_balance():
    db=get_db(); years=get_years()
    year=request.args.get('year', str(date.today().year))
    monthly_exp = db.execute("SELECT strftime('%m',expense_date) as m,SUM(amount) as total FROM expenses WHERE is_pending=0 AND strftime('%Y',expense_date)=? GROUP BY m ORDER BY m",(year,)).fetchall()
    monthly_inc = db.execute("SELECT strftime('%m',income_date) as m,SUM(amount) as total FROM income WHERE strftime('%Y',income_date)=? GROUP BY m ORDER BY m",(year,)).fetchall()
    annual_bal  = db.execute("""
        SELECT y,
               COALESCE(inc,0) as income,
               COALESCE(exp,0) as expenses,
               COALESCE(inc,0)-COALESCE(exp,0) as balance
        FROM (
            SELECT strftime('%Y',income_date) as y, SUM(amount) as inc FROM income GROUP BY y
        ) LEFT JOIN (
            SELECT strftime('%Y',expense_date) as y2, SUM(amount) as exp FROM expenses GROUP BY y2
        ) ON y=y2
        UNION
        SELECT y2 as y,
               COALESCE(inc,0),
               COALESCE(exp,0),
               COALESCE(inc,0)-COALESCE(exp,0)
        FROM (
            SELECT strftime('%Y',expense_date) as y2, SUM(amount) as exp FROM expenses GROUP BY y2
        ) LEFT JOIN (
            SELECT strftime('%Y',income_date) as y, SUM(amount) as inc FROM income GROUP BY y
        ) ON y2=y
        WHERE y IS NULL
        ORDER BY y
    """).fetchall()
    db.close()
    return render_template('report_balance.html', year=year, years=years, monthly_exp=monthly_exp, monthly_inc=monthly_inc, annual_bal=annual_bal, month_names=MONTH_NAMES, month_short=MONTH_SHORT)

# JSON serialization fix
import json as _json
from flask.json.provider import DefaultJSONProvider
class RowJSONProvider(DefaultJSONProvider):
    def default(self, o):
        if hasattr(o, 'keys'): return dict(o)
        return super().default(o)
app.json_provider_class = RowJSONProvider
app.json = RowJSONProvider(app)

@app.route('/favicon.svg')
def favicon():
    from flask import send_from_directory
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'favicon.svg', mimetype='image/svg+xml'
    )

if __name__=='__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)

# ─── API (token-based, για Homepage widget) ───────────────────────────────────

API_TOKEN = os.environ.get('API_TOKEN', '')

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.args.get('token') or request.headers.get('X-API-Token', '')
        if not API_TOKEN or token != API_TOKEN:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated

@app.route('/api/pending')
@token_required
def api_pending():
    db = get_db()
    rows = db.execute('''
        SELECT e.id, e.expense_date, e.amount, e.notes,
               c.name as category, p.name as person
        FROM expenses e
        JOIN categories c ON e.category_id = c.id
        LEFT JOIN persons p ON e.person_id = p.id
        WHERE e.is_pending = 1
        ORDER BY e.expense_date ASC
    ''').fetchall()
    total = sum(r['amount'] for r in rows)
    db.close()
    return jsonify({
        'count': len(rows),
        'total': round(total, 2),
        'items': [dict(r) for r in rows]
    })

# ─── PENDING EXPENSES ────────────────────────────────────────────────────────

@app.route('/expenses/complete/<int:eid>', methods=['POST'])
@login_required
def complete_expense(eid):
    db = get_db()
    db.execute('UPDATE expenses SET is_pending=0 WHERE id=?', (eid,))
    db.commit(); db.close()
    flash('Η πληρωμή ολοκληρώθηκε! ✓', 'success')
    return redirect(request.referrer or url_for('index'))

@app.route('/expenses/pending')
@login_required
def pending_expenses():
    db = get_db()
    rows = db.execute('''
        SELECT e.id, e.expense_date, e.amount, e.notes,
               c.name as category, p.name as person
        FROM expenses e
        JOIN categories c ON e.category_id = c.id
        LEFT JOIN persons p ON e.person_id = p.id
        WHERE e.is_pending = 1
        ORDER BY e.expense_date ASC
    ''').fetchall()
    total = sum(r['amount'] for r in rows)
    db.close()
    today_str = date.today().isoformat()
    return render_template('pending_expenses.html', rows=rows, total=total, now=today_str)

# ─── ACCOUNTS ────────────────────────────────────────────────────────────────

@app.route('/accounts/update/<int:aid>', methods=['POST'])
@login_required
def update_account(aid):
    name = request.form.get('name', '').strip()
    try:
        balance = float(request.form['initial_balance'])
    except (ValueError, KeyError):
        flash('Μη έγκυρο ποσό.', 'danger'); return redirect(url_for('index'))
    if not name:
        flash('Το όνομα δεν μπορεί να είναι κενό.', 'danger'); return redirect(url_for('index'))
    db = get_db(); db.execute('UPDATE accounts SET name=?, initial_balance=? WHERE id=?', (name, balance, aid)); db.commit(); db.close()
    flash('Λογαριασμός ενημερώθηκε!', 'success'); return redirect(url_for('index'))
