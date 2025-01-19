from datetime import datetime as dt
import hashlib
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
from functools import wraps
from src.forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from jinja2.exceptions import TemplateNotFound
from database import db, create_all, User as UserModel, BlogComment, BlogPost
from src.utils import (
    add_author,
    find_post,
    get_tags_description,
    get_time,
    get_unique_tags,
    is_author,
    humanize_time,
    parse_title,
    pipe_tag,
    random_gravatar_url,
    calculate_reading_time,
    tags_to_list,
    tags_to_string,
)
from src.config import (
    ANONYMOUS_ID,
    BLOG_DESCRIPTION,
    BLOG_NAME,
    BLOG_TITLE,
    COMMENT_RICH_EDITOR,
    DB_URI,
    AUTH_URL,
    NR_RELATED_POSTS,
    SECRET_KEY,
    SHOW_COMMENT_TUTORIAL,
    DATE_FORMAT,
    LANGUAGE,
    DISPLAY_EDIT_DATE,
    DISPLAY_READING_TIME,
    POSTS_PER_PAGE,
    SHOW_COMMENT_TUTORIAL,
    TIMEZONE_OFFSET,
)
import requests
import dotenv
import os

dotenv.load_dotenv()

from jinja2.exceptions import TemplateNotFound
from sqlalchemy import extract, func, or_

app = Flask(__name__)
app.secret_key = SECRET_KEY

app.config["SQLALCHEMY_DATABASE_URI"] = DB_URI
db.init_app(app)

ckeditor = CKEditor(app)

Bootstrap5(app)

babel = Babel()
babel.init_app(app, default_locale=LANGUAGE)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_message = lazy_gettext(
    "You need to login to use this feature. Use your own or the anonymous account!"
)
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


app.jinja_env.filters.update(tags_to_list=tags_to_list, humanize_time=humanize_time)
app.jinja_env.add_extension("jinja2.ext.i18n")


class User(UserMixin, UserModel):
    pass


with app.app_context():
    create_all(app)


@app.context_processor
def global_vars():
    return dict(
        ANONYMOUS_ID=ANONYMOUS_ID,
        DISPLAY_EDIT_DATE=DISPLAY_EDIT_DATE,
        DISPLAY_READING_TIME=DISPLAY_READING_TIME,
        DATE_FORMAT=DATE_FORMAT,
        is_author=is_author,
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
                gettext(
                    "You do not have the necessary permissions to use this feature. Admin access is required!"
                ),
                "danger",
            )
            return redirect(url_for("home"))
        return f(*args, **kwargs)

    return decorated_function


@app.route("/")
def home():
    tag = request.args.get("tag")
    year = request.args.get("year")
    author = request.args.get("author")

    query = BlogPost.query.order_by(BlogPost.create_date.desc())

    filters = [BlogPost.deleted == False]

    if tag:
        if (
            tag.lower() == "draft"
            and current_user.is_authenticated
            and current_user.admin
        ):
            filters.append(BlogPost.is_draft == True)
        else:
            filters.append(BlogPost.tags.contains(pipe_tag(tag)))

    if year:
        filters.append(extract("year", BlogPost.create_date) == int(year))
    if author:
        author_obj = User.query.filter_by(username=author).first()
        filters.append(BlogPost.author_id == author_obj.id)

    if current_user.is_anonymous or not current_user.admin:
        filters.append(BlogPost.is_draft == False)

    query = query.filter(*filters)
    pagination = query.paginate(per_page=POSTS_PER_PAGE)
    posts = add_author(pagination, User)

    filter_badges = []
    for key in request.args:
        if key == "tag" and tag:
            filter_badges.append((gettext("tag"), tag))
        elif key == "year" and year:
            filter_badges.append((gettext("year"), year))
        elif key == "author" and author:
            filter_badges.append((gettext("author"), author))

    return render_template(
        "index.html",
        all_posts=posts,
        pagination=pagination,
        filter=filter_badges,
    )


@app.route("/<post_title>", methods=["GET", "POST"])
def show_post(post_title):
    post = find_post(post_title, BlogPost, User)
    result_comments = (
        BlogComment.query.where(
            BlogComment.post_id == post.id, BlogComment.deleted == False
        )
        .order_by(BlogComment.id.asc())
        .all()
    )
    comments = add_author(result_comments, User)[::-1]

    edit_comment = request.args.get("edit_comment")
    if edit_comment:
        comment = BlogComment.query.filter_by(id=edit_comment).first()
        if not comment or comment.deleted or not is_author(current_user, comment):
            abort(404)

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
                    create_date=get_time(TIMEZONE_OFFSET)
                )
                db.session.add(new_comment)
                db.session.commit()
                flash(gettext("Commment successfully posted!"), "success")
                return redirect(
                    url_for("show_post", post_title=post_title, commented=True)
                )
            else:
                return login_manager.unauthorized()

    filters = [
        BlogPost.deleted == False,
        BlogPost.is_draft == False,
        BlogPost.id != post.id,
    ]

    filters.append(
        or_(
            *[
                BlogPost.tags.like(f"%{pipe_tag(tag)}%")
                for tag in tags_to_list(post.tags)
            ]
        )
    )

    related_posts = (
        BlogPost.query.filter(*filters)
        .order_by(func.random())
        .limit(NR_RELATED_POSTS)
        .all()
    )

    return render_template(
        "post.html",
        post=post,
        related_posts=related_posts,
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
            create_date=get_time(),
            img_url=form.img_url.data,
            author_id=current_user.id,
            is_draft=form.is_draft.data,
            tags=tags_to_string(form.tags.data),
        )

        if form.publish.data:
            db.session.add(new_post)
            db.session.commit()
            if new_post.is_draft:
                flash(gettext("Post saved as draft!"), "success")
            else:
                flash(gettext("Post published!"), "success")
            return redirect(url_for("home"))

        elif form.preview.data:
            flash(gettext("You are in preview mode!"), "success")
            return render_template(
                "post.html",
                preview=True,
                post=add_author([new_post], User)[0],
                calculate_reading_time=calculate_reading_time,
            )

    return render_template("make-post.html", form=form)


@app.route("/<post_title>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_post(post_title):
    post = find_post(post_title, BlogPost, User)

    if not is_author(current_user, post):
        abort(404)

    unique_tags = get_unique_tags(BlogPost)

    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        body=post.body,
        is_draft=post.is_draft,
        tags=", ".join(tags_to_list(post.tags)),
    )
    edit_form.tags.description = get_tags_description(unique_tags)

    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        if post.is_draft and not edit_form.is_draft.data:
            post.create_date = get_time()
        post.edit_date = (
            get_time()
            if post.body != edit_form.body.data and not post.is_draft
            else None
        )
        post.body = edit_form.body.data
        post.is_draft = edit_form.is_draft.data
        post.tags = tags_to_string(edit_form.tags.data)

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

    if not is_author(current_user, post):
        abort(404)

    post.deleted = True
    db.session.commit()
    flash(
        f"{gettext('Successfully deleted the post!')} <a href='/{post_title}/restore'>{gettext('Undo')}</a>",
        "success",
    )
    return redirect(url_for("home"))


@app.route("/<post_title>/restore")
def restore_post(post_title):
    post = find_post(post_title, BlogPost, User)

    if not is_author(current_user, post):
        abort(404)

    post.deleted = False
    db.session.commit()

    flash(gettext("Post successfully restored!"), "success")
    return redirect(url_for("show_post", post_title=post_title))


@app.route("/<post_title>/delete/comment/<int:comment_id>")
@login_required
def delete_comment(post_title, comment_id):
    comment = db.get_or_404(BlogComment, comment_id)

    if not is_author(current_user, comment):
        abort(404)

    comment.deleted = True
    db.session.commit()

    flash(
        f"{gettext('Successfully deleted the comment!')} <a href='/{post_title}/restore/comment/{comment_id}'>{gettext('Undo')}</a>",
        "success",
    )
    return redirect(url_for("show_post", post_title=post_title, commented=True))


@app.route("/<post_title>/restore/comment/<int:comment_id>")
@login_required
def restore_comment(post_title, comment_id):
    comment = db.get_or_404(BlogComment, comment_id)

    if not is_author(current_user, comment):
        abort(404)

    comment.deleted = False
    db.session.commit()

    flash(gettext("Comment successfully restored!"), "success")
    return redirect(url_for("show_post", post_title=post_title, commented=True))


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
        data = {"email": email, "password": password}
        response = requests.post(url=f"{AUTH_URL}/login", json=data)
        if response.status_code == 200:
            flash(response.json()["message"], "success")
            login_user(user)
            if redirect_to:
                return redirect(redirect_to)
            return redirect(url_for("home"))
        flash(response.json()["message"], "danger")

    if request.args.get("u") == str(ANONYMOUS_ID):
        user = User.query.filter_by(id=ANONYMOUS_ID).first()
        login_user(user)
        flash(
            gettext("Logged in as an anonymous user. Start commenting anonymously!"),
            "success",
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
        data = {
            "email": email,
            "password": password,
            "username": username,
            "then": f"{request.url_root}/login",
        }
        response = requests.post(f"{AUTH_URL}/register", json=data)
        (
            flash(response.json()["message"], "success")
            if response.status_code == 200
            else flash(response.json()["message"], "danger")
        )

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
        BlogPost.query.where(BlogPost.deleted == False, BlogPost.is_draft == False)
        .order_by(BlogPost.id.desc())
        .all()
    )

    posts = add_author(result, User)

    # Generate RSS feed
    rss_items = []
    for post in posts:
        rss_items.append(
            f"""
        <item>
            <title>{post.title}</title>
            <guid isPermaLink="true">{ url_for('show_post', post_title=post.title.lower().replace(' ', '-'), _external=True) }</guid>
            <description>{post.subtitle}</description>
            <pubDate>{post.create_date.strftime("%d. %B %Y")}</pubDate>
            <dc:creator>{post.author.username}</dc:creator>
        </item>
        """
        )

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
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains; preload"
    )
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    if not app.debug:
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
    if request.path.startswith("/static/"):
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
