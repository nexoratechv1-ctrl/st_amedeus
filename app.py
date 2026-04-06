import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps
from groq import Groq

app = Flask(__name__)
app.config['SECRET_KEY'] = 'st-amedeus-secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///school.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ---------- GROQ API ----------
GROQ_API_KEY = "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"
groq_client = Groq(api_key=GROQ_API_KEY)

# ---------- MODELS ----------
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
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default='news')
    event_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class StudentLifeMedia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    media_type = db.Column(db.String(20), default='image')
    url = db.Column(db.String(500), nullable=False)
    order = db.Column(db.Integer, default=0)

class GalleryItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    media_type = db.Column(db.String(20), default='image')
    url = db.Column(db.String(500), nullable=False)

class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name, email, phone, message = db.Column(db.String(100)), db.Column(db.String(100)), db.Column(db.String(20)), db.Column(db.Text)

class AdmissionApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name, parent_name, email, phone, date_of_birth, previous_school, grade_applying, message = (
        db.Column(db.String(100)), db.Column(db.String(100)), db.Column(db.String(100)), db.Column(db.String(20)),
        db.Column(db.String(50)), db.Column(db.String(200)), db.Column(db.String(50)), db.Column(db.Text))

class ExamResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    index_number = db.Column(db.String(50), unique=True, nullable=False)
    student_name, exam_type, year, subjects, total_marks, division = (
        db.Column(db.String(100)), db.Column(db.String(50)), db.Column(db.Integer),
        db.Column(db.Text), db.Column(db.Integer), db.Column(db.String(10)))

class Suggestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default='general')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Alumni(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    graduation_year = db.Column(db.Integer)
    current_occupation = db.Column(db.String(200))
    story = db.Column(db.Text)
    image_url = db.Column(db.String(300))
    is_featured = db.Column(db.Boolean, default=False)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    event_date = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(200))

class QuizQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    option_a, option_b, option_c, option_d, correct_answer, explanation = (
        db.Column(db.String(200)), db.Column(db.String(200)), db.Column(db.String(200)),
        db.Column(db.String(200)), db.Column(db.String(1)), db.Column(db.Text))

# ---------- HELPERS ----------
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

# ---------- PUBLIC ROUTES ----------
@app.route('/')
def home():
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).limit(3).all()
    return render_template('index.html', announcements=announcements)

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
        db.session.add(a); db.session.commit(); flash('Submitted!','success')
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

# ---------- FEATURE ROUTES ----------
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

# ---------- AI ASSISTANT (Groq) ----------
@app.route('/ai-assistant', methods=['GET','POST'])
def ai_assistant():
    response = None
    if request.method=='POST':
        user_input = request.form.get('user_input','').strip()
        if user_input:
            try:
                completion = groq_client.chat.completions.create(
                    messages=[{"role": "system", "content": "Msaidizi wa St. Amedeus, jibu kwa Kiswahili au Kiingereza kwa heshima."},
                              {"role": "user", "content": user_input}],
                    model="llama3-8b-8192", temperature=0.7)
                response = completion.choices[0].message.content
            except:
                response = "Samahani, kuna tatizo. Jaribu tena."
        else:
            response = "Andika swali lako."
    return render_template('ai_assistant.html', response=response)

# ---------- ADMIN DASHBOARD & CRUD (compressed) ----------
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

# Helper to delete any model
def delete_by_id(model, id):
    item = model.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash('Deleted','success')

# CRUD endpoints (minimal)
for model, name, prefix in [
    (Announcement, 'announcement', 'add_announcement'),
    (StudentLifeMedia, 'media', 'add_media'),
    (GalleryItem, 'gallery', 'add_gallery'),
    (ExamResult, 'result', 'add_result'),
    (Alumni, 'alumni', 'add_alumni'),
    (Event, 'event', 'add_event'),
    (QuizQuestion, 'quiz', 'add_quiz')
]:
    @app.route(f'/admin/add_{name}', methods=['POST'])
    @admin_required
    def add_generic(model=model, name=name):
        # Manual mapping because fields differ
        if model == Announcement:
            obj = model(title=request.form['title'], content=request.form['content'], category=request.form['category'])
            if request.form.get('event_date'): obj.event_date = datetime.strptime(request.form['event_date'], '%Y-%m-%d')
        elif model == StudentLifeMedia:
            obj = model(title=request.form['title'], description=request.form.get('description',''), media_type=request.form['media_type'], url=request.form['url'], order=int(request.form.get('order',0)))
        elif model == GalleryItem:
            obj = model(title=request.form['title'], description=request.form.get('description',''), media_type=request.form['media_type'], url=request.form['url'])
        elif model == ExamResult:
            obj = model(index_number=request.form['index_number'].upper(), student_name=request.form['student_name'], exam_type=request.form['exam_type'], year=request.form['year'], subjects=request.form.get('subjects',''), total_marks=request.form.get('total_marks',0), division=request.form.get('division',''))
        elif model == Alumni:
            obj = model(name=request.form['name'], graduation_year=request.form.get('graduation_year'), current_occupation=request.form.get('occupation'), story=request.form.get('story'), image_url=request.form.get('image_url'), is_featured=(request.form.get('is_featured')=='on'))
        elif model == Event:
            obj = model(title=request.form['title'], description=request.form.get('description',''), event_date=datetime.strptime(request.form['event_date'], '%Y-%m-%dT%H:%M'), location=request.form.get('location',''))
        elif model == QuizQuestion:
            obj = model(question=request.form['question'], option_a=request.form['opt_a'], option_b=request.form['opt_b'], option_c=request.form['opt_c'], option_d=request.form['opt_d'], correct_answer=request.form['correct_answer'], explanation=request.form.get('explanation',''))
        else:
            obj = None
        if obj:
            db.session.add(obj); db.session.commit(); flash(f'{name.capitalize()} added','success')
        return redirect(url_for('admin_dashboard'))
    @app.route(f'/admin/delete_{name}/<int:id>')
    @admin_required
    def delete_generic(id, model=model):
        delete_by_id(model, id)
        return redirect(url_for('admin_dashboard'))

# Manual delete for contact and application (different names)
@app.route('/admin/delete_message/<int:id>')
@admin_required
def delete_message(id): delete_by_id(ContactMessage, id); return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_application/<int:id>')
@admin_required
def delete_application(id): delete_by_id(AdmissionApplication, id); return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_suggestion/<int:id>')
@admin_required
def delete_suggestion(id): delete_by_id(Suggestion, id); return redirect(url_for('admin_dashboard'))

# ---------- INIT ----------
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
