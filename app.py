import os
import sqlite3
import json
import hashlib
import jwt
import datetime
import functools
from flask import Flask, render_template, request, jsonify, send_from_directory, session, redirect, url_for
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'gallery'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'announcements'), exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
    conn = sqlite3.connect('school_management.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        index_number TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        parent_name TEXT,
        class_level TEXT,
        region TEXT,
        phone TEXT,
        email TEXT,
        gender TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        exam_type TEXT,
        form TEXT,
        term TEXT,
        year INTEGER,
        marks_json TEXT,
        total_marks REAL,
        average REAL,
        division TEXT,
        position INTEGER,
        subject_details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(student_id) REFERENCES students(id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_name TEXT,
        parent_name TEXT,
        class_level TEXT,
        region TEXT,
        phone TEXT,
        email TEXT,
        gender TEXT,
        status TEXT DEFAULT 'pending',
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS announcements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        content TEXT,
        image TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS gallery (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        image_path TEXT,
        description TEXT,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        result_id INTEGER,
        student_index TEXT,
        comment TEXT,
        suggestion TEXT,
        admin_reply TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS staff (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        full_name TEXT
    )''')
    
    admin_pass = generate_password_hash('amedeus wireless.com')
    c.execute("INSERT OR IGNORE INTO admins (username, password, role) VALUES (?, ?, ?)", ('admin', admin_pass, 'super_admin'))
    
    staff_pass = generate_password_hash('amedeus wireless.com')
    c.execute("INSERT OR IGNORE INTO staff (username, password, full_name) VALUES (?, ?, ?)", ('staff', staff_pass, 'Default Staff'))
    
    c.execute('''CREATE TABLE IF NOT EXISTS subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        form TEXT,
        subject_name TEXT
    )''')
    
    default_subjects = [
        ('Form I', 'Mathematics'), ('Form I', 'English'), ('Form I', 'Kiswahili'), ('Form I', 'Biology'),
        ('Form I', 'Chemistry'), ('Form I', 'Physics'), ('Form I', 'History'), ('Form I', 'Geography'),
        ('Form I', 'Civics'), ('Form I', 'Bible Knowledge'),
        ('Form II', 'Mathematics'), ('Form II', 'English'), ('Form II', 'Kiswahili'), ('Form II', 'Biology'),
        ('Form II', 'Chemistry'), ('Form II', 'Physics'), ('Form II', 'History'), ('Form II', 'Geography'),
        ('Form III', 'Mathematics'), ('Form III', 'English'), ('Form III', 'Kiswahili'), ('Form III', 'Biology'),
        ('Form III', 'Chemistry'), ('Form III', 'Physics'), ('Form III', 'History'), ('Form III', 'Geography'),
        ('Form IV', 'Mathematics'), ('Form IV', 'English'), ('Form IV', 'Kiswahili'), ('Form IV', 'Biology'),
        ('Form IV', 'Chemistry'), ('Form IV', 'Physics'), ('Form IV', 'History'), ('Form IV', 'Geography'),
        ('Form V', 'Mathematics'), ('Form V', 'English'), ('Form V', 'Kiswahili'), ('Form V', 'Biology'),
        ('Form V', 'Chemistry'), ('Form V', 'Physics'), ('Form V', 'History'), ('Form V', 'Geography'),
        ('Form VI', 'Mathematics'), ('Form VI', 'English'), ('Form VI', 'Kiswahili'), ('Form VI', 'Biology'),
        ('Form VI', 'Chemistry'), ('Form VI', 'Physics'), ('Form VI', 'History'), ('Form VI', 'Geography'),
    ]
    for form, sub in default_subjects:
        c.execute("INSERT OR IGNORE INTO subjects (form, subject_name) VALUES (?, ?)", (form, sub))
    
    conn.commit()
    conn.close()

init_db()

def generate_token(user_id, role):
    payload = {
        'user_id': user_id,
        'role': role,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }
    token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')
    return token

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token missing!'}), 401
        try:
            token = token.split(' ')[1] if ' ' in token else token
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            request.user = data
        except:
            return jsonify({'message': 'Invalid token!'}), 401
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/gallery')
def gallery_page():
    return render_template('gallery.html')

@app.route('/announcements')
def announcements_page():
    return render_template('announcements.html')

@app.route('/apply')
def apply_page():
    return render_template('application.html')

@app.route('/results')
def results_page():
    return render_template('results.html')

@app.route('/admin/login')
def admin_login_page():
    return render_template('admin_login.html')

@app.route('/staff/login')
def staff_login_page():
    return render_template('staff_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/staff/dashboard')
def staff_dashboard():
    return render_template('staff_dashboard.html')

@app.route('/api/admin/auth', methods=['POST'])
def admin_auth():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    conn = sqlite3.connect('school_management.db')
    c = conn.cursor()
    c.execute("SELECT id, password FROM admins WHERE username=?", (username,))
    admin = c.fetchone()
    conn.close()
    if admin and check_password_hash(admin[1], password):
        token = generate_token(admin[0], 'admin')
        return jsonify({'token': token, 'role': 'admin'})
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/staff/auth', methods=['POST'])
def staff_auth():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    conn = sqlite3.connect('school_management.db')
    c = conn.cursor()
    c.execute("SELECT id, password FROM staff WHERE username=?", (username,))
    staff = c.fetchone()
    conn.close()
    if staff and check_password_hash(staff[1], password):
        token = generate_token(staff[0], 'staff')
        return jsonify({'token': token, 'role': 'staff'})
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/apply', methods=['POST'])
def submit_application():
    data = request.json
    conn = sqlite3.connect('school_management.db')
    c = conn.cursor()
    c.execute('''INSERT INTO applications 
        (student_name, parent_name, class_level, region, phone, email, gender)
        VALUES (?,?,?,?,?,?,?)''',
        (data['student_name'], data['parent_name'], data['class_level'],
         data['region'], data['phone'], data.get('email', ''), data['gender']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Application submitted successfully!'})

@app.route('/api/applications', methods=['GET'])
@token_required
def get_applications():
    conn = sqlite3.connect('school_management.db')
    c = conn.cursor()
    c.execute("SELECT id, student_name, parent_name, class_level, region, phone, email, gender, status, applied_at FROM applications ORDER BY applied_at DESC")
    apps = c.fetchall()
    conn.close()
    apps_list = [{'id': a[0], 'student_name': a[1], 'parent_name': a[2], 'class_level': a[3], 'region': a[4],
                  'phone': a[5], 'email': a[6], 'gender': a[7], 'status': a[8], 'applied_at': a[9]} for a in apps]
    return jsonify(apps_list)

@app.route('/api/gallery', methods=['GET'])
def get_gallery():
    conn = sqlite3.connect('school_management.db')
    c = conn.cursor()
    c.execute("SELECT id, image_path, description FROM gallery ORDER BY uploaded_at DESC")
    images = c.fetchall()
    conn.close()
    return jsonify([{'id': i[0], 'path': i[1], 'description': i[2]} for i in images])

@app.route('/api/gallery/upload', methods=['POST'])
@token_required
def upload_gallery():
    if 'image' not in request.files:
        return jsonify({'error': 'No image file'}), 400
    file = request.files['image']
    description = request.form.get('description', '')
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join('gallery', filename)
        full_path = os.path.join(app.config['UPLOAD_FOLDER'], filepath)
        file.save(full_path)
        db_path = f'/static/uploads/{filepath}'
        conn = sqlite3.connect('school_management.db')
        c = conn.cursor()
        c.execute("INSERT INTO gallery (image_path, description) VALUES (?, ?)", (db_path, description))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Uploaded successfully', 'path': db_path})
    return jsonify({'error': 'Invalid file'}), 400

@app.route('/api/gallery/<int:img_id>', methods=['DELETE'])
@token_required
def delete_gallery(img_id):
    conn = sqlite3.connect('school_management.db')
    c = conn.cursor()
    c.execute("SELECT image_path FROM gallery WHERE id=?", (img_id,))
    img = c.fetchone()
    if img:
        path = img[0].replace('/static/uploads/', '')
        full_path = os.path.join(app.config['UPLOAD_FOLDER'], path)
        if os.path.exists(full_path):
            os.remove(full_path)
        c.execute("DELETE FROM gallery WHERE id=?", (img_id,))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Deleted'})
    conn.close()
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/announcements', methods=['GET'])
def get_announcements():
    conn = sqlite3.connect('school_management.db')
    c = conn.cursor()
    c.execute("SELECT id, title, content, image, created_at FROM announcements ORDER BY created_at DESC")
    anns = c.fetchall()
    conn.close()
    return jsonify([{'id': a[0], 'title': a[1], 'content': a[2], 'image': a[3], 'created_at': a[4]} for a in anns])

@app.route('/api/announcements', methods=['POST'])
@token_required
def add_announcement():
    data = request.json
    conn = sqlite3.connect('school_management.db')
    c = conn.cursor()
    c.execute("INSERT INTO announcements (title, content, image) VALUES (?, ?, ?)", 
              (data['title'], data['content'], data.get('image', '')))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Announcement added'})

@app.route('/api/announcements/<int:ann_id>', methods=['PUT'])
@token_required
def edit_announcement(ann_id):
    data = request.json
    conn = sqlite3.connect('school_management.db')
    c = conn.cursor()
    c.execute("UPDATE announcements SET title=?, content=?, image=? WHERE id=?", 
              (data['title'], data['content'], data.get('image', ''), ann_id))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Updated'})

@app.route('/api/announcements/<int:ann_id>', methods=['DELETE'])
@token_required
def delete_announcement(ann_id):
    conn = sqlite3.connect('school_management.db')
    c = conn.cursor()
    c.execute("DELETE FROM announcements WHERE id=?", (ann_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Deleted'})

@app.route('/api/students', methods=['GET'])
@token_required
def get_students():
    conn = sqlite3.connect('school_management.db')
    c = conn.cursor()
    c.execute("SELECT id, index_number, name, class_level FROM students")
    students = c.fetchall()
    conn.close()
    return jsonify([{'id': s[0], 'index_number': s[1], 'name': s[2], 'class_level': s[3]} for s in students])

@app.route('/api/students', methods=['POST'])
@token_required
def add_student():
    data = request.json
    conn = sqlite3.connect('school_management.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO students (index_number, name, parent_name, class_level, region, phone, email, gender) VALUES (?,?,?,?,?,?,?,?)",
                  (data['index_number'], data['name'], data.get('parent_name',''), data['class_level'], data.get('region',''), data.get('phone',''), data.get('email',''), data.get('gender','')))
        conn.commit()
        return jsonify({'message': 'Student added'})
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Index number exists'}), 400
    finally:
        conn.close()

@app.route('/api/results', methods=['POST'])
@token_required
def add_result():
    data = request.json
    marks = data.get('marks', {})
    total = sum(marks.values())
    average = total / len(marks) if marks else 0
    division = compute_division(average)
    conn = sqlite3.connect('school_management.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM results WHERE exam_type=? AND form=? AND year=? AND total_marks > ?",
              (data['exam_type'], data['form'], data['year'], total))
    position = c.fetchone()[0] + 1
    c.execute('''INSERT INTO results 
        (student_id, exam_type, form, term, year, marks_json, total_marks, average, division, position)
        VALUES (?,?,?,?,?,?,?,?,?,?)''',
        (data['student_id'], data['exam_type'], data['form'], data.get('term',''), data['year'],
         json.dumps(marks), total, average, division, position))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Result added', 'position': position, 'division': division})

@app.route('/api/results/student/<index_number>', methods=['GET'])
def get_student_results(index_number):
    conn = sqlite3.connect('school_management.db')
    c = conn.cursor()
    c.execute("SELECT id, name, class_level FROM students WHERE index_number=?", (index_number,))
    student = c.fetchone()
    if not student:
        conn.close()
        return jsonify({'error': 'Student not found'}), 404
    c.execute("SELECT id, exam_type, form, term, year, marks_json, total_marks, average, division, position, created_at FROM results WHERE student_id=? ORDER BY year DESC, created_at DESC", (student[0],))
    results = c.fetchall()
    conn.close()
    results_list = []
    for r in results:
        results_list.append({
            'id': r[0], 'exam_type': r[1], 'form': r[2], 'term': r[3], 'year': r[4],
            'marks': json.loads(r[5]), 'total': r[6], 'average': r[7], 'division': r[8],
            'position': r[9], 'date': r[10]
        })
    return jsonify({'student': {'id': student[0], 'name': student[1], 'index': index_number, 'class': student[2]}, 'results': results_list})

@app.route('/api/results/<int:result_id>', methods=['PUT'])
@token_required
def edit_result(result_id):
    data = request.json
    marks = data.get('marks', {})
    total = sum(marks.values())
    average = total / len(marks) if marks else 0
    division = compute_division(average)
    conn = sqlite3.connect('school_management.db')
    c = conn.cursor()
    c.execute("UPDATE results SET marks_json=?, total_marks=?, average=?, division=? WHERE id=?", 
              (json.dumps(marks), total, average, division, result_id))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Result updated'})

def compute_division(average):
    if average >= 80:
        return 'I'
    elif average >= 65:
        return 'II'
    elif average >= 45:
        return 'III'
    elif average >= 30:
        return 'IV'
    else:
        return '0'

@app.route('/api/ai_comment/<int:result_id>', methods=['GET'])
def ai_comment(result_id):
    conn = sqlite3.connect('school_management.db')
    c = conn.cursor()
    c.execute("SELECT marks_json, average, student_id FROM results WHERE id=?", (result_id,))
    res = c.fetchone()
    if not res:
        conn.close()
        return jsonify({'error': 'Not found'}), 404
    marks = json.loads(res[0])
    avg = res[1]
    weak_subjects = [sub for sub, mark in marks.items() if mark < 50]
    if avg >= 85:
        comment = "Excellent performance! Keep up the outstanding dedication."
    elif avg >= 70:
        comment = "Very good progress. You're doing well, continue striving for excellence."
    elif avg >= 50:
        comment = "Good effort. With more focus you can achieve higher scores."
    else:
        comment = "Needs improvement. Let's work harder."
    if weak_subjects:
        advice = f"Focus more on: {', '.join(weak_subjects[:3])}."
    else:
        advice = "Great job balancing all subjects!"
    final_comment = f"{comment} {advice}"
    return jsonify({'ai_comment': final_comment, 'weak_subjects': weak_subjects})

@app.route('/api/comments', methods=['POST'])
def add_comment():
    data = request.json
    conn = sqlite3.connect('school_management.db')
    c = conn.cursor()
    c.execute("INSERT INTO comments (result_id, student_index, comment, suggestion) VALUES (?,?,?,?)",
              (data.get('result_id'), data.get('student_index'), data['comment'], data.get('suggestion','')))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Comment added'})

@app.route('/api/comments', methods=['GET'])
@token_required
def get_all_comments():
    conn = sqlite3.connect('school_management.db')
    c = conn.cursor()
    c.execute("SELECT id, result_id, student_index, comment, suggestion, admin_reply, created_at FROM comments ORDER BY created_at DESC")
    comments = c.fetchall()
    conn.close()
    return jsonify([{'id': c[0], 'result_id': c[1], 'student_index': c[2], 'comment': c[3], 'suggestion': c[4], 'admin_reply': c[5], 'date': c[6]} for c in comments])

@app.route('/api/comments/<int:comment_id>/reply', methods=['POST'])
@token_required
def reply_comment(comment_id):
    data = request.json
    conn = sqlite3.connect('school_management.db')
    c = conn.cursor()
    c.execute("UPDATE comments SET admin_reply=? WHERE id=?", (data['reply'], comment_id))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Reply added'})

@app.route('/static/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory('static/uploads', filename)

@app.route('/api/subjects', methods=['GET'])
de
