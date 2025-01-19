LANGUAGE = "en"
DISPLAY_READING_TIME = True
DISPLAY_EDIT_DATE = True
DRAFT_ON_DEFAULT = True
LEVEL_ADMINS = False
TIMEZONE_OFFSET = 0
DATE_FORMAT = "MMMM d, yyyy"
CHECK_EMAIL = True
IMAGES_FOLDER = "static/uploads/"
POSTS_PER_PAGE = 10
NR_RELATED_POSTS = 3
COMMENT_RICH_EDITOR = False
SHOW_COMMENT_TUTORIAL = True
BLOG_TITLE = "Brain Snippets"
BLOG_DESCRIPTION = "Here I write about Ideas, Thoughts, Conclusions I'd like to share with you. It's about programming, books, philosophy, data analysis, and lots of other topics."

import dotenv
import os

dotenv.load_dotenv()
# Edit the following in the .env file
ANONYMOUS_ID = int(
    os.getenv("ANONYMOUS_ID")
)  # Register a dummy account that users can use for commenting anonymously without registering themselves
SUPER_ID = int(
    os.getenv("SUPER_ID")
)  # The super user's ID that can edit other admin's content and delete every comment
DB_URI = os.environ.get("DB_URI", "sqlite:///blog.db")
SECRET_KEY = os.getenv("SECRET_KEY")
AUTH_URL = os.getenv("AUTH_URL")
