from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import uuid
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')  # Needed for flash messages


# Database initialization
def init_db():
    conn = sqlite3.connect('referral.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id TEXT PRIMARY KEY, 
                  username TEXT UNIQUE, 
                  referral_code TEXT UNIQUE, 
                  referred_by TEXT,
                  created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS referrals 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  referrer_id TEXT, 
                  referred_id TEXT, 
                  created_at TEXT)''')
    conn.commit()
    conn.close()

# Home route
@app.route('/')
def home():
    return render_template('index.html', ref=request.args.get('ref', ''))

# Registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        referred_by = request.form.get('ref', '')
        
        if not username or len(username) < 3:
            flash('Username must be at least 3 characters long')
            return render_template('register.html')
            
        # Generate unique identifiers
        user_id = str(uuid.uuid4())
        referral_code = str(uuid.uuid4())[:8]
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        conn = sqlite3.connect('referral.db')
        c = conn.cursor()
        
        try:
            # Insert new user
            c.execute("INSERT INTO users (id, username, referral_code, referred_by, created_at) VALUES (?, ?, ?, ?, ?)",
                     (user_id, username, referral_code, referred_by, created_at))
            
            # If referred by someone, update referrals table
            if referred_by:
                c.execute("SELECT id FROM users WHERE referral_code = ?", (referred_by,))
                referrer = c.fetchone()
                if referrer:
                    c.execute("INSERT INTO referrals (referrer_id, referred_id, created_at) VALUES (?, ?, ?)",
                             (referrer[0], user_id, created_at))
            
            conn.commit()
            flash('Registration successful!')
            return redirect(url_for('dashboard', user_id=user_id))
            
        except sqlite3.IntegrityError:
            conn.rollback()
            flash('Username already exists')
            return render_template('register.html')
        finally:
            conn.close()
    
    return render_template('register.html', ref=request.args.get('ref', ''))

# Dashboard route
@app.route('/dashboard/<user_id>')
def dashboard(user_id):
    conn = sqlite3.connect('referral.db')
    c = conn.cursor()
    
    try:
        # Get user info
        c.execute("SELECT username, referral_code FROM users WHERE id = ?", (user_id,))
        user = c.fetchone()
        if not user:
            flash('User not found')
            return redirect(url_for('home'))
            
        # Get referral stats
        c.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user_id,))
        referral_count = c.fetchone()[0]
        
        # Get referred users with timestamps
        c.execute("""
            SELECT u.username, r.created_at
            FROM referrals r 
            JOIN users u ON r.referred_id = u.id 
            WHERE r.referrer_id = ?
            ORDER BY r.created_at DESC
        """, (user_id,))
        referred_users = c.fetchall()
        
        referral_link = f"{request.host_url}register?ref={user[1]}"
        
        return render_template('dashboard.html',
                            username=user[0],
                            referral_count=referral_count,
                            referral_link=referral_link,
                            referred_users=referred_users,
                            user_id=user_id)
    finally:
        conn.close()

# Activity route
@app.route('/activity/<user_id>')
def activity(user_id):
    conn = sqlite3.connect('referral.db')
    c = conn.cursor()
    
    try:
        # Get user info
        c.execute("SELECT username, referred_by, created_at FROM users WHERE id = ?", (user_id,))
        user = c.fetchone()
        if not user:
            flash('User not found')
            return redirect(url_for('home'))
            
        # Get referrer info
        referred_by_name = None
        if user[1]:
            c.execute("SELECT username FROM users WHERE referral_code = ?", (user[1],))
            referred_by = c.fetchone()
            referred_by_name = referred_by[0] if referred_by else None
            
        return render_template('activity.html',
                            username=user[0],
                            referred_by=referred_by_name,
                            created_at=user[2],
                            user_id=user_id)
    finally:
        conn.close()

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port)