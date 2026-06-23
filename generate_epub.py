import os
import re
import zipfile
import uuid
from datetime import datetime
import xml.etree.ElementTree as ET
import html as html_lib

# Attempt to import markdown, which is installed in the pelican environment
try:
    import markdown
except ImportError:
    print("Error: 'markdown' package is required. Please install it or run within the proper environment.")
    raise

def parse_date(date_str, filepath):
    if not date_str:
        try:
            mtime = os.path.getmtime(filepath)
            return datetime.fromtimestamp(mtime)
        except Exception:
            return datetime.min

    formats = [
        "%Y/%m/%d %I:%M%p",  # e.g., 2024/07/18 03:06PM
        "%Y/%m/%d %H:%M",
        "%Y/%m/%d",
        "%Y-%m-%d %I:%M%p",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue

    # Try matching regex patterns if exact match fails
    try:
        match = re.search(r'(\d{4})[/-](\d{2})[/-](\d{2})', date_str)
        if match:
            return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except Exception:
        pass

    return datetime.min

def parse_markdown_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    metadata = {}
    body_lines = []
    in_headers = True

    for line in lines:
        if in_headers:
            if line.strip() == "":
                in_headers = False
                continue
            match = re.match(r'^([A-Za-z0-9_-]+):\s*(.*)$', line)
            if match:
                key = match.group(1).lower().strip()
                val = match.group(2).strip()
                metadata[key] = val
            else:
                in_headers = False
                body_lines.append(line)
        else:
            body_lines.append(line)

    body_content = '\n'.join(body_lines)
    return metadata, body_content

def slugify(s):
    s = s.lower()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'[\s-]+', '-', s)
    return s.strip('-')

def clean_html_entities(html_text):
    # First, convert named entities to their unicode character equivalents
    # to prevent XML parser errors in e-readers for entities like &nbsp;, &rdquo;, etc.
    import html.entities
    def replace_entity(match):
        entity = match.group(1)
        if entity in ['amp', 'lt', 'gt', 'quot', 'apos']:
            return f"&{entity};"
        # Convert named entity to unicode character
        cp = html.entities.name2codepoint.get(entity)
        if cp is not None:
            return chr(cp)
        return match.group(0)

    html_text = re.sub(r'&([a-zA-Z0-9]+);', replace_entity, html_text)
    
    # Second, escape ampersands not part of an XML entity
    html_text = re.sub(r'&(?!(amp|lt|gt|quot|apos|#[0-9]+|#x[0-9a-fA-F]+);)', '&amp;', html_text)
    return html_text

def fix_xhtml_tags(html_text):
    # Fix unclosed <br> tags
    html_text = re.sub(r'<br\s*([^>]*)(?<!/)>', r'<br \1/>', html_text, flags=re.IGNORECASE)
    # Fix unclosed <hr> tags
    html_text = re.sub(r'<hr\s*([^>]*)(?<!/)>', r'<hr \1/>', html_text, flags=re.IGNORECASE)
    # Fix unclosed <img> tags
    html_text = re.sub(r'<img\s*([^>]*)(?<!/)>', r'<img \1/>', html_text, flags=re.IGNORECASE)
    return html_text

def process_images(html_content, epub_zip, manifest_items):
    # Find all img tags and extract their src
    img_matches = re.findall(r'<img\s+[^>]*src=["\']([^"\']+)["\'][^>]*>', html_content, flags=re.IGNORECASE)
    
    for src in img_matches:
        # Resolve clean path
        # Pelican uses {static}/images/filename or {attach}/images/filename
        cleaned_src = src.replace('{static}', '').replace('{attach}', '').lstrip('/')
        
        filename = os.path.basename(cleaned_src)
        local_img_path = os.path.join("content", "images", filename)
        
        if os.path.exists(local_img_path):
            epub_img_path = f"OEBPS/images/{filename}"
            # Add to zip if not already added
            if epub_img_path not in epub_zip.namelist():
                # Detect media type
                ext = os.path.splitext(filename)[1].lower()
                media_type = "image/png"
                if ext in ['.jpg', '.jpeg']:
                    media_type = "image/jpeg"
                elif ext == '.gif':
                    media_type = "image/gif"
                elif ext == '.svg':
                    media_type = "image/svg+xml"
                
                # Add to manifest
                base_name = os.path.splitext(filename)[0]
                img_id = f"img_{slugify(base_name)}"
                manifest_items.append(f'<item id="{img_id}" href="images/{filename}" media-type="{media_type}"/>')
                
                # Write to zip
                epub_zip.write(local_img_path, epub_img_path)
            
            # Replace in HTML
            html_content = html_content.replace(src, f"../images/{filename}")
        else:
            print(f"Warning: Referenced image not found locally: {local_img_path}")
            
    return html_content

def validate_xml(xml_content, filename):
    try:
        # Strip DOCTYPE declaration to avoid attempting to download external DTDs during validation
        clean_xml = re.sub(r'<!DOCTYPE[^>]*>', '', xml_content)
        ET.fromstring(clean_xml)
    except ET.ParseError as e:
        print(f"XML validation failed for {filename}: {e}")
        lines = xml_content.split('\n')
        line_num = e.position[0] - 1
        col_num = e.position[1]
        start = max(0, line_num - 3)
        end = min(len(lines), line_num + 4)
        for idx in range(start, end):
            prefix = "--> " if idx == line_num else "    "
            print(f"{prefix}{idx+1:3d}: {lines[idx]}")
            if idx == line_num:
                print(" " * (col_num + 8) + "^")
        raise ValueError(f"Invalid XML generated for {filename}: {e}")

def build_epub(poetry_dir, cover_img_path, output_epub_path):
    print("Collecting and parsing poetry markdown files...")
    poems = []
    
    for root, _, files in os.walk(poetry_dir):
        for file in files:
            if file.endswith('.md') and not file.startswith('_') and not file.startswith('.'):
                filepath = os.path.join(root, file)
                metadata, body = parse_markdown_file(filepath)
                
                # Ignore draft or hidden poems
                if metadata.get('status') in ['hidden', 'draft']:
                    continue
                
                # Extract details
                title = metadata.get('title', file[:-3])
                date_str = metadata.get('date', '')
                parsed_date = parse_date(date_str, filepath)
                tags = [t.strip() for t in metadata.get('tags', '').split(',') if t.strip()]
                category = metadata.get('category', 'Poetry')
                category = category.strip().title() if category else 'Poetry'
                
                poems.append({
                    'title': title,
                    'date': date_str,
                    'parsed_date': parsed_date,
                    'tags': tags,
                    'category': category,
                    'body': body,
                    'slug': slugify(title) or slugify(file[:-3])
                })
                
    # Sort chronologically by date
    poems.sort(key=lambda p: p['parsed_date'])
    print(f"Found {len(poems)} items to compile.")

    # Group poems by category, preserving chronological order
    grouped_poems = {}
    for poem in poems:
        cat = poem['category']
        if cat not in grouped_poems:
            grouped_poems[cat] = []
        grouped_poems[cat].append(poem)

    # Sort categories: predefined ones first, then others alphabetically
    category_order = ["Poetry", "Essays", "Short Stories"]
    all_categories = list(grouped_poems.keys())

    def cat_sort_key(c):
        try:
            return (0, category_order.index(c))
        except ValueError:
            return (1, c)

    sorted_categories = sorted(all_categories, key=cat_sort_key)

    # Unique identifiers
    book_uuid = uuid.uuid4()
    modified_time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    build_date_str = datetime.now().strftime("%B %d, %Y")

    # Start writing zip file
    with zipfile.ZipFile(output_epub_path, 'w') as epub:
        # 1. mimetype (MUST be first, uncompressed)
        epub.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)

        # 2. META-INF/container.xml
        container_xml = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"""
        epub.writestr('META-INF/container.xml', container_xml)

        # 3. OEBPS/style.css
        style_css = """body {
  font-family: "Georgia", "Times New Roman", serif;
  line-height: 1.6;
  margin: 5% 8%;
  color: #111111;
  background-color: #ffffff;
}

h1, h2, h3, h4 {
  font-family: "Montserrat", "Helvetica Neue", "Arial", sans-serif;
  color: #2c1654;
  text-align: center;
  margin-top: 1.5em;
  margin-bottom: 0.5em;
}

h1 {
  font-size: 2.2em;
  border-bottom: 1px solid #eeeeee;
  padding-bottom: 0.3em;
}

h2 {
  font-size: 1.6em;
}

h3 {
  font-size: 1.3em;
}

p {
  margin-bottom: 1.2em;
  text-align: justify;
}

/* Poetry specific layouts */
blockquote {
  margin: 1.5em auto;
  max-width: 32em;
  border-left: none;
  padding: 0;
  font-style: normal;
}

blockquote ul {
  list-style-type: none;
  padding-left: 0;
  margin-left: 0;
}

blockquote li {
  text-indent: -1.5em;
  padding-left: 1.5em;
  margin-bottom: 0.6em;
  line-height: 1.5;
}

/* Notes at the end of poems */
.poem-body h2 {
  margin-top: 3em;
  border-top: 1px solid #eeeeee;
  padding-top: 1em;
  font-size: 1.1em;
  font-weight: bold;
  color: #555555;
  text-align: left;
}

.poem-body h2 + p {
  font-size: 0.9em;
  color: #555555;
  line-height: 1.5;
  margin-top: 0.5em;
}

.poem-body h2 ~ p {
  font-size: 0.9em;
  color: #555555;
  line-height: 1.5;
}

.poem-meta {
  text-align: center;
  font-size: 0.85em;
  color: #777777;
  font-style: italic;
  margin-bottom: 2.5em;
}

.poem-tags {
  display: block;
  margin-top: 0.3em;
  font-size: 0.8em;
  color: #999999;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Cover styling */
.cover-container {
  text-align: center;
  padding: 0;
  margin: 0;
}

.cover-image {
  max-width: 100%;
  max-height: 100%;
  height: auto;
  width: auto;
}

/* TOC page styling */
.toc-title {
  font-size: 2em;
  margin-bottom: 1.5em;
  text-align: center;
}

.toc-list {
  list-style-type: none;
  padding-left: 0;
  max-width: 85%;
  margin: 2em auto;
}

.toc-item {
  margin-bottom: 0.8em;
  border-bottom: 1px dotted #cccccc;
  position: relative;
}

.toc-link {
  text-decoration: none;
  color: #2c1654;
  font-weight: 500;
  background-color: #ffffff;
  padding-right: 0.3em;
}

/* Tables */
table {
  width: 100%;
  border-collapse: collapse;
  margin: 1.5em 0;
  font-size: 0.9em;
  font-family: "Montserrat", "Helvetica Neue", "Arial", sans-serif;
}

th {
  background-color: #2c1654;
  color: #ffffff;
  font-weight: bold;
  text-align: left;
  padding: 8px 12px;
  border: 1px solid #2c1654;
}

td {
  padding: 8px 12px;
  border: 1px solid #dddddd;
}

tr:nth-child(even) {
  background-color: #f8f6fa;
}

.toc-build-date {
  text-align: center;
  font-size: 0.85em;
  color: #777777;
  font-style: italic;
  margin-top: 3em;
  border-top: 1px solid #eeeeee;
  padding-top: 1em;
}
"""
        epub.writestr('OEBPS/style.css', style_css)

        # 4. OEBPS/images/cover.png
        if os.path.exists(cover_img_path):
            epub.write(cover_img_path, 'OEBPS/images/cover.png')
            has_cover = True
        else:
            print(f"Warning: Cover image not found at {cover_img_path}")
            has_cover = False

        # 5. OEBPS/cover.xhtml
        if has_cover:
            cover_xhtml = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en" lang="en">
<head>
  <title>Cover</title>
  <link rel="stylesheet" type="text/css" href="style.css"/>
  <style type="text/css">
    @page { padding: 0; margin: 0; }
    body { padding: 0; margin: 0; text-align: center; background-color: #ffffff; }
  </style>
</head>
<body>
  <div class="cover-container">
    <img src="images/cover.png" alt="Cover Image" class="cover-image" />
  </div>
</body>
</html>"""
            validate_xml(cover_xhtml, "cover.xhtml")
            epub.writestr('OEBPS/cover.xhtml', cover_xhtml)

        # 6. Generate Section Dividers and Chapters (Poems)
        manifest_items = []
        spine_items = []
        toc_categories_xhtml = []
        toc_ncx_items = []
        
        # Helper to convert numbers to Roman numerals
        def to_roman(n):
            romans = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI", 7: "VII", 8: "VIII", 9: "IX", 10: "X"}
            return romans.get(n, str(n))
            
        play_order = 3 # Start after Cover (1) and TOC (2)
        
        for cat_idx, cat_name in enumerate(sorted_categories, start=1):
            cat_slug = slugify(cat_name)
            roman_num = to_roman(cat_idx)
            
            # Create a section divider page
            sec_filename = f"sections/section_{cat_slug}.xhtml"
            sec_id = f"sec_{cat_slug}"
            
            sec_xhtml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>
  <title>{cat_name}</title>
  <link rel="stylesheet" type="text/css" href="../style.css"/>
  <style type="text/css">
    body {{
      margin: 0;
      padding: 0;
      text-align: center;
      background-color: #ffffff;
    }}
    .section-divider-container {{
      margin-top: 35%;
    }}
    .part-number {{
      font-size: 1.2em;
      text-transform: uppercase;
      letter-spacing: 0.2em;
      color: #777777;
      margin-bottom: 0.5em;
    }}
    .part-title {{
      font-size: 2.5em;
      font-weight: bold;
      color: #2c1654;
      border: none;
      padding: 0;
    }}
    .ornament {{
      font-size: 1.5em;
      color: #2c1654;
      margin-top: 0.5em;
    }}
  </style>
</head>
<body>
  <div class="section-divider-container">
    <div class="part-number">Part {roman_num}</div>
    <h1 class="part-title">{cat_name}</h1>
    <div class="ornament">❦</div>
  </div>
</body>
</html>"""
            validate_xml(sec_xhtml, sec_filename)
            epub.writestr(f"OEBPS/{sec_filename}", sec_xhtml)
            
            # Register Section Divider in manifest and spine
            manifest_items.append(f'<item id="{sec_id}" href="{sec_filename}" media-type="application/xhtml+xml"/>')
            spine_items.append(f'<itemref idref="{sec_id}"/>')
            
            # For Hierarchical TOC (HTML)
            toc_poems_xhtml = []
            
            # For Hierarchical TOC (NCX)
            toc_ncx_subpoints = []
            cat_play_order = play_order
            play_order += 1 # Increment for the Section Divider itself
            
            # Loop over poems in this category
            for poem in grouped_poems[cat_name]:
                ch_filename = f"chapters/poem_{poem['slug']}.xhtml"
                ch_id = f"poem_{poem['slug']}"
                
                body_html = markdown.markdown(poem['body'], extensions=['extra'], output_format='xhtml')
                body_html = fix_xhtml_tags(body_html)
                body_html = process_images(body_html, epub, manifest_items)
                body_html = clean_html_entities(body_html)
                
                escaped_title = html_lib.escape(poem['title'])
                escaped_date = html_lib.escape(poem['date'])
                escaped_tags_list = [html_lib.escape(t) for t in poem['tags']]
                
                tags_str = ", ".join(escaped_tags_list) if escaped_tags_list else "un-tagged"
                tags_xhtml = f'<span class="poem-tags">Tagged: {tags_str}</span>'
                
                poem_xhtml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>
  <title>{escaped_title}</title>
  <link rel="stylesheet" type="text/css" href="../style.css"/>
</head>
<body>
  <div class="poem-container">
    <h1 class="poem-title">{escaped_title}</h1>
    <div class="poem-meta">
      <span class="poem-date">{escaped_date}</span>
      {tags_xhtml}
    </div>
    <div class="poem-body">
      {body_html}
    </div>
  </div>
</body>
</html>"""
                validate_xml(poem_xhtml, ch_filename)
                epub.writestr(f"OEBPS/{ch_filename}", poem_xhtml)
                
                # Register poem in manifest and spine
                manifest_items.append(f'<item id="{ch_id}" href="{ch_filename}" media-type="application/xhtml+xml"/>')
                spine_items.append(f'<itemref idref="{ch_id}"/>')
                
                # Add to sub TOC items
                toc_poems_xhtml.append(f'<li><a href="{ch_filename}">{escaped_title}</a></li>')
                
                toc_ncx_subpoints.append(f"""      <navPoint id="navpoint-{ch_id}" playOrder="{play_order}">
        <navLabel><text>{escaped_title}</text></navLabel>
        <content src="{ch_filename}"/>
      </navPoint>""")
                play_order += 1
                
            # Combine Category TOC items
            joined_poems_xhtml = "\n        ".join(toc_poems_xhtml)
            toc_categories_xhtml.append(f"""<li>
      <a href="{sec_filename}" style="font-weight: bold; font-size: 1.1em;">Part {roman_num}: {cat_name}</a>
      <ol class="toc-sub-list">
        {joined_poems_xhtml}
      </ol>
    </li>""")
            
            joined_ncx_subpoints = "\n".join(toc_ncx_subpoints)
            toc_ncx_items.append(f"""    <navPoint id="category-{cat_slug}" playOrder="{cat_play_order}">
      <navLabel><text>Part {roman_num}: {cat_name}</text></navLabel>
      <content src="{sec_filename}"/>
{joined_ncx_subpoints}
    </navPoint>""")

        # 7. OEBPS/toc.xhtml (EPUB 3 nav doc)
        cover_toc_xhtml = '<li><a href="cover.xhtml">Cover</a></li>' if has_cover else ''
        joined_toc_categories_xhtml = "\n      ".join(toc_categories_xhtml)
        toc_xhtml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en" lang="en">
<head>
  <title>Table of Contents</title>
  <link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
  <nav epub:type="toc" id="toc">
    <h1 class="toc-title">Table of Contents</h1>
    <ol class="toc-list-root">
      {cover_toc_xhtml}
      <li><a href="toc.xhtml">Table of Contents</a></li>
      {joined_toc_categories_xhtml}
    </ol>
    <p class="toc-build-date">Compiled on {build_date_str}</p>
  </nav>
</body>
</html>"""
        validate_xml(toc_xhtml, "toc.xhtml")
        epub.writestr('OEBPS/toc.xhtml', toc_xhtml)

        # 8. OEBPS/toc.ncx (EPUB 2 backward compatibility)
        cover_toc_ncx = '<navPoint id="navpoint-cover" playOrder="1"><navLabel><text>Cover</text></navLabel><content src="cover.xhtml"/></navPoint>' if has_cover else ''
        joined_toc_ncx_items = "\n".join(toc_ncx_items)
        toc_ncx = f"""<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="urn:uuid:{book_uuid}"/>
    <meta name="dtb:depth" content="2"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle>
    <text>Runic Reflections</text>
  </docTitle>
  <navMap>
    {cover_toc_ncx}
    <navPoint id="navpoint-toc" playOrder="2">
      <navLabel><text>Table of Contents</text></navLabel>
      <content src="toc.xhtml"/>
    </navPoint>
    {joined_toc_ncx_items}
  </navMap>
</ncx>"""
        validate_xml(toc_ncx, "toc.ncx")
        epub.writestr('OEBPS/toc.ncx', toc_ncx)

        # 9. OEBPS/content.opf (Book manifest)
        manifest_str = "\n    ".join(manifest_items)
        spine_str = "\n    ".join(spine_items)
        cover_meta_opf = '<meta name="cover" content="cover-image"/>' if has_cover else ''
        cover_manifest_opf = '<item id="cover-image" href="images/cover.png" media-type="image/png" properties="cover-image"/>\n    <item id="cover" href="cover.xhtml" media-type="application/xhtml+xml"/>' if has_cover else ''
        cover_spine_opf = '<itemref idref="cover"/>' if has_cover else ''
        
        content_opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="pub-id" version="3.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="pub-id">urn:uuid:{book_uuid}</dc:identifier>
    <dc:title>Runic Reflections</dc:title>
    <dc:language>en</dc:language>
    <dc:creator id="creator">Michael Russell</dc:creator>
    <dc:publisher>Runic Reflections</dc:publisher>
    <dc:date>{modified_time}</dc:date>
    <meta property="dcterms:modified">{modified_time}</meta>
    {cover_meta_opf}
  </metadata>
  <manifest>
    <item id="style" href="style.css" media-type="text/css"/>
    {cover_manifest_opf}
    <item id="toc" href="toc.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    {manifest_str}
  </manifest>
  <spine toc="ncx">
    {cover_spine_opf}
    <itemref idref="toc"/>
    {spine_str}
  </spine>
</package>"""
        validate_xml(content_opf, "content.opf")
        epub.writestr('OEBPS/content.opf', content_opf)

    print(f"Successfully generated EPUB at {output_epub_path}")

if __name__ == "__main__":
    poetry_directory = "content/poetry"
    cover_image = "content/images/runic_reflections_cover.png"
    output_epub = "content/images/runic_reflections.epub"
    
    build_epub(poetry_directory, cover_image, output_epub)
