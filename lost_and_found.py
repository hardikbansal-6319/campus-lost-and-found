"""A menu-based lost and found register for a campus help desk."""

import csv
import os
from datetime import datetime, date


# Keep the CSV beside this program, even when run from another folder.
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "lost_found_records.csv")
FIELDS = ["id", "item_name", "category", "location", "date",
          "description", "status"]
CATEGORIES = ["ID Card", "Wallet", "Mobile Phone", "Book", "Bag",
              "Keys", "Earphones", "Water Bottle", "Other"]
STATUSES = ["Lost", "Found", "Returned"]
DATE_FORMAT = "%d-%m-%Y"


def load_records():
    """Read the CSV. Return None if existing data cannot be loaded safely."""
    records = []
    used_ids = set()
    try:
        with open(DATA_FILE, "r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file, strict=True)
            if reader.fieldnames != FIELDS:
                raise ValueError("The CSV column headings are incorrect.")

            for record in reader:
                if None in record or None in record.values():
                    raise ValueError("A row has missing or extra columns.")
                for field in FIELDS:
                    record[field] = record[field].strip()
                    if not record[field]:
                        raise ValueError("A row contains an empty field.")

                record["id"] = int(record["id"])
                if record["id"] < 1 or record["id"] in used_ids:
                    raise ValueError("Record IDs must be positive and unique.")
                if record["status"] not in STATUSES:
                    raise ValueError("A record has an unknown status.")
                if record["category"] not in CATEGORIES:
                    raise ValueError("A record has an unknown category.")
                saved_date = datetime.strptime(record["date"], DATE_FORMAT).date()
                if (saved_date > date.today()
                        or saved_date.strftime(DATE_FORMAT) != record["date"]):
                    raise ValueError("A record has an invalid date.")
                if (len(record["item_name"]) > 40
                        or len(record["location"]) > 40
                        or len(record["description"]) > 100):
                    raise ValueError("A record exceeds the text length limits.")
                used_ids.add(record["id"])
                records.append(record)

    except FileNotFoundError:
        return []
    except (OSError, ValueError, csv.Error, UnicodeError) as error:
        print("Could not load the records:", error)
        print("Please check the CSV file. Existing data has not been changed.")
        return None
    return records


def save_records(records):
    """Write a temporary file first so a failed write preserves the old CSV."""
    temporary_file = DATA_FILE + ".tmp"
    try:
        with open(temporary_file, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(records)
        os.replace(temporary_file, DATA_FILE)
        return True
    except (OSError, csv.Error, UnicodeError) as error:
        print("Could not save the records:", error)
        print("The change was not saved. Please check the folder permissions.")
        return False


def generate_id(records):
    highest_id = 0
    for record in records:
        if record["id"] > highest_id:
            highest_id = record["id"]
    return highest_id + 1


def get_text(prompt, maximum_length):
    while True:
        text = input(prompt).strip()
        if not text:
            print("Input cannot be empty. Please try again.")
        elif len(text) > maximum_length:
            print("Please use at most", maximum_length, "characters.")
        else:
            return text


def get_category():
    print("\nCategories:")
    for number, category in enumerate(CATEGORIES, start=1):
        print(str(number) + ". " + category)
    while True:
        try:
            choice = int(input("Choose a category (1-9): "))
            if 1 <= choice <= len(CATEGORIES):
                return CATEGORIES[choice - 1]
            print("Please enter a number between 1 and 9.")
        except ValueError:
            print("Please enter a whole number.")


def get_date():
    while True:
        text = input("Date DD-MM-YYYY (Enter = today): ").strip()
        if not text:
            return date.today().strftime(DATE_FORMAT)
        try:
            item_date = datetime.strptime(text, DATE_FORMAT).date()
            if item_date.strftime(DATE_FORMAT) != text:
                raise ValueError
            if item_date > date.today():
                print("The date cannot be in the future.")
            else:
                return text
        except ValueError:
            print("Invalid date. Use DD-MM-YYYY (for example 25-09-2026).")


def show_record(record):
    print("-" * 50)
    print("Record ID:", record["id"])
    print("Item:", record["item_name"])
    print("Category:", record["category"])
    print("Location:", record["location"])
    print("Date:", record["date"])
    print("Description:", record["description"])
    print("Status:", record["status"])


def find_matches(new_record, records):
    if new_record["status"] == "Returned":
        return []
    if new_record["status"] == "Lost":
        opposite_status = "Found"
    else:
        opposite_status = "Lost"

    matches = []
    new_words = set(new_record["item_name"].lower().split())
    for record in records:
        if (record["status"] == opposite_status
                and record["category"] == new_record["category"]):
            saved_words = set(record["item_name"].lower().split())
            # Set intersection gives the words that occur in both names.
            if new_words & saved_words:
                matches.append(record)
    return matches


def report_item(records, status):
    print("\nREPORT " + status.upper() + " ITEM")
    record = {
        "id": generate_id(records),
        "item_name": get_text("Item name: ", 40),
        "category": get_category(),
        "location": get_text("Location: ", 40),
        "date": get_date(),
        "description": get_text("Description: ", 100),
        "status": status
    }

    records.append(record)
    if not save_records(records):
        records.pop()  # Undo the addition if it could not be saved.
        return
    print("Record saved successfully. Your record ID is", record["id"])
    matches = find_matches(record, records)
    if matches:
        print("\nPossible matching records found:")
        for match in matches:
            show_record(match)
        print("These are suggestions. Verify the item details before returning it.")
    else:
        print("No matching records found yet.")


def search_score(result):
    # Each search result is a tuple containing (score, record).
    return result[0]


def search_items(records):
    keyword = input("\nEnter search keyword(s): ").strip()
    if not keyword:
        print("Please enter at least one keyword.")
        return

    results = rank_records(records, keyword)
    if not results:
        print("No records found for '" + keyword + "'.")
        return
    print(len(results), "matching record(s) found:")
    for score, record in results:
        show_record(record)
        print("Match score:", score)


def rank_records(records, keyword):
    """Shared search logic for the terminal and website."""

    # Count repeated search words only once.
    words = []
    for word in keyword.lower().split():
        if word not in words:
            words.append(word)

    results = []
    for record in records:
        text = (record["item_name"] + " " + record["category"] + " "
                + record["location"] + " " + record["description"] + " "
                + record["status"]).lower()
        score = 0
        for word in words:
            if word in text:
                score += 1
        if score > 0:
            results.append((score, record))

    results.sort(key=search_score, reverse=True)
    return results


def view_records(records):
    if not records:
        print("\nNo records available yet.")
        return
    print("\nALL RECORDS")
    print(f"{'ID':<5} {'Item':<22} {'Category':<13} {'Location':<22} "
          f"{'Date':<10} {'Status':<8}")
    print("-" * 85)
    for record in records:
        item = record["item_name"]
        location = record["location"]
        if len(item) > 22:
            item = item[:19] + "..."
        if len(location) > 22:
            location = location[:19] + "..."
        print(f"{record['id']:<5} {item:<22} {record['category']:<13} "
              f"{location:<22} {record['date']:<10} {record['status']:<8}")
    print("Total records:", len(records))
    print("Search an item to see its full details.")


def update_status(records):
    try:
        record_id = int(input("\nEnter record ID: "))
    except ValueError:
        print("Invalid ID. Please enter a number.")
        return

    selected_record = None
    for record in records:
        if record["id"] == record_id:
            selected_record = record
            break
    if selected_record is None:
        print("No record found with ID", record_id)
        return

    show_record(selected_record)
    print("\n1. Lost\n2. Found\n3. Returned")
    try:
        choice = int(input("Choose the new status (1-3): "))
    except ValueError:
        print("Invalid status choice. Please enter a number from 1 to 3.")
        return
    if choice < 1 or choice > 3:
        print("Invalid status choice. Please enter a number from 1 to 3.")
        return

    new_status = STATUSES[choice - 1]
    old_status = selected_record["status"]
    if new_status == old_status:
        print("The item is already marked as " + new_status + ". No change made.")
        return
    selected_record["status"] = new_status
    if save_records(records):
        print("Status of record", record_id, "updated to " + new_status + ".")
        if new_status == "Returned":
            print("If a separate report describes the same item, update that ID too.")
    else:
        selected_record["status"] = old_status


def show_menu():
    print("\nCAMPUS LOST & FOUND MANAGEMENT SYSTEM")
    print("1. Report Lost Item")
    print("2. Report Found Item")
    print("3. Search Items")
    print("4. View All Records")
    print("5. Update Item Status")
    print("6. Exit")


def main():
    records = load_records()
    if records is None:
        return
    while True:
        show_menu()
        try:
            choice = int(input("Enter your choice (1-6): "))
        except ValueError:
            print("Invalid choice. Please enter a number from 1 to 6.")
            continue
        if choice == 1:
            report_item(records, "Lost")
        elif choice == 2:
            report_item(records, "Found")
        elif choice == 3:
            search_items(records)
        elif choice == 4:
            view_records(records)
        elif choice == 5:
            update_status(records)
        elif choice == 6:
            print("Thank you for using Campus Lost & Found.")
            break
        else:
            print("Invalid choice. Please enter a number from 1 to 6.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nProgram closed. Previously saved records are kept.")
