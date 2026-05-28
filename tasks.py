import datetime
import glob
import hashlib
import json
import os
import shlex
import shutil
import sys

from invoke.main import program
from invoke.tasks import task
from pelican import main as pelican_main
from pelican.server import ComplexHTTPRequestHandler, RootedHTTPServer
from pelican.settings import DEFAULT_CONFIG, get_settings_from_file

OPEN_BROWSER_ON_SERVE = True
SETTINGS_FILE_BASE = "pelicanconf.py"
SETTINGS = {}
SETTINGS.update(DEFAULT_CONFIG)
LOCAL_SETTINGS = get_settings_from_file(SETTINGS_FILE_BASE)
SETTINGS.update(LOCAL_SETTINGS)

CONFIG = {
    "settings_base": SETTINGS_FILE_BASE,
    "settings_publish": "publishconf.py",
    # Output path. Can be absolute or relative to tasks.py. Default: 'output'
    "deploy_path": SETTINGS["OUTPUT_PATH"],
    # Github Pages configuration
    "github_pages_branch": "gh-pages",
    "commit_message": f"'Publish site on {datetime.date.today().isoformat()}'",
    # Host and port for `serve`
    "host": "localhost",
    "port": 8000,
}


def build_tailwind(c):
    """Compile Tailwind CSS, hash it for cache-busting, and write an asset manifest."""
    input_css = "rr-theme/static/css/tailwind-input.css"
    output_css = "rr-theme/static/css/tailwind.css"
    css_dir = "rr-theme/static/css"

    print("Compiling and minifying Tailwind CSS...")

    # Force absolute paths to ensure target safety across directories
    input_abs = os.path.abspath(input_css)
    output_abs = os.path.abspath(output_css)

    # Run pytailwindcss as a python module inside the active environment shell context.
    # This completely bypasses Windows CMD unquoted/quoted nested path parsing errors.
    c.run(
        f'"{sys.executable}" -m pytailwindcss -i "{input_abs}" -o "{output_abs}" --minify',
        hide=False,
    )

    # Clear out old hashed files to prevent accumulation
    for old_hashed_file in glob.glob(os.path.join(css_dir, "tailwind.*.css")):
        try:
            os.remove(old_hashed_file)
        except OSError:
            pass

    # Compute hash from compiled payload
    with open(output_css, "rb") as f:
        file_hash = hashlib.md5(f.read()).hexdigest()[:8]

    hashed_filename = f"tailwind.{file_hash}.css"
    shutil.copy(output_css, os.path.join(css_dir, hashed_filename))

    # Save mapping for pelicanconf context resolution
    manifest = {"TAILWIND_CSS": hashed_filename}
    with open("asset_manifest.json", "w") as f:
        json.dump(manifest, f)

    print(f"Asset pipeline ready: Generated {hashed_filename}")


@task
def clean(c):
    """Remove generated files"""
    if os.path.isdir(CONFIG["deploy_path"]):
        shutil.rmtree(CONFIG["deploy_path"])
        os.makedirs(CONFIG["deploy_path"])


@task
def build(c):
    """Build local version of site"""
    build_tailwind(c)
    pelican_run("-s {settings_base}".format(**CONFIG))


@task
def rebuild(c):
    """`build` with the delete switch"""
    build_tailwind(c)
    pelican_run("-d -s {settings_base}".format(**CONFIG))


@task
def regenerate(c):
    """Automatically regenerate site upon file modification"""
    build_tailwind(c)
    pelican_run("-r -s {settings_base}".format(**CONFIG))


@task
def serve(c):
    """Serve site at http://$HOST:$PORT/ (default is localhost:8000)"""

    class AddressReuseTCPServer(RootedHTTPServer):
        allow_reuse_address = True

    server = AddressReuseTCPServer(
        CONFIG["deploy_path"],
        (CONFIG["host"], CONFIG["port"]),
        ComplexHTTPRequestHandler,
    )

    if OPEN_BROWSER_ON_SERVE:
        # Open site in default browser
        import webbrowser

        webbrowser.open("http://{host}:{port}".format(**CONFIG))

    sys.stderr.write("Serving at {host}:{port} ...\n".format(**CONFIG))
    server.serve_forever()


@task
def reserve(c):
    """`build`, then `serve`"""
    build(c)
    serve(c)


@task
def preview(c):
    """Build production version of site"""
    pelican_run("-s {settings_publish}".format(**CONFIG))


@task
def livereload(c):
    """Automatically reload browser tab upon file modification."""
    from livereload import Server

    def cached_build():
        cmd = "-s {settings_base} -e CACHE_CONTENT=true LOAD_CONTENT_CACHE=true"
        pelican_run(cmd.format(**CONFIG))

    cached_build()
    server = Server()
    theme_path = SETTINGS["THEME"]
    watched_globs = [
        CONFIG["settings_base"],
        f"{theme_path}/templates/**/*.html",
    ]

    content_file_extensions = [".md", ".rst"]
    for extension in content_file_extensions:
        content_glob = "{}/**/*{}".format(SETTINGS["PATH"], extension)
        watched_globs.append(content_glob)

    static_file_extensions = [".css", ".js"]
    for extension in static_file_extensions:
        static_file_glob = f"{theme_path}/static/**/*{extension}"
        watched_globs.append(static_file_glob)

    for glob in watched_globs:
        server.watch(glob, cached_build)

    if OPEN_BROWSER_ON_SERVE:
        # Open site in default browser
        import webbrowser

        webbrowser.open("http://{host}:{port}".format(**CONFIG))

    server.serve(host=CONFIG["host"], port=CONFIG["port"], root=CONFIG["deploy_path"])


@task
def publish(c):
    """Publish to production via rsync"""
    pelican_run("-s {settings_publish}".format(**CONFIG))
    c.run(
        'rsync --delete --exclude ".DS_Store" -pthrvz -c '
        '-e "ssh -p {ssh_port}" '
        "{} {ssh_user}@{ssh_host}:{ssh_path}".format(
            CONFIG["deploy_path"].rstrip("/") + "/", **CONFIG
        )
    )


@task
def gh_pages(c):
    """Publish to GitHub Pages"""
    preview(c)
    c.run(
        "ghp-import -b {github_pages_branch} "
        "-m {commit_message} "
        "{deploy_path} -p".format(**CONFIG)
    )


def pelican_run(cmd):
    cmd += " " + program.core.remainder  # allows to pass-through args to pelican
    pelican_main(shlex.split(cmd))
