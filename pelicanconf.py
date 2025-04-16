# pylint: disable=missing-function-docstring,missing-module-docstring

from math import ceil
from string import capwords

from pelican import signals

AUTHOR = "Michael Russell"
SITENAME = "Runic Reflections"
SITEURL = ""

PATH = "content"
ARTICLE_PATHS = ["poetry"]
ARTICLE_SAVE_AS = "{date:%Y}/{slug}.html"
ARTICLE_URL = "{date:%Y}/{slug}.html"
ARTICLE_ORDER_BY = "reversed-date"

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

DEFAULT_PAGINATION = 6
USE_FOLDER_AS_CATEGORY = True

# Theme
THEME = "rr-theme"
THEME_STATIC_DIR = f"{THEME}/static"
TAILWIND_CSS = "tailwind.min.css"


def title_case_custom(title):
    # Use regex to handle apostrophes correctly
    # This regex will ensure that letters following apostrophes are not capitalized
    title = capwords(title)

    return title


def group_articles(articles):
    """Group articles by the first letter of their title and sort them alphabetically."""
    grouped = {}
    articles_to_ignore = {"the", "an", "a"}

    # Group articles by the first letter
    for article in articles:
        title = article.title
        words = title.split()

        # Determine the first letter to consider
        if len(words) > 1 and words[0].lower() in articles_to_ignore:
            # Ignore the first word if it's an article
            first_letter = words[1][0].upper() if len(words[1]) > 0 else "A"
        else:
            # Use the first letter of the first word
            first_letter = words[0][0].upper() if len(words) > 0 else "A"

        if first_letter not in grouped:
            grouped[first_letter] = []
        grouped[first_letter].append(article)

    # Sort the articles in each group alphabetically by title, ignoring articles
    for letter in grouped:
        grouped[letter].sort(
            key=lambda x: "".join(x.title.split()[1:])
            if x.title.startswith(("A ", "An ", "The ")) and len(x.title.split()) > 1
            else x.title
        )

    # Create a sorted dictionary based on the keys (letters)
    sorted_grouped = {letter: grouped[letter] for letter in sorted(grouped.keys())}

    return sorted_grouped


def get_article_urls(articles):
    """Return a list of article URLs."""
    return [article.url for article in articles]


JINJA_FILTERS = {
    "group_articles": group_articles,
    "ceil": ceil,
    "title_case_custom": title_case_custom,
    "get_article_urls": get_article_urls,
}


def sort_articles(generator):
    generator.articles.sort(key=lambda article: article.title)


def register():
    signals.article_generator_finalized.connect(sort_articles)
