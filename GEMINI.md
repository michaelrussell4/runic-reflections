# Project Overview: Runic Reflections

## Architecture & Tech Stack
- **Type:** Static Site Generator
- **Core Framework:** Pelican (Python)
- **Language:** Python (>= 3.11)
- **Dependency Management:** `uv` (`pyproject.toml`, `uv.lock`)
- **Main Dependencies:** `pelican[markdown]`, `pytailwindcss`, `tqdm`.
- **Styling:** Custom theme (`rr-theme`) with Tailwind CSS.

## Project Structure
- `content/`: Contains all Markdown content.
  - `content/poetry/`: Primary directory for articles (poems).
  - `content/pages/`: Static pages like `about.md`.
  - `content/images/`: Image assets.
- `rr-theme/`: Custom Pelican theme directory containing `static/` and `templates/`.
- `pelicanconf.py`: Main Pelican configuration file. Includes custom Jinja filters and a comprehensive list of standard tags (`STANDARD_TAGS`).
- `publishconf.py`: Production configuration for Pelican.
- `auto_tagger.py`: A custom utility script using the Google GenAI SDK (Gemini 2.5 Flash) to automatically generate and apply standardized tags to poetry markdown files based on their content.

## Key Configurations & Conventions
- **Site Name:** Runic Reflections (Author: Michael Russell)
- **URL Structure:** Articles are saved and served at `{date:%Y}/{slug}.html`.
- **Custom Jinja Filters:** The site utilizes several custom filters defined in `pelicanconf.py`:
  - `group_articles`: Groups articles alphabetically by the first letter.
  - `title_case_custom`: Custom title casing handling apostrophes.
  - `get_article_urls`, `format_number`, and standard `ceil`.
- **Article Sorting:** `pelicanconf.py` registers a signal (`article_generator_finalized`) to strictly sort articles alphabetically by title.
- **Standardized Tags:** The site enforces a strictly predefined list of tags (e.g., `whimsical`, `melancholic`, `philosophical`, `existential`, `nature`).

## Tooling & Workflows
- **Content Tagging:** Run `python auto_tagger.py` to auto-tag poetry files missing tags. Use the `--force` flag to overwrite existing tags. Requires the `GEMINI_API_KEY` environment variable.
- **Tailwind Integration:** The project uses `pytailwindcss` to manage Tailwind CSS generation natively within the Python environment.
- **Development Tasks:** Use `make` or `inv` (via `tasks.py`) commands for local building and serving, typical of standard Pelican setups.
