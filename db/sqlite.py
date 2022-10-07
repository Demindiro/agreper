import sqlite3

class DB:
    def __init__(self, conn):
        self.conn = conn
        pass

    def get_subforums(self):
        return self._db().execute('select forum_id, name, description from subforums').fetchall()

    def get_subforum(self, subforum):
        return self._db().execute('select name, description from subforums where forum_id = ?', (subforum,)).fetchone()

    def get_threads(self, subforum):
        return self._db().execute('select thread_id, title from threads where forum_id = ?', (subforum,)).fetchall()

    def get_thread(self, thread):
        db = self._db()
        title, text, author = db.execute('''
            select title, text, name
            from threads, users
            where thread_id = ? and author_id = user_id
            ''',
            (thread,)
        ).fetchone()
        comments = db.execute('''
            select comment_id, parent_id, name, text
            from comments, users
            where thread_id = ? and author_id = user_id
            ''',
            (thread,)
        ).fetchall()
        return title, text, author, comments

    def get_comments(self, thread):
        return self._db().execute('''
            select text
            from comments
            where thread_id = ?
            ''',
            (thread,)
        ).fetchall()

    def get_comment_tree(self, comment):
        db = self._db()
        parent = db.execute('select text from comments where comment_id = ?', (comment,)).fetchall()
        children = db.execute('select text from comments where parent_id = ?', (comment,)).fetchall()
        print(parent, children)
        return str(parent) + str(children)
        return parent

    def get_user_password(self, username):
        return self._db().execute('''
            select user_id, password
            from users
            where name = ?
            ''',
            (username,)
        ).fetchone()

    def get_user_public_info(self, user_id):
        return self._db().execute('''
            select name, about
            from users
            where user_id = ?
            ''',
            (user_id,)
        ).fetchone()

    def get_user_private_info(self, user_id):
        return self._db().execute('''
            select about
            from users
            where user_id = ?
            ''',
            (user_id,)
        ).fetchone()

    def set_user_private_info(self, user_id, about):
        print('BROH', about)
        db = self._db()
        db.execute('''
            update users
            set about = ?
            where user_id = ?
            ''',
            (about, user_id)
        )
        db.commit()

    def _db(self):
        return sqlite3.connect(self.conn)
