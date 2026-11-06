import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from pathlib import Path
import sqlite3
import hashlib
import secrets
import html
import io
import json
import math
import re
from datetime import datetime, timezone

st.set_page_config(
    page_title="REVORA | Sustainable Reuse Marketplace",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).parent
DATA_PATH = BASE_DIR / "products.csv"
DB_PATH = BASE_DIR / "revora_marketplace.db"

CATEGORY_ICONS = {
    "Drinkware": "🚰",
    "Bags": "🛍️",
    "Food & drink": "☕",
    "Personal care": "🪥",
    "Home cleaning": "🧼",
    "Stationery": "📓",
    "Electronics": "🔌",
    "Clothing": "👕",
    "Food containers": "🍱",
    "Household": "🔋",
    "Clothing & shoes": "👟",
    "Books & education": "📚",
    "Home & kitchen": "🏡",
    "Toys & games": "🎲",
    "Sports & outdoors": "⚽",
    "Other": "✨",
}

BREAKEVEN_PROFILES = {
    "Drinkware": (25, 82, 18),
    "Bags": (45, 33, 8),
    "Food & drink": (20, 65, 14),
    "Personal care": (15, 45, 12),
    "Home cleaning": (12, 95, 35),
    "Stationery": (18, 50, 25),
    "Electronics": (30, 180, 45),
    "Clothing": (35, 220, 60),
    "Food containers": (22, 75, 22),
    "Household": (16, 110, 28),
}

RESIN_DECODER_DATA = {
    "♳ #1 PET / PETE (Polyethylene Terephthalate)": {
        "common_uses": "Disposable water bottles, soda bottles, clear condiment jars",
        "recyclability": "High (~55–70% municipal acceptance when clean and clear)",
        "risk": "Antimony & microplastic shedding when exposed to heat or repeated refilling",
        "verdict": "✅ Widely Recyclable (Single-Use Only)",
        "swap": "Food-grade 304 stainless steel or borosilicate glass bottle",
    },
    "♴ #2 HDPE (High-Density Polyethylene)": {
        "common_uses": "Shampoo bottles, detergent jugs, milk containers, cleaning triggers",
        "recyclability": "High (~60%+ acceptance in rigid container streams)",
        "risk": "Low leaching risk, but triggers/pumps contain mixed metal springs that jam recyclers",
        "verdict": "✅ Widely Recyclable",
        "swap": "Refillable glass/HDPE bottle using concentrated refill tablets or pouches",
    },
    "♵ #3 PVC / V (Polyvinyl Chloride)": {
        "common_uses": "Blister packs, cable insulation, synthetic leather, plumbing pipes",
        "recyclability": "Very Low (<3% recycled; contaminates PET/HDPE batches)",
        "risk": "Contains phthalates and releases toxic dioxins if incinerated",
        "verdict": "⚠️ Rarely Recyclable — Avoid Packaging",
        "swap": "Cardboard-only packaging, braided fabric cables, and natural canvas",
    },
    "♶ #4 LDPE (Low-Density Polyethylene)": {
        "common_uses": "Single-use shopping bags, bubble mailers, shrink wrap, squeezable tubes",
        "recyclability": "Low (~10%; flexible films tangle municipal sorting machinery)",
        "risk": "Fragments into persistent film microplastics in waterways",
        "verdict": "⚠️ Curbside Reject (Store Drop-Off Only)",
        "swap": "Washable organic cotton tote bags and all-paper honeycomb mailers",
    },
    "♷ #5 PP (Polypropylene)": {
        "common_uses": "Takeaway food containers, bottle caps, yogurt tubs, plastic straws",
        "recyclability": "Moderate (~30–40%; dark/black PP is often missed by optical sorters)",
        "risk": "Degrades and sheds microplastics when microwaved with oily foods",
        "verdict": "⚖️ Check Local Rules (Never Microwave)",
        "swap": "Stainless steel tiffin boxes or glass snap-lock meal containers",
    },
    "♸ #6 PS (Polystyrene / Styrofoam)": {
        "common_uses": "Disposable foam plates, coffee cup lids, protective foam blocks",
        "recyclability": "Extremely Low (<1% economically recovered)",
        "risk": "Styrene monomer leaching with hot liquids; breaks into wind-blown foam beads",
        "verdict": "🚫 Not Recyclable in Standard Streams",
        "swap": "Reusable stainless tumbler, ceramic tableware, or moulded pulp packaging",
    },
    "♹ #7 OTHER (PC, Bio-Plastics, Multi-Layer)": {
        "common_uses": "Snack pouches, bamboo-melamine composites, PLA cups, polycarbonate",
        "recyclability": "Virtually Zero in standard curbside bins",
        "risk": "PLA requires industrial composting (60°C+); multi-layer films cannot be separated",
        "verdict": "🚫 Landfill Bound Unless Industrially Certified",
        "swap": "Mono-material glass, metal, or home-compostable uncoated plant fiber",
    },
    "🗑️⚡ WEEE (Crossed-Out Wheeled Bin — E-Waste)": {
        "common_uses": "LED bulbs, charging cables, batteries, headphones, circuit boards",
        "recyclability": "High metal recovery ONLY at certified e-waste drop-off centers",
        "risk": "Lead, lithium, and mercury contaminate soil/groundwater and cause landfill fires",
        "verdict": "🔋 Mandatory E-Waste Hub Drop-Off",
        "swap": "Modular repairable electronics and rechargeable NiMH/Li-ion cells",
    },
}

# -------------------- Global State & Weights (DEFINED EARLY) --------------------

DEFAULT_WEIGHTS = {
    "material_score": 0.25,
    "lifecycle_score": 0.25,
    "packaging_score": 0.15,
    "usage_score": 0.20,
    "end_of_life_score": 0.15,
}
DISPLAY_NAMES = {
    "material_score": "Materials & sourcing",
    "lifecycle_score": "Durability & lifespan",
    "packaging_score": "Packaging",
    "usage_score": "Usage & reuse",
    "end_of_life_score": "Repair & end-of-life",
}

if "WEIGHTS" not in st.session_state:
    st.session_state["WEIGHTS"] = DEFAULT_WEIGHTS.copy()
WEIGHTS = st.session_state["WEIGHTS"]

# One-time branded splash screen for the first page load in this browser session.
if not st.session_state.get("revora_splash_seen", False):
    st.session_state["revora_splash_seen"] = True
    st.markdown("""
    <div class="revora-splash" aria-label="REVORA loading screen">
      <div class="splash-content">
        <svg class="revora-mark" viewBox="0 0 120 120" role="img" aria-label="REVORA leaf logo">
          <defs>
            <linearGradient id="revoraLeaf" x1="0" y1="1" x2="1" y2="0">
              <stop offset="0%" stop-color="#a8d977"/>
              <stop offset="100%" stop-color="#e0f5bd"/>
            </linearGradient>
          </defs>
          <circle cx="60" cy="60" r="55" fill="none" stroke="#477a54" stroke-width="2"/>
          <path d="M88 26C55 27 30 41 29 65c-1 16 11 27 25 25 24-3 34-31 34-64Z" fill="url(#revoraLeaf)"/>
          <path d="M28 94C43 73 59 57 82 39" fill="none" stroke="#f5ffe9" stroke-width="4" stroke-linecap="round"/>
          <path d="M49 70c-1-10-7-17-16-20M61 58c9 1 16 5 20 12" fill="none" stroke="#f5ffe9" stroke-width="3" stroke-linecap="round"/>
        </svg>
        <div class="splash-wordmark">REVORA</div>
        <div class="splash-tagline">RETHINK · REUSE · REVIVE</div>
        <div class="splash-loader"><span></span></div>
        <div class="splash-loading-text">Building a more circular tomorrow…</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

# -------------------- Marketplace & Ecosystem Database Setup --------------------

def db_connect():
    conn = sqlite3.connect(DB_PATH, timeout=20, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def hash_pin(pin):
    return hashlib.sha256(pin.encode("utf-8")).hexdigest()

def safe_text(value):
    return html.escape(str(value or ""))

def init_db():
    with db_connect() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            category TEXT NOT NULL,
            item_condition TEXT NOT NULL,
            location TEXT NOT NULL,
            description TEXT NOT NULL,
            donor_name TEXT NOT NULL,
            donor_contact TEXT NOT NULL,
            contact_type TEXT NOT NULL,
            pin_hash TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Available',
            listing_mode TEXT NOT NULL DEFAULT 'Permanent Donation',
            loan_days INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """)
        existing_cols = [r["name"] for r in conn.execute("PRAGMA table_info(items)").fetchall()]
        if "listing_mode" not in existing_cols:
            conn.execute("ALTER TABLE items ADD COLUMN listing_mode TEXT NOT NULL DEFAULT 'Permanent Donation'")
        if "loan_days" not in existing_cols:
            conn.execute("ALTER TABLE items ADD COLUMN loan_days INTEGER NOT NULL DEFAULT 0")

        conn.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            requester_name TEXT NOT NULL,
            requester_contact TEXT NOT NULL,
            message TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            created_at TEXT NOT NULL,
            FOREIGN KEY(item_id) REFERENCES items(id)
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS wishes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wish_name TEXT NOT NULL,
            category TEXT NOT NULL,
            location TEXT NOT NULL,
            description TEXT NOT NULL,
            requester_name TEXT NOT NULL,
            requester_contact TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Active',
            created_at TEXT NOT NULL
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS repair_hubs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hub_name TEXT NOT NULL,
            hub_type TEXT NOT NULL,
            city_area TEXT NOT NULL,
            services TEXT NOT NULL,
            contact_info TEXT NOT NULL,
            hours TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_items_status ON items(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_wishes_status ON wishes(status)")

        existing_hubs = conn.execute("SELECT COUNT(*) AS n FROM repair_hubs").fetchone()["n"]
        if existing_hubs == 0:
            default_hubs = [
                ("GreenCircuit E-Waste Drop-Off", "E-Waste Drop-Off", "Indiranagar, Bengaluru", "Certified collection for dead batteries, cables, circuit boards, and broken phones.", "+91 80-4112-9001", "Mon–Sat · 9:30 AM – 6:30 PM", now_iso()),
                ("FixIt Right Community Electronics Cafe", "Electronics Repair", "Yelahanka / Hennur, Bengaluru", "Soldering, headphone jack replacement, modular laptop upgrades, and multimeter diagnostics.", "+91 98450-11223", "Tue–Sun · 10:00 AM – 7:30 PM", now_iso()),
                ("Stitch & Revive Denim / Apparel Studio", "Tailor & Clothing Repair", "Jayanagar, Bengaluru", "Zipper replacement, darning, hem adjustments, and canvas bag reinforcement.", "+91 99001-44556", "Mon–Sat · 10:00 AM – 8:00 PM", now_iso()),
                ("Salem Circular E-Care & Battery Point", "E-Waste Drop-Off", "Fairlands, Salem", "Authorized e-waste bin for household LED bulbs, cells, chargers, and small appliances.", "+91 427-244-8899", "Mon–Sat · 9:00 AM – 6:00 PM", now_iso()),
                ("SoleMate Cobbler & Leather Craft", "Footwear & Bag Repair", "Koramangala, Bengaluru", "Backpack strap stitching, sole re-gluing, buckle hardware swaps, and conditioning.", "+91 97312-66778", "Daily · 9:30 AM – 8:30 PM", now_iso()),
                ("Campus Makerspace & Tool Library", "Appliance & Modular Fix", "College Tech Park / Innovation Lab", "Shared screwdrivers, 3D-printed spare knobs, glue guns, and peer repair mentoring.", "makerspace@campus.edu", "Mon–Fri · 1:00 PM – 5:30 PM", now_iso()),
            ]
            conn.executemany(
                "INSERT INTO repair_hubs (hub_name, hub_type, city_area, services, contact_info, hours, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                default_hubs,
            )

init_db()

def get_items(status=None, category=None, search_text=None, listing_mode=None):
    sql = "SELECT * FROM items"
    clauses, params = [], []
    if status and status != "All":
        clauses.append("status = ?"); params.append(status)
    if category and category != "All categories":
        clauses.append("category = ?"); params.append(category)
    if listing_mode and listing_mode != "All Modes":
        clauses.append("listing_mode = ?"); params.append(listing_mode)
    if search_text:
        clauses.append("(lower(item_name) LIKE ? OR lower(description) LIKE ? OR lower(location) LIKE ?)")
        term = f"%{search_text.lower()}%"
        params.extend([term, term, term])
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY created_at DESC"
    with db_connect() as conn:
        return conn.execute(sql, params).fetchall()

def get_item(item_id):
    with db_connect() as conn:
        return conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()

def get_requests_for_item(item_id):
    with db_connect() as conn:
        return conn.execute("SELECT * FROM requests WHERE item_id = ? ORDER BY created_at DESC", (item_id,)).fetchall()

def get_request_for_tracking(request_id, requester_contact):
    with db_connect() as conn:
        return conn.execute(
            """SELECT r.*, i.item_name, i.status AS item_status, i.donor_name, i.donor_contact, i.contact_type, i.location, i.listing_mode, i.loan_days
               FROM requests r JOIN items i ON i.id = r.item_id
               WHERE r.id = ? AND lower(r.requester_contact) = lower(?)""",
            (request_id, requester_contact.strip())
        ).fetchone()

def find_wish_matches_for_item(item_name, item_category, item_desc=""):
    with db_connect() as conn:
        wishes = conn.execute("SELECT * FROM wishes WHERE status='Active' ORDER BY created_at DESC").fetchall()
    tokens = {
        w for w in re.findall(r"[a-z0-9]+", f"{item_name} {item_desc}".lower())
        if len(w) >= 3 and w not in {"the", "and", "for", "with", "good", "used", "new", "item", "need", "want", "looking"}
    }
    matches = []
    for w in wishes:
        wish_tokens = set(re.findall(r"[a-z0-9]+", f"{w['wish_name']} {w['description']}".lower()))
        overlap = tokens.intersection(wish_tokens)
        cat_match = (w["category"] == item_category)
        if overlap or cat_match:
            score = len(overlap) * 35 + (25 if cat_match else 0)
            if score >= 25:
                matches.append((min(98, score), w, sorted(overlap)))
    matches.sort(key=lambda x: x[0], reverse=True)
    return matches[:4]

def compute_all_wish_item_matches():
    avail_items = get_items(status="Available")
    pairs = []
    for it in avail_items:
        m_list = find_wish_matches_for_item(it["item_name"], it["category"], it["description"])
        for score, w, overlap in m_list:
            pairs.append({
                "score": score,
                "item": it,
                "wish": w,
                "keywords": overlap,
            })
    pairs.sort(key=lambda x: x["score"], reverse=True)
    return pairs[:6]

def get_donor_badge(donated_count, listed_count):
    if donated_count >= 10:
        return "👑 REVORA Earth Legend", "#fef08a", "#713f12"
    if donated_count >= 5:
        return "🌳 Zero-Waste Champion", "#bbf7d0", "#14532d"
    if donated_count >= 2:
        return "🌿 Circular Guardian", "#dcecdf", "#174c31"
    if donated_count >= 1 or listed_count >= 1:
        return "🌱 Seedling Starter", "#e0f2fe", "#0c4a6e"
    return "✨ New Member", "#f3f4f6", "#374151"

def get_donor_leaderboard():
    with db_connect() as conn:
        rows = conn.execute("""
            SELECT donor_name,
                   COUNT(*) AS listed_count,
                   SUM(CASE WHEN status = 'Donated' THEN 1 ELSE 0 END) AS donated_count,
                   SUM(CASE WHEN listing_mode = 'Peer Lending (Borrow & Return)' THEN 1 ELSE 0 END) AS loan_count
            FROM items
            GROUP BY lower(donor_name)
            ORDER BY donated_count DESC, listed_count DESC
            LIMIT 12
        """).fetchall()
    return rows

def build_impact_certificate_html(person_name, rehomed_cnt, listed_cnt, loan_cnt):
    badge_title, _, _ = get_donor_badge(rehomed_cnt, listed_cnt)
    effective_actions = max(1, rehomed_cnt + loan_cnt) if (rehomed_cnt + listed_cnt + loan_cnt) > 0 else 1
    waste_kg = round(effective_actions * 1.5, 1)
    co2_kg = round(effective_actions * 4.2, 1)
    cert_hash = hashlib.sha256(f"REVORA-CERT-{person_name}-{rehomed_cnt}-{listed_cnt}".encode("utf-8")).hexdigest()[:10].upper()
    date_str = datetime.now().strftime("%d %B %Y")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>REVORA Certificate of Circular Impact - {safe_text(person_name)}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@600;700;800&family=Plus+Jakarta+Sans:wght@400;600;700&display=swap');
  body {{ font-family: 'Plus Jakarta Sans', sans-serif; background: #f4f8f4; margin: 0; padding: 24px; display: flex; justify-content: center; }}
  .cert {{ max-width: 760px; width: 100%; background: #ffffff; border: 8px double #1b6741; border-radius: 22px; padding: 36px 42px; box-sizing: border-box; text-align: center; box-shadow: 0 16px 40px rgba(16,42,29,0.12); position: relative; }}
  .eyebrow {{ color: #2e7a53; font-weight: 700; letter-spacing: 3px; font-size: 12px; text-transform: uppercase; }}
  h1 {{ font-family: 'Outfit', sans-serif; color: #102a1d; font-size: 32px; margin: 8px 0 4px; }}
  .sub {{ color: #5b6d61; font-size: 14px; margin-bottom: 20px; }}
  .recipient {{ font-family: 'Outfit', sans-serif; font-size: 28px; font-weight: 800; color: #1b6741; border-bottom: 2px solid #cce3d4; display: inline-block; padding: 4px 28px; margin: 8px 0 16px; }}
  .badge-pill {{ display: inline-block; background: #dcecdf; color: #13462b; padding: 6px 16px; border-radius: 999px; font-weight: 700; font-size: 14px; margin-bottom: 18px; }}
  .metrics {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 18px 0 24px; }}
  .m-box {{ background: #f4f8f4; border: 1px solid #d5e4d4; border-radius: 14px; padding: 12px 8px; }}
  .m-val {{ font-family: 'Outfit', sans-serif; font-size: 22px; font-weight: 800; color: #1b6741; }}
  .m-lbl {{ font-size: 11px; color: #5b6d61; font-weight: 600; margin-top: 2px; }}
  .footer {{ display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #e2ece2; padding-top: 14px; font-size: 12px; color: #5b6d61; margin-top: 12px; }}
  @media print {{ body {{ background: #fff; padding: 0; }} .no-print {{ display: none; }} }}
</style>
</head>
<body>
  <div class="cert">
    <div class="eyebrow">🌱 REVORA · WASTE-TO-DESIGN & COMMUNITY REUSE</div>
    <h1>Certificate of Circular Impact</h1>
    <div class="sub">Proudly presented for advancing neighborhood resource circularity and landfill diversion</div>
    <div class="recipient">{safe_text(person_name)}</div><br/>
    <div class="badge-pill">Earned Rank: {safe_text(badge_title)}</div>
    <p style="color:#2c4235;font-size:14px;max-width:580px;margin:0 auto 14px;line-height:1.5;">
      In recognition of active participation in the REVORA Circular Reuse Ecosystem—extending product lifecycles, sharing tools, and keeping valuable materials in community circulation.
    </p>
    <div class="metrics">
      <div class="m-box"><div class="m-val">{rehomed_cnt}</div><div class="m-lbl">Items Rehomed</div></div>
      <div class="m-box"><div class="m-val">{listed_cnt + loan_cnt}</div><div class="m-lbl">Listings & Loans</div></div>
      <div class="m-box"><div class="m-val">{waste_kg} kg</div><div class="m-lbl">Waste Diverted</div></div>
      <div class="m-box"><div class="m-val">{co2_kg} kg</div><div class="m-lbl">CO₂ Prevented</div></div>
    </div>
    <div class="footer">
      <span>📅 Issued: <b>{date_str}</b></span>
      <span>🔒 Verification ID: <b>REV-CERT-{cert_hash}</b></span>
      <span>🌍 <b>REVORA Platform</b></span>
    </div>
  </div>
</body>
</html>"""

def build_svg_handover_pass(item_id, request_id, item_name, location_text, status_text, listing_mode="Permanent Donation", loan_days=0):
    seed_str = f"REVORA-{item_id}-{request_id}-{item_name}"
    digest = hashlib.sha256(seed_str.encode("utf-8")).hexdigest().upper()
    pass_code = f"REV-PASS-{digest[:8]}"
    bits = bin(int(digest[:32], 16))[2:].zfill(128)

    grid_size = 11
    cell = 10
    cells_svg = ""
    bit_idx = 0
    for r in range(grid_size):
        for c in range(grid_size):
            in_tl = r < 3 and c < 3
            in_tr = r < 3 and c >= grid_size - 3
            in_bl = r >= grid_size - 3 and c < 3
            if in_tl or in_tr or in_bl:
                fill = "#174c31"
            else:
                fill = "#1b6741" if bits[bit_idx % len(bits)] == "1" else "#eaf4eb"
                bit_idx += 1
            cells_svg += f'<rect x="{10 + c * cell}" y="{10 + r * cell}" width="{cell - 1}" height="{cell - 1}" rx="2" fill="{fill}"/>'

    mode_badge = f"🔄 Tool Loan ({loan_days} Days)" if "Lending" in str(listing_mode) else "🎁 Permanent Donation"

    return f"""
    <div class="result-card" style="border:2px dashed #2e8b57;padding:1rem 1.2rem;margin-top:.6rem;">
        <div style="display:flex;flex-wrap:wrap;gap:16px;align-items:center;justify-content:space-between;">
            <div style="flex:1;min-width:200px;">
                <span class="pill">🎫 VERIFIED DIGITAL HANDOVER PASS · {safe_text(mode_badge)}</span>
                <h4 style="margin:.45rem 0 .2rem;">{safe_text(item_name)}</h4>
                <div class="muted">Listing: <b>REV-{int(item_id):05d}</b> · Request: <b>REV-R{int(request_id):05d}</b></div>
                <div class="muted">📍 Handover Zone: <b>{safe_text(location_text)}</b> · Status: <b>{safe_text(status_text)}</b></div>
                <div style="margin-top:8px;font-family:monospace;font-size:.95rem;font-weight:700;color:#1b6741;background:#eaf4eb;padding:4px 10px;border-radius:8px;display:inline-block;">
                    🔑 {pass_code}
                </div>
            </div>
            <div style="text-align:center;">
                <svg width="130" height="130" viewBox="0 0 130 130" style="background:#ffffff;border-radius:12px;border:1px solid #cce0cb;">
                    {cells_svg}
                </svg>
                <div class="muted" style="font-size:.72rem;margin-top:2px;">Verify code at pickup</div>
            </div>
        </div>
    </div>
    """

# -------------------- Sidebar Theme Customizer --------------------

with st.sidebar:
    st.markdown("## 🌱 REVORA")
    st.caption("Waste-to-Design & Circular Reuse")
    dark_mode = st.toggle("🌙 Midnight Forest Dark Mode", value=False, key="revora_dark_mode")
    st.markdown("---")
    st.markdown("**✨ Full Feature Suite**")
    st.write("🌿 **Explore** 105 product lifecycles")
    st.write("⚖️ **Calculate** Break-Even Reuse")
    st.write("♻️ **Decode** Plastic Resin Symbols")
    st.write("🤝 **Match** Wishes to Donations")
    st.write("🔄 **Borrow** from Peer Tool Library")
    st.write("📸 **Scan** condition & DIY Upcycle")
    st.write("🕵️‍♂️ **Detect** Greenwashing Claims")
    st.write("📜 **Export** Impact Certificates")
    st.write("🛠️ **Find** Local Repair & E-Waste Hubs")

    st.markdown("---")
    with st.expander("🎛️ Customize EcoScore Weights", expanded=False):
        st.caption("Adjust sliders to personalize how REVORA calculates EcoScores:")
        w_m = st.slider("Materials & sourcing", 0, 100, int(DEFAULT_WEIGHTS["material_score"]*100), 5, key="w_m")
        w_l = st.slider("Durability & lifespan", 0, 100, int(DEFAULT_WEIGHTS["lifecycle_score"]*100), 5, key="w_l")
        w_p = st.slider("Packaging impact", 0, 100, int(DEFAULT_WEIGHTS["packaging_score"]*100), 5, key="w_p")
        w_u = st.slider("Usage & reuse", 0, 100, int(DEFAULT_WEIGHTS["usage_score"]*100), 5, key="w_u")
        w_e = st.slider("Repair & end-of-life", 0, 100, int(DEFAULT_WEIGHTS["end_of_life_score"]*100), 5, key="w_e")
        total_w = max(1, w_m + w_l + w_p + w_u + w_e)
        st.session_state["WEIGHTS"] = {
            "material_score": w_m / total_w,
            "lifecycle_score": w_l / total_w,
            "packaging_score": w_p / total_w,
            "usage_score": w_u / total_w,
            "end_of_life_score": w_e / total_w,
        }
    WEIGHTS = st.session_state["WEIGHTS"]

    st.markdown("---")
    st.caption("Demo EcoScores are heuristic estimates, not verified lifecycle assessments.")
    st.caption("Arrange handovers in safe, public places.")

# -------------------- Dynamic Theme CSS --------------------

if dark_mode:
    theme_vars = """
        --bg-main: #0b1911;
        --bg-sidebar: linear-gradient(180deg, #0f2419 0%, #091710 100%);
        --card-bg: rgba(20, 43, 30, 0.88);
        --card-border: rgba(110, 190, 135, 0.22);
        --text-main: #ecfdf3;
        --text-body: #cce3d4;
        --text-muted: #93b5a0;
        --score-color: #7ee094;
        --pill-bg: linear-gradient(135deg, #1b4d31 0%, #256642 100%);
        --pill-text: #d9fbe5;
        --tab-bar-bg: rgba(16, 36, 25, 0.85);
        --tab-text: #b7d9c4;
        --track-bg: #1e3a2a;
        --note-bg: rgba(18, 40, 28, 0.92);
    """
else:
    theme_vars = """
        --bg-main: #f4f8f4;
        --bg-sidebar: linear-gradient(180deg, #e7f1e6 0%, #dbeadd 100%);
        --card-bg: rgba(255, 255, 255, 0.92);
        --card-border: rgba(27, 103, 65, 0.15);
        --text-main: #102a1d;
        --text-body: #2c4235;
        --text-muted: #5b6d61;
        --score-color: #1b6741;
        --pill-bg: linear-gradient(135deg, #dcecdf 0%, #c8e4ce 100%);
        --pill-text: #13462b;
        --tab-bar-bg: rgba(255, 255, 255, 0.82);
        --tab-text: #264c38;
        --track-bg: #e6efe6;
        --note-bg: rgba(255, 255, 255, 0.92);
    """

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@500;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

    :root {{ {theme_vars} }}

    html, body, [class*="css"] {{ font-family: 'Plus Jakarta Sans', sans-serif; color: var(--text-main); }}
    h1, h2, h3, h4, .splash-wordmark {{ font-family: 'Outfit', sans-serif !important; color: var(--text-main); }}
    p, li, label, .stMarkdown {{ color: var(--text-body); }}

    .stApp {{
        background-color: var(--bg-main);
        background-image:
            radial-gradient(at 12% 10%, rgba(168, 217, 119, 0.16) 0px, transparent 48%),
            radial-gradient(at 88% 15%, rgba(35, 102, 71, 0.14) 0px, transparent 50%),
            radial-gradient(at 50% 90%, rgba(181, 229, 140, 0.14) 0px, transparent 55%);
    }}

    .revora-splash {{
        position: fixed; inset: 0; z-index: 999999; display: flex;
        align-items: center; justify-content: center; text-align: center;
        background: radial-gradient(circle at 50% 35%, #1f573b 0%, #103523 52%, #081c13 100%);
        color: #f4ffe9; animation: revoraSplashFade 2.8s ease forwards;
        pointer-events: none;
    }}
    .splash-content {{ display:flex; flex-direction:column; align-items:center; padding:24px; animation: revoraRise .8s ease both; }}
    .revora-mark {{ width:112px; height:112px; filter: drop-shadow(0 0 22px #80bf7966); animation: revoraPulse 1.5s ease-in-out infinite; }}
    .splash-wordmark {{ margin-top:18px; font-size:clamp(2.6rem, 7vw, 4.5rem); font-weight:800; letter-spacing:.22em; padding-left:.22em; color:#f4ffe9 !important; }}
    .splash-tagline {{ margin-top:5px; color:#b9d9b8; font-size:.78rem; letter-spacing:.24em; }}
    .splash-loader {{ width:180px; height:3px; margin-top:30px; overflow:hidden; background:#ffffff24; border-radius:10px; }}
    .splash-loader span {{ display:block; width:40%; height:100%; border-radius:10px; background:#b5e58c; animation: revoraLoad 1.2s ease-in-out infinite; }}
    .splash-loading-text {{ margin-top:13px; color:#c8ddca; font-size:.85rem; }}
    @keyframes revoraSplashFade {{ 0%,72% {{ opacity:1; visibility:visible; }} 100% {{ opacity:0; visibility:hidden; }} }}
    @keyframes revoraPulse {{ 0%,100% {{ transform:scale(1); }} 50% {{ transform:scale(1.06); }} }}
    @keyframes revoraLoad {{ 0% {{ transform:translateX(-110%); }} 100% {{ transform:translateX(360%); }} }}
    @keyframes revoraRise {{ from {{ opacity:0; transform:translateY(12px); }} to {{ opacity:1; transform:translateY(0); }} }}

    [data-testid="stSidebar"] {{ background: var(--bg-sidebar); border-right: 1px solid var(--card-border); }}

    .hero {{
        position: relative; overflow: hidden; padding: 2.2rem 2.4rem; border-radius: 26px;
        background: linear-gradient(125deg, #0d2e20 0%, #1b563b 48%, #2e7a53 100%);
        color: white; margin-bottom: 1.4rem; box-shadow: 0 20px 42px -15px rgba(18, 59, 43, 0.38);
        border: 1px solid rgba(255, 255, 255, 0.14);
    }}
    .hero h1 {{ color: white !important; font-size: clamp(2.4rem, 4.5vw, 3.4rem); font-weight: 800; margin: 0.25rem 0 0; letter-spacing: -1px; }}
    .hero p {{ color: #e3f3e7 !important; font-size: 1.08rem; margin: .35rem 0 0; max-width: 720px; }}
    .hero-badges {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 1.15rem; }}
    .hero-badge {{
        background: rgba(255, 255, 255, 0.12); backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.22); color: #f4ffe9;
        padding: 0.38rem 0.85rem; border-radius: 999px; font-size: 0.82rem; font-weight: 600;
    }}

    .pill {{ display: inline-block; padding: .3rem .75rem; border-radius: 999px; background: var(--pill-bg); color: var(--pill-text); font-size: .8rem; font-weight: 700; }}

    .result-card {{
        border: 1px solid var(--card-border); border-radius: 20px; padding: 1.3rem 1.35rem;
        background: var(--card-bg); backdrop-filter: blur(10px); height: 100%; margin-bottom: 0.65rem;
        box-shadow: 0 8px 22px -8px rgba(0, 0, 0, 0.12);
        transition: transform 0.24s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.24s ease, border-color 0.24s ease;
    }}
    .result-card:hover {{ transform: translateY(-5px); box-shadow: 0 18px 34px -10px rgba(27, 103, 65, 0.25); border-color: #4f9369; }}
    .muted {{ color: var(--text-muted) !important; font-size: .88rem; font-weight: 500; }}
    .big-score {{ font-size: 2.1rem; font-weight: 800; color: var(--score-color); font-family: 'Outfit', sans-serif; }}

    .eco-bar-track {{ width: 100%; height: 7px; background: var(--track-bg); border-radius: 999px; overflow: hidden; margin: 8px 0 12px; }}
    .eco-bar-fill {{ height: 100%; border-radius: 999px; transition: width 0.4s ease; }}

    div[data-baseweb="tab-list"] {{
        gap: 6px; background: var(--tab-bar-bg); backdrop-filter: blur(10px);
        padding: 8px 10px; border-radius: 18px; border: 1px solid var(--card-border); margin-bottom: 1rem;
        flex-wrap: wrap;
    }}
    button[data-baseweb="tab"] {{ border-radius: 12px !important; padding: 8px 14px !important; font-weight: 600 !important; color: var(--tab-text) !important; }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        background: linear-gradient(135deg, #1b6741 0%, #2d8659 100%) !important; color: #ffffff !important;
        box-shadow: 0 4px 12px rgba(27, 103, 65, 0.28) !important;
    }}
    div[data-baseweb="tab-highlight"] {{ display: none !important; }}
    div[data-testid="stMetric"] {{ background: var(--card-bg); border: 1px solid var(--card-border); padding: 14px 18px; border-radius: 18px; }}
    .marketplace-note {{ border: 1px solid var(--card-border); border-left: 5px solid #2e8b57; border-radius: 16px; padding: 1rem 1.2rem; background: var(--note-bg); margin: .5rem 0 1.1rem; }}
</style>
""", unsafe_allow_html=True)

# -------------------- 105-Product Embedded Fallback Dataset --------------------

_FALLBACK_PRODUCTS_CSV = '''product_id,product_name,category,material,packaging,description,waste_risk,design_opportunity,tradeoff,material_score,lifecycle_score,packaging_score,usage_score,end_of_life_score
1,Disposable PET water bottle,Drinkware,PET plastic,Single-use plastic bottle,Convenient single-use water container,Repeated single-use packaging,Refill from safe drinking water or use a durable bottle,Reusable alternatives require repeated use and cleaning,35,25,20,25,35
2,Reusable stainless steel bottle,Drinkware,Stainless steel,Minimal cardboard box,Durable bottle designed for repeated daily hydration,Can be underused or lost if not carried daily,Use consistently for hundreds of refill cycles,Higher initial manufacturing footprint requires long use,65,85,80,90,65
3,Reusable borosilicate glass bottle,Drinkware,Borosilicate glass and silicone sleeve,Recycled cardboard box,Pure taste reusable bottle for home or desk use,Breakage can shorten functional lifespan,Use in low-impact settings and protect with silicone sleeve,Heavier transport weight and drop fragility,70,70,75,80,70
4,Single-use plastic shopping bag,Bags,Thin LDPE plastic film,None,Lightweight grocery carrier bag,Often discarded after a single trip and tangles sorting machines,Reuse existing bags and refuse thin single-use film bags,Reusable totes require many trips to offset production,25,20,30,25,25
5,Reusable organic cotton tote,Bags,Unbleached organic cotton,Paper tag,Washable multi-purpose shopping bag,Accumulating too many unused tote bags in drawers,Keep two bags handy and reuse weekly for years,Cotton cultivation is water and land intensive,55,75,75,80,60
6,Recycled-content kraft paper bag,Bags,Post-consumer recycled kraft paper,None,Paper carrier with high recycled fiber content,Tears easily when wet or overloaded,Reuse as a bin liner or gift wrap before paper recycling,Higher pulp energy footprint than thin film if used once,70,45,65,50,75
7,Disposable lined coffee cup,Food & drink,Paperboard with PE plastic lining,Stack sleeve,Takeaway hot beverage cup used for one drink,Plastic lining prevents standard paper mill pulping,Bring a personal tumbler or choose dine-in ceramic mugs,Washing reusable cups uses hot water and soap,45,20,20,25,35
8,Insulated reusable coffee tumbler,Food & drink,Double-wall stainless steel,Cardboard sleeve,Vacuum-insulated cup for takeaway drinks,Forgotten at home or lid seal wears out,Store near keys and choose brands selling replacement seals,Requires 20 to 30 uses to break even on steel production,65,80,75,85,60
9,Conventional plastic toothbrush,Personal care,Virgin polypropylene and nylon bristles,Plastic blister pack,Standard manual toothbrush replaced every three months,Entire heavy plastic handle is landfilled four times a year,Switch to replaceable-head or compostable bamboo handles,Mixed plastic and nylon cannot be curbside recycled,35,45,45,55,30
10,Replaceable-head manual toothbrush,Personal care,Aluminum or bio-plastic handle with snap head,Compact paper box,Reusable handle where only the bristle head is swapped,Replacement heads still generate small mixed waste,Keep handle for years and snap in compatible refill heads,Must verify long-term availability of refill heads,60,75,70,80,55
11,Disposable trigger spray cleaner,Home cleaning,HDPE bottle with mixed-material trigger,Shrink label,Ready-to-use liquid surface cleaner,Metal spring inside trigger ruins plastic recycling and ships 95% water,Reuse the trigger sprayer with concentrated refill tablets,Concentrates require accurate home dilution,35,50,25,45,35
12,Refillable glass spray bottle with tablets,Home cleaning,Tempered glass and reusable trigger,Compostable tablet wrapper,Permanent spray bottle paired with dissolvable cleaning tabs,Drop hazard on tile floors if protective base is removed,Dissolve compact tablets in tap water to eliminate bottle shipping,Glass bottle has higher initial embodied energy,55,75,65,80,55
13,Standard wire-bound notebook,Stationery,Bleached paper and PVC-coated wire,Plastic shrink wrap,Spiral-bound notebook for lectures and notes,Partially used notebooks are discarded and wire blocks recycling,Fill all pages on both sides and remove wire before recycling,Spiral binding is convenient but complicates pulping,65,55,70,65,65
14,Refillable disc-bound or ring notebook,Stationery,Recycled poly cover and loose-leaf paper,Paper band,Modular notebook allowing pages to be added and rearranged,Loose refill packs may still come in plastic film,Buy recycled paper refills and archive completed subject sheets,Binder mechanism only pays off if cover is kept for years,60,80,75,85,65
15,Non-repairable moulded charging cable,Electronics,PVC jacket and copper wire,Blister pack,Standard USB charging cord with fixed strain relief,Fraying near the connector forces disposal of the whole copper cord,Use spring strain-relief protectors or modular magnetic cables,Cheap cables fail rapidly and create hazardous e-waste,40,30,45,70,25
16,Modular repairable braided USB cable,Electronics,Recycled nylon braid and screw-fit connectors,Kraft box,Durable cable designed with replaceable terminal heads,Higher upfront cost and slightly bulker connector housing,Swap only the worn connector tip instead of the entire wire,Requires basic precision screwdriver for module swaps,60,80,75,85,65
17,Fast-fashion polyester t-shirt,Clothing,Virgin polyester knit,Polybag mailer,Low-cost synthetic graphic shirt,Sheds microfibers in laundry and loses shape after a few washes,Wash in a microfiber filter bag and buy durable natural fibers,Synthetic blends are nearly impossible to textile-recycle,35,40,35,45,30
18,Heavyweight repairable cotton shirt,Clothing,Organic combed cotton,Paper twine tag,Classic-fit garment built with reinforced seams for multi-year wear,Can still be discarded early due to staining or fit changes,Mend small tears and over-dye faded fabric to extend wear life,Higher upfront price and water footprint during farming,55,75,70,85,50
19,Single-use black plastic meal box,Food containers,Polypropylene with carbon black pigment,Plastic bag,Takeaway restaurant container used for a single meal,Optical recycling sorters cannot detect carbon-black plastic,Request stainless tiffin pickup or reuse clean tubs for storage,Reusable containers require carrying and washing,30,25,20,30,30
20,Stainless steel leak-proof tiffin box,Food containers,304 food-grade stainless steel and silicone ring,Cardboard box,Multi-tier or latch meal container built for decades of lunches,Silicone gasket can loosen if stretched during washing,Keep spare gasket rings and use daily for campus or office meals,Cannot be used in microwave ovens,65,85,80,90,70
21,Single-use alkaline AA batteries,Household,Zinc manganese dioxide and steel casing,Plastic blister card,Primary non-rechargeable cells for remotes and gadgets,Frequent purchases and toxic heavy metal leakage if landfilled,Replace with low-self-discharge NiMH rechargeables in active devices,Alkalines have lower upfront cost for emergency flashlights,40,40,50,45,35
22,Rechargeable NiMH battery set,Household,Nickel-metal hydride chemistry,Recycled pulp carton,Cells rated for 500 to 1000 recharge cycles,Underutilization if left idle in drawers without a smart charger,Pair with an auto-cutoff smart charger and rotate across devices,Higher initial purchase cost and requires e-waste drop-off at end of life,55,80,70,85,55
23,Plastic-wrapped liquid body wash,Personal care,HDPE bottle and dispensing pump,Plastic shrink seal,Liquid soap consisting mostly of water in heavy plastic,Pump springs prevent recycling and bottles accumulate rapidly,Switch to unpackaged bar soap or bulk refill stations,Liquid soap is convenient for shared gym showers,55,60,35,70,55
24,Paper-wrapped cold-process soap bar,Personal care,Saponified plant oils and recycled paper,Uncoated paper band,Concentrated solid cleansing bar with zero plastic waste,Mushy bar wear if left sitting in standing water,Store on a slotted draining dish to double bar longevity,Some hard-water areas leave soap scum with natural bars,60,60,75,70,65
25,Fast-fashion stretch denim jeans,Clothing,Cotton and elastane synthetic blend,Plastic tag and polybag,Trend-cut jeans with synthetic stretch fibers,Elastane ruins cotton fiber recycling and heavy dye pollutes water,Air out between wears and wash cold to preserve fiber elasticity,Stretch comfort comes at the cost of end-of-life recyclability,45,60,70,75,40
26,Thrifted 100% cotton vintage denim,Clothing,Pre-owned cotton denim,Minimal thrift tag,Secondhand heavyweight jeans with zero new manufacturing impact,Crotch or hem wear may require basic tailor darning,Reinforce high-wear seams at a local tailor to wear for another decade,Finding exact sizing in secondhand markets takes patience,90,85,90,95,85
27,Disposable plastic twin-blade razor,Personal care,Polystyrene handle and steel strips,Blister pack,Single-piece shaving razor discarded after a few shaves,Fused plastic and sharp steel cannot be separated for recycling,Switch to a lifetime brass or stainless safety razor,Extremely cheap upfront but costly and wasteful over a year,20,30,25,30,20
28,Solid metal double-edge safety razor,Personal care,Chromed brass or stainless steel,Cardboard box,Lifetime shaving handle using recyclable bare steel blades,Blades require safe storage in a metal blade bank before recycling,Collect used blades in a sealed tin for scrap metal recovery,Requires a gentle angle and short learning curve,85,95,90,90,95
29,Glued wired over-ear headphones,Electronics,ABS plastic copper and PU leather,Plastic window box,Budget audio headphones with non-removable cord and pads,Flaking ear pads or a tugged wire ruins the whole headset,Choose headsets with standard 3.5mm jacks and snap-on cushions,Glued enclosures make DIY soldering repairs difficult,45,60,60,75,45
30,Modular repairable studio headphones,Electronics,Aluminum spring steel and replaceable modules,Recycled pulp box,Headphones engineered with plug-in cables and twist-lock ear pads,Higher initial price for precision modular connectors,Replace worn ear cushions or audio cords in seconds without tools,Slightly heavier frame due to metal fasteners,75,90,85,90,85
31,Wax-coated disposable paper plates,Food containers,Bleached paperboard with wax or PE film,Plastic shrink wrap,Single-use party plates discarded after one meal,Food grease and plastic coating contaminate paper recycling bins,Keep a stack of lightweight steel or melamine plates for events,Requires dishwashing after group gatherings,35,15,25,30,25
32,Bamboo travel cutlery set,Food & drink,Moso bamboo and cotton roll pouch,Paper tag,Lightweight spoon fork and chopsticks for lunch bags,Bamboo can split if soaked in boiling water or dishwashers,Hand wash promptly and rub with food-safe oil every few months,Slightly thicker mouthfeel than thin metal cutlery,80,70,85,85,85
33,Single-use plastic wet wipes,Personal care,Polyester and polypropylene non-woven fibers,Foil-lined plastic flow pack,Moistened cleansing cloths marketed for quick cleanup,Shed microplastics and cause massive sewer fatbergs when flushed,Use washable cotton flannel cloths with a small water spritzer,Washable cloths require laundry bag washing,15,10,20,20,10
34,Washable organic cotton face rounds,Personal care,Two-ply organic cotton flannel,Cotton mesh laundry bag,Reusable pads for toner and makeup removal,Small rounds can get lost inside washing machine seals,Always zip rounds inside the mesh laundry bag before washing,Requires air drying to prevent shrinkage,85,80,85,90,80
35,Synthetic polyurethane kitchen sponge,Home cleaning,Polyurethane foam and nylon scouring pad,Cellophane wrap,Two-sided dish scrubber replaced every few weeks,Nylon green pad sheds microplastics directly into sink drains,Switch to plant cellulose sponges and coconut coir scrubbers,Synthetic foam is cheap but non-recyclable and fossil-derived,25,30,35,40,20
36,Compostable loofah and coir dish scrubber,Home cleaning,Dried Luffa aegyptiaca plant fiber,Paper belly band,Zero-plastic plant sponge that expands when wet,Wears down faster on cast iron than metal chainmail,Boil weekly to sanitize and cut into pieces for home compost at end of life,Slightly stiffer texture until softened in warm water,95,65,90,80,95
37,Standard potted LED light bulb,Household,Polycarbonate diffuser aluminum and potted driver,Cardboard carton,Energy-saving household lamp with sealed base,Capacitor failure kills the bulb while the LED chips are still good,Use in ventilated fixtures and drop dead bulbs at e-waste bins,Potted resin prevents component-level repair,60,70,75,85,50
38,Modular replaceable-driver LED bulb,Household,Aluminum heatsink and snap-in driver module,Recycled kraft box,Circular light bulb where the electronic driver clicks out for swap,Limited retail availability outside circular design brands,Replace only the failed driver module while keeping the heatsink,Higher upfront cost per luminaire,75,85,85,90,80
39,Plastic-lined paper bubble mailer,Bags,Kraft paper bonded to LDPE bubble film,Peel-and-seal strip,Padded shipping envelope for e-commerce orders,Fused plastic bubble lining makes neither material recyclable,Reuse intact mailers for outbound parcels by taping over the flap,Lightweight postage but guaranteed landfill waste,20,15,30,30,15
40,All-paper honeycomb padded mailer,Bags,FSC kraft paper with expandable honeycomb core,Water-activated paper tape,100% paper protective shipping envelope,Slightly thicker wall profile and vulnerable to heavy rain,Flatten and place directly in curbside paper recycling after reuse,Slightly heavier than air-filled plastic film,85,60,85,75,90
41,Brittle polypropylene ice cube tray,Home cleaning,Rigid polypropylene plastic,Polybag sleeve,Freezer tray that twists to release ice cubes,Plastic embrittles at sub-zero temperatures and snaps within a year,Upgrade to food-grade silicone or lever-release stainless steel,Low upfront price leads to repeated replacement cycles,40,50,60,70,45
42,Stainless steel lever ice cube tray,Home cleaning,18/8 stainless steel,Kraft box,Lifetime metal freezer tray with mechanical ice-crack lever,Metal handle feels very cold to bare hands straight from freezer,Freeze faster due to metal conductivity and keep for decades,Higher upfront investment than moulded plastic,90,95,90,90,95
43,Recycled copper insulated bottle,Drinkware,Pure copper with lacquer-free interior,Jute pouch,Ayurvedic-inspired durable water vessel for room-temperature storage,Acidic juices react with bare copper if misused,Use strictly for plain water and polish naturally with lemon and salt,Not insulated for hot coffee or boiling liquids,80,90,85,85,90
44,Collapsible food-grade silicone cup,Drinkware,Platinum-cured silicone and PP rim,Small paper box,Pocket-sized folding cup for commuters and hikers,Silicone can retain strong coffee aromas over time,Soak in baking soda solution monthly to refresh silicone,Requires a rigid grip ring to prevent squeezing spills,70,80,80,85,65
45,Single-use polystyrene foam cup,Drinkware,Expanded polystyrene #6 foam,Plastic sleeve stack,Insulated disposable cup for street tea and coffee,Breaks into wind-blown foam beads that never biodegrade,Carry a pocket steel tumbler or request clay kulhad cups,Zero washing needed but severe ecological persistence,10,10,15,15,10
46,Double-wall ceramic travel mug,Drinkware,Kiln-fired ceramic and silicone press lid,Cardboard cylinder,Reusable mug offering cafe ceramic feel on the go,Dropping on pavement shatters the ceramic body,Use for desk and car commutes rather than rugged trekking,Heavier and more fragile than stainless steel,75,70,80,80,75
47,Plant-based PLA cold drink cup,Drinkware,Polylactic acid corn bio-resin,Bio-film sleeve,Clear cup marketed as biodegradable plastic,Requires 60C industrial composting and contaminates PET recycling,Use washable tumblers instead of single-use bio-plastics,Looks identical to PET so consumers sort it into the wrong bin,40,20,35,25,30
48,Titan-grade ultralight camping mug,Drinkware,Grade-1 titanium,Mesh storage sack,Corrosion-proof lifetime mug for outdoor and hostel use,High smelting energy footprint if only used once a year,Use daily at home as well as on treks to maximize utility,Expensive raw material refinement,75,95,85,90,90
49,Upcycled sailcloth or banner backpack,Bags,Reclaimed PVC billboard or Dacron sailcloth,None,Weatherproof commuter pack cut from diverted event banners,Heavy duty stitching or zipper sliders may wear first,Lubricate zippers and repair sliders at a local cobbler,Each bag has unique graphics and stiffer drape,90,85,95,90,75
50,Jute burlap market sack,Bags,Natural golden jute bast fiber,Cotton string tie,Breathable heavy-duty sack for vegetables and grains,Coarse fibers can shed lint and absorb spills if wet,Shake out dry soil and line with a washable cotton cloth,Cannot be machine washed on harsh cycles,85,75,90,80,90
51,Virgin nylon drawstring gym bag,Bags,Thin 210D virgin nylon and polyester cord,Polybag,Promotional event cinch sack,Thin corners rip around metal grommets within months,Reinforce corner grommets with fabric patches or use canvas totes,Petrochemical fabric with low tear resistance,30,35,30,45,25
52,Waxed canvas messenger bag,Bags,Heavy cotton duck and beeswax coating,Paper hangtag,Water-resistant laptop and book bag that ages with patina,Wax coating thins out at crease lines over years of rain,Re-rub with a beeswax block every two years for lifetime waterproofing,Heavier empty weight than synthetic nylon packs,80,90,85,90,85
53,Washable organic cotton produce mesh bags,Bags,Unbleached organic cotton net,Recycled paper band,Lightweight drawstring sacks replacing supermarket plastic produce rolls,Drawstring cord can tangle in washing machines,Tie cords in a knot before cold washing and air dry flat,Tare weight is slightly higher at checkout scales,85,85,90,90,85
54,Single-use metallized snack pouch,Food & drink,Multi-layer BOPP plastic and aluminum vapor coat,Carton case,Shiny chip and namkeen wrapper,Fused plastic and micron-thin metal cannot be separated by recyclers,Buy dry snacks in bulk jars or return clean multi-layer wrappers to collection drives,Superior moisture barrier but zero curbside recyclability,15,15,15,20,10
55,Permanent stainless steel coffee filter,Food & drink,Fine-mesh 304 stainless steel,Small kraft box,Cone drip filter replacing thousands of paper filters,Fine coffee oils can clog micro-mesh holes over time,Simmer in water and vinegar every month to descale micro-pores,Lets more natural coffee oils through than bleached paper,85,95,90,95,90
56,Single-use plastic boba and juice straw,Food & drink,Virgin polypropylene #5,Paper or film wrapper,Disposable drinking tube used for 15 minutes,Too light and narrow for mechanical recycling screens,Carry a wide-bore steel or glass straw with a cleaning brush,Convenient for thick drinks but high marine litter risk,15,10,20,15,15
57,Borosilicate glass and steel straw kit,Food & drink,304 steel and tempered glass with sisal brush,Cotton pouch,Reusable drinking straws for smoothies and iced coffee,Uncleaned residue inside tube if brushed infrequently,Rinse immediately after smoothies and use the sisal bristle brush,Glass variant can chip if dropped on granite counters,80,85,85,85,85
58,Aluminum beverage can,Food & drink,Recycled and virgin aluminum alloy with thin epoxy liner,Cardboard six-pack holder,Chilled beverage container with high scrap value,Crushed cans littered outdoors or mixed with food waste,Empty completely and place in dry metal recycling for infinite smelting,Requires bauxite mining if not recovered in closed loop,75,45,70,40,90
59,Returnable glass milk or soda bottle,Food & drink,Thick soda-lime flint glass,Reusable plastic crate,Deposit-return bottle sanitized and refilled up to 40 times,Broken or unreturned bottles negate the heavy glass footprint,Always return empty bottles to the dairy or vendor crate promptly,Heavy local transport weight requires short delivery loops,85,90,95,95,90
60,Bamboo handle toothbrush,Personal care,Moso bamboo handle and castor-oil nylon bristles,Kraft paper box,Compostable-handle toothbrush reducing plastic bathroom waste,Mold on handle base if kept inside a wet enclosed toothbrush cup,Air dry upright and snap off bristle head with pliers before composting handle,Bristles still require separate disposal in most regions,80,65,90,75,80
61,Refillable silk dental floss in glass dispenser,Personal care,Ahimsa silk or corn PLA floss in glass vial,Paper refill box,Zero-plastic tooth flossing dispenser with metal cutter lid,Losing the small glass dispenser before finishing refills,Keep dispenser in bathroom cabinet and buy 2-pack spool refills,Natural silk floss is slightly thicker between tight teeth,80,85,85,85,85
62,Concentrated solid shampoo bar,Personal care,Syndet coconut surfactants and plant butters,Recycled paperboard box,Waterless hair cleanser equivalent to two 250ml plastic bottles,Softens rapidly if left under direct shower spray,Cut bar in half and store on a dry cedar soap deck outside spray,Adjustment period for hair used to heavy silicone liquids,85,80,95,85,95
63,Medical-grade silicone menstrual cup,Personal care,Platinum-cured medical silicone,Unbleached cotton pouch,Reusable period care device lasting up to 10 years,Improper sizing or boiling in an unattended pot can damage silicone,Sterilize in a dedicated mug with boiling water between cycles,Replaces over 2400 single-use plastic-lined pads or tampons,90,95,90,95,80
64,Washable bamboo-cotton charcoal pads,Personal care,Organic cotton bamboo fleece and PUL waterproof layer,Paper band,Snap-on reusable sanitary pads for 3 to 5 years of use,Hot dryer heat degrades the thin waterproof PUL backing,Soak in cold water first before washing and line dry in sunlight,Requires cold-water soaking and laundry routine,85,85,90,90,75
65,Aluminum tube toothpaste with metal key,Personal care,Pure aluminum collapsible tube and PP cap,Paperboard carton,Recyclable metal paste tube replacing multi-layer plastic laminate tubes,Rolling without a key leaves 15% of paste trapped in corners,Use a reusable metal tube-wringer key to extract every drop before metal recycling,Cap is still small plastic that must be separated,75,70,80,80,85
66,Concentrated laundry detergent sheets,Home cleaning,PVA water-soluble film and plant surfactants,Flat cardboard envelope,Pre-measured featherweight laundry strips with zero plastic jug waste,Moisture in humid bathrooms can fuse sheets together,Store envelope in a dry tin and tear half-sheets for small loads,Cuts shipping weight by 90% compared to liquid jugs,80,75,95,85,85
67,Swedish cellulose dishcloth,Home cleaning,70% FSC wood cellulose and 30% cotton fiber,Paper label,Super-absorbent washable sponge cloth replacing 15 paper towel rolls,Stiffens when dry and tears if wrung aggressively while brittle,Wet before flexing and boil or top-rack wash weekly to sanitize,Home compostable once worn out after 6 to 9 months,90,80,90,90,95
68,Organic New Zealand wool dryer balls,Home cleaning,100% felted sheep wool,Cotton drawstring bag,Reusable laundry tumblers that shorten drying time and replace chemical sheets,Over-drying can cause static if removed too late,Add two drops of essential oil and recharge wool in sunlight monthly,Lasts for over 1000 laundry loads with zero synthetic film waste,90,95,90,95,95
69,Coconut coir bottle and pan brush,Home cleaning,Untreated coconut husk bristles and galvanized wire handle,Paper tag,Stiff natural bristle scrubber made from agricultural husk waste,Wooden handle end can crack if left submerged in sink water,Hang by the wire loop to air dry after scrubbing pots,Wire core is recyclable steel while bristles biodegrade,90,75,95,85,90
70,Concentrated floor cleaner refill pod,Home cleaning,Water-soluble film pod or glass ampoule,Small paper box,Ultra-concentrated mopping solution diluted in an existing bucket,Over-dosing if mixed without measuring water volume,Drop one pod into a 4-liter reusable bottle and shake gently,Eliminates heavy 2-liter HDPE floor cleaner bottles,80,80,90,85,85
71,Refillable aluminum fountain pen,Stationery,Anodized aluminum body and steel nib,Tin or cardboard case,Precision writing instrument filled from bottled ink via converter,Ink dries in nib feed if left uncapped or unused for months,Flush nib with lukewarm water every two months and use bottled ink,Eliminates hundreds of disposable plastic ballpoint barrels,85,95,85,95,90
72,Plantable seed paper woodless pencil,Stationery,Recycled compressed newspaper and graphite core with seed capsule,Kraft sleeve,Pencil rolled from waste paper that sprouts herbs when the stub is planted,Chewing the end ruins the gelatin seed capsule,Sharpen gently and plant the final 3cm stub in moist potting soil,Slightly softer outer barrel than cedar wood if soaked,90,70,95,80,95
73,Refillable glass-body whiteboard marker,Stationery,Glass barrel replaceable felt nib and liquid ink dropper,Recycled cardboard box,Classroom and seminar marker designed for 50+ ink refills,Felt tip frays if pressed too hard on rough boards,Refill with 5 drops of pigment ink and swap the felt nib when worn,Prevents thousands of dry PP marker tubes in colleges,85,90,85,90,85
74,100% post-consumer recycled A4 printer paper,Stationery,De-inked post-consumer waste paper bleached without chlorine,Paper ream wrapper,Uncoated archival sheet paper for academic reports and notes,Single-sided printing wastes 50% of fiber capacity,Set default printer settings to duplex double-sided mode and draft quality,Slightly warmer off-white shade than virgin tree pulp paper,85,65,85,75,90
75,Solid brass mechanical drafting pencil,Stationery,Machined brass barrel and steel clutch mechanism,Kraft tube,Weighted engineering drawing pencil built to last an entire career,Thin 0.5mm lead snaps if drop-shocked onto concrete,Use replaceable eraser plugs and standard graphite lead tubes,Zero plastic waste across decades of CAED and engineering studio work,85,95,90,95,95
76,High-efficiency GaN multi-port USB-C charger,Electronics,Gallium nitride semiconductors and recycled PC shell,Paperboard box,Compact 65W charger that powers both laptop and phone simultaneously,Buying separate bricks for every gadget multiplies e-waste,Consolidate laptop tablet and phone charging into one GaN brick with detachable cables,Higher component density requires certified e-waste recovery at end of life,70,85,85,95,70
77,User-repairable modular smartphone concept,Electronics,Recycled aluminum frame and screw-mounted camera/battery modules,Slim kraft box,Smartphone engineered with a single Phillips screwdriver and spare part store,Software bloat or cracked screen without a tempered glass protector,Swap a degraded battery or USB port in 5 minutes using official spare modules,Slightly thicker bezel than glued waterproof flagship phones,80,90,90,95,85
78,Hand-crank and solar emergency radio torch,Electronics,Monocrystalline solar cell dynamo crank and LiFePO4 cell,Cardboard box,Off-grid LED lantern and radio requiring zero disposable batteries,Leaving battery at 0% charge for years in a damp closet,Expose to window sunlight once a month to keep the internal cell healthy,LiFePO4 chemistry offers 2000+ cycles without cobalt,75,85,80,85,75
79,Recycled-plastic ergonomic wireless mouse,Electronics,85% post-consumer recycled ABS and optical sensor,FSC paper pulp tray,Repairable office mouse with accessible switches and single AA NiMH slot,Micro-switch double-click wear after millions of clicks,Use a rechargeable AA cell instead of sealed pouch batteries and clean scroll wheel dust,Easy battery removal makes e-waste recycling much safer,75,80,85,85,75
80,Refurbished enterprise-grade laptop,Electronics,Mag-alloy chassis with upgradeable SO-DIMM RAM and NVMe slots,Recycled brown shipping box,Second-life workstation laptop tested and upgraded for engineering studies,Battery wear after 3 to 4 years of heavy compilation and CAD,Upgrade RAM and SSD modularly and swap the clip-in battery rather than buying a new laptop,Avoids 250+ kg of mining and manufacturing CO2 emissions,90,90,90,95,85
81,Recycled-wool repairable winter sweater,Clothing,80% mechanically shredded post-consumer wool and 20% nylon,Paper twine bundle,Warm knit pullover spun from sorted pre-colored wool sweaters,Moth damage or elbow thinning over winters,Store with cedar blocks and add suede or darning patches on elbows,No new dye water needed when sorted by color before re-spinning,85,85,90,85,80
82,Natural cork and recycled-rubber wallet,Clothing,Harvested Portuguese oak bark cork fabric,Kraft sleeve,Vegan leather-alternative billfold harvested without cutting down trees,Over-stuffing card slots can stretch stitching,Wipe clean with a damp cloth and avoid machine washing,Cork oak trees absorb more CO2 after bark harvesting regeneration,90,80,90,85,90
83,Resoleable Goodyear-welt leather boots,Clothing,Vegetable-tanned leather and stitched rubber lug sole,Unbleached shoebox,Footwear where the worn outsole can be unstitched and replaced by a cobbler,Leather cracks if dried near heaters after monsoon rain,Condition with natural wax twice a year and resole at a local cobbler every 4 years,Initial break-in period and higher price than cemented foam sneakers,80,95,85,95,85
84,Cemented fast-fashion foam sneakers,Clothing,Fused EVA foam polyurethane mesh and rubber glue,Glossy laminated box,Lightweight athletic-style shoes with permanently glued soles,Midsole foam compresses flat in 8 months and cannot be resoled or separated,Reserve for gym floors and donate gently worn pairs before foam hydrolysis,Multi-material glue bonds make sneaker recycling nearly impossible,30,35,45,50,20
85,Linen-hemp breathable summer shirt,Clothing,55% industrial hemp and 45% flax linen,Compostable cornstarch bag,Bast-fiber woven shirt grown with minimal water and zero pesticides,Creases naturally if spun on high washing machine RPM,Wash on gentle cycle and hang dry damp to smooth wrinkles without heavy ironing,Softens with every wash and is 100% biodegradable if unblended,90,85,85,85,90
86,Beeswax or plant-wax food wrap,Food containers,Organic cotton infused with beeswax jojoba oil and pine resin,Paper envelope,Moldable breathable wrap replacing plastic cling film for bowls and fruit,Melts if washed in hot water or wrapped around steaming hot food,Rinse in cool water with mild soap and refresh wax in a low oven after a year,Not suitable for raw meat storage due to cool-water washing,85,75,95,85,95
87,Platinum silicone stretch bowl lids,Food containers,100% food-grade platinum silicone,Cardboard card,Elastic lids that seal leftover bowls mugs and cut melons without cling wrap,Punctures if stretched over sharp knife blades,Dry bowl rims before stretching lid to create an airtight suction seal,Dishwasher and freezer safe for 10+ years,80,90,85,90,75
88,Wide-mouth mason and pickle glass jars,Food containers,Soda-lime glass and two-piece tinplate lid,Reused grocery jar,Upcycled pasta or pickle jars used for dry pantry storage and overnight oats,Tin lid inner ring can rust if left wet after washing,Dry metal lids immediately or pair with reusable stainless or plastic screw caps,Zero manufacturing cost when upcycled from kitchen grocery jars,95,90,95,95,90
89,Single-use aluminum foil food tray,Food containers,Stamped aluminum sheet with paperboard lid,Plastic takeaway bag,Takeaway biryani and baking tray,Heavily grease-stained foil is often rejected by paper and plastic sorters,Scrape food residue clean and scrunch clean foil into a fist-sized ball for metal recovery,High embodied smelting energy wasted if used once and landfilled,55,25,40,30,75
90,Insulated stainless steel vacuum food flask,Food containers,Double-wall 304 steel with copper thermal lining,Recycled box,Wide-mouth thermal jar keeping soups or rice hot for 8 hours without reheating,Dropping dented outer wall can breach vacuum seal,Pre-warm with boiling water for 2 minutes before packing hot lunch,Saves microwave electricity and eliminates single-use delivery bowls,75,90,85,90,80
91,Mechanical wind-up kitchen timer,Household,Stainless steel spring gear train and bell housing,Small kraft box,Battery-free clockwork timer for cooking and Pomodoro study sessions,Over-winding past the 55-minute stop pin can jam the spring,Wind fully to 55 minutes first then turn back to your target minute to ring clearly,Zero button-cell battery waste for decades,85,90,85,85,90
92,Cast iron heirloom skillet,Household,Sand-cast pig iron seasoned with vegetable oil,Corrugated cardboard sleeve,Indestructible cooking pan that improves its non-stick patina over generations,Surface flash rust if soaked in sink water or run through dishwashers,Scrub with warm water dry on stove burner and wipe a drop of oil after use,Replaces 10+ peeled PTFE non-stick pans that leach PFAS chemicals,90,99,90,95,99
93,PTFE-coated aluminum non-stick pan,Household,Stamped aluminum with fluoropolymer coating,Plastic sleeve and carton,Lightweight frying pan with synthetic slick coating,Coating scratches and peels within 2 to 3 years making the pan unsafe to use,Never use metal utensils or high heat and switch to cast iron or stainless steel,Scrap yards penalize coated aluminum and PFAS production persists in water,35,30,50,55,30
94,Gravity-fed ceramic & activated-carbon water filter,Household,Stainless steel chambers with replaceable ceramic/coconut carbon candles,Cardboard box,Electricity-free drinking water purifier with zero wastewater reject,Ceramic candle pores clog if not lightly scrubbed in muddy water seasons,Scrub ceramic outer shell gently every month and replace only the carbon core yearly,Saves 3 liters of RO reject wastewater per liter of drinking water,85,90,85,95,85
95,Plastic pitcher filter with sealed cartridges,Household,SAN plastic jug and ultrasonic-welded PP filter pods,Glossy box and polybags,Countertop water pitcher requiring monthly sealed plastic cartridge swaps,Each sealed pod traps ion-exchange resin inside non-recyclable polypropylene housing,Choose refillable loose-granule filter cartridges or stainless gravity filters,Low jug price locks users into high-waste monthly plastic cartridges,45,50,40,60,30
96,Solar outdoor motion pathway light,Household,Polycrystalline solar panel LiFePO4 cell and ABS/aluminum housing,Kraft box,Self-contained garden and hostel walkway light charged by daylight,Cheap epoxy solar coatings yellow and cloud over in harsh UV sun,Tempered glass solar top panel and screw-accessible battery bay extend life to 8+ years,Zero grid electricity draw and easy battery replacement,75,80,80,85,75
97,Compostable kitchen countertop caddy,Household,Recycled stainless steel with replaceable coconut-carbon lid filter,Kraft box,Odor-sealed bin for collecting fruit peels tea leaves and coffee grounds,Fruit flies if charcoal filter is saturated or bin is unwashed,Empty into community or garden compost bin every 2 days and rinse with soapy water,Diverts 40% of household wet weight away from methane-producing landfills,85,90,85,95,90
98,Upcycled tire-rubber welcome doormat,Household,Devulcanized or strip-woven scrap car tire rubber,Paper tag,Heavy-duty weatherproof entrance mat diverted from automotive tire piles,Slight rubber smell during the first week if used in unventilated indoor rooms,Place on covered porch or balcony entrance and hose off dirt with water,Gives a 15-year second life to tough vulcanized rubber waste,90,95,95,90,80
99,Modular screw-together wooden bookshelf,Household,FSC rubberwood or birch plywood with steel hex bolts,Flat-pack kraft carton,Furniture designed to be disassembled and re-tightened across 10+ hostel or apartment moves,Particleboard alternatives crumble at screw holes after a single move,Use solid wood or threaded metal inserts so bolts never strip the wood grain,Flat-pack shipping plus lifetime repairability,85,90,85,90,90
100,Fast-furniture laminated particleboard desk,Household,Urea-formaldehyde resin woodchips and melamine plastic veneer,Styrofoam corners and shrink film,Low-cost flat-pack desk that swells when wet and strips at cam-locks,Moisture from a spilled glass or moving disassembly snaps the chipboard joints,Reinforce joints with L-brackets or buy secondhand solid wood study tables,Resin-glued woodchips cannot be composted or cleanly recycled,35,30,30,45,25
101,Refillable piezoelectric kitchen gas lighter,Household,Stainless steel barrel with piezo crystal igniter,Blister card or box,Battery-free spark igniter for gas stoves lasting 30000+ clicks,Disposable plastic butane lighters are landfilled as hazardous pressurized waste,Keep piezo tip dry from curry splatters to maintain strong spark generation,Zero butane gas or battery required for years of daily cooking,85,90,75,95,85
102,Single-use plastic butane pocket lighter,Household,POM plastic tank steel wheel and pressurized butane,Plastic tray of 50,Cheap disposable flame lighter without refill valve,Non-refillable tank with residual gas is a fire hazard in waste compactors,Switch to a refillable metal butane torch or USB arc/piezo igniter,Over 1.5 billion disposable lighters end up in landfills annually,20,20,25,30,15
103,Natural terracotta clay water matka,Drinkware,Unfired and kiln-baked porous alluvial clay,Straw cushioning,Traditional evaporative-cooling earthen water pot with tap,Hairline cracks if bumped with metal pots or scrubbed with chemical soap,Clean only with warm water and baking soda and place on a stable iron stand,Cools water naturally without electricity or refrigerants and returns to soil,95,75,95,85,99
104,Reusable silicone zip-top freezer bag,Food containers,Thick platinum-cured food-grade silicone,Paper sleeve,Washable pinch-seal bag for marinating freezing and travel toiletries,Pinch seal track can trap crumbs if not turned inside-out to wash,Turn inside-out over a glass to dry completely after washing,Replaces 300+ single-use LDPE zip bags per pouch,80,85,85,85,75
105,Modular repairable power strip with surge fuse,Electronics,Flame-retardant polycarbonate brass busbars and replaceable ceramic fuse,Kraft box,Heavy-duty extension board with standard screws and replaceable surge fuse,Cheap riveted power strips must be thrown away when a ₹5 internal fuse blows,Unscrew the fuse cap to swap a blown glass/ceramic fuse in 60 seconds,Protects expensive laptops while preventing premature e-waste,80,90,85,90,85'''

@st.cache_data
def load_data():
    try:
        if DATA_PATH.is_file():
            df = pd.read_csv(DATA_PATH, encoding="utf-8-sig", on_bad_lines="skip")
            if len(df) > 5:
                return df, "Loaded custom products.csv."
    except Exception:
        pass
    df = pd.read_csv(io.StringIO(_FALLBACK_PRODUCTS_CSV))
    return df, "Loaded built-in errorless dataset (105 products)."

df, data_load_notice = load_data()

def score_product(row):
    return round(sum(float(row[col]) * weight for col, weight in WEIGHTS.items()), 1)

def score_bar_color(score):
    if score >= 70: return "linear-gradient(90deg, #1b6741, #48b578)"
    if score >= 45: return "linear-gradient(90deg, #b87d14, #f0b429)"
    return "linear-gradient(90deg, #a82828, #e05252)"

def score_badge_label(score):
    if score >= 70: return "🌟 High Circularity", "#dcecdf", "#174c31"
    if score >= 45: return "⚖️ Moderate Impact", "#fff3cd", "#7a5200"
    return "⚠️ High Waste Risk", "#fde2e2", "#8c1d1d"

def build_svg_radar(primary_row, compare_row=None, is_dark=False):
    axes = [
        ("material_score", "Materials"),
        ("lifecycle_score", "Lifespan"),
        ("packaging_score", "Packaging"),
        ("usage_score", "Usage"),
        ("end_of_life_score", "End-of-Life"),
    ]
    cx, cy, radius = 185, 165, 105
    grid_color = "#2e543e" if is_dark else "#cfe0cf"
    label_color = "#d6f5e0" if is_dark else "#1d3b2a"

    def pt(idx, val):
        angle = -math.pi / 2 + idx * (2 * math.pi / 5)
        r = (float(val) / 100.0) * radius
        return cx + r * math.cos(angle), cy + r * math.sin(angle)

    rings_svg = ""
    for level in [25, 50, 75, 100]:
        ring_pts = " ".join(f"{pt(i, level)[0]:.1f},{pt(i, level)[1]:.1f}" for i in range(5))
        rings_svg += f'<polygon points="{ring_pts}" fill="none" stroke="{grid_color}" stroke-width="1" stroke-dasharray="3,3"/>'

    spokes_svg, labels_svg = "", ""
    for i, (_, label) in enumerate(axes):
        x_end, y_end = pt(i, 100)
        spokes_svg += f'<line x1="{cx}" y1="{cy}" x2="{x_end:.1f}" y2="{y_end:.1f}" stroke="{grid_color}" stroke-width="1"/>'
        lx, ly = pt(i, 124)
        labels_svg += f'<text x="{lx:.1f}" y="{ly:.1f}" fill="{label_color}" font-size="11.5" font-weight="700" text-anchor="middle" dominant-baseline="middle">{label}</text>'

    p1_pts = " ".join(f"{pt(i, primary_row[k])[0]:.1f},{pt(i, primary_row[k])[1]:.1f}" for i, (k, _) in enumerate(axes))
    poly1_svg = f'<polygon points="{p1_pts}" fill="rgba(46, 139, 87, 0.34)" stroke="#2e8b57" stroke-width="2.6"/>'
    dots1_svg = "".join(f'<circle cx="{pt(i, primary_row[k])[0]:.1f}" cy="{pt(i, primary_row[k])[1]:.1f}" r="4" fill="#2e8b57"/>' for i, (k, _) in enumerate(axes))

    poly2_svg, legend_2 = "", ""
    if compare_row is not None:
        p2_pts = " ".join(f"{pt(i, compare_row[k])[0]:.1f},{pt(i, compare_row[k])[1]:.1f}" for i, (k, _) in enumerate(axes))
        poly2_svg = f'<polygon points="{p2_pts}" fill="rgba(240, 180, 41, 0.22)" stroke="#e09f1f" stroke-width="2.2" stroke-dasharray="5,3"/>'
        legend_2 = f'<span style="display:inline-flex;align-items:center;gap:6px;font-size:12px;"><span style="width:12px;height:12px;border-radius:3px;background:#e09f1f;display:inline-block;"></span>{html.escape(str(compare_row["product_name"]))}</span>'

    legend_1 = f'<span style="display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:700;"><span style="width:12px;height:12px;border-radius:3px;background:#2e8b57;display:inline-block;"></span>{html.escape(str(primary_row["product_name"]))}</span>'

    return f"""
    <div class="result-card" style="text-align:center;padding:1rem;">
        <div style="font-weight:700;font-size:.95rem;margin-bottom:4px;">🕸️ 5-Axis Lifecycle Radar Comparison</div>
        <svg viewBox="0 0 370 325" style="width:100%;max-width:360px;height:auto;">
            {rings_svg} {spokes_svg} {poly2_svg} {poly1_svg} {dots1_svg} {labels_svg}
        </svg>
        <div style="display:flex;justify-content:center;gap:16px;flex-wrap:wrap;margin-top:4px;">{legend_1} {legend_2}</div>
    </div>
    """

# -------------------- AI & Accessibility Helpers --------------------

def get_gemini_client():
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        api_key = ""
    if not api_key:
        raise KeyError("GEMINI_API_KEY is not configured")
    from google import genai
    return genai.Client(api_key=api_key)

def generate_with_fallback(client, contents, config=None):
    for model_name in ["gemini-2.5-flash", "gemini-3.5-flash-lite", "gemini-2.0-flash"]:
        try:
            return client.models.generate_content(model=model_name, contents=contents, config=config)
        except Exception:
            continue
    raise RuntimeError("All configured Gemini models failed to respond.")

def render_tts_buttons(text_to_read, key_suffix):
    clean = str(text_to_read).replace("*", "").replace("#", "").replace("`", "").replace("\n", " ")
    js_safe_text = json.dumps(clean)
    components.html(f"""
        <div style="display:flex;gap:8px;align-items:center;font-family:sans-serif;margin:0;padding:0;">
            <button onclick='window.speechSynthesis.cancel(); const u = new SpeechSynthesisUtterance({js_safe_text}); u.rate = 1.0; window.speechSynthesis.speak(u);' style="background:#eaf1e7;border:1px solid #b9d9b8;color:#174c31;padding:4px 11px;border-radius:8px;font-size:12px;cursor:pointer;font-weight:600;">🔊 Read Aloud</button>
            <button onclick='window.speechSynthesis.cancel();' style="background:#fdf2f2;border:1px solid #f8d7da;color:#8c1d1d;padding:4px 11px;border-radius:8px;font-size:12px;cursor:pointer;font-weight:600;">⏹️ Stop</button>
        </div>
    """, height=36)

def heuristic_greenwash_check(claim_text):
    lower_c = claim_text.lower()
    buzzwords = [w for w in ["100% eco", "chemical-free", "all-natural", "green", "earth-friendly", "biodegradable plastic", "miracle", "zero-impact", "bamboo plastic"] if w in lower_c]
    has_cert = any(w in lower_c for w in ["fsc", "gots", "iso", "post-consumer", "bis", "epr", "compostable astm"])
    score = 75 if has_cert else max(25, 70 - len(buzzwords) * 18)
    verdict = "Verified / Specific Claim" if score >= 70 else ("Vague / Needs Proof" if score >= 45 else "High Greenwashing Risk")
    return {
        "trust_score": score,
        "verdict": verdict,
        "red_flags": buzzwords if buzzwords else ["No certified standard or material percentage cited"],
        "reality_check": "Blended materials (like bamboo-melamine or bio-PE) and vague 'eco-friendly' labels rarely break down in home compost or standard municipal recycling.",
        "better_alternative": "Look for mono-material construction (100% stainless steel, glass, or unbleached kraft paper) or third-party certifications (FSC, GOTS)."
    }

# -------------------- Hero Banner & Live Impact Counter --------------------

with db_connect() as conn:
    donated_count = conn.execute("SELECT COUNT(*) AS n FROM items WHERE status='Donated'").fetchone()["n"]
    available_count = conn.execute("SELECT COUNT(*) AS n FROM items WHERE status='Available'").fetchone()["n"]
    loan_items_count = conn.execute("SELECT COUNT(*) AS n FROM items WHERE listing_mode LIKE '%Lending%'").fetchone()["n"]
    wishes_count = conn.execute("SELECT COUNT(*) AS n FROM wishes WHERE status='Active'").fetchone()["n"]
    hubs_count = conn.execute("SELECT COUNT(*) AS n FROM repair_hubs").fetchone()["n"]

total_waste_diverted_kg = donated_count * 1.5
total_co2_saved_kg = donated_count * 4.2

st.markdown(f"""
<div class="hero">
  <span class="pill" style="background:rgba(224,245,189,0.22);color:#e6f9d5;border:1px solid rgba(224,245,189,0.4);">
    🌱 WASTE-TO-DESIGN INTELLIGENCE & COMMUNITY REUSE MARKETPLACE
  </span>
  <h1>REVORA</h1>
  <p>Rethink materials. Reuse what works. Revive everyday objects before they become waste.</p>
  <div class="hero-badges">
    <span class="hero-badge">📊 Impact: <b>{total_waste_diverted_kg:.1f} kg</b> Waste Diverted</span>
    <span class="hero-badge">🌍 Impact: <b>{total_co2_saved_kg:.1f} kg</b> CO₂ Saved</span>
    <span class="hero-badge">🎁 <b>{available_count}</b> Available Items</span>
    <span class="hero-badge">🔄 <b>{loan_items_count}</b> Tool Library Loans</span>
    <span class="hero-badge">📌 <b>{wishes_count}</b> Active Wishes</span>
    <span class="hero-badge">🛠️ <b>{hubs_count}</b> Repair & E-Waste Hubs</span>
    <span class="hero-badge">📚 <b>{len(df)}</b> Products in Catalog</span>
  </div>
</div>
""", unsafe_allow_html=True)

tab_explore, tab_wish, tab_ai, tab_browse, tab_donate, tab_manage, tab_track, tab_repair = st.tabs([
    "🌿 Product Explorer",
    "📌 Wish Board & Matchmaker",
    "🤖 REVORA AI Studio",
    "🔎 Browse, Loans & Certificates",
    "🎁 Donate or Lend an Item",
    "📬 Manage Requests",
    "📦 Track & QR Pass",
    "🛠️ Repair & E-Waste Hub",
])

# -------------------- Tab 1: Product Explorer, Break-Even Calculator & Resin Decoder --------------------

with tab_explore:
    st.markdown("## 🌿 Explore the 105-Product Lifecycle Catalog")
    filter_col1, filter_col2, filter_col3 = st.columns([1, 1, 1])
    with filter_col1:
        categories = ["All categories"] + sorted(df["category"].unique().tolist())
        selected_category = st.selectbox("Product category", categories, key="explore_category")
    with filter_col2:
        problem_options = [
            "Single-use waste builds up", "Breaks before the rest wears out",
            "Too much product is dispensed or used", "Packaging is excessive",
            "Product is rarely used", "Hard to recycle or dispose of",
        ]
        problem = st.selectbox("Main waste problem", problem_options, key="explore_problem")
    with filter_col3:
        priority = st.selectbox("Your priority", ["Overall sustainability", "Longer lifespan", "Less packaging", "Repairability", "Reuse potential"], key="explore_priority")

    with st.expander("♻️ Interactive Plastic Resin & Packaging Symbol Decoder (#1–#7 & E-Waste)", expanded=False):
        st.caption("Inspect the triangle resin code or symbol stamped on any product or packaging to see its real-world municipal recyclability:")
        selected_resin = st.selectbox("Select Packaging Symbol / Resin Code", list(RESIN_DECODER_DATA.keys()), key="resin_decoder_select")
        r_info = RESIN_DECODER_DATA[selected_resin]
        rc1, rc2 = st.columns([1.3, 1.7])
        with rc1:
            st.markdown(f"""
            <div class="result-card">
                <span class="pill">{safe_text(r_info['verdict'])}</span>
                <h4 style="margin:.55rem 0 .25rem;">{safe_text(selected_resin)}</h4>
                <p style="font-size:.9rem;"><b>📦 Common Products:</b> {safe_text(r_info['common_uses'])}</p>
                <p style="font-size:.9rem;"><b>♻️ Municipal Recyclability:</b> {safe_text(r_info['recyclability'])}</p>
            </div>
            """, unsafe_allow_html=True)
        with rc2:
            st.markdown(f"""
            <div class="marketplace-note">
                <b>⚠️ Material & Contamination Risk:</b><br>{safe_text(r_info['risk'])}<br><br>
                <b>🌱 Recommended Circular Swap:</b><br>{safe_text(r_info['swap'])}
            </div>
            """, unsafe_allow_html=True)

    search = st.text_input("🔎 Search 105+ products by keyword, name, or material", placeholder="Try: bottle, notebook, copper, wool, bamboo, drill...", key="product_search")
    filtered = df.copy()
    if selected_category != "All categories":
        filtered = filtered[filtered["category"] == selected_category]
    if search.strip():
        filtered = filtered[filtered.apply(lambda r: search.lower() in " ".join(map(str, r.values)).lower(), axis=1)]
    filtered["eco_score"] = filtered.apply(score_product, axis=1)

    if priority == "Longer lifespan": filtered["rank_score"] = filtered["lifecycle_score"]
    elif priority == "Less packaging": filtered["rank_score"] = filtered["packaging_score"]
    elif priority == "Repairability": filtered["rank_score"] = filtered["end_of_life_score"]
    elif priority == "Reuse potential": filtered["rank_score"] = filtered["usage_score"]
    else: filtered["rank_score"] = filtered["eco_score"]
    filtered = filtered.sort_values("rank_score", ascending=False)

    if filtered.empty:
        st.info("No matching products. Try another search or category.")
    else:
        show_limit = st.slider("Number of products to display", min_value=12, max_value=len(filtered), value=min(24, len(filtered)), step=12, key="catalog_display_limit")
        cols = st.columns(3)
        for idx, (_, row) in enumerate(filtered.head(show_limit).iterrows()):
            icon = CATEGORY_ICONS.get(row["category"], "🌱")
            score_val = float(row["eco_score"])
            bar_bg = score_bar_color(score_val)
            badge_text, badge_bg, badge_fg = score_badge_label(score_val)
            with cols[idx % 3]:
                st.markdown(f"""
                <div class="result-card">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <span class="muted">{icon} {safe_text(row['category'])}</span>
                        <span style="background:{badge_bg};color:{badge_fg};padding:3px 9px;border-radius:999px;font-size:.73rem;font-weight:700;">{badge_text}</span>
                    </div>
                    <h3 style="margin:.45rem 0 .2rem">{safe_text(row['product_name'])}</h3>
                    <div class="big-score">{score_val:.0f}<span style="font-size:.88rem;font-weight:500;" class="muted"> / 100 EcoScore</span></div>
                    <div class="eco-bar-track">
                        <div class="eco-bar-fill" style="width:{min(100, max(5, score_val))}%;background:{bar_bg};"></div>
                    </div>
                    <p style="min-height:3rem;font-size:.93rem;">{safe_text(row['description'])}</p>
                    <span class="pill">🧱 {safe_text(row['material'])}</span>
                </div>
                """, unsafe_allow_html=True)
                if st.button("🔬 Analyze & Break-Even Math", key=f"analyze_{row['product_id']}", use_container_width=True):
                    st.session_state.selected_product_id = row["product_id"]

    if "selected_product_id" in st.session_state:
        chosen_matches = df[df["product_id"] == st.session_state.selected_product_id]
        if not chosen_matches.empty:
            chosen = chosen_matches.iloc[0].copy()
            chosen["eco_score"] = score_product(chosen)
            candidates = df.copy()
            candidates["eco_score"] = candidates.apply(score_product, axis=1)

            def intervention_for(prob):
                rules = {
                    "Breaks before the rest wears out": ("Prioritize a repairable or modular design", "Look for replaceable parts, accessible fasteners, and repair guides."),
                    "Too much product is dispensed or used": ("Choose controlled-dose or refillable packaging", "A measured dispenser or refill pack reduces overuse."),
                    "Packaging is excessive": ("Prefer right-sized, concentrated, or refill packaging", "Compare packaging per use—not just package size."),
                    "Product is rarely used": ("Borrow, share, or keep using what you own", "Test whether sharing or renting solves the need without a new product."),
                    "Single-use waste builds up": ("Switch to a durable alternative if reuse is frequent", "Compare expected lifetime uses and cleaning needs."),
                    "Hard to recycle or dispose of": ("Choose simpler materials and a known take-back route", "Prefer clearly labelled materials and check local collection rules."),
                }
                return rules[prob]

            title, explanation = intervention_for(problem)
            sc = candidates[(candidates["category"] == chosen["category"]) & (candidates["product_name"] != chosen["product_name"])].copy()
            sc["score_gain"] = sc["eco_score"] - float(chosen["eco_score"])
            recs = sc.sort_values(["eco_score", "score_gain"], ascending=False).head(3)

            st.markdown("---")
            st.markdown("## 🔬 Waste-to-Design Analysis & Radar Comparison")
            st.markdown(f"### {CATEGORY_ICONS.get(chosen['category'], '🌱')} {chosen['product_name']}")

            info_col, radar_col = st.columns([1.35, 1])
            with info_col:
                st.markdown(f"""
                <div class="marketplace-note">
                    <b>⚠️ Likely Waste Pattern:</b><br>{safe_text(chosen['waste_risk'])}<br><br>
                    <b>🧱 Material:</b> {safe_text(chosen['material'])} &nbsp;·&nbsp; <b>📦 Packaging:</b> {safe_text(chosen['packaging'])}
                </div>
                <div class="marketplace-note" style="border-left-color:#2e8b57;">
                    <b>💡 Design Opportunity:</b><br>{safe_text(chosen['design_opportunity'])}<br><br>
                    <b>⚖️ Key Trade-off:</b> {safe_text(chosen['tradeoff'])}
                </div>
                """, unsafe_allow_html=True)
                st.success(f"**Suggested Design Intervention: {title}** — {explanation}")

            with radar_col:
                compare_options = df[df["product_name"] != chosen["product_name"]]["product_name"].tolist()
                default_comp = recs.iloc[0]["product_name"] if not recs.empty else compare_options[0]
                comp_name = st.selectbox("Compare on Radar Chart against:", compare_options, index=compare_options.index(default_comp) if default_comp in compare_options else 0, key="radar_compare_select")
                comp_row = df[df["product_name"] == comp_name].iloc[0]
                st.markdown(build_svg_radar(chosen, comp_row, is_dark=dark_mode), unsafe_allow_html=True)

            st.markdown("### ⚖️ Break-Even Reuse Calculator")
            st.caption("Calculate how quickly switching to a durable alternative in this category pays off its manufacturing footprint.")
            be_uses, co2_g_per_use, weight_g_per_use = BREAKEVEN_PROFILES.get(chosen["category"], (20, 60, 15))
            calc_col1, calc_col2 = st.columns([1.2, 2])
            with calc_col1:
                uses_per_week = st.slider("How many times per week do you use this item?", min_value=1, max_value=35, value=7, key="breakeven_slider")
                expected_years = st.slider("Expected years you will keep a reusable version", min_value=1, max_value=10, value=2, key="breakeven_years")
            with calc_col2:
                weeks_to_breakeven = round(be_uses / max(1, uses_per_week), 1)
                total_uses_period = uses_per_week * 52 * expected_years
                net_disposables_avoided = max(0, total_uses_period - be_uses)
                co2_saved_kg = round((net_disposables_avoided * co2_g_per_use) / 1000.0, 1)
                waste_saved_kg = round((net_disposables_avoided * weight_g_per_use) / 1000.0, 2)

                b1, b2, b3 = st.columns(3)
                with b1: st.metric("Break-Even Threshold", f"{be_uses} uses", f"~{weeks_to_breakeven} weeks")
                with b2: st.metric(f"{expected_years}-Yr Disposables Avoided", f"{total_uses_period:,} units")
                with b3: st.metric(f"Net Carbon & Waste Saved", f"{co2_saved_kg} kg CO₂", f"{waste_saved_kg} kg waste")

# -------------------- Tab 2: Community Wish Board & Smart Matchmaker --------------------

with tab_wish:
    st.markdown("## 📌 Community Wish Board & Smart Matchmaker")
    st.write("Post items you need (textbooks, calculators, tools) or see automated matches between community wishes and available donations.")

    live_matches = compute_all_wish_item_matches()
    if live_matches:
        st.markdown("### 🤝 Smart Wish-to-Donation Matchmaker (Live Hits)")
        st.caption("REVORA automatically detected available donations that match active community wishes:")
        m_cols = st.columns(min(2, len(live_matches)))
        for idx, pair in enumerate(live_matches):
            it = pair["item"]
            w = pair["wish"]
            kw_str = ", ".join(pair["keywords"]) if pair["keywords"] else "Category Match"
            with m_cols[idx % 2]:
                st.markdown(f"""
                <div class="result-card" style="border-left:5px solid #2e8b57;">
                    <span class="pill">🎯 {pair['score']}% Match · {safe_text(kw_str)}</span>
                    <h4 style="margin:.45rem 0 .15rem;">Wish: {safe_text(w['wish_name'])}</h4>
                    <div class="muted">Requested by <b>{safe_text(w['requester_name'])}</b> ({safe_text(w['location'])}) · Contact: <b>{safe_text(w['requester_contact'])}</b></div>
                    <hr style="border:none;border-top:1px dashed #cce0cb;margin:8px 0;"/>
                    <div><b>🎁 Matching Listing:</b> {safe_text(it['item_name'])} (<code>REV-{it['id']:05d}</code> · {safe_text(it['listing_mode'])})</div>
                    <div class="muted">Listed by <b>{safe_text(it['donor_name'])}</b> in {safe_text(it['location'])}</div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown("---")

    wish_mode = st.radio("Wish Board Actions", ["Browse Wishes", "Post a New Wish"], horizontal=True, key="wish_board_mode")

    if wish_mode == "Post a New Wish":
        with st.form("post_wish_form", clear_on_submit=True):
            w1, w2 = st.columns(2)
            with w1:
                wish_name = st.text_input("What are you looking for? *", placeholder="e.g. Scientific Calculator or 1st Year Engineering Books", max_chars=100)
                wish_cat = st.selectbox("Category *", ["Books & education", "Electronics", "Clothing & shoes", "Home & kitchen", "Toys & games", "Sports & outdoors", "Other"])
                wish_loc = st.text_input("Your Area / City *", placeholder="e.g. Indiranagar, Bengaluru", max_chars=120)
            with w2:
                req_name = st.text_input("Your Name *", max_chars=80)
                req_contact = st.text_input("Your Email or Phone *", placeholder="Shown to donors who want to fulfill your wish", max_chars=120)
            wish_desc = st.text_area("Details / Specifications *", placeholder="Mention model, edition, condition required, or whether borrowing is okay...", max_chars=500)
            submit_wish = st.form_submit_button("📌 Publish Wish", use_container_width=True)

        if submit_wish:
            if not all([wish_name.strip(), wish_loc.strip(), req_name.strip(), req_contact.strip(), wish_desc.strip()]):
                st.error("Please fill in all required fields.")
            else:
                with db_connect() as conn:
                    conn.execute(
                        "INSERT INTO wishes (wish_name, category, location, description, requester_name, requester_contact, status, created_at) VALUES (?, ?, ?, ?, ?, ?, 'Active', ?)",
                        (wish_name.strip(), wish_cat, wish_loc.strip(), wish_desc.strip(), req_name.strip(), req_contact.strip(), now_iso())
                    )
                st.success("Your wish has been posted! If an available donation matches, it will appear in the Smart Matchmaker above.")
    else:
        with db_connect() as conn:
            active_wishes = conn.execute("SELECT * FROM wishes WHERE status='Active' ORDER BY created_at DESC").fetchall()

        if not active_wishes:
            st.info("No active wishes right now. Be the first to post what you're looking for!")
        else:
            st.caption(f"{len(active_wishes)} active community wish(es)")
            for wish in active_wishes:
                icon = CATEGORY_ICONS.get(wish["category"], "📌")
                with st.container(border=True):
                    w_left, w_right = st.columns([3, 1])
                    with w_left:
                        st.markdown(f"""
                        <div class="result-card" style="margin-bottom:0;">
                            <span class="pill">{icon} {safe_text(wish['category'])}</span> &nbsp;<span class="muted">· Posted by <b>{safe_text(wish['requester_name'])}</b></span>
                            <h3 style="margin:.45rem 0">{safe_text(wish['wish_name'])}</h3>
                            <p>{safe_text(wish['description'])}</p>
                            <div class="muted">📍 {safe_text(wish['location'])} · Contact: <b>{safe_text(wish['requester_contact'])}</b> · {wish['created_at'][:10]}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with w_right:
                        if st.button("🎁 Fulfill This Wish", key=f"fulfill_wish_{wish['id']}", use_container_width=True):
                            st.session_state.prefill_item_name = wish["wish_name"]
                            st.session_state.prefill_category = wish["category"]
                            st.session_state.prefill_description = f"Fulfilling community wish posted by {wish['requester_name']}: {wish['description']}"
                            st.success("Pre-filled in the 'Donate or Lend an Item' tab!")

# -------------------- Tab 3: REVORA AI Studio --------------------

with tab_ai:
    st.markdown("## 🤖 REVORA AI Studio")
    st.write("Scan household objects, generate DIY upcycling blueprints, audit eco-marketing claims for greenwashing, or ask by voice.")

    if "revora_chat_history" not in st.session_state:
        st.session_state.revora_chat_history = []

    with st.expander("📸 AI Object Condition Scanner & DIY Upcycling Blueprint", expanded=True):
        scan_mode = st.radio("Choose input method", ["📤 Upload a photo", "📷 Take a picture"], horizontal=True, key="scan_input_mode")
        scanned_file = st.file_uploader("Upload a clear photo", type=["jpg", "jpeg", "png", "webp"], key="object_file_uploader") if scan_mode == "📤 Upload a photo" else st.camera_input("Point camera", key="object_camera_input")
        user_scan_note = st.text_input("Optional context (e.g., 'zipper is stuck' or 'cracked jar')", placeholder="Add any hidden issues...", key="object_scan_note")

        if scanned_file is not None:
            preview_col, result_col = st.columns([1, 1.8])
            with preview_col:
                st.image(scanned_file, caption="Scanned Object", use_container_width=True)
                analyze_btn = st.button("🔍 Analyze Object & Upcycling Ideas", type="primary", use_container_width=True)

            if analyze_btn:
                try:
                    client = get_gemini_client()
                    from google.genai import types
                    img_bytes = scanned_file.getvalue()
                    image_part = types.Part.from_bytes(data=img_bytes, mime_type=scanned_file.type or "image/jpeg")
                    scan_prompt = f"""Analyze the object in this image and return a strict JSON object with these keys:
                    object_name, marketplace_category, condition_status (Usable, Needs Minor Repair, Bad Condition),
                    marketplace_condition, condition_score (0-100), object_explanation, recommended_action, action_advice,
                    upcycling_blueprint (step-by-step creative DIY upcycling project or safe disassembly guide for this item),
                    draft_listing_description. User note: '{user_scan_note}'"""
                    with result_col:
                        with st.spinner("Scanning object materials, wear patterns, and DIY upcycling blueprints..."):
                            response = generate_with_fallback(client, contents=[image_part, scan_prompt], config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.2))
                            st.session_state.last_scan_result = json.loads(response.text)
                except Exception as e:
                    st.error(f"Could not analyze image: {e}")

            if "last_scan_result" in st.session_state:
                res = st.session_state.last_scan_result
                status, score = res.get("condition_status", "Usable"), int(res.get("condition_score", 50))
                badge_color, badge_bg = ("#1b6741", "#dcecdf") if status == "Usable" else ("#855800", "#fff1cc")
                with result_col:
                    st.markdown(f"""
                    <div class="result-card">
                        <span style="display:inline-block;padding:.3rem .75rem;border-radius:999px;background:{badge_bg};color:{badge_color};font-weight:700;">{status} · {score}/100</span>
                        <h3 style="margin:.5rem 0">{safe_text(res.get('object_name'))}</h3>
                        <p><b>🔎 About:</b> {safe_text(res.get('object_explanation'))}</p>
                        <p><b>🌱 Recommendation:</b> {safe_text(res.get('action_advice'))}</p>
                        <p><b>🛠️ DIY Upcycling / Disassembly Blueprint:</b><br>{safe_text(res.get('upcycling_blueprint', 'Clean thoroughly, separate mono-materials, or repurpose as a storage organizer.'))}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    render_tts_buttons(f"{res.get('object_name')}. Condition {status}. {res.get('action_advice')} Upcycling idea: {res.get('upcycling_blueprint', '')}", "scan_tts")
                    if status in ["Usable", "Needs Minor Repair"]:
                        if st.button("🎁 Pre-fill 'Donate or Lend' Form", use_container_width=True):
                            st.session_state.prefill_item_name = res.get("object_name", "")
                            st.session_state.prefill_category = res.get("marketplace_category", "Other")
                            st.session_state.prefill_condition = res.get("marketplace_condition", "Good")
                            st.session_state.prefill_description = res.get("draft_listing_description", "")
                            st.success("Details copied to Donate or Lend tab!")

    tool_col1, tool_col2 = st.columns(2)
    with tool_col1:
        with st.expander("🕵️‍♂️ AI Greenwashing Claim Detector", expanded=False):
            st.caption("Paste a product's eco-claim or label text to check for vague buzzwords vs. real circularity.")
            claim_input = st.text_area("Marketing Claim or Label Text", placeholder="e.g. '100% Eco-Friendly Biodegradable Bamboo-Plastic Composite Cup'", key="gw_claim_input")
            if st.button("🔎 Audit Claim for Greenwashing", use_container_width=True, key="gw_btn"):
                if not claim_input.strip():
                    st.warning("Paste a product claim first.")
                else:
                    try:
                        client = get_gemini_client()
                        from google.genai import types
                        gw_prompt = f"""Analyze this product sustainability claim for greenwashing and return strict JSON with keys:
                        trust_score (integer 0-100), verdict (string), red_flags (list of strings), reality_check (string), better_alternative (string).
                        Claim: {claim_input}"""
                        resp = generate_with_fallback(client, contents=gw_prompt, config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.2))
                        gw_data = json.loads(resp.text)
                    except Exception:
                        gw_data = heuristic_greenwash_check(claim_input)
                    st.markdown(f"""
                    <div class="result-card">
                        <span class="pill">Trust Score: {gw_data.get('trust_score', 50)}/100 · {safe_text(gw_data.get('verdict'))}</span>
                        <p style="margin-top:.5rem;"><b>🚩 Red Flags:</b> {safe_text(', '.join(gw_data.get('red_flags', [])))}</p>
                        <p><b>🔬 Reality Check:</b> {safe_text(gw_data.get('reality_check'))}</p>
                        <p><b>✅ Better Spec to Look For:</b> {safe_text(gw_data.get('better_alternative'))}</p>
                    </div>
                    """, unsafe_allow_html=True)

    with tool_col2:
        with st.expander("🛠️ On-Demand DIY Upcycling Blueprint Generator", expanded=False):
            st.caption("Have a broken or worn-out item? Generate a step-by-step creative upcycling or safe disassembly guide.")
            broken_item = st.text_input("Broken or Worn Item", placeholder="e.g. Torn denim jeans, cracked glass jar, old keyboard...", key="upcycle_item_input")
            if st.button("✨ Generate Upcycling Blueprint", use_container_width=True, key="upcycle_btn"):
                if not broken_item.strip():
                    st.warning("Enter an item to upcycle.")
                else:
                    try:
                        client = get_gemini_client()
                        up_prompt = f"Create a concise, practical 4-step DIY upcycling blueprint (with tools needed and safety tips) plus safe material disposal advice for: {broken_item}"
                        resp = generate_with_fallback(client, contents=up_prompt)
                        up_text = resp.text
                    except Exception:
                        up_text = f"**DIY Upcycling Blueprint for {broken_item}:**\n1. **Clean & Prep:** Separate any metal fasteners, batteries, or sharp edges.\n2. **Repurpose Core Material:** Cut intact sections into organizer pouches, planters, or desk trays.\n3. **Reinforce:** Use simple stitching or non-toxic adhesive.\n4. **Safe E-Waste/Scrap Drop-off:** Send any non-reusable electronics or mixed plastics to a certified hub in the Repair & E-Waste tab."
                    st.markdown(up_text)
                    render_tts_buttons(up_text, "upcycle_tts")

    st.markdown("---")
    st.markdown("### 🎙️ Voice Search & AI Chat")
    chat_col, clear_col = st.columns([5, 1])
    with chat_col: st.caption("Powered by Google Gemini · Speak by voice or type.")
    with clear_col:
        if st.button("Clear chat", key="clear_revora_chat"):
            st.session_state.revora_chat_history = []
            st.rerun()

    for idx, message in enumerate(st.session_state.revora_chat_history):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                render_tts_buttons(message["content"], f"hist_{idx}")

    voice_recording = st.audio_input("🎙️ Voice Search: Speak your question", key="revora_voice_search")
    prompt = st.chat_input("Or type your question...", key="revora_chat_input")

    new_voice_bytes = None
    if voice_recording is not None:
        raw_bytes = voice_recording.getvalue()
        voice_hash = hashlib.md5(raw_bytes).hexdigest()
        if st.session_state.get("last_voice_hash") != voice_hash:
            st.session_state["last_voice_hash"] = voice_hash
            new_voice_bytes = raw_bytes

    if prompt or new_voice_bytes:
        user_display = prompt if prompt else "🎙️ *[Voice Search Query]*"
        st.session_state.revora_chat_history.append({"role": "user", "content": user_display})
        with st.chat_message("user"):
            st.markdown(user_display)
            if new_voice_bytes:
                st.audio(new_voice_bytes)

        try:
            client = get_gemini_client()
            from google.genai import types
            recent_history = st.session_state.revora_chat_history[-12:]
            transcript = "\n\n".join(("User" if m["role"] == "user" else "REVORA AI") + ": " + m["content"] for m in recent_history)
            system_context = "You are REVORA AI, a helpful sustainability and circular-economy assistant inside a community reuse website."
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    if new_voice_bytes:
                        audio_part = types.Part.from_bytes(data=new_voice_bytes, mime_type=voice_recording.type or "audio/wav")
                        contents_payload = [audio_part, system_context + "\n\n" + transcript + "\n\nTranscribe user's voice query and answer helpfully."]
                    else:
                        contents_payload = system_context + "\n\n" + transcript
                    response = generate_with_fallback(client, contents=contents_payload)
                    answer = response.text or "I couldn't generate a response."
                st.markdown(answer)
                render_tts_buttons(answer, "latest_reply")
            st.session_state.revora_chat_history.append({"role": "assistant", "content": answer})
        except Exception as e:
            st.error(f"Error connecting to Gemini: {e}")

# -------------------- Tab 4: Browse Donations, Tool Library & Impact Certificate Exporter --------------------

with tab_browse:
    st.markdown("## 🏆 Community Donor Leaderboard & Impact Certificates")
    leaders = get_donor_leaderboard()
    if leaders:
        l_cols = st.columns(min(4, len(leaders)))
        for idx, leader in enumerate(leaders[:4]):
            b_title, b_bg, b_fg = get_donor_badge(int(leader["donated_count"] or 0), int(leader["listed_count"] or 0))
            with l_cols[idx]:
                st.markdown(f"""
                <div class="result-card" style="text-align:center;padding:1rem;">
                    <span style="background:{b_bg};color:{b_fg};padding:4px 10px;border-radius:999px;font-size:.75rem;font-weight:700;">{b_title}</span>
                    <h4 style="margin:.5rem 0 .2rem;">{safe_text(leader['donor_name'])}</h4>
                    <div class="muted">🎁 <b>{int(leader['donated_count'] or 0)}</b> Rehomed · 🔄 <b>{int(leader['loan_count'] or 0)}</b> Loans · 📦 <b>{int(leader['listed_count'] or 0)}</b> Listed</div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.caption("List, lend, or rehome items to earn community badges and unlock your Impact Certificate!")

    with st.expander("📜 Generate & Download Your Certificate of Circular Impact", expanded=False):
        st.caption("Export an official, verifiable HTML/printable certificate showcasing your circular economy contributions for student portfolios or NSS/community service logs.")
        cert_col1, cert_col2 = st.columns([1.2, 1.8])
        with cert_col1:
            donor_names_list = [r["donor_name"] for r in leaders] if leaders else []
            custom_or_select = st.text_input("Contributor / Student Name", value=donor_names_list[0] if donor_names_list else "Rahul R", key="cert_name_input")
            matched_leader = next((r for r in leaders if r["donor_name"].lower() == custom_or_select.strip().lower()), None)
            rehomed_val = int(matched_leader["donated_count"] or 0) if matched_leader else 1
            listed_val = int(matched_leader["listed_count"] or 0) if matched_leader else 1
            loan_val = int(matched_leader["loan_count"] or 0) if matched_leader else 0

            cert_html_str = build_impact_certificate_html(custom_or_select.strip() or "REVORA Contributor", rehomed_val, listed_val, loan_val)
            st.download_button(
                label="📥 Download Printable Impact Certificate (.html)",
                data=cert_html_str.encode("utf-8"),
                file_name=f"REVORA_Impact_Certificate_{(custom_or_select.strip() or 'Contributor').replace(' ', '_')}.html",
                mime="text/html",
                use_container_width=True,
            )
        with cert_col2:
            b_title, _, _ = get_donor_badge(rehomed_val, listed_val)
            eff = max(1, rehomed_val + loan_val)
            st.markdown(f"""
            <div class="result-card" style="border:2px solid #2e8b57;">
                <span class="pill">📜 CERTIFICATE PREVIEW · {safe_text(b_title)}</span>
                <h3 style="margin:.4rem 0 .15rem;">{safe_text(custom_or_select.strip() or 'REVORA Contributor')}</h3>
                <div class="muted">Verified Impact: <b>{eff * 1.5:.1f} kg</b> Waste Diverted · <b>{eff * 4.2:.1f} kg CO₂</b> Prevented</div>
                <p style="font-size:.86rem;margin-top:.4rem;">Open the downloaded file in any browser and press <code>Ctrl + P</code> to save as a bordered A4 PDF certificate.</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("## ♻️ Browse Donations & Peer Tool Library")
    b_col1, b_col2 = st.columns([1.2, 1.8])
    with b_col1:
        mode_filter = st.radio(
            "Filter by Listing Mode",
            ["All Modes", "Permanent Donation", "Peer Lending (Borrow & Return)"],
            horizontal=True,
            key="browse_mode_filter"
        )
    with b_col2:
        browse_search = st.text_input("🔎 Search available items or tools by keyword or location", key="browse_item_search")

    items = get_items(status="Available", search_text=browse_search, listing_mode=mode_filter)
    if not items:
        st.info("No matching listings right now. Switch the mode filter or list the first item in the Donate or Lend tab!")
    else:
        for item in items:
            icon = CATEGORY_ICONS.get(item["category"], "🎁")
            is_loan = "Lending" in str(item["listing_mode"])
            mode_tag = f"🔄 Borrow & Return ({item['loan_days']} Days Max)" if is_loan else "🎁 Permanent Donation"
            with st.container(border=True):
                left, right = st.columns([2.6, 1.2])
                with left:
                    st.markdown(f"""
                    <div class="result-card" style="margin-bottom:0;">
                        <span class="pill">{icon} {safe_text(item['category'])}</span> &nbsp;
                        <span class="pill" style="background:#e0f2fe;color:#0c4a6e;">{safe_text(mode_tag)}</span> &nbsp;
                        <span class="muted">· Condition: <b>{safe_text(item['item_condition'])}</b></span>
                        <h3 style="margin:.45rem 0">{safe_text(item['item_name'])}</h3>
                        <p>{safe_text(item['description'])}</p>
                        <div class="muted">📍 {safe_text(item['location'])} · Listed by <b>{safe_text(item['donor_name'])}</b> (ID: REV-{item['id']:05d})</div>
                    </div>
                    """, unsafe_allow_html=True)
                with right:
                    with st.form(f"request_form_{item['id']}"):
                        st.markdown(f"**✋ {'Request to Borrow' if is_loan else 'Request this Item'}**")
                        req_name = st.text_input("Your name", key=f"req_name_{item['id']}")
                        req_contact = st.text_input("Your email/phone", key=f"req_contact_{item['id']}")
                        req_message = st.text_area("Message (and return plan if borrowing)", key=f"req_msg_{item['id']}")
                        confirm = st.checkbox("I will arrange a safe public handover.", key=f"req_confirm_{item['id']}")
                        submitted = st.form_submit_button("Send request", use_container_width=True)
                    if submitted:
                        if not req_name.strip() or not req_contact.strip() or not req_message.strip():
                            st.error("Complete all required fields.")
                        elif not confirm:
                            st.error("Confirm safe handover.")
                        else:
                            with db_connect() as conn:
                                cursor = conn.execute("INSERT INTO requests (item_id, requester_name, requester_contact, message, status, created_at) VALUES (?, ?, ?, ?, 'Pending', ?)", (item["id"], req_name.strip(), req_contact.strip(), req_message.strip(), now_iso()))
                                st.success(f"Request sent! Track ID: REV-R{cursor.lastrowid:05d}")

# -------------------- Tab 5: Donate or Lend an Item --------------------

with tab_donate:
    st.markdown("## 🎁 Donate Permanently or 🔄 Lend to the Peer Tool Library")
    st.write("Pass along surplus items permanently, or lend high-utility tools (calculators, drafting kits, soldering irons, drills) for neighbors to borrow and return.")

    with st.form("donate_item_form", clear_on_submit=True):
        d1, d2 = st.columns(2)
        with d1:
            cat_options = ["Clothing & shoes", "Books & education", "Electronics", "Home & kitchen", "Toys & games", "Sports & outdoors", "Other"]
            cond_options = ["Like new", "Good", "Used but working", "Needs minor repair"]
            default_cat = st.session_state.get("prefill_category", "Clothing & shoes")
            default_cond = st.session_state.get("prefill_condition", "Good")

            item_name = st.text_input("Item or Tool name *", value=st.session_state.get("prefill_item_name", ""))
            item_category = st.selectbox("Category *", cat_options, index=cat_options.index(default_cat) if default_cat in cat_options else 0)
            listing_mode_sel = st.selectbox("Listing Mode *", ["Permanent Donation", "Peer Lending (Borrow & Return)"])
            loan_days_sel = st.slider("Max Loan Duration (Days — only applies to Peer Lending)", min_value=1, max_value=30, value=7)
        with d2:
            item_condition = st.selectbox("Condition *", cond_options, index=cond_options.index(default_cond) if default_cond in cond_options else 1)
            item_location = st.text_input("Area / city *")
            donor_name = st.text_input("Your name *")
            donor_contact = st.text_input("Your email or phone *")
            contact_type = st.selectbox("Contact preference", ["Email", "Phone / WhatsApp", "Either"])
            listing_pin = st.text_input("Private listing PIN (6+ chars) *", type="password")
        item_description = st.text_area("Description & pickup/return notes *", value=st.session_state.get("prefill_description", ""))
        safety_confirm = st.checkbox("I confirm this item is legal and safe.")
        submit_donation = st.form_submit_button("🌱 Publish Listing", use_container_width=True)

    if submit_donation:
        if not all([item_name.strip(), item_location.strip(), donor_name.strip(), donor_contact.strip(), item_description.strip(), listing_pin]) or len(listing_pin) < 6:
            st.error("Please complete all fields and use a 6+ character PIN.")
        else:
            effective_loan_days = int(loan_days_sel) if "Lending" in listing_mode_sel else 0
            with db_connect() as conn:
                cursor = conn.execute(
                    """INSERT INTO items (item_name, category, item_condition, location, description, donor_name, donor_contact, contact_type, pin_hash, status, listing_mode, loan_days, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Available', ?, ?, ?)""",
                    (item_name.strip(), item_category, item_condition, item_location.strip(), item_description.strip(), donor_name.strip(), donor_contact.strip(), contact_type, hash_pin(listing_pin), listing_mode_sel, effective_loan_days, now_iso())
                )
                new_id = cursor.lastrowid
            st.success(f"Listed successfully ({listing_mode_sel})! Listing ID: **REV-{new_id:05d}**. Save your PIN to manage requests.")

            instant_matches = find_wish_matches_for_item(item_name.strip(), item_category, item_description.strip())
            if instant_matches:
                st.markdown("### 🎯 Instant Wish Board Match Detected!")
                for score, w, overlap in instant_matches:
                    st.info(f"**{score}% Match:** **{w['requester_name']}** in {w['location']} is looking for **{w['wish_name']}** — Contact: `{w['requester_contact']}`")

# -------------------- Tab 6: Manage Requests, Loan Returns & QR Handover Pass --------------------

with tab_manage:
    st.markdown("## 📬 Manage Your Donation & Tool Library Requests")
    with st.form("manage_listing_form"):
        manage_id_text = st.text_input("Listing ID", placeholder="e.g. REV-00001")
        manage_pin = st.text_input("Private listing PIN", type="password")
        load_listing = st.form_submit_button("🔑 View Requests", use_container_width=True)
    if load_listing:
        try:
            listing_id = int(manage_id_text.strip().upper().replace("REV-", ""))
            listing = get_item(listing_id)
            if not listing or not secrets.compare_digest(listing["pin_hash"], hash_pin(manage_pin)):
                st.error("Incorrect Listing ID or PIN.")
            else:
                st.session_state.managed_listing_id = listing_id
        except Exception:
            st.error("Enter a valid listing ID like REV-00001.")

    if st.session_state.get("managed_listing_id"):
        listing = get_item(st.session_state.managed_listing_id)
        if listing:
            is_loan = "Lending" in str(listing["listing_mode"])
            st.markdown(f"### {safe_text(listing['item_name'])} (`{listing['status']}` · {safe_text(listing['listing_mode'])})")
            requests = get_requests_for_item(listing["id"])
            if not requests:
                st.info("No requests received for this listing yet.")
            for req in requests:
                with st.container(border=True):
                    st.markdown(f"**Request #REV-R{req['id']:05d} from {safe_text(req['requester_name'])}** · Status: **{req['status']}**")
                    st.write(req["message"])
                    if req["status"] in ["Approved", "Completed"]:
                        st.markdown(build_svg_handover_pass(listing["id"], req["id"], listing["item_name"], listing["location"], listing["status"], listing["listing_mode"], listing["loan_days"]), unsafe_allow_html=True)
                    if req["status"] == "Pending" and listing["status"] == "Available":
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("✅ Approve & Issue QR Pass", key=f"app_{req['id']}", use_container_width=True):
                                with db_connect() as conn:
                                    conn.execute("UPDATE requests SET status='Approved' WHERE id=?", (req["id"],))
                                    conn.execute("UPDATE items SET status='Reserved' WHERE id=?", (listing["id"],))
                                st.rerun()
                        with c2:
                            if st.button("Decline", key=f"dec_{req['id']}", use_container_width=True):
                                with db_connect() as conn:
                                    conn.execute("UPDATE requests SET status='Declined' WHERE id=?", (req["id"],))
                                st.rerun()

            if listing["status"] == "Reserved":
                b_col1, b_col2 = st.columns(2)
                with b_col1:
                    if st.button("🎉 Mark Handover / Loan Complete (Update Impact & Badges)", key=f"complete_{listing['id']}", type="primary", use_container_width=True):
                        with db_connect() as conn:
                            conn.execute("UPDATE items SET status='Donated' WHERE id=?", (listing["id"],))
                        st.success("Marked as completed! Impact metrics and badges updated.")
                        st.rerun()
                with b_col2:
                    if is_loan:
                        if st.button("🔄 Tool Returned — Relist as Available", key=f"relist_{listing['id']}", use_container_width=True):
                            with db_connect() as conn:
                                conn.execute("UPDATE items SET status='Available' WHERE id=?", (listing["id"],))
                            st.success("Tool marked as returned and available for the next borrower!")
                            st.rerun()

# -------------------- Tab 7: Track Request & View Digital QR Pass --------------------

with tab_track:
    st.markdown("## 📦 Track Your Request & Digital Handover Pass")
    with st.form("track_request_form"):
        track_id_text = st.text_input("Request ID", placeholder="e.g. REV-R00001")
        track_contact = st.text_input("Your email or phone used in the request")
        track_submit = st.form_submit_button("🔎 Check Status & Pass", use_container_width=True)
    if track_submit:
        try:
            req_id = int(track_id_text.strip().upper().replace("REV-R", ""))
            tracked = get_request_for_tracking(req_id, track_contact)
            if not tracked:
                st.error("Request not found. Check your Request ID and contact info.")
            else:
                st.markdown(f"### {safe_text(tracked['item_name'])} — Status: **{tracked['status']}**")
                if tracked["status"] == "Approved":
                    st.success(f"Approved! Donor Contact: **{tracked['donor_contact']}** ({tracked['contact_type']})")
                    st.markdown(build_svg_handover_pass(tracked["item_id"], tracked["id"], tracked["item_name"], tracked["location"], tracked["item_status"], tracked["listing_mode"], tracked["loan_days"]), unsafe_allow_html=True)
                elif tracked["status"] == "Pending":
                    st.info("Your request is currently pending donor review.")
                else:
                    st.warning(f"Request status: {tracked['status']}")
        except Exception:
            st.error("Enter a valid request ID like REV-R00001.")

# -------------------- Tab 8: Local Repair & E-Waste Hub --------------------

with tab_repair:
    st.markdown("## 🛠️ Local Repair & Certified E-Waste Directory")
    st.write("Before discarding a repairable item or hazardous electronic waste, find a neighborhood repair specialist or authorized e-waste drop-off point.")

    hub_col1, hub_col2 = st.columns([1.2, 2])
    with hub_col1:
        hub_filter = st.selectbox(
            "Filter by Service Type",
            ["All Types", "Electronics Repair", "Tailor & Clothing Repair", "E-Waste Drop-Off", "Footwear & Bag Repair", "Appliance & Modular Fix"],
            key="repair_type_filter"
        )
    with hub_col2:
        hub_search = st.text_input("🔎 Search by area, city, or service (e.g., Bengaluru, Salem, soldering, denim)", key="repair_search")

    with db_connect() as conn:
        sql_h = "SELECT * FROM repair_hubs"
        h_clauses, h_params = [], []
        if hub_filter != "All Types":
            h_clauses.append("hub_type = ?"); h_params.append(hub_filter)
        if hub_search.strip():
            h_clauses.append("(lower(hub_name) LIKE ? OR lower(city_area) LIKE ? OR lower(services) LIKE ?)")
            term = f"%{hub_search.strip().lower()}%"
            h_params.extend([term, term, term])
        if h_clauses:
            sql_h += " WHERE " + " AND ".join(h_clauses)
        sql_h += " ORDER BY id DESC"
        hubs = conn.execute(sql_h, h_params).fetchall()

    if not hubs:
        st.info("No matching repair hubs found. Try clearing your filter or add a new neighborhood hub below!")
    else:
        h_cols = st.columns(2)
        for idx, h in enumerate(hubs):
            with h_cols[idx % 2]:
                st.markdown(f"""
                <div class="result-card">
                    <span class="pill">🛠️ {safe_text(h['hub_type'])}</span>
                    <h3 style="margin:.45rem 0 .2rem;">{safe_text(h['hub_name'])}</h3>
                    <div class="muted">📍 <b>{safe_text(h['city_area'])}</b> · 🕒 {safe_text(h['hours'])}</div>
                    <p style="margin:.5rem 0;">{safe_text(h['services'])}</p>
                    <div class="muted">📞 Contact: <b>{safe_text(h['contact_info'])}</b></div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("---")
    with st.expander("➕ Suggest a Local Tailor, Repair Shop, or E-Waste Bin"):
        with st.form("add_repair_hub_form", clear_on_submit=True):
            rc1, rc2 = st.columns(2)
            with rc1:
                new_hub_name = st.text_input("Shop / Center Name *")
                new_hub_type = st.selectbox("Category *", ["Electronics Repair", "Tailor & Clothing Repair", "E-Waste Drop-Off", "Footwear & Bag Repair", "Appliance & Modular Fix"])
                new_hub_area = st.text_input("Neighborhood & City *", placeholder="e.g. Yelahanka, Bengaluru")
            with rc2:
                new_hub_contact = st.text_input("Phone / Email / Landmark *")
                new_hub_hours = st.text_input("Operating Hours *", value="Mon–Sat · 10:00 AM – 7:00 PM")
            new_hub_services = st.text_area("Services Offered *", placeholder="What do they repair or collect?")
            sub_hub = st.form_submit_button("🌱 Add to Community Directory", use_container_width=True)
            if sub_hub:
                if not all([new_hub_name.strip(), new_hub_area.strip(), new_hub_contact.strip(), new_hub_services.strip()]):
                    st.error("Please fill in all required fields.")
                else:
                    with db_connect() as conn:
                        conn.execute(
                            "INSERT INTO repair_hubs (hub_name, hub_type, city_area, services, contact_info, hours, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (new_hub_name.strip(), new_hub_type, new_hub_area.strip(), new_hub_services.strip(), new_hub_contact.strip(), new_hub_hours.strip(), now_iso())
                        )
                    st.success("Added to the Local Repair & E-Waste Directory!")
                    st.rerun()

st.markdown("---")
st.markdown("### 🌍 Small actions, less waste")
st.caption("REVORA is a community reuse prototype. Arrange handovers in safe, public places.")
