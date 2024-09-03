from flask import jsonify, request, g, url_for, current_app
from .. import db
from ..models import ToDo, Permission
from . import api
from ..decorators import permission_required
from .errors import forbidden


@api.route("/todos/")
def get_todos():
    page = request.args.get("page", 1, type=int)
    pagination = ToDo.query.paginate(
        page=page, per_page=current_app.config["TODO_PER_PAGE"], error_out=False
    )
    todos = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for("api.get_todos", page=page - 1)
    next = None
    if pagination.has_next:
        next = url_for("api.get_todos", page=page + 1)

    return jsonify(
        {
            "todos": [todo.to_json() for todo in todos],
            "prev": prev,
            "next": next,
            "count": pagination.total,
        }
    )


@api.route("/todos/<int:id>")
def get_post(id):
    post = ToDo.query.get_or_404(id)
    return jsonify(post.to_json())


@api.route("/todos/", methods=["POST"])
@permission_required(Permission.WRITE)
def new_todo():
    todo = ToDo.from_json(request.json)
    todo.user_id = g.current_user
    db.session.add(todo)
    db.session.commit()

    return jsonify(
        todo.to_json(), 201, {"Location": url_for("api.get.todo", id=todo.id)}
    )


@api.route("/todos/<int:id>", methods=["PUT"])
@permission_required(Permission.WRITE)
def edit_todo(id):
    todo = ToDo.query.get_or_404(id)
    if g.current_user != todo.user_id and not g.current_user.can(Permission.ADMIN):
        return forbidden("Insufficient permissions")
    todo.body = request.json.get("body", todo.body)
    db.session.add(todo)
    db.session.commit()
    return jsonify(todo.to_json())
