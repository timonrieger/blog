from collections import Counter
import json
import os
import hashlib
import re
from src.config import LANGUAGE, TIMEZONE_OFFSET
from flask_babel import lazy_gettext
from werkzeug.exceptions import NotFound
from datetime import datetime, timezone, timedelta
import humanize
from werkzeug.security import generate_password_hash


# JINJA FILTER
_LOCAL_MAPPING = {
    "de": "de_DE",
}


def humanize_time(date, language=LANGUAGE, timezone_offset=TIMEZONE_OFFSET):
    """Humanizes a datetime.timedelta object, e.g. one hour ago."""
    lang = _LOCAL_MAPPING.get(language, None)
    humanize.i18n.activate(lang)
    tzinfo = timezone(timedelta(hours=timezone_offset))
    input_date = date.replace(tzinfo=timezone.utc).astimezone(tzinfo)
    current = datetime.now(tz=tzinfo)
    print(type(humanize.naturaltime(current - input_date)))
    return humanize.naturaltime(current - input_date)


# FORMS UTILS
def validate_tags_format(form, tags):
    """
    Validates that the tags are comma-separated and do not include any whitespaces.

    :param tags: A string containing comma-separated tags
    :return: A list of valid tags if the format is correct, otherwise raises a ValueError
    """
    if form.tags.data == "":
        return []

    tags_list = [tag.strip() for tag in form.tags.data.split(",")]

    if any(not tag for tag in tags_list):
        raise ValueError("Tags must be separated by commas and cannot be empty.")

    return tags_list


def suggest_img_url(directory):
    """Suggest the relative url for the next post's image."""
    try:
        files = os.listdir(directory)
        max_value = -1
        ext = ""
        num_pattern = re.compile(r"\d+")

        for file in files:
            match = num_pattern.search(file)
            if match:
                number = int(match.group())
                if number > max_value:
                    max_value = number
                    ext = os.path.splitext(file)[1]

    except Exception:
        suggestion = lazy_gettext("nothing found (use numbered filenames, e.g. 1.jpg)")
    else:
        incremented_number = str(max_value + 1)
        suggestion = f"{directory}{incremented_number}{ext}"
    finally:
        return lazy_gettext("Suggestion: %(suggestion)s", suggestion=suggestion)


# DB FILTER UTILS
def filter_posts_by_tag(tag, current_user, posts):
    """Filter by tag and draft posts if the user is an admin"""
    if tag.lower() == "draft" and current_user.is_authenticated and current_user.admin:
        return [post for post in posts if post.is_draft]
    else:
        return [post for post in posts if tag in tags_to_list(post.tags)]


# MISCELLANEOUS
def get_tags_description(tags):
    """Add description to tag field."""
    if tags and tags != [""]:
        suggestion = ", ".join(tags)
    else:
        suggestion = "nothing found (add tags first, e.g. travel, food, books)"
    return lazy_gettext("Suggestion: %(suggestion)s", suggestion=suggestion)


def tags_to_list(tag_string):
    """Splits a string with tags separated with pipe delimiter into a python list"""
    return tag_string.strip("|").split("|")


def tags_to_string(form_tags):
    """Generates the string of tags separated with pipe delimiter for database commit"""
    return f"|{'|'.join([tag.strip() for tag in form_tags.split(",")])}|"


def pipe_tag(tag):
    return f"|{tag}|"


def get_unique_tags(post_model):
    """Sorted tags by occurence."""
    all_tags = [tags_to_list(post.tags) for post in post_model.query.all()]
    unique_tags = set(tag for tags in all_tags for tag in tags)
    tag_counts = Counter(tag for tags in all_tags for tag in tags)
    return sorted(unique_tags, key=lambda tag: tag_counts[tag], reverse=True)


def get_time(timezone_offset=TIMEZONE_OFFSET):
    """Return current time for the specified timezone."""
    tzinfo = timezone(timedelta(hours=timezone_offset))
    return datetime.now(tz=tzinfo)


def parse_title(raw_title):
    """Converts the post title to a url string"""
    return raw_title.lower().replace(" ", "-")


def find_post(title, post_model, user_model):
    """Uses a lower case title combined with hyphens and returns the corresponding BlogPost object in the database"""
    all_posts = post_model.query.all()
    post_list = [item for item in all_posts if parse_title(item.title) == title]
    if not post_list:
        raise NotFound()
    post = post_list[0]
    post.author = user_model.query.filter_by(id=post.author_id).first()
    return post


def add_author(list, user_model):
    """Maps the author id to the User object and attaches the username to each item in the list (BlogPost or BlogComment)"""
    authors = [post.author_id for post in list]
    usernames = user_model.query.filter(user_model.id.in_(authors)).all()
    user_dict = {user.id: user for user in usernames}
    list_with_authors = []
    for item in list:
        item.author = user_dict.get(item.author_id, "")
        list_with_authors.append(item)
    return list_with_authors


def random_gravatar_url(size=80):
    """Generate a unique Gravatar-like URL using a random value."""
    random_bytes = os.urandom(16)
    random_hash = hashlib.md5(random_bytes).hexdigest()
    return f"{random_hash}@mailinator.com"


def calculate_reading_time(text, words_per_minute=200):
    """Calculate the estimated reading time for a given text."""
    words = text.split()
    total_words = len(words)
    reading_time_minutes = total_words / words_per_minute
    minutes = int(reading_time_minutes)
    return minutes


def initialize_database(db, user_model, post_model):
    """Initializes the database with admin and anonymous users and dummy posts."""
    # Create admin and anonymous users
    if not user_model.query.filter_by(username="admin").first():
        admin = user_model(
            email="admin@example.com",
            password=generate_password_hash("admin123", "pbkdf2:sha256", 8),
            username="admin",
            admin=True,
        )
        db.session.add(admin)

    if not user_model.query.filter_by(username="anonymous").first():
        anonymous = user_model(
            email="anonymous@example.com",
            password=generate_password_hash("anonymous", "pbkdf2:sha256", 8),
            username="anonymous",
            admin=False,
        )
        db.session.add(anonymous)

    db.session.commit()

    # Create 10 dummy blog posts
    admin_user = user_model.query.filter_by(username="admin").first()
    for i in range(1, 11):
        post = post_model(
            title=f"Dummy Post {i}",
            subtitle=f"This is the subtitle for dummy post {i}.",
            body=f"This is the body of dummy post {i}.",
            img_url=f"https://example.com/dummy{i}.jpg",
            tags=f"|example|post{i}|",
            author_id=admin_user.id,
        )
        db.session.add(post)

    db.session.commit()
