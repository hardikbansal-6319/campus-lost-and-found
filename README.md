# Campus Lost & Found

A working local web application for a campus help desk. HTML and CSS provide the interface. Python validates reports, ranks search results, finds possible matches, and saves records in a CSV file. JavaScript connects the forms to Python and displays the results.

## Start the website

Python **3.9 or newer** is required. No extra packages or internet connection are needed.

From this folder, run:

```sh
python3 app.py
```

Then open **http://127.0.0.1:8765** in your browser. Keep the terminal running while using the website. Press **Ctrl+C** in the terminal to stop it.

- **macOS:** You can also double-click `Start Website.command`.
- **Windows:** Run `py -3 app.py`, or double-click `Start Website.bat`.
- **Linux:** Run `python3 app.py`.

Open the address above rather than opening the HTML file directly: the Python server is needed for saving, searching, and matching.

## Use the terminal version

The terminal interface works without the `web/` files, which are not included in this checkout. From the project folder, run:

```sh
python3 lost_and_found.py
```

On Windows, use `py -3 lost_and_found.py`.

Choose a numbered menu option to report a lost or found item, search items, view all records, or update an item's status using its record ID. Choose **6** to exit. Each successful report or status update is saved immediately to `lost_found_records.csv`, the same file used by the web server. Stop the web server before making changes through the terminal.

- Item names and locations must contain at most **40 characters** each; descriptions must contain at most **100 characters**. These fields cannot be blank.
- Select a category using its number in the displayed list.
- Enter dates as **DD-MM-YYYY**, or press **Enter** to use today's date. Future dates are rejected.
- When an item is returned, choose **Update Item Status**, enter its record ID, and select **Returned**. If both a lost report and a found report exist for that item, update each record separately.

## Features

- Browse a noticeboard of lost, found, and returned items with record totals.
- Report items through HTML forms with category, location, date, and description.
- Search multiple keywords and rank matches by the number of distinct keywords found.
- Filter the noticeboard by category and status.
- See possible matches with the same category, a shared item-name word, and the opposite Lost/Found status.
- View complete item details and change the status to Lost, Found, or Returned.
- Keep records after closing and restarting the app.
- Display useful errors for invalid input and file problems.

## Quick demonstration

1. Choose **I lost something**. Report **Black Wallet**, category **Wallet**, location **Central Library**, today's date, description **Black leather wallet with an ID card inside**.
2. Choose **I found something**. Report **Wallet**, category **Wallet**, location **Cafeteria**, today's date, description **Black wallet found on a table**.
3. Open the saved found report. The lost wallet appears under **Possible matches**.
4. Browse and search **wallet library**. The library record scores 2; the cafeteria record scores 1.
5. Open a report and update it to **Returned**. It remains searchable but is no longer suggested as a lost/found match.
6. Stop and restart `app.py`. The saved records and updated statuses remain available.

If two reports describe the same returned item, update both records after confirming ownership. Suggestions never automatically mark an item returned.

## Project files

| File | Purpose |
|---|---|
| `app.py` | Python web server, request handling, web input validation, and filtering |
| `lost_and_found.py` | Shared CSV storage, IDs, matching, and ranked search; also retains the terminal version |
| `web/index.html` | Page structure and forms |
| `web/style.css` | Desktop and mobile layouts |
| `web/app.js` | Browser navigation, form submission, and displaying Python's results |
| `lost_found_records.csv` | Saved project records |
| `tests/` | Automated checks, isolated from your actual records |

## Verification

```sh
python3 -m unittest discover -s tests -v
```

The tests cover the terminal flow, CSV persistence, search ranking, matching, input errors, web requests, and failed saves. Web request tests call the actual HTTP handler with in-memory request/response streams, so they work even in environments that prohibit opening a network port.

## Use and limitations

This version is a working local help-desk application. It is not publicly hosted and has no student accounts. The operator verifies ownership in person. Run one copy of the app at a time, and do not use the terminal version to modify data while the website is running.

The CSV is stored beside the Python files. Existing records are loaded at request time. A missing CSV is created on the first save. If the CSV is damaged, the app displays an error instead of overwriting it.

Keyword search uses substrings, so `car` also matches `card`. Name matching uses lowercase words separated by spaces; punctuation, spelling mistakes, and synonyms can prevent a suggestion. The date records when an item was lost or found, not the date its status was updated.

The web server uses Python's standard `http.server` module for local use. Public deployment would require a production server, authentication, and storage designed for multiple users. Reference: https://docs.python.org/3/library/http.server.html

## Submission documents

The existing Word report describes the original terminal interface. Update its interface description, file list, library list, screenshots, and test evidence to match this web version. A PPT is also required by the assignment and has not been created yet.

The search uses a named sorting function (`search_score`), and repeated keywords count only once. Include these details when updating the report.
