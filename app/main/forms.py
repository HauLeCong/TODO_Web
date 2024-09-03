from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SelectField, SubmitField

from wtforms.validators import DataRequired, Length, Email, Regexp
from wtforms import ValidationError
from flask_pagedown.fields import PageDownField
from ..models import Role, User


class NamedForm(FlaskForm):
    name = StringField("What is your name", validators=[DataRequired()])
    sublit = SubmitField("Submit")


class ToDoForm(FlaskForm):
    body = PageDownField("What will you do?", validators=[DataRequired()])
    submit = SubmitField("Submit")
