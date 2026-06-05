import os, sqlite3, json, jwt, datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'gallery'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'announcements'), exist_ok=True)

def allowed_file(f): return '.' in f and f.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
    c = sqlite3.connect('school_management.db').cursor()
    c.execute('CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY AUTOINCREMENT,index_number TEXT UNIQUE,name TEXT,parent_name TEXT,class_level TEXT,region TEXT,phone TEXT,email TEXT,gender TEXT,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
    c.execute('CREATE TABLE IF NOT EXISTS results(id INTEGER PRIMARY KEY AUTOINCREMENT,student_id INTEGER,exam_type TEXT,form TEXT,term TEXT,year INTEGER,marks_json TEXT,total_marks REAL,average REAL,division TEXT,position INTEGER,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(student_id) REFERENCES students(id))')
    c.execute('CREATE TABLE IF NOT EXISTS applications(id INTEGER PRIMARY KEY AUTOINCREMENT,student_name TEXT,parent_name TEXT,class_level TEXT,region TEXT,phone TEXT,email TEXT,gender TEXT,status TEXT DEFAULT "pending",applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
    c.execute('CREATE TABLE IF NOT EXISTS announcements(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT,content TEXT,image TEXT,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
    c.execute('CREATE TABLE IF NOT EXISTS gallery(id INTEGER PRIMARY KEY AUTOINCREMENT,image_path TEXT,description TEXT,uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
    c.execute('CREATE TABLE IF NOT EXISTS comments(id INTEGER PRIMARY KEY AUTOINCREMENT,result_id INTEGER,student_index TEXT,comment TEXT,suggestion TEXT,admin_reply TEXT,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
    c.execute('CREATE TABLE IF NOT EXISTS admins(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT UNIQUE,password TEXT,role TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS staff(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT UNIQUE,password TEXT,full_name TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS subjects(id INTEGER PRIMARY KEY AUTOINCREMENT,form TEXT,subject_name TEXT)')
    
    pwd = generate_password_hash('amedeus wireless.com')
    c.execute("INSERT OR IGNORE INTO admins (username, password, role) VALUES (?, ?, ?)", ('admin', pwd, 'super_admin'))
    c.execute("INSERT OR IGNORE INTO staff (username, password, full_name) VALUES (?, ?, ?)", ('staff', pwd, 'Default Staff'))
    
    for f in ['Form I','Form II','Form III','Form IV','Form V','Form VI']:
        for s in ['Mathematics','English','Kiswahili','Biology','Chemistry','Physics','History','Geography']:
            c.execute("INSERT OR IGNORE INTO subjects (form, subject_name) VALUES (?, ?)", (f, s))
    c.connection.commit()
    c.connection.close()

init_db()

def token_required(f):
    @wraps(f)
    def dec(*args,**kwargs):
        t = request.headers.get('Authorization')
        if not t: return jsonify({'message':'Token missing'}),401
        try: request.user = jwt.decode(t.split(' ')[1] if ' ' in t else t, app.config['SECRET_KEY'], algorithms=['HS256'])
        except: return jsonify({'message':'Invalid token'}),401
        return f(*args,**kwargs)
    return dec

def division(a): return 'I' if a>=80 else 'II' if a>=65 else 'III' if a>=45 else 'IV' if a>=30 else '0'

@app.route('/');app.route('/gallery');app.route('/announcements');app.route('/apply');app.route('/results')
@app.route('/admin/login');app.route('/staff/login');app.route('/admin/dashboard');app.route('/staff/dashboard')
def render_pages():
    return render_template(request.endpoint+'.html' if request.endpoint not in ['home'] else 'index.html')

@app.route('/api/admin/auth', methods=['POST'])
def admin_auth():
    d=request.json
    c=sqlite3.connect('school_management.db').cursor()
    a=c.execute("SELECT id,password FROM admins WHERE username=?",(d.get('username'),)).fetchone()
    c.connection.close()
    if a and check_password_hash(a[1],d.get('password')):
        return jsonify({'token':jwt.encode({'user_id':a[0],'role':'admin','exp':datetime.datetime.utcnow()+datetime.timedelta(hours=24)},app.config['SECRET_KEY'],algorithm='HS256'),'role':'admin'})
    return jsonify({'error':'Invalid'}),401

@app.route('/api/staff/auth', methods=['POST'])
def staff_auth():
    d=request.json
    c=sqlite3.connect('school_management.db').cursor()
    s=c.execute("SELECT id,password FROM staff WHERE username=?",(d.get('username'),)).fetchone()
    c.connection.close()
    if s and check_password_hash(s[1],d.get('password')):
        return jsonify({'token':jwt.encode({'user_id':s[0],'role':'staff','exp':datetime.datetime.utcnow()+datetime.timedelta(hours=24)},app.config['SECRET_KEY'],algorithm='HS256'),'role':'staff'})
    return jsonify({'error':'Invalid'}),401

@app.route('/api/apply', methods=['POST'])
def apply():
    d=request.json
    c=sqlite3.connect('school_management.db').cursor()
    c.execute("INSERT INTO applications (student_name,parent_name,class_level,region,phone,email,gender) VALUES (?,?,?,?,?,?,?)",(d['student_name'],d['parent_name'],d['class_level'],d['region'],d['phone'],d.get('email',''),d['gender']))
    c.connection.commit()
    c.connection.close()
    return jsonify({'message':'Application submitted'})

@app.route('/api/applications', methods=['GET'])
@token_required
def get_apps():
    c=sqlite3.connect('school_management.db').cursor()
    a=c.execute("SELECT id,student_name,parent_name,class_level,region,phone,email,gender,status,applied_at FROM applications ORDER BY applied_at DESC").fetchall()
    c.connection.close()
    return jsonify([{'id':x[0],'student_name':x[1],'parent_name':x[2],'class_level':x[3],'region':x[4],'phone':x[5],'email':x[6],'gender':x[7],'status':x[8],'applied_at':x[9]} for x in a])

@app.route('/api/gallery', methods=['GET'])
def get_gallery():
    c=sqlite3.connect('school_management.db').cursor()
    i=c.execute("SELECT id,image_path,description FROM gallery ORDER BY uploaded_at DESC").fetchall()
    c.connection.close()
    return jsonify([{'id':x[0],'path':x[1],'description':x[2]} for x in i])

@app.route('/api/gallery/upload', methods=['POST'])
@token_required
def upload_gallery():
    if 'image' not in request.files: return jsonify({'error':'No file'}),400
    f=request.files['image']
    desc=request.form.get('description','')
    if f and allowed_file(f.filename):
        fn=f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(f.filename)}"
        fp=os.path.join(app.config['UPLOAD_FOLDER'],'gallery',fn)
        f.save(fp)
        dbp=f'/static/uploads/gallery/{fn}'
        c=sqlite3.connect('school_management.db').cursor()
        c.execute("INSERT INTO gallery (image_path,description) VALUES (?,?)",(dbp,desc))
        c.connection.commit()
        c.connection.close()
        return jsonify({'message':'Uploaded','path':dbp})
    return jsonify({'error':'Invalid file'}),400

@app.route('/api/gallery/<int:iid>', methods=['DELETE'])
@token_required
def del_gallery(iid):
    c=sqlite3.connect('school_management.db').cursor()
    img=c.execute("SELECT image_path FROM gallery WHERE id=?",(iid,)).fetchone()
    if img:
        p=img[0].replace('/static/uploads/','')
        fp=os.path.join(app.config['UPLOAD_FOLDER'],p)
        if os.path.exists(fp): os.remove(fp)
        c.execute("DELETE FROM gallery WHERE id=?",(iid,))
        c.connection.commit()
        c.connection.close()
        return jsonify({'message':'Deleted'})
    c.connection.close()
    return jsonify({'error':'Not found'}),404

@app.route('/api/announcements', methods=['GET'])
def get_ann():
    c=sqlite3.connect('school_management.db').cursor()
    a=c.execute("SELECT id,title,content,image,created_at FROM announcements ORDER BY created_at DESC").fetchall()
    c.connection.close()
    return jsonify([{'id':x[0],'title':x[1],'content':x[2],'image':x[3],'created_at':x[4]} for x in a])

@app.route('/api/announcements', methods=['POST'])
@token_required
def add_ann():
    d=request.json
    c=sqlite3.connect('school_management.db').cursor()
    c.execute("INSERT INTO announcements (title,content,image) VALUES (?,?,?)",(d['title'],d['content'],d.get('image','')))
    c.connection.commit()
    c.connection.close()
    return jsonify({'message':'Added'})

@app.route('/api/announcements/<int:aid>', methods=['PUT','DELETE'])
@token_required
def edit_del_ann(aid):
    c=sqlite3.connect('school_management.db').cursor()
    if request.method=='DELETE':
        c.execute("DELETE FROM announcements WHERE id=?",(aid,))
    else:
        d=request.json
        c.execute("UPDATE announcements SET title=?,content=?,image=? WHERE id=?",(d['title'],d['content'],d.get('image',''),aid))
    c.connection.commit()
    c.connection.close()
    return jsonify({'message':'Done'})

@app.route('/api/students', methods=['GET'])
@token_required
def get_students():
    c=sqlite3.connect('school_management.db').cursor()
    s=c.execute("SELECT id,index_number,name,class_level FROM students").fetchall()
    c.connection.close()
    return jsonify([{'id':x[0],'index_number':x[1],'name':x[2],'class_level':x[3]} for x in s])

@app.route('/api/students', methods=['POST'])
@token_required
def add_student():
    d=request.json
    c=sqlite3.connect('school_management.db').cursor()
    try:
        c.execute("INSERT INTO students (index_number,name,parent_name,class_level,region,phone,email,gender) VALUES (?,?,?,?,?,?,?,?)",(d['index_number'],d['name'],d.get('parent_name',''),d['class_level'],d.get('region',''),d.get('phone',''),d.get('email',''),d.get('gender','')))
        c.connection.commit()
        return jsonify({'message':'Student added'})
    except: return jsonify({'error':'Index exists'}),400
    finally: c.connection.close()

@app.route('/api/results', methods=['POST'])
@token_required
def add_result():
    d=request.json
    m=d.get('marks',{})
    total=sum(m.values())
    avg=total/len(m) if m else 0
    div=division(avg)
    c=sqlite3.connect('school_management.db').cursor()
    pos=c.execute("SELECT COUNT(*) FROM results WHERE exam_type=? AND form=? AND year=? AND total_marks>?",(d['exam_type'],d['form'],d['year'],total)).fetchone()[0]+1
    c.execute("INSERT INTO results (student_id,exam_type,form,term,year,marks_json,total_marks,average,division,position) VALUES (?,?,?,?,?,?,?,?,?,?)",(d['student_id'],d['exam_type'],d['form'],d.get('term',''),d['year'],json.dumps(m),total,avg,div,pos))
    c.connection.commit()
    c.connection.close()
    return jsonify({'message':'Result added','position':pos,'division':div})

@app.route('/api/results/student/<idx>', methods=['GET'])
def get_results(idx):
    c=sqlite3.connect('school_management.db').cursor()
    s=c.execute("SELECT id,name,class_level FROM students WHERE index_number=?",(idx,)).fetchone()
    if not s: return jsonify({'error':'Not found'}),404
    r=c.execute("SELECT id,exam_type,form,term,year,marks_json,total_marks,average,division,position,created_at FROM results WHERE student_id=? ORDER BY year DESC",(s[0],)).fetchall()
    c.connection.close()
    return jsonify({'student':{'id':s[0],'name':s[1],'index':idx,'class':s[2]},'results':[{'id':x[0],'exam_type':x[1],'form':x[2],'term':x[3],'year':x[4],'marks':json.loads(x[5]),'total':x[6],'average':x[7],'division':x[8],'position':x[9],'date':x[10]} for x in r]})

@app.route('/api/ai_comment/<int:rid>', methods=['GET'])
def ai_comment(rid):
    c=sqlite3.connect('school_management.db').cursor()
    r=c.execute("SELECT marks_json,average FROM results WHERE id=?",(rid,)).fetchone()
    c.connection.close()
    if not r: return jsonify({'error':'Not found'}),404
    m=json.loads(r[0])
    weak=[s for s,mark in m.items() if mark<50]
    avg=r[1]
    com='Excellent! Keep it up.' if avg>=85 else 'Good progress.' if avg>=70 else 'Good effort.' if avg>=50 else 'Needs improvement.'
    adv=f' Focus on: {", ".join(weak[:3])}.' if weak else ' Great job in all subjects!'
    return jsonify({'ai_comment':com+adv,'weak_subjects':weak})

@app.route('/api/comments', methods=['GET','POST'])
def comments():
    c=sqlite3.connect('school_management.db').cursor()
    if request.method=='POST':
        d=request.json
        c.execute("INSERT INTO comments (result_id,student_index,comment,suggestion) VALUES (?,?,?,?)",(d.get('result_id'),d.get('student_index'),d['comment'],d.get('suggestion','')))
        c.connection.commit()
        c.connection.close()
        return jsonify({'message':'Comment added'})
    else:
        if not request.headers.get('Authorization'): return jsonify({'error':'Unauthorized'}),401
        cm=c.execute("SELECT id,result_id,student_index,comment,suggestion,admin_reply,created_at FROM comments ORDER BY created_at DESC").fetchall()
        c.connection.close()
        return jsonify([{'id':x[0],'result_id':x[1],'student_index':x[2],'comment':x[3],'suggestion':x[4],'admin_reply':x[5],'date':x[6]} for x in cm])

@app.route('/api/comments/<int:cid>/reply', methods=['POST'])
@token_required
def reply_comment(cid):
    c=sqlite3.connect('school_management.db').cursor()
    c.execute("UPDATE comments SET admin_reply=? WHERE id=?",(request.json['reply'],cid))
    c.connection.commit()
    c.connection.close()
    return jsonify({'message':'Reply added'})

@app.route('/static/uploads/<path:fn>')
def uploads(fn): return send_from_directory('static/uploads',fn)

@app.route('/api/subjects', methods=['GET'])
def get_subjects():
    c=sqlite3.connect('school_management.db').cursor()
    s=c.execute("SELECT form,subject_name FROM subjects").fetchall()
    c.connection.close()
    return jsonify([{'form':x[0],'subject_name':x[1]} for x in s])

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
