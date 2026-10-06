import json
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path

from extractkit import documents, feeds, files, text, web
from extractkit.cli import main

NS_W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
NS_S = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
NS_R = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
NS_A = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'


def make_zip(path, members):
    with zipfile.ZipFile(path, "w") as z:
        for name, data in members.items():
            z.writestr(name, data)


class DocumentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_docx(self):
        f = self.tmp / "a.docx"
        make_zip(f, {"word/document.xml": f"""<w:document {NS_W}><w:body>
            <w:p><w:r><w:t>Hello</w:t></w:r><w:r><w:t> world</w:t></w:r></w:p><w:p/>
            <w:tbl><w:tr><w:tc><w:p><w:r><w:t>A</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>B</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
            </w:body></w:document>"""})
        r = documents.read_docx(f)
        self.assertEqual(r["paragraphs"], ["Hello world"])
        self.assertEqual(r["tables"], [[["A", "B"]]])

    def test_xlsx(self):
        f = self.tmp / "a.xlsx"
        make_zip(f, {
            "xl/workbook.xml": f'<workbook {NS_S} {NS_R}><sheets><sheet name="Sales" sheetId="1" r:id="rId1"/></sheets></workbook>',
            "xl/_rels/workbook.xml.rels": '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>',
            "xl/sharedStrings.xml": f'<sst {NS_S}><si><t>Item</t></si><si><t>Price</t></si><si><t>Chair</t></si></sst>',
            "xl/worksheets/sheet1.xml": f'''<worksheet {NS_S}><sheetData>
                <row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row>
                <row r="2"><c r="A2" t="s"><v>2</v></c><c r="B2"><v>50</v></c></row>
                <row r="3"><c r="B3"><v>7.5</v></c></row></sheetData></worksheet>''',
        })
        self.assertEqual(documents.xlsx_sheet_names(f), ["Sales"])
        self.assertEqual(documents.read_xlsx(f), [{"Item": "Chair", "Price": 50}, {"Item": "", "Price": 7.5}])
        with self.assertRaises(ValueError):
            documents.read_xlsx(f, "Nope")

    def test_pptx(self):
        f = self.tmp / "a.pptx"
        slide = lambda t: f"<p:sld xmlns:p='x' {NS_A}><a:t>{t}</a:t></p:sld>"
        make_zip(f, {"ppt/slides/slide10.xml": slide("Ten"), "ppt/slides/slide2.xml": slide("Two"), "ppt/slides/slide1.xml": slide("One")})
        self.assertEqual([s["text"] for s in documents.read_pptx(f)], ["One", "Two", "Ten"])

    def test_bad_office_file(self):
        f = self.tmp / "bad.docx"
        f.write_text("not a zip")
        with self.assertRaises(ValueError):
            documents.read_docx(f)

    def test_eml(self):
        f = self.tmp / "m.eml"
        f.write_text("From: a@x.com\nTo: b@y.com\nSubject: Hi\nDate: Tue, 06 Oct 2026 10:00:00 +0000\n\nBody text\n")
        r = documents.read_eml(f)
        self.assertEqual((r["from"], r["subject"], r["attachments"]), ("a@x.com", "Hi", []))
        self.assertEqual(r["body"].strip(), "Body text")


class FeedTests(unittest.TestCase):
    def test_rss(self):
        xml = "<rss><channel><item><title>T1</title><link>http://a/1</link><pubDate>Mon</pubDate><description>D</description></item></channel></rss>"
        self.assertEqual(feeds.parse_feed(xml), [{"title": "T1", "link": "http://a/1", "published": "Mon", "summary": "D"}])

    def test_atom(self):
        xml = '<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>E</title><link href="http://a/e"/><updated>2026</updated></entry></feed>'
        r = feeds.parse_feed(xml)
        self.assertEqual((r[0]["title"], r[0]["link"], r[0]["published"]), ("E", "http://a/e", "2026"))

    def test_sitemap_and_index(self):
        ns = 'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"'
        r = feeds.parse_sitemap(f"<urlset {ns}><url><loc>http://a/</loc><lastmod>2026-01-01</lastmod></url></urlset>")
        self.assertEqual(r, [{"url": "http://a/", "lastmod": "2026-01-01", "is_index": False}])
        r = feeds.parse_sitemap(f"<sitemapindex {ns}><sitemap><loc>http://a/s.xml</loc></sitemap></sitemapindex>")
        self.assertTrue(r[0]["is_index"])

    def test_invalid_xml(self):
        with self.assertRaises(ValueError):
            feeds.parse_feed("<rss>")


class WebExtraTests(unittest.TestCase):
    def test_jsonld(self):
        html = '<script type="application/ld+json">{"@type": "Product", "name": "Chair"}</script><script type="application/ld+json">{bad</script><script>var x</script>'
        self.assertEqual(web.parse_html(html)["jsonld"], [{"@type": "Product", "name": "Chair"}])

    def test_robots(self):
        rules = "User-agent: *\nDisallow: /private\n"
        self.assertFalse(web.robots_allows("https://x.com/private/a", rules))
        self.assertTrue(web.robots_allows("https://x.com/public", rules))
        self.assertTrue(web.robots_allows("https://x.com/anything", ""))


class TextExtraTests(unittest.TestCase):
    def test_ip_and_uuid(self):
        r = text.extract_entities("from 192.168.1.10 and 999.1.1.1 id 123e4567-e89b-12d3-a456-426614174000")
        self.assertEqual(r["ipv4"], ["192.168.1.10"])
        self.assertEqual(r["uuids"], ["123e4567-e89b-12d3-a456-426614174000"])
        self.assertEqual(r["phones"], [])  # IP addresses are not phone numbers


class FileExtraTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_outline(self):
        f = self.tmp / "m.py"
        f.write_text('class A:\n    """Doc A."""\n    def m(self, x):\n        pass\n\ndef top(a, b):\n    """Top."""\n')
        r = files.outline_python(f)
        self.assertEqual([(x["kind"], x["name"]) for x in r], [("class", "A"), ("method", "A.m"), ("function", "top")])
        self.assertEqual(r[2]["args"], "a, b")
        f.write_text("def (")
        with self.assertRaises(ValueError):
            files.outline_python(f)

    def test_sqlite_schema(self):
        db = self.tmp / "t.db"
        conn = sqlite3.connect(db)
        conn.execute('CREATE TABLE "my table" (id INTEGER PRIMARY KEY, name TEXT NOT NULL)')
        conn.execute('INSERT INTO "my table" (name) VALUES ("x")')
        conn.commit()
        conn.close()
        r = files.sqlite_schema(db)
        self.assertEqual([(x["column"], x["rows"], x["primary_key"], x["not_null"]) for x in r],
                         [("id", 1, True, False), ("name", 1, False, True)])
        with self.assertRaises(ValueError):
            files.sqlite_schema(self.tmp / "missing.db")


class CliExtraTests(unittest.TestCase):
    def test_feed_csv_via_cli(self):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "f.xml").write_text("<rss><channel><item><title>T</title></item></channel></rss>")
        out = tmp / "o.csv"
        main(["--csv", "-o", str(out), "feed", str(tmp / "f.xml")])
        self.assertEqual(out.read_text().splitlines()[0], "title,link,published,summary")

    def test_pdf_without_pypdf_is_clean_error(self):
        try:
            import pypdf  # noqa
            self.skipTest("pypdf installed")
        except ImportError:
            with self.assertRaises(SystemExit):
                main(["pdf", "x.pdf"])


if __name__ == "__main__":
    unittest.main()
