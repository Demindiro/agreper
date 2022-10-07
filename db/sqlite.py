import sqlite3

class DB:
    def __init__(self, conn):
        self.conn = conn
        pass

    def get_subforums(self):
        return self._db().execute('select forum_id, name, description from subforums')

    def get_subforum(self, subforum):
        return self._db().execute('select name, description from subforums where forum_id = ?', (subforum,)).fetchone()

    def get_threads(self, subforum):
        return self._db().execute('select thread_id, title from threads where forum_id = ?', (subforum,))

    def get_thread(self, thread):
        db = self._db()
        title, text, author, author_id = db.execute('''
            select title, text, name, author_id
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
        )
        return title, text, author, author_id, comments

    def get_thread_title(self, thread_id):
        return self._db().execute('''
            select title
            from threads
            where thread_id = ?
            ''',
            (thread_id,)
        ).fetchone()

    def get_comments(self, thread):
        return self._db().execute('''
            select text
            from comments
            where thread_id = ?
            ''',
            (thread,)
        )

    def get_subcomments(self, comment_id):
        db = self._db()
        thread_id, parent_id, title = db.execute('''
            select threads.thread_id, parent_id, title
            from threads, comments
            where comment_id = ? and threads.thread_id = comments.thread_id
            ''',
            (comment_id,)
        ).fetchone()
        # Recursive CTE, see https://www.sqlite.org/lang_with.html
        return thread_id, parent_id, title, db.execute('''
            with recursive
              descendant_of(id) as (
                select comment_id from comments where comment_id = ?
                union
                select comment_id from descendant_of, comments where id = parent_id
              )
            select id, parent_id, name, text from descendant_of, comments, users
            where id = comment_id and user_id = author_id
            ''',
            (comment_id,)
        )

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
        db = self._db()
        db.execute('''
            update users
            set about = ?
            where user_id = ?
            ''',
            (about, user_id)
        )
        db.commit()

    def add_thread(self, author_id, forum_id, title, text, time):
        db = self._db()
        c = db.cursor()
        c.execute('''
            insert into threads (author_id, forum_id, title, text,
                create_time, modify_time, update_time)
            values (?, ?, ?, ?, ?, ?, ?)
            ''',
            (author_id, forum_id, title, text, time, time, time)
        )
        rowid = c.lastrowid
        db.commit()
        return db.execute('''
            select thread_id
            from threads
            where rowid = ?
            ''',
            (rowid,)
        ).fetchone()

    def delete_thread(self, thread_id):
        db = self._db()
        db.execute('''
            delete
            from threads
            where thread_id = ?
            ''',
            (thread_id,)
        )
        db.commit()

    def add_comment_to_thread(self, thread_id, author_id, text, time):
        db = self._db()
        c = db.cursor()
        c.execute('''
            insert into comments(thread_id, author_id, text, create_time, modify_time)
            select ?, ?, ?, ?, ?
            from threads
            where thread_id = ?
            ''',
            (thread_id, author_id, text, time, time, thread_id)
        )
        rowid = c.lastrowid
        db.commit()
        return rowid is not None

    def add_comment_to_comment(self, parent_id, author_id, text, time):
        db = self._db()
        c = db.cursor()
        print(c.lastrowid, parent_id)
        c.execute('''
            insert into comments(thread_id, parent_id, author_id, text, create_time, modify_time)
            select thread_id, ?, ?, ?, ?, ?
            from comments
            where comment_id = ?
            ''',
            (parent_id, author_id, text, time, time, parent_id)
        )
        print(c.lastrowid)
        rowid = c.lastrowid
        db.commit()
        return rowid is not None

    def _db(self):
        return sqlite3.connect(self.conn)
