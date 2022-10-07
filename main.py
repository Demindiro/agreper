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
    return render_template(
        'subforum.html',
        title = title,
        forum_id = forum_id,
        description = description,
        threads = threads,
    )

@app.route('/thread/<int:thread_id>/')
def thread(thread_id):
    user_id = session.get('user_id')
    title, text, author, author_id, comments = db.get_thread(thread_id)
    comments = create_comment_tree(comments)
    return render_template(
        'thread.html',
        title = title,
        text = text,
        author = author,
        comments = comments,
        manage = author_id == user_id,
    )

@app.route('/comment/<int:comment_id>/')
def comment(comment_id):
    user_id = session.get('user_id')
    thread_id, parent_id, title, comments = db.get_subcomments(comment_id)
    comments = create_comment_tree(comments)
    return render_template(
        'comments.html',
        title = title,
        comments = comments,
        parent_id = parent_id,
        thread_id = thread_id,
    )

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

@app.route('/user/<int:user_id>/')
def user_info(user_id):
    name, about = db.get_user_public_info(user_id)
    return render_template(
        'user_info.html',
        title = 'Profile',
        name = name,
        about = about
    )

@app.route('/forum/<int:forum_id>/new/', methods = ['GET', 'POST'])
def new_thread(forum_id):
    user_id = session.get('user_id')
    if user_id is None:
        return redirect(url_for('login'))

    if request.method == 'POST':
        id, = db.add_thread(user_id, forum_id, request.form['title'], request.form['text'], time.time_ns())
        flash('Created thread', 'success')
        return redirect(url_for('thread', thread_id = id))

    return render_template(
        'new_thread.html',
        title = 'Create new thread',
    )

@app.route('/thread/<int:thread_id>/confirm_delete/')
def confirm_delete_thread(thread_id):
    title, = db.get_thread_title(thread_id)
    return render_template(
        'confirm_delete_thread.html',
        title = 'Delete thread',
        thread_title = title,
    )

@app.route('/thread/<int:thread_id>/delete/', methods = ['POST'])
def delete_thread(thread_id):
    db.delete_thread(thread_id)
    flash('Thread has been deleted', 'success')
    return redirect(url_for('index'))

@app.route('/thread/<int:thread_id>/comment/', methods = ['POST'])
def add_comment(thread_id):
    user_id = session.get('user_id')
    if user_id is None:
        return redirect(url_for('login'))

    if db.add_comment_to_thread(thread_id, user_id, request.form['text'], time.time_ns()):
        flash('Added comment', 'success')
    else:
        flash('Failed to add comment', 'error')
    return redirect(url_for('thread', thread_id = thread_id))

@app.route('/comment/<int:comment_id>/comment/', methods = ['POST'])
def add_comment_parent(comment_id):
    user_id = session.get('user_id')
    if user_id is None:
        return redirect(url_for('login'))

    if db.add_comment_to_comment(comment_id, user_id, request.form['text'], time.time_ns()):
        flash('Added comment', 'success')
    else:
        flash('Failed to add comment', 'error')
    return redirect(url_for('comment', comment_id = comment_id))


class Comment:
    def __init__(self, id, author, text):
        self.id = id
        self.author = author
        self.text = text
        self.children = []

def create_comment_tree(comments):
    # Collect comments first, then build the tree in case we encounter a child before a parent
    comment_map = {
        comment_id: (Comment(comment_id, author, text), parent_id)
        for comment_id, parent_id, author, text
        in comments
    }
    root = []
    for comment, parent_id in comment_map.values():
        parent = comment_map.get(parent_id)
        if parent is not None:
            parent[0].children.append(comment)
        else:
            root.append(comment)
    return root
