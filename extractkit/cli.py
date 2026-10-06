"""Command line interface. Run `python -m extractkit --help`."""
import argparse
import sys

from . import files, text, web
from .output import emit


def _read_source(source):
    """Read text from a URL, a file path, or '-' for stdin."""
    if source == "-":
        return sys.stdin.read()
    if source.startswith(("http://", "https://")):
        return web.fetch(source)
    with open(source, encoding="utf-8", errors="replace") as f:
        return f.read()


def _page(source):
    html = _read_source(source)
    return web.parse_html(html, source if source.startswith("http") else "")


def build_parser():
    p = argparse.ArgumentParser(prog="extractkit", description="Handy data extraction tools.")
    p.add_argument("-o", "--out", help="save output to this file instead of printing")
    p.add_argument("--csv", action="store_true", help="output CSV (for commands that return rows)")
    sub = p.add_subparsers(dest="command", required=True)

    def add(name, help_, **kw):
        sp = sub.add_parser(name, help=help_)
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
    sp = add("inventory", "list files in a folder with sizes and duplicates", source_help="folder path")
    sp.add_argument("--no-dupes", action="store_true", help="skip duplicate detection (faster)")
    return p


def run(args):
    c, src = args.command, args.source
    if c == "entities":
        return text.extract_entities(_read_source(src), args.kinds)
    if c == "words":
        return [{"word": w, "count": n} for w, n in text.word_frequencies(_read_source(src), args.top)]
    if c in ("links", "images", "headings"):
        return _page(src)[c]
    if c == "meta":
        page = _page(src)
        return {"title": page["title"], **page["meta"]}
    if c == "page-text":
        return {"text": _page(src)["text"]}
    if c == "table":
        tables = _page(src)["tables"]
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
