AUTHOR = "Michael Russell"
SITENAME = "Runic Reflections"
SITEURL = ""

PATH = "content"
ARTICLE_PATHS = ["poetry"]
ARTICLE_SAVE_AS = "{date:%Y}/{slug}.html"
ARTICLE_URL = "{date:%Y}/{slug}.html"

TIMEZONE = "America/Denver"

DEFAULT_LANG = "en"

# Feed generation is usually not desired when developing
SOCIAL = None
FEED_ALL_ATOM = None
FEED_ALL_RSS = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

DEFAULT_PAGINATION = 5
USE_FOLDER_AS_CATEGORY = True

# Theme
THEME = "rr-theme"
THEME_STATIC_DIR = f"{THEME}/static"
TAILWIND_CSS = "tailwind.min.css"
