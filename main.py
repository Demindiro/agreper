from flask import Flask, render_template, session, request, redirect, url_for, flash, g
from db.sqlite import DB
import os
import passlib.hash
import time
from datetime import datetime
import captcha

app = Flask(__name__)
db = DB(os.getenv('DB'))
NAME = 'Agrepy'

# TODO config file
app.config['SECRET_KEY'] = 'totally random'
captcha_key = 'piss off bots'
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True

class Role:
    USER = 0
    MODERATOR = 1
    ADMIN = 2

@app.route('/')
def index():
    return render_template(
        'index.html',
        title = NAME,
        user = get_user(),
        forums = db.get_forums()
    )

@app.route('/forum/<int:forum_id>/')
def forum(forum_id):
    title, description = db.get_forum(forum_id)
    threads = db.get_threads(forum_id)
    return render_template(
        'forum.html',
        title = title,
        user = get_user(),
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
        user = get_user(),
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
    thread_id, parent_id, title, comments = db.get_subcomments(comment_id)
    comments = create_comment_tree(comments)
    reply_comment, = comments
    comments = reply_comment.children
    reply_comment.children = []
    return render_template(
        'comments.html',
        title = title,
        user = get_user(),
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
            if verify_password(request.form['password'], hash):
                flash('Logged in', 'success')
                session['user_id'] = id
                return redirect(url_for('index'))
        else:
            # Sleep to reduce effectiveness of bruteforce
            time.sleep(0.1)
        flash('Username or password is invalid', 'error')
    return render_template(
        'login.html',
        title = 'Login',
        user = get_user()
    )

@app.route('/logout/')
def logout():
    session.pop('user_id')
    return redirect(url_for('index'))

@app.route('/user/', methods = ['GET', 'POST'])
def user_edit():
    user = get_user()
    if user is None:
        return redirect(url_for('login'))

    if request.method == 'POST':
        about = request.form['about'].replace('\r', '')
        db.set_user_private_info(user.id, about)
        flash('Updated profile', 'success')
    else:
        about, = db.get_user_private_info(user.id)

    return render_template(
        'user_edit.html',
        title = 'Edit profile',
        user = user,
        about = about
    )

@app.route('/user/<int:user_id>/')
def user_info(user_id):
    name, about = db.get_user_public_info(user_id)
    return render_template(
        'user_info.html',
        title = 'Profile',
        user = get_user(),
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
        user = get_user(),
    )

@app.route('/thread/<int:thread_id>/confirm_delete/')
def confirm_delete_thread(thread_id):
    title, = db.get_thread_title(thread_id)
    return render_template(
        'confirm_delete_thread.html',
        title = 'Delete thread',
        user = get_user(),
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
        user = get_user(),
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

@app.route('/thread/<int:thread_id>/edit/', methods = ['GET', 'POST'])
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
        user = get_user(),
        thread_title = title,
        text = text,
    )

@app.route('/comment/<int:comment_id>/edit/', methods = ['GET', 'POST'])
def edit_comment(comment_id):
    user_id = session.get('user_id')
    if user_id is None:
        return redirect(url_for('login'))

    if request.method == 'POST':
        if db.modify_comment(
            comment_id,
            user_id,
            request.form['text'].replace('\r', ''),
            time.time_ns(),
        ):
            flash('Comment has been edited', 'success')
        else:
            flash('Comment could not be edited', 'error')
        return redirect(url_for('comment', comment_id = comment_id))

    title, text = db.get_comment(comment_id)

    return render_template(
        'edit_comment.html',
        title = 'Edit comment',
        user = get_user(),
        thread_title = title,
        text = text,
    )

@app.route('/register/', methods = ['GET', 'POST'])
def register():
    if request.method == 'POST':
        username, password = request.form['username'], request.form['password']
        if len(username) < 3:
            flash('Username must be at least 3 characters long', 'error')
        elif len(password) < 8:
            flash('Password must be at least 8 characters long', 'error')
        elif not captcha.verify(
            captcha_key,
            request.form['captcha'],
            request.form['answer'],
        ):
            flash('CAPTCHA answer is incorrect', 'error')
        elif not db.add_user(username, hash_password(password), time.time_ns()):
            flash('Failed to create account (username may already be taken)', 'error')
        else:
            flash('Account has been created. You can login now.', 'success')
            return redirect(url_for('index'))

    capt, answer = captcha.generate(captcha_key)
    return render_template(
        'register.html',
        title = 'Register',
        user = get_user(),
        captcha = capt,
        answer = answer,
    )

@app.route('/admin/')
def admin():
    user = get_user()
    if user is None:
        return redirect(url_for('login'))
    if not user.is_admin():
        return '<h1>Forbidden</h1>', 403

    return render_template(
        'admin/index.html',
        title = 'Admin panel',
        forums = db.get_forums(),
        users = db.get_users(),
    )

@app.route('/admin/query/', methods = ['GET', 'POST'])
def admin_query():
    user = get_user()
    if user is None:
        return redirect(url_for('login'))
    if not user.is_admin():
        return '<h1>Forbidden</h1>', 403

    try:
        rows = db.query(request.form['q']) if request.method == 'POST' else []
    except Exception as e:
        flash(e, 'error')
        rows = []
    return render_template(
        'admin/query.html',
        title = 'Query',
        rows = rows,
    )

@app.route('/admin/forum/<int:forum_id>/edit/<string:what>/', methods = ['POST'])
def admin_edit_forum(forum_id, what):
    try:
        if what == 'description':
            res = db.set_forum_description(forum_id, request.form['description'].replace('\r', ''))
        elif what == 'name':
            res = db.set_forum_name(forum_id, request.form['name'])
        else:
            flash(f'Unknown property "{what}"', 'error')
            res = None
        if res is True:
            flash(f'Updated {what}', 'success')
        elif res is False:
            flash(f'Failed to update {what}', 'error')
    except Exception as e:
        flash(e, 'error')
    return redirect(url_for('admin'))

@app.route('/admin/forum/new/', methods = ['POST'])
def admin_new_forum():
    try:
        db.add_forum(request.form['name'], request.form['description'].replace('\r', ''))
        flash('Added forum', 'success')
    except Exception as e:
        flash(str(e), 'error')
    return redirect(url_for('admin'))


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
    comments = [*comments]
    print(comments)
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


class User:
    def __init__(self, id, name, role):
        self.id = id
        self.name = name
        self.role = role

    def is_moderator(self):
        return self.role in (Role.ADMIN, Role.MODERATOR)

    def is_admin(self):
        return self.role == Role.ADMIN

def get_user():
    id = session.get('user_id')
    if id is not None:
        name, role = db.get_user_name_role(id)
        return User(id, name, role)
    return None


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

    def format_time(t):
        return datetime.utcfromtimestamp(t / 10 ** 9)

    def minimd(text):
        # Replace angle brackets to prevent XSS
        # Also replace ampersands to prevent surprises.
        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        # Split into paragraphs
        paragraphs = map(lambda l: l.strip('\n'), text.split('\n\n'))
        paragraphs = map(lambda l: l if not l.startswith('  ') else f'<pre>{l}</pre>', paragraphs)
        paragraphs = map(lambda l: f'<p>{l}</p>', paragraphs)
        # Glue together again
        return ''.join(paragraphs)

    return {
        'format_since': format_since,
        'format_time': format_time,
        'minimd': minimd,
    }


def hash_password(password):
    return passlib.hash.argon2.hash(password)

def verify_password(password, hash):
    return passlib.hash.argon2.verify(password, hash)
