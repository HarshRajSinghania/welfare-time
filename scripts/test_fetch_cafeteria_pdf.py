import os
import sys
import tempfile
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fetch_cafeteria_pdf as fetcher


class FakeResponse:
    def __init__(self, status_code=200, text="", content=b"", headers=None):
        self.status_code = status_code
        self.text = text
        self.content = content
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise fetcher.requests.HTTPError(f"{self.status_code} error")


def run_main(argv):
    old = sys.argv
    sys.argv = argv
    try:
        fetcher.main()
    finally:
        sys.argv = old


def test_requests_use_timeout_and_reject_error_pages():
    html = '<a href="menu.pdf">menu</a>'
    calls = []

    def fake_get(url, timeout=None):
        calls.append(("get", url, timeout))
        if url.endswith(".pdf"):
            return FakeResponse(status_code=404, content=b"<html>missing</html>")
        return FakeResponse(text=html)

    def fake_head(url, timeout=None):
        calls.append(("head", url, timeout))
        return FakeResponse(headers={"Last-Modified": "Wed, 01 Oct 2026 00:00:00 GMT"})

    fetcher.requests.get = fake_get
    fetcher.requests.head = fake_head

    with tempfile.TemporaryDirectory() as output:
        try:
            run_main(["fetch_cafeteria_pdf.py", "-u", "https://example.test/campus/", "-o", output])
            raise AssertionError("expected HTTPError for the 404 PDF")
        except fetcher.requests.HTTPError:
            pass
        assert not os.path.exists(os.path.join(output, "temp.pdf"))

    assert calls == [
        ("get", "https://example.test/campus/", fetcher.REQUEST_TIMEOUT),
        ("head", "https://example.test/campus/menu.pdf", fetcher.REQUEST_TIMEOUT),
        ("get", "https://example.test/campus/menu.pdf", fetcher.REQUEST_TIMEOUT),
    ]


def test_successful_pdf_is_saved():
    html = '<a href="https://files.test/2026_10.pdf">menu</a>'
    page = MagicMock()
    page.extract_text.return_value = "10月のメニュー"
    pdf = MagicMock()
    pdf.pages = [page]
    pdf.__enter__.return_value = pdf
    pdf.__exit__.return_value = False
    fetcher.pdfplumber.open = MagicMock(return_value=pdf)

    def fake_get(url, timeout=None):
        assert timeout == fetcher.REQUEST_TIMEOUT
        if url.endswith(".pdf"):
            return FakeResponse(content=b"%PDF-1.4")
        return FakeResponse(text=html)

    def fake_head(url, timeout=None):
        assert timeout == fetcher.REQUEST_TIMEOUT
        return FakeResponse(headers={"Last-Modified": "Wed, 01 Oct 2026 00:00:00 GMT", "ETag": "abc"})

    fetcher.requests.get = fake_get
    fetcher.requests.head = fake_head

    with tempfile.TemporaryDirectory() as output:
        run_main(["fetch_cafeteria_pdf.py", "-u", "https://example.test/", "-o", output])
        saved = os.path.join(output, f"{fetcher.datetime.now(fetcher.JST).year}_10.pdf")
        assert os.path.exists(saved)
        assert not os.path.exists(os.path.join(output, "temp.pdf"))


if __name__ == "__main__":
    test_requests_use_timeout_and_reject_error_pages()
    test_successful_pdf_is_saved()
    print("ok")
