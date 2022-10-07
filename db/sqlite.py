import sqlite3

class DB:
    def __init__(self, conn):
        self.conn = conn
        pass

    def get_forums(self):
        return self._db().execute('''
            select f.forum_id, name, description, thread_id, title, update_time
            from forums f
            left join threads t
            on t.thread_id = (
              select tt.thread_id
              from threads tt
              where f.forum_id = tt.forum_id
              order by update_time desc
              limit 1
            )
            '''
        )

    def get_forum(self, forum_id):
        return self._db().execute('''
            select name, description
            from forums
            where forum_id = ?
            ''',
            (forum_id,)
        ).fetchone()

    def get_threads(self, forum_id):
        return self._db().execute('''
            select t.thread_id, title, t.create_time, t.update_time, t.author_id, name, count(1)
            from threads t, users, comments c
            where forum_id = ? and user_id = t.author_id and t.thread_id = c.thread_id
            group by t.thread_id
            ''',
            (forum_id,)
        )

    def get_thread(self, thread):
        db = self._db()
        title, text, author, author_id, create_time, modify_time = db.execute('''
            select title, text, name, author_id, create_time, modify_time
            from threads, users
            where thread_id = ? and author_id = user_id
            ''',
            (thread,)
        ).fetchone()
        comments = db.execute('''
            select comment_id, parent_id, name, text, create_time, modify_time
            from comments, users
            where thread_id = ? and author_id = user_id
            ''',
            (thread,)
        )
        return title, text, author, author_id, create_time, modify_time, comments

    def get_thread_title(self, thread_id):
        return self._db().execute('''
            select title
            from threads
            where thread_id = ?
            ''',
            (thread_id,)
        ).fetchone()

    def get_recent_threads(self, limit):
        return self._db().execute('''
            select thread_id, title, modify_date
            from threads
            order by modify_date
            limit ?
            ''',
            (limit,)
        )

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
            select id, parent_id, name, text, create_time, modify_time from descendant_of, comments, users
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

    def delete_thread(self, user_id, thread_id):
        db = self._db()
        c = db.cursor()
        c.execute('''
            delete
            from threads
            where thread_id = ? and author_id = ?
            ''',
            (thread_id, user_id)
        )
        db.commit()
        return c.rowcount > 0

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
        if c.rowcount > 0:
            print('SHIT')
            c.execute('''
                update threads
                set update_time = ?
                where thread_id = ?
                ''',
                (time, thread_id)
            )
            db.commit()
            return True
        return False

    def add_comment_to_comment(self, parent_id, author_id, text, time):
        db = self._db()
        c = db.cursor()
        c.execute('''
            insert into comments(thread_id, parent_id, author_id, text, create_time, modify_time)
            select thread_id, ?, ?, ?, ?, ?
            from comments
            where comment_id = ?
            ''',
            (parent_id, author_id, text, time, time, parent_id)
        )
        if c.rowcount > 0:
            c.execute('''
                update threads
                set update_time = ?
                where threads.thread_id = (
                  select c.thread_id
                  from comments c
                  where comment_id = ?
                )
                ''',
                (time, parent_id)
            )
            db.commit()
            return True
        return False

    def _db(self):
        return sqlite3.connect(self.conn)
