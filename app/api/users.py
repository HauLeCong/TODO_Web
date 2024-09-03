from flask import jsonify, request, current_app, url_for
from . import api
from ..models import User, ToDo


@api.route("/user/<int:id>")
def get_user(id):
    user = User.query.get_or_404(id)
    return jsonify(user.to_json())


@api.route("/users/<int:id>/todo/")
def get_user_todos(id):
    user = User.query.get_or_404(id)
    page = request.args.get("page", 1, type=int)
    pagination = user.todos.order_by(ToDo.timestamp.desc()).paginate(
        page=page, per_page=current_app.config["TODO_PER_PAGE"], error_out=False
    )

    todos = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for("api.get_user_todos", id=id, page=page - 1)

    next = None
    if pagination.has_next:
        next = url_for("api.get_user_todos", id=id, page=page + 1)

    return jsonify(
        {
            "todos": [todo.to_json for todo in todos],
            "prev": prev,
            "next": next,
            "count": pagination.total,
        }
    )
