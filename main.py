VERSION = 'agreper-v0.1'
# TODO put in config table
THREADS_PER_PAGE = 50

from flask import Flask, render_template, session, request, redirect, url_for, flash, g
from db.sqlite import DB
import os, sys, subprocess
import passlib.hash, secrets
import time
from datetime import datetime
import captcha, password, minimd

app = Flask(__name__)
db = DB(os.getenv('DB'))

class Config:
    pass
config = Config()
config.version, config.server_name, config.server_description, app.config['SECRET_KEY'], config.captcha_key, config.registration_enabled = db.get_config()

if config.version != VERSION:
    print(f'Incompatible version {config.version} (expected {VERSION})')
    sys.exit(1)

class Role:
    USER = 0
    MODERATOR = 1
    ADMIN = 2

@app.route('/')
def index():
    return render_template(
        'index.html',
        title = config.server_name,
        description = config.server_description,
        config = config,
        user = get_user(),
        forums = db.get_forums()
    )

@app.route('/forum/<int:forum_id>/')
def forum(forum_id):
    title, description = db.get_forum(forum_id)
    offset = int(request.args.get('p', 0))
    threads = [*db.get_threads(forum_id, offset, THREADS_PER_PAGE + 1)]
    if len(threads) == THREADS_PER_PAGE + 1:
        threads.pop()
        next_page = offset + THREADS_PER_PAGE
    else:
        next_page = None
    return render_template(
        'forum.html',
        title = title,
        user = get_user(),
        config = config,
        forum_id = forum_id,
        description = description,
        threads = threads,
        next_page = next_page,
        prev_page = max(offset - THREADS_PER_PAGE, 0) if offset > 0 else None,
    )

@app.route('/thread/<int:thread_id>/')
def thread(thread_id):
    user_id = session.get('user_id')
    title, text, author, author_id, create_time, modify_time, comments = db.get_thread(thread_id)
    comments = create_comment_tree(comments)
    return render_template(
        'thread.html',
        title = title,
        config = config,
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
        config = config,
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
            if password.verify(request.form['password'], hash):
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
        config = config,
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
        about = trim_text(request.form['about'])
        db.set_user_private_info(user.id, about)
        flash('Updated profile', 'success')
    else:
        about, = db.get_user_private_info(user.id)

    return render_template(
        'user_edit.html',
        title = 'Edit profile',
        config = config,
        user = user,
        about = about
    )

@app.route('/user/edit/password/', methods = ['POST'])
def user_edit_password():
    user_id = session.get('user_id')
    if user_id is None:
        return redirect(url_for('login'))

    new = request.form['new']
    if len(new) < 8:
        flash('New password must be at least 8 characters long', 'error')
    else:
        hash, = db.get_user_password_by_id(user_id)
        if password.verify(request.form['old'], hash):
            if db.set_user_password(user_id, password.hash(new)):
                flash('Updated password', 'success')
            else:
                flash('Failed to update password', 'error')
        else:
            flash('Old password does not match', 'error')
    return redirect(url_for('user_edit'))

@app.route('/user/<int:user_id>/')
def user_info(user_id):
    name, about = db.get_user_public_info(user_id)
    return render_template(
        'user_info.html',
        title = 'Profile',
        config = config,
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
        title, text = request.form['title'], trim_text(request.form['text'])
        if title == '' or text == '':
            flash('Title and text may not be empty', 'error')
            return redirect(url_for('forum', forum_id = forum_id))
        id = db.add_thread(user_id, forum_id, title, text, time.time_ns())
        if id is None:
            flash('Failed to create thread', 'error')
            return redirect(url_for('forum', forum_id = forum_id))
        else:
            id, = id
            flash('Created thread', 'success')
            return redirect(url_for('thread', thread_id = id))

    return render_template(
        'new_thread.html',
        title = 'Create new thread',
        config = config,
        user = get_user(),
    )

@app.route('/thread/<int:thread_id>/confirm_delete/')
def confirm_delete_thread(thread_id):
    title, = db.get_thread_title(thread_id)
    return render_template(
        'confirm_delete_thread.html',
        title = 'Delete thread',
        config = config,
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

    text = trim_text(request.form['text'])
    if text == '':
        flash('Text may not be empty', 'error')
    elif db.add_comment_to_thread(thread_id, user_id, text, time.time_ns()):
        flash('Added comment', 'success')
    else:
        flash('Failed to add comment', 'error')
    return redirect(url_for('thread', thread_id = thread_id))

@app.route('/comment/<int:comment_id>/comment/', methods = ['POST'])
def add_comment_parent(comment_id):
    user_id = session.get('user_id')
    if user_id is None:
        return redirect(url_for('login'))

    text = trim_text(request.form['text'])
    if text == '':
        flash('Text may not be empty', 'error')
    elif db.add_comment_to_comment(comment_id, user_id, text, time.time_ns()):
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
        config = config,
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
        title, text = request.form['title'], trim_text(request.form['text'])
        if title == '' or text == '':
            flash('Title and text may not be empty', 'error')
        elif db.modify_thread(
            thread_id,
            user_id,
            title,
            text,
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
        config = config,
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
        text = trim_text(request.form['text'])
        if text == '':
            flash('Text may not be empty', 'error')
        elif db.modify_comment(
            comment_id,
            user_id,
            trim_text(request.form['text']),
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
        config = config,
        user = get_user(),
        thread_title = title,
        text = text,
    )

@app.route('/register/', methods = ['GET', 'POST'])
def register():
    if request.method == 'POST':
        username, passwd = request.form['username'], request.form['password']
        if len(username) < 3:
            flash('Username must be at least 3 characters long', 'error')
        elif len(passwd) < 8:
            flash('Password must be at least 8 characters long', 'error')
        elif not captcha.verify(
            config.captcha_key,
            request.form['captcha'],
            request.form['answer'],
        ):
            flash('CAPTCHA answer is incorrect', 'error')
        elif not db.register_user(username, password.hash(passwd), time.time_ns()):
            flash('Failed to create account (username may already be taken)', 'error')
        else:
            flash('Account has been created. You can login now.', 'success')
            return redirect(url_for('index'))

    capt, answer = captcha.generate(config.captcha_key)
    return render_template(
        'register.html',
        title = 'Register',
        config = config,
        user = get_user(),
        captcha = capt,
        answer = answer,
    )

@app.route('/admin/')
def admin():
    chk, user = _admin_check()
    if not chk:
        return user

    return render_template(
        'admin/index.html',
        title = 'Admin panel',
        config = config,
        forums = db.get_forums(),
        users = db.get_users(),
    )

@app.route('/admin/query/', methods = ['GET', 'POST'])
def admin_query():
    chk, user = _admin_check()
    if not chk:
        return user

    try:
        rows, rowcount = db.query(request.form['q']) if request.method == 'POST' else []
        if rowcount > 0:
            flash(f'{rowcount} rows changed', 'success')
    except Exception as e:
        flash(e, 'error')
        rows = []
    return render_template(
        'admin/query.html',
        title = 'Query',
        config = config,
        rows = rows,
    )

@app.route('/admin/forum/<int:forum_id>/edit/<string:what>/', methods = ['POST'])
def admin_edit_forum(forum_id, what):
    chk, user = _admin_check()
    if not chk:
        return user

    try:
        if what == 'description':
            res = db.set_forum_description(forum_id, trim_text(request.form['description']))
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
    chk, user = _admin_check()
    if not chk:
        return user

    try:
        db.add_forum(request.form['name'], trim_text(request.form['description']))
        flash('Added forum', 'success')
    except Exception as e:
        flash(str(e), 'error')
    return redirect(url_for('admin'))

@app.route('/admin/config/edit/', methods = ['POST'])
def admin_edit_config():
    chk, user = _admin_check()
    if not chk:
        return user

    try:
        db.set_config(
            request.form['server_name'],
            trim_text(request.form['server_description']),
            'registration_enabled' in request.form,
        )
        flash('Updated config. Refresh the page to see the changes.', 'success')
        restart()
    except Exception as e:
        flash(str(e), 'error')
    return redirect(url_for('admin'))

@app.route('/admin/config/new_secrets/', methods = ['POST'])
def admin_new_secrets():
    chk, user = _admin_check()
    if not chk:
        return user

    secret_key = secrets.token_urlsafe(30)
    captcha_key = secrets.token_urlsafe(30)
    try:
        db.set_config_secrets(secret_key, captcha_key)
        flash('Changed secrets. You will be logged out.', 'success')
        restart()
    except Exception as e:
        flash(str(e), 'error')
    return redirect(url_for('admin'))

@app.route('/admin/user/<int:user_id>/ban/', methods = ['POST'])
def admin_ban_user(user_id):
    chk, user = _admin_check()
    if not chk:
        return user

    d, t = request.form['days'], request.form['time']
    d = 0 if d == '' else int(d)
    h, m = (0, 0) if t == '' else map(int, t.split(':'))
    until = time.time_ns() + (d * 24 * 60 + h * 60 + m) * (60 * 10**9)
    until = min(until, 0xffff_ffff_ffff_ffff)

    try:
        if db.set_user_ban(user_id, until):
            flash('Banned user', 'success')
        else:
            flash('Failed to ban user', 'error')
    except Exception as e:
        flash(str(e), 'error')
    return redirect(url_for('admin'))

@app.route('/admin/user/<int:user_id>/unban/', methods = ['POST'])
def admin_unban_user(user_id):
    chk, user = _admin_check()
    if not chk:
        return user

    try:
        if db.set_user_ban(user_id, None):
            flash('Unbanned user', 'success')
        else:
            flash('Failed to unban user', 'error')
    except Exception as e:
        flash(str(e), 'error')
    return redirect(url_for('admin'))

@app.route('/admin/user/new/', methods = ['POST'])
def admin_new_user():
    try:
        name, passwd = request.form['name'], request.form['password']
        if name == '' or passwd == '':
            flash('Name and password may not be empty')
        elif db.add_user(name, password.hash(passwd), time.time_ns()):
            flash('Added user', 'success')
        else:
            flash('Failed to add user', 'error')
    except Exception as e:
        flash(str(e), 'error')
    return redirect(url_for('admin'))

@app.route('/admin/restart/', methods = ['POST'])
def admin_restart():
    chk, user = _admin_check()
    if not chk:
        return user

    restart()
    return redirect(url_for('admin'))


def _admin_check():
    user = get_user()
    if user is None:
        return False, redirect(url_for('login'))
    if not user.is_admin():
        return False, ('<h1>Forbidden</h1>', 403)
    return True, user


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


class User:
    def __init__(self, id, name, role, banned_until):
        self.id = id
        self.name = name
        self.role = role
        self.banned_until = banned_until

    def is_moderator(self):
        return self.role in (Role.ADMIN, Role.MODERATOR)

    def is_admin(self):
        return self.role == Role.ADMIN

    def is_banned(self):
        return self.banned_until > time.time_ns()

def get_user():
    id = session.get('user_id')
    if id is not None:
        name, role, banned_until = db.get_user_name_role_banned(id)
        return User(id, name, role, banned_until)
    return None


@app.context_processor
def utility_processor():
    def _format_time_delta(n, t):
        # Try the sane thing first
        dt = (n - t) // 10 ** 9
        if dt < 1:
            return "less than a second"
        if dt < 2:
            return f"1 second"
        if dt < 60:
            return f"{dt} seconds"
        if dt < 119:
            return f"1 minute"
        if dt < 3600:
            return f"{dt // 60} minutes"
        if dt < 3600 * 2:
            return f"1 hour"
        if dt < 3600 * 24:
            return f"{dt // 3600} hours"
        if dt < 3600 * 24 * 31:
            return f"{dt // (3600 * 24)} days"

        # Try some very rough estimate, whatever
        f = lambda x: datetime.utcfromtimestamp(x // 10 ** 9)
        n, t = f(n), f(t)
        def f(x, y, s):
            return f'{y - x} {s}{"s" if y - x > 1 else ""}'
        if t.year < n.year:
            return f(t.year, n.year, "year")
        if t.month < n.month:
            return f(t.month, n.month, "month")
        assert False, 'unreachable'

    def format_since(t):
        n = time.time_ns()
        if n < t:
            return 'in a distant future'
        return _format_time_delta(n, t) + ' ago'

    def format_until(t):
        n = time.time_ns()
        if t <= n:
            return 'in a distant past'
        return _format_time_delta(t, n)

    def format_time(t):
        return datetime.utcfromtimestamp(t / 10 ** 9).replace(microsecond=0)

    return {
        'format_since': format_since,
        'format_time': format_time,
        'format_until': format_until,
        'minimd': minimd.html,
    }


def restart():
    '''
    Shut down *all* workers and spawn new ones.
    This is necessary on e.g. a configuration change.

    Since restarting workers depends is platform-dependent this task is delegated to an external
    program.
    '''
    r = subprocess.call(['./restart.sh'])
    if r == 0:
        flash('Restart script exited successfully', 'success')
    else:
        flash(f'Restart script exited with error (code {r})', 'error')

def trim_text(s):
    '''
    Because browsers LOVE \\r, trailing whitespace etc.
    '''
    return s.strip().replace('\r', '')
