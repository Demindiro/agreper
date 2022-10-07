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

    def _db(self):
        return sqlite3.connect(self.conn)
