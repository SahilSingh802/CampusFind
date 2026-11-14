# CampusFind – Project Report

## Abstract
CampusFind is a web-based Lost & Found Management System for a university campus, built with Python 3.12, Django 5, SQLite, Bootstrap 5 and JavaScript. Users register, report lost or found items with optional photos, search and filter reports, discover active opposite-type reports in the same category, save reports for later, and submit claims on found items. Finders review claims against private identifying details that are never shown publicly. Administrators manage everything through Django Admin. The project implements all six units of INT253.

## 1. Introduction
Students lose IDs, wallets, phones and books every week. CampusFind gives the campus a single platform to reunite people with their belongings.

## 2. Problem definition
Current handling is informal: chat groups and notice boards. Reports are hard to search, quickly forgotten, have no ownership verification and leave no record of what happened to an item.

## 3. Objectives
1. A central, searchable database of lost and found items.
2. Secure accounts with session-based authentication.
3. A verified claim workflow with Pending / Approved / Rejected states.
4. Privacy of identifying details.
5. Administrative control through Django Admin.
6. A clean, responsive interface usable on phones.

## 4. Existing system
Manual registers at the security desk, notice boards and chat groups. Drawbacks: no search, no verification, no history, low reach, information lost over time.

## 5. Proposed system
A Django web application with role-aware access. Visitors browse; registered users report, claim and manage; owners review claims; staff administer. Private details are visible only to the reporter and admins.

## 6. System requirements
- Software: Python 3.12, Django 5.x, Pillow, a modern browser, SQLite (bundled with Python).
- Hardware: any computer that runs Python (1 GB RAM, 200 MB disk).
- Network: internet access for CDN assets (Bootstrap, icons, font) when viewing pages.

## 7. System architecture
Django MVT (Model, View, Template):
```
Browser <-> urls.py <-> views.py <-> forms.py
                          |
                     models.py (ORM) <-> SQLite
                          |
                     templates/ (DTL) -> HTML + Bootstrap + CSS/JS
```
Middleware provides sessions, CSRF protection and authentication. A context processor supplies the navbar pending-claims badge.

## 8. Database design
| Table | Key fields | Relationships |
|---|---|---|
| Category | id, name (unique), icon | one to many Items |
| Item | id, title, description, item_type, location, date_reported, image, contact, private_details, status, created_at | FK user, FK category |
| Claim | id, contact, verification_answer, explanation, status, created_at | FK item, FK claimant; unique (item, claimant) |
| SavedItem | id, created_at | FK user, FK item; unique (user, item) |
| User (built-in) | username, name, email, password hash, is_staff | one to many Items, Claims and SavedItems |

## 9. Modules
1. Authentication: register, login, logout, sessions.
2. Home: search, recent items, statistics, cookie/session personalisation.
3. Reporting: lost and found forms, edit, delete, status update.
4. Listing and search: lost list, found list, global search, filters, pagination, category-based possible matches.
5. Claims: submit, review (approve/reject), automatic rejection of competing claims.
6. Saved items and dashboard: bookmark reports, view/remove saved items, statistics, own reports and claims, incoming claims.
7. Administration: Django Admin with filters, search and bulk actions.

## 10. Implementation
- **Views:** function-based, using `@login_required` and `@require_POST`; ownership enforced by `_can_manage()` which raises `PermissionDenied`.
- **Forms:** `ItemForm` adapts to lost or found, validates date, title and image type/size; `ClaimForm` requires a meaningful verification answer.
- **Search:** `Q(title__icontains) | Q(description__icontains)` combined with category, location and status filters.
- **Possible matches:** item detail suggests up to three active reports of the opposite type in the same category.
- **Saved items:** authenticated users can bookmark/unbookmark items; a unique database constraint prevents duplicate saves, and saved items appear on the dashboard.
- **Cookies and sessions:** `last_viewed_item` cookie (7 days); sessions store `visit_count` and `recent_searches`.
- **Security:** CSRF tokens on every POST form, POST-only logout, image extension and content-type validation, private details rendered only for owner/staff, contact details only for logged-in users, no hardcoded passwords (secret key read from `DJANGO_SECRET_KEY`).
- **UI:** Bootstrap 5 grid, custom CSS (navy, blue, soft grey light theme), Bootstrap Icons, empty states, responsive navbar, JavaScript for image preview, auto-dismissing messages and confirmations.

## 11. Testing
`python manage.py test items` runs 34 tests; all pass.
| # | Area | Checked |
|---|---|---|
| 1 | Registration | creates user and logs in; weak password and duplicate email rejected |
| 2 | Login/logout | success, wrong password, session cleared |
| 3-4 | Report lost/found | saved correctly; image upload; private details required; future date and non-image rejected |
| 5 | Listing | lost vs found separation; empty state |
| 6 | Search/filters | name, description, category, location, status, type; recent searches in session |
| 7 | Claims | submit; cannot claim own item, twice, or a lost item |
| 8 | Claim status | approve (others auto-rejected, item becomes Claimed), reject, non-owner gets 403 |
| 9 | Dashboard | counts, own items, edit, delete |
| 10 | Saved items and matching | save/remove, login and POST requirements, safe redirects, dashboard display, active opposite-type same-category suggestions |
| 11 | Admin | changelists load for superuser; normal users blocked |
| 12 | Unauthorised access | login redirects, 403 on others' items, private details and contact hidden, CSRF enforced |

A manual smoke test of every URL against `runserver` returned the expected status codes.

## 12. Results
All required modules work end to end: reports can be created, found by search, claimed, verified and closed; admins can supervise all data; unauthorised actions are blocked.

## 13. Conclusion
CampusFind delivers a practical, secure and presentable solution to a real campus problem using only the prescribed stack, while covering every INT253 unit.

## 14. Future enhancements
Email/SMS notifications, image-similarity matching, map view, QR tags, in-app chat, PostgreSQL deployment, REST API and mobile app.
