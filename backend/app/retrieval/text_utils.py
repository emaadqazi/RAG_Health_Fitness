"""Shared text-cleaning helpers for titles/metadata coming back from literature APIs.

Some sources (observed on Europe PMC, and defensively applied to Semantic Scholar too)
return title fields that already contain HTML-entity-escaped markup as literal text,
e.g. a title arriving as the literal string "The &lt;i&gt;Comrades Marathon&lt;/i&gt;: a
narrative review..." instead of "The Comrades Marathon: a narrative review...". Left
as-is, React correctly (and unhelpfully) renders that literal string verbatim -- the
user sees the escaped entities on screen. Fixing this at ingestion (once, here) means
every place a title is displayed (Sources tab, citation chips, bottom citation list) is
automatically clean, rather than needing a rendering workaround in each component.

PubMed's title extraction already avoids this: it comes from real XML parsed via
`itertext()`, which yields only text nodes and inherently drops inline tags like
`<i>...</i>` -- `clean_title` is still applied there for defense-in-depth/consistency,
but is a no-op on already-clean text.
"""

from __future__ import annotations

import html
import re

_TAG_RE = re.compile(r"<[^>]+>")


def clean_title(text: str | None) -> str:
    if not text:
        return ""
    # Unescape first (turns literal "&lt;i&gt;" back into "<i>"), then strip any real
    # tags that results in (or that were already present unescaped).
    unescaped = html.unescape(text)
    return _TAG_RE.sub("", unescaped).strip()
