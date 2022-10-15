import sqlite3

class DB:
    def __init__(self, conn):
        self.conn = conn
        pass

    def get_config(self):
        return self._db().execute('''
            select version, name, description, secret_key, captcha_key, registration_enabled from config
            '''
        ).fetchone()

    def get_forums(self):
        return self._db().execute('''
            select f.forum_id, name, description, thread_id, title, update_time
            from forums f
            left join threads t
            on t.thread_id = (
              select tt.thread_id
              from threads tt
              where f.forum_id = tt.forum_id and not tt.hidden
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

    def get_threads(self, forum_id, offset, limit, user_id):
        return self._db().execute('''
            select
              t.thread_id,
              title,
              t.create_time,
              t.update_time,
              t.author_id,
              name,
              count(c.thread_id),
              t.hidden
            from
              threads t,
              users
            left join
              comments c
            on
              t.thread_id = c.thread_id
            where forum_id = ?
              and user_id = t.author_id
              and (
                t.hidden = 0 or (
                  select 1 from users
                  where user_id = ?
                    and (
                      user_id = t.author_id
                      -- 1 = moderator, 2 = admin
                      or role in (1, 2)
                    )
                )
              )
            group by t.thread_id
            order by t.update_time desc
            limit ?
            offset ?
            ''',
            (forum_id, user_id, limit, offset)
        )

    def get_thread(self, thread):
        db = self._db()
        title, text, author, author_id, create_time, modify_time, hidden = db.execute('''
            select title, text, name, author_id, create_time, modify_time, hidden
            from threads, users
            where thread_id = ? and author_id = user_id
            ''',
            (thread,)
        ).fetchone()
        comments = db.execute('''
            select
              comment_id,
              parent_id,
              author_id,
              name,
              text,
              create_time,
              modify_time,
              hidden
            from comments
              left join users
              on author_id = user_id
            where thread_id = ?
            ''',
            (thread,)
        )
        return title, text, author, author_id, create_time, modify_time, comments, hidden

    def get_thread_title(self, thread_id):
        return self._db().execute('''
            select title
            from threads
            where thread_id = ?
            ''',
            (thread_id,)
        ).fetchone()

    def get_thread_title_text(self, thread_id):
        return self._db().execute('''
            select title, text
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

    def get_comment(self, comment_id):
        return self._db().execute('''
            select title, c.text
            from comments c, threads t
            where comment_id = ? and c.thread_id = t.thread_id
            ''',
            (comment_id,)
        ).fetchone()

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
            select
              id,
              parent_id,
              author_id,
              name,
              text,
              create_time,
              modify_time,
              hidden
            from
              descendant_of,
              comments,
              users
            where id = comment_id
              and user_id = author_id
            ''',
            (comment_id,)
        )

    def get_user_password(self, username):
        return self._db().execute('''
            select user_id, password
            from users
            where name = lower(?)
            ''',
            (username,)
        ).fetchone()

    def get_user_password_by_id(self, user_id):
        return self._db().execute('''
            select password
            from users
            where user_id = ?
            ''',
            (user_id,)
        ).fetchone()

    def set_user_password(self, user_id, password):
        return self.change_one('''
            update users
            set password = ?
            where user_id = ?
            ''',
            (password, user_id)
        )

    def get_user_public_info(self, user_id):
        return self._db().execute('''
            select name, about, banned_until
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

    def get_user_name_role_banned(self, user_id):
        return self._db().execute('''
            select name, role, banned_until
            from users
            where user_id = ?
            ''',
            (user_id,)
        ).fetchone()

    def get_user_name(self, user_id):
        return self._db().execute('''
            select name
            from users
            where user_id = ?
            ''',
            (user_id,)
        ).fetchone()

    def add_thread(self, author_id, forum_id, title, text, time):
        db = self._db()
        c = db.cursor()
        c.execute('''
            insert into threads (author_id, forum_id, title, text,
                create_time, modify_time, update_time)
            select ?, ?, ?, ?, ?, ?, ?
            from users
            where user_id = ? and banned_until < ?
            ''',
            (author_id, forum_id, title, text, time, time, time, author_id, time)
        )
        rowid = c.lastrowid
        if rowid is None:
            return None
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
            -- 1 = moderator, 2 = admin
            where thread_id = ? and (
              author_id = ?
              or (select 1 from users where user_id = ? and (role = 1 or role = 2))
            )
            ''',
            (thread_id, user_id, user_id)
        )
        db.commit()
        return c.rowcount > 0

    def delete_comment(self, user_id, comment_id):
        db = self._db()
        c = db.cursor()
        c.execute('''
            delete
            from comments
            where comment_id = ?
              and (
                author_id = ?
                -- 1 = moderator, 2 = admin
                or (select 1 from users where user_id = ? and (role = 1 or role = 2))
              )
              -- Don't allow deleting comments with children
              and (select 1 from comments where parent_id = ?) is null
            ''',
            (comment_id, user_id, user_id, comment_id)
        )
        db.commit()
        return c.rowcount > 0

    def add_comment_to_thread(self, thread_id, author_id, text, time):
        db = self._db()
        c = db.cursor()
        c.execute('''
            insert into comments(thread_id, author_id, text, create_time, modify_time)
            select ?, ?, ?, ?, ?
            from threads, users
            where thread_id = ? and user_id = ? and banned_until < ?
            ''',
            (thread_id, author_id, text, time, time, thread_id, author_id, time)
        )
        if c.rowcount > 0:
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
            from comments, users
            where comment_id = ? and user_id = ? and banned_until < ?
            ''',
            (parent_id, author_id, text, time, time, parent_id, author_id, time)
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

    def modify_thread(self, thread_id, user_id, title, text, time):
        db = self._db()
        c = db.cursor()
        c.execute('''
            update threads
            set title = ?, text = ?, modify_time = ?
            where thread_id = ? and (
              (author_id = ? and (select 1 from users where user_id = ? and banned_until < ?))
              -- 1 = moderator, 2 = admin
              or (select 1 from users where user_id = ? and (role = 1 or role = 2))
            )
            ''',
            (
                title, text, time,
                thread_id,
                user_id, user_id, time,
                user_id,
            )
        )
        if c.rowcount > 0:
            db.commit()
            return True
        return False

    def modify_comment(self, comment_id, user_id, text, time):
        db = self._db()
        c = db.cursor()
        c.execute('''
            update comments
            set text = ?, modify_time = ?
            where comment_id = ? and (
              (author_id = ? and (select 1 from users where user_id = ? and banned_until < ?))
              -- 1 = moderator, 2 = admin
              or (select 1 from users where user_id = ? and (role = 1 or role = 2))
            )
            ''',
            (
                text, time,
                comment_id,
                user_id, user_id, time,
                user_id,
            )
        )
        if c.rowcount > 0:
            db.commit()
            return True
        return False

    def register_user(self, username, password, time):
        '''
        Add a user if registrations are enabled.
        '''
        try:
            db = self._db()
            c = db.cursor()
            c.execute('''
                insert into users(name, password, join_time)
                select lower(?), ?, ?
                from config
                where registration_enabled = 1
                ''',
                (username, password, time)
            )
            if c.rowcount > 0:
                db.commit()
                # TODO find a way to get the (autoincremented) user ID without looking
                # up by name.
                # ROWID is *probably* not always consistent (race conditions).
                # Ideally we get the ID immediately on insert.
                return c.execute('''
                    select user_id
                    from users
                    where name = ?
                    ''',
                    (username,)
                ).fetchone()
            return None
        except sqlite3.IntegrityError:
            # User already exists, probably
            return None

    def add_user(self, username, password, time):
        '''
        Add a user without checking if registrations are enabled.
        '''
        try:
            db = self._db()
            c = db.cursor()
            c.execute('''
                insert into users(name, password, join_time)
                values (lower(?), ?, ?)
                ''',
                (username, password, time)
            )
            if c.rowcount > 0:
                db.commit()
                return True
            return False
        except sqlite3.IntegrityError:
            # User already exists, probably
            return False

    def get_users(self):
        return self._db().execute('''
            select user_id, name, join_time, role, banned_until
            from users
            ''',
        )

    def set_forum_name(self, forum_id, name):
        return self.change_one('''
            update forums
            set name = ?
            where forum_id = ?
            ''',
            (name, forum_id)
        )

    def set_forum_description(self, forum_id, description):
        return self.change_one('''
            update forums
            set description = ?
            where forum_id = ?
            ''',
            (description, forum_id)
        )

    def add_forum(self, name, description):
        db = self._db()
        db.execute('''
            insert into forums(name, description)
            values (?, ?)
            ''',
            (name, description)
        )
        db.commit()

    def set_config(self, server_name, server_description, registration_enabled):
        return self.change_one('''
            update config
            set name = ?, description = ?, registration_enabled = ?
            ''',
            (server_name, server_description, registration_enabled)
        )

    def set_config_secrets(self, secret_key, captcha_key):
        return self.change_one('''
            update config
            set secret_key = ?, captcha_key = ?
            ''',
            (secret_key, captcha_key)
        )

    def set_user_ban(self, user_id, until):
        return self.change_one('''
            update users
            set banned_until = ?
            where user_id = ?
            ''',
            (until, user_id)
        )

    def set_user_role(self, user_id, role):
        return self.change_one('''
            update users
            set role = ?
            where user_id = ?
            ''',
            (role, user_id)
        )

    def set_thread_hidden(self, thread_id, hide):
        return self.change_one('''
            update threads
            set hidden = ?
            where thread_id = ?
            ''',
            (hide, thread_id)
        )

    def set_comment_hidden(self, comment_id, hide):
        return self.change_one('''
            update comments
            set hidden = ?
            where comment_id = ?
            ''',
            (hide, comment_id)
        )

    def change_one(self, query, values):
        db = self._db()
        c = db.cursor()
        c.execute(query, values)
        if c.rowcount > 0:
            db.commit()
            return True
        return False

    def query(self, q):
        db = self._db()
        c = db.cursor()
        rows = c.execute(q)
        db.commit()
        return rows, c.rowcount

    def _db(self):
        return sqlite3.connect(self.conn, timeout=5)
