import os, sqlite3, json, jwt, datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-2024'

def init_db():
    conn = sqlite3.connect('results_system.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY AUTOINCREMENT, index_number TEXT UNIQUE NOT NULL, full_name TEXT NOT NULL, class_level TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS exam_types (id INTEGER PRIMARY KEY AUTOINCREMENT, exam_name TEXT UNIQUE, exam_code TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS results (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER, exam_name TEXT, class_level TEXT, term TEXT, year INTEGER, subject_name TEXT, marks REAL, total_marks REAL, average REAL, grade TEXT, division TEXT, position INTEGER, is_new INTEGER DEFAULT 1, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(student_id) REFERENCES students(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS announcements (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, student_index TEXT, sender_name TEXT, message TEXT, reply TEXT, is_replied INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, role TEXT, full_name TEXT)''')
    
    admin_pass = generate_password_hash('admin123')
    staff_pass = generate_password_hash('staff123')
    c.execute("INSERT OR IGNORE INTO users (username, password, role, full_name) VALUES (?, ?, ?, ?)", ('admin', admin_pass, 'admin', 'System Administrator'))
    c.execute("INSERT OR IGNORE INTO users (username, password, role, full_name) VALUES (?, ?, ?, ?)", ('staff', staff_pass, 'staff', 'School Staff'))
    
    exam_types = ['Opening Test', 'Midterm Exam', 'Terminal Exam', 'Monthly Exam', 'Mock Exam', 'Pre-National', 'FTNA', 'CSEE', 'Annual Exam']
    for exam in exam_types:
        c.execute("INSERT OR IGNORE INTO exam_types (exam_name, exam_code) VALUES (?, ?)", (exam, exam[:3].upper()))
    
    conn.commit()
    conn.close()

init_db()

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token missing!'}), 401
        try:
            token = token.split(' ')[1] if ' ' in token else token
            request.user = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        except:
            return jsonify({'message': 'Invalid token!'}), 401
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def index(): return render_template('index.html')
@app.route('/admin')
def admin(): return render_template('admin.html')
@app.route('/staff')
def staff(): return render_template('staff.html')

@app.route('/api/auth', methods=['POST'])
def auth():
    data = request.json
    conn = sqlite3.connect('results_system.db')
    c = conn.cursor()
    user = c.execute("SELECT id, password, role, full_name FROM users WHERE username=?", (data.get('username'),)).fetchone()
    conn.close()
    if user and check_password_hash(user[1], data.get('password')):
        token = jwt.encode({'id': user[0], 'role': user[2], 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)}, app.config['SECRET_KEY'])
        return jsonify({'token': token, 'role': user[2], 'full_name': user[3]})
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/students', methods=['GET', 'POST'])
@token_required
def manage_students():
    conn = sqlite3.connect('results_system.db')
    c = conn.cursor()
    if request.method == 'POST':
        data = request.json
        try:
            for student in data:
                c.execute("INSERT OR REPLACE INTO students (index_number, full_name, class_level) VALUES (?, ?, ?)", (student['index_number'], student['full_name'], student['class_level']))
            conn.commit()
            return jsonify({'message': 'Students saved successfully'})
        except Exception as e:
            return jsonify({'error': str(e)}), 400
    else:
        students = c.execute("SELECT id, index_number, full_name, class_level FROM students ORDER BY index_number").fetchall()
        conn.close()
        return jsonify([{'id': s[0], 'index_number': s[1], 'full_name': s[2], 'class_level': s[3]} for s in students])

@app.route('/api/exam-types', methods=['GET', 'POST', 'DELETE'])
@token_required
def manage_exam_types():
    conn = sqlite3.connect('results_system.db')
    c = conn.cursor()
    if request.method == 'POST':
        data = request.json
        c.execute("INSERT INTO exam_types (exam_name, exam_code) VALUES (?, ?)", (data['exam_name'], data.get('exam_code', '')))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Exam type added'})
    elif request.method == 'DELETE':
        exam_id = request.json.get('id')
        c.execute("DELETE FROM exam_types WHERE id=?", (exam_id,))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Exam type deleted'})
    else:
        exams = c.execute("SELECT id, exam_name, exam_code FROM exam_types ORDER BY exam_name").fetchall()
        conn.close()
        return jsonify([{'id': e[0], 'exam_name': e[1], 'exam_code': e[2]} for e in exams])

@app.route('/api/results/sheet', methods=['GET'])
@token_required
def get_results_sheet():
    exam_name = request.args.get('exam_name')
    class_level = request.args.get('class_level')
    term = request.args.get('term')
    year = request.args.get('year')
    subject_name = request.args.get('subject_name')
    conn = sqlite3.connect('results_system.db')
    c = conn.cursor()
    students = c.execute("SELECT id, index_number, full_name FROM students WHERE class_level=? ORDER BY index_number", (class_level,)).fetchall()
    results = []
    for student in students:
        mark_data = c.execute("SELECT marks FROM results WHERE student_id=? AND exam_name=? AND class_level=? AND term=? AND year=? AND subject_name=?", (student[0], exam_name, class_level, term, year, subject_name)).fetchone()
        marks = mark_data[0] if mark_data else ''
        results.append({'student_id': student[0], 'index_number': student[1], 'full_name': student[2], 'marks': marks})
    conn.close()
    return jsonify({'exam_name': exam_name, 'class_level': class_level, 'term': term, 'year': year, 'subject_name': subject_name, 'results': results})

@app.route('/api/results/bulk', methods=['POST'])
@token_required
def save_bulk_results():
    data = request.json
    conn = sqlite3.connect('results_system.db')
    c = conn.cursor()
    exam_name = data['exam_name']
    class_level = data['class_level']
    term = data['term']
    year = data['year']
    subject_name = data['subject_name']
    for result in data['results']:
        student_id = result['student_id']
        marks = result.get('marks', 0)
        existing = c.execute("SELECT id FROM results WHERE student_id=? AND exam_name=? AND class_level=? AND term=? AND year=? AND subject_name=?", (student_id, exam_name, class_level, term, year, subject_name)).fetchone()
        if existing:
            c.execute("UPDATE results SET marks=? WHERE id=?", (marks, existing[0]))
        else:
            c.execute("INSERT INTO results (student_id, exam_name, class_level, term, year, subject_name, marks, is_new) VALUES (?, ?, ?, ?, ?, ?, ?, 1)", (student_id, exam_name, class_level, term, year, subject_name, marks))
    students = c.execute("SELECT DISTINCT student_id FROM results WHERE exam_name=? AND class_level=? AND term=? AND year=?", (exam_name, class_level, term, year)).fetchall()
    for student in students:
        sid = student[0]
        marks_data = c.execute("SELECT subject_name, marks FROM results WHERE student_id=? AND exam_name=? AND class_level=? AND term=? AND year=?", (sid, exam_name, class_level, term, year)).fetchall()
        total = sum([m[1] for m in marks_data if m[1] > 0])
        count = len([m for m in marks_data if m[1] > 0])
        average = total / count if count > 0 else 0
        if average >= 80: grade = 'A'; division = 'I'
        elif average >= 70: grade = 'B'; division = 'I'
        elif average >= 60: grade = 'C'; division = 'II'
        elif average >= 50: grade = 'D'; division = 'III'
        elif average >= 40: grade = 'E'; division = 'IV'
        else: grade = 'F'; division = '0'
        c.execute("UPDATE results SET total_marks=?, average=?, grade=?, division=? WHERE student_id=? AND exam_name=? AND class_level=? AND term=? AND year=?", (total, average, grade, division, sid, exam_name, class_level, term, year))
    student_totals = c.execute("SELECT student_id, total_marks FROM results WHERE exam_name=? AND class_level=? AND term=? AND year=? GROUP BY student_id ORDER BY total_marks DESC", (exam_name, class_level, term, year)).fetchall()
    for pos, st in enumerate(student_totals, 1):
        c.execute("UPDATE results SET position=? WHERE student_id=? AND exam_name=? AND class_level=? AND term=? AND year=?", (pos, st[0], exam_name, class_level, term, year))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Results saved successfully!'})

@app.route('/api/student/results/<index_number>', methods=['GET'])
def get_student_results(index_number):
    conn = sqlite3.connect('results_system.db')
    c = conn.cursor()
    student = c.execute("SELECT id, index_number, full_name, class_level FROM students WHERE index_number=?", (index_number,)).fetchone()
    if not student:
        conn.close()
        return jsonify({'error': 'Student not found'}), 404
    results_data = c.execute("""SELECT DISTINCT exam_name, term, year, class_level, total_marks, average, grade, division, position, is_new, created_at FROM results WHERE student_id=? ORDER BY year DESC, created_at DESC""", (student[0],)).fetchall()
    exams = []
    for exam in results_data:
        subjects = c.execute("SELECT subject_name, marks FROM results WHERE student_id=? AND exam_name=? AND term=? AND year=?", (student[0], exam[0], exam[1], exam[2])).fetchall()
        exams.append({'exam_name': exam[0], 'term': exam[1], 'year': exam[2], 'class_level': exam[3], 'total_marks': exam[4], 'average': exam[5], 'grade': exam[6], 'division': exam[7], 'position': exam[8], 'is_new': exam[9], 'date': exam[10], 'subjects': [{'name': s[0], 'marks': s[1]} for s in subjects]})
    conn.close()
    if exams:
        latest = exams[0]
        avg = latest['average'] if latest['average'] else 0
        weak_subjects = [s['name'] for s in latest['subjects'] if s['marks'] and s['marks'] < 50]
        if avg >= 80: comment = "EXCELLENT PERFORMANCE! Keep up the outstanding dedication and hard work."
        elif avg >= 70: comment = "VERY GOOD PROGRESS! You are doing well. Continue striving for excellence."
        elif avg >= 60: comment = "GOOD EFFORT! Solid understanding shown. Aim higher next time."
        elif avg >= 50: comment = "SATISFACTORY. You need to put more effort, especially in weaker subjects."
        else: comment = "NEEDS SIGNIFICANT IMPROVEMENT. Seek help from teachers and improve study habits."
        if weak_subjects: advice = f"\n\nSPECIFIC ADVICE: Focus more on these subjects: {', '.join(weak_subjects[:3])}. Create a study timetable, consult teachers, practice past papers."
        else: advice = "\n\nGreat job balancing all subjects! Maintain your study routine."
        if len(exams) >= 2:
            prev_avg = exams[1]['average'] if exams[1]['average'] else 0
            if avg > prev_avg: trend = f"\n\nPERFORMANCE TREND: Your average has IMPROVED from {prev_avg:.1f}% to {avg:.1f}%! Keep building on this momentum."
            elif avg < prev_avg: trend = f"\n\nPERFORMANCE TREND: Your average has DROPPED from {prev_avg:.1f}% to {avg:.1f}%. Identify what went wrong and take corrective measures."
            else: trend = f"\n\nPERFORMANCE TREND: Your average has remained STABLE at {avg:.1f}%. Push harder to improve."
        else: trend = "\n\nFirst recorded exam. Use this as baseline to set higher goals."
        final_comment = comment + advice + trend
    else:
        final_comment = "No results available yet. Please check back after exams are released."
    return jsonify({'student': {'index_number': student[1], 'full_name': student[2], 'class_level': student[3]}, 'exams': exams, 'ai_comment': final_comment})

@app.route('/api/announcements', methods=['GET', 'POST'])
def announcements():
    conn = sqlite3.connect('results_system.db')
    c = conn.cursor()
    if request.method == 'POST':
        token = request.headers.get('Authorization')
        if not token: return jsonify({'error': 'Unauthorized'}), 401
        data = request.json
        c.execute("INSERT INTO announcements (title, content) VALUES (?, ?)", (data['title'], data['content']))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Announcement added'})
    else:
        anns = c.execute("SELECT id, title, content, created_at FROM announcements ORDER BY created_at DESC LIMIT 10").fetchall()
        conn.close()
        return jsonify([{'id': a[0], 'title': a[1], 'content': a[2], 'date': a[3]} for a in anns])

@app.route('/api/messages', methods=['GET', 'POST'])
def messages():
    conn = sqlite3.connect('results_system.db')
    c = conn.cursor()
    if request.method == 'POST':
        data = request.json
        c.execute("INSERT INTO messages (student_index, sender_name, message) VALUES (?, ?, ?)", (data['student_index'], data['sender_name'], data['message']))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Message sent successfully'})
    else:
        token = request.headers.get('Authorization')
        if token:
            msgs = c.execute("SELECT id, student_index, sender_name, message, reply, is_replied, created_at FROM messages ORDER BY created_at DESC").fetchall()
            conn.close()
            return jsonify([{'id': m[0], 'student_index': m[1], 'sender_name': m[2], 'message': m[3], 'reply': m[4], 'is_replied': m[5], 'date': m[6]} for m in msgs])
        else:
            student_index = request.args.get('student_index')
            if student_index:
                msgs = c.execute("SELECT id, message, reply, created_at FROM messages WHERE student_index=? ORDER BY created_at DESC", (student_index,)).fetchall()
                conn.close()
                return jsonify([{'id': m[0], 'message': m[1], 'reply': m[2], 'date': m[3]} for m in msgs])
            conn.close()
            return jsonify([])

@app.route('/api/messages/<int:msg_id>/reply', methods=['POST'])
@token_required
def reply_message(msg_id):
    data = request.json
    conn = sqlite3.connect('results_system.db')
    c = conn.cursor()
    c.execute("UPDATE messages SET reply=?, is_replied=1 WHERE id=?", (data['reply'], msg_id))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Reply sent'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
