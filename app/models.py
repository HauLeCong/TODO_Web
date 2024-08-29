from datetime import datetime
import hashlib
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from markdown import markdown
import bleach
from flask import current_app, request, url_for
from flask_login import UserMixin, AnonymousUserMixin
from app.exceptions import ValidateionError
from . import db, login_manager


class Permission:
    ADMIN = 16
    WRITE = 4


class Role(db.Model):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    permission = db.Column(db.Integer)
    users = db.relationship("User", backref="role", lazy="dynamic")

    def __init__(self, **kwargs):
        super(Role, self).__init__(**kwargs)
        if self.permissions is None:
            self.permission = 0

    @staticmethod
    def insert_roles():
        roles = {
            "User": [Permission.WRITE],
            "Administator": [Permission.WRITE, Permission.ADMIN],
        }

        default_role = "User"
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.reset_permissions()
            for perm in roles[r]:
                role.add_permission(perm)
            role.default = role.name == default_role
            db.session.add(role)
        db.session.commit()

    def add_permission(self, perm):
        if not self.has_permission(perm):
            self.permissions += perm

    def reset_permission(self):
        self.permissions -= 0

    def remove_permission(self, perm):
        if not self.has_permission(perm):
            self.permissions -= perm

    def has_permission(self, perm):
        return self.permissions & perm == perm

    def __repr__(self):
        return "<Role %r" % self.name


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Intefer, primary_key=True)
    email = db.Column(db.String, unique=True, index=True)
    username = db.Column(db.String, unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"))
    password_hash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean, default=False)
    todos = db.relationship("ToDo", backref="user", lazy="dynamic")

    def __init__(self, **kwargs):
        if self.role is None:
            if self.email == current_app.config["TODO_ADMIN"]:
                self.role = Role.query.filter_by(name="Administrator").first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()

    @property
    def password(self):
        raise AttributeError("password is not a readable attribute")

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(current_app.config["SECRET_KEY"], expiration)
        return s.dumps({"confirm": self.id}).decode("utf-8")

    def confirm(self, token):
        s = Serializer(current_app.config["SECRET_KEY"])
        try:
            data = s.loads(token.encode("utf-8"))
        except:
            return False
        if data.get("confirm") != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True

    def can(self, perm):
        return self.role is not None and self.role.has_permission(perm)

    @property
    def todo_list(self):
        return ToDo.query(ToDo).filter(user_id=self.id)

    def to_json(self):
        json_user = {
            "url": url_for("api.get_user", id=self.id),
            "username": self.username,
            "todo": url_for("api.get_todo_list", id=self.id),
            "todo_count": self.todos.count(),
        }
        return json_user

    def generate_auth_token(self, expiration):
        s = Serializer(current_app.config["SECRET_KEY"], expires_in=expiration)
        return s.dumps({"id": self.id}).decode("utf-8")

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(current_app.config["SECRET_KEY"])
        try:
            data = s.loads(token)
        except:
            return None
        return User.query.get(data["id"])

    def __repr__(self) -> str:
        return "<User %r>" % self.username


class ToDo(db.Model):
    __tablename__ = "posts"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.now(datetime.UTC))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    @staticmethod
    def on_change_body(target, value, oldvalue, initiator):
        target.body_html = bleach.linkify(
            bleach.clean(markdown(value, output_format="html"), strip=True)
        )

    def to_json(self):
        json_post = {
            "url": url_for("api.get_todo", id=self.id),
            "name": self.name,
            "user_id": self.user_id,
            "timestamp": self.timestamp,
        }

        return json_post

    @staticmethod
    def from_json(json_post):
        body = json_post.get("body")
        if body is None or body == "":
            raise ValidateionError("post does not have a body")
        return ToDo(body=body)


db.event.listen(ToDo.name, "set", ToDo.on_change_body)
