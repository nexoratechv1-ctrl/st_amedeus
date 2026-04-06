import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps
from groq import Groq

app = Flask(__name__)
app.config['SECRET_KEY'] = 'st-amedeus-secret-key-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///school.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ------------------- GROQ API KEY (embedded) -------------------
GROQ_API_KEY = "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"
# Initialize Groq client
try:
    groq_client = Groq(api_key=GROQ_API_KEY)
    GROQ_AVAILABLE = True
except Exception as e:
    print("Groq client error:", e)
    GROQ_AVAILABLE = False

# ------------------- MODELS -------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

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
    description = db.Column(db.Text, nullable=True)
    media_type = db.Column(db.String(20), default='image')
    url = db.Column(db.String(500), nullable=False)
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class GalleryItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    media_type = db.Column(db.String(20), default='image')
    url = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AdmissionApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    parent_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    date_of_birth = db.Column(db.String(50), nullable=False)
    previous_school = db.Column(db.String(200), nullable=True)
    grade_applying = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=True)
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)

class ExamResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    index_number = db.Column(db.String(50), nullable=False, index=True)
    student_name = db.Column(db.String(100), nullable=False)
    exam_type = db.Column(db.String(50))
    year = db.Column(db.Integer)
    subjects = db.Column(db.Text)
    total_marks = db.Column(db.Integer)
    division = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Suggestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default='general')
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Alumni(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    graduation_year = db.Column(db.Integer)
    current_occupation = db.Column(db.String(200))
    story = db.Column(db.Text)
    image_url = db.Column(db.String(300))
    is_featured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    event_date = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class QuizQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(200))
    option_b = db.Column(db.String(200))
    option_c = db.Column(db.String(200))
    option_d = db.Column(db.String(200))
    correct_answer = db.Column(db.String(1))
    explanation = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ------------------- LOGIN HELPERS -------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_user():
    return dict(current_user=current_user)

# ------------------- PUBLIC ROUTES -------------------
@app.route('/')
def home():
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).limit(3).all()
    return render_template('index.html', announcements=announcements)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/academics')
def academics():
    return render_template('academics.html')

@app.route('/students-life')
def students_life():
    media_items = StudentLifeMedia.query.order_by(StudentLifeMedia.order).all()
    return render_template('students_life.html', media_items=media_items)

@app.route('/news-events')
def news_events():
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
    return render_template('news_events.html', announcements=announcements)

@app.route('/gallery')
def gallery():
    items = GalleryItem.query.order_by(GalleryItem.created_at.desc()).all()
    return render_template('gallery.html', gallery_items=items)

@app.route('/admissions', methods=['GET', 'POST'])
def admissions():
    if request.method == 'POST':
        app_obj = AdmissionApplication(
            full_name=request.form.get('full_name'),
            parent_name=request.form.get('parent_name'),
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            date_of_birth=request.form.get('date_of_birth'),
            previous_school=request.form.get('previous_school'),
            grade_applying=request.form.get('grade_applying'),
            message=request.form.get('message')
        )
        db.session.add(app_obj)
        db.session.commit()
        flash('Application submitted successfully!', 'success')
        return redirect(url_for('admissions'))
    return render_template('admissions.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        msg = ContactMessage(
            name=request.form.get('name'),
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            message=request.form.get('message')
        )
        db.session.add(msg)
        db.session.commit()
        flash('Message sent!', 'success')
        return redirect(url_for('contact'))
    return render_template('contact.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and user.check_password(request.form.get('password')):
            login_user(user)
            flash(f'Welcome {user.username}!', 'success')
            return redirect(url_for('home'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        if request.form.get('password') != request.form.get('confirm_password'):
            flash('Passwords do not match', 'danger')
            return redirect(url_for('register'))
        if User.query.filter_by(username=request.form.get('username')).first():
            flash('Username taken', 'danger')
            return redirect(url_for('register'))
        user = User(username=request.form.get('username'), phone=request.form.get('phone'))
        user.set_password(request.form.get('password'))
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out.', 'info')
    return redirect(url_for('home'))

# ------------------- FEATURE ROUTES -------------------
@app.route('/results', methods=['GET', 'POST'])
def results():
    result = None
    error = None
    if request.method == 'POST':
        idx = request.form.get('index_number', '').strip().upper()
        exam = request.form.get('exam_type')
        r = ExamResult.query.filter_by(index_number=idx, exam_type=exam).first()
        if r:
            subjects = []
            if r.subjects:
                for s in r.subjects.split(','):
                    if ':' in s:
                        subj, mark = s.split(':')
                        subjects.append({'name': subj, 'marks': mark})
            result = {'name': r.student_name, 'index': r.index_number, 'year': r.year,
                      'division': r.division, 'total': r.total_marks, 'subjects': subjects}
        else:
            error = 'No results found.'
    return render_template('results.html', result=result, error=error)

@app.route('/suggest', methods=['GET', 'POST'])
def suggest():
    if request.method == 'POST':
        s = Suggestion(content=request.form.get('content'), category=request.form.get('category'))
        db.session.add(s)
        db.session.commit()
        flash('Thank you for your anonymous suggestion!', 'success')
        return redirect(url_for('suggest'))
    return render_template('suggest.html')

@app.route('/alumni')
def alumni():
    all_alumni = Alumni.query.order_by(Alumni.graduation_year.desc()).all()
    featured = Alumni.query.filter_by(is_featured=True).first()
    return render_template('alumni.html', alumni=all_alumni, featured=featured)

@app.route('/events')
def events():
    upcoming = Event.query.filter(Event.event_date >= datetime.utcnow()).order_by(Event.event_date).all()
    past = Event.query.filter(Event.event_date < datetime.utcnow()).order_by(Event.event_date.desc()).limit(5).all()
    return render_template('events.html', upcoming=upcoming, past=past)

@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    feedback = None
    question = QuizQuestion.query.order_by(db.func.random()).first()
    if request.method == 'POST':
        qid = request.form.get('q_id')
        q = QuizQuestion.query.get(qid)
        if q:
            ans = request.form.get('answer')
            if ans and ans.upper() == q.correct_answer:
                feedback = f"✅ Correct! {q.explanation}"
            else:
                correct_text = getattr(q, f'option_{q.correct_answer.lower()}')
                feedback = f"❌ Wrong. Correct: {q.correct_answer} - {correct_text}. {q.explanation}"
    return render_template('quiz.html', question=question, feedback=feedback)

# ------------------- AI ASSISTANT (GROQ) -------------------
@app.route('/ai-assistant', methods=['GET', 'POST'])
def ai_assistant():
    response = None
    if request.method == 'POST':
        user_input = request.form.get('user_input', '').strip()
        if user_input:
            if GROQ_AVAILABLE:
                try:
                    chat_completion = groq_client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": "Wewe ni msaidizi wa shule ya St. Amedeus. Unasaidia kwa maswali ya elimu, maisha, ushauri. Jibu kwa Kiswahili au Kiingereza kwa ukarimu na kwa ufupi."},
                            {"role": "user", "content": user_input}
                        ],
                        model="llama3-8b-8192",
                        temperature=0.7,
                    )
                    response = chat_completion.choices[0].message.content
                except Exception as e:
                    response = "Samahani, kuna tatizo la kiufundi. Jaribu tena baadaye."
            else:
                # Fallback responses (no API)
                lower = user_input.lower()
                if any(w in lower for w in ['shule', 'school', 'masomo']):
                    response = "St. Amedeus High School inatoa masomo ya PCM, PCB, CBG, na EGM. Tembelea ukurasa wa Academics."
                elif any(w in lower for w in ['mitihani', 'exam', 'matokeo']):
                    response = "Matokeo ya mitihani yanapatikana kwa kuingiza index number kwenye ukurasa wa Results."
                elif any(w in lower for w in ['admission', 'jiunge']):
                    response = "Unaweza kujiunga kwa kujaza fomu ya maombi kwenye ukurasa wa Admissions."
                else:
                    response = "Asante kwa swali lako. Tafadhali wasiliana nasi kwenye Contact page."
        else:
            response = "Tafadhali andika swali lako."
    return render_template('ai_assistant.html', response=response)

# ------------------- ADMIN DASHBOARD -------------------
@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
    media_items = StudentLifeMedia.query.order_by(StudentLifeMedia.order).all()
    gallery_items = GalleryItem.query.order_by(GalleryItem.created_at.desc()).all()
    contact_messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    applications = AdmissionApplication.query.order_by(AdmissionApplication.applied_at.desc()).all()
    users = User.query.all()
    exam_results = ExamResult.query.all()
    suggestions = Suggestion.query.order_by(Suggestion.created_at.desc()).all()
    alumni_list = Alumni.query.all()
    events = Event.query.order_by(Event.event_date.desc()).all()
    quiz_questions = QuizQuestion.query.all()
    return render_template('admin/dashboard.html', 
                         announcements=announcements,
                         media_items=media_items,
                         gallery_items=gallery_items,
                         contact_messages=contact_messages,
                         applications=applications,
                         users=users,
                         exam_results=exam_results,
                         suggestions=suggestions,
                         alumni_list=alumni_list,
                         events=events,
                         quiz_questions=quiz_questions)

# ------------------- ADMIN CRUD (abbreviated but complete) -------------------
@app.route('/admin/add_announcement', methods=['POST'])
@login_required
@admin_required
def add_announcement():
    a = Announcement(title=request.form['title'], content=request.form['content'], category=request.form['category'])
    if request.form.get('event_date'):
        a.event_date = datetime.strptime(request.form['event_date'], '%Y-%m-%d')
    db.session.add(a)
    db.session.commit()
    flash('Added', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_announcement/<int:id>')
@login_required
@admin_required
def delete_announcement(id):
    db.session.delete(Announcement.query.get_or_404(id))
    db.session.commit()
    flash('Deleted', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_media', methods=['POST'])
@login_required
@admin_required
def add_media():
    m = StudentLifeMedia(title=request.form['title'], description=request.form.get('description',''), media_type=request.form['media_type'], url=request.form['url'], order=int(request.form.get('order',0)))
    db.session.add(m)
    db.session.commit()
    flash('Media added', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_media/<int:id>')
@login_required
@admin_required
def delete_media(id):
    db.session.delete(StudentLifeMedia.query.get_or_404(id))
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_gallery', methods=['POST'])
@login_required
@admin_required
def add_gallery():
    g = GalleryItem(title=request.form['title'], description=request.form.get('description',''), media_type=request.form['media_type'], url=request.form['url'])
    db.session.add(g)
    db.session.commit()
    flash('Gallery item added', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_gallery/<int:id>')
@login_required
@admin_required
def delete_gallery(id):
    db.session.delete(GalleryItem.query.get_or_404(id))
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_message/<int:id>')
@login_required
@admin_required
def delete_message(id):
    db.session.delete(ContactMessage.query.get_or_404(id))
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_application/<int:id>')
@login_required
@admin_required
def delete_application(id):
    db.session.delete(AdmissionApplication.query.get_or_404(id))
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_result', methods=['POST'])
@login_required
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
    db.session.add(r)
    db.session.commit()
    flash('Result added', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_result/<int:id>')
@login_required
@admin_required
def delete_result(id):
    db.session.delete(ExamResult.query.get_or_404(id))
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_suggestion/<int:id>')
@login_required
@admin_required
def delete_suggestion(id):
    db.session.delete(Suggestion.query.get_or_404(id))
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_alumni', methods=['POST'])
@login_required
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
    db.session.add(a)
    db.session.commit()
    flash('Alumni added', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_alumni/<int:id>')
@login_required
@admin_required
def delete_alumni(id):
    db.session.delete(Alumni.query.get_or_404(id))
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_event', methods=['POST'])
@login_required
@admin_required
def add_event():
    e = Event(
        title=request.form['title'],
        description=request.form.get('description',''),
        event_date=datetime.strptime(request.form['event_date'], '%Y-%m-%dT%H:%M'),
        location=request.form.get('location','')
    )
    db.session.add(e)
    db.session.commit()
    flash('Event added', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_event/<int:id>')
@login_required
@admin_required
def delete_event(id):
    db.session.delete(Event.query.get_or_404(id))
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_quiz', methods=['POST'])
@login_required
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
    db.session.add(q)
    db.session.commit()
    flash('Quiz added', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_quiz/<int:id>')
@login_required
@admin_required
def delete_quiz(id):
    db.session.delete(QuizQuestion.query.get_or_404(id))
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

# ------------------- INIT ADMIN AND TABLES -------------------
def init_admin():
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', phone='+255700000000', is_admin=True)
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("Admin created: admin / admin123")

with app.app_context():
    db.create_all()
    init_admin()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

