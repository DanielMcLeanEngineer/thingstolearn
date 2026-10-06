"""Extract links, headings, tables, metadata and text from a web page (standard library only)."""
import json
from html.parser import HTMLParser
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

SKIP_TAGS = {"script", "style", "noscript"}


USER_AGENT = "extractkit/1.0 (+learning project)"


def robots_allows(url, robots_text):
    """True if robots.txt content allows our user agent to fetch this URL."""
    parser = RobotFileParser()
    parser.parse(robots_text.splitlines())
    return parser.can_fetch(USER_AGENT, url)


def fetch(url, timeout=15, respect_robots=True):
    """Download a page and return its HTML as text. Checks the site's robots.txt first by default."""
    if respect_robots:
        parts = urlsplit(url)
        try:
            robots = fetch(f"{parts.scheme}://{parts.netloc}/robots.txt", timeout, respect_robots=False)
        except HTTPError as e:
            if e.code in (401, 403):
                raise ValueError(f"robots.txt denies access to {parts.netloc} (use --ignore-robots to override)")
            robots = ""  # 404 etc.: no rules, so allowed
        except OSError:
            robots = ""  # robots.txt unreachable: fall through to the real request, which reports any error
        if not robots_allows(url, robots):
            raise ValueError(f"robots.txt disallows fetching {url} (use --ignore-robots to override)")
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


class _PageParser(HTMLParser):
    def __init__(self, base_url=""):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title = ""
        self.meta = {}
        self.links = []
        self.images = []
        self.headings = []
        self.tables = []
        self.jsonld = []
        self.text_parts = []
        self._ld = None           # buffer while inside <script type="application/ld+json">
        self._stack = []          # currently open tags
        self._link = None         # [href, text parts]
        self._heading = None      # [tag, text parts]
        self._table = None        # list of rows
        self._row = None
        self._cell = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self._stack.append(tag)
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self._ld = []
        elif tag == "meta":
            key = attrs.get("name") or attrs.get("property")
            if key and attrs.get("content"):
                self.meta[key] = attrs["content"]
        elif tag == "a" and attrs.get("href"):
            self._link = [urljoin(self.base_url, attrs["href"]), []]
        elif tag == "img" and attrs.get("src"):
            self.images.append({"src": urljoin(self.base_url, attrs["src"]), "alt": attrs.get("alt", "")})
        elif tag in ("h1", "h2", "h3"):
            self._heading = [tag, []]
        elif tag == "table":
            self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag):
        if tag == "script" and self._ld is not None:
            try:
                self.jsonld.append(json.loads("".join(self._ld)))
            except ValueError:
                pass  # malformed JSON-LD: ignore
            self._ld = None
        if tag in self._stack:  # tolerate sloppy HTML
            while self._stack and self._stack.pop() != tag:
                pass
        if tag == "a" and self._link:
            self.links.append({"url": self._link[0], "text": " ".join("".join(self._link[1]).split())})
            self._link = None
        elif tag in ("h1", "h2", "h3") and self._heading:
            self.headings.append({"level": self._heading[0], "text": " ".join("".join(self._heading[1]).split())})
            self._heading = None
        elif tag in ("td", "th") and self._cell is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            if self._table:
                self.tables.append(self._table)
            self._table = None

    def handle_data(self, data):
        if self._ld is not None:
            self._ld.append(data)
            return
        if any(t in SKIP_TAGS for t in self._stack):
            return
        if "title" in self._stack:
            self.title += data
            return
        self.text_parts.append(data)
        for target in (self._link and self._link[1], self._heading and self._heading[1], self._cell):
            if target is not None:
                target.append(data)


def parse_html(html, base_url=""):
    """Parse HTML into a dict of title, meta, headings, links, images, tables and plain text."""
    parser = _PageParser(base_url)
    parser.feed(html)
    return {
        "title": " ".join(parser.title.split()),
        "meta": parser.meta,
        "headings": parser.headings,
        "links": parser.links,
        "images": parser.images,
        "tables": parser.tables,
        "jsonld": parser.jsonld,
        "text": "\n".join(line for line in (" ".join(p.split()) for p in parser.text_parts) if line),
    }


def tables_to_rows(table):
    """Turn a table (list of rows) into a list of dicts using the first row as headers."""
    if len(table) < 2:
        return []
    headers = table[0]
    return [dict(zip(headers, row)) for row in table[1:]]
