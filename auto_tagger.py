import os
import random
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from google import genai
from tqdm import tqdm

try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import pelicanconf

    STANDARD_TAGS = set(pelicanconf.STANDARD_TAGS)
except ImportError:
    print("Error: Could not import pelicanconf.py.")
    sys.exit(1)


def process_file(client, filepath, force_retag=False):
    filename = os.path.basename(filepath)
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    parts = content.split("\n\n", 1)
    if len(parts) < 2:
        return "skipped", f"Skipped {filename}: No clear metadata/body separation."

    metadata_block, body = parts
    has_tags = re.search(r"^Tags:", metadata_block, flags=re.MULTILINE | re.IGNORECASE)

    if has_tags and not force_retag:
        return "skipped", f"Skipped {filename}: Already has tags."

    allowed_tags_str = ", ".join(sorted(STANDARD_TAGS))
    prompt = (
        "Read the following poem and provide 1 to 4 comma-separated tags "
        "that describe its theme, tone, or subject matter. "
        "You MUST ONLY select tags from the following list. Do not invent any new tags.\n"
        f"Allowed tags: {allowed_tags_str}\n\n"
        "Provide ONLY the tags as a single line, lowercase, separated by commas, "
        "with no other text.\n\n"
        f"Poem:\n{body}"
    )

    max_retries = 5
    base_delay = 1.0

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )

            raw_tags = response.text.strip().strip(".")
            if not raw_tags:
                return "failed", f"Failed {filename}: Empty response."

            parsed_tags = [t.strip().lower() for t in raw_tags.split(",")]
            valid_tags = [t for t in parsed_tags if t in STANDARD_TAGS]

            if not valid_tags:
                return (
                    "failed",
                    f"Failed {filename}: API returned no valid standard tags (got: {raw_tags}).",
                )

            new_tags_str = ", ".join(valid_tags)

            if has_tags:
                new_metadata = re.sub(
                    r"^Tags:.*$",
                    f"Tags: {new_tags_str}",
                    metadata_block,
                    flags=re.MULTILINE | re.IGNORECASE,
                )
            else:
                new_metadata = metadata_block.rstrip() + f"\nTags: {new_tags_str}"

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_metadata + "\n\n" + body)

            return "updated", f"Updated {filename} with tags: {new_tags_str}"

        except Exception as e:
            error_msg = str(e)
            if "503" in error_msg or "429" in error_msg:
                if attempt == max_retries - 1:
                    return (
                        "failed",
                        f"Failed {filename} after {max_retries} attempts: {e}",
                    )
                sleep_time = base_delay * (2**attempt) + random.uniform(0, 1)
                time.sleep(sleep_time)
            else:
                return "failed", f"Failed {filename}: {e}"


if __name__ == "__main__":
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set.")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    poetry_dir = os.path.join("content", "poetry")
    if not os.path.exists(poetry_dir):
        print(f"Error: Directory '{poetry_dir}' not found.")
        sys.exit(1)

    force_all = "--force" in sys.argv
    if force_all:
        print("Running in --force mode: All existing tags will be overwritten.")
    else:
        print("Running in normal mode: Skipping files that already have tags.")

    files_to_process = [
        os.path.join(poetry_dir, f)
        for f in os.listdir(poetry_dir)
        if f.endswith(".md") and f != "_template.md"
    ]

    stats = {"updated": 0, "skipped": 0, "failed": 0}
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {
            executor.submit(process_file, client, fp, force_all): fp
            for fp in files_to_process
        }

        for future in tqdm(
            as_completed(futures), total=len(files_to_process), desc="Tagging Files"
        ):
            status, message = future.result()
            stats[status] += 1
            # Uncomment the next line if you wish to see individual file outcomes during execution
            # tqdm.write(message)

    elapsed_time = time.time() - start_time

    print("\n--- Execution Summary ---")
    print(f"Total Time: {elapsed_time:.2f} seconds")
    print(f"Files Updated: {stats['updated']}")
    print(f"Files Skipped: {stats['skipped']}")
    print(f"Files Failed:  {stats['failed']}")
