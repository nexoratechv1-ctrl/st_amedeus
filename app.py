import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'st-amedeus-secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///school.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi', 'webm'}
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ------------------- MODELS (simplified but complete) -------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    def set_password(self, pwd): self.password_hash = generate_password_hash(pwd)
    def check_password(self, pwd): return check_password_hash(self.password_hash, pwd)

class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title, content, category = db.Column(db.String(200)), db.Column(db.Text), db.Column(db.String(50), default='news')
    event_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class StudentLifeMedia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title, description, media_type = db.Column(db.String(200)), db.Column(db.Text), db.Column(db.String(20), default='image')
    url = db.Column(db.String(500), nullable=False)
    order = db.Column(db.Integer, default=0)

class GalleryItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title, description, media_type = db.Column(db.String(200)), db.Column(db.Text), db.Column(db.String(20), default='image')
    url = db.Column(db.String(500), nullable=False)

class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name, email, phone, message = db.Column(db.String(100)), db.Column(db.String(100)), db.Column(db.String(20)), db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AdmissionApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name, parent_name, email, phone, date_of_birth = db.Column(db.String(100)), db.Column(db.String(100)), db.Column(db.String(100)), db.Column(db.String(20)), db.Column(db.String(50))
    previous_school, grade_applying, message = db.Column(db.String(200)), db.Column(db.String(50)), db.Column(db.Text)
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)

class ExamResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    index_number = db.Column(db.String(50), unique=True, nullable=False)
    student_name, exam_type, year, subjects, total_marks, division = db.Column(db.String(100)), db.Column(db.String(50)), db.Column(db.Integer), db.Column(db.Text), db.Column(db.Integer), db.Column(db.String(10))

class Suggestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content, category = db.Column(db.Text), db.Column(db.String(50), default='general')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Alumni(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name, graduation_year, current_occupation, story, image_url = db.Column(db.String(100)), db.Column(db.Integer), db.Column(db.String(200)), db.Column(db.Text), db.Column(db.String(300))
    is_featured = db.Column(db.Boolean, default=False)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title, description, location = db.Column(db.String(200)), db.Column(db.Text), db.Column(db.String(200))
    event_date = db.Column(db.DateTime, nullable=False)

class QuizQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    option_a, option_b, option_c, option_d = db.Column(db.String(200)), db.Column(db.String(200)), db.Column(db.String(200)), db.Column(db.String(200))
    correct_answer, explanation = db.Column(db.String(1)), db.Column(db.Text)

# ------------------- HELPERS -------------------
@login_manager.user_loader
def load_user(uid): return User.query.get(int(uid))

def admin_required(f):
    @wraps(f)
    def dec(*a, **kw):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Access denied', 'danger')
            return redirect(url_for('home'))
        return f(*a, **kw)
    return dec

@app.context_processor
def inject_user(): return dict(current_user=current_user)

# ------------------- PUBLIC ROUTES -------------------
@app.route('/')
def home():
    return render_template('index.html', announcements=Announcement.query.order_by(Announcement.created_at.desc()).limit(3).all())

@app.route('/about')
def about(): return render_template('about.html')
@app.route('/academics')
def academics(): return render_template('academics.html')
@app.route('/students-life')
def students_life(): return render_template('students_life.html', media_items=StudentLifeMedia.query.order_by(StudentLifeMedia.order).all())
@app.route('/news-events')
def news_events(): return render_template('news_events.html', announcements=Announcement.query.order_by(Announcement.created_at.desc()).all())
@app.route('/gallery')
def gallery(): return render_template('gallery.html', gallery_items=GalleryItem.query.order_by(GalleryItem.id.desc()).all())

@app.route('/admissions', methods=['GET','POST'])
def admissions():
    if request.method=='POST':
        a = AdmissionApplication(**{k: request.form.get(k) for k in ['full_name','parent_name','email','phone','date_of_birth','previous_school','grade_applying','message']})
        db.session.add(a); db.session.commit(); flash('Application submitted!','success')
        return redirect(url_for('admissions'))
    return render_template('admissions.html')

@app.route('/contact', methods=['GET','POST'])
def contact():
    if request.method=='POST':
        c = ContactMessage(name=request.form['name'], email=request.form['email'], phone=request.form.get('phone'), message=request.form['message'])
        db.session.add(c); db.session.commit(); flash('Message sent!','success')
        return redirect(url_for('contact'))
    return render_template('contact.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('home'))
    if request.method=='POST':
        u = User.query.filter_by(username=request.form['username']).first()
        if u and u.check_password(request.form['password']):
            login_user(u); flash(f'Welcome {u.username}!','success')
            return redirect(url_for('home'))
        flash('Invalid credentials','danger')
    return render_template('login.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if current_user.is_authenticated: return redirect(url_for('home'))
    if request.method=='POST':
        if request.form['password'] != request.form['confirm_password']:
            flash('Passwords mismatch','danger'); return redirect(url_for('register'))
        if User.query.filter_by(username=request.form['username']).first():
            flash('Username taken','danger'); return redirect(url_for('register'))
        u = User(username=request.form['username'], phone=request.form['phone'])
        u.set_password(request.form['password'])
        db.session.add(u); db.session.commit(); flash('Registered! Please login.','success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout(): logout_user(); flash('Logged out.','info'); return redirect(url_for('home'))

# ------------------- FEATURE ROUTES -------------------
@app.route('/results', methods=['GET','POST'])
def results():
    res, err = None, None
    if request.method=='POST':
        r = ExamResult.query.filter_by(index_number=request.form['index_number'].strip().upper(), exam_type=request.form['exam_type']).first()
        if r:
            subs = [{'name': s.split(':')[0], 'marks': s.split(':')[1]} for s in r.subjects.split(',') if ':' in s] if r.subjects else []
            res = {'name': r.student_name, 'index': r.index_number, 'year': r.year, 'division': r.division, 'total': r.total_marks, 'subjects': subs}
        else: err = 'No results found.'
    return render_template('results.html', result=res, error=err)

@app.route('/suggest', methods=['GET','POST'])
def suggest():
    if request.method=='POST':
        s = Suggestion(content=request.form['content'], category=request.form['category'])
        db.session.add(s); db.session.commit(); flash('Suggestion sent (anonymous)','success')
        return redirect(url_for('suggest'))
    return render_template('suggest.html')

@app.route('/alumni')
def alumni():
    return render_template('alumni.html', alumni=Alumni.query.order_by(Alumni.graduation_year.desc()).all(), featured=Alumni.query.filter_by(is_featured=True).first())

@app.route('/events')
def events():
    now = datetime.utcnow()
    return render_template('events.html', upcoming=Event.query.filter(Event.event_date >= now).order_by(Event.event_date).all(), past=Event.query.filter(Event.event_date < now).order_by(Event.event_date.desc()).limit(5).all())

@app.route('/quiz', methods=['GET','POST'])
def quiz():
    fb = None
    q = QuizQuestion.query.order_by(db.func.random()).first()
    if request.method=='POST':
        qq = QuizQuestion.query.get(request.form['q_id'])
        if qq:
            ans = request.form.get('answer')
            if ans and ans.upper() == qq.correct_answer:
                fb = f"✅ Correct! {qq.explanation}"
            else:
                correct_text = getattr(qq, f'option_{qq.correct_answer.lower()}')
                fb = f"❌ Wrong. Correct: {qq.correct_answer} - {correct_text}"
    return render_template('quiz.html', question=q, feedback=fb)

@app.route('/ai-assistant', methods=['GET','POST'])
def ai_assistant():
    resp = None
    if request.method=='POST':
        inp = request.form.get('user_input','').strip()
        if inp:
            low = inp.lower()
            if any(w in low for w in ['shule','school','masomo']):
                resp = "St. Amedeus inatoa PCM, PCB, CBG, EGM. Tembelea Academics."
            elif any(w in low for w in ['mitihani','exam','matokeo']):
                resp = "Matokeo yanapatikana kwa index number kwenye Results."
            elif any(w in low for w in ['admission','jiunge']):
                resp = "Jaza fomu kwenye Admissions."
            else:
                resp = "Asante kwa swali. Wasiliana nasi kwenye Contact."
        else: resp = "Andika swali lako."
    return render_template('ai_assistant.html', response=resp)

# ------------------- ADMIN DASHBOARD & CRUD -------------------
@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    return render_template('admin/dashboard.html',
        announcements=Announcement.query.all(),
        media_items=StudentLifeMedia.query.all(),
        gallery_items=GalleryItem.query.all(),
        contact_messages=ContactMessage.query.all(),
        applications=AdmissionApplication.query.all(),
        users=User.query.all(),
        exam_results=ExamResult.query.all(),
        suggestions=Suggestion.query.all(),
        alumni_list=Alumni.query.all(),
        events=Event.query.all(),
        quiz_questions=QuizQuestion.query.all()
    )

# Helper delete
def delete_by_id(model, id):
    db.session.delete(model.query.get_or_404(id))
    db.session.commit()
    flash('Deleted','success')

# CRUD for announcements
@app.route('/admin/add_announcement', methods=['POST'])
@admin_required
def add_announcement():
    a = Announcement(title=request.form['title'], content=request.form['content'], category=request.form['category'])
    if request.form.get('event_date'):
        a.event_date = datetime.strptime(request.form['event_date'], '%Y-%m-%d')
    db.session.add(a); db.session.commit(); flash('Added','success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_announcement/<int:id>')
@admin_required
def delete_announcement(id): delete_by_id(Announcement, id); return redirect(url_for('admin_dashboard'))

# CRUD for StudentLifeMedia with file upload
@app.route('/admin/add_media', methods=['POST'])
@admin_required
def add_media():
    title = request.form['title']
    desc = request.form.get('description','')
    media_type = request.form['media_type']
    order = int(request.form.get('order',0))
    file = request.files.get('file')
    url = request.form.get('url')
    if file and allowed_file(file.filename):
        fname = secure_filename(file.filename)
        name, ext = os.path.splitext(fname)
        newname = f"{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], newname))
        url = url_for('static', filename=f'uploads/{newname}')
    elif not url:
        flash('Provide file or URL','danger'); return redirect(url_for('admin_dashboard'))
    media = StudentLifeMedia(title=title, description=desc, media_type=media_type, url=url, order=order)
    db.session.add(media); db.session.commit(); flash('Media added','success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_media/<int:id>')
@admin_required
def delete_media(id): delete_by_id(StudentLifeMedia, id); return redirect(url_for('admin_dashboard'))

# CRUD for Gallery with file upload
@app.route('/admin/add_gallery', methods=['POST'])
@admin_required
def add_gallery():
    title = request.form['title']
    desc = request.form.get('description','')
    media_type = request.form['media_type']
    file = request.files.get('file')
    url = request.form.get('url')
    if file and allowed_file(file.filename):
        fname = secure_filename(file.filename)
        name, ext = os.path.splitext(fname)
        newname = f"{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], newname))
        url = url_for('static', filename=f'uploads/{newname}')
    elif not url:
        flash('Provide file or URL','danger'); return redirect(url_for('admin_dashboard'))
    item = GalleryItem(title=title, description=desc, media_type=media_type, url=url)
    db.session.add(item); db.session.commit(); flash('Gallery item added','success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_gallery/<int:id>')
@admin_required
def delete_gallery(id): delete_by_id(GalleryItem, id); return redirect(url_for('admin_dashboard'))

# Other simple CRUD
@app.route('/admin/delete_message/<int:id>')
@admin_required
def delete_message(id): delete_by_id(ContactMessage, id); return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_application/<int:id>')
@admin_required
def delete_application(id): delete_by_id(AdmissionApplication, id); return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_suggestion/<int:id>')
@admin_required
def delete_suggestion(id): delete_by_id(Suggestion, id); return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_result', methods=['POST'])
@admin_required
def add_result():
    r = ExamResult(
        index_number=request.form['index_number'].upper(),
        student_name=request.form['student_name'],
        exam_type=request.form['exam_type'],
        year=request.form['year'],
        subjects=request.form.get('subjects',''),
        total_marks=request.form.get('total_marks',0),
        division=request.form.get('division','')
    )
    db.session.add(r); db.session.commit(); flash('Result added','success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_result/<int:id>')
@admin_required
def delete_result(id): delete_by_id(ExamResult, id); return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_alumni', methods=['POST'])
@admin_required
def add_alumni():
    a = Alumni(
        name=request.form['name'],
        graduation_year=request.form.get('graduation_year'),
        current_occupation=request.form.get('occupation'),
        story=request.form.get('story'),
        image_url=request.form.get('image_url'),
        is_featured=(request.form.get('is_featured') == 'on')
    )
    db.session.add(a); db.session.commit(); flash('Alumni added','success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_alumni/<int:id>')
@admin_required
def delete_alumni(id): delete_by_id(Alumni, id); return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_event', methods=['POST'])
@admin_required
def add_event():
    e = Event(
        title=request.form['title'],
        description=request.form.get('description',''),
        event_date=datetime.strptime(request.form['event_date'], '%Y-%m-%dT%H:%M'),
        location=request.form.get('location','')
    )
    db.session.add(e); db.session.commit(); flash('Event added','success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_event/<int:id>')
@admin_required
def delete_event(id): delete_by_id(Event, id); return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_quiz', methods=['POST'])
@admin_required
def add_quiz():
    q = QuizQuestion(
        question=request.form['question'],
        option_a=request.form['opt_a'],
        option_b=request.form['opt_b'],
        option_c=request.form['opt_c'],
        option_d=request.form['opt_d'],
        correct_answer=request.form['correct_answer'],
        explanation=request.form.get('explanation','')
    )
    db.session.add(q); db.session.commit(); flash('Quiz added','success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_quiz/<int:id>')
@admin_required
def delete_quiz(id): delete_by_id(QuizQuestion, id); return redirect(url_for('admin_dashboard'))

# ------------------- INIT -------------------
def init_admin():
    if not User.query.filter_by(username='admin').first():
        a = User(username='admin', phone='+255700000000', is_admin=True)
        a.set_password('admin123')
        db.session.add(a); db.session.commit()
        print("Admin: admin / admin123")

with app.app_context():
    db.create_all()
    init_admin()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
