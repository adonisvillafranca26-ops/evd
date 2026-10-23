"""StudyHive website logic, written in Python and run in the browser by PyScript.

Four features live here:
  1. Print cost estimator
  2. Study planner (saved in the visitor's own browser)
  3. Business "what-if" calculator
  4. Survey result charts

Every price and cost below is a planning assumption, not a final price list.
Edit the constants at the top of each section to match your real numbers.
"""
import json
from datetime import date
from html import escape

from pyscript import document, when, window


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def q(selector):
    """Shortcut for document.querySelector."""
    return document.querySelector(selector)


def peso(amount, decimals=0):
    sign = "-" if amount < 0 else ""
    return f"{sign}₱{abs(amount):,.{decimals}f}"


def to_int(value, default=0):
    try:
        return max(int(float(value)), 0)
    except (TypeError, ValueError):
        return default


def to_float(value, default=0.0):
    try:
        return max(float(value), 0.0)
    except (TypeError, ValueError):
        return default


# --------------------------------------------------------------------------
# 1. Print cost estimator
# --------------------------------------------------------------------------
# Price per printed page in pesos (placeholders, change to your real rates).
PRICES = {
    "bw": {"short": 2.0, "a4": 2.0, "legal": 3.0},
    "color": {"short": 8.0, "a4": 8.0, "legal": 10.0},
}
DUPLEX_DISCOUNT = 0.10      # 10% off for double-sided printing
BULK_PAGES = 100            # total pages that unlock the bulk discount
BULK_DISCOUNT = 0.10        # 10% off for big jobs
MINIMUM_CHARGE = 5.0        # smallest amount charged for any job

COLOR_NAMES = {"bw": "black & white", "color": "full color"}
SIZE_NAMES = {"short": "short (8.5 x 11 in)", "a4": "A4", "legal": "legal (8.5 x 13 in)"}


def estimate(pages, copies, color, size, duplex):
    """Return a dict describing the price of a print job."""
    rate = PRICES[color][size]
    total_pages = pages * copies
    subtotal = total_pages * rate
    total = subtotal
    notes = []

    if duplex and subtotal > 0:
        saved = subtotal * DUPLEX_DISCOUNT
        total -= saved
        notes.append(f"Double-sided discount: -{peso(saved, 2)}")

    if total_pages >= BULK_PAGES:
        saved = subtotal * BULK_DISCOUNT
        total -= saved
        notes.append(f"Bulk discount ({BULK_PAGES}+ pages): -{peso(saved, 2)}")

    if 0 < total < MINIMUM_CHARGE:
        total = MINIMUM_CHARGE
        notes.append(f"Minimum charge of {peso(MINIMUM_CHARGE, 2)} applied")

    return {
        "rate": rate,
        "total_pages": total_pages,
        "subtotal": subtotal,
        "total": total,
        "notes": notes,
    }


def budget_hint(total):
    # Survey: half of students would spend P31-P50 per transaction, a third P10-P30.
    if total <= 0:
        return "Enter the number of pages to see your price."
    if total <= 30:
        return "That fits the ₱10–₱30 range many students told us they spend."
    if total <= 50:
        return "That fits the ₱31–₱50 range most students told us they spend."
    return "That is above the usual per-visit budget. Ask about a student bundle."


def refresh_estimate():
    pages = to_int(q("#est-pages").value)
    copies = max(to_int(q("#est-copies").value, 1), 1)
    color = q("#est-color").value
    size = q("#est-size").value
    duplex = bool(q("#est-duplex").checked)

    result = estimate(pages, copies, color, size, duplex)
    notes = "".join(f"<li>{escape(n)}</li>" for n in result["notes"])
    detail = (
        f"{result['total_pages']} page(s) × {peso(result['rate'], 2)} "
        f"({COLOR_NAMES[color]}, {SIZE_NAMES[size]})"
    )

    q("#est-result").innerHTML = (
        f'<p class="big">{peso(result["total"], 2)}</p>'
        f"<p>{escape(detail)}</p>"
        f"<ul>{notes}</ul>"
        f'<p class="hint">{escape(budget_hint(result["total"]))}</p>'
    )
@when("input", "#estimator")
def on_estimate_input(event):
    refresh_estimate()

# --------------------------------------------------------------------------
# 2. Study planner
# --------------------------------------------------------------------------
STORAGE_KEY = "studyhive.tasks"


def load_tasks():
    try:
        raw = window.localStorage.getItem(STORAGE_KEY)
        return json.loads(raw) if raw else []
    except Exception:
        return []


def save_tasks():
    try:
        window.localStorage.setItem(STORAGE_KEY, json.dumps(tasks))
    except Exception:
        pass  # storage may be blocked (private mode); the planner still works


tasks = load_tasks()


def urgency(days_left):
    """Return (css class, label) for a task."""
    if days_left < 0:
        late = -days_left
        return "overdue", f"Overdue by {late} day{'s' if late != 1 else ''}"
    if days_left == 0:
        return "urgent", "Due today"
    if days_left <= 2:
        return "urgent", f"Due in {days_left} day{'s' if days_left != 1 else ''}"
    if days_left <= 7:
        return "", f"{days_left} days left"
    return "", f"{days_left} days left"


def render_tasks():
    box = q("#task-list")
    summary = q("#task-summary")

    if not tasks:
        box.innerHTML = '<li class="hint">No tasks yet. Add your first one using the form.</li>'
        summary.textContent = ""
        return

    today = date.today()
    ordered = sorted(tasks, key=lambda t: (t["due"], t["id"]))
    rows = []
    for t in ordered:
        due = date.fromisoformat(t["due"])
        days_left = (due - today).days
        css, label = urgency(days_left)

        pace = ""
        if days_left >= 0 and t["hours"] > 0:
            per_day = t["hours"] / max(days_left, 1)
            pace = f" · about {per_day:.1f} h per day"

        subject = f"{escape(t['subject'])} · " if t["subject"] else ""
        rows.append(
            f'<li class="task {css}">'
            f"<div><strong>{escape(t['name'])}</strong> "
            f'<span class="badge">{escape(label)}</span></div>'
            f'<button class="remove" type="button" data-id="{t["id"]}" '
            f'aria-label="Remove {escape(t["name"])}">Done</button>'
            f'<div class="meta">{subject}Due {due.strftime("%b %d, %Y")} · '
            f'{t["hours"]:g} h of work{pace}</div>'
            f"</li>"
        )

    box.innerHTML = "".join(rows)
    total_hours = sum(t["hours"] for t in tasks)
    count = len(tasks)
    summary.textContent = (
        f"{count} task{'s' if count != 1 else ''}, {total_hours:g} hours of work planned."
    )


@when("submit", "#task-form")
def add_task(event):
    event.preventDefault()
    name = q("#task-name").value.strip()
    subject = q("#task-subject").value.strip()
    due = q("#task-due").value
    hours = to_float(q("#task-hours").value, 1.0)

    if not name or not due:
        q("#task-error").textContent = "Please enter a task name and a due date."
        return
    q("#task-error").textContent = ""

    next_id = max((t["id"] for t in tasks), default=0) + 1
    tasks.append(
        {"id": next_id, "name": name, "subject": subject, "due": due, "hours": hours}
    )
    save_tasks()
    render_tasks()
    q("#task-form").reset()
    q("#task-name").focus()


@when("click", "#task-list")
def remove_task(event):
    button = event.target.closest("button[data-id]")
    if button is None:
        return
    task_id = int(button.getAttribute("data-id"))
    tasks[:] = [t for t in tasks if t["id"] != task_id]
    save_tasks()
    render_tasks()


# --------------------------------------------------------------------------
# 3. Business what-if calculator
# --------------------------------------------------------------------------
STARTUP_CAPITAL = 40_000    # from the feasibility study
COGS_RATE = 0.55            # cost of goods sold as a share of sales
FIXED_COSTS = 3_500         # internet 500 + maintenance 500 + staff 2,000 + misc 500


def refresh_whatif():
    reach = to_int(q("#wi-reach").value)
    conversion = to_int(q("#wi-conv").value)
    per_month = to_int(q("#wi-txn").value)
    value = to_int(q("#wi-value").value)

    q("#wi-reach-out").textContent = f"{reach} students"
    q("#wi-conv-out").textContent = f"{conversion}%"
    q("#wi-txn-out").textContent = f"{per_month} per customer"
    q("#wi-value-out").textContent = peso(value)

    customers = round(reach * conversion / 100)
    sales = customers * per_month * value
    profit = sales - sales * COGS_RATE - FIXED_COSTS

    if profit > 0:
        months = f"{STARTUP_CAPITAL / profit:.1f} months"
        bad = ""
    else:
        months = "Not profitable"
        bad = " bad"

    profit_bad = " bad" if profit <= 0 else ""
    q("#wi-result").innerHTML = (
        f'<div class="stat"><b>{customers}</b><span>Active customers per month</span></div>'
        f'<div class="stat"><b>{peso(sales)}</b><span>Monthly sales</span></div>'
        f'<div class="stat{profit_bad}"><b>{peso(profit)}</b><span>Net monthly profit</span></div>'
        f'<div class="stat{bad}"><b>{months}</b><span>Break-even on {peso(STARTUP_CAPITAL)}</span></div>'
    )
@when("input", "#whatif")
def on_whatif_input(event):
    refresh_whatif()

# --------------------------------------------------------------------------
# 4. Survey charts (30 respondents)
# --------------------------------------------------------------------------
RESPONDENTS = 30

INTEREST = [
    ("Affordable printing/photocopying", 22),
    ("Reviewers and study materials", 21),
    ("Digital study resources", 10),
    ("School supplies", 8),
    ("Planners and productivity tools", 7),
    ("Study packages/bundles", 5),
]

FEATURES = [
    ("Affordable prices", 21),
    ("Fast service", 18),
    ("Customized study materials", 17),
    ("Student discounts", 12),
    ("Study bundles/packages", 5),
]

SPEND = [
    ("₱10–₱30", 10),
    ("₱31–₱50", 15),
    ("₱51–₱100", 4),
    ("₱101–₱150", 1),
]


def bars(data):
    rows = []
    for label, count in data:
        pct = round(count / RESPONDENTS * 100)
        rows.append(
            '<div class="bar-row">'
            f'<span class="bar-label">{escape(label)}</span>'
            f'<div class="bar-track"><div class="bar-fill" style="width: {pct}%"></div></div>'
            f'<span class="bar-value">{count} ({pct}%)</span>'
            "</div>"
        )
    return "".join(rows)


def draw_charts():
    q("#chart-interest").innerHTML = bars(INTEREST)
    q("#chart-features").innerHTML = bars(FEATURES)
    q("#chart-spend").innerHTML = bars(SPEND)


# --------------------------------------------------------------------------
# Start-up: fill every dynamic section once the page has loaded
# --------------------------------------------------------------------------
refresh_estimate()
refresh_whatif()
render_tasks()
draw_charts()
