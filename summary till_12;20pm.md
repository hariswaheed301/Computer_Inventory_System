Here is a summary of the entire system, architecture, tech stack, and what has been built. You can use this as a reference or recap before your presentation and interview demo!📌 Executive System Summary & Context🎯 Core Business ObjectiveTo build an offline-ready, secure, and performant Computer Hardware & Parts Inventory Management System featuring Role-Based Access Control (RBAC), multi-level parent/child categories (e.g., Keyboards $\rightarrow$ Mechanical Keyboards), real-time stock adjustments, and administrative price controls (separating Cost Price from Retail Price).🛠️ Tech Stack & DependenciesLanguage: Python 3.xWeb Framework: Flask (App Factory Pattern with Blueprints)Database: PostgreSQL (Relational Database)Database Driver: psycopg2 / psycopg2-binary (Using ThreadedConnectionPool & raw, parameterized SQL queries)Authentication & Security: \* Flask-Login (Session management & user loader)Werkzeug.security (generate_password_hash & check_password_hash)Flask-WTF / CSRFProtect (CSRF token protection on all forms)Frontend UI Framework: Bootstrap 5 + SB Admin v7.0.7 (Custom CSS & JS) + FontAwesome 6 icons🏗️ System Architecture & Data Flow+-------------------------------------------------------------------+
| BROWSER / FRONTEND |
| (Bootstrap 5 + SB Admin v7 Templates + Jinja2 Rendering) |
+-------------------------------------------------------------------+
│
HTTP Requests / Form Data
│
▼
+-------------------------------------------------------------------+
| FLASK APPLICATION SERVER |
| |
| • wsgi.py (Entrypoint & DB Seeder) |
| • app/**init**.py (App Factory & Flask Extension Init) |
| • app/config.py (Environment Variable Loader) |
| |
| ┌────────────────────────┐ ┌─────────────────────────────┐ |
| │ auth_routes Blueprint │ │ stock_routes Blueprint │ |
| │ (/login, /register, │ │ (/dashboard, /inventory, │ |
| │ /logout) │ │ /inventory/adjust) │ |
| └────────────────────────┘ └─────────────────────────────┘ |
+-------------------------------------------------------------------+
│
Raw Parameterized SQL Statements (%s)
│
▼
+-------------------------------------------------------------------+
| DATABASE LAYER (app/db.py) |
| psycopg2.pool.ThreadedConnectionPool (Thread-safe pool) |
+-------------------------------------------------------------------+
│
▼
+-------------------------------------------------------------------+
| POSTGRESQL DATABASE |
| Tables: users, categories, brands, products |
+-------------------------------------------------------------------+
🗄️ Relational Database Schema (PostgreSQL)usersid (SERIAL PRIMARY KEY)username (VARCHAR, UNIQUE)email (VARCHAR, UNIQUE)password_hash (VARCHAR)role (VARCHAR: 'ADMIN' vs 'STORE_PERSON')created_at (TIMESTAMP)categories (Hierarchical / Self-Referencing)id (SERIAL PRIMARY KEY)name (VARCHAR)parent_id (INT, Foreign Key referencing categories(id))brandsid (SERIAL PRIMARY KEY)name (VARCHAR, UNIQUE)productsid (SERIAL PRIMARY KEY)sku (VARCHAR, UNIQUE)name (VARCHAR)brand_id (INT FK $\rightarrow$ brands.id)category_id (INT FK $\rightarrow$ categories.id)quantity (INT)reorder_level (INT)cost_price (NUMERIC(10,2) — Restricted to Admin view)retail_price (NUMERIC(10,2))🔐 Security Highlights (Production & Offline Readiness)SQL Injection Prevention: No ORM (SQLAlchemy) used. All database calls utilize parameterized SQL query placeholders (%s) via psycopg2. User inputs are passed separately as tuple parameters.Role-Based Access Control (RBAC):Custom @role_required('ADMIN') decorator and template checks ({% if current_user.role == 'ADMIN' %}).Admin Role: Full visibility into financial metrics including product Cost Prices.Store Person Role: Restricted from viewing sensitive financial/cost data while managing stock levels.Cross-Site Request Forgery (CSRF): Protected via Flask-WTF using hidden csrf_token fields in POST forms.Connection Pooling: Uses psycopg2.pool.ThreadedConnectionPool in app/db.py to minimize overhead and optimize connection re-use.📦 What We Have BuiltDatabase & Seeder (wsgi.py & app/db.py): Auto-creates PostgreSQL schema tables on startup and seeds default admin/store user accounts alongside hardware sample data (Keyboards, Silent Keyboards, Mechanical Keyboards, Razer, Logitech, Dell).Authentication System (/register, /login, /logout): Supports registration with role assignment (ADMIN or STORE_PERSON), login via username or email, session persistence via Flask-Login, and secure password hashing.Store Dashboard (/dashboard): Aggregates inventory metrics via SQL queries showing total SKUs, Out of Stock items (NIL), and Low Stock alert warnings.Inventory Catalog & Management (/inventory, /inventory/adjust/<id>):Displays hardware products with live stock status badges (NIL, Low, or available quantity).Left sidebar listing parent categories and subcategories with filtering capability.Quick-action buttons (+ / -) for instant stock level updates.Conditional layout rendering to display cost price strictly for ADMIN users.UI Layout Integration (base.html): Integrated SB Admin v7 template with dynamic alert flash messages, navigation bar, responsive sidebar toggle, and user profile badges.

Here is the complete Project Folder Architecture & Directory Structure for your application. You can copy this or present it directly during your interview to demonstrate clean, enterprise-grade project organization.

📂 Directory Tree Layout
Plaintext
Computer_Inventory_System/
│
├── .env # Environment variables (DB credentials, secret keys)
├── .gitignore # Prevents committing venv, .env, and **pycache**
├── requirements.txt # Python dependencies (Flask, psycopg2-binary, python-dotenv, etc.)
├── wsgi.py # Entry point for starting app & auto-creating/seeding database
│
├── venv/ # Isolated Python Virtual Environment folder
│
└── app/ # Main Application Package (Modular Monolith)
├── **init**.py # Application Factory (create_app), Flask extension setup
├── config.py # Config class loading variables from .env
├── db.py # Threaded PostgreSQL connection pool & execution helper
├── models.py # User class & Flask-Login user_loader query callback
│
├── routes/ # Modular Blueprints (Clean Route Separation)
│ ├── **init**.py
│ ├── auth_routes.py # Authentication routes (/login, /register, /logout)
│ └── stock_routes.py # Inventory & dashboard routes (/dashboard, /inventory, /inventory/adjust)
│
├── static/ # Static Assets (CSS / JS / Images)
│ ├── css/
│ │ └── styles.css # SB Admin v7 compiled theme styles
│ └── js/
│ └── scripts.js # Sidebar toggle & frontend logic
│
└── templates/ # Server-Side Jinja2 HTML Templates
├── base.html # Main layout shell (Navbar, Sidebar, Footer, Flash Alerts)
├── auth/
│ ├── login.html # Login page form
│ └── register.html # Staff account creation form
│
├── dashboard/
│ └── dashboard.html # Analytics overview (Total SKUs, Out of Stock, Low Stock cards)
│
└── stock/
└── inventory.html # Inventory catalog table, sidebar category tree, stock controls
🔍 Detailed Responsibility Breakdown
wsgi.py (App Runner & Database Seeder)

Imports create_app() from app.

Creates the database tables (users, categories, brands, products) if they don't already exist.

Auto-seeds initial admin (admin) & store user (storeperson) accounts alongside default categories and sample computer hardware.

app/**init**.py (Application Factory)

Uses the Application Factory pattern (def create_app():).

Initializes Flask-Login (for user sessions) and CSRFProtect (for security).

Registers route Blueprints (auth_bp and stock_bp).

app/db.py (Database Connection Pool)

Manages PostgreSQL connections using psycopg2.pool.ThreadedConnectionPool for high-performance concurrent request handling.

Provides the execute_query() parameterized wrapper to safely execute SQL queries without SQL injection risk.

app/routes/ (Modular Blueprints)

auth_routes.py: Handles authentication workflows (logging in, hashing passwords, role assignment, logging out).

stock_routes.py: Handles inventory listing, SQL metrics calculation for the dashboard, stock adjustments (+ / -), and category filtering.

app/templates/ (UI Layer)

base.html: Enforces a consistent UI across all pages using Jinja2 Template Inheritance ({% extends "base.html" %}).

Contains Bootstrap 5 and SB Admin v7 navigation elements.
