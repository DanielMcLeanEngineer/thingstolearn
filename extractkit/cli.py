"""Command line interface. Run `python -m extractkit --help`."""
import argparse
import sys

from . import documents, feeds, files, text, web
from .output import emit


def _read_source(source, respect_robots=True):
    """Read text from a URL, a file path, or '-' for stdin."""
    if source == "-":
        return sys.stdin.read()
    if source.startswith(("http://", "https://")):
        return web.fetch(source, respect_robots=respect_robots)
    with open(source, encoding="utf-8", errors="replace") as f:
        return f.read()


def _page(source, respect_robots=True):
    html = _read_source(source, respect_robots)
    return web.parse_html(html, source if source.startswith("http") else "")


def build_parser():
    p = argparse.ArgumentParser(prog="extractkit", description="Handy data extraction tools.")

    def add_common(parser, suppress):
        """Options accepted both before and after the command name."""
        d = (lambda v: argparse.SUPPRESS) if suppress else (lambda v: v)
        parser.add_argument("-o", "--out", default=d(None), help="save output to this file instead of printing")
        parser.add_argument("--csv", action="store_true", default=d(False), help="output CSV (for commands that return rows)")
        parser.add_argument("--ignore-robots", action="store_true", default=d(False),
                            help="do not check robots.txt before fetching a URL")

    add_common(p, suppress=False)
    sub = p.add_subparsers(dest="command", required=True)

    def add(name, help_, **kw):
        sp = sub.add_parser(name, help=help_)
        add_common(sp, suppress=True)
        sp.add_argument("source", help=kw.get("source_help", "URL, file path, or - for stdin"))
        return sp

    sp = add("entities", "emails, URLs, phones, dates, money, hashtags from text")
    sp.add_argument("--kinds", nargs="+", choices=list(text.PATTERNS), help="limit to these kinds")
    sp = add("words", "most frequent words in text")
    sp.add_argument("--top", type=int, default=20)
    add("links", "all links on a web page")
    add("images", "all images on a web page")
    add("headings", "h1-h3 headings on a web page")
    add("meta", "title and meta tags (description, og:*) of a web page")
    sp = add("table", "an HTML table as rows of dicts")
    sp.add_argument("--index", type=int, default=0, help="which table on the page (0 = first)")
    add("page-text", "readable text of a web page")
    add("csv-profile", "summarise each column of a CSV file", source_help="CSV file path")
    add("json-flat", "flatten a JSON file to key/value pairs", source_help="JSON file path")
    add("log-summary", "summarise a web server access log", source_help="log file path")
    add("structured", "JSON-LD structured data (products, recipes, articles...) embedded in a web page")
    add("feed", "entries of an RSS/Atom feed")
    add("sitemap", "URLs listed in a sitemap.xml")
    add("docx", "paragraphs and tables of a Word file", source_help=".docx file path")
    sp = add("xlsx", "rows of an Excel worksheet", source_help=".xlsx file path")
    sp.add_argument("--sheet", help="sheet name (default: first sheet)")
    add("pptx", "text of each PowerPoint slide", source_help=".pptx file path")
    add("pdf", "text of each PDF page (needs: pip install pypdf)", source_help=".pdf file path")
    add("eml", "headers, body and attachments of an email file", source_help=".eml file path")
    add("py-outline", "classes and functions in a Python file", source_help=".py file path")
    add("sqlite-schema", "tables, columns and row counts of a SQLite database", source_help="database file path")
    sp = add("inventory", "list files in a folder with sizes and duplicates", source_help="folder path")
    sp.add_argument("--no-dupes", action="store_true", help="skip duplicate detection (faster)")
    return p


def run(args):
    c, src = args.command, args.source
    robots = not args.ignore_robots
    if c == "entities":
        return text.extract_entities(_read_source(src, robots), args.kinds)
    if c == "words":
        return [{"word": w, "count": n} for w, n in text.word_frequencies(_read_source(src, robots), args.top)]
    if c in ("links", "images", "headings"):
        return _page(src, robots)[c]
    if c == "meta":
        page = _page(src, robots)
        return {"title": page["title"], **page["meta"]}
    if c == "page-text":
        return {"text": _page(src, robots)["text"]}
    if c == "structured":
        return _page(src, robots)["jsonld"]
    if c == "feed":
        return feeds.parse_feed(_read_source(src, robots))
    if c == "sitemap":
        return feeds.parse_sitemap(_read_source(src, robots))
    if c == "docx":
        return documents.read_docx(src)
    if c == "xlsx":
        return documents.read_xlsx(src, args.sheet)
    if c == "pptx":
        return documents.read_pptx(src)
    if c == "pdf":
        return documents.read_pdf(src)
    if c == "eml":
        return documents.read_eml(src)
    if c == "py-outline":
        return files.outline_python(src)
    if c == "sqlite-schema":
        return files.sqlite_schema(src)
    if c == "table":
        tables = _page(src, robots)["tables"]
        if args.index >= len(tables):
            sys.exit(f"Page has {len(tables)} table(s); --index {args.index} is out of range.")
        return web.tables_to_rows(tables[args.index])
    if c == "csv-profile":
        return files.profile_csv(src)
    if c == "json-flat":
        flat = files.load_json_flat(src)
        return [{"key": k, "value": v} for k, v in flat.items()]
    if c == "log-summary":
        return files.summarise_access_log(src)
    if c == "inventory":
        result = files.inventory(src, find_duplicates=not args.no_dupes)
        return result["files"] if args.csv else result


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        data = run(args)
    except (OSError, ValueError) as e:  # missing file, network error, bad JSON, ...
        sys.exit(f"Error: {e}")
    emit(data, args.out, args.csv)
