from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, BooleanField, SelectMultipleField
from wtforms.validators import DataRequired, Optional
from flask_ckeditor import CKEditorField
from src.config import DRAFT_ON_DEFAULT
from src.utils import validate_tags_format


class CreatePostForm(FlaskForm):
    title = StringField("Blog Post Title", validators=[DataRequired()])
    subtitle = StringField("Subtitle", validators=[DataRequired()])
    img_url = StringField("Blog Image URL", validators=[DataRequired()])
    body = CKEditorField("Blog Content", validators=[DataRequired()])
    tags = StringField("Tags (comma-separated)",validators=[Optional(), validate_tags_format])
    is_draft = BooleanField("Save as a draft?")
    submit = SubmitField("Submit Post")


class RegisterForm(FlaskForm):
    email = StringField(label="Email", validators=[DataRequired()])
    password = StringField(label="Password", validators=[DataRequired()])
    username = StringField(label="Username", validators=[DataRequired()])
    submit = SubmitField("Sign Me Up!")


class LoginForm(FlaskForm):
    email = StringField(label="Email", validators=[DataRequired()])
    password = StringField(label="Password", validators=[DataRequired()])
    submit = SubmitField("Let me in!")


class CommentForm(FlaskForm):
    comment = TextAreaField("Comment", validators=[DataRequired()])
    submit = SubmitField("Submit Comment")
