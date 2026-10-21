import sqlite3
import bcrypt

DB_NAME = "learning_system_v2.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def create_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL CHECK (
            role IN ('Student', 'Teacher', 'Administrator', 'Parent')
        ),
        class_name TEXT,
        profile_picture TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS parent_student (
        parent_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        PRIMARY KEY (parent_id, student_id),
        FOREIGN KEY (parent_id) REFERENCES users(id),
        FOREIGN KEY (student_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        is_active INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS teacher_subjects (
        teacher_id INTEGER NOT NULL,
        subject_id INTEGER NOT NULL,
        PRIMARY KEY (teacher_id, subject_id),
        FOREIGN KEY (teacher_id) REFERENCES users(id),
        FOREIGN KEY (subject_id) REFERENCES subjects(id)
    );

    CREATE TABLE IF NOT EXISTS student_subjects (
        student_id INTEGER NOT NULL,
        subject_id INTEGER NOT NULL,
        PRIMARY KEY (student_id, subject_id),
        FOREIGN KEY (student_id) REFERENCES users(id),
        FOREIGN KEY (subject_id) REFERENCES subjects(id)
    );

    CREATE TABLE IF NOT EXISTS subject_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        teacher_id INTEGER NOT NULL,
        subject_id INTEGER NOT NULL,
        request_type TEXT NOT NULL CHECK (
            request_type IN ('ADD', 'DROP')
        ),
        status TEXT DEFAULT 'Pending',
        admin_remark TEXT,
        requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        reviewed_at TIMESTAMP,
        FOREIGN KEY (teacher_id) REFERENCES users(id),
        FOREIGN KEY (subject_id) REFERENCES subjects(id)
    );

    CREATE TABLE IF NOT EXISTS topics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        FOREIGN KEY (subject_id) REFERENCES subjects(id),
        UNIQUE (subject_id, name)
    );

    CREATE TABLE IF NOT EXISTS quizzes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id INTEGER NOT NULL,
        teacher_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        scheduled_at TEXT,
        due_at TEXT,
        status TEXT DEFAULT 'Draft',
        is_requiz INTEGER DEFAULT 0,
        original_quiz_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (subject_id) REFERENCES subjects(id),
        FOREIGN KEY (teacher_id) REFERENCES users(id),
        FOREIGN KEY (original_quiz_id) REFERENCES quizzes(id)
    );

    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quiz_id INTEGER NOT NULL,
        topic_id INTEGER NOT NULL,
        question_text TEXT NOT NULL,
        option_a TEXT NOT NULL,
        option_b TEXT NOT NULL,
        option_c TEXT,
        option_d TEXT,
        correct_answer TEXT NOT NULL,
        explanation TEXT,
        difficulty TEXT DEFAULT 'Medium',
        marks INTEGER DEFAULT 1,
        FOREIGN KEY (quiz_id) REFERENCES quizzes(id),
        FOREIGN KEY (topic_id) REFERENCES topics(id)
    );

    CREATE TABLE IF NOT EXISTS quiz_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        quiz_id INTEGER NOT NULL,
        score REAL DEFAULT 0,
        max_score REAL DEFAULT 0,
        status TEXT DEFAULT 'In Progress',
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        submitted_at TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES users(id),
        FOREIGN KEY (quiz_id) REFERENCES quizzes(id)
    );

    CREATE TABLE IF NOT EXISTS attempt_answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        attempt_id INTEGER NOT NULL,
        question_id INTEGER NOT NULL,
        selected_answer TEXT,
        is_correct INTEGER DEFAULT 0,
        help_used INTEGER DEFAULT 0,
        answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (attempt_id) REFERENCES quiz_attempts(id),
        FOREIGN KEY (question_id) REFERENCES questions(id),
        UNIQUE (attempt_id, question_id)
    );

    CREATE TABLE IF NOT EXISTS ai_help_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        quiz_id INTEGER NOT NULL,
        question_id INTEGER NOT NULL,
        topic_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES users(id),
        FOREIGN KEY (quiz_id) REFERENCES quizzes(id),
        FOREIGN KEY (question_id) REFERENCES questions(id),
        FOREIGN KEY (topic_id) REFERENCES topics(id)
    );

    CREATE TABLE IF NOT EXISTS requiz_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        quiz_id INTEGER NOT NULL,
        reason TEXT,
        status TEXT DEFAULT 'Pending',
        teacher_remark TEXT,
        requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        reviewed_at TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES users(id),
        FOREIGN KEY (quiz_id) REFERENCES quizzes(id)
    );

    CREATE TABLE IF NOT EXISTS learning_resources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id INTEGER NOT NULL,
        teacher_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        file_path TEXT NOT NULL,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (subject_id) REFERENCES subjects(id),
        FOREIGN KEY (teacher_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER NOT NULL,
        receiver_id INTEGER NOT NULL,
        subject_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (sender_id) REFERENCES users(id),
        FOREIGN KEY (receiver_id) REFERENCES users(id),
        FOREIGN KEY (subject_id) REFERENCES subjects(id)
    );

    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipient_id INTEGER NOT NULL,
        notification_type TEXT NOT NULL,
        message TEXT NOT NULL,
        reference_id INTEGER,
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (recipient_id) REFERENCES users(id)
    );
    """)

    demo_users = [
        ("chetna", "chetz0712", "Student", "Student Demo", "SE-A"),
        ("sahithi", "sahi2006", "Teacher", "Teacher Demo", None),
        ("admin", "admin123", "Administrator", "Administrator", None),
        ("parent1", "parent123", "Parent", "Parent Demo", None),
    ]

    for username, password, role, full_name, class_name in demo_users:
        password_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        cursor.execute("""
            INSERT OR IGNORE INTO users
            (username, password, role, full_name, class_name)
            VALUES (?, ?, ?, ?, ?)
        """, (username, password_hash, role, full_name, class_name))

    cursor.execute("""
        INSERT OR IGNORE INTO subjects (name)
        VALUES ('Data Structures')
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO subjects (name)
        VALUES ('Database Systems')
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO teacher_subjects (teacher_id, subject_id)
        SELECT u.id, s.id
        FROM users u, subjects s
        WHERE u.username = 'yashi'
          AND s.name IN ('Data Structures', 'Database Systems')
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO student_subjects (student_id, subject_id)
        SELECT u.id, s.id
        FROM users u, subjects s
        WHERE u.username = 'chetna'
          AND s.name IN ('Data Structures', 'Database Systems')
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO parent_student (parent_id, student_id)
        SELECT p.id, s.id
        FROM users p, users s
        WHERE p.username = 'parent1'
          AND s.username = 'chetna'
    """)

    conn.commit()
    conn.close()


def verify_password(password, stored_hash):
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            stored_hash.encode("utf-8")
        )
    except (ValueError, TypeError):
        return False

def login_user(username, password, role):
    conn = get_connection()

    if role == "Parent":
        user = conn.execute("""
            SELECT * FROM users
            WHERE username = ? AND role = 'Student'
        """, (username,)).fetchone()
    else:
        user = conn.execute("""
            SELECT * FROM users
            WHERE username = ? AND role = ?
        """, (username, role)).fetchone()

    conn.close()

    if user and verify_password(password, user["password"]):
        result = dict(user)

        if role == "Parent":
            result["role"] = "Parent"
            result["student_id"] = user["id"]

        return result

    return None