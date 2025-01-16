from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, BooleanField, PasswordField, EmailField
from wtforms.validators import DataRequired, Optional, Length, Email
from flask_ckeditor import CKEditorField
from src.config import DRAFT_ON_DEFAULT, CHECK_EMAIL, IMAGES_FOLDER, COMMENT_RICH_EDITOR
from src.utils import validate_tags_format, suggest_img_url
from flask_babel import lazy_gettext


class CreatePostForm(FlaskForm):
    title = StringField(lazy_gettext("Title"), description=lazy_gettext("Warning: If you change the title, the URL of the post changes, too.") ,validators=[DataRequired()])
    subtitle = StringField(lazy_gettext("Subtitle"), validators=[DataRequired()])
    img_url = StringField(lazy_gettext("Image URL"), default=IMAGES_FOLDER, description=suggest_img_url(IMAGES_FOLDER) ,validators=[DataRequired()])
    body = CKEditorField(lazy_gettext("Content"), validators=[DataRequired()])
    tags = StringField(lazy_gettext("Tags"),validators=[Optional(), validate_tags_format])
    is_draft = BooleanField(lazy_gettext("Save as a draft?"), default=DRAFT_ON_DEFAULT)
    publish = SubmitField(lazy_gettext("Publish!"))
    preview = SubmitField(lazy_gettext("Preview!"),
        render_kw={"formtarget": "_blank"})


class RegisterForm(FlaskForm):
    if CHECK_EMAIL:
        email = EmailField(label=lazy_gettext("Email"), validators=[DataRequired(), Email(check_deliverability=True)])
    else:
        email = EmailField(label=lazy_gettext("Email"), validators=[DataRequired()])  
    password = PasswordField(label=lazy_gettext("Password"), validators=[DataRequired(), Length(min=8, max=64)])
    username = StringField(label=lazy_gettext("Username"), validators=[DataRequired()])
    submit = SubmitField(lazy_gettext("Sign Me Up!"))


class LoginForm(FlaskForm):
    email = EmailField(label=lazy_gettext("Email"), validators=[DataRequired()])
    password = PasswordField(label=lazy_gettext("Password"), validators=[DataRequired()])
    submit = SubmitField(lazy_gettext("Let me in!"))


class CommentForm(FlaskForm):
    if COMMENT_RICH_EDITOR:
        comment = CKEditorField(lazy_gettext("Comment"), validators=[DataRequired()])
    else:
        comment = TextAreaField(lazy_gettext("Comment"), validators=[DataRequired()])
    submit = SubmitField(lazy_gettext("Send it!"))
