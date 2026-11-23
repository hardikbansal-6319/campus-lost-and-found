"""Run the local HTML application with: python3 app.py

Python handles all records, validation, search, matching, and CSV storage.
The HTTP handler connects browser requests to these Python functions.
"""

import json
import errno
import secrets
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from urllib.parse import parse_qs, urlsplit

import lost_and_found as project


ROOT = Path(__file__).resolve().parent
HOST = "127.0.0.1"
PORT = 8765
# A browser must obtain this token from our own site before making changes.
FORM_TOKEN = secrets.token_hex(24)
DATA_LOCK = Lock()
STATIC_FILES = {
    "/": ("web/index.html", "text/html; charset=utf-8"),
    "/style.css": ("web/style.css", "text/css; charset=utf-8"),
    "/app.js": ("web/app.js", "text/javascript; charset=utf-8"),
    "/favicon.svg": ("web/favicon.svg", "image/svg+xml")
}


def validate_report(data):
    """Return cleaned input and field errors without changing any records."""
    clean = {}
    errors = {}
    for field, limit in [("item_name", 40), ("location", 40), ("description", 100)]:
        value = data.get(field, "")
        if not isinstance(value, str):
            value = ""
        value = value.strip()
        clean[field] = value
        if not value:
            errors[field] = "Please fill in this field."
        elif len(value) > limit:
            errors[field] = "Please use at most " + str(limit) + " characters."

    for field, options in [("category", project.CATEGORIES), ("status", ["Lost", "Found"])]:
        clean[field] = data.get(field, "")
        if clean[field] not in options:
            errors[field] = "Please choose a valid " + field + "."

    try:
        # HTML date inputs send YYYY-MM-DD. The CSV keeps DD-MM-YYYY.
        text = data.get("date", "")
        item_date = datetime.strptime(text, "%Y-%m-%d").date()
        if item_date.isoformat() != text or item_date > date.today():
            raise ValueError
        clean["date"] = item_date.strftime(project.DATE_FORMAT)
    except (ValueError, TypeError):
        errors["date"] = "Choose a valid date that is not in the future."
    return clean, errors


def list_records(records, query):
    """Filter the records and rank keyword matches in Python."""
    keyword = query.get("q", [""])[0].strip()
    category = query.get("category", [""])[0]
    status = query.get("status", [""])[0]
    counts = {"Lost": 0, "Found": 0, "Returned": 0}
    filtered = []
    for record in records:
        counts[record["status"]] += 1
        if category and record["category"] != category:
            continue
        if status and record["status"] != status:
            continue
        filtered.append(record)

    results = []
    if keyword:
        for score, record in project.rank_records(filtered, keyword):
            result = record.copy()
            result["score"] = score
            results.append(result)
    else:
        # New reports appear first when no search keywords are entered.
        results = list(reversed(filtered))
    return {"records": results, "counts": counts, "total": len(records)}


def get_record(records, record_id):
    for record in records:
        if record["id"] == record_id:
            return record
    return None


class CampusHandler(BaseHTTPRequestHandler):
    """Small HTTP adapter. Project logic stays in ordinary functions above."""

    def send_json(self, data, status=200):
        content = json.dumps(data).encode("utf-8")
        self.send_content(content, "application/json; charset=utf-8", status)

    def send_content(self, content, content_type, status=200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; "
                         "script-src 'self'; img-src 'self'; frame-ancestors 'none'; "
                         "base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(content)

    def valid_host(self):
        # This app is intended to run on the local computer.
        hostname = self.headers.get("Host", "").split(":")[0]
        if hostname not in ["127.0.0.1", "localhost"]:
            self.send_json({"error": "Please open the app using localhost."}, 403)
            return False
        return True

    def read_records(self):
        records = project.load_records()
        if records is None:
            self.send_json({"error": "The saved records could not be read. "
                            "Check the CSV file before continuing; it has not been changed."}, 500)
        return records

    def do_GET(self):
        if not self.valid_host():
            return
        url = urlsplit(self.path)
        if url.path in STATIC_FILES:
            filename, content_type = STATIC_FILES[url.path]
            self.send_content((ROOT / filename).read_bytes(), content_type)
            return
        if url.path == "/api/config":
            self.send_json({"categories": project.CATEGORIES, "statuses": project.STATUSES,
                            "today": date.today().isoformat(), "token": FORM_TOKEN})
            return
        if url.path == "/api/records":
            records = self.read_records()
            if records is not None:
                self.send_json(list_records(records, parse_qs(url.query)))
            return
        if url.path.startswith("/api/records/"):
            try:
                record_id = int(url.path.removeprefix("/api/records/"))
            except ValueError:
                self.send_json({"error": "This report could not be found."}, 404)
                return
            records = self.read_records()
            if records is None:
                return
            record = get_record(records, record_id)
            if record is not None:
                self.send_json({"record": record, "matches": project.find_matches(record, records)})
                return
        self.send_json({"error": "This page or report could not be found."}, 404)

    def do_POST(self):
        if not self.valid_host():
            return
        if self.headers.get("X-Campus-Token") != FORM_TOKEN:
            self.send_json({"error": "Please refresh the page and try again."}, 403)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > 8192:
                raise ValueError
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                raise ValueError
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError
        except (ValueError, UnicodeError):
            self.send_json({"error": "The submitted form could not be read."}, 400)
            return

        # Complete one read/change/save operation before starting another.
        with DATA_LOCK:
            self.save_form(data)

    def save_form(self, data):
        records = self.read_records()
        if records is None:
            return
        path = urlsplit(self.path).path
        if path == "/api/records":
            record, errors = validate_report(data)
            if errors:
                self.send_json({"error": "Please check the highlighted fields.", "fields": errors}, 400)
                return
            record["id"] = project.generate_id(records)
            records.append(record)
        elif (path.startswith("/api/records/") and path.endswith("/status")
              and len(path.split("/")) == 5):
            try:
                record_id = int(path.split("/")[3])
            except ValueError:
                record_id = -1
            record = get_record(records, record_id)
            if record is None:
                self.send_json({"error": "This report could not be found."}, 404)
                return
            if data.get("status") not in project.STATUSES:
                self.send_json({"error": "Please choose a valid status."}, 400)
                return
            record["status"] = data["status"]
        else:
            self.send_json({"error": "This action could not be found."}, 404)
            return

        if not project.save_records(records):
            self.send_json({"error": "Your change could not be saved. "
                            "Check the folder permissions and try again."}, 500)
            return
        self.send_json({"record": record}, 201 if path == "/api/records" else 200)


def main():
    # Browser requests can run together; DATA_LOCK keeps CSV changes in sequence.
    try:
        server = ThreadingHTTPServer((HOST, PORT), CampusHandler)
    except OSError as error:
        print("Could not start the website:", error)
        if error.errno == errno.EADDRINUSE:
            print("If another copy is running, open http://127.0.0.1:8765")
        return
    print("Campus Lost & Found is running at http://127.0.0.1:8765")
    print("Open that address in your browser. Press Ctrl+C here to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nWebsite stopped. Your saved records are kept.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
