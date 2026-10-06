"""Extract information from local files: CSV profiles, nested JSON, log files and folder inventories."""
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


def profile_csv(path, max_rows=100_000):
    """Per-column summary: filled/empty counts, distinct values, numeric min/max/mean, top values."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        columns = defaultdict(list)
        rows = 0
        for row in reader:
            rows += 1
            if rows > max_rows:
                break
            for key, value in row.items():
                columns[key].append((value or "").strip())
    report = {"rows": rows, "columns": {}}
    for name, values in columns.items():
        filled = [v for v in values if v]
        info = {"filled": len(filled), "empty": len(values) - len(filled), "distinct": len(set(filled))}
        numbers = []
        for v in filled:
            try:
                numbers.append(float(v.replace(",", "").lstrip("$€£")))
            except ValueError:
                break
        else:
            if numbers:
                info.update(min=min(numbers), max=max(numbers), mean=round(sum(numbers) / len(numbers), 3))
        if "mean" not in info:
            info["top_values"] = Counter(filled).most_common(3)
        report["columns"][name] = info
    return report


def flatten_json(data, prefix=""):
    """Flatten nested JSON into {'a.b[0].c': value} so any structure can be viewed as a table."""
    flat = {}
    if isinstance(data, dict):
        for key, value in data.items():
            flat.update(flatten_json(value, f"{prefix}.{key}" if prefix else str(key)))
    elif isinstance(data, list):
        for i, value in enumerate(data):
            flat.update(flatten_json(value, f"{prefix}[{i}]"))
    else:
        flat[prefix] = data
    return flat


def load_json_flat(path):
    with open(path, encoding="utf-8") as f:
        return flatten_json(json.load(f))


# Matches the common Apache/Nginx "combined" access log format.
LOG_LINE = re.compile(
    r'(?P<ip>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] "(?P<method>\S+) (?P<path>\S+) [^"]*" '
    r'(?P<status>\d{3}) (?P<size>\S+)'
)


def summarise_access_log(path, top=5):
    """Summarise a web server access log: totals, busiest IPs, popular paths, status codes."""
    ips, paths, statuses, total, bad = Counter(), Counter(), Counter(), 0, 0
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = LOG_LINE.match(line)
            if not m:
                bad += 1
                continue
            total += 1
            ips[m["ip"]] += 1
            paths[m["path"]] += 1
            statuses[m["status"]] += 1
    return {
        "requests": total,
        "unparsed_lines": bad,
        "top_ips": ips.most_common(top),
        "top_paths": paths.most_common(top),
        "status_codes": dict(sorted(statuses.items())),
    }


def inventory(folder, find_duplicates=True):
    """List every file in a folder tree with size and type, optionally flagging duplicate content."""
    files, by_hash = [], defaultdict(list)
    for p in sorted(Path(folder).rglob("*")):
        if p.is_file():
            size = p.stat().st_size
            files.append({"path": str(p), "extension": p.suffix.lower() or "(none)", "bytes": size})
            if find_duplicates and size:
                by_hash[(size, hashlib.sha256(p.read_bytes()).hexdigest())].append(str(p))
    by_type = Counter(f["extension"] for f in files)
    return {
        "files": files,
        "total_files": len(files),
        "total_bytes": sum(f["bytes"] for f in files),
        "by_extension": dict(by_type.most_common()),
        "duplicates": [group for group in by_hash.values() if len(group) > 1],
    }
