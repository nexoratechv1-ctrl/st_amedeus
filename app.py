import os, sqlite3, json, jwt, datetime
from flask import Flask, render_template, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-2024'

def init_db():
    conn = sqlite3.connect('results.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY, index_number TEXT UNIQUE, full_name TEXT, class_level TEXT, stream TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS exam_types (id INTEGER PRIMARY KEY, exam_name TEXT UNIQUE, year INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS streams (id INTEGER PRIMARY KEY, class_level TEXT, stream_name TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS results (id INTEGER PRIMARY KEY, student_id INTEGER, index_number TEXT, student_name TEXT, class_level TEXT, stream TEXT, exam_name TEXT, exam_year INTEGER, civics REAL, history REAL, geography REAL, kiswahili REAL, english REAL, mathematics REAL, biology REAL, chemistry REAL, physics REAL, bmath REAL, total_marks REAL, average_points REAL, division TEXT, position INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS suggestions (id INTEGER PRIMARY KEY, parent_name TEXT, student_index TEXT, suggestion TEXT, reply TEXT, is_replied INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT)''')
    
    admin_pass = generate_password_hash('admin123')
    staff_pass = generate_password_hash('staff123')
    c.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES ('admin', ?, 'admin')", (admin_pass,))
    c.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES ('staff', ?, 'staff')", (staff_pass,))
    
    exams = ['FTNA', 'CSEE', 'Terminal', 'Midterm', 'Mock']
    for e in exams:
        c.execute("INSERT OR IGNORE INTO exam_types (exam_name, year) VALUES (?, 2024)", (e,))
    
    streams = [('Form I','A'),('Form I','B'),('Form II','A'),('Form II','B'),('Form III','A'),('Form III','B'),('Form IV','A'),('Form IV','B')]
    for cls, st in streams:
        c.execute("INSERT OR IGNORE INTO streams (class_level, stream_name) VALUES (?, ?)", (cls, st))
    
    conn.commit()
    conn.close()

init_db()

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token: return jsonify({'message': 'Token missing'}), 401
        try:
            token = token.split(' ')[1] if ' ' in token else token
            request.user = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        except: return jsonify({'message': 'Invalid token'}), 401
        return f(*args, **kwargs)
    return decorated

def calc_total_division(c,h,g,k,e,m,bio,che,phy,bm):
    marks = [c,h,g,k,e,m,bio,che,phy,bm]
    total = sum([x for x in marks if x])
    count = len([x for x in marks if x])
    avg = total / count if count > 0 else 0
    div = 'I' if avg >= 80 else 'I' if avg >= 65 else 'II' if avg >= 50 else 'III' if avg >= 40 else 'IV'
    return total, avg, div

@app.route('/')
def index(): return render_template('index.html')
@app.route('/admin')
def admin(): return render_template('admin.html')
@app.route('/staff')
def staff(): return render_template('staff.html')

@app.route('/api/auth', methods=['POST'])
def auth():
    data = request.json
    conn = sqlite3.connect('results.db')
    user = conn.cursor().execute("SELECT password, role FROM users WHERE username=?", (data.get('username'),)).fetchone()
    conn.close()
    if user and check_password_hash(user[0], data.get('password')):
        token = jwt.encode({'role': user[1], 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)}, app.config['SECRET_KEY'])
        return jsonify({'token': token, 'role': user[1]})
    return jsonify({'error': 'Invalid'}), 401

@app.route('/api/students', methods=['GET','POST'])
@token_required
def students():
    conn = sqlite3.connect('results.db')
    c = conn.cursor()
    if request.method == 'POST':
        data = request.json
        c.execute("INSERT OR REPLACE INTO students (index_number, full_name, class_level, stream) VALUES (?,?,?,?)", (data['index_number'], data['full_name'], data['class_level'], data['stream']))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Student saved'})
    else:
        cls = request.args.get('class_level')
        stream = request.args.get('stream')
        if cls and stream:
            students = c.execute("SELECT id, index_number, full_name, class_level, stream FROM students WHERE class_level=? AND stream=?", (cls, stream)).fetchall()
        else:
            students = c.execute("SELECT id, index_number, full_name, class_level, stream FROM students").fetchall()
        conn.close()
        return jsonify([{'id':s[0],'index_number':s[1],'full_name':s[2],'class_level':s[3],'stream':s[4]} for s in students])

@app.route('/api/exam-types', methods=['GET'])
def exam_types():
    conn = sqlite3.connect('results.db')
    exams = conn.cursor().execute("SELECT id, exam_name, year FROM exam_types ORDER BY year DESC").fetchall()
    conn.close()
    return jsonify([{'id':e[0],'exam_name':e[1],'year':e[2]} for e in exams])

@app.route('/api/streams', methods=['GET'])
def streams_list():
    conn = sqlite3.connect('results.db')
    streams = conn.cursor().execute("SELECT class_level, stream_name FROM streams ORDER BY class_level").fetchall()
    conn.close()
    return jsonify([{'class_level':s[0],'stream_name':s[1]} for s in streams])

@app.route('/api/results', methods=['GET','POST'])
@token_required
def results():
    conn = sqlite3.connect('results.db')
    c = conn.cursor()
    if request.method == 'GET':
        cls = request.args.get('class_level')
        stream = request.args.get('stream')
        exam = request.args.get('exam_name')
        year = request.args.get('exam_year')
        data = c.execute("SELECT id, index_number, student_name, civics, history, geography, kiswahili, english, mathematics, biology, chemistry, physics, bmath, total_marks, average_points, division, position FROM results WHERE class_level=? AND stream=? AND exam_name=? AND exam_year=?", (cls, stream, exam, year)).fetchall()
        conn.close()
        return jsonify([{'id':r[0],'index_number':r[1],'student_name':r[2],'civics':r[3],'history':r[4],'geography':r[5],'kiswahili':r[6],'english':r[7],'mathematics':r[8],'biology':r[9],'chemistry':r[10],'physics':r[11],'bmath':r[12],'total_marks':r[13],'average_points':r[14],'division':r[15],'position':r[16]} for r in data])
    else:
        data = request.json
        for s in data['students']:
            total, avg, div = calc_total_division(s.get('civics'), s.get('history'), s.get('geography'), s.get('kiswahili'), s.get('english'), s.get('mathematics'), s.get('biology'), s.get('chemistry'), s.get('physics'), s.get('bmath'))
            existing = c.execute("SELECT id FROM results WHERE index_number=? AND exam_name=? AND exam_year=?", (s['index_number'], data['exam_name'], data['exam_year'])).fetchone()
            if existing:
                c.execute("UPDATE results SET civics=?, history=?, geography=?, kiswahili=?, english=?, mathematics=?, biology=?, chemistry=?, physics=?, bmath=?, total_marks=?, average_points=?, division=? WHERE id=?", (s.get('civics'), s.get('history'), s.get('geography'), s.get('kiswahili'), s.get('english'), s.get('mathematics'), s.get('biology'), s.get('chemistry'), s.get('physics'), s.get('bmath'), total, avg, div, existing[0]))
            else:
                c.execute("INSERT INTO results (index_number, student_name, class_level, stream, exam_name, exam_year, civics, history, geography, kiswahili, english, mathematics, biology, chemistry, physics, bmath, total_marks, average_points, division) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (s['index_number'], s['student_name'], data['class_level'], data['stream'], data['exam_name'], data['exam_year'], s.get('civics'), s.get('history'), s.get('geography'), s.get('kiswahili'), s.get('english'), s.get('mathematics'), s.get('biology'), s.get('chemistry'), s.get('physics'), s.get('bmath'), total, avg, div))
        # Update positions
        all_res = c.execute("SELECT id, total_marks FROM results WHERE exam_name=? AND exam_year=? AND class_level=? AND stream=? ORDER BY total_marks DESC", (data['exam_name'], data['exam_year'], data['class_level'], data['stream'])).fetchall()
        for pos, r in enumerate(all_res, 1):
            c.execute("UPDATE results SET position=? WHERE id=?", (pos, r[0]))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Saved'})

@app.route('/api/parent/results', methods=['GET'])
def parent_results():
    idx = request.args.get('index_number')
    exam = request.args.get('exam_name')
    year = request.args.get('exam_year')
    cls = request.args.get('class_level')
    conn = sqlite3.connect('results.db')
    c = conn.cursor()
    student = c.execute("SELECT full_name, class_level, stream FROM students WHERE index_number=?", (idx,)).fetchone()
    if not student:
        conn.close()
        return jsonify({'error': 'Student not found'}), 404
    result = c.execute("SELECT civics,history,geography,kiswahili,english,mathematics,biology,chemistry,physics,bmath,total_marks,average_points,division,position FROM results WHERE index_number=? AND exam_name=? AND exam_year=? AND class_level=?", (idx, exam, year, cls)).fetchone()
    conn.close()
    if not result:
        return jsonify({'error': 'No results found'}), 404
    subjects = {'CIVICS':result[0],'HISTORY':result[1],'GEOGRAPHY':result[2],'KISWAHILI':result[3],'ENGLISH':result[4],'MATHEMATICS':result[5],'BIOLOGY':result[6],'CHEMISTRY':result[7],'PHYSICS':result[8],'B/MATH':result[9]}
    avg = result[11] or 0
    weak = [s for s,m in subjects.items() if m and m < 50]
    if avg >= 80: comment = "EXCELLENT! Keep it up."
    elif avg >= 65: comment = "VERY GOOD! Well done."
    elif avg >= 50: comment = "GOOD! Room for improvement."
    elif avg >= 40: comment = "SATISFACTORY. Work harder."
    else: comment = "NEEDS IMPROVEMENT. Seek help."
    advice = f"Focus on: {', '.join(weak[:3])}" if weak else "Great job in all subjects!"
    return jsonify({'student':{'full_name':student[0],'index_number':idx,'class_level':student[1],'stream':student[2]},'exam':{'name':exam,'year':year},'subjects':subjects,'total_marks':result[10],'average_points':result[11],'division':result[12],'position':result[13],'ai_comment':f"{comment}\n{advice}"})

@app.route('/api/suggestions', methods=['GET','POST'])
def suggestions():
    conn = sqlite3.connect('results.db')
    c = conn.cursor()
    if request.method == 'POST':
        data = request.json
        c.execute("INSERT INTO suggestions (parent_name, student_index, suggestion) VALUES (?,?,?)", (data['parent_name'], data['student_index'], data['suggestion']))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Sent'})
    else:
        token = request.headers.get('Authorization')
        if token:
            sugg = c.execute("SELECT id, parent_name, student_index, suggestion, reply, created_at FROM suggestions ORDER BY created_at DESC").fetchall()
            conn.close()
            return jsonify([{'id':s[0],'parent_name':s[1],'student_index':s[2],'suggestion':s[3],'reply':s[4],'date':s[5]} for s in sugg])
        conn.close()
        return jsonify([])

@app.route('/api/suggestions/<int:sid>/reply', methods=['POST'])
@token_required
def reply_suggestion(sid):
    data = request.json
    conn = sqlite3.connect('results.db')
    conn.cursor().execute("UPDATE suggestions SET reply=?, is_replied=1 WHERE id=?", (data['reply'], sid))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Replied'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
