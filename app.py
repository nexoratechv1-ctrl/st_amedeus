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

