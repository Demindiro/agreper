from flask import Flask, render_template, session, request, redirect, url_for, flash, g
from db.sqlite import DB
import os
import passlib.hash
import time
from datetime import datetime

app = Flask(__name__)
db = DB(os.getenv('DB'))
NAME = 'Agrepy'

# TODO config file
app.config['SECRET_KEY'] = 'totally random'
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True

@app.route('/')
def index():
    return render_template('index.html', title = NAME, forums = db.get_forums())

@app.route('/forum/<int:forum_id>/')
def forum(forum_id):
    title, description = db.get_forum(forum_id)
    threads = db.get_threads(forum_id)
    return render_template(
        'forum.html',
        title = title,
        forum_id = forum_id,
        description = description,
        threads = threads,
    )

@app.route('/thread/<int:thread_id>/')
def thread(thread_id):
    user_id = session.get('user_id')
    title, text, author, author_id, create_time, modify_time, comments = db.get_thread(thread_id)
    comments = create_comment_tree(comments)
    return render_template(
        'thread.html',
        title = title,
        text = text,
        author = author,
        author_id = author_id,
        thread_id = thread_id,
        create_time = create_time,
        modify_time = modify_time,
        comments = comments,
    )

@app.route('/comment/<int:comment_id>/')
def comment(comment_id):
    user_id = session.get('user_id')
    thread_id, parent_id, title, comments = db.get_subcomments(comment_id)
    comments = create_comment_tree(comments)
    reply_comment, = comments
    comments = reply_comment.children
    reply_comment.children = []
    return render_template(
        'comments.html',
        title = title,
        reply_comment = reply_comment,
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
        about = request.form['about'].replace('\r', '')
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
        id, = db.add_thread(user_id, forum_id, request.form['title'], request.form['text'].replace('\r', ''), time.time_ns())
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
    user_id = session.get('user_id')
    if user_id is None:
        return redirect(url_for('login'))

    if db.delete_thread(user_id, thread_id):
        flash('Thread has been deleted', 'success')
    else:
        flash('Thread could not be removed', 'error')
        # TODO return 403, maybe?
    return redirect(url_for('index'))

@app.route('/thread/<int:thread_id>/comment/', methods = ['POST'])
def add_comment(thread_id):
    user_id = session.get('user_id')
    if user_id is None:
        return redirect(url_for('login'))

    if db.add_comment_to_thread(thread_id, user_id, request.form['text'].replace('\r', ''), time.time_ns()):
        flash('Added comment', 'success')
    else:
        flash('Failed to add comment', 'error')
    return redirect(url_for('thread', thread_id = thread_id))

@app.route('/comment/<int:comment_id>/comment/', methods = ['POST'])
def add_comment_parent(comment_id):
    user_id = session.get('user_id')
    if user_id is None:
        return redirect(url_for('login'))

    if db.add_comment_to_comment(comment_id, user_id, request.form['text'].replace('\r', ''), time.time_ns()):
        flash('Added comment', 'success')
    else:
        flash('Failed to add comment', 'error')
    return redirect(url_for('comment', comment_id = comment_id))

@app.route('/comment/<int:comment_id>/confirm_delete/')
def confirm_delete_comment(comment_id):
    title, text = db.get_comment(comment_id)
    return render_template(
        'confirm_delete_comment.html',
        title = 'Delete comment',
        thread_title = title,
        text = text,
    )

@app.route('/comment/<int:comment_id>/delete/', methods = ['POST'])
def delete_comment(comment_id):
    user_id = session.get('user_id')
    if user_id is None:
        return redirect(url_for('login'))

    if db.delete_comment(user_id, comment_id):
        flash('Comment has been deleted', 'success')
    else:
        flash('Comment could not be removed', 'error')
        # TODO return 403, maybe?
    return redirect(url_for('index'))

@app.route('/thread/<int:thread_id>/edit', methods = ['GET', 'POST'])
def edit_thread(thread_id):
    user_id = session.get('user_id')
    if user_id is None:
        return redirect(url_for('login'))

    if request.method == 'POST':
        if db.modify_thread(
            thread_id,
            user_id,
            request.form['title'],
            request.form['text'].replace('\r', ''),
            time.time_ns(),
        ):
            flash('Thread has been edited', 'success')
        else:
            flash('Thread could not be edited', 'error')
        return redirect(url_for('thread', thread_id = thread_id))

    title, text = db.get_thread_title_text(thread_id)

    return render_template(
        'edit_thread.html',
        title = 'Edit thread',
        thread_title = title,
        text = text,
    )


class Comment:
    def __init__(self, id, author_id, author, text, create_time, modify_time, parent_id):
        self.id = id
        self.author_id = author_id
        self.author = author
        self.text = text
        self.children = []
        self.create_time = create_time
        self.modify_time = modify_time
        self.parent_id = parent_id

def create_comment_tree(comments):
    start = time.time();
    # Collect comments first, then build the tree in case we encounter a child before a parent
    comment_map = {
        comment_id: Comment(comment_id, author_id, author, text, create_time, modify_time, parent_id)
        for comment_id, parent_id, author_id, author, text, create_time, modify_time
        in comments
    }
    root = []
    # Build tree
    for comment in comment_map.values():
        parent = comment_map.get(comment.parent_id)
        if parent is not None:
            parent.children.append(comment)
        else:
            root.append(comment)
    # Sort each comment based on create time
    def sort_time(l):
        l.sort(key=lambda c: c.modify_time, reverse=True)
        for c in l:
            sort_time(c.children)
    sort_time(root)
    if __debug__:
        print('building tree with', len(comment_map), 'comments took', time.time() - start, 'seconds')
    return root


@app.context_processor
def utility_processor():
    def format_since(t):
        n = time.time_ns()
        if n < t:
            return 'In a distant future'

        # Try the sane thing first
        dt = (n - t) // 10 ** 9
        if dt < 1:
            return "less than a second ago"
        if dt < 2:
            return f"1 second ago"
        if dt < 60:
            return f"{dt} seconds ago"
        if dt < 119:
            return f"1 minute ago"
        if dt < 3600:
            return f"{dt // 60} minutes ago"
        if dt < 3600 * 2:
            return f"1 hour ago"
        if dt < 3600 * 24:
            return f"{dt // 3600} hours ago"
        if dt < 3600 * 24 * 31:
            return f"{dt // (3600 * 24)} days ago"

        # Try some very rough estimate, whatever
        f = lambda x: datetime.utcfromtimestamp(x // 10 ** 9)
        n, t = f(n), f(t)
        def f(x, y, s):
            return f'{y - x} {s}{"s" if y - x > 1 else ""} ago'
        if t.year < n.year:
            return f(t.year, n.year, "year")
        if t.month < n.month:
            return f(t.month, n.month, "month")
        # This shouldn't be reachable, but it's still better to return something
        return "incredibly long ago"

    def minimd(text):
        # Replace angle brackets to prevent XSS
        # Also replace ampersands to prevent surprises.
        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        # Split into paragraphs
        paragraphs = text.split('\n\n')
        paragraphs = map(lambda l: l if not l.startswith('  ') else f'<pre>{l}</pre>', paragraphs)
        paragraphs = map(lambda l: f'<p>{l}</p>', paragraphs)
        # Glue together again
        return ''.join(paragraphs)

    return {
        'format_since': format_since,
        'minimd': minimd,
    }
