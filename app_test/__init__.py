from flask import Flask, redirect, session, url_for, render_template, request, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from app_test.models import User, Guest

app = Flask(__name__)
app.secret_key = 'your_secret_key'
login_manager = LoginManager()
login_manager.init_app(app)

# Inisiasi user loader untuk menangani sesi user
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('dashboard'))  # Setelah login, redirect ke dashboard
        else:
            flash('Login gagal, cek username dan password Anda!')
    return render_template('login.html')

@app.route('/login-otp', methods=['GET', 'POST'])
def login_otp():
    if request.method == 'POST':
        email = request.form['email']
        otp = request.form['otp']
        guest = Guest.query.filter_by(email=email, otp=otp).first()
        
        if guest:
            # Buat login simulasi (tanpa Flask-Login)
            session['guest_id'] = guest.id
            return redirect(url_for('guest_dashboard'))
        else:
            flash('OTP salah atau email tidak terdaftar!')
    return render_template('login_otp.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)

@app.route('/guest-dashboard')
def guest_dashboard():
    if 'guest_id' in session:
        guest = Guest.query.get(session['guest_id'])
        return render_template('guest_dashboard.html', guest=guest)
    return redirect(url_for('login_otp'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/guest-logout')
def guest_logout():
    session.pop('guest_id', None)
    return redirect(url_for('login_otp'))

if __name__ == '__main__':
    app.run(debug=True)