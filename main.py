from datetime import datetime as dt, date
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
from flask_caching import Cache
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
from jinja2.exceptions import TemplateNotFound
from database import db, create_all, User as UserModel, BlogComment, BlogPost
from src.utils import add_author, filter_posts_by_author, filter_posts_by_tag, filter_posts_by_year, find_post, from_json, get_tags_description, get_unique_tags, hide_drafts, parse_title, random_gravatar_url, calculate_reading_time
from src.config import LANGUAGE, DISPLAY_EDIT_DATE, DISPLAY_READING_TIME
import requests
import dotenv
import os

dotenv.load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DB_URI")
db.init_app(app)

ckeditor = CKEditor(app)
Bootstrap5(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_message = u"You need to login to use this feature. Use your own account or login anonymously!"
login_manager.login_view = "/login"
login_manager.login_message_category = "danger"

# cache = Cache(config={"CACHE_TYPE": "SimpleCache"})
# cache.init_app(app)

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

AUTH_URL = os.getenv("AUTH_URL")
ANONYMOUS_ID = int(os.getenv("ANONYMOUS_ID"))
SUPER_ID = int(os.getenv("SUPER_ID"))

class User(UserMixin, UserModel):
    pass

app.jinja_env.filters.update(from_json=from_json)

with app.app_context():
    create_all(app)


@app.context_processor
def global_vars():
    return dict(
        current_url=request.url_root,
        SUPER_ID=SUPER_ID,
        ANONYMOUS_ID=ANONYMOUS_ID,
        LANGUAGE=LANGUAGE,
        DISPLAY_EDIT_DATE=DISPLAY_EDIT_DATE,
        DISPLAY_READING_TIME=DISPLAY_READING_TIME,
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
                "You do not have the necessary permissions to use this feature. Admin access is required!",
                "danger",
            )
            return redirect(url_for("home"))
        return f(*args, **kwargs)

    return decorated_function


@app.route("/")
def home():
    page = int(request.args.get("page", 1))
    posts_per_page = 10
    offset = (page - 1) * posts_per_page
    total_posts = BlogPost.query.count()
    max_page = max(1, (total_posts + posts_per_page - 1) // posts_per_page)

    if page < 1 or page > max_page:
        return redirect(url_for("home"))

    result = (
        db.session.execute(
            db.select(BlogPost)
            .order_by(BlogPost.id.desc())
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

    return render_template("index.html", all_posts=posts, page=page, max_page=max_page, filter=[(tag, "tag"), (year, "year"), (author, "author")] if tag or year or author else [])


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
            flash("As an anonymous user you cannot edit comments!", "danger")
            return redirect(url_for("show_post", post_title=post_title, commented=True))
        comment = BlogComment.query.filter_by(id=edit_comment).first()
        if not comment or comment.deleted:
            abort(404)
        if comment.author_id != current_user.id:
            flash("You are not the author of the comment!", "danger") 
            return redirect(url_for("show_post", post_title=post_title, commented=True))
        comment_form = CommentForm(comment=comment.text)
        if comment_form.validate_on_submit():
            comment.text = comment_form.comment.data
            db.session.commit()
            flash("Commment successfully updated!", "success")
            return redirect(url_for("show_post", post_title=post_title, commented=True))
    
    else:
        comment_form = CommentForm()
        if comment_form.validate_on_submit():
            if current_user.is_authenticated:
                time = dt.now().strftime("%b %d, %Y") + " at " + dt.now().strftime("%H:%M")
                new_comment = BlogComment(
                    text=comment_form.comment.data,
                    parent_post=db.get_or_404(BlogPost, post.id),
                    author_id=current_user.id,
                    create_date=time,
                )
                db.session.add(new_comment)
                db.session.commit()
                flash("Commment successfully posted!", "success")
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
            create_date=date.today().strftime("%B %d, %Y"),
            author_id=current_user.id,
            is_draft=form.is_draft.data,
            tags=json.dumps([tag.strip() for tag in form.tags.data.split(',')])  # Convert tags to JSON format
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
        flash(f"No post found for title {post_title}!", "danger")
        return redirect(url_for("home"))
    
    unique_tags = get_unique_tags(BlogPost)

    edit_form = CreatePostForm(
        title=post.title, subtitle=post.subtitle, img_url=post.img_url, body=post.body, is_draft=post.is_draft, tags=', '.join((json.loads(post.tags)))
    )
    edit_form.tags.description = get_tags_description(unique_tags)
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data
        post.edit_date = date.today().strftime("%B %d, %Y")
        post.is_draft = edit_form.is_draft.data
        post.tags = json.dumps([tag.strip() for tag in edit_form.tags.data.split(',')])
        db.session.commit()
        flash("Post successfully updated!", "success")
        return redirect(url_for("show_post", post_title=parse_title(post.title)))
    return render_template("make-post.html", form=edit_form, is_edit=True)


@app.route("/<post_title>/delete")
@login_required
@admin_required
def delete_post(post_title):
    post = find_post(post_title, BlogPost, User)
    if not post:
        flash(f"No post found for title {post_title}!", "danger")
        return redirect(url_for("home"))
    if current_user.id == ANONYMOUS_ID:
        flash("As an anonymous user you cannot delete posts!", "danger")
    elif current_user.id == post.author_id or current_user.id == SUPER_ID:
        post.deleted = True
        db.session.commit()
        flash(
            "Successfully deleted the post! <a href='/{}/restore'>Undo</a>".format(
                post_title
            ),
            "success",
        )
    else:
        flash("You are not the author of the post!", "danger")
    return redirect(url_for("home"))


@app.route("/<post_title>/restore")
def restore_post(post_title):
    post = find_post(post_title, BlogPost, User)
    if current_user.id == ANONYMOUS_ID:
        flash("As an anonymous user you cannot restore comments!", "danger")
    if current_user.id == post.author_id or current_user.id == SUPER_ID:
        post.deleted = False
        db.session.commit()
        flash("Post successfully restored!", "success")
        return redirect(url_for("show_post", post_title=post_title))
    else:
        flash("You are not the author of the post!", "danger")
        return redirect(url_for("home"))


@app.route("/<post_title>/delete/comment/<int:comment_id>")
@login_required
def delete_comment(post_title, comment_id):
    comment = db.get_or_404(BlogComment, comment_id)

    if current_user.id == ANONYMOUS_ID:
        flash("As an anonymous user you cannot delete comments!", "danger")
    elif current_user.id == comment.author_id or current_user.id == SUPER_ID:
        comment.deleted = True
        db.session.commit()
        flash(
            "Successfully deleted the comment! <a href='/{}/restore/comment/{}'>Undo</a>".format(
                post_title, comment_id
            ),
            "success",
        )
    else:
        flash("You are not the author of the comment!", "danger")

    return redirect(url_for("show_post", post_title=post_title, commented=True))


@app.route("/<post_title>/restore/comment/<int:comment_id>")
@login_required
def restore_comment(post_title, comment_id):
    comment = db.get_or_404(BlogComment, comment_id)

    if current_user.id == comment.author_id or current_user.id == SUPER_ID:
        comment.deleted = False
        db.session.commit()
        flash("Comment successfully restored!", "success")
        return redirect(url_for("show_post", post_title=post_title, commented=True))
    else:
        flash("You are not the author of the comment!", "danger")
        return redirect(url_for("show_post", post_title=post_title))


@app.route("/author")
def show_author():
    return redirect(f"https://timonrieger.de?utm_source={request.url_root}")


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    redirect_to = request.args.get("next")

    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = User.query.filter_by(email=email).first()
        data = {
            "email": email,
            "password": password
        }
        response = requests.post(url=f"{AUTH_URL}/login", json=data)
        if response.status_code == 200:
            flash(response.json()['message'], "success")
            login_user(user)
            if redirect_to:
                return redirect(redirect_to)
            return redirect(url_for("home"))
        flash(response.json()['message'], "danger")

    if request.args.get("u") == str(ANONYMOUS_ID):
        user = User.query.filter_by(id=ANONYMOUS_ID).first()
        login_user(user)
        flash(
            f"Logged in as an anonymous user. Start commenting anonymously!", "success"
        )
        if redirect_to:
            return redirect(redirect_to)
        return redirect(url_for("home"))

    return render_template("login.html", form=form)


@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        username = form.username.data
        data = {
            "email": email,
            "password": password,
            "username": username,
            "then": "https:blog.timonrieger.de/login"
        }
        response = requests.post(f"{AUTH_URL}/register", json=data)
        flash(response.json()['message'], "success") if response.status_code == 200 else flash(response.json()['message'], "danger")
        
    return render_template("register.html", form=form)


@app.route("/logout")
def logout():
    username = current_user.username
    logout_user()
    flash(f"Logged out. See you soon, {username}!", "success")
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
        post_date = dt.strptime(post.create_date, "%B %d, %Y")
        rss_items.append(f"""
        <item>
            <title>{post.title}</title>
            <guid isPermaLink="true">{ url_for('show_post', post_title=post.title.lower().replace(' ', '-'), _external=True) }</guid>
            <description>{post.subtitle}</description>
            <pubDate>{post_date.strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate>
            <dc:creator>{post.author.username}</dc:creator>
        </item>
        """)

    rss_feed = f"""<?xml version="1.0" encoding="UTF-8" ?>
    <rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
        <channel>
            <title>Brain Snippets Blog RSS Feed</title>
            <link>{url_for('home', _external=True)}</link>
            <atom:link href="{ url_for('rss_feed', _external=True) }" rel="self" type="application/rss+xml" />
            <description>Latest posts from Brain Snippets Blog</description>
            <language>en-us</language>
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
    #response.headers["Cache-Control"] = "max-age=86400"
    return response


if __name__ == "__main__":
    app.run(debug=False, port=5007)
