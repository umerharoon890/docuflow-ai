from datetime import datetime


def validate_invoice(invoice: dict) -> dict:
    checks = []

    checks.append(check_required_fields(invoice))
    checks.append(check_total(invoice))
    checks.append(check_dates(invoice))
    checks.append(check_line_items(invoice))

    passed = sum(check["passed"] for check in checks)
    total_checks = len(checks)

    score = passed / total_checks if total_checks else 0

    return {
        "checks": checks,
        "passed": passed,
        "total_checks": total_checks,
        "score": round(score, 2),
        "status": "PASS" if passed == total_checks else "REVIEW",
    }


def check_required_fields(invoice: dict) -> dict:
    required = [
        "vendor",
        "invoice_number",
        "invoice_date",
        "total",
    ]

    missing = [
        field
        for field in required
        if invoice.get(field) in (None, "")
    ]

    return {
        "name": "Required fields",
        "passed": len(missing) == 0,
        "details": (
            "All required fields found."
            if not missing
            else f"Missing: {', '.join(missing)}"
        ),
    }


def check_total(invoice: dict) -> dict:
    subtotal = invoice.get("subtotal")
    tax = invoice.get("tax")
    total = invoice.get("total")

    if subtotal is None or tax is None or total is None:
        return {
            "name": "Total calculation",
            "passed": False,
            "details": "Subtotal, tax, or total is missing.",
        }

    expected = round(float(subtotal) + float(tax), 2)
    actual = round(float(total), 2)

    passed = abs(expected - actual) <= 0.02

    return {
        "name": "Total calculation",
        "passed": passed,
        "details": (
            f"{subtotal} + {tax} = {total}"
            if passed
            else f"Expected {expected}, extracted {actual}"
        ),
    }


def parse_date(value: str) -> datetime:
    formats = [
        "%Y-%m-%d",
        "%d %b %Y",
        "%d %B %Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
    ]

    for date_format in formats:
        try:
            return datetime.strptime(value, date_format)
        except ValueError:
            continue

    raise ValueError(f"Unsupported date format: {value}")


def check_dates(invoice: dict) -> dict:
    invoice_date = invoice.get("invoice_date")
    due_date = invoice.get("due_date")

    if not invoice_date or not due_date:
        return {
            "name": "Date validation",
            "passed": False,
            "details": "Invoice date or due date is missing.",
        }

    try:
        invoice_dt = parse_date(invoice_date)
        due_dt = parse_date(due_date)

        passed = due_dt >= invoice_dt

        return {
            "name": "Date validation",
            "passed": passed,
            "details": (
                "Due date is after invoice date."
                if passed
                else "Due date occurs before invoice date."
            ),
        }

    except ValueError as exc:
        return {
            "name": "Date validation",
            "passed": False,
            "details": str(exc),
        }


def check_line_items(invoice: dict) -> dict:
    line_items = invoice.get("line_items") or []

    if not line_items:
        return {
            "name": "Line item validation",
            "passed": False,
            "details": "No line items were extracted.",
        }

    errors = []

    for index, item in enumerate(line_items, start=1):
        quantity = item.get("quantity")
        unit_price = item.get("unit_price")
        amount = item.get("amount")

        if quantity is None or unit_price is None or amount is None:
            errors.append(f"Item {index} has missing values.")
            continue

        expected = round(float(quantity) * float(unit_price), 2)
        actual = round(float(amount), 2)

        if abs(expected - actual) > 0.02:
            errors.append(
                f"Item {index}: expected {expected}, found {actual}."
            )

    return {
        "name": "Line item validation",
        "passed": len(errors) == 0,
        "details": (
            "All line item calculations are valid."
            if not errors
            else " ".join(errors)
        ),
    }