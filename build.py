#!/usr/bin/env python3
"""
build.py — Static blog builder for profcruz.com

Converts Markdown files in /drafts to HTML posts in /posts,
and regenerates the index page with all posts listed.

Usage:
    python build.py              # Build all drafts
    python build.py --clean      # Remove generated posts and rebuild

Markdown files should have YAML-like frontmatter:
---
title: My Post Title
subtitle: Optional subtitle
date: February 25, 2026
tags: Strategy, Governance
excerpt: A short description for the index page.
---

Post content in Markdown here...
"""

import os
import re
import sys
import html
from pathlib import Path
from datetime import datetime

# ── Configuration ──────────────────────────────────────────

SITE_DIR = Path(__file__).parent
DRAFTS_DIR = SITE_DIR / "drafts"
POSTS_DIR = SITE_DIR / "posts"
INDEX_FILE = SITE_DIR / "index.html"
TEMPLATE_DIR = SITE_DIR / "templates"

# ── Minimal Markdown → HTML converter ──────────────────────
# (No dependencies required. For richer Markdown, install
#  `markdown` package: pip install markdown)

def md_to_html(text):
    """Convert basic Markdown to HTML. Handles the essentials."""
    lines = text.split('\n')
    result = []
    in_list = False
    in_ol = False
    in_code = False
    in_blockquote = False
    bq_lines = []

    def flush_blockquote():
        nonlocal in_blockquote, bq_lines
        if in_blockquote:
            content = ' '.join(bq_lines)
            content = inline_format(content)
            result.append(f'<blockquote><p>{content}</p></blockquote>')
            in_blockquote = False
            bq_lines = []

    def inline_format(s):
        # Bold + italic
        s = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', s)
        # Bold
        s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
        # Italic
        s = re.sub(r'\*(.+?)\*', r'<em>\1</em>', s)
        # Inline code
        s = re.sub(r'`(.+?)`', r'<code>\1</code>', s)
        # Links
        s = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', s)
        return s

    for line in lines:
        stripped = line.strip()

        # Code blocks
        if stripped.startswith('```'):
            if in_code:
                result.append('</code></pre>')
                in_code = False
            else:
                lang = stripped[3:].strip()
                result.append(f'<pre><code>')
                in_code = True
            continue
        if in_code:
            result.append(html.escape(line))
            continue

        # Blockquotes
        if stripped.startswith('> '):
            if not in_blockquote:
                in_blockquote = True
                bq_lines = []
            bq_lines.append(stripped[2:])
            continue
        else:
            flush_blockquote()

        # Headings
        if m := re.match(r'^(#{1,3})\s+(.+)', stripped):
            level = len(m.group(1)) + 1  # h2, h3, h4 (h1 is title)
            if level > 4: level = 4
            result.append(f'<h{level}>{inline_format(m.group(2))}</h{level}>')
            continue

        # Horizontal rule
        if stripped in ('---', '***', '___') and len(stripped) >= 3:
            result.append('<hr>')
            continue

        # Unordered list
        if re.match(r'^[-*]\s+', stripped):
            if not in_list:
                result.append('<ul>')
                in_list = True
            content = re.sub(r'^[-*]\s+', '', stripped)
            result.append(f'<li>{inline_format(content)}</li>')
            continue
        elif in_list:
            result.append('</ul>')
            in_list = False

        # Ordered list
        if re.match(r'^\d+\.\s+', stripped):
            if not in_ol:
                result.append('<ol>')
                in_ol = True
            content = re.sub(r'^\d+\.\s+', '', stripped)
            result.append(f'<li>{inline_format(content)}</li>')
            continue
        elif in_ol:
            result.append('</ol>')
            in_ol = False

        # Empty line
        if not stripped:
            continue

        # Paragraph
        result.append(f'<p>{inline_format(stripped)}</p>')

    # Close any open elements
    flush_blockquote()
    if in_list: result.append('</ul>')
    if in_ol: result.append('</ol>')
    if in_code: result.append('</code></pre>')

    return '\n          '.join(result)


# ── Frontmatter parser ─────────────────────────────────────

def parse_frontmatter(content):
    """Extract YAML-like frontmatter and body from Markdown file."""
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', content, re.DOTALL)
    if not match:
        return {}, content

    meta = {}
    for line in match.group(1).split('\n'):
        if ':' in line:
            key, val = line.split(':', 1)
            meta[key.strip().lower()] = val.strip()

    return meta, match.group(2).strip()


# ── HTML generators ─────────────────────────────────────────

def slugify(title):
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s]+', '-', slug)
    slug = re.sub(r'-+', '-', slug).strip('-')
    return slug


def generate_post_html(meta, body_html):
    tags_str = meta.get('tags', '')
    date = meta.get('date', '')
    title = meta.get('title', 'Untitled')
    subtitle = meta.get('subtitle', '')

    meta_line = date
    if tags_str:
        meta_line += f' · {tags_str}'

    subtitle_html = f'<p class="post-subtitle">{subtitle}</p>' if subtitle else ''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(title)} — Prof Cruz</title>
  <meta name="description" content="{html.escape(meta.get('excerpt', ''))}">
  <link rel="stylesheet" href="../assets/style.css">
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>◈</text></svg>">
</head>
<body>

  <header class="site-header">
    <div class="container">
      <a href="/" class="site-name">Prof Cruz</a>
      <nav>
        <ul class="site-nav">
          <li><a href="/">Writing</a></li>
          <li><a href="/about.html">About</a></li>
        </ul>
      </nav>
    </div>
  </header>

  <main>
    <article>
      <header class="post-header">
        <div class="container">
          <div class="post-meta">{html.escape(meta_line)}</div>
          <h1>{html.escape(title)}</h1>
          {subtitle_html}
        </div>
      </header>

      <div class="post-content">
        <div class="container">
          {body_html}
        </div>
      </div>
    </article>
  </main>

  <footer class="site-footer">
    <div class="container">
      <p>&copy; 2026 Richard Cruz. All rights reserved.</p>
      <ul class="footer-links">
        <li><a href="mailto:richard@profcruz.com">Email</a></li>
        <li><a href="https://www.linkedin.com/in/richardcruz" target="_blank" rel="noopener">LinkedIn</a></li>
      </ul>
    </div>
  </footer>

</body>
</html>'''


def generate_index_item(meta, slug):
    tags_str = meta.get('tags', '')
    tags_html = ''
    if tags_str:
        tags = [t.strip() for t in tags_str.split(',')]
        tags_html = '<div class="post-tags">\n' + \
            '\n'.join(f'            <span class="post-tag">{html.escape(t)}</span>' for t in tags) + \
            '\n          </div>'

    return f'''        <article class="post-item">
          <div class="post-meta">{html.escape(meta.get('date', ''))}</div>
          <h2><a href="posts/{slug}.html">{html.escape(meta.get('title', 'Untitled'))}</a></h2>
          <p class="post-excerpt">{html.escape(meta.get('excerpt', ''))}</p>
          {tags_html}
        </article>'''


def generate_index(posts):
    """Generate complete index.html from list of (meta, slug) tuples."""
    items = '\n\n'.join(generate_index_item(m, s) for m, s in posts)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Prof Cruz — Thinking in Systems</title>
  <meta name="description" content="Notes on strategy, governance, transformation, and learning architecture by Richard Cruz.">
  <link rel="stylesheet" href="assets/style.css">
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>◈</text></svg>">
</head>
<body>

  <header class="site-header">
    <div class="container">
      <a href="/" class="site-name">Prof Cruz</a>
      <nav>
        <ul class="site-nav">
          <li><a href="/" class="active">Writing</a></li>
          <li><a href="/about.html">About</a></li>
        </ul>
      </nav>
    </div>
  </header>

  <main>
    <section class="index-hero">
      <div class="container">
        <h1>Thinking in Systems</h1>
        <p class="subtitle">Notes on strategy, governance, institutional transformation, and the architecture of learning — from 25 years at the intersection of theory and practice.</p>
      </div>
    </section>

    <section class="post-list">
      <div class="container">
{items}
      </div>
    </section>
  </main>

  <footer class="site-footer">
    <div class="container">
      <p>&copy; 2026 Richard Cruz. All rights reserved.</p>
      <ul class="footer-links">
        <li><a href="mailto:richard@profcruz.com">Email</a></li>
        <li><a href="https://www.linkedin.com/in/richardcruz" target="_blank" rel="noopener">LinkedIn</a></li>
      </ul>
    </div>
  </footer>

</body>
</html>'''


# ── Sort helper ─────────────────────────────────────────────

def parse_date(date_str):
    """Try to parse a date string. Returns datetime for sorting."""
    formats = ['%B %d, %Y', '%Y-%m-%d', '%b %d, %Y', '%d %B %Y']
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return datetime.min


# ── Main build ──────────────────────────────────────────────

def build():
    DRAFTS_DIR.mkdir(exist_ok=True)
    POSTS_DIR.mkdir(exist_ok=True)

    drafts = list(DRAFTS_DIR.glob('*.md'))
    if not drafts:
        print("No .md files found in /drafts. Add Markdown files there and re-run.")
        print(f"  Drafts directory: {DRAFTS_DIR}")
        return

    posts = []  # (meta, slug) for index generation

    for md_file in drafts:
        content = md_file.read_text(encoding='utf-8')
        meta, body = parse_frontmatter(content)

        if not meta.get('title'):
            meta['title'] = md_file.stem.replace('-', ' ').title()

        slug = slugify(meta['title'])
        body_html = md_to_html(body)
        post_html = generate_post_html(meta, body_html)

        out_path = POSTS_DIR / f"{slug}.html"
        out_path.write_text(post_html, encoding='utf-8')
        print(f"  ✓ {md_file.name} → posts/{slug}.html")

        posts.append((meta, slug))

    # Sort by date, newest first
    posts.sort(key=lambda p: parse_date(p[0].get('date', '')), reverse=True)

    # Generate index
    index_html = generate_index(posts)
    INDEX_FILE.write_text(index_html, encoding='utf-8')
    print(f"\n  ✓ index.html updated with {len(posts)} post(s)")
    print("\nDone. Your site is ready to deploy.")


if __name__ == '__main__':
    if '--clean' in sys.argv:
        for f in POSTS_DIR.glob('*.html'):
            f.unlink()
            print(f"  Removed {f}")
        print()

    build()
