from flask import (
    render_template,
    redirect,
    url_for,
    abort,
    flash,
    request,
    current_app,
    make_response,
)
from flask_login import login_required, current_user
from flask_sqlalchemy.record_queries import get_recorded_queries
from . import main
from .forms import ToDoForm
from .. import db
from ..models import Permission, User, ToDo
from ..decorators import admin_required, permission_required


@main.route("/shutdown")
def server_shutdown():
    if not current_app.testing:
        abort(404)
    shutdown = request.environ.get("werkzeug.server.shutdown")
    if not shutdown:
        abort(500)
    shutdown()
    return "Shutting down..."


@main.route("/", methods=["GET", "POST"])
def index():
    form = ToDoForm()
    print(form.validate_on_submit())
    if form.validate_on_submit():

        todo = ToDo(name=form.body.data, user=current_user._get_current_object())
        db.session.add(todo)
        db.session.commit()
        return redirect(url_for(".index"))
    page = request.args.get("page", 1, type=int)
    show_followed = False
    if current_user.is_authenticated:
        show_followed = bool(request.cookies.get("show_followed", ""))
    if show_followed:
        query = current_user.followed_posts
    else:
        query = ToDo.query
    pagination = query.order_by(ToDo.timestamp.desc()).paginate(
        page=page, per_page=current_app.config["TODO_POSTS_PER_PAGE"], error_out=False
    )
    todos = pagination.items
    return render_template(
        "index.html",
        form=form,
        todos=todos,
        show_followed=show_followed,
        pagination=pagination,
    )


@main.route("/user/<username>")
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get("page", 1, type=int)
    pagination = user.todos.order_by(ToDo.timestamp.desc()).paginate(
        page=page, per_page=current_app.config["TODO_POSTS_PER_PAGE"], error_out=False
    )
    posts = pagination.items
    return render_template("user.html", user=user, posts=posts, pagination=pagination)


@main.route("/post/<int:id>", methods=["GET", "POST"])
def post(id):
    todos = ToDo.query.get_or_404(id)
    form = ToDoForm()
    return render_template("todo.html", posts=[todos], form=form)


@main.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit(id):
    todo = ToDo.query.get_or_404(id)
    if current_user != todo.user and not current_user.can(Permission.ADMIN):
        abort(403)
    form = ToDoForm()
    if form.validate_on_submit():
        todo.name = form.body.data
        db.session.add(todo)
        db.session.commit()
        flash("The post has been updated.")
        return redirect(url_for(".post", id=todo.id))
    form.body.data = todo.name
    return render_template("edit_post.html", form=form)
