from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, g
from bson.objectid import ObjectId
from datetime import datetime, date
import os
from dotenv import load_dotenv

load_dotenv()  # Load .env file automatically (python-dotenv)

app = Flask(__name__)
# SECRET_KEY must be set in .env for production. Falls back to dev-only placeholder.
app.secret_key = os.environ.get('SECRET_KEY') or 'dev-only-replace-in-production'

# =============================================================================
# STORAGE BACKEND AUTO-DETECT
# Attempts MongoDB connection first; falls back to JSON sandbox automatically.
# This is the Storage Interface Adapter Pattern in action.
# =============================================================================

MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/crm')
STORAGE_MODE = 'json'  # Default; overridden below if MongoDB is available.

try:
    from pymongo import MongoClient
    _test_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
    _test_client.server_info()  # Raises ServerSelectionTimeoutError if unavailable

    from flask_pymongo import PyMongo
    app.config["MONGO_URI"] = MONGO_URI
    mongo = PyMongo(app)
    db = mongo.db
    STORAGE_MODE = 'mongodb'
    print(f"\n[OK] Seora CRM -- MongoDB mode active: {MONGO_URI}")

except Exception as e:
    from storage import JSONDatabase
    db = JSONDatabase()
    STORAGE_MODE = 'json'
    print(f"[!!] Seora CRM -- MongoDB not available ({type(e).__name__})")
    print("[!!] Activating JSON Sandbox Mode -- full demo data loaded automatically.\n")


# =============================================================================
# CONTEXT PROCESSOR — injects storage mode into every template
# =============================================================================

@app.context_processor
def inject_storage_mode():
    return dict(storage_mode=STORAGE_MODE)


# =============================================================================
# HELPERS & SERIALIZATION
# =============================================================================

def serialize_doc(doc, for_api=False):
    """Convert MongoDB/JSON document to a JSON-serializable dict."""
    if not doc:
        return None
    doc['id'] = str(doc['_id'])
    if for_api:
        for key, value in doc.items():
            if isinstance(value, (datetime, date)):
                doc[key] = value.isoformat()
    return doc


def parse_date(val):
    """Normalize a date value to datetime (works for both MongoDB datetime and JSON ISO string)."""
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val)
        except ValueError:
            pass
    return val



# =============================================================================
# RICH SEED DATA — 15 customers, 25 instruments, 20 transactions, 10 repairs
# Runs at startup regardless of whether Flask is invoked via Gunicorn or CLI.
# =============================================================================

def seed_data():
    if db.customers.count_documents({}) > 0:
        return  # Already seeded

    print("[*] Seeding demo data...")

    # ── Customers (15) ─────────────────────────────────────────────────────────
    customers = [
        {'name': 'Carlos Mendez',        'email': 'carlos@mendez.com',     'phone': '+34 612 345 678', 'segment': 'VIP',        'city': 'Madrid',    'created_at': datetime(2024, 1, 15)},
        {'name': 'Laura Jiménez',         'email': 'laura@jimenez.com',     'phone': '+34 622 111 222', 'segment': 'VIP',        'city': 'Barcelona', 'created_at': datetime(2024, 2, 3)},
        {'name': 'Marco Rivera',          'email': 'marco@rivera.com',      'phone': '+34 633 999 000', 'segment': 'Frequent',   'city': 'Valencia',  'created_at': datetime(2024, 3, 10)},
        {'name': 'Ana Torres',            'email': 'ana@torres.com',        'phone': '+34 644 555 777', 'segment': 'VIP',        'city': 'Sevilla',   'created_at': datetime(2024, 4, 22)},
        {'name': 'Diego Morales',         'email': 'diego@morales.com',     'phone': '+34 655 321 654', 'segment': 'Frequent',   'city': 'Madrid',    'created_at': datetime(2024, 5, 8)},
        {'name': 'Isabella Ruiz',         'email': 'isabella@ruiz.com',     'phone': '+34 666 789 012', 'segment': 'Occasional', 'city': 'Bilbao',    'created_at': datetime(2024, 6, 19)},
        {'name': 'Santiago López',        'email': 'santiago@lopez.com',    'phone': '+34 677 456 789', 'segment': 'New',        'city': 'Granada',   'created_at': datetime(2024, 8, 5)},
        {'name': 'Valentina García',      'email': 'valentina@garcia.com',  'phone': '+34 688 234 567', 'segment': 'VIP',        'city': 'Barcelona', 'created_at': datetime(2024, 9, 14)},
        {'name': 'Alejandro Hernández',   'email': 'alex@hernandez.com',    'phone': '+34 699 876 543', 'segment': 'Frequent',   'city': 'Madrid',    'created_at': datetime(2024, 10, 2)},
        {'name': 'Camila Martínez',       'email': 'camila@martinez.com',   'phone': '+34 611 345 678', 'segment': 'Occasional', 'city': 'Valencia',  'created_at': datetime(2024, 10, 28)},
        {'name': 'Luis Fernández',        'email': 'luis@fernandez.com',    'phone': '+34 621 987 654', 'segment': 'New',        'city': 'Málaga',    'created_at': datetime(2024, 11, 3)},
        {'name': 'Sofía Ramírez',         'email': 'sofia@ramirez.com',     'phone': '+34 631 234 567', 'segment': 'Frequent',   'city': 'Sevilla',   'created_at': datetime(2024, 11, 22)},
        {'name': 'Mateo González',        'email': 'mateo@gonzalez.com',    'phone': '+34 641 765 432', 'segment': 'VIP',        'city': 'Madrid',    'created_at': datetime(2024, 12, 8)},
        {'name': 'Paula Sánchez',         'email': 'paula@sanchez.com',     'phone': '+34 651 543 210', 'segment': 'Occasional', 'city': 'Zaragoza',  'created_at': datetime(2025, 1, 15)},
        {'name': 'Roberto Castro',        'email': 'roberto@castro.com',    'phone': '+34 661 111 222', 'segment': 'New',        'city': 'Bilbao',    'created_at': datetime(2025, 2, 20)},
    ]
    db.customers.insert_many(customers)
    c_ids = {c['name']: c['_id'] for c in db.customers.find()}

    # ── Suppliers (3) ─────────────────────────────────────────────────────────
    suppliers = [
        {'name': 'Music Distribution SA',  'contact': 'Jose Ruiz',   'email': 'jose@musicdist.com',    'phone': '+34 91 234 5678',  'address': 'Calle Mayor 14, Madrid'},
        {'name': 'Fender Europe GmbH',      'contact': 'Klaus Wagner', 'email': 'kwagner@fender.eu',    'phone': '+49 89 1234 567',  'address': 'Münchener Str. 3, Munich'},
        {'name': 'Gibson Guitar Corp.',     'contact': 'John Smith',   'email': 'jsmith@gibson.com',   'phone': '+1 615 871 4500', 'address': '309 Plus Park Blvd, Nashville'},
    ]
    db.suppliers.insert_many(suppliers)

    # ── Employees (5) ─────────────────────────────────────────────────────────
    employees = [
        {'name': 'Admin User',     'email': 'admin@seora.com',   'role': 'Admin'},
        {'name': 'Pedro Alonso',   'email': 'pedro@seora.com',   'role': 'Sales'},
        {'name': 'Sofia Vega',     'email': 'sofia@seora.com',   'role': 'Tech'},
        {'name': 'Javier Cruz',    'email': 'javier@seora.com',  'role': 'Sales'},
        {'name': 'Elena Morales',  'email': 'elena@seora.com',   'role': 'Tech'},
    ]
    db.employees.insert_many(employees)
    e_ids = {e['name']: e['_id'] for e in db.employees.find()}

    # ── Instruments (25) ──────────────────────────────────────────────────────
    instruments = [
        {'internal_id': 'INST-001', 'name': 'Fender AM Pro II Stratocaster',    'brand': 'Fender',    'type': 'Electric Guitar',   'condition': 'New',       'buy_price': 1500,  'sell_price': 2100,  'stock': 3, 'serial_number': 'US22012345',  'description': 'American Professional II Stratocaster — 3-Color Sunburst, rosewood fingerboard.'},
        {'internal_id': 'INST-002', 'name': "Gibson Les Paul Standard '60s",    'brand': 'Gibson',    'type': 'Electric Guitar',   'condition': 'New',       'buy_price': 2200,  'sell_price': 3500,  'stock': 2, 'serial_number': 'GIB-LP200456', 'description': "Les Paul Standard '60s with push/pull coil taps — Bourbon Burst finish."},
        {'internal_id': 'INST-003', 'name': 'Yamaha C3X Grand Piano',           'brand': 'Yamaha',    'type': 'Grand Piano',       'condition': 'Used',      'buy_price': 9000,  'sell_price': 14500, 'stock': 1, 'serial_number': 'YC3-098765',   'description': 'Yamaha C3X Studio Grand, 6ft 1in. Lightly used, tuned and regulated.'},
        {'internal_id': 'INST-004', 'name': 'Martin 000-28EC Eric Clapton',     'brand': 'Martin',    'type': 'Acoustic Guitar',   'condition': 'New',       'buy_price': 2200,  'sell_price': 3200,  'stock': 2, 'serial_number': 'MX-EC-20245',  'description': 'Eric Clapton signature model, Sitka spruce top, Adirondack bracing.'},
        {'internal_id': 'INST-005', 'name': 'Roland TD-27KV V-Drums',           'brand': 'Roland',    'type': 'Electronic Drums',  'condition': 'Used',      'buy_price': 900,   'sell_price': 1850,  'stock': 1, 'serial_number': 'RD-TD27-555',  'description': 'Roland V-Drums TD-27KV complete kit with mesh pads, excellent condition.'},
        {'internal_id': 'INST-006', 'name': 'PRS Custom 24 10-Top',             'brand': 'PRS',       'type': 'Electric Guitar',   'condition': 'New',       'buy_price': 2800,  'sell_price': 4200,  'stock': 1, 'serial_number': 'PRS-C24-2025', 'description': 'Paul Reed Smith Custom 24 with figured maple 10-Top — Trampas Green.'},
        {'internal_id': 'INST-007', 'name': 'Steinway Model M Grand Piano',     'brand': 'Steinway',  'type': 'Grand Piano',       'condition': 'Used',      'buy_price': 28000, 'sell_price': 45000, 'stock': 1, 'serial_number': 'STW-M-67890',  'description': "Steinway Model M 5'7'' - Ebony lacquer, fully rebuilt hammers and strings."},
        {'internal_id': 'INST-008', 'name': 'Taylor 814ce DLX',                 'brand': 'Taylor',    'type': 'Acoustic Guitar',   'condition': 'New',       'buy_price': 2600,  'sell_price': 3800,  'stock': 3, 'serial_number': 'TAY-814-2025', 'description': 'Taylor 814ce Deluxe with Expression System 2 electronics and V-Class bracing.'},
        {'internal_id': 'INST-009', 'name': 'Fender Jazz Bass AM Performer',    'brand': 'Fender',    'type': 'Bass Guitar',       'condition': 'New',       'buy_price': 1100,  'sell_price': 1600,  'stock': 2, 'serial_number': 'US-JB-AM2024', 'description': 'American Performer Jazz Bass, Satin Surf Green, compound-radius fingerboard.'},
        {'internal_id': 'INST-010', 'name': 'Gibson ES-335 Figured',            'brand': 'Gibson',    'type': 'Electric Guitar',   'condition': 'Repairing', 'buy_price': 2800,  'sell_price': 4500,  'stock': 0, 'serial_number': 'GIB-ES335-789','description': 'Gibson ES-335 Heritage Cherry — In shop for fret leveling and full setup.'},
        {'internal_id': 'INST-011', "name": "DW Collector's Maple Shell Pack",  'brand': 'DW',        'type': 'Acoustic Drums',    'condition': 'New',       'buy_price': 3500,  'sell_price': 5200,  'stock': 1, 'serial_number': 'DW-CM-20250',  'description': "DW Collector's Series Maple — 5-piece, Chrome hardware, Natural/Black Burst."},
        {'internal_id': 'INST-012', 'name': 'Yamaha LL16 ARE',                  'brand': 'Yamaha',    'type': 'Acoustic Guitar',   'condition': 'New',       'buy_price': 900,   'sell_price': 1400,  'stock': 4, 'serial_number': 'YLL16-2024',   'description': 'Yamaha LL16 ARE with Acoustic Resonance Enhancement — solid Engelmann top.'},
        {'internal_id': 'INST-013', 'name': 'Kawai MP11SE Stage Piano',         'brand': 'Kawai',     'type': 'Digital Piano',     'condition': 'New',       'buy_price': 2200,  'sell_price': 3200,  'stock': 2, 'serial_number': 'KAW-MP11-507', 'description': 'Kawai MP11SE with Grand Feel Wooden Key action — flagship stage piano.'},
        {'internal_id': 'INST-014', 'name': 'Rickenbacker 4003 Bass',           'brand': 'Rickenbacker','type': 'Bass Guitar',     'condition': 'New',       'buy_price': 1400,  'sell_price': 2100,  'stock': 1, 'serial_number': 'RIC-4003-777', 'description': 'Rickenbacker 4003 in Fireglo — iconic bass with double-truss-rod neck.'},
        {'internal_id': 'INST-015', "name": "Gretsch G6120T-59 Chet Atkins",   'brand': 'Gretsch',   'type': 'Electric Guitar',   'condition': 'Used',      'buy_price': 2500,  'sell_price': 3800,  'stock': 1, 'serial_number': 'GRE-G6120-333','description': "Gretsch G6120T-59 Vintage Select '59 Chet Atkins — Orange Stain."},
        {'internal_id': 'INST-016', 'name': 'Martin D-45 Standard',             'brand': 'Martin',    'type': 'Acoustic Guitar',   'condition': 'New',       'buy_price': 6200,  'sell_price': 9000,  'stock': 1, 'serial_number': 'MX-D45-2025',  'description': 'The Martin D-45 — the pinnacle of the dreadnought tradition with full abalone purfling.'},
        {'internal_id': 'INST-017', 'name': 'Seora Custom Acoustic SN-2025',    'brand': 'Seora',     'type': 'Acoustic Guitar',   'condition': 'New',       'buy_price': 1800,  'sell_price': 3200,  'stock': 2, 'serial_number': 'SR-2025-001',  'description': 'Hand-crafted limited edition acoustic — cedar top, Indian rosewood back & sides.'},
        {'internal_id': 'INST-018', 'name': 'Fender Precision Bass AM Original','brand': 'Fender',    'type': 'Bass Guitar',       'condition': 'New',       'buy_price': 1600,  'sell_price': 2400,  'stock': 1, 'serial_number': 'US-PB-OR2025', 'description': 'American Original Precision Bass with vintage Pure Vintage pickups — Surf Green.'},
        {'internal_id': 'INST-019', 'name': 'Korg Kronos2 88',                  'brand': 'Korg',      'type': 'Synthesizer',       'condition': 'Used',      'buy_price': 1900,  'sell_price': 2800,  'stock': 1, 'serial_number': 'KRG-KR2-444',  'description': 'Korg Kronos2 88 with RH3 keybed — 9 sound engines, full workstation.'},
        {'internal_id': 'INST-020', 'name': 'Ibanez RG6003FM',                  'brand': 'Ibanez',    'type': 'Electric Guitar',   'condition': 'New',       'buy_price': 700,   'sell_price': 1100,  'stock': 5, 'serial_number': 'IBZ-RG6-599',  'description': 'Ibanez RG6003FM with figured maple top, Edge-Zero II tremolo — Flat Blue.'},
        {'internal_id': 'INST-021', 'name': 'Mesa/Boogie Mark V 90',            'brand': 'Mesa/Boogie','type': 'Guitar Amplifier',  'condition': 'Used',      'buy_price': 1500,  'sell_price': 2200,  'stock': 1, 'serial_number': 'MB-MV90-202',  'description': 'Mesa/Boogie Mark V 90W — all tube, 3 channels, includes matching 4x12 cab.'},
        {'internal_id': 'INST-022', 'name': 'Pearl Masters Custom Maple',       'brand': 'Pearl',     'type': 'Acoustic Drums',    'condition': 'New',       'buy_price': 2600,  'sell_price': 3800,  'stock': 1, 'serial_number': 'PRL-MCM-900',  'description': '5-piece Pearl Masters Custom Maple in Aqua Marine Fade — hardware included.'},
        {'internal_id': 'INST-023', "name": "Gibson SG Standard '61",           'brand': 'Gibson',    'type': 'Electric Guitar',   'condition': 'Used',      'buy_price': 1000,  'sell_price': 1600,  'stock': 1, 'serial_number': 'GIB-SG61-321', 'description': "Gibson SG Standard '61 in Vintage Cherry — light wear, great player."},
        {'internal_id': 'INST-024', 'name': 'Fender Telecaster AM Elite',       'brand': 'Fender',    'type': 'Electric Guitar',   'condition': 'New',       'buy_price': 1500,  'sell_price': 2300,  'stock': 2, 'serial_number': 'US-TE-EL2025', 'description': "Fender American Elite Telecaster — 4th-gen Noiseless pickups, shawbucker at neck."},
        {'internal_id': 'INST-025', 'name': 'Yamaha Pacifica 612VIIFM',         'brand': 'Yamaha',    'type': 'Electric Guitar',   'condition': 'New',       'buy_price': 700,   'sell_price': 1100,  'stock': 6, 'serial_number': 'YAM-PAC-612',  'description': 'Yamaha Pacifica 612VIIFM with solid figured maple top — Indigo Blue.'},
    ]
    db.instruments.insert_many(instruments)
    i_ids = {i['name']: i['_id'] for i in db.instruments.find()}

    # ── Transactions (20) ─────────────────────────────────────────────────────
    transactions = [
        {'type': 'sale',     'customer_id': c_ids['Carlos Mendez'],       'instrument_id': i_ids['Fender AM Pro II Stratocaster'],  'amount': 2100,  'payment_method': 'Card',     'notes': 'VIP regular purchase.', 'date': datetime(2025, 9, 5)},
        {'type': 'purchase', 'customer_id': c_ids['Laura Jiménez'],        'instrument_id': i_ids['Yamaha C3X Grand Piano'],          'amount': 9000,  'payment_method': 'Transfer', 'notes': 'Consignment intake.', 'date': datetime(2025, 9, 18)},
        {'type': 'sale',     'customer_id': c_ids['Marco Rivera'],         'instrument_id': i_ids['Roland TD-27KV V-Drums'],          'amount': 1850,  'payment_method': 'Cash',     'notes': '', 'date': datetime(2025, 10, 2)},
        {'type': 'sale',     'customer_id': c_ids['Ana Torres'],           'instrument_id': i_ids['Martin 000-28EC Eric Clapton'],    'amount': 3200,  'payment_method': 'Card',     'notes': 'Gift purchase.', 'date': datetime(2025, 10, 14)},
        {'type': 'sale',     'customer_id': c_ids['Valentina García'],     'instrument_id': i_ids['Taylor 814ce DLX'],                'amount': 3800,  'payment_method': 'Transfer', 'notes': 'Layaway completed.', 'date': datetime(2025, 10, 22)},
        {'type': 'sale',     'customer_id': c_ids['Mateo González'],       'instrument_id': i_ids["Gibson Les Paul Standard '60s"],   'amount': 3500,  'payment_method': 'Card',     'notes': '', 'date': datetime(2025, 11, 3)},
        {'type': 'purchase', 'customer_id': c_ids['Diego Morales'],        'instrument_id': i_ids['Mesa/Boogie Mark V 90'],           'amount': 1500,  'payment_method': 'Cash',     'notes': 'Trade-in from customer.', 'date': datetime(2025, 11, 9)},
        {'type': 'sale',     'customer_id': c_ids['Alejandro Hernández'],  'instrument_id': i_ids['Kawai MP11SE Stage Piano'],        'amount': 3200,  'payment_method': 'Transfer', 'notes': '', 'date': datetime(2025, 11, 20)},
        {'type': 'sale',     'customer_id': c_ids['Sofía Ramírez'],        'instrument_id': i_ids['Fender Jazz Bass AM Performer'],   'amount': 1600,  'payment_method': 'Card',     'notes': '', 'date': datetime(2025, 12, 1)},
        {'type': 'sale',     'customer_id': c_ids['Carlos Mendez'],        'instrument_id': i_ids['PRS Custom 24 10-Top'],            'amount': 4200,  'payment_method': 'Card',     'notes': 'Second purchase this quarter.', 'date': datetime(2025, 12, 10)},
        {'type': 'purchase', 'customer_id': c_ids['Camila Martínez'],      'instrument_id': i_ids["Gretsch G6120T-59 Chet Atkins"],   'amount': 2500,  'payment_method': 'Transfer', 'notes': 'Instrument consigned.', 'date': datetime(2025, 12, 15)},
        {'type': 'sale',     'customer_id': c_ids['Laura Jiménez'],        'instrument_id': i_ids['Yamaha C3X Grand Piano'],          'amount': 14500, 'payment_method': 'Transfer', 'notes': 'Grand piano final sale.', 'date': datetime(2026, 1, 8)},
        {'type': 'sale',     'customer_id': c_ids['Ana Torres'],           'instrument_id': i_ids['Seora Custom Acoustic SN-2025'],   'amount': 3200,  'payment_method': 'Card',     'notes': '', 'date': datetime(2026, 1, 22)},
        {'type': 'sale',     'customer_id': c_ids['Santiago López'],       'instrument_id': i_ids['Yamaha Pacifica 612VIIFM'],        'amount': 1100,  'payment_method': 'Cash',     'notes': 'First purchase — new customer.', 'date': datetime(2026, 2, 5)},
        {'type': 'sale',     'customer_id': c_ids['Mateo González'],       'instrument_id': i_ids['Steinway Model M Grand Piano'],    'amount': 45000, 'payment_method': 'Transfer', 'notes': 'Flagship sale — Steinway.', 'date': datetime(2026, 2, 14)},
        {'type': 'sale',     'customer_id': c_ids['Valentina García'],     'instrument_id': i_ids['Rickenbacker 4003 Bass'],          'amount': 2100,  'payment_method': 'Card',     'notes': '', 'date': datetime(2026, 2, 28)},
        {'type': 'purchase', 'customer_id': c_ids['Luis Fernández'],       'instrument_id': i_ids["Gibson SG Standard '61"],          'amount': 1000,  'payment_method': 'Cash',     'notes': 'Used guitar trade.', 'date': datetime(2026, 3, 5)},
        {'type': 'sale',     'customer_id': c_ids['Diego Morales'],        'instrument_id': i_ids['Korg Kronos2 88'],                 'amount': 2800,  'payment_method': 'Card',     'notes': '', 'date': datetime(2026, 3, 12)},
        {'type': 'sale',     'customer_id': c_ids['Paula Sánchez'],        'instrument_id': i_ids['Yamaha LL16 ARE'],                 'amount': 1400,  'payment_method': 'Card',     'notes': '', 'date': datetime(2026, 3, 20)},
        {'type': 'sale',     'customer_id': c_ids['Roberto Castro'],       'instrument_id': i_ids['Ibanez RG6003FM'],                 'amount': 1100,  'payment_method': 'Cash',     'notes': 'New customer first purchase.', 'date': datetime(2026, 3, 27)},
    ]
    db.transactions.insert_many(transactions)

    # ── Repairs (10) ──────────────────────────────────────────────────────────
    repairs = [
        {'order_number': 'REP-001', 'customer_id': c_ids['Carlos Mendez'],     'instrument_id': i_ids['Gibson ES-335 Figured'],         'technician_id': e_ids['Sofia Vega'],   'problem': 'Fret buzz on strings 1–3, needs fret leveling and full setup.', 'status': 'InProgress', 'estimated_cost': 180.0, 'entry_date': datetime(2026, 3, 10)},
        {'order_number': 'REP-002', 'customer_id': c_ids['Laura Jiménez'],      'instrument_id': i_ids['Kawai MP11SE Stage Piano'],       'technician_id': e_ids['Elena Morales'], 'problem': 'Broken sustain pedal, key sticking on D3.', 'status': 'Pending',   'estimated_cost': 95.0,  'entry_date': datetime(2026, 3, 18)},
        {'order_number': 'REP-003', 'customer_id': c_ids['Marco Rivera'],       'instrument_id': i_ids['Fender AM Pro II Stratocaster'],  'technician_id': e_ids['Sofia Vega'],   'problem': 'Pickup switch intermittent, nut replacement.', 'status': 'Done',      'estimated_cost': 70.0,  'entry_date': datetime(2026, 2, 22), 'exit_date': datetime(2026, 3, 1),  'final_cost': 65.0},
        {'order_number': 'REP-004', 'customer_id': c_ids['Ana Torres'],         'instrument_id': i_ids['Taylor 814ce DLX'],               'technician_id': e_ids['Elena Morales'], 'problem': 'Humidity crack on top near soundhole, needs binding repair.', 'status': 'InProgress', 'estimated_cost': 250.0, 'entry_date': datetime(2026, 3, 25)},
        {'order_number': 'REP-005', 'customer_id': c_ids['Valentina García'],   'instrument_id': i_ids['Fender Jazz Bass AM Performer'],  'technician_id': e_ids['Sofia Vega'],   'problem': 'Output jack loose, bridge saddle replacement.', 'status': 'Done',      'estimated_cost': 45.0,  'entry_date': datetime(2026, 2, 10), 'exit_date': datetime(2026, 2, 15), 'final_cost': 45.0},
        {'order_number': 'REP-006', 'customer_id': c_ids['Alejandro Hernández'],'instrument_id': i_ids["Gibson Les Paul Standard '60s"],   'technician_id': e_ids['Sofia Vega'],   'problem': 'Wiring upgrade requested — CTS pots and Switchcraft jack.', 'status': 'Done',      'estimated_cost': 120.0, 'entry_date': datetime(2026, 1, 18), 'exit_date': datetime(2026, 1, 25), 'final_cost': 115.0},
        {'order_number': 'REP-007', 'customer_id': c_ids['Diego Morales'],      'instrument_id': i_ids['Mesa/Boogie Mark V 90'],           'technician_id': e_ids['Elena Morales'], 'problem': 'Bias adjustment, power tube replacement (EL34 matched set).', 'status': 'InProgress', 'estimated_cost': 200.0, 'entry_date': datetime(2026, 4, 1)},
        {'order_number': 'REP-008', 'customer_id': c_ids['Sofía Ramírez'],      'instrument_id': i_ids['Yamaha LL16 ARE'],                 'technician_id': e_ids['Sofia Vega'],   'problem': 'Bridge saddle replacement, intonation setup.', 'status': 'Pending',   'estimated_cost': 60.0,  'entry_date': datetime(2026, 4, 3)},
        {'order_number': 'REP-009', 'customer_id': c_ids['Mateo González'],     'instrument_id': i_ids['Steinway Model M Grand Piano'],    'technician_id': e_ids['Elena Morales'], 'problem': 'Annual regulation and voicing. Hammer reshaping required.', 'status': 'Done',      'estimated_cost': 450.0, 'entry_date': datetime(2025, 12, 5), 'exit_date': datetime(2025, 12, 20), 'final_cost': 430.0},
        {'order_number': 'REP-010', 'customer_id': c_ids['Camila Martínez'],    'instrument_id': i_ids["Gretsch G6120T-59 Chet Atkins"],   'technician_id': e_ids['Sofia Vega'],   'problem': 'Bigsby tremolo arm replacement, string action adjustment.', 'status': 'Pending',   'estimated_cost': 85.0,  'entry_date': datetime(2026, 4, 5)},
    ]
    db.repairs.insert_many(repairs)

    print(f"[OK] Seed complete — {db.customers.count_documents({})} customers, "
          f"{db.instruments.count_documents({})} instruments, "
          f"{db.transactions.count_documents({})} transactions, "
          f"{db.repairs.count_documents({})} repairs loaded.")


# =============================================================================
# Seed at module load — works with Gunicorn (multi-worker) AND direct python.
# MongoDB: seeds once (count_documents guard). JSON: seeds on first run.
# =============================================================================

def _create_indexes():
    """Create MongoDB indexes for query performance. Only runs in MongoDB mode."""
    if STORAGE_MODE != 'mongodb':
        return
    try:
        db.customers.create_index('email', sparse=True)
        db.customers.create_index('name')
        db.instruments.create_index('internal_id', unique=True)
        db.instruments.create_index([('name', 1), ('brand', 1)])
        db.transactions.create_index([('type', 1), ('date', -1)])
        db.repairs.create_index('order_number', unique=True)
        db.repairs.create_index('status')
        print('[OK] MongoDB indexes created.')
    except Exception as e:
        print(f'[!!] Index creation skipped: {e}')

with app.app_context():
    seed_data()
    _create_indexes()


# =======================
# HELPERS
# =======================
def get_dashboard_stats():
    revenue_pipeline = [{"$match": {"type": "sale"}},     {"$group": {"_id": None, "total": {"$sum": "$amount"}}}]
    spent_pipeline   = [{"$match": {"type": "purchase"}}, {"$group": {"_id": None, "total": {"$sum": "$amount"}}}]

    rev_result   = list(db.transactions.aggregate(revenue_pipeline))
    spent_result = list(db.transactions.aggregate(spent_pipeline))

    total_revenue = rev_result[0]['total']   if rev_result   else 0
    total_spent   = spent_result[0]['total'] if spent_result else 0

    instruments_sold = db.transactions.count_documents({"type": "sale"})
    active_repairs   = db.repairs.count_documents({"status": {"$ne": "Done"}})

    recent_transactions = list(db.transactions.find({"type": "sale"}).sort("date", -1).limit(5))
    recent_sales = []
    for t in recent_transactions:
        t['date'] = parse_date(t.get('date'))  # Normalize for strftime in templates
        c = db.customers.find_one({"_id": t['customer_id']})
        i = db.instruments.find_one({"_id": t['instrument_id']})
        if i:
            i['status'] = 'In Stock'
        recent_sales.append((t, c, i))

    return {
        'total_revenue': total_revenue,
        'net_profit':    total_revenue - total_spent,
        'instruments_sold': instruments_sold,
        'active_repairs':   active_repairs,
        'recent_sales': recent_sales,
    }


# =======================
# MAIN ROUTES
# =======================

@app.route('/')
def index():
    return redirect(url_for('landing'))

@app.route('/landing')
def landing():
    stats = get_dashboard_stats()
    return render_template('landing.html', stats=stats)

@app.route('/dashboard')
def dashboard():
    stats = get_dashboard_stats()
    customers = [serialize_doc(c) for c in db.customers.find()]
    instruments = [serialize_doc(i) for i in db.instruments.find({"stock": {"$gt": 0}})]
    techs = [serialize_doc(e) for e in db.employees.find({"role": "Tech"})]
    return render_template('dashboard.html', stats=stats, customers=customers, instruments=instruments, techs=techs)


# --- INSTRUMENTS ---
@app.route('/instruments')
def instruments():
    q = request.args.get('q', '')
    cond = request.args.get('condition', '')
    query = {}
    if q:
        query["$or"] = [
            {"name":        {"$regex": q, "$options": "i"}},
            {"brand":       {"$regex": q, "$options": "i"}},
            {"internal_id": {"$regex": q, "$options": "i"}},
        ]
    if cond:
        query["condition"] = cond

    inventory = []
    for inst in db.instruments.find(query):
        inst['margin'] = round(((inst['sell_price'] - inst['buy_price']) / inst['buy_price'] * 100), 1) if inst.get('buy_price', 0) > 0 else 0
        if inst['condition'] == 'Repairing': inst['status'] = 'Unavailable'
        elif inst.get('stock', 0) == 0:      inst['status'] = 'Out of Stock'
        elif inst.get('stock', 0) <= 2:      inst['status'] = 'Low Stock'
        else:                                inst['status'] = 'In Stock'
        inventory.append(serialize_doc(inst))

    return render_template('instruments.html', inventory=inventory, q=q, cond=cond)

@app.route('/instruments/add', methods=['GET', 'POST'])
def add_instrument():
    if request.method == 'POST':
        next_num = db.instruments.count_documents({}) + 1
        inst = {
            'internal_id':   f'INST-{next_num:03d}',
            'name':          request.form['name'],
            'brand':         request.form['brand'],
            'type':          request.form['type'],
            'condition':     request.form['condition'],
            'buy_price':     float(request.form.get('buy_price', 0)),
            'sell_price':    float(request.form.get('sell_price', 0)),
            'stock':         int(request.form.get('stock', 0)),
            'serial_number': request.form.get('serial_number', ''),
            'description':   request.form.get('description', ''),
        }
        db.instruments.insert_one(inst)
        flash('Instrument added to the system!', 'success')
        return redirect(url_for('instruments'))
    return render_template('instrument_form.html', instrument=None, action='Add')

@app.route('/instruments/edit/<id>', methods=['GET', 'POST'])
def edit_instrument(id):
    inst = db.instruments.find_one({"_id": ObjectId(id)})
    if request.method == 'POST':
        update_data = {
            'name':          request.form['name'],
            'brand':         request.form['brand'],
            'type':          request.form['type'],
            'condition':     request.form['condition'],
            'buy_price':     float(request.form.get('buy_price', 0)),
            'sell_price':    float(request.form.get('sell_price', 0)),
            'stock':         int(request.form.get('stock', 0)),
            'serial_number': request.form.get('serial_number', ''),
            'description':   request.form.get('description', ''),
        }
        db.instruments.update_one({"_id": ObjectId(id)}, {"$set": update_data})
        flash('Instrument updated!', 'success')
        return redirect(url_for('instruments'))
    return render_template('instrument_form.html', instrument=serialize_doc(inst), action='Edit')

@app.route('/instruments/delete/<id>', methods=['POST'])
def delete_instrument(id):
    db.instruments.delete_one({"_id": ObjectId(id)})
    flash('Instrument removed.', 'info')
    return redirect(url_for('instruments'))


# --- TRANSACTIONS ---
@app.route('/transactions')
def transactions():
    txs_raw = list(db.transactions.find().sort("date", -1))
    txs = []
    for t in txs_raw:
        t['date'] = parse_date(t.get('date'))
        c = db.customers.find_one({"_id": t['customer_id']})
        i = db.instruments.find_one({"_id": t['instrument_id']})
        txs.append((serialize_doc(t), serialize_doc(c), serialize_doc(i)))

    customers   = [serialize_doc(c) for c in db.customers.find()]
    instruments = [serialize_doc(i) for i in db.instruments.find({"stock": {"$gt": 0}})]
    return render_template('transactions.html', transactions=txs, customers=customers, instruments=instruments)

@app.route('/transactions/add', methods=['POST'])
def add_transaction():
    tx = {
        'type':           request.form['type'],
        'customer_id':    ObjectId(request.form['customer_id']),
        'instrument_id':  ObjectId(request.form['instrument_id']),
        'amount':         float(request.form['amount']),
        'payment_method': request.form.get('payment_method', 'Cash'),
        'notes':          request.form.get('notes', ''),
        'date':           datetime.utcnow(),
    }
    db.transactions.insert_one(tx)
    if tx['type'] == 'sale':
        db.instruments.update_one({"_id": tx['instrument_id']}, {"$inc": {"stock": -1}})
    else:
        db.instruments.update_one({"_id": tx['instrument_id']}, {"$inc": {"stock": 1}})
    flash('Transaction registered!', 'success')
    return redirect(url_for('transactions'))


# --- REPAIRS ---
@app.route('/repairs')
def repairs():
    repairs_raw = list(db.repairs.find().sort("entry_date", -1))
    all_repairs = []
    for r in repairs_raw:
        r['entry_date'] = parse_date(r.get('entry_date'))
        if 'exit_date' in r:
            r['exit_date'] = parse_date(r.get('exit_date'))
        c = db.customers.find_one({"_id": r['customer_id']})
        i = db.instruments.find_one({"_id": r['instrument_id']})
        e = db.employees.find_one({"_id": r['technician_id']}) if r.get('technician_id') else None
        all_repairs.append((serialize_doc(r), serialize_doc(c), serialize_doc(i), serialize_doc(e)))

    customers   = [serialize_doc(c) for c in db.customers.find()]
    instruments = [serialize_doc(i) for i in db.instruments.find()]
    techs       = [serialize_doc(e) for e in db.employees.find({"role": "Tech"})]
    return render_template('repairs.html', repairs=all_repairs, customers=customers, instruments=instruments, techs=techs)

@app.route('/repairs/add', methods=['POST'])
def add_repair():
    next_num = db.repairs.count_documents({}) + 1
    rep = {
        'order_number':  f'REP-{next_num:03d}',
        'customer_id':   ObjectId(request.form['customer_id']),
        'instrument_id': ObjectId(request.form['instrument_id']),
        'technician_id': ObjectId(request.form['technician_id']) if request.form.get('technician_id') else None,
        'problem':       request.form.get('problem', ''),
        'estimated_cost': float(request.form.get('estimated_cost', 0)),
        'status':        'Pending',
        'entry_date':    datetime.utcnow(),
    }
    db.repairs.insert_one(rep)
    flash('Repair order created!', 'success')
    return redirect(url_for('repairs'))

@app.route('/repairs/status/<id>', methods=['POST'])
def update_repair_status(id):
    status = request.form['status']
    if status == 'DELETE':
        db.repairs.delete_one({"_id": ObjectId(id)})
        flash('Repair removed.', 'info')
    else:
        update_data = {"status": status}
        if status == 'Done':
            update_data["exit_date"] = datetime.utcnow()
            if request.form.get('final_cost'):
                update_data["final_cost"] = float(request.form['final_cost'])
        db.repairs.update_one({"_id": ObjectId(id)}, {"$set": update_data})
        flash('Repair status updated!', 'success')
    return redirect(url_for('repairs'))


# --- CUSTOMERS ---
@app.route('/customers')
def customers():
    all_customers = []
    for c in db.customers.find().sort("name", 1):
        c['created_at'] = parse_date(c.get('created_at'))
        all_customers.append(serialize_doc(c))
    return render_template('customers.html', customers=all_customers)


@app.route('/customers/add', methods=['POST'])
def add_customer():
    c = {
        'name':       request.form['name'],
        'email':      request.form.get('email', ''),
        'phone':      request.form.get('phone', ''),
        'segment':    request.form.get('segment', 'Occasional'),
        'created_at': datetime.utcnow(),
    }
    db.customers.insert_one(c)
    flash('Customer registered!', 'success')
    return redirect(url_for('customers'))

@app.route('/customers/delete/<id>', methods=['POST'])
def delete_customer(id):
    db.customers.delete_one({"_id": ObjectId(id)})
    flash('Customer deleted.', 'info')
    return redirect(url_for('customers'))


# --- SUPPLIERS ---
@app.route('/suppliers')
def suppliers():
    all_suppliers = [serialize_doc(s) for s in db.suppliers.find()]
    return render_template('suppliers.html', suppliers=all_suppliers)

@app.route('/suppliers/add', methods=['POST'])
def add_supplier():
    s = {
        'name':    request.form['name'],
        'contact': request.form.get('contact', ''),
        'email':   request.form.get('email', ''),
        'phone':   request.form.get('phone', ''),
        'address': request.form.get('address', ''),
    }
    db.suppliers.insert_one(s)
    flash('Supplier added!', 'success')
    return redirect(url_for('suppliers'))

@app.route('/suppliers/delete/<id>', methods=['POST'])
def delete_supplier(id):
    db.suppliers.delete_one({"_id": ObjectId(id)})
    flash('Supplier removed.', 'info')
    return redirect(url_for('suppliers'))


# --- EMPLOYEES ---
@app.route('/employees')
def employees():
    all_employees = [serialize_doc(e) for e in db.employees.find()]
    return render_template('employees.html', employees=all_employees)

@app.route('/employees/add', methods=['POST'])
def add_employee():
    e = {
        'name':  request.form['name'],
        'email': request.form.get('email', ''),
        'role':  request.form.get('role', 'Sales'),
    }
    db.employees.insert_one(e)
    flash('Employee registered!', 'success')
    return redirect(url_for('employees'))

@app.route('/employees/delete/<id>', methods=['POST'])
def delete_employee(id):
    db.employees.delete_one({"_id": ObjectId(id)})
    flash('Employee removed.', 'info')
    return redirect(url_for('employees'))


# =======================
# REST API ROUTES (v1)
# =======================

@app.route('/api/v1/instruments', methods=['GET'])
def api_instruments():
    return jsonify([serialize_doc(i, for_api=True) for i in db.instruments.find()])

@app.route('/api/v1/customers', methods=['GET'])
def api_customers():
    return jsonify([serialize_doc(c, for_api=True) for c in db.customers.find()])

@app.route('/api/v1/transactions', methods=['GET'])
def api_transactions():
    return jsonify([serialize_doc(t, for_api=True) for t in db.transactions.find().sort("date", -1)])

@app.route('/api/v1/repairs', methods=['GET'])
def api_repairs():
    return jsonify([serialize_doc(r, for_api=True) for r in db.repairs.find()])

@app.route('/api/v1/dashboard', methods=['GET'])
def api_dashboard():
    stats = get_dashboard_stats()
    return jsonify({
        'total_revenue':    stats['total_revenue'],
        'net_profit':       stats['net_profit'],
        'instruments_sold': stats['instruments_sold'],
        'active_repairs':   stats['active_repairs'],
        'storage_mode':     STORAGE_MODE,
    })

@app.route('/api')
def api_explorer():
    return render_template('api_explorer.html')


# =======================
# RUN (direct invocation)
# =======================
if __name__ == '__main__':
    print(f"[OK] Seora Premium Music CRM — {STORAGE_MODE.upper()} mode")
    print("[OK] Running at http://127.0.0.1:3000/")
    app.run(debug=True, port=3000, host='0.0.0.0')
