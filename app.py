import streamlit as st
import pandas as pd
from pathlib import Path
import sqlite3
import hashlib
import secrets
import html
import io
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

st.markdown("""
<style>
    .stApp { background: #f6f8f3; }
    .revora-splash {
        position: fixed; inset: 0; z-index: 999999; display: flex;
        align-items: center; justify-content: center; text-align: center;
        background: radial-gradient(circle at 50% 35%, #1f573b 0%, #103523 52%, #081c13 100%);
        color: #f4ffe9; animation: revoraSplashFade 3s ease forwards;
        pointer-events: none;
    }
    .splash-content { display:flex; flex-direction:column; align-items:center; padding:24px; animation: revoraRise .8s ease both; }
    .revora-mark { width:112px; height:112px; filter: drop-shadow(0 0 22px #80bf7966); animation: revoraPulse 1.5s ease-in-out infinite; }
    .splash-wordmark { margin-top:18px; font-size:clamp(2.6rem, 7vw, 4.5rem); font-weight:850; letter-spacing:.22em; padding-left:.22em; color:#f4ffe9; }
    .splash-tagline { margin-top:5px; color:#b9d9b8; font-size:.78rem; letter-spacing:.24em; }
    .splash-loader { width:180px; height:3px; margin-top:30px; overflow:hidden; background:#ffffff24; border-radius:10px; }
    .splash-loader span { display:block; width:40%; height:100%; border-radius:10px; background:#b5e58c; animation: revoraLoad 1.2s ease-in-out infinite; }
    .splash-loading-text { margin-top:13px; color:#c8ddca; font-size:.85rem; }
    @keyframes revoraSplashFade { 0%,72% { opacity:1; visibility:visible; } 100% { opacity:0; visibility:hidden; } }
    @keyframes revoraPulse { 0%,100% { transform:scale(1); } 50% { transform:scale(1.06); } }
    @keyframes revoraLoad { 0% { transform:translateX(-110%); } 100% { transform:translateX(360%); } }
    @keyframes revoraRise { from { opacity:0; transform:translateY(12px); } to { opacity:1; transform:translateY(0); } }
    [data-testid="stSidebar"] { background: #eaf1e7; }
    .hero {
        padding: 1.6rem 1.8rem; border-radius: 22px;
        background: linear-gradient(120deg, #123b2b 0%, #236647 70%, #3f8058 100%);
        color: white; margin-bottom: 1.1rem;
    }
    .hero h1 { color: white; font-size: 3rem; margin: 0; letter-spacing: -1px; }
    .hero p { color: #e3f3e7; font-size: 1.08rem; margin: .35rem 0 0; }
    .pill {
        display:inline-block; padding:.28rem .65rem; border-radius:999px;
        background:#dcecdf; color:#174c31; font-size:.82rem; font-weight:600;
    }
    .result-card {
        border: 1px solid #d9e5d7; border-radius: 16px; padding: 1rem 1.1rem;
        background: white; height: 100%;
    }
    .muted { color: #627268; font-size: .9rem; }
    .big-score { font-size: 2rem; font-weight: 800; color: #1b6741; }
    div[data-testid="stMetric"] {
        background: white; border: 1px solid #dce7da; padding: 12px 16px; border-radius: 14px;
    }
    .marketplace-note {
        border: 1px solid #d9e5d7; border-radius: 14px; padding: 1rem;
        background: #fff; margin: .5rem 0 1rem;
    }
</style>
""", unsafe_allow_html=True)

# -------------------- Product recommendation engine --------------------

# Built-in, validated fallback keeps the Product Explorer running if products.csv is
# missing from the deployment or contains malformed CSV quoting. Keep products.csv
# alongside app.py for easier editing; this embedded copy is a safety net.
_FALLBACK_PRODUCTS_CSV = 'product_id,product_name,category,material,packaging,description,waste_risk,design_opportunity,tradeoff,material_score,lifecycle_score,packaging_score,usage_score,end_of_life_score\n1,Disposable PET water bottle,Drinkware,PET plastic,Single-use plastic bottle,Convenient single-use water container,Repeated single-use packaging,Refill from safe drinking water or use a durable bottle when used frequently,Reusable alternatives require repeated use and cleaning,35,25,20,25,35\n2,Reusable stainless steel bottle,Drinkware,Stainless steel,Minimal or cardboard packaging,Durable bottle designed for repeated use,Can be underused or lost,Use consistently for many refill cycles,Material-intensive manufacture and cleaning needs matter,65,85,80,90,65\n3,Reusable glass bottle,Drinkware,Glass,Cardboard or protective packaging,Reusable bottle for home or office,Breakage can shorten lifespan,Use in settings where breakage risk is low,Heavier transport and breakage risk,70,70,75,80,70\n4,Single-use shopping bag,Bags,Thin plastic,No additional packaging,Lightweight carrier bag,Often discarded after one trip,Reuse bags already owned before acquiring new ones,Some reusable bags require many uses to offset production,25,20,30,25,25\n5,Reusable fabric tote,Bags,Cotton or blended fabric,Minimal packaging,Reusable shopping bag,May accumulate unused bags,Keep a small set and reuse frequently,Cotton production can be resource intensive,55,75,75,80,60\n6,Recycled-content paper bag,Bags,Recycled paper,Paper bag,Paper carrier with recycled content,May tear when wet or overloaded,Reuse when practical and recycle where accepted,Not always lower impact than reusing a bag already owned,70,45,65,50,75\n7,Disposable coffee cup,Food & drink,Paper with possible lining,Single-use cup,Takeaway cup used for one drink,Repeated cups and lids,Bring a cup or use dine-in service when practical,Reusable cup benefits depend on repeated use and washing,45,20,20,25,35\n8,Reusable coffee cup,Food & drink,Stainless steel or durable plastic,Minimal packaging,Reusable cup for takeaway drinks,May be forgotten or rarely used,Store it where it is easy to remember,Manufacture and washing impacts need repeated use,65,80,75,85,60\n9,Conventional toothbrush,Personal care,Plastic,Cardboard and plastic blister,Low-cost toothbrush with replaceable use cycle,Entire handle is often discarded,Consider replaceable-head options if compatible and durable,Material claims and recycling routes vary,35,45,45,55,30\n10,Replaceable-head toothbrush,Personal care,Reusable handle with replaceable head,Compact packaging,Only the brush head needs regular replacement,Replacement heads still create waste,Use compatible heads and check material disposal,Availability and actual material mix vary,60,75,70,80,55\n11,Disposable cleaning spray bottle,Home cleaning,Plastic bottle and trigger,Plastic bottle plus label,Ready-to-use household cleaner,Packaging and leftover liquid can be wasted,Use measured dispensing and refill options,Refills help only when total packaging is reduced,35,50,25,45,35\n12,Refillable cleaning bottle,Home cleaning,Durable plastic or glass,Refill pouch or concentrate,Reusable container with refill format,Refill packaging may still be significant,Compare packaging per volume and follow dilution instructions,Concentrate transport and refill material matter,55,75,65,80,55\n13,Standard notebook,Stationery,Paper and cardboard,Paper wrap,Bound notebook for writing,Unused pages may be discarded with the notebook,Finish existing notebooks and consider refillable formats,Binding and refill availability vary,65,55,70,65,65\n14,Refillable notebook,Stationery,Reusable cover and replaceable paper,Minimal packaging,Reusable cover with refill pages,Refills still use paper,Replace only the pages needed and use both sides,Extra hardware is only beneficial if reused,60,80,75,85,65\n15,Non-repairable charging cable,Electronics,Plastic and copper,Small cardboard or plastic pack,Cable with fixed connector assembly,Failure near one connector can discard the whole cable,Look for reinforced strain relief and repairable modular parts,Modular products may cost more or be hard to find,40,30,45,70,25\n16,Modular repairable cable concept,Electronics,Replaceable connector modules,Compact recyclable packaging,Concept design allowing a failed connector to be replaced,Design is a proposal and may not be commercially available,Prototype replaceable connectors and document repair instructions,Compatibility and safety testing are essential,60,80,75,85,65\n17,Fast-fashion synthetic shirt,Clothing,Polyester blend,Plastic mailer or tag,Low-cost synthetic garment,Short use cycles and difficult fibre recycling,Buy fewer durable items and extend wear life,Recycled fibres do not remove all shedding or end-of-life issues,35,40,35,45,30\n18,Durable repairable shirt,Clothing,Cotton or durable blend,Minimal packaging,Garment intended for repeated wear and repair,May still be discarded due to fit or style changes,Choose versatile fit and repair small damage,Material impact depends on fibre source and production,55,75,70,85,50\n19,Single-use food container,Food containers,Plastic or coated fibre,Single-use container,Takeaway container for one meal,Frequent packaging waste,Choose reusable containers where washing and return are practical,Food safety and cleaning requirements matter,30,25,20,30,30\n20,Reusable food container,Food containers,Durable glass or stainless steel,Minimal packaging,Container designed for repeated meal storage,Can be lost or left unused,Use regularly and maintain the seal,Heavier manufacture and washing must be considered,65,85,80,90,70\n21,Disposable batteries,Household,Primary battery chemistry,Cardboard and plastic pack,Single-use battery for low-drain devices,Repeated battery purchases and disposal,Use rechargeable batteries for compatible frequent-use devices,Rechargeable batteries are not ideal for every device or use,40,40,50,45,35\n22,Rechargeable battery set,Household,Rechargeable battery chemistry,Cardboard pack,Rechargeable cells for repeated use,May be unsuitable for infrequently used devices,Match charger and battery type to the device,Charging electricity and eventual proper recycling matter,55,80,70,85,55\n23,Plastic-wrapped soap bars,Personal care,Soap and plastic film,Plastic wrap,Bar soap in plastic packaging,Packaging after each purchase,Choose paper-wrapped or unpackaged options when hygiene and availability allow,Paper is not automatically better if coatings or waste are high,55,60,35,70,55\n24,Paper-wrapped soap bar,Personal care,Soap and paper,Paper wrap,Bar soap with paper packaging,Paper packaging still requires resources,Use fully and recycle packaging if locally accepted,"Check inks, coatings, and local recycling acceptance",60,60,75,70,65\n'

@st.cache_data
def load_data():
    """Load products from common deployment paths, falling back safely if needed."""
    candidate_paths = [
        DATA_PATH,
        Path.cwd() / "products.csv",
        Path.cwd() / "revora" / "products.csv",
    ]
    existing_paths = []
    for path in candidate_paths:
        try:
            resolved = path.resolve()
            if resolved not in existing_paths and resolved.is_file():
                existing_paths.append(resolved)
        except OSError:
            continue

    df = None
    load_notice = ""
    for path in existing_paths:
        try:
            df = pd.read_csv(path, encoding="utf-8-sig", on_bad_lines="error")
            load_notice = f"Loaded product data from `{path.name}`."
            break
        except (pd.errors.ParserError, UnicodeDecodeError, OSError, ValueError):
            # Try another candidate, then use the known-good embedded copy.
            continue

    if df is None:
        df = pd.read_csv(io.StringIO(_FALLBACK_PRODUCTS_CSV))
        if existing_paths:
            load_notice = (
                "The uploaded products.csv could not be parsed, so REVORA is using "
                "its built-in validated product dataset. Replace products.csv with "
                "the corrected file to use your editable dataset."
            )
        else:
            load_notice = (
                "products.csv was not found beside app.py. REVORA is using its "
                "built-in product dataset so the app can still run. Upload the "
                "corrected products.csv beside app.py when possible."
            )

    required_columns = [
        "product_id", "product_name", "category", "material", "packaging",
        "description", "waste_risk", "design_opportunity", "tradeoff",
        "material_score", "lifecycle_score", "packaging_score", "usage_score",
        "end_of_life_score",
    ]
    missing = [column for column in required_columns if column not in df.columns]
    if missing:
        df = pd.read_csv(io.StringIO(_FALLBACK_PRODUCTS_CSV))
        load_notice = (
            "The product CSV was missing required columns, so REVORA is using "
            "its built-in validated product dataset."
        )

    numeric = [
        "material_score", "lifecycle_score", "packaging_score",
        "usage_score", "end_of_life_score",
    ]
    for col in numeric:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(50).clip(0, 100)
    return df, load_notice

df, data_load_notice = load_data()
if data_load_notice and "built-in" in data_load_notice:
    st.warning(data_load_notice)

WEIGHTS = {
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

def score_product(row):
    return round(sum(float(row[col]) * weight for col, weight in WEIGHTS.items()), 1)

def intervention_for(problem, product_name):
    rules = {
        "Breaks before the rest wears out": (
            "Prioritize a repairable or modular design",
            "Look for replaceable parts, accessible fasteners, spare-part availability, and a repair guide. Avoid replacing the whole product when one component fails."
        ),
        "Too much product is dispensed or used": (
            "Choose controlled-dose or refillable packaging",
            "A measured dispenser, adjustable opening, or refill pack may reduce overuse and packaging. Check that the refill format is actually available locally."
        ),
        "Packaging is excessive": (
            "Prefer right-sized, concentrated, or refill packaging",
            "Compare packaging per use—not just package size. Concentrates and refills help only when they reduce total material and are used as intended."
        ),
        "Product is rarely used": (
            "Borrow, share, or keep using what you own",
            "Before buying a greener replacement, test whether sharing, renting, repairing, or changing your routine solves the need without a new product."
        ),
        "Single-use waste builds up": (
            "Switch to a durable alternative if reuse is frequent",
            "Compare expected lifetime uses, cleaning needs, and end-of-life options. A reusable product is most helpful when it replaces many single-use items."
        ),
        "Hard to recycle or dispose of": (
            "Choose simpler materials and a known take-back route",
            "Prefer clearly labelled materials and check local collection rules. 'Compostable' does not necessarily mean it can go in a home compost or local bin."
        ),
    }
    return rules[problem]

def generate_recommendation(problem, category, current_row, candidates):
    title, explanation = intervention_for(problem, current_row["product_name"])
    if problem == "Product is rarely used":
        candidates = candidates[candidates["category"] == category]
        return title, explanation, candidates.sort_values("eco_score", ascending=False).head(3)
    same_category = candidates[candidates["category"] == category].copy()
    if same_category.empty:
        same_category = candidates.copy()
    current_score = float(current_row["eco_score"])
    same_category = same_category[same_category["product_name"] != current_row["product_name"]]
    same_category["score_gain"] = same_category["eco_score"] - current_score
    same_category = same_category.sort_values(["eco_score", "score_gain"], ascending=False)
    return title, explanation, same_category.head(3)

# -------------------- Marketplace database --------------------

def db_connect():
    conn = sqlite3.connect(DB_PATH, timeout=20, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

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
            created_at TEXT NOT NULL
        )
        """)
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
        conn.execute("CREATE INDEX IF NOT EXISTS idx_items_status ON items(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_requests_item_id ON requests(item_id)")

def hash_pin(pin):
    return hashlib.sha256(pin.encode("utf-8")).hexdigest()

def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def get_items(status=None, category=None, search_text=None):
    sql = "SELECT * FROM items"
    clauses, params = [], []
    if status and status != "All":
        clauses.append("status = ?")
        params.append(status)
    if category and category != "All categories":
        clauses.append("category = ?")
        params.append(category)
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
        return conn.execute(
            "SELECT * FROM requests WHERE item_id = ? ORDER BY created_at DESC", (item_id,)
        ).fetchall()

def get_request_for_tracking(request_id, requester_contact):
    with db_connect() as conn:
        return conn.execute(
            """SELECT r.*, i.item_name, i.status AS item_status,
                      i.donor_contact, i.contact_type, i.location
               FROM requests r JOIN items i ON i.id = r.item_id
               WHERE r.id = ? AND lower(r.requester_contact) = lower(?)""",
            (request_id, requester_contact.strip())
        ).fetchone()

def item_request_count(item_id):
    with db_connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM requests WHERE item_id = ?", (item_id,)
        ).fetchone()
        return int(row["n"])

def safe_text(value):
    return html.escape(str(value or ""))

init_db()

# -------------------- Sidebar and hero --------------------

with st.sidebar:
    st.markdown("## 🌱 REVORA")
    st.caption("Waste-to-Design Intelligence")
    st.markdown("---")
    st.markdown("**Explore both sides of sustainability**")
    st.write("♻️ Discover better product choices")
    st.write("🤝 Pass useful items to someone who needs them")
    st.markdown("---")
    st.caption("Demo EcoScores are heuristic estimates, not verified lifecycle assessments.")
    st.caption("Marketplace listings are community-submitted; arrange safe handovers.")

st.markdown("""
<div class="hero">
  <div class="pill">WASTE-TO-DESIGN INTELLIGENCE</div>
  <h1>REVORA</h1>
  <p>Turn waste into better design.</p>
  <p style="font-size:.94rem">Discover better product choices. Donate useful items. Request what you need. Keep good things in use.</p>
</div>
""", unsafe_allow_html=True)

# Tabs preserve the original product explorer and add the marketplace.
tab_explore, tab_ai, tab_browse, tab_donate, tab_manage, tab_track = st.tabs([
    "🌿 Product Explorer", "🤖 REVORA AI Chat", "🔎 Browse Donations", "🎁 Donate an Item", "📬 Manage Requests", "📦 Track My Request"
])

# -------------------- Original product explorer --------------------

with tab_explore:
    st.markdown("## Explore the product lifecycle")
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Products in prototype", len(df))
    with m2:
        st.metric("Product categories", df["category"].nunique())
    with m3:
        with db_connect() as conn:
            total_available = conn.execute("SELECT COUNT(*) AS n FROM items WHERE status='Available'").fetchone()["n"]
        st.metric("Items available to reuse", int(total_available))

    filter_col1, filter_col2, filter_col3 = st.columns([1, 1, 1])
    with filter_col1:
        categories = ["All categories"] + sorted(df["category"].unique().tolist())
        selected_category = st.selectbox("Product category", categories, key="explore_category")
    with filter_col2:
        problem_options = [
            "Single-use waste builds up",
            "Breaks before the rest wears out",
            "Too much product is dispensed or used",
            "Packaging is excessive",
            "Product is rarely used",
            "Hard to recycle or dispose of",
        ]
        problem = st.selectbox("Main waste problem", problem_options, key="explore_problem")
    with filter_col3:
        priority = st.selectbox(
            "Your priority",
            ["Overall sustainability", "Longer lifespan", "Less packaging", "Repairability", "Reuse potential"],
            key="explore_priority",
        )

    search = st.text_input("Search products", placeholder="Try: bottle, notebook, cable, cleaner...", key="product_search")
    filtered = df.copy()
    if selected_category != "All categories":
        filtered = filtered[filtered["category"] == selected_category]
    if search.strip():
        filtered = filtered[filtered.apply(lambda r: search.lower() in " ".join(map(str, r.values)).lower(), axis=1)]
    filtered["eco_score"] = filtered.apply(score_product, axis=1)
    if priority == "Longer lifespan":
        filtered["rank_score"] = filtered["lifecycle_score"]
    elif priority == "Less packaging":
        filtered["rank_score"] = filtered["packaging_score"]
    elif priority == "Repairability":
        filtered["rank_score"] = filtered["end_of_life_score"]
    elif priority == "Reuse potential":
        filtered["rank_score"] = filtered["usage_score"]
    else:
        filtered["rank_score"] = filtered["eco_score"]
    filtered = filtered.sort_values("rank_score", ascending=False)

    if filtered.empty:
        st.info("No matching products. Try another search or category.")
    else:
        cols = st.columns(3)
        for idx, (_, row) in enumerate(filtered.head(9).iterrows()):
            with cols[idx % 3]:
                st.markdown(f"""
                <div class="result-card">
                    <div class="muted">{safe_text(row['category'])}</div>
                    <h3 style="margin:.35rem 0">{safe_text(row['product_name'])}</h3>
                    <div class="big-score">{row['eco_score']:.0f}<span style="font-size:.9rem;color:#627268"> / 100 EcoScore</span></div>
                    <p style="min-height:3.2rem">{safe_text(row['description'])}</p>
                    <span class="pill">{safe_text(row['material'])}</span>
                </div>
                """, unsafe_allow_html=True)
                if st.button("Analyze waste pattern", key=f"analyze_{row['product_id']}"):
                    st.session_state.selected_product_id = row["product_id"]

    if "selected_product_id" in st.session_state:
        chosen_matches = df[df["product_id"] == st.session_state.selected_product_id]
        if not chosen_matches.empty:
            chosen = chosen_matches.iloc[0].copy()
            chosen["eco_score"] = score_product(chosen)
            st.markdown("---")
            st.markdown("## Your waste-to-design analysis")
            st.markdown(f"### {chosen['product_name']}")
            st.write(f"**Likely waste pattern:** {chosen['waste_risk']}")
            st.write(f"**Design opportunity:** {chosen['design_opportunity']}")
            st.write(f"**Material:** {chosen['material']} · **Packaging:** {chosen['packaging']}")
            title, explanation = intervention_for(problem, chosen["product_name"])
            st.success(f"**Suggested intervention: {title}**")
            st.write(explanation)
            st.markdown("### Lifecycle score breakdown")
            score_cols = st.columns(5)
            for col, key in zip(score_cols, WEIGHTS.keys()):
                with col:
                    st.metric(DISPLAY_NAMES[key], f"{chosen[key]:.0f}/100")
            st.progress(min(1.0, max(0.0, chosen["eco_score"] / 100)))
            st.caption(f"Weighted EcoScore: {chosen['eco_score']:.1f}/100. Weights: materials 25%, lifespan 25%, packaging 15%, usage 20%, end-of-life 15%.")
            candidates = df.copy()
            candidates["eco_score"] = candidates.apply(score_product, axis=1)
            heading, details, recs = generate_recommendation(problem, chosen["category"], chosen, candidates)
            st.markdown("### Recommended next steps")
            st.write(details)
            if problem == "Product is rarely used":
                st.info("Consider borrowing, sharing, or keeping your current item before purchasing a replacement.")
            if recs.empty:
                st.info("No alternative in this sample dataset. Try another category or product.")
            else:
                rec_cols = st.columns(min(3, len(recs)))
                for col, (_, rec) in zip(rec_cols, recs.iterrows()):
                    with col:
                        st.markdown(f"""
                        <div class="result-card">
                          <div class="muted">{safe_text(rec['category'])}</div>
                          <h4>{safe_text(rec['product_name'])}</h4>
                          <div class="big-score">{rec['eco_score']:.0f}<span style="font-size:.8rem;color:#627268"> / 100</span></div>
                          <p>{safe_text(rec['description'])}</p>
                          <p><b>Trade-off:</b> {safe_text(rec['tradeoff'])}</p>
                        </div>
                        """, unsafe_allow_html=True)
            st.caption("Recommendations use an illustrative demo dataset. Verify product claims and lifecycle evidence before making real-world comparisons.")
    with st.expander("How the EcoScore works"):
        st.write("EcoScore is a weighted heuristic score designed for this prototype.")
        st.latex(r"EcoScore = 0.25M + 0.25L + 0.15P + 0.20U + 0.15E")
        st.write("M = materials and sourcing; L = durability and lifespan; P = packaging; U = usage and reuse; E = repairability and end-of-life.")
        st.warning("Values are illustrative demo inputs, not measured carbon footprints or certified environmental claims.")

# -------------------- Gemini AI chatbox --------------------

with tab_ai:
    st.markdown("## 🤖 Chat with REVORA AI")
    st.write("Ask about reducing waste, choosing reusable products, repairing items, or using the Donate & Request marketplace.")
    st.markdown("<div class='marketplace-note'><b>REVORA AI</b> gives practical sustainability guidance. It can make mistakes, so verify important product, recycling, and safety information locally.</div>", unsafe_allow_html=True)

    if "revora_chat_history" not in st.session_state:
        st.session_state.revora_chat_history = []

    chat_col, clear_col = st.columns([5, 1])
    with chat_col:
        st.caption("Powered by Google's Gemini API")
    with clear_col:
        if st.button("Clear chat", key="clear_revora_chat"):
            st.session_state.revora_chat_history = []
            st.rerun()

    for message in st.session_state.revora_chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("Ask REVORA anything about sustainability...", key="revora_chat_input")
    if prompt:
        st.session_state.revora_chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        try:
            try:
                api_key = st.secrets["GEMINI_API_KEY"]
            except Exception:
                api_key = ""
            if not api_key:
                raise KeyError("GEMINI_API_KEY is not configured")

            from google import genai
            client = genai.Client(api_key=api_key)

            recent_history = st.session_state.revora_chat_history[-12:]
            transcript = "\n\n".join(
                ("User" if m["role"] == "user" else "REVORA AI") + ": " + m["content"]
                for m in recent_history
            )
            system_context = """You are REVORA AI, a helpful sustainability and circular-economy assistant inside a community reuse website.

Your goals:
- Give practical, affordable ways to reduce waste, reuse, repair, share, and donate usable items.
- Explain trade-offs honestly; do not invent exact carbon, water, money, or landfill savings.
- Do not claim a product is certified or a local item is available unless verified in the app.
- Encourage users to use REVORA's Donate & Request tabs when they want to pass on or request usable items.
- For recycling questions, explain that local rules differ and suggest checking the local authority.
- Keep answers friendly, clear, and reasonably concise.
- Do not ask users to share passwords, API keys, or sensitive personal information.
"""
            with st.chat_message("assistant"):
                with st.spinner("REVORA AI is thinking..."):
                    response = client.models.generate_content(
                        model="gemini-3.5-flash-lite",
                        contents=system_context + "\n\nConversation so far:\n" + transcript,
                    )
                    answer = response.text or "I couldn't generate a response this time. Please try asking in a different way."
                st.markdown(answer)
            st.session_state.revora_chat_history.append({"role": "assistant", "content": answer})
        except KeyError:
            st.error("Gemini API key not configured. Add GEMINI_API_KEY in your Streamlit Cloud app Settings → Secrets, then reboot the app.")
        except Exception:
            st.error("REVORA AI couldn't connect to Gemini. Check that your API key is valid, the google-genai package is installed, and your API quota/model access is available.")

    if not st.session_state.revora_chat_history:
        st.markdown("**Try asking:**")
        st.caption("How can I reduce plastic waste at home? · Should I repair or replace a product? · What items are good to donate?")

# -------------------- Browse available items and submit requests --------------------

with tab_browse:
    st.markdown("## ♻️ Browse donations")
    st.write("Find useful items nearby and request them directly from the donor.")
    browse_col1, browse_col2, browse_col3 = st.columns([1, 1, 1.2])
    with browse_col1:
        browse_categories = ["All categories", "Clothing & shoes", "Books & education", "Electronics", "Home & kitchen", "Toys & games", "Sports & outdoors", "Other"]
        browse_category = st.selectbox("Category", browse_categories, key="browse_category")
    with browse_col2:
        browse_search = st.text_input("Search items or area", placeholder="e.g. textbooks, Bengaluru", key="browse_search")
    with browse_col3:
        st.caption("Only available items are shown. Donor contact details are kept private until a request is approved.")
    items = get_items(status="Available", category=browse_category, search_text=browse_search.strip())
    if not items:
        st.info("No matching donations yet. Be the first to list a useful item in the Donate an Item tab.")
    else:
        st.caption(f"{len(items)} available item(s)")
        for item in items:
            with st.container(border=True):
                left, right = st.columns([3, 1])
                with left:
                    st.markdown(f"### {safe_text(item['item_name'])}")
                    st.markdown(f"<span class='pill'>{safe_text(item['category'])}</span> &nbsp; <span class='muted'>{safe_text(item['item_condition'])}</span>", unsafe_allow_html=True)
                    st.write(safe_text(item["description"]))
                    st.caption(f"📍 {safe_text(item['location'])} · Listed by {safe_text(item['donor_name'])} · {item['created_at'][:10]}")
                    st.caption(f"{item_request_count(item['id'])} request(s) received")
                with right:
                    with st.form(f"request_form_{item['id']}"):
                        st.markdown("**Request this item**")
                        req_name = st.text_input("Your name", key=f"req_name_{item['id']}", max_chars=80)
                        req_contact = st.text_input("Your email or phone", key=f"req_contact_{item['id']}", max_chars=120)
                        req_message = st.text_area("Message to donor", placeholder="Tell the donor why you need it and when you can collect it.", key=f"req_msg_{item['id']}", max_chars=500)
                        confirm = st.checkbox("I will arrange a safe handover.", key=f"req_confirm_{item['id']}")
                        submitted = st.form_submit_button("Send request", use_container_width=True)
                    if submitted:
                        if not req_name.strip() or not req_contact.strip() or not req_message.strip():
                            st.error("Please complete your name, contact, and message.")
                        elif not confirm:
                            st.error("Please confirm safe handover.")
                        else:
                            with db_connect() as conn:
                                current = conn.execute("SELECT status FROM items WHERE id=?", (item["id"],)).fetchone()
                                if not current or current["status"] != "Available":
                                    st.error("Sorry, this item is no longer available.")
                                else:
                                    cursor = conn.execute(
                                        "INSERT INTO requests (item_id, requester_name, requester_contact, message, status, created_at) VALUES (?, ?, ?, ?, 'Pending', ?)",
                                        (item["id"], req_name.strip(), req_contact.strip(), req_message.strip(), now_iso())
                                    )
                                    request_id = cursor.lastrowid
                                    st.session_state.last_request_id = request_id
                                    st.success(f"Request sent! Save your request ID: REV-R{request_id:05d}")
                                    st.info("Use the Track My Request tab and your contact detail to check approval status.")

# -------------------- Donate an item --------------------

with tab_donate:
    st.markdown("## 🎁 Give a useful item a second life")
    st.write("List items that are clean, safe, and in usable condition. You can approve or decline requests later.")
    st.markdown("""
    <div class="marketplace-note">
    <b>Privacy tip:</b> Your contact information is only shown to requesters after you approve their request.
    Keep your listing PIN private; it is used to manage requests for your item.
    </div>
    """, unsafe_allow_html=True)
    with st.form("donate_item_form", clear_on_submit=True):
        d1, d2 = st.columns(2)
        with d1:
            item_name = st.text_input("Item name *", placeholder="e.g. First-year engineering textbooks", max_chars=100)
            item_category = st.selectbox("Category *", ["Clothing & shoes", "Books & education", "Electronics", "Home & kitchen", "Toys & games", "Sports & outdoors", "Other"])
            item_condition = st.selectbox("Condition *", ["Like new", "Good", "Used but working", "Needs minor repair"])
            item_location = st.text_input("Area / city *", placeholder="e.g. Kasturi Nagar, Bengaluru", max_chars=120)
        with d2:
            donor_name = st.text_input("Your display name *", placeholder="First name or nickname", max_chars=80)
            donor_contact = st.text_input("Your email or phone *", placeholder="Used to contact you after approval", max_chars=120)
            contact_type = st.selectbox("Contact preference", ["Email", "Phone / WhatsApp", "Either"])
            listing_pin = st.text_input("Create a private 6+ character listing PIN *", type="password", max_chars=64)
        item_description = st.text_area("Description *", placeholder="Mention size, model, included accessories, defects, pickup conditions, etc.", max_chars=1000)
        safety_confirm = st.checkbox("I confirm this item is legal, safe to give away, and described honestly.")
        submit_donation = st.form_submit_button("Publish donation listing", use_container_width=True)
    if submit_donation:
        if not all([item_name.strip(), item_location.strip(), donor_name.strip(), donor_contact.strip(), item_description.strip(), listing_pin]):
            st.error("Please complete all required fields.")
        elif len(listing_pin) < 6:
            st.error("Choose a PIN of at least 6 characters.")
        elif not safety_confirm:
            st.error("Please confirm the item is safe and accurately described.")
        else:
            with db_connect() as conn:
                cursor = conn.execute(
                    """INSERT INTO items
                    (item_name, category, item_condition, location, description, donor_name, donor_contact, contact_type, pin_hash, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Available', ?)""",
                    (item_name.strip(), item_category, item_condition, item_location.strip(), item_description.strip(),
                     donor_name.strip(), donor_contact.strip(), contact_type, hash_pin(listing_pin), now_iso())
                )
                new_id = cursor.lastrowid
            st.success(f"Your donation is listed! Your listing ID is **REV-{new_id:05d}**. Save this ID and your private PIN to manage requests.")
            st.info("Your contact details are not displayed publicly. They are revealed to a requester only after you approve their request.")
            st.code(f"Listing ID: REV-{new_id:05d}", language=None)

# -------------------- Donor request management --------------------

with tab_manage:
    st.markdown("## 📬 Manage your donation requests")
    st.write("Enter your listing ID and private PIN to view requests and approve or decline them.")
    st.markdown("""
    <div class="marketplace-note">
    <b>How approval works:</b> approving a request shares your contact preference and contact details with that requester, marks the item as reserved, and declines other pending requests for the same item. Final handover is arranged by both people.
    </div>
    """, unsafe_allow_html=True)
    with st.form("manage_listing_form"):
        manage_id_text = st.text_input("Listing ID", placeholder="e.g. REV-00012")
        manage_pin = st.text_input("Private listing PIN", type="password")
        load_listing = st.form_submit_button("View requests", use_container_width=True)
    if load_listing:
        cleaned = manage_id_text.strip().upper()
        try:
            listing_id = int(cleaned.replace("REV-", ""))
            listing = get_item(listing_id)
            if not listing or not secrets.compare_digest(listing["pin_hash"], hash_pin(manage_pin)):
                st.error("Listing ID or PIN is incorrect.")
                st.session_state.pop("managed_listing_id", None)
            else:
                st.session_state.managed_listing_id = listing_id
        except (ValueError, TypeError):
            st.error("Enter a valid listing ID, such as REV-00012.")
            st.session_state.pop("managed_listing_id", None)

    if st.session_state.get("managed_listing_id"):
        listing = get_item(st.session_state.managed_listing_id)
        if listing:
            # Require re-entry of the PIN each time a new listing is loaded; after a successful check, session is trusted.
            st.markdown(f"### {safe_text(listing['item_name'])}")
            st.caption(f"REV-{listing['id']:05d} · {safe_text(listing['status'])} · {safe_text(listing['location'])}")
            st.write(safe_text(listing["description"]))
            requests = get_requests_for_item(listing["id"])
            if not requests:
                st.info("No requests yet. Your listing is visible in Browse Donations.")
            else:
                for req in requests:
                    with st.container(border=True):
                        req_col, status_col = st.columns([3, 1])
                        with req_col:
                            st.markdown(f"**Request from {safe_text(req['requester_name'])}**")
                            st.write(safe_text(req["message"]))
                            st.caption(f"Requester contact: {safe_text(req['requester_contact'])} · Sent {req['created_at'][:10]}")
                        with status_col:
                            st.markdown(f"**{safe_text(req['status'])}**")
                            if req["status"] == "Pending" and listing["status"] == "Available":
                                approve_col, decline_col = st.columns(2)
                                with approve_col:
                                    if st.button("Approve", key=f"approve_{req['id']}", use_container_width=True):
                                        with db_connect() as conn:
                                            conn.execute("UPDATE requests SET status='Approved' WHERE id=? AND status='Pending'", (req["id"],))
                                            conn.execute("UPDATE items SET status='Reserved' WHERE id=?", (listing["id"],))
                                            conn.execute("UPDATE requests SET status='Declined' WHERE item_id=? AND id<>? AND status='Pending'", (listing["id"], req["id"]))
                                        st.success("Request approved. The requester can now see your contact details.")
                                        st.rerun()
                                with decline_col:
                                    if st.button("Decline", key=f"decline_{req['id']}", use_container_width=True):
                                        with db_connect() as conn:
                                            conn.execute("UPDATE requests SET status='Declined' WHERE id=? AND status='Pending'", (req["id"],))
                                        st.rerun()
                            elif req["status"] == "Approved":
                                st.success(f"Approved. Contact: {listing['donor_contact']} ({listing['contact_type']})")
            if listing["status"] == "Reserved":
                st.warning("This item is reserved. After the handover, mark it as donated below.")
                if st.button("Mark as donated / completed", key=f"complete_{listing['id']}"):
                    with db_connect() as conn:
                        conn.execute("UPDATE items SET status='Donated' WHERE id=?", (listing["id"],))
                    st.success("Thanks for keeping a useful item in circulation!")
                    st.rerun()
            if listing["status"] == "Available":
                with st.expander("Unlist this item"):
                    st.warning("Unlisting hides it from new requests.")
                    if st.button("Unlist donation", key=f"unlist_{listing['id']}"):
                        with db_connect() as conn:
                            conn.execute("UPDATE items SET status='Removed' WHERE id=?", (listing["id"],))
                            conn.execute("UPDATE requests SET status='Declined' WHERE item_id=? AND status='Pending'", (listing["id"],))
                        st.success("Listing removed.")
                        st.rerun()

# -------------------- Requester tracking --------------------

with tab_track:
    st.markdown("## 📦 Track your request")
    st.write("Check whether the donor has approved your request. Enter the request ID shown when you submitted it and the same contact detail you used.")
    if st.session_state.get("last_request_id"):
        st.info(f"Your most recent request ID in this session: **REV-R{st.session_state.last_request_id:05d}**")
    with st.form("track_request_form"):
        track_id_text = st.text_input("Request ID", placeholder="e.g. REV-R00012")
        track_contact = st.text_input("Your email or phone used for the request")
        track_submit = st.form_submit_button("Check request status", use_container_width=True)
    if track_submit:
        cleaned_request_id = track_id_text.strip().upper()
        try:
            request_id = int(cleaned_request_id.replace("REV-R", ""))
            tracked = get_request_for_tracking(request_id, track_contact)
            if not tracked:
                st.error("We couldn't find a request matching that ID and contact detail.")
            else:
                st.markdown(f"### {safe_text(tracked['item_name'])}")
                st.markdown(f"**Request status:** {safe_text(tracked['status'])}")
                st.caption(f"Location: {safe_text(tracked['location'])}")
                if tracked["status"] == "Pending":
                    st.info("Your request is waiting for the donor to review it.")
                elif tracked["status"] == "Declined":
                    st.warning("The donor declined this request. You can browse other available items.")
                elif tracked["status"] == "Approved":
                    st.success("Your request was approved! Contact the donor to coordinate a safe handover.")
                    st.markdown(f"**Donor contact:** {safe_text(tracked['donor_contact'])} ({safe_text(tracked['contact_type'])})")
                    st.caption("Please agree on the handover directly and do not send money to strangers.")
                else:
                    st.info(f"The item status is {safe_text(tracked['item_status'])}.")
        except (ValueError, TypeError):
            st.error("Enter a valid request ID, such as REV-R00012.")

st.markdown("---")
st.markdown("### 🌍 Small actions, less waste")
st.caption("REVORA is a community reuse prototype. Meet in a public place where practical, inspect items before accepting them, avoid sending money to strangers, and never list unsafe or illegal items.")
st.caption("Deployment note: this starter version stores marketplace data in a local SQLite database. On Streamlit Community Cloud, that database can be lost when the app is rebuilt or its runtime is reset. For reliable long-term shared listings, connect a hosted database such as Supabase before launching publicly.")
