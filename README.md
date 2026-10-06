# thingstolearn

Things that I'm trying to learn for work etc.

## extractkit: a data extraction toolkit

A command line tool for pulling structured data out of text, web pages and local files.
Uses only the Python standard library (3.9+), so there is nothing to install.

Run from the repo folder: `python -m extractkit [-o FILE] [--csv] <command> <source>`

`<source>` can be a URL, a file path, or `-` to read from stdin.

| Command | What it does |
|---|---|
| `entities` | Emails, URLs, phone numbers, dates, money amounts, hashtags from any text |
| `words` | Most frequent words (`--top N`) |
| `links` / `images` / `headings` | Everything of that type on a web page |
| `meta` | Page title plus description / Open Graph tags |
| `table` | An HTML table as rows (`--index N` picks which one) |
| `page-text` | Readable text of a page (scripts and styles removed) |
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
cat email.txt | python -m extractkit entities - --kinds emails phones
```

`--csv` works for commands that return a list of rows (`links`, `images`, `headings`, `table`, `words`, `json-flat`, `inventory`) and the output opens straight in Excel.

### Tests

```bash
python -m unittest discover -s tests -v
```

### Layout

- `extractkit/text.py` regex-based entity extraction
- `extractkit/web.py` HTML parsing (uses `html.parser`)
- `extractkit/files.py` CSV, JSON, log and folder tools
- `extractkit/output.py` JSON / CSV output
- `extractkit/cli.py` command line wiring

Please only scrape sites you are allowed to, and respect their terms and robots.txt.
