"""Print or save results as JSON or CSV."""
import csv
import json
import sys


def to_json(data):
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


def write_csv(rows, file):
    """Write a list of dicts as CSV to an open file."""
    rows = list(rows)
    if not rows:
        print("No rows found.", file=sys.stderr)
        return
    fieldnames = list(dict.fromkeys(k for row in rows for k in row))
    writer = csv.DictWriter(file, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)


def emit(data, out_path=None, as_csv=False):
    """Send data to stdout or a file. CSV needs a list of dicts."""
    if as_csv and not (isinstance(data, list) and all(isinstance(r, dict) for r in data)):
        sys.exit("--csv only works for commands that return a list of rows (e.g. links, images, table, inventory).")
    stream = open(out_path, "w", newline="", encoding="utf-8") if out_path else sys.stdout
    try:
        if as_csv:
            write_csv(data, stream)
        else:
            stream.write(to_json(data) + "\n")
    finally:
        if out_path:
            stream.close()
            print(f"Saved to {out_path}", file=sys.stderr)
