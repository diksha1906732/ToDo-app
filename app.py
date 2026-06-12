from functools import wraps

from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import os
from datetime import datetime, date
from email.mime.text import MIMEText
import smtplib
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
CORS(app)

# ─────────────────────────────────────────────
# Database Configuration
# Update these values to match your MySQL setup
# ─────────────────────────────────────────────
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': int(os.environ.get('DB_PORT', 3306)),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', 'Diksha@2006'),
    'database': os.environ.get('DB_NAME', 'todo_db'),
    'autocommit': True
}

MAIL_CONFIG = {
    'host': os.environ.get('SMTP_HOST', ''),
    'port': int(os.environ.get('SMTP_PORT', 587)),
    'user': os.environ.get('SMTP_USER', ''),
    'password': os.environ.get('SMTP_PASSWORD', ''),
    'from': os.environ.get('SMTP_FROM', os.environ.get('SMTP_USER', 'noreply@todo-app.local')),
    'use_tls': os.environ.get('SMTP_USE_TLS', '1').lower() not in ('0', 'false', 'no'),
}
ALERT_COOLDOWN_HOURS = int(os.environ.get('ALERT_COOLDOWN_HOURS', 24))


def get_connection():
    """Create and return a MySQL connection."""
    return mysql.connector.connect(**DB_CONFIG)


def init_db():
    """Initialize the database and create the todos table if it doesn't exist."""
    try:
        # Connect without specifying database first
        config = {k: v for k, v in DB_CONFIG.items() if k != 'database'}
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()

        # Create database
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['database']}`")
        cursor.execute(f"USE `{DB_CONFIG['database']}`")

        # Create todos table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS todos (
                id          INT AUTO_INCREMENT PRIMARY KEY,
                user_id     INT           NULL,
                order_index INT           DEFAULT 0,
                title       VARCHAR(255)  NOT NULL,
                description TEXT,
                category    VARCHAR(60)   DEFAULT 'general',
                priority    ENUM('low', 'medium', 'high') DEFAULT 'medium',
                due_date    DATE          NULL,
                completed   TINYINT(1)    DEFAULT 0,
                completed_at DATETIME     NULL,
                created_at  DATETIME      DEFAULT CURRENT_TIMESTAMP,
                updated_at  DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)

        # Keep existing deployments compatible by adding missing columns.
        _ensure_column(cursor, 'todos', 'user_id', "ALTER TABLE todos ADD COLUMN user_id INT NULL AFTER id")
        _ensure_column(cursor, 'todos', 'order_index', "ALTER TABLE todos ADD COLUMN order_index INT DEFAULT 0 AFTER user_id")
        _ensure_column(cursor, 'todos', 'category', "ALTER TABLE todos ADD COLUMN category VARCHAR(60) DEFAULT 'general' AFTER description")
        _ensure_column(cursor, 'todos', 'due_date', "ALTER TABLE todos ADD COLUMN due_date DATE NULL AFTER priority")
        _ensure_column(cursor, 'todos', 'completed_at', "ALTER TABLE todos ADD COLUMN completed_at DATETIME NULL AFTER completed")
        _ensure_column(cursor, 'todos', 'alerted_at', "ALTER TABLE todos ADD COLUMN alerted_at DATETIME NULL AFTER completed_at")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            INT AUTO_INCREMENT PRIMARY KEY,
                name          VARCHAR(120)  NOT NULL,
                email         VARCHAR(255)  NOT NULL UNIQUE,
                password_hash VARCHAR(255)  NOT NULL,
                created_at    DATETIME      DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()
        print("✅  Database initialised successfully.")
    except Error as e:
        print(f"⚠️  Database init error: {e}")


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.route('/')
def index():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    return render_template('index.html', user=session.get('user_name'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('index'))

    error = None
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''

        if not email or not password:
            error = 'Email and password are required.'
        else:
            try:
                conn = get_connection()
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
                user = cursor.fetchone()
                cursor.close()
                conn.close()

                if not user or not check_password_hash(user['password_hash'], password):
                    error = 'Invalid email or password.'
                else:
                    session['user_id'] = user['id']
                    session['user_name'] = user['name']
                    session['user_email'] = user['email']
                    return redirect(url_for('index'))
            except Error as e:
                error = str(e)

    return render_template('login.html', error=error)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if session.get('user_id'):
        return redirect(url_for('index'))

    error = None
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        confirm = request.form.get('confirm_password') or ''

        if not name or not email or not password:
            error = 'All fields are required.'
        elif len(password) < 8:
            error = 'Password must be at least 8 characters.'
        elif password != confirm:
            error = 'Passwords do not match.'
        else:
            try:
                conn = get_connection()
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
                existing = cursor.fetchone()

                if existing:
                    error = 'That email is already registered.'
                else:
                    cursor.execute(
                        "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)",
                        (name, email, generate_password_hash(password))
                    )
                    conn.commit()
                    user_id = cursor.lastrowid
                    cursor.close()
                    conn.close()
                    session['user_id'] = user_id
                    session['user_name'] = name
                    session['user_email'] = email
                    return redirect(url_for('index'))

                cursor.close()
                conn.close()
            except Error as e:
                error = str(e)

    return render_template('signup.html', error=error)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.before_request
def protect_api_routes():
    allowed_paths = {'login', 'signup', 'static'}
    if request.endpoint in allowed_paths or request.endpoint is None:
        return None
    if request.endpoint == 'index':
        return None
    if request.path.startswith('/api/') and not session.get('user_id'):
        return jsonify({'error': 'Authentication required'}), 401


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapped


# ── CREATE ────────────────────────────────────
@app.route('/api/todos', methods=['POST'])
@login_required
def create_todo():
    data = request.get_json()
    title = (data.get('title') or '').strip()
    if not title:
        return jsonify({'error': 'Title is required'}), 400

    description = (data.get('description') or '').strip()
    category = _normalize_category(data.get('category'))
    priority    = data.get('priority', 'medium')
    due_date = _parse_due_date(data.get('due_date'))
    user_id = session.get('user_id')

    if priority not in ('low', 'medium', 'high'):
        priority = 'medium'
    if data.get('due_date') and due_date is None:
        return jsonify({'error': 'Invalid due date format. Use YYYY-MM-DD'}), 400

    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT COALESCE(MAX(order_index), 0) + 1 AS next_order FROM todos WHERE user_id = %s", (user_id,))
        next_order = cursor.fetchone()['next_order']
        cursor.execute(
            "INSERT INTO todos (user_id, order_index, title, description, category, priority, due_date, alerted_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (user_id, next_order, title, description, category, priority, due_date, None)
        )
        new_id = cursor.lastrowid
        cursor.execute("SELECT * FROM todos WHERE id = %s", (new_id,))
        todo = cursor.fetchone()
        cursor.close()
        conn.close()
        todo = _serialize(todo)
        return jsonify({'message': 'Todo created', 'todo': todo}), 201
    except Error as e:
        return jsonify({'error': str(e)}), 500


# ── READ ALL ──────────────────────────────────
@app.route('/api/todos', methods=['GET'])
@login_required
def get_todos():
    filter_by = request.args.get('filter', 'all')   # all | active | completed
    priority  = request.args.get('priority', 'all') # all | low | medium | high
    category  = _normalize_category(request.args.get('category', 'all'))
    due       = request.args.get('due', 'all')      # all | overdue | today | upcoming | no_due
    calendar_date = request.args.get('calendar_date', '').strip()
    sort_by   = request.args.get('sort', 'manual')  # manual | due | priority | created
    search    = request.args.get('search', '').strip()

    conditions, params = [], []

    if filter_by == 'active':
        conditions.append('completed = 0')
    elif filter_by == 'completed':
        conditions.append('completed = 1')

    if priority != 'all':
        conditions.append('priority = %s')
        params.append(priority)

    if category != 'all':
        conditions.append('category = %s')
        params.append(category)

    if due == 'overdue':
        conditions.append('due_date IS NOT NULL AND due_date < CURDATE() AND completed = 0')
    elif due == 'today':
        conditions.append('due_date = CURDATE()')
    elif due == 'upcoming':
        conditions.append('due_date > CURDATE()')
    elif due == 'no_due':
        conditions.append('due_date IS NULL')

    if calendar_date:
        parsed_calendar = _parse_due_date(calendar_date)
        if parsed_calendar is not None:
          conditions.append('due_date = %s')
          params.append(parsed_calendar)

    if search:
        conditions.append('(title LIKE %s OR description LIKE %s)')
        params += [f'%{search}%', f'%{search}%']

    conditions.append('user_id = %s')
    params.append(session.get('user_id'))

    where = ('WHERE ' + ' AND '.join(conditions)) if conditions else ''

    order_clause = {
        'due': 'ORDER BY (due_date IS NULL), due_date ASC, order_index ASC, created_at DESC',
        'priority': "ORDER BY FIELD(priority, 'high', 'medium', 'low'), (due_date IS NULL), due_date ASC, created_at DESC",
        'created': 'ORDER BY created_at DESC',
        'manual': 'ORDER BY order_index ASC, created_at DESC',
    }.get(sort_by, 'ORDER BY order_index ASC, created_at DESC')

    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(f"SELECT * FROM todos {where} {order_clause}", params)
        todos = [_serialize(t) for t in cursor.fetchall()]

        cursor.execute(
            """
            SELECT id, title, due_date, priority, alerted_at
            FROM todos
            WHERE user_id = %s AND completed = 0 AND due_date IS NOT NULL AND due_date < CURDATE()
            ORDER BY due_date ASC, order_index ASC, created_at DESC
            """,
            (session.get('user_id'),)
        )
        overdue_todos = [_serialize(row) for row in cursor.fetchall()]

        if overdue_todos and _should_send_overdue_email(overdue_todos):
            try:
                _send_overdue_email(session.get('user_email'), session.get('user_name'), overdue_todos)
                cursor.execute(
                    """
                    UPDATE todos
                    SET alerted_at = NOW()
                    WHERE user_id = %s AND completed = 0 AND due_date IS NOT NULL AND due_date < CURDATE()
                    """,
                    (session.get('user_id'),)
                )
            except Exception as email_error:
                app.logger.warning('Overdue email alert failed: %s', email_error)

        # Stats
        cursor.execute("SELECT COUNT(*) AS total FROM todos WHERE user_id = %s", (session.get('user_id'),))
        total = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(*) AS done FROM todos WHERE completed = 1 AND user_id = %s", (session.get('user_id'),))
        done = cursor.fetchone()['done']

        cursor.execute("SELECT COUNT(*) AS pending FROM todos WHERE completed = 0 AND user_id = %s", (session.get('user_id'),))
        pending = cursor.fetchone()['pending']

        completion_percent = round((done / total * 100) if total else 0)
        streak = _current_streak(cursor, session.get('user_id'))

        cursor.execute(
            """
            SELECT DATE(completed_at) AS day, COUNT(*) AS count
            FROM todos
            WHERE user_id = %s AND completed = 1 AND completed_at IS NOT NULL AND completed_at >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
            GROUP BY DATE(completed_at)
            ORDER BY day ASC
            """,
            (session.get('user_id'),)
        )
        chart_rows = cursor.fetchall()
        chart_map = {row['day'].isoformat(): row['count'] for row in chart_rows if row['day']}
        last_7_days = []
        for offset in range(6, -1, -1):
            day = date.today() - __import__('datetime').timedelta(days=offset)
            iso_day = day.isoformat()
            last_7_days.append({'day': iso_day, 'count': int(chart_map.get(iso_day, 0))})

        cursor.close()
        conn.close()
        return jsonify({
            'todos': todos,
            'stats': {
                'total': total,
                'completed': done,
                'active': pending,
                'pending': pending,
                'completion_percent': completion_percent,
                'streak': streak,
                'completed_today': next((item['count'] for item in last_7_days if item['day'] == date.today().isoformat()), 0),
            },
            'alerts': {
                'overdue_count': len(overdue_todos),
                'overdue_todos': overdue_todos[:5],
            },
            'chart': last_7_days,
        })
    except Error as e:
        return jsonify({'error': str(e)}), 500


# ── READ ONE ──────────────────────────────────
@app.route('/api/todos/<int:todo_id>', methods=['GET'])
@login_required
def get_todo(todo_id):
    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM todos WHERE id = %s AND user_id = %s", (todo_id, session.get('user_id')))
        todo = cursor.fetchone()
        cursor.close()
        conn.close()
        if not todo:
            return jsonify({'error': 'Todo not found'}), 404
        return jsonify({'todo': _serialize(todo)})
    except Error as e:
        return jsonify({'error': str(e)}), 500


# ── UPDATE ────────────────────────────────────
@app.route('/api/todos/<int:todo_id>', methods=['PUT'])
@login_required
def update_todo(todo_id):
    data = request.get_json()
    fields, params = [], []
    reset_alerted_at = False

    if 'title' in data:
        title = data['title'].strip()
        if not title:
            return jsonify({'error': 'Title cannot be empty'}), 400
        fields.append('title = %s');       params.append(title)

    if 'description' in data:
        fields.append('description = %s'); params.append(data['description'].strip())

    if 'category' in data:
        fields.append('category = %s'); params.append(_normalize_category(data.get('category')))

    if 'priority' in data:
        p = data['priority']
        if p not in ('low', 'medium', 'high'):
            return jsonify({'error': 'Invalid priority'}), 400
        fields.append('priority = %s');    params.append(p)

    if 'due_date' in data:
        parsed_due = _parse_due_date(data.get('due_date'))
        if data.get('due_date') and parsed_due is None:
            return jsonify({'error': 'Invalid due date format. Use YYYY-MM-DD'}), 400
        fields.append('due_date = %s'); params.append(parsed_due)
        reset_alerted_at = True

    if 'completed' in data:
        completed = bool(data['completed'])
        fields.append('completed = %s');   params.append(completed)
        fields.append('completed_at = %s'); params.append(datetime.now() if completed else None)
        if not completed:
            reset_alerted_at = True

    if reset_alerted_at:
        fields.append('alerted_at = %s'); params.append(None)

    if not fields:
        return jsonify({'error': 'No fields to update'}), 400

    params.append(todo_id)
    params.append(session.get('user_id'))
    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(f"UPDATE todos SET {', '.join(fields)} WHERE id = %s AND user_id = %s", params)
        cursor.execute("SELECT * FROM todos WHERE id = %s AND user_id = %s", (todo_id, session.get('user_id')))
        todo = cursor.fetchone()
        cursor.close()
        conn.close()
        if not todo:
            return jsonify({'error': 'Todo not found'}), 404
        return jsonify({'message': 'Todo updated', 'todo': _serialize(todo)})
    except Error as e:
        return jsonify({'error': str(e)}), 500


# ── DELETE ────────────────────────────────────
@app.route('/api/todos/<int:todo_id>', methods=['DELETE'])
@login_required
def delete_todo(todo_id):
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM todos WHERE id = %s AND user_id = %s", (todo_id, session.get('user_id')))
        affected = cursor.rowcount
        cursor.close()
        conn.close()
        if affected == 0:
            return jsonify({'error': 'Todo not found'}), 404
        return jsonify({'message': 'Todo deleted'})
    except Error as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/todos/reorder', methods=['POST'])
@login_required
def reorder_todos():
    data = request.get_json() or {}
    ids = data.get('ids', [])
    if not isinstance(ids, list) or not ids:
        return jsonify({'error': 'ids must be a non-empty list'}), 400

    try:
        conn = get_connection()
        cursor = conn.cursor()
        for index, todo_id in enumerate(ids, start=1):
            cursor.execute(
                "UPDATE todos SET order_index = %s WHERE id = %s AND user_id = %s",
                (index, int(todo_id), session.get('user_id')),
            )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'message': 'Order updated'})
    except Error as e:
        return jsonify({'error': str(e)}), 500


# ── BULK DELETE COMPLETED ─────────────────────
@app.route('/api/todos/completed', methods=['DELETE'])
@login_required
def delete_completed():
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM todos WHERE completed = 1 AND user_id = %s", (session.get('user_id'),))
        count = cursor.rowcount
        cursor.close()
        conn.close()
        return jsonify({'message': f'{count} completed todo(s) deleted'})
    except Error as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _serialize(todo: dict) -> dict:
    """Convert MySQL row to JSON-safe dict."""
    todo.pop('user_id', None)
    for key in ('created_at', 'updated_at'):
        if isinstance(todo.get(key), datetime):
            todo[key] = todo[key].isoformat()
    if isinstance(todo.get('due_date'), (datetime, date)):
        todo['due_date'] = todo['due_date'].isoformat()
    todo['completed'] = bool(todo.get('completed'))
    return todo


def _normalize_category(raw) -> str:
    value = (raw or 'general').strip().lower()
    if not value:
        return 'general'
    return value[:60]


def _parse_due_date(raw):
    if raw in (None, ''):
        return None
    try:
        return datetime.strptime(raw, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return None


def _ensure_column(cursor, table_name: str, column_name: str, alter_sql: str):
    cursor.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s AND column_name = %s
        LIMIT 1
        """,
        (DB_CONFIG['database'], table_name, column_name),
    )
    if cursor.fetchone() is None:
        cursor.execute(alter_sql)


def _current_streak(cursor, user_id):
    cursor.execute(
        """
        SELECT DISTINCT DATE(completed_at) AS day
        FROM todos
        WHERE user_id = %s AND completed = 1 AND completed_at IS NOT NULL
        ORDER BY day DESC
        """,
        (user_id,)
    )
    days = [row['day'] for row in cursor.fetchall() if row['day']]
    if not days:
        return 0

    streak = 0
    expected = date.today()
    day_set = set(days)
    while expected in day_set:
        streak += 1
        expected = expected.fromordinal(expected.toordinal() - 1)
    return streak


def _should_send_overdue_email(overdue_todos):
    if not MAIL_CONFIG['host']:
        return False

    oldest_pending = None
    for todo in overdue_todos:
        alerted_at = todo.get('alerted_at')
        if alerted_at is None:
            return True
        if isinstance(alerted_at, str):
            try:
                alerted_at = datetime.fromisoformat(alerted_at)
            except ValueError:
                return True
        if oldest_pending is None or alerted_at < oldest_pending:
            oldest_pending = alerted_at

    if oldest_pending is None:
        return True

    return datetime.now() - oldest_pending >= __import__('datetime').timedelta(hours=ALERT_COOLDOWN_HOURS)


def _send_overdue_email(recipient_email, recipient_name, overdue_todos):
    if not recipient_email or not MAIL_CONFIG['host']:
        return

    subject = f"TASKR overdue reminder ({len(overdue_todos)} task(s))"
    lines = [
        f"Hi {recipient_name or 'there'},",
        "",
        "You have overdue task(s) that are still incomplete:",
        "",
    ]
    for todo in overdue_todos[:10]:
        due_date = todo.get('due_date') or 'unknown date'
        lines.append(f"- {todo.get('title', 'Untitled')} (due {due_date})")
    lines.extend([
        "",
        "Open TASKR and mark them complete or update the due date.",
    ])

    message = MIMEText('\n'.join(lines), 'plain', 'utf-8')
    message['Subject'] = subject
    message['From'] = MAIL_CONFIG['from']
    message['To'] = recipient_email

    with smtplib.SMTP(MAIL_CONFIG['host'], MAIL_CONFIG['port'], timeout=10) as server:
        if MAIL_CONFIG['use_tls']:
            server.starttls()
        if MAIL_CONFIG['user']:
            server.login(MAIL_CONFIG['user'], MAIL_CONFIG['password'])
        server.sendmail(MAIL_CONFIG['from'], [recipient_email], message.as_string())


# ─────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
