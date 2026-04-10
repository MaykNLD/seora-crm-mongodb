"""
Automated QA test suite for Seora CRM
Probes every public route and REST API endpoint, reporting pass/fail.
"""
import requests
import json

BASE = "http://127.0.0.1:3000"
PASS = 0
FAIL = 0
ERRORS = []

def check(label, method, path, expected_status=200, data=None, follow=True):
    global PASS, FAIL
    url = BASE + path
    try:
        if method == "GET":
            r = requests.get(url, allow_redirects=follow, timeout=6)
        else:
            r = requests.post(url, data=data, allow_redirects=follow, timeout=6)

        ok = r.status_code in ([expected_status] if isinstance(expected_status, int) else expected_status)
        symbol = "[PASS]" if ok else "[FAIL]"
        if ok:
            PASS += 1
        else:
            FAIL += 1
            ERRORS.append(f"{label} -> got {r.status_code}")
        print(f"  {symbol}  {label:<55} {r.status_code}")
    except Exception as e:
        FAIL += 1
        ERRORS.append(f"{label} -> EXCEPTION: {e}")
        print(f"  [FAIL]  {label:<55} ERROR: {e}")


print("\n=== Seora CRM — Automated QA Suite ===\n")

# ── Page Routes ──────────────────────────────────────────────────────────────
print("[ PAGES ]")
check("Index redirect",           "GET",  "/",            [301, 302, 200])
check("Landing page",             "GET",  "/landing",     200)
check("Dashboard",                "GET",  "/dashboard",   200)
check("Instruments list",         "GET",  "/instruments", 200)
check("Instruments search",       "GET",  "/instruments?q=Fender", 200)
check("Instruments filter cond",  "GET",  "/instruments?condition=New", 200)
check("Add instrument form",      "GET",  "/instruments/add", 200)
check("Transactions list",        "GET",  "/transactions", 200)
check("Repairs list",             "GET",  "/repairs",     200)
check("Customers list",           "GET",  "/customers",   200)
check("Suppliers list",           "GET",  "/suppliers",   200)
check("Employees list",           "GET",  "/employees",   200)
check("API Explorer",             "GET",  "/api",         200)

# ── REST API Endpoints ────────────────────────────────────────────────────────
print("\n[ REST API ]")
check("GET /api/v1/instruments",  "GET",  "/api/v1/instruments",  200)
check("GET /api/v1/customers",    "GET",  "/api/v1/customers",    200)
check("GET /api/v1/transactions", "GET",  "/api/v1/transactions", 200)
check("GET /api/v1/repairs",      "GET",  "/api/v1/repairs",      200)
check("GET /api/v1/dashboard",    "GET",  "/api/v1/dashboard",    200)

# ── API Data Integrity ────────────────────────────────────────────────────────
print("\n[ DATA INTEGRITY ]")
try:
    instruments = requests.get(BASE + "/api/v1/instruments", timeout=6).json()
    customers   = requests.get(BASE + "/api/v1/customers",   timeout=6).json()
    transactions= requests.get(BASE + "/api/v1/transactions",timeout=6).json()
    repairs     = requests.get(BASE + "/api/v1/repairs",     timeout=6).json()
    dashboard   = requests.get(BASE + "/api/v1/dashboard",   timeout=6).json()

    def assert_data(label, condition):
        global PASS, FAIL
        if condition:
            print(f"  [PASS]  {label}")
            PASS += 1
        else:
            print(f"  [FAIL]  {label}")
            FAIL += 1
            ERRORS.append(f"DATA: {label}")

    assert_data(f"Instruments count >= 25               got {len(instruments)}", len(instruments) >= 25)
    assert_data(f"Customers count >= 15                 got {len(customers)}",   len(customers)   >= 15)
    assert_data(f"Transactions count >= 20              got {len(transactions)}", len(transactions)>= 20)
    assert_data(f"Repairs count >= 10                   got {len(repairs)}",     len(repairs)     >= 10)
    assert_data(f"Total revenue > 0                     got {dashboard.get('total_revenue',0)}", dashboard.get('total_revenue', 0) > 0)
    assert_data(f"Net profit > 0                        got {dashboard.get('net_profit',0)}",    dashboard.get('net_profit', 0) > 0)
    assert_data(f"Storage mode field present            got '{dashboard.get('storage_mode')}'",  'storage_mode' in dashboard)

    # Check a Steinway is in instruments (flagship data)
    names = [i.get('name', '') for i in instruments]
    assert_data(f"Steinway Model M in seed data",        any('Steinway' in n for n in names))
    assert_data(f"Each instrument has buy_price > 0",    all(i.get('buy_price', 0) > 0 for i in instruments))
    assert_data(f"Each customer has name and email",     all(c.get('name') and c.get('email') for c in customers))

    # Check CRUD: Add a customer
    add_r = requests.post(BASE + "/customers/add", data={
        'name': 'QA Test User', 'email': 'qa@test.com', 'phone': '+1 000 000', 'segment': 'New'
    }, allow_redirects=True, timeout=6)
    assert_data(f"POST /customers/add -> 200",           add_r.status_code == 200)

    # Verify it was persisted
    customers2 = requests.get(BASE + "/api/v1/customers", timeout=6).json()
    assert_data(f"New customer persisted (count +1)",    len(customers2) == len(customers) + 1)

except Exception as e:
    print(f"  [FAIL]  Data integrity check crashed: {e}")
    FAIL += 1
    ERRORS.append(str(e))

# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"  TOTAL: {PASS + FAIL}  |  PASS: {PASS}  |  FAIL: {FAIL}")
if ERRORS:
    print(f"\n  FAILURES:")
    for e in ERRORS:
        print(f"    - {e}")
else:
    print("\n  All checks passed. CRM is production-ready.")
print(f"{'='*50}\n")
