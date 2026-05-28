# pylint: disable=missing-function-docstring,missing-module-docstring

import json
import os
from datetime import datetime
from math import ceil
from string import capwords

from pelican import signals

AUTHOR = "Michael Russell"
SITENAME = "Runic Reflections"
SITE_DESCRIPTION = "A collection of poems exploring the human experience, nature, philosophy, and the beauty of language."
SITE_KEYWORDS = "poetry, reflections, philosophy, nature, literature"
SITEURL = ""
AUTHOR_SLUG = "michael-russell"
AUTHOR_EMAIL = None  # Not publicly displayed

PATH = "content"
ARTICLE_PATHS = ["poetry"]
ARTICLE_SAVE_AS = "{date:%Y}/{slug}.html"
ARTICLE_URL = "{date:%Y}/{slug}.html"
ARTICLE_ORDER_BY = "reversed-date"

TIMEZONE = "America/Denver"

DEFAULT_LANG = "en"

STANDARD_TAGS = (
    "abstract",
    "adventurous",
    "childrens",
    "comical",
    "educational",
    "existential",
    "fantasy",
    "logophile",
    "melancholic",
    "narrative",
    "nature",
    "nostalgic",
    "philosophical",
    "reflective",
    "religious",
    "romantic",
    "satirical",
    "seasonal",
    "serious",
    "surreal",
    "whimsical",
)

# Feed generation
SOCIAL = None  # Can add social media links here if desired
FEED_DOMAIN = "https://runicreflections.com"
FEED_ALL_ATOM = None
FEED_ALL_RSS = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

DEFAULT_PAGINATION = 6
USE_FOLDER_AS_CATEGORY = True
DEFAULT_DATE_FORMAT = "%B %d, %Y"

# Analytics & Comments (set these in publishconf.py for production)
GOOGLE_ANALYTICS = None  # Set to your Google Analytics ID for tracking
DISQUS_SITENAME = None  # Enable comments if desired

# Theme
THEME = "rr-theme"
STATIC_PATHS = ["images"]
THEME_STATIC_PATHS = ["static"]

# Dynamically extract current cache-busted asset name
TAILWIND_CSS = "tailwind.css"
manifest_path = "asset_manifest.json"
if os.path.exists(manifest_path):
    try:
        with open(manifest_path, "r") as f:
            TAILWIND_CSS = json.load(f).get("TAILWIND_CSS", "tailwind.css")
    except Exception:
        pass


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
            key=lambda x: (
                "".join(x.title.split()[1:])
                if x.title.startswith(("A ", "An ", "The "))
                and len(x.title.split()) > 1
                else x.title
            )
        )

    # Create a sorted dictionary based on the keys (letters)
    sorted_grouped = {letter: grouped[letter] for letter in sorted(grouped.keys())}

    return sorted_grouped


def format_number(value):
    """Format a number with commas."""
    return f"{value:,}"


def get_article_urls(articles):
    """Return a list of article URLs."""
    return [article.url for article in articles]


JINJA_FILTERS = {
    "group_articles": group_articles,
    "ceil": ceil,
    "title_case_custom": title_case_custom,
    "get_article_urls": get_article_urls,
    "format_number": format_number,
}

# Make 'now' available in all templates
JINJA_GLOBALS = {
    "now": datetime.now(),
}


def sort_articles(generator):
    # Set up neighbor relationships based on the current (date-ordered) article list
    # WITHOUT sorting them - keep articles in their natural date order for main page display
    for i, article in enumerate(generator.articles):
        article.next_article = (
            generator.articles[i + 1] if i + 1 < len(generator.articles) else None
        )
        article.prev_article = generator.articles[i - 1] if i > 0 else None


# Connect the signal when pelicanconf is loaded
signals.article_generator_finalized.connect(sort_articles)
