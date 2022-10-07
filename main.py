from flask import Flask, render_template
from db.sqlite import DB
import os

app = Flask(__name__)
db = DB(os.getenv('DB'))
NAME = 'Agrepy'

@app.route('/')
def index():
    return render_template('index.html', title = NAME, subforums = db.get_subforums())

@app.route('/forum/<forum_id>/')
def subforum(forum_id):
    title, description = db.get_subforum(forum_id)
    threads = db.get_threads(forum_id)
    return render_template('subforum.html', title = title, description = description, threads = threads)

@app.route('/thread/<thread_id>/')
def thread(thread_id):
    title, text, author, comments = db.get_thread(thread_id)
    comments = create_comment_tree(comments)
    return render_template('thread.html', title = title, text = text, author = author, comments = comments)

@app.route('/comment/<comment_id>/')
def comment(comment_id):
    #return str(db.get_comment_tree(comment_id)[0])
    return str(db.get_comment_tree(comment_id))


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
