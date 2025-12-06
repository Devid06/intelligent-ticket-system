import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from textblob import TextBlob  # The Free NLP Library

app = Flask(__name__)

# CONFIGURATION
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///tickets.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- DATABASE MODEL ---
class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Open')
    priority = db.Column(db.String(20), default='Medium')
    ai_suggested_fix = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

# --- THE FREE "INTELLIGENCE" ENGINE ---
def analyze_ticket(title, description):
    text = f"{title} {description}".lower()
    
    # 1. Sentiment Analysis (Detect Frustration)
    # Polarity is between -1 (Very Negative) and +1 (Very Positive)
    blob = TextBlob(description)
    sentiment_score = blob.sentiment.polarity
    
    # 2. Rule-Based Priority Assignment
    priority = "Medium"
    
    # Critical Keywords override everything
    critical_keywords = ['server down', 'crash', 'data loss', 'hack', 'emergency']
    high_keywords = ['slow', 'error', 'failed', 'broken', 'bug']
    
    if any(word in text for word in critical_keywords):
        priority = "Critical"
    elif any(word in text for word in high_keywords):
        priority = "High"
    elif sentiment_score < -0.3: 
        # If user is angry/negative, bump priority
        priority = "High"
    else:
        priority = "Low"

    # 3. Knowledge Base Matching (The "Suggested Fix")
    # This acts like a simple Expert System
    suggested_fix = "Assigning to general support queue for review."
    
    knowledge_base = {
        "password": "Ask user to visit /reset-password. Check Active Directory status.",
        "login": "Check if user account is locked. Verify network connection.",
        "internet": "Request user to restart router. Ping gateway IP.",
        "wifi": "Update network drivers. Check signal strength.",
        "printer": "Clear print spooler. Check paper tray.",
        "crash": "Check application logs in Event Viewer. Reinstall latest patch.",
        "slow": "Clear browser cache and cookies. Check RAM usage."
    }
    
    # Find the first matching keyword in our knowledge base
    for key, fix in knowledge_base.items():
        if key in text:
            suggested_fix = fix
            break
            
    return priority, suggested_fix

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit_ticket():
    title = request.form.get('title')
    description = request.form.get('description')
    
    # Run our local analysis
    priority, suggested_fix = analyze_ticket(title, description)
    
    new_ticket = Ticket(
        title=title, 
        description=description, 
        priority=priority, 
        ai_suggested_fix=suggested_fix
    )
    db.session.add(new_ticket)
    db.session.commit()
    
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    tickets = Ticket.query.order_by(
        db.case(
            (Ticket.priority == 'Critical', 1),
            (Ticket.priority == 'High', 2),
            (Ticket.priority == 'Medium', 3),
            (Ticket.priority == 'Low', 4),
            else_=5
        )
    ).all()
    return render_template('dashboard.html', tickets=tickets)

if __name__ == '__main__':
    app.run(debug=True)