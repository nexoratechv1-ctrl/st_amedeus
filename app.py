# app.py
import os
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'st-amedeus-secret-key-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///school.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ------------------- DATABASE MODELS -------------------
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
    category = db.Column(db.String(50), default='news')  # news, event, announcement
    event_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
class StudentLifeMedia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    media_type = db.Column(db.String(20), default='image')  # image or video
    url = db.Column(db.String(500), nullable=False)  # image URL or video embed URL
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

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Admin decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

# ------------------- ROUTES -------------------
@app.context_processor
def inject_user():
    return dict(current_user=current_user)

@app.route('/')
def home():
    latest_announcements = Announcement.query.order_by(Announcement.created_at.desc()).limit(3).all()
    return render_template('index.html', announcements=latest_announcements)

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
    gallery_items = GalleryItem.query.order_by(GalleryItem.created_at.desc()).all()
    return render_template('gallery.html', gallery_items=gallery_items)

@app.route('/admissions', methods=['GET', 'POST'])
def admissions():
    if request.method == 'POST':
        application = AdmissionApplication(
            full_name=request.form.get('full_name'),
            parent_name=request.form.get('parent_name'),
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            date_of_birth=request.form.get('date_of_birth'),
            previous_school=request.form.get('previous_school'),
            grade_applying=request.form.get('grade_applying'),
            message=request.form.get('message')
        )
        db.session.add(application)
        db.session.commit()
        flash('Your application has been submitted successfully! We will contact you soon.', 'success')
        return redirect(url_for('admissions'))
    return render_template('admissions.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        message = ContactMessage(
            name=request.form.get('name'),
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            message=request.form.get('message')
        )
        db.session.add(message)
        db.session.commit()
        flash('Your message has been sent. We will get back to you shortly!', 'success')
        return redirect(url_for('contact'))
    return render_template('contact.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash(f'Welcome back, {user.username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        phone = request.form.get('phone')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('register'))
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists!', 'danger')
            return redirect(url_for('register'))
        
        existing_phone = User.query.filter_by(phone=phone).first()
        if existing_phone:
            flash('Phone number already registered!', 'danger')
            return redirect(url_for('register'))
        
        user = User(username=username, phone=phone)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

# ------------------- ADMIN PANEL -------------------
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
    return render_template('admin/dashboard.html', 
                         announcements=announcements,
                         media_items=media_items,
                         gallery_items=gallery_items,
                         contact_messages=contact_messages,
                         applications=applications,
                         users=users)

@app.route('/admin/add_announcement', methods=['POST'])
@login_required
@admin_required
def add_announcement():
    title = request.form.get('title')
    content = request.form.get('content')
    category = request.form.get('category')
    event_date = request.form.get('event_date')
    
    announcement = Announcement(
        title=title,
        content=content,
        category=category
    )
    if event_date:
        announcement.event_date = datetime.strptime(event_date, '%Y-%m-%d')
    
    db.session.add(announcement)
    db.session.commit()
    flash('Announcement added successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_announcement/<int:id>')
@login_required
@admin_required
def delete_announcement(id):
    announcement = Announcement.query.get_or_404(id)
    db.session.delete(announcement)
    db.session.commit()
    flash('Announcement deleted!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_media', methods=['POST'])
@login_required
@admin_required
def add_media():
    title = request.form.get('title')
    description = request.form.get('description')
    media_type = request.form.get('media_type')
    url = request.form.get('url')
    order = request.form.get('order', 0)
    
    media = StudentLifeMedia(
        title=title,
        description=description,
        media_type=media_type,
        url=url,
        order=order
    )
    db.session.add(media)
    db.session.commit()
    flash('Media item added to Student Life!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_media/<int:id>')
@login_required
@admin_required
def delete_media(id):
    media = StudentLifeMedia.query.get_or_404(id)
    db.session.delete(media)
    db.session.commit()
    flash('Media item deleted!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_gallery', methods=['POST'])
@login_required
@admin_required
def add_gallery():
    title = request.form.get('title')
    description = request.form.get('description')
    media_type = request.form.get('media_type')
    url = request.form.get('url')
    
    item = GalleryItem(
        title=title,
        description=description,
        media_type=media_type,
        url=url
    )
    db.session.add(item)
    db.session.commit()
    flash('Gallery item added!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_gallery/<int:id>')
@login_required
@admin_required
def delete_gallery(id):
    item = GalleryItem.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash('Gallery item deleted!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_message/<int:id>')
@login_required
@admin_required
def delete_message(id):
    message = ContactMessage.query.get_or_404(id)
    db.session.delete(message)
    db.session.commit()
    flash('Message deleted!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_application/<int:id>')
@login_required
@admin_required
def delete_application(id):
    app = AdmissionApplication.query.get_or_404(id)
    db.session.delete(app)
    db.session.commit()
    flash('Application deleted!', 'success')
    return redirect(url_for('admin_dashboard'))

# Create admin user if not exists
def init_admin():
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(username='admin', phone='+255700000000', is_admin=True)
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("Admin user created: username 'admin', password 'admin123'")

# ------------------- CREATE TABLES -------------------
with app.app_context():
    db.create_all()
    init_admin()

if __name__ == '__main__':
    app.run(debug=True, threaded=True, host='0.0.0.0', port=5000)
