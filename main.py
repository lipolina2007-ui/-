from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
import sqlite3
import hashlib
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = "yoga_om_secret_key_2024"
CORS(app, supports_credentials=True)

DB_PATH = "yoga_studio.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_tables():
    conn = get_db()
    
    # Таблица пользователей
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('client', 'instructor', 'admin')),
            phone TEXT,
            created_at TEXT NOT NULL
        )
    """)
    
    # Таблица клиентов (доп. информация)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            address TEXT,
            birth_date TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Таблица инструкторов (доп. информация)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS instructors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            specialization TEXT,
            experience_years INTEGER,
            bio TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Таблица занятий
    conn.execute("""
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            instructor_id INTEGER NOT NULL,
            instructor_name TEXT NOT NULL,
            datetime TEXT NOT NULL,
            duration_minutes INTEGER DEFAULT 60,
            max_participants INTEGER DEFAULT 15,
            current_participants INTEGER DEFAULT 0,
            location TEXT,
            price INTEGER DEFAULT 0,
            FOREIGN KEY (instructor_id) REFERENCES users(id)
        )
    """)
    
    # Таблица записей на занятия
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            class_id INTEGER NOT NULL,
            booking_date TEXT NOT NULL,
            status TEXT DEFAULT 'confirmed' CHECK(status IN ('confirmed', 'cancelled', 'completed')),
            payment_status TEXT DEFAULT 'pending',
            FOREIGN KEY (client_id) REFERENCES clients(id),
            FOREIGN KEY (class_id) REFERENCES classes(id)
        )
    """)
    
    conn.commit()
    conn.close()

def init_test_data():
    conn = get_db()
    
    # Проверяем, есть ли уже данные
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if count > 0:
        conn.close()
        return
    
    now = datetime.now().isoformat()
    
    # Создаём администратора
    conn.execute("""
        INSERT INTO users (name, email, password, role, phone, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, ("Алексей Иванов", "admin@om.ru", hash_password("admin123"), "admin", "+7 (999) 111-22-33", now))
    
    # Создаём инструкторов
    instructors = [
        ("Екатерина Смирнова", "instructor@om.ru", hash_password("instructor123"), "instructor", "+7 (999) 222-33-44", "Хатха-йога, Виньяса-флоу", 5, "Сертифицированный инструктор с 5-летним опытом"),
        ("Дмитрий Петров", "dmitry@om.ru", hash_password("dmitry123"), "instructor", "+7 (999) 333-44-55", "Аштанга-йога, Пранаяма", 3, "Практикует йогу более 10 лет")
    ]
    
    for inst in instructors:
        conn.execute("""
            INSERT INTO users (name, email, password, role, phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (inst[0], inst[1], inst[2], inst[3], inst[4], now))
        
        user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute("""
            INSERT INTO instructors (user_id, specialization, experience_years, bio)
            VALUES (?, ?, ?, ?)
        """, (user_id, inst[5], inst[6], inst[7]))
    
    # Создаём клиентов
    clients_data = [
        ("Анна Михайлова", "client@om.ru", hash_password("client123"), "client", "+7 (999) 444-55-66", "г. Москва, ул. Цветочная, д. 10", "1990-05-15"),
        ("Сергей Козлов", "sergey@om.ru", hash_password("sergey123"), "client", "+7 (999) 555-66-77", "г. Москва, ул. Солнечная, д. 5", "1988-10-20")
    ]
    
    for client in clients_data:
        conn.execute("""
            INSERT INTO users (name, email, password, role, phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (client[0], client[1], client[2], client[3], client[4], now))
        
        user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute("""
            INSERT INTO clients (user_id, address, birth_date)
            VALUES (?, ?, ?)
        """, (user_id, client[5], client[6]))
    
    # Создаём занятия
    classes_data = [
        ("Хатха-йога", "Мягкая практика для начинающих", 2, "Екатерина Смирнова", "2024-12-20 10:00:00", 60, 15, "Зал 1", 500),
        ("Виньяса-флоу", "Динамичная практика с дыханием", 2, "Екатерина Смирнова", "2024-12-21 18:30:00", 75, 12, "Зал 2", 600),
        ("Аштанга-йога", "Интенсивная практика для продвинутых", 3, "Дмитрий Петров", "2024-12-22 09:00:00", 90, 10, "Зал 1", 700),
        ("Медитация", "Практика осознанности", 2, "Екатерина Смирнова", "2024-12-23 08:00:00", 45, 20, "Зал 3", 300),
        ("Йога-нидра", "Глубокая релаксация", 3, "Дмитрий Петров", "2024-12-24 19:00:00", 60, 15, "Зал 2", 400)
    ]
    
    for cls in classes_data:
        conn.execute("""
            INSERT INTO classes (title, description, instructor_id, instructor_name, datetime, duration_minutes, max_participants, location, price)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, cls)
    
    conn.commit()
    conn.close()

# Декоратор для проверки авторизации
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Не авторизован"}), 401
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user_role' not in session or session['user_role'] not in roles:
                return jsonify({"error": "Недостаточно прав"}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator

# ============= API РОУТЫ =============

@app.route('/')
def index():
    return render_template('index.html')

# Регистрация
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    phone = data.get('phone', '').strip()
    role = data.get('role', 'client')
    
    if not name or not email or not password:
        return jsonify({"error": "Заполните все обязательные поля"}), 400
    if len(password) < 6:
        return jsonify({"error": "Пароль должен быть не менее 6 символов"}), 400
    
    conn = get_db()
    existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        conn.close()
        return jsonify({"error": "Email уже зарегистрирован"}), 400
    
    now = datetime.now().isoformat()
    
    conn.execute("""
        INSERT INTO users (name, email, password, role, phone, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name, email, hash_password(password), role, phone, now))
    
    user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    
    # Создаём запись в соответствующей таблице
    if role == 'client':
        conn.execute("INSERT INTO clients (user_id) VALUES (?)", (user_id,))
    elif role == 'instructor':
        conn.execute("INSERT INTO instructors (user_id) VALUES (?)", (user_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Регистрация успешна! Теперь вы можете войти"})

# Вход
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    
    conn = get_db()
    user = conn.execute("""
        SELECT id, name, email, role, phone FROM users 
        WHERE email = ? AND password = ?
    """, (email, hash_password(password))).fetchone()
    conn.close()
    
    if not user:
        return jsonify({"error": "Неверный email или пароль"}), 401
    
    session['user_id'] = user['id']
    session['user_name'] = user['name']
    session['user_email'] = user['email']
    session['user_role'] = user['role']
    session['user_phone'] = user['phone']
    
    return jsonify({
        "message": "Вход выполнен",
        "user": {
            "id": user['id'],
            "name": user['name'],
            "email": user['email'],
            "role": user['role'],
            "phone": user['phone']
        }
    })

# Выход
@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"message": "Вы вышли из системы"})

# Получить текущего пользователя
@app.route('/api/me', methods=['GET'])
@login_required
def get_me():
    return jsonify({
        "id": session['user_id'],
        "name": session['user_name'],
        "email": session['user_email'],
        "role": session['user_role'],
        "phone": session['user_phone']
    })

# Получить все занятия
@app.route('/api/classes', methods=['GET'])
def get_classes():
    conn = get_db()
    classes = conn.execute("""
        SELECT c.*, 
               (SELECT COUNT(*) FROM bookings WHERE class_id = c.id AND status = 'confirmed') as booked_count
        FROM classes c
        ORDER BY datetime
    """).fetchall()
    conn.close()
    
    result = []
    for cls in classes:
        result.append({
            "id": cls['id'],
            "title": cls['title'],
            "description": cls['description'],
            "instructor_id": cls['instructor_id'],
            "instructor_name": cls['instructor_name'],
            "datetime": cls['datetime'],
            "duration_minutes": cls['duration_minutes'],
            "max_participants": cls['max_participants'],
            "current_participants": cls['current_participants'] or 0,
            "booked_count": cls['booked_count'] or 0,
            "location": cls['location'],
            "price": cls['price']
        })
    return jsonify(result)

# Получить занятия инструктора
@app.route('/api/instructor/classes', methods=['GET'])
@login_required
@role_required('instructor', 'admin')
def get_instructor_classes():
    user_id = session['user_id']
    conn = get_db()
    
    classes = conn.execute("""
        SELECT c.*, 
               (SELECT COUNT(*) FROM bookings WHERE class_id = c.id AND status = 'confirmed') as booked_count
        FROM classes c
        WHERE c.instructor_id = ?
        ORDER BY c.datetime
    """, (user_id,)).fetchall()
    
    result = []
    for cls in classes:
        # Получаем клиентов, записанных на это занятие
        clients = conn.execute("""
            SELECT u.name, u.phone, u.email, b.booking_date, b.payment_status
            FROM bookings b
            JOIN clients cl ON b.client_id = cl.id
            JOIN users u ON cl.user_id = u.id
            WHERE b.class_id = ? AND b.status = 'confirmed'
        """, (cls['id'],)).fetchall()
        
        clients_list = [{
            "name": c['name'],
            "phone": c['phone'],
            "email": c['email'],
            "booking_date": c['booking_date'],
            "payment_status": c['payment_status']
        } for c in clients]
        
        result.append({
            "id": cls['id'],
            "title": cls['title'],
            "description": cls['description'],
            "datetime": cls['datetime'],
            "duration_minutes": cls['duration_minutes'],
            "max_participants": cls['max_participants'],
            "booked_count": cls['booked_count'] or 0,
            "location": cls['location'],
            "price": cls['price'],
            "clients": clients_list
        })
    
    conn.close()
    return jsonify(result)

# Записаться на занятие
@app.route('/api/book', methods=['POST'])
@login_required
@role_required('client')
def book_class():
    data = request.get_json()
    class_id = data.get('class_id')
    
    conn = get_db()
    
    # Проверяем существование занятия
    cls = conn.execute("SELECT * FROM classes WHERE id = ?", (class_id,)).fetchone()
    if not cls:
        conn.close()
        return jsonify({"error": "Занятие не найдено"}), 404
    
    # Получаем клиента
    client = conn.execute("SELECT id FROM clients WHERE user_id = ?", (session['user_id'],)).fetchone()
    if not client:
        conn.close()
        return jsonify({"error": "Профиль клиента не найден"}), 400
    
    # Проверяем, не записан ли уже
    existing = conn.execute("""
        SELECT id FROM bookings 
        WHERE client_id = ? AND class_id = ? AND status = 'confirmed'
    """, (client['id'], class_id)).fetchone()
    if existing:
        conn.close()
        return jsonify({"error": "Вы уже записаны на это занятие"}), 400
    
    # Проверяем количество активных записей
    active_count = conn.execute("""
        SELECT COUNT(*) FROM bookings b
        JOIN classes c ON b.class_id = c.id
        WHERE b.client_id = ? AND b.status = 'confirmed' AND c.datetime > datetime('now')
    """, (client['id'],)).fetchone()[0]
    
    if active_count >= 5:
        conn.close()
        return jsonify({"error": "У вас уже 5 активных записей. Отмените одну, чтобы записаться на новую"}), 400
    
    # Проверяем свободные места
    booked = conn.execute("""
        SELECT COUNT(*) FROM bookings WHERE class_id = ? AND status = 'confirmed'
    """, (class_id,)).fetchone()[0]
    
    if booked >= cls['max_participants']:
        conn.close()
        return jsonify({"error": "Нет свободных мест"}), 400
    
    # Создаём запись
    now = datetime.now().isoformat()
    conn.execute("""
        INSERT INTO bookings (client_id, class_id, booking_date, status)
        VALUES (?, ?, ?, 'confirmed')
    """, (client['id'], class_id, now))
    
    # Обновляем количество участников
    conn.execute("""
        UPDATE classes SET current_participants = current_participants + 1
        WHERE id = ?
    """, (class_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Вы успешно записаны на занятие!"})

# Отменить запись
@app.route('/api/cancel-booking/<int:booking_id>', methods=['POST'])
@login_required
@role_required('client')
def cancel_booking(booking_id):
    conn = get_db()
    
    client = conn.execute("SELECT id FROM clients WHERE user_id = ?", (session['user_id'],)).fetchone()
    if not client:
        conn.close()
        return jsonify({"error": "Профиль клиента не найден"}), 400
    
    booking = conn.execute("""
        SELECT * FROM bookings WHERE id = ? AND client_id = ? AND status = 'confirmed'
    """, (booking_id, client['id'])).fetchone()
    
    if not booking:
        conn.close()
        return jsonify({"error": "Запись не найдена"}), 404
    
    # Отменяем запись
    conn.execute("UPDATE bookings SET status = 'cancelled' WHERE id = ?", (booking_id,))
    conn.execute("""
        UPDATE classes SET current_participants = current_participants - 1
        WHERE id = ?
    """, (booking['class_id'],))
    
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Запись отменена"})

# Мои занятия (для клиента)
@app.route('/api/my-bookings', methods=['GET'])
@login_required
@role_required('client')
def my_bookings():
    conn = get_db()
    
    client = conn.execute("SELECT id FROM clients WHERE user_id = ?", (session['user_id'],)).fetchone()
    if not client:
        conn.close()
        return jsonify([])
    
    bookings = conn.execute("""
        SELECT b.id, b.booking_date, b.status, b.payment_status,
               c.id as class_id, c.title, c.description, c.instructor_name, 
               c.datetime, c.duration_minutes, c.location, c.price
        FROM bookings b
        JOIN classes c ON b.class_id = c.id
        WHERE b.client_id = ? AND b.status = 'confirmed'
        ORDER BY c.datetime
    """, (client['id'],)).fetchall()
    
    result = []
    for b in bookings:
        result.append({
            "id": b['id'],
            "class_id": b['class_id'],
            "title": b['title'],
            "description": b['description'],
            "instructor_name": b['instructor_name'],
            "datetime": b['datetime'],
            "duration_minutes": b['duration_minutes'],
            "location": b['location'],
            "price": b['price'],
            "booking_date": b['booking_date'],
            "payment_status": b['payment_status']
        })
    
    conn.close()
    return jsonify(result)

# История посещений (для клиента)
@app.route('/api/history', methods=['GET'])
@login_required
@role_required('client')
def get_history():
    conn = get_db()
    
    client = conn.execute("SELECT id FROM clients WHERE user_id = ?", (session['user_id'],)).fetchone()
    if not client:
        conn.close()
        return jsonify([])
    
    history = conn.execute("""
        SELECT b.id, b.booking_date, b.status,
               c.title, c.instructor_name, c.datetime, c.location
        FROM bookings b
        JOIN classes c ON b.class_id = c.id
        WHERE b.client_id = ? AND b.status IN ('cancelled', 'completed')
        ORDER BY b.booking_date DESC
    """, (client['id'],)).fetchall()
    
    result = [dict(h) for h in history]
    conn.close()
    return jsonify(result)

# Добавить занятие (для админа)
@app.route('/api/admin/add-class', methods=['POST'])
@login_required
@role_required('admin')
def add_class():
    data = request.get_json()
    
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    instructor_id = data.get('instructor_id')
    datetime_str = data.get('datetime')
    duration = data.get('duration_minutes', 60)
    max_participants = data.get('max_participants', 15)
    location = data.get('location', '')
    price = data.get('price', 0)
    
    if not title or not instructor_id or not datetime_str:
        return jsonify({"error": "Заполните обязательные поля"}), 400
    
    conn = get_db()
    
    # Получаем имя инструктора
    instructor = conn.execute("SELECT name FROM users WHERE id = ? AND role = 'instructor'", (instructor_id,)).fetchone()
    if not instructor:
        conn.close()
        return jsonify({"error": "Инструктор не найден"}), 404
    
    conn.execute("""
        INSERT INTO classes (title, description, instructor_id, instructor_name, datetime, duration_minutes, max_participants, location, price)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (title, description, instructor_id, instructor['name'], datetime_str, duration, max_participants, location, price))
    
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Занятие успешно добавлено"})

# Получить всех инструкторов (для админа)
@app.route('/api/admin/instructors', methods=['GET'])
@login_required
@role_required('admin')
def get_instructors():
    conn = get_db()
    instructors = conn.execute("""
        SELECT u.id, u.name, u.email, u.phone, i.specialization, i.experience_years
        FROM users u
        JOIN instructors i ON u.id = i.user_id
        WHERE u.role = 'instructor'
    """).fetchall()
    conn.close()
    return jsonify([dict(i) for i in instructors])

# Статистика (для админа)
@app.route('/api/admin/stats', methods=['GET'])
@login_required
@role_required('admin')
def get_stats():
    conn = get_db()
    
    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_clients = conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
    total_instructors = conn.execute("SELECT COUNT(*) FROM instructors").fetchone()[0]
    total_classes = conn.execute("SELECT COUNT(*) FROM classes").fetchone()[0]
    total_bookings = conn.execute("SELECT COUNT(*) FROM bookings WHERE status = 'confirmed'").fetchone()[0]
    
    conn.close()
    
    return jsonify({
        "total_users": total_users,
        "total_clients": total_clients,
        "total_instructors": total_instructors,
        "total_classes": total_classes,
        "total_bookings": total_bookings
    })

# Удалить занятие (для админа)
@app.route('/api/admin/delete-class/<int:class_id>', methods=['DELETE'])
@login_required
@role_required('admin')
def delete_class(class_id):
    conn = get_db()
    
    # Проверяем, есть ли записи на это занятие
    bookings = conn.execute("SELECT COUNT(*) FROM bookings WHERE class_id = ? AND status = 'confirmed'", (class_id,)).fetchone()[0]
    if bookings > 0:
        conn.close()
        return jsonify({"error": f"Нельзя удалить занятие, на него записано {bookings} человек"}), 400
    
    conn.execute("DELETE FROM classes WHERE id = ?", (class_id,))
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Занятие удалено"})

if __name__ == '__main__':
    create_tables()
    init_test_data()
    print("=" * 50)
    print("🧘 Студия йоги 'Ом' запущена!")
    print("📍 http://localhost:5000")
    print("-" * 50)
    print("🔑 Тестовые аккаунты:")
    print("   👤 Клиент:    client@om.ru / client123")
    print("   🧘 Инструктор: instructor@om.ru / instructor123")
    print("   👑 Админ:     admin@om.ru / admin123")
    print("=" * 50)
    app.run(debug=True, port=5000)
