# thingstolearn

Things that I'm trying to learn for work etc.

## extractkit: a data extraction toolkit

A command line tool for pulling structured data out of text, web pages and local files.
Uses only the Python standard library (3.9+), so there is nothing to install. PDF support is the one optional extra (`pip install pypdf`).

Run from the repo folder: `python -m extractkit [-o FILE] [--csv] <command> <source>`

`<source>` can be a URL, a file path, or `-` to read from stdin.

| Command | What it does |
|---|---|
| `entities` | Emails, URLs, phone numbers, dates, money amounts, hashtags, IPv4 addresses, UUIDs from any text |
| `words` | Most frequent words (`--top N`) |
| `links` / `images` / `headings` | Everything of that type on a web page |
| `meta` | Page title plus description / Open Graph tags |
| `table` | An HTML table as rows (`--index N` picks which one) |
| `page-text` | Readable text of a page (scripts and styles removed) |
| `structured` | JSON-LD data embedded in a page (products, prices, recipes, articles, events) |
| `feed` | Entries of an RSS/Atom feed: title, link, date, summary |
| `sitemap` | URLs (and last-modified dates) from a sitemap.xml or sitemap index |
| `docx` | Paragraphs and tables from a Word file |
| `xlsx` | Rows of an Excel sheet as dicts (`--sheet NAME`) |
| `pptx` | Text of every PowerPoint slide |
| `pdf` | Text of each PDF page (optional: `pip install pypdf`) |
| `eml` | From / To / Subject / Date, body and attachment names of an email file |
| `py-outline` | Classes, functions and methods in a Python file, with line numbers and docstrings |
| `sqlite-schema` | Tables, columns, types and row counts of a SQLite database (read-only) |
| `csv-profile` | Per-column summary of a CSV: empties, distinct values, min/max/mean, top values |
| `json-flat` | Flatten nested JSON into `a.b[0].c` = value pairs |
| `log-summary` | Summarise an Apache/Nginx access log: top IPs, paths, status codes |
| `inventory` | List files in a folder with sizes, types and duplicate detection |

### Examples

```bash
python -m extractkit entities notes.txt
python -m extractkit --csv -o links.csv links https://example.com
python -m extractkit --csv -o prices.csv table https://example.com/products --index 1
python -m extractkit csv-profile sales.csv
python -m extractkit log-summary /var/log/nginx/access.log
python -m extractkit inventory ~/Downloads
python -m extractkit --csv -o orders.csv xlsx report.xlsx --sheet Orders
python -m extractkit feed https://example.com/feed.xml
python -m extractkit structured https://example.com/some-product
python -m extractkit sqlite-schema app.db
cat email.txt | python -m extractkit entities - --kinds emails phones
```

`-o`, `--csv` and `--ignore-robots` can go before or after the command name.

`--csv` works for commands that return a list of rows (`links`, `images`, `headings`, `table`, `words`, `json-flat`, `feed`, `sitemap`, `xlsx`, `pptx`, `pdf`, `py-outline`, `sqlite-schema`, `inventory`) and the output opens straight in Excel.

When you give a URL, `extractkit` checks the site's `robots.txt` first and refuses disallowed pages. Use `--ignore-robots` only where you have permission.

### Tests

```bash
python -m unittest discover -s tests -v
```

### Layout

- `extractkit/text.py` regex-based entity extraction
- `extractkit/web.py` HTML parsing (uses `html.parser`)
- `extractkit/files.py` CSV, JSON, log, folder, Python-source and SQLite tools
- `extractkit/documents.py` Word, Excel, PowerPoint, PDF and email files
- `extractkit/feeds.py` RSS/Atom feeds and sitemaps
- `extractkit/output.py` JSON / CSV output
- `extractkit/cli.py` command line wiring

Please only scrape sites you are allowed to, and respect their terms and robots.txt.
