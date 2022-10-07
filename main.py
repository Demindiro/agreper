from flask import Flask, render_template, session, request, redirect, url_for, flash
from db.sqlite import DB
import os
import passlib.hash
import time

app = Flask(__name__)
db = DB(os.getenv('DB'))
NAME = 'Agrepy'

# TODO config file
app.config['SECRET_KEY'] = 'totally random'

@app.route('/')
def index():
    return render_template('index.html', title = NAME, subforums = db.get_subforums())

@app.route('/forum/<int:forum_id>/')
def subforum(forum_id):
    title, description = db.get_subforum(forum_id)
    threads = db.get_threads(forum_id)
    return render_template('subforum.html', title = title, description = description, threads = threads)

@app.route('/thread/<int:thread_id>/')
def thread(thread_id):
    title, text, author, comments = db.get_thread(thread_id)
    comments = create_comment_tree(comments)
    return render_template('thread.html', title = title, text = text, author = author, comments = comments)

@app.route('/comment/<int:comment_id>/')
def comment(comment_id):
    #return str(db.get_comment_tree(comment_id)[0])
    return str(db.get_comment_tree(comment_id))

@app.route('/login/', methods = ['GET', 'POST'])
def login():
    if request.method == 'POST':
        v = db.get_user_password(request.form['username'])
        if v is not None:
            id, hash = v
            if passlib.hash.argon2.verify(request.form['password'], hash):
                flash('Logged in', 'success')
                session['user_id'] = id
                session['username'] = request.form['username']
                return redirect(url_for('index'))
        else:
            # Sleep to reduce effectiveness of bruteforce
            time.sleep(0.1)
        flash('Username or password is invalid', 'error')
        return render_template('login.html', title = "Login")
    return render_template('login.html', title = "Login")

@app.route('/logout/')
def logout():
    session.pop('user_id')
    return redirect(url_for('index'))

@app.route('/user/', methods = ['GET', 'POST'])
def user_edit():
    user_id = session.get('user_id')
    if user_id is None:
        return redirect(url_for('login'))

    if request.method == 'POST':
        about = request.form['about']
        db.set_user_private_info(user_id, about)
    else:
        about, = db.get_user_private_info(user_id)

    return render_template(
        'user_edit.html',
        name = session.get('username', '???'),
        title = 'Edit profile',
        about = about
    )

@app.route('/user/<int:user_id>')
def user_info(user_id):
    name, about = db.get_user_public_info(user_id)
    return render_template(
        'user_info.html',
        title = 'Profile',
        name = name,
        about = about
    )

class Comment:
    def __init__(self, author, text):
        self.author = author
        self.text = text
        self.children = []

def create_comment_tree(comments):
    root = []
    comment_map = {}
    for comment_id, parent_id, author, text in comments:
        comment = Comment(author, text)
        parent = comment_map.get(parent_id)
        if parent is not None:
            parent.children.append(comment)
        else:
            root.append(comment)
        comment_map[comment_id] = comment
    return root
