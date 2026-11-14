# CampusFind – Campus Lost & Found Management System

A full-stack Django web application where students and staff report lost items, report found items, search for belongings, submit ownership claims and manage recovery. Built for **INT253: Web Development in Python Using Django**.

## Problem statement
Lost belongings on a campus are usually handled through scattered WhatsApp groups, notice boards and security desks. Reports get buried, cannot be searched, and nobody can safely verify who the real owner is. CampusFind replaces this with one searchable, verified, login-protected system.

## Objectives
- Provide one central place to report lost and found items.
- Make reports searchable and filterable by name, description, category, location and status.
- Verify ownership through hidden "private details" and a claim workflow.
- Let owners and admins review claims (Pending / Approved / Rejected).
- Demonstrate every unit (I to VI) of the INT253 syllabus in real source code.

## Features
| Area | What it does |
|---|---|
| Authentication | Register (with password validation), login, logout, sessions, login-protected pages |
| Home | Hero, search bar, report buttons, recent items, how-it-works, live statistics |
| Report lost / found | ModelForm with optional image upload; found items also take hidden verification details |
| Listings | Separate Lost and Found pages with cards, pagination and empty states |
| Search & filter | Name/description search plus category, location and status filters (ORM `Q` objects) |
| Possible matches | Item detail suggests up to three active opposite-type reports from the same category |
| Claims | Logged-in users claim found items; finder approves/rejects; approving auto-rejects other pending claims |
| Saved items | Bookmark reports from their detail page and manage saved items on the dashboard |
| Dashboard | Stats, own reports (edit/delete), saved items, own claims, incoming claims to review |
| Admin | All models registered with search, filters, list display, bulk actions, inline claims |
| Security | CSRF, ownership checks (403), server-side validation, safe image upload, private details never shown publicly |

## Technologies
Python 3.12, Django 5.x, SQLite, HTML5, CSS3, Bootstrap 5 (CDN), JavaScript, Django Template Language. Pillow is also required because Django's `ImageField` depends on it.

## Installation
```bash
cd CampusFind

python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS / Linux

pip install -r requirements.txt
python manage.py migrate            # creates tables + default categories
python manage.py createsuperuser    # you choose the admin password
python manage.py seed_demo --password "ChooseADemoPassword#1"   # optional sample data + match example
python manage.py runserver
```
Open http://127.0.0.1:8000/ (admin: http://127.0.0.1:8000/admin/).
Bootstrap, icons and the Manrope font load from CDNs, so an internet connection is needed for the full look.
Run the app tests with `python manage.py test items`.

## Demo walkthrough
1. Register two accounts, or create demo accounts and sample reports with `python manage.py seed_demo --password "ChooseADemoPassword#1"`.
2. Log in as `demo_asha` or `demo_ravi` using the password passed to the seed command.
3. Open a lost or found report. Its detail page suggests up to three active reports of the opposite type in the same category.
4. On any report detail page, select **Save for later**. Open the dashboard to see the saved report; use the bookmark button to remove it.
5. To demonstrate claiming, log in with the other demo account, open an active found report, and submit an ownership claim. The account that reported it can review the claim on the report detail page or dashboard.

The seed command adds a lost backpack and an active found backpack in the same category to demonstrate possible matches. It does not reset or delete existing data.

## Recent feature details
- **Possible matches** use the existing category and item type: only active reports of the opposite type in the same category are suggested, with a maximum of three results. This is a helpful lead, not an automatic ownership decision.
- **Saved items** are private to the signed-in user and shown on that user's dashboard. Saving and removing requires a POST request and a CSRF token; a database constraint prevents duplicate saves.
- Apply schema changes before using the features with `python manage.py migrate`. The saved-items table is created by `items/migrations/0003_saveditem.py`.

## Project structure
```
CampusFind/
  manage.py, requirements.txt, README.md, PROJECT_REPORT.md
  campusfind/        settings.py, urls.py, wsgi.py, asgi.py
  items/             models.py, views.py, forms.py, urls.py, admin.py, tests.py,
                     context_processors.py, migrations/, management/commands/seed_demo.py
  templates/         base.html + all pages + partials (_item_card, _filters, _field, _results)
  static/            css/style.css, js/script.js
  media/             uploaded images
```

## Database models
- **Category**: name (unique), icon.
- **Item**: user (FK User), title, category (FK), description, item_type (LOST/FOUND), location, date_reported, image, contact, private_details, status (ACTIVE/CLAIMED/RETURNED), created_at.
- **Claim**: item (FK), claimant (FK User), contact, verification_answer, explanation, status (PENDING/APPROVED/REJECTED), created_at. A UniqueConstraint allows one claim per user per item.
- **SavedItem**: user (FK User), item (FK Item), created_at. A UniqueConstraint prevents the same user from saving an item twice.

## Django concepts implemented
| Unit | Concept | Where |
|---|---|---|
| I | Project, app, settings.py, INSTALLED_APPS, manage.py commands | `campusfind/settings.py`, `items/` |
| II | Function-based views, URL routing, dynamic parameters, GET/POST, render, HttpResponse, redirects, 404/403/400 | `items/views.py`, `items/urls.py` |
| III | Template inheritance, variables, for/if/empty, include, filters | `templates/` |
| IV | ModelForms/Forms, validation (`clean_<field>`), CSRF, POST-Redirect-GET | `items/forms.py`, `report_item`, `claim_item` |
| V | Models, migrations, ORM CRUD, ForeignKeys, Q queries, Admin, permissions (`is_staff`), SQLite | `items/models.py`, `items/admin.py` |
| VI | Cookie `last_viewed_item` (set in `item_detail`, read in `home`); sessions (`visit_count`, `recent_searches`); registration, login/logout; `@login_required` | `items/views.py`, `settings.py` |

## Future scope
Email/SMS notifications, image matching between lost and found items, QR-coded tags, map of locations, in-app chat, PostgreSQL deployment.

## Conclusion
CampusFind turns an informal, error-prone process into a structured, searchable and verified workflow while demonstrating the complete INT253 Django syllabus.
