from collections import Counter
import json
import os
import hashlib
import re
from flask_babel import lazy_gettext
from werkzeug.exceptions import NotFound
from datetime import datetime, timezone, timedelta


def get_time(timezone_offset):
    """Return current time for the specified timezone."""
    tzinfo = timezone(timedelta(hours=timezone_offset))
    return datetime.now(tz=tzinfo)


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


def parse_title(raw_title):
    """Converts the post title to a url string"""
    return raw_title.lower().replace(" ", "-")


def find_post(title, post_model, user_model):
    """Uses a lower case title combined with hyphens and returns the corresponding Post object in the database"""
    all_posts = post_model.query.all()
    post_list = [item for item in all_posts if parse_title(item.title) == title]
    if not post_list:
        raise NotFound()
    post = post_list[0]
    post.author = user_model.query.filter_by(id=post.author_id).first()
    return post


def add_author(list, user_model):
    """Maps the author id to the User object and attaches the username to each item in the list (Post or Comment)"""
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


def from_json(json_string):
    """Deserialize (a str, bytes or bytearray instance containing a JSON document) to a Python object. Used as and"""
    return json.loads(json_string)


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


def get_tags_description(tags):
    """Add description to tag field."""
    if tags and tags != [""]:
        suggestion = ", ".join(tags)
    else:
        suggestion = "nothing found (add tags first, e.g. travel, food, books)"
    return lazy_gettext("Suggestion: %(suggestion)s", suggestion=suggestion)


def get_unique_tags(post_model):
    """Sorted tags by occurence."""
    all_tags = [json.loads(post.tags) for post in post_model.query.all()]
    unique_tags = set(tag for tags in all_tags for tag in tags)
    tag_counts = Counter(tag for tags in all_tags for tag in tags)
    return sorted(unique_tags, key=lambda tag: tag_counts[tag], reverse=True)


def filter_posts_by_tag(tag, current_user, posts):
    """Filter by tag and draft posts if the user is an admin"""
    if tag.lower() == "draft" and current_user.is_authenticated and current_user.admin:
        return [post for post in posts if post.is_draft]
    else:
        return [post for post in posts if tag in json.loads(post.tags)]


def filter_posts_by_year(year, posts):
    """Filter by the year the post was created."""
    return [post for post in posts if year == str(post.create_date.strftime("%Y"))]


def hide_drafts(current_user, SUPER_ID, posts):
    """Filter out drafts if the user is not the author or the super admin"""
    if current_user.is_authenticated:
        return [
            post
            for post in posts
            if not post.is_draft
            or (post.is_draft and post.author_id == current_user.id)
            or current_user.id == SUPER_ID
        ]
    else:
        return [post for post in posts if not post.is_draft]


def filter_posts_by_author(author, user_model, posts):
    """Filter by the post author."""
    author_id = user_model.query.filter_by(username=author).first().id
    return [post for post in posts if author_id == post.author_id]
