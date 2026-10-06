"""Parse RSS/Atom feeds and sitemaps (XML) into plain rows."""
from xml.etree import ElementTree as ET


def _local(tag):
    """Strip the XML namespace: '{http://...}title' -> 'title'."""
    return tag.rsplit("}", 1)[-1]


def _child_text(element, name):
    for child in element:
        if _local(child.tag) == name:
            return (child.text or "").strip()
    return ""


def _parse_xml(xml_text):
    try:
        return ET.fromstring(xml_text.strip())
    except ET.ParseError as e:
        raise ValueError(f"Not valid XML: {e}")


def parse_feed(xml_text):
    """RSS or Atom -> [{'title', 'link', 'published', 'summary'}]."""
    root = _parse_xml(xml_text)
    rows = []
    for item in root.iter():
        if _local(item.tag) not in ("item", "entry"):
            continue
        link = _child_text(item, "link")
        if not link:  # Atom stores the URL in an href attribute
            link = next((c.get("href", "") for c in item if _local(c.tag) == "link"), "")
        rows.append({
            "title": _child_text(item, "title"),
            "link": link,
            "published": _child_text(item, "pubDate") or _child_text(item, "published") or _child_text(item, "updated"),
            "summary": _child_text(item, "description") or _child_text(item, "summary"),
        })
    return rows


def parse_sitemap(xml_text):
    """Sitemap or sitemap index -> [{'url', 'lastmod', 'is_index'}]."""
    root = _parse_xml(xml_text)
    is_index = _local(root.tag) == "sitemapindex"
    return [
        {"url": _child_text(e, "loc"), "lastmod": _child_text(e, "lastmod"), "is_index": is_index}
        for e in root if _local(e.tag) in ("url", "sitemap")
    ]
