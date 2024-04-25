from flask import Flask, render_template, request, redirect, url_for
from flask_mysqldb import MySQL
from flask_socketio import SocketIO, emit
from collections import defaultdict
import time

app = Flask(__name__)
socketio = SocketIO(app)

# Configuration for MySQL database
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'MYsql#93134'
app.config['MYSQL_DB'] = 'distry2'

mysql = MySQL(app)

# Dictionary to store message counts and last message timestamp for each user
user_data = defaultdict(lambda: {'message_counts': defaultdict(int), 'last_message_time': 0})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/sevent')
def sevent():
    return render_template('sevent.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/team')
def team():
    return render_template('team.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/unity')
def unity():
    cur = mysql.connection.cursor()
    cur.execute("SELECT title FROM discussions ORDER BY created_at DESC")
    data = cur.fetchall()
    cur.close()
    return render_template('unity.html', discussions=data)

@app.route('/create_discussion', methods=['POST'])
def create_discussion():
    title = request.form['title']
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO discussions (title) VALUES (%s)", (title,))
    mysql.connection.commit()
    cur.close()
    return redirect('/unity')

@app.route('/chat/<discussion_title>')
def chat(discussion_title):
    return render_template('index.html', title=discussion_title)

@app.route('/discussion/<title>')
def discussion(title):
    return render_template('chat.html', title=title)

@app.route('/volunteer')
def volunteer():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM events ORDER BY id DESC")
    events = cur.fetchall()
    cur.close()
    return render_template('volunteer.html', events=events)

@app.route('/submit_event', methods=['POST'])
def submit_event():
    if request.method == 'POST':
        event_title = request.form['event_title']
        event_time = request.form['event_time']
        event_date = request.form['event_date']
        event_location = request.form['event_location']
        event_description = request.form['event_description']
        event_mnum = request.form['event_mnum']
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO events (title ,time, date, location, description, mobile_num) VALUES (%s, %s, %s, %s, %s, %s)", (event_title,  event_time, event_date, event_location, event_description, event_mnum))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('volunteer'))

@app.route('/apply/<int:event_id>', methods=['POST'])
def apply(event_id):
    if request.method == 'POST':
        applicant_name = request.form['name']
        applicant_number = request.form['number']
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO event_applications (event_id, applicant_name, applicant_number) VALUES (%s, %s, %s)", (event_id, applicant_name, applicant_number))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('volunteer'))

@socketio.on('connect')
def handle_connect():
    print('User Joined')

@socketio.on('message')
def handle_message(data):
    title = data['title']
    message = data['message']
    
    # Get the user's IP address from the request
    user_ip = request.remote_addr
    
    # Get the current timestamp
    current_time = time.time()
    
    # Get user's message data
    user_message_data = user_data[user_ip]
    
    # Check if the message has been sent more than 5 times in the last minute
    if current_time - user_message_data['last_message_time'] < 60:
        if user_message_data['message_counts'][message] >= 5:
            emit('error_message', {'message': "You can only send up to 5 identical messages per minute"}, room=request.sid)
            return
    
    # Increment message count for the user
    user_message_data['message_counts'][message] += 1
    
    # Reset message count if more than 1 minute has passed since the last message
    if current_time - user_message_data['last_message_time'] >= 60:
        user_message_data['message_counts'] = defaultdict(int)
    
    # Update the last message timestamp for the user
    user_message_data['last_message_time'] = current_time
    
    # Proceed to store the message in the database and emit it to all clients
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO messages (title, message) VALUES (%s, %s)", (title, message))
    mysql.connection.commit()
    cur.close()
    emit('new_message', {'message': message}, broadcast=True)

@socketio.on('join')
def handle_join(data):
    title = data['title']
    cur = mysql.connection.cursor()
    cur.execute("SELECT message FROM messages WHERE title = %s", (title,))
    messages = cur.fetchall()
    cur.close()
    for message in messages:
        emit('previous_message', {'message': message[0]})

if __name__ == '__main__':
    socketio.run(app, debug=True)
