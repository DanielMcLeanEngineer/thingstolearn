"""Extract text and tables from Word, Excel, PowerPoint, PDF and email files.

docx/xlsx/pptx are zip files full of XML, so the standard library is enough.
PDF needs the optional `pypdf` package (pip install pypdf).
"""
import re
import zipfile
from email import policy
from email.parser import BytesParser
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def _read_zip_xml(path, member):
    try:
        with zipfile.ZipFile(path) as z:
            return ET.fromstring(z.read(member))
    except zipfile.BadZipFile:
        raise ValueError(f"{path} is not a valid Office file")
    except KeyError:
        raise ValueError(f"{path} is missing {member}; is it the right file type?")


def read_docx(path):
    """Paragraphs and tables of a .docx file."""
    root = _read_zip_xml(path, "word/document.xml")
    para = lambda p: "".join(t.text or "" for t in p.iter(f"{W}t"))
    body = root.find(f"{W}body")
    paragraphs = [para(p) for p in body.findall(f"{W}p")]
    tables = [
        [[" ".join(para(p) for p in cell.iter(f"{W}p")).strip() for cell in row.findall(f"{W}tc")]
         for row in tbl.findall(f"{W}tr")]
        for tbl in body.findall(f"{W}tbl")
    ]
    return {"paragraphs": [p for p in paragraphs if p.strip()], "tables": tables}


def read_pptx(path):
    """Text of every slide in a .pptx file, as [{'slide': 1, 'text': '...'}]."""
    try:
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)]
            names.sort(key=lambda n: int(re.search(r"(\d+)\.xml", n).group(1)))
            return [
                {"slide": i, "text": " | ".join(t.text for t in ET.fromstring(z.read(n)).iter(f"{A}t") if t.text)}
                for i, n in enumerate(names, 1)
            ]
    except zipfile.BadZipFile:
        raise ValueError(f"{path} is not a valid .pptx file")


def _col_index(ref):
    """'C7' -> 2 (zero-based column number)."""
    letters = re.match(r"[A-Z]+", ref).group()
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n - 1


def xlsx_sheet_names(path):
    root = _read_zip_xml(path, "xl/workbook.xml")
    return [s.get("name") for s in root.iter(f"{S}sheet")]


def read_xlsx(path, sheet=None):
    """Rows of one worksheet as a list of dicts (first row = headers). Defaults to the first sheet."""
    try:
        z = zipfile.ZipFile(path)
    except zipfile.BadZipFile:
        raise ValueError(f"{path} is not a valid .xlsx file")
    with z:
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
        sheets = {s.get("name"): rels[s.get(f"{R}id")] for s in wb.iter(f"{S}sheet")}
        name = sheet or next(iter(sheets))
        if name not in sheets:
            raise ValueError(f"No sheet named {name!r}. Sheets: {', '.join(sheets)}")
        target = sheets[name].lstrip("/")
        member = target if target.startswith("xl/") else f"xl/{target}"
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(f"{S}si"):
                shared.append("".join(t.text or "" for t in si.iter(f"{S}t")))
        rows = []
        for row in ET.fromstring(z.read(member)).iter(f"{S}row"):
            cells = {}
            for c in row.findall(f"{S}c"):
                kind, v = c.get("t"), c.find(f"{S}v")
                if kind == "inlineStr":
                    value = "".join(t.text or "" for t in c.iter(f"{S}t"))
                elif v is None or v.text is None:
                    continue
                elif kind == "s":
                    value = shared[int(v.text)]
                elif kind in ("str", "b", "e"):
                    value = v.text
                else:
                    value = float(v.text)
                    value = int(value) if value.is_integer() else value
                cells[_col_index(c.get("r"))] = value
            if cells:
                rows.append([cells.get(i, "") for i in range(max(cells) + 1)])
    if not rows:
        return []
    headers = [str(h) or f"column{i + 1}" for i, h in enumerate(rows[0])]
    return [dict(zip(headers, r + [""] * (len(headers) - len(r)))) for r in rows[1:]]


def read_pdf(path):
    """Text of each page of a PDF (needs `pip install pypdf`). Scanned PDFs without a text layer return empty pages."""
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ValueError("PDF support needs the optional pypdf package: pip install pypdf")
    reader = PdfReader(path)
    return [{"page": i, "text": (page.extract_text() or "").strip()} for i, page in enumerate(reader.pages, 1)]


def read_eml(path):
    """Headers, plain-text body and attachment names of an .eml email file."""
    with open(path, "rb") as f:
        msg = BytesParser(policy=policy.default).parse(f)
    body = msg.get_body(preferencelist=("plain", "html"))
    return {
        "from": msg["from"], "to": msg["to"], "cc": msg["cc"], "date": msg["date"], "subject": msg["subject"],
        "body": body.get_content() if body else "",
        "attachments": [a.get_filename() for a in msg.iter_attachments()],
    }
