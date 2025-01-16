from datetime import datetime as dt
import hashlib
import json
from flask import (
    Flask,
    Response,
    abort,
    render_template,
    redirect,
    send_from_directory,
    url_for,
    flash,
    request,
)
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_babel import Babel, gettext, lazy_gettext
from flask_login import (
    UserMixin,
    login_user,
    LoginManager,
    current_user,
    logout_user,
    login_required,
)
from functools import partial, wraps
from src.forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from src.utils import (
    add_author,
    filter_posts_by_author,
    filter_posts_by_tag,
    filter_posts_by_year,
    find_post,
    from_json,
    get_tags_description,
    get_time,
    get_unique_tags,
    hide_drafts,
    parse_title,
    random_gravatar_url,
    calculate_reading_time,
)
from src.config import (
    BLOG_NAME,
    BLOG_TITLE,
    BLOG_DESCRIPTION,
    COMMENT_RICH_EDITOR,
    SHOW_COMMENT_TUTORIAL,
    DATE_FORMAT,
    DATE_FORMAT_LONG,
    LANGUAGE,
    DISPLAY_EDIT_DATE,
    DISPLAY_READING_TIME,
    TIMEZONE_OFFSET,
    POSTS_PER_PAGE
)
from jinja2.exceptions import TemplateNotFound
from jinja2.ext import i18n
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase
from sqlalchemy import Integer, String, Text, Boolean, DateTime
from typing import List
from werkzeug.security import generate_password_hash, check_password_hash
import dotenv
import os

dotenv.load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

ckeditor = CKEditor(app)
Bootstrap5(app)

babel = Babel()
babel.init_app(app, default_locale=LANGUAGE)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_message = lazy_gettext("You need to login to use this feature. Use your own or the anonymous account!")
login_manager.login_view = "/login"
login_manager.login_message_category = "danger"

gravatar = Gravatar(
    app,
    size=100,
    rating="g",
    default="retro",
    force_default=False,
    force_lower=False,
    use_ssl=False,
    base_url=None,
)

ANONYMOUS_ID = int(
    os.getenv("ANONYMOUS_ID")
)  # Register a dummy account that users can use for commenting anonymously with registering themselves
SUPER_ID = int(
    os.getenv("SUPER_ID")
)  # The super user's ID that can edit other admin's content and delete every comment

app.jinja_env.filters.update(from_json=from_json)
app.jinja_env.add_extension('jinja2.ext.i18n')

class Base(DeclarativeBase):
    pass


app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DB_URI", "sqlite:///blog.db")
db = SQLAlchemy(model_class=Base)
db.init_app(app)


class User(db.Model, UserMixin):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(150), unique=True)
    password: Mapped[str] = mapped_column(String(150))
    username: Mapped[str] = mapped_column(String(150), unique=True)
    admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class BlogPost(db.Model):
    __tablename__ = "post"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    create_date: Mapped[dt] = mapped_column(DateTime, default=get_time(TIMEZONE_OFFSET), nullable=False)
    edit_date: Mapped[dt] = mapped_column(DateTime, nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_draft: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tags: Mapped[str] = mapped_column(String, default=json.dumps([]))

    # Relationships
    author_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("user.id"))
    comments: Mapped[List["BlogComment"]] = relationship(
        "BlogComment", back_populates="parent_post"
    )


class BlogComment(db.Model):
    __tablename__ = "comment"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(String, nullable=False)
    create_date: Mapped[dt] = mapped_column(DateTime, default=get_time(TIMEZONE_OFFSET), nullable=False)
    edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Relationships
    author_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("user.id"))
    post_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("post.id"))
    parent_post: Mapped["BlogPost"] = relationship("BlogPost", back_populates="comments")


with app.app_context():
    db.create_all()


@app.context_processor
def global_vars():
    return dict(
        current_url=request.url_root,
        SUPER_ID=SUPER_ID,
        ANONYMOUS_ID=ANONYMOUS_ID,
        DISPLAY_EDIT_DATE=DISPLAY_EDIT_DATE,
        DISPLAY_READING_TIME=DISPLAY_READING_TIME,
        DATE_FORMAT=DATE_FORMAT,
        DATE_FORMAT_LONG=DATE_FORMAT_LONG,
        COMMENT_RICH_EDITOR=COMMENT_RICH_EDITOR,
        SHOW_COMMENT_TUTORIAL=SHOW_COMMENT_TUTORIAL,
        BLOG_NAME=BLOG_NAME,
        BLOG_TITLE=BLOG_TITLE,
        BLOG_DESCRIPTION=BLOG_DESCRIPTION,
    )


@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = User.query.filter_by(id=current_user.id).first()
        if not user.admin:
            flash(
                gettext("You do not have the necessary permissions to use this feature. Admin access is required!"),
                "danger",
            )
            return redirect(url_for("home"))
        return f(*args, **kwargs)

    return decorated_function


@app.route("/")
def home():
    page = int(request.args.get("page", 1))
    posts_per_page = POSTS_PER_PAGE
    offset = (page - 1) * posts_per_page
    total_posts = BlogPost.query.count()
    max_page = max(1, (total_posts + posts_per_page - 1) // posts_per_page)

    if page < 1 or page > max_page:
        return redirect(url_for("home"))

    result = (
        db.session.execute(
            db.select(BlogPost)
            .order_by(BlogPost.create_date.desc())
            .where(BlogPost.deleted == False)
            .limit(posts_per_page)
            .offset(offset)
        )
        .scalars()
        .all()
    )
    tag = request.args.get("tag")
    year = request.args.get("year")
    author = request.args.get("author")
    filters = []
    if tag:
        filters.append(partial(filter_posts_by_tag, tag, current_user))
    if year:
        filters.append(partial(filter_posts_by_year, year))
    if author:
        filters.append(partial(filter_posts_by_author, author, User))
    
    filters.append(partial(hide_drafts, current_user, SUPER_ID))

    filtered_posts = result

    for filter_func in filters:
        filtered_posts = [post for post in filtered_posts if post in filter_func(result)]

    posts = add_author(filtered_posts, User)

    return render_template("index.html", all_posts=posts, page=page, max_page=max_page, filter=[(tag, gettext("tag")), (year, gettext("year")), (author, gettext("author"))] if tag or year or author else [])


@app.route("/<post_title>", methods=["GET", "POST"])
def show_post(post_title):
    post = find_post(post_title, BlogPost, User)
    result = (
        db.session.execute(
            db.select(BlogComment).where(
                BlogComment.post_id == post.id, BlogComment.deleted == False
            ).order_by(BlogComment.id.asc())
        )
        .scalars()
        .all()
    )
    comments = add_author(result, User)[::-1]
    edit_comment = request.args.get("edit_comment")
    if edit_comment:
        if not current_user.is_authenticated or current_user.id == ANONYMOUS_ID:
            flash(gettext("As an anonymous user you cannot edit comments!", "danger"))
            return redirect(url_for("show_post", post_title=post_title, commented=True))
        comment = BlogComment.query.filter_by(id=edit_comment).first()
        if not comment or comment.deleted:
            abort(404)
        if comment.author_id != current_user.id:
            flash(gettext("You are not the author of the comment!"), "danger") 
            return redirect(url_for("show_post", post_title=post_title, commented=True))
        comment_form = CommentForm(comment=comment.text)
        if comment_form.validate_on_submit():
            comment.text = comment_form.comment.data
            comment.edited = True
            db.session.commit()
            flash(gettext("Commment successfully updated!"), "success")
            return redirect(url_for("show_post", post_title=post_title, commented=True))
    
    else:
        comment_form = CommentForm()
        if comment_form.validate_on_submit():
            if current_user.is_authenticated:
                new_comment = BlogComment(
                    text=comment_form.comment.data,
                    parent_post=db.get_or_404(BlogPost, post.id),
                    author_id=current_user.id,
                )
                db.session.add(new_comment)
                db.session.commit()
                flash(gettext("Commment successfully posted!"), "success")
                return redirect(url_for("show_post", post_title=post_title, commented=True))
            else:
                return login_manager.unauthorized()

    return render_template(
        "post.html",
        post=post,
        comments=comments,
        form=comment_form,
        anonymous_gravatar=random_gravatar_url,
        calculate_reading_time=calculate_reading_time,
        scroll_down=request.args.get("commented") or edit_comment,
    )


@app.route("/new", methods=["GET", "POST"])
@login_required
@admin_required
def new_post():
    unique_tags = get_unique_tags(BlogPost)

    form = CreatePostForm()
    form.tags.description = get_tags_description(unique_tags)

    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author_id=current_user.id,
            is_draft=form.is_draft.data,
            tags=json.dumps([tag.strip() for tag in form.tags.data.split(',')] if not "" else [])
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("home"))
    return render_template("make-post.html", form=form)


@app.route("/<post_title>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_post(post_title):
    post = find_post(post_title, BlogPost, User)
    if not post:
        abort(404)
    
    unique_tags = get_unique_tags(BlogPost)

    edit_form = CreatePostForm(
        title=post.title, subtitle=post.subtitle, img_url=post.img_url, body=post.body, is_draft=post.is_draft, tags=', '.join((json.loads(post.tags)))
    )
    edit_form.tags.description = get_tags_description(unique_tags)
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        if post.is_draft and not edit_form.is_draft.data:
            post.create_date = get_time(TIMEZONE_OFFSET)
        post.edit_date = get_time(TIMEZONE_OFFSET) if post.body != edit_form.body.data and not post.is_draft else None
        post.body = edit_form.body.data
        post.is_draft = edit_form.is_draft.data
        post.tags=json.dumps([tag.strip() for tag in edit_form.tags.data.split(',')] if not "" else [])
        if edit_form.publish.data:
            db.session.commit()
            flash(gettext("Post successfully updated!"), "success")
            return redirect(url_for("show_post", post_title=parse_title(post.title)))
        elif edit_form.preview.data:
            flash(gettext("You are in preview mode!"), "success")
            return render_template(
                "post.html",
                preview=True,
                post=post,
                calculate_reading_time=calculate_reading_time,
            )
    return render_template("make-post.html", form=edit_form, is_edit=True)


@app.route("/<post_title>/delete")
@login_required
@admin_required
def delete_post(post_title):
    post = find_post(post_title, BlogPost, User)
    if not post:
        abort(404)
    if current_user.id == ANONYMOUS_ID:
        flash(gettext("As an anonymous user you cannot delete posts!"), "danger")
    elif current_user.id == post.author_id or current_user.id == SUPER_ID:
        post.deleted = True
        db.session.commit()
        flash(
            f"{gettext('Successfully deleted the post!')} <a href='/{post_title}/restore'>{gettext('Undo')}</a>",
            "success",
        )
    else:
        flash("You are not the author of the post!", "danger")
    return redirect(url_for("home"))


@app.route("/<post_title>/restore")
def restore_post(post_title):
    post = find_post(post_title, BlogPost, User)
    if current_user.id == ANONYMOUS_ID:
        flash(gettext("As an anonymous user you cannot restore comments!"), "danger")
    if current_user.id == post.author_id or current_user.id == SUPER_ID:
        post.deleted = False
        db.session.commit()
        flash(gettext("Post successfully restored!"), "success")
        return redirect(url_for("show_post", post_title=post_title))
    else:
        flash(gettext("You are not the author of the post!"), "danger")
        return redirect(url_for("home"))


@app.route("/<post_title>/delete/comment/<int:comment_id>")
@login_required
def delete_comment(post_title, comment_id):
    comment = db.get_or_404(BlogComment, comment_id)

    if current_user.id == ANONYMOUS_ID:
        flash(gettext("As an anonymous user you cannot delete comments!"), "danger")
    elif current_user.id == comment.author_id or current_user.id == SUPER_ID:
        comment.deleted = True
        db.session.commit()
        flash(
            f"{gettext('Successfully deleted the comment!')} <a href='/{post_title}/restore/comment/{comment_id}'>{gettext('Undo')}</a>",
            "success",
        )
    else:
        flash(gettext("You are not the author of the comment!"), "danger")

    return redirect(url_for("show_post", post_title=post_title, commented=True))


@app.route("/<post_title>/restore/comment/<int:comment_id>")
@login_required
def restore_comment(post_title, comment_id):
    comment = db.get_or_404(BlogComment, comment_id)

    if current_user.id == comment.author_id or current_user.id == SUPER_ID:
        comment.deleted = False
        db.session.commit()
        flash(gettext("Comment successfully restored!"), "success")
        return redirect(url_for("show_post", post_title=post_title, commented=True))
    else:
        flash(gettext("You are not the author of the comment!"), "danger")
        return redirect(url_for("show_post", post_title=post_title))


@app.route("/author/<author>")
def show_author(author):
    try:
        return render_template(f"authors/{author}.html")
    except TemplateNotFound:
        abort(404)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    
    form = LoginForm()
    redirect_to = request.args.get("next")

    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = User.query.filter_by(email=email).first()
        if not user:
            flash(gettext("No account found. Register first!"), "danger")
            return redirect(url_for("register"))
        if check_password_hash(user.password, password):
            login_user(user)
            flash(gettext("Login successful, %(username)s!", username=user.username), "success")
            if redirect_to:
                return redirect(redirect_to)
            return redirect(url_for("home"))
        else:
            flash(gettext("Invalid credentials!"), "danger")

    if request.args.get("u") == str(ANONYMOUS_ID):
        user = User.query.filter_by(id=ANONYMOUS_ID).first()
        login_user(user)
        flash(
            gettext("Logged in as an anonymous user. Start commenting anonymously!"), "success"
        )
        if redirect_to:
            return redirect(redirect_to)
        return redirect(url_for("home"))

    return render_template("login.html", form=form)


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("home")) 
    
    form = RegisterForm()

    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        username = form.username.data
        user = User.query.filter_by(email=email).first()
        if user:
            flash(gettext("Already registered! Login instead."), "danger")
            return redirect(url_for("login"))

        hashed_password = generate_password_hash(password, "pbkdf2:sha256", 8)
        if not user:
            new_user = User(
                email=email,
                password=hashed_password,
                username=username,
            )
            db.session.add(new_user)
            db.session.commit()
            flash(gettext("Registration and login successful, %(username)s!", username=new_user.username), "success")

            login_user(new_user)
            return redirect(url_for("home"))

    return render_template("register.html", form=form)


@app.route("/logout")
def logout():
    if not current_user.is_authenticated:
        return redirect(url_for("home"))

    username = current_user.username
    logout_user()
    flash(gettext("Logout successful, %(username)s!", username=username), "success")

    return redirect(url_for("home"))


@app.route("/rss.xml")
def rss_feed():

    result = (
        db.session.execute(
            db.select(BlogPost)
            .order_by(BlogPost.id.desc())
            .where(BlogPost.deleted == False, BlogPost.is_draft == False)
        )
        .scalars()
        .all()
    )

    posts = add_author(result, User)

    # Generate RSS feed
    rss_items = []
    for post in posts:
        rss_items.append(f"""
        <item>
            <title>{post.title}</title>
            <guid isPermaLink="true">{ url_for('show_post', post_title=post.title.lower().replace(' ', '-'), _external=True) }</guid>
            <description>{post.subtitle}</description>
            <pubDate>{post.create_date.strftime("%d. %B %Y")}</pubDate>
            <dc:creator>{post.author.username}</dc:creator>
        </item>
        """)

    rss_feed = f"""<?xml version="1.0" encoding="UTF-8" ?>
    <rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
        <channel>
            <title>{BLOG_NAME}</title>
            <link>{url_for('home', _external=True)}</link>
            <atom:link href="{ url_for('rss_feed', _external=True) }" rel="self" type="application/rss+xml" />
            <description>{BLOG_DESCRIPTION}</description>
            <language>{LANGUAGE}</language>
            {''.join(rss_items)}
        </channel>
    </rss>
    """

    return Response(rss_feed, mimetype="application/rss+xml")


@app.route("/robots.txt")
def static_from_root():
    return send_from_directory(app.static_folder, request.path[1:])


@app.route("/rss")
def rss_redirect():
    return redirect(url_for("rss_feed"))

@app.route("/feed")
def feed_redirect():
    return redirect(url_for("rss_feed"))


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.after_request
def add_header(response):
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Cache-Control"] = "max-age=86400"
    return response


@app.after_request
def add_etag(response):
    """
    Automatically add ETag headers and handle cache invalidation.
    """
    # Only apply invalidation to GET or HEAD requests and non-error responses
    if request.method not in ["GET", "HEAD"] or response.status_code != 200:
        return response

    # Exclude static from invalidation
    if request.path.startswith('/static/'):
        return response

    content = response.get_data(as_text=True)
    etag = hashlib.sha256(content.encode("utf-8")).hexdigest()

    if request.headers.get("If-None-Match") == etag:
        # Content is unchanged, return 304 Not Modified
        response.status_code = 304

    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "public, max-age=0"
    return response


if __name__ == "__main__":
    app.run(debug=False)
