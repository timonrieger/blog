from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, BooleanField, PasswordField, EmailField
from wtforms.validators import DataRequired, Optional, Length, Email
from flask_ckeditor import CKEditorField
from src.config import DRAFT_ON_DEFAULT, CHECK_EMAIL, IMAGES_FOLDER
from src.utils import validate_tags_format, suggest_img_url


class CreatePostForm(FlaskForm):
    title = StringField("Blog Post Title", description="Warning: If you change the title, the URL of the post changes, too." ,validators=[DataRequired()])
    subtitle = StringField("Subtitle", validators=[DataRequired()])
    img_url = StringField("Blog Image URL", default=IMAGES_FOLDER, description=suggest_img_url(IMAGES_FOLDER) ,validators=[DataRequired()])
    body = CKEditorField("Blog Content", validators=[DataRequired()])
    tags = StringField("Tags",validators=[Optional(), validate_tags_format])
    is_draft = BooleanField("Save as a draft?", default=DRAFT_ON_DEFAULT)
    submit = SubmitField("Publish!")


class RegisterForm(FlaskForm):
    if CHECK_EMAIL:
        email = EmailField(label="Email", validators=[DataRequired(), Email(check_deliverability=True)])
    else:
        email = EmailField(label="Email", validators=[DataRequired()])  
    password = PasswordField(label="Password", validators=[DataRequired(), Length(min=8, max=64)])
    username = StringField(label="Username", validators=[DataRequired()])
    submit = SubmitField("Sign Me Up!")


class LoginForm(FlaskForm):
    email = EmailField(label="Email", validators=[DataRequired()])
    password = PasswordField(label="Password", validators=[DataRequired()])
    submit = SubmitField("Let me in!")


class CommentForm(FlaskForm):
    comment = TextAreaField("Comment", validators=[DataRequired()])
    submit = SubmitField("Send it!")
