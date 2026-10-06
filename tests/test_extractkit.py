import json
import tempfile
import unittest
from pathlib import Path

from extractkit import files, text, web
from extractkit.cli import main

HTML = """<html><head><title> Demo  Page </title>
<meta name="description" content="A demo"><script>var x = 'hidden';</script></head>
<body><h1>Welcome</h1><a href="/about">About us</a><img src="/a.png" alt="logo">
<table><tr><th>Name</th><th>Price</th></tr><tr><td>Chair</td><td>$50</td></tr>
<tr><td>Lamp</td><td>$20</td></tr></table><p>Hello world</p></body></html>"""


class TextTests(unittest.TestCase):
    def test_entities(self):
        s = "Mail a.b@x.com or a.b@x.com, see https://x.com/p. Call +61 412 345 678. Paid $1,200.50 on 2026-10-06 #python"
        r = text.extract_entities(s)
        self.assertEqual(r["emails"], ["a.b@x.com"])
        self.assertEqual(r["urls"], ["https://x.com/p"])
        self.assertEqual(r["phones"], ["+61 412 345 678"])
        self.assertEqual(r["money"], ["$1,200.50"])
        self.assertEqual(r["dates"], ["2026-10-06"])
        self.assertEqual(r["hashtags"], ["#python"])

    def test_short_numbers_not_phones(self):
        self.assertEqual(text.extract_entities("order 12345", ["phones"])["phones"], [])


class WebTests(unittest.TestCase):
    def test_parse(self):
        p = web.parse_html(HTML, "https://ex.com/")
        self.assertEqual(p["title"], "Demo Page")
        self.assertEqual(p["meta"]["description"], "A demo")
        self.assertEqual(p["links"], [{"url": "https://ex.com/about", "text": "About us"}])
        self.assertEqual(p["images"][0]["src"], "https://ex.com/a.png")
        self.assertEqual(p["headings"], [{"level": "h1", "text": "Welcome"}])
        self.assertNotIn("hidden", p["text"])
        self.assertEqual(web.tables_to_rows(p["tables"][0]), [{"Name": "Chair", "Price": "$50"}, {"Name": "Lamp", "Price": "$20"}])


class FileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_csv_profile(self):
        f = self.tmp / "d.csv"
        f.write_text("name,price\nA,10\nB,20\nA,\n")
        r = files.profile_csv(f)
        self.assertEqual(r["rows"], 3)
        self.assertEqual(r["columns"]["price"]["mean"], 15.0)
        self.assertEqual(r["columns"]["price"]["empty"], 1)
        self.assertEqual(r["columns"]["name"]["top_values"][0], ("A", 2))

    def test_flatten(self):
        self.assertEqual(files.flatten_json({"a": {"b": [1, {"c": 2}]}}), {"a.b[0]": 1, "a.b[1].c": 2})

    def test_log(self):
        f = self.tmp / "a.log"
        f.write_text('1.1.1.1 - - [06/Oct/2026:10:00:00 +0000] "GET /x HTTP/1.1" 200 12\n'
                     '1.1.1.1 - - [06/Oct/2026:10:00:01 +0000] "GET /y HTTP/1.1" 404 0\ngarbage\n')
        r = files.summarise_access_log(f)
        self.assertEqual((r["requests"], r["unparsed_lines"]), (2, 1))
        self.assertEqual(r["status_codes"], {"200": 1, "404": 1})

    def test_inventory_duplicates(self):
        (self.tmp / "a.txt").write_text("same")
        (self.tmp / "b.txt").write_text("same")
        (self.tmp / "c.md").write_text("different")
        r = files.inventory(self.tmp)
        self.assertEqual(r["total_files"], 3)
        self.assertEqual(len(r["duplicates"]), 1)


class CliTests(unittest.TestCase):
    def test_cli_writes_csv(self):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "p.html").write_text(HTML)
        out = tmp / "t.csv"
        main(["-o", str(out), "--csv", "table", str(tmp / "p.html")])
        self.assertEqual(out.read_text().splitlines()[0], "Name,Price")


if __name__ == "__main__":
    unittest.main()
