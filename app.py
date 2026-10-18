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

# -------------------- Sidebar with Theme Toggle & Weight Customizer --------------------

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

with st.sidebar:
    st.markdown("## 🌱 REVORA")
    st.caption("Waste-to-Design & Circular Reuse")
    dark_mode = st.toggle("🌙 Midnight Forest Dark Mode", value=False, key="revora_dark_mode")
    st.markdown("---")
    st.markdown("**✨ What You Can Do Here**")
    st.write("🌿 **Explore** 42+ product lifecycles")
    st.write("📌 **Wish Board** (Post & fulfill needs)")
    st.write("🕸️ **Compare** products on Radar Charts")
    st.write("📸 **Scan** item condition with AI")
    st.write("🎙️ **Ask** via Voice Search & Read Aloud")
    st.write("🤝 **Donate & Request** community items")

    st.markdown("---")
    with st.expander("🎛️ Customize EcoScore Weights", expanded=False):
        st.caption("Adjust sliders to personalize how REVORA calculates EcoScores:")
        w_m = st.slider("Materials & sourcing", 0, 100, 25, 5, key="w_m")
        w_l = st.slider("Durability & lifespan", 0, 100, 25, 5, key="w_l")
        w_p = st.slider("Packaging impact", 0, 100, 15, 5, key="w_p")
        w_u = st.slider("Usage & reuse", 0, 100, 20, 5, key="w_u")
        w_e = st.slider("Repair & end-of-life", 0, 100, 15, 5, key="w_e")
        total_w = max(1, w_m + w_l + w_p + w_u + w_e)
        WEIGHTS = {
            "material_score": w_m / total_w,
            "lifecycle_score": w_l / total_w,
            "packaging_score": w_p / total_w,
            "usage_score": w_u / total_w,
            "end_of_life_score": w_e / total_w,
        }
    if "WEIGHTS" not in locals():
        WEIGHTS = DEFAULT_WEIGHTS.copy()

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
        gap: 8px; background: var(--tab-bar-bg); backdrop-filter: blur(10px);
        padding: 8px 10px; border-radius: 18px; border: 1px solid var(--card-border); margin-bottom: 1rem;
    }}
    button[data-baseweb="tab"] {{ border-radius: 12px !important; padding: 9px 16px !important; font-weight: 600 !important; color: var(--tab-text) !important; }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        background: linear-gradient(135deg, #1b6741 0%, #2d8659 100%) !important; color: #ffffff !important;
        box-shadow: 0 4px 12px rgba(27, 103, 65, 0.28) !important;
    }}
    div[data-baseweb="tab-highlight"] {{ display: none !important; }}
    div[data-testid="stMetric"] {{ background: var(--card-bg); border: 1px solid var(--card-border); padding: 14px 18px; border-radius: 18px; }}
    .marketplace-note {{ border: 1px solid var(--card-border); border-left: 5px solid #2e8b57; border-radius: 16px; padding: 1rem 1.2rem; background: var(--note-bg); margin: .5rem 0 1.1rem; }}
</style>
""", unsafe_allow_html=True)

# -------------------- Expanded 42-Product Errorless Dataset --------------------

_FALLBACK_PRODUCTS_CSV = '''product_id,product_name,category,material,packaging,description,waste_risk,design_opportunity,tradeoff,material_score,lifecycle_score,packaging_score,usage_score,end_of_life_score
1,Disposable PET water bottle,Drinkware,PET plastic,Single-use plastic bottle,Convenient single-use water container,Repeated single-use packaging,Refill from safe drinking water or use a durable bottle when used frequently,Reusable alternatives require repeated use and cleaning,35,25,20,25,35
2,Reusable stainless steel bottle,Drinkware,Stainless steel,Minimal or cardboard packaging,Durable bottle designed for repeated use,Can be underused or lost,Use consistently for many refill cycles,Material-intensive manufacture and cleaning needs matter,65,85,80,90,65
3,Reusable glass bottle,Drinkware,Glass,Cardboard or protective packaging,Reusable bottle for home or office,Breakage can shorten lifespan,Use in settings where breakage risk is low,Heavier transport and breakage risk,70,70,75,80,70
4,Single-use shopping bag,Bags,Thin plastic,No additional packaging,Lightweight carrier bag,Often discarded after one trip,Reuse bags already owned before acquiring new ones,Some reusable bags require many uses to offset production,25,20,30,25,25
5,Reusable fabric tote,Bags,Cotton or blended fabric,Minimal packaging,Reusable shopping bag,May accumulate unused bags,Keep a small set and reuse frequently,Cotton production can be resource intensive,55,75,75,80,60
6,Recycled-content paper bag,Bags,Recycled paper,Paper bag,Paper carrier with recycled content,May tear when wet or overloaded,Reuse when practical and recycle where accepted,Not always lower impact than reusing a bag already owned,70,45,65,50,75
7,Disposable coffee cup,Food & drink,Paper with possible lining,Single-use cup,Takeaway cup used for one drink,Repeated cups and lids,Bring a cup or use dine-in service when practical,Reusable cup benefits depend on repeated use and washing,45,20,20,25,35
8,Reusable coffee cup,Food & drink,Stainless steel or durable plastic,Minimal packaging,Reusable cup for takeaway drinks,May be forgotten or rarely used,Store it where it is easy to remember,Manufacture and washing impacts need repeated use,65,80,75,85,60
9,Conventional toothbrush,Personal care,Plastic,Cardboard and plastic blister,Low-cost toothbrush with replaceable use cycle,Entire handle is often discarded,Consider replaceable-head options if compatible and durable,Material claims and recycling routes vary,35,45,45,55,30
10,Replaceable-head toothbrush,Personal care,Reusable handle with replaceable head,Compact packaging,Only the brush head needs regular replacement,Replacement heads still create waste,Use compatible heads and check material disposal,Availability and actual material mix vary,60,75,70,80,55
11,Disposable cleaning spray bottle,Home cleaning,Plastic bottle and trigger,Plastic bottle plus label,Ready-to-use household cleaner,Packaging and leftover liquid can be wasted,Use measured dispensing and refill options,Refills help only when total packaging is reduced,35,50,25,45,35
12,Refillable cleaning bottle,Home cleaning,Durable plastic or glass,Refill pouch or concentrate,Reusable container with refill format,Refill packaging may still be significant,Compare packaging per volume and follow dilution instructions,Concentrate transport and refill material matter,55,75,65,80,55
13,Standard notebook,Stationery,Paper and cardboard,Paper wrap,Bound notebook for writing,Unused pages may be discarded with the notebook,Finish existing notebooks and consider refillable formats,Binding and refill availability vary,65,55,70,65,65
14,Refillable notebook,Stationery,Reusable cover and replaceable paper,Minimal packaging,Reusable cover with refill pages,Refills still use paper,Replace only the pages needed and use both sides,Extra hardware is only beneficial if reused,60,80,75,85,65
15,Non-repairable charging cable,Electronics,Plastic and copper,Small cardboard or plastic pack,Cable with fixed connector assembly,Failure near one connector can discard the whole cable,Look for reinforced strain relief and repairable modular parts,Modular products may cost more or be hard to find,40,30,45,70,25
16,Modular repairable cable concept,Electronics,Replaceable connector modules,Compact recyclable packaging,Concept design allowing a failed connector to be replaced,Design is a proposal and may not be commercially available,Prototype replaceable connectors and document repair instructions,Compatibility and safety testing are essential,60,80,75,85,65
17,Fast-fashion synthetic shirt,Clothing,Polyester blend,Plastic mailer or tag,Low-cost synthetic garment,Short use cycles and difficult fibre recycling,Buy fewer durable items and extend wear life,Recycled fibres do not remove all shedding or end-of-life issues,35,40,35,45,30
18,Durable repairable shirt,Clothing,Cotton or durable blend,Minimal packaging,Garment intended for repeated wear and repair,May still be discarded due to fit or style changes,Choose versatile fit and repair small damage,Material impact depends on fibre source and production,55,75,70,85,50
19,Single-use food container,Food containers,Plastic or coated fibre,Single-use container,Takeaway container for one meal,Frequent packaging waste,Choose reusable containers where washing and return are practical,Food safety and cleaning requirements matter,30,25,20,30,30
20,Reusable food container,Food containers,Durable glass or stainless steel,Minimal packaging,Container designed for repeated meal storage,Can be lost or left unused,Use regularly and maintain the seal,Heavier manufacture and washing must be considered,65,85,80,90,70
21,Disposable batteries,Household,Primary battery chemistry,Cardboard and plastic pack,Single-use battery for low-drain devices,Repeated battery purchases and disposal,Use rechargeable batteries for compatible frequent-use devices,Rechargeable batteries are not ideal for every device or use,40,40,50,45,35
22,Rechargeable battery set,Household,Rechargeable battery chemistry,Cardboard pack,Rechargeable cells for repeated use,May be unsuitable for infrequently used devices,Match charger and battery type to the device,Charging electricity and eventual proper recycling matter,55,80,70,85,55
23,Plastic-wrapped soap bars,Personal care,Soap and plastic film,Plastic wrap,Bar soap in plastic packaging,Packaging after each purchase,Choose paper-wrapped or unpackaged options when hygiene and availability allow,Paper is not automatically better if coatings or waste are high,55,60,35,70,55
24,Paper-wrapped soap bar,Personal care,Soap and paper,Paper wrap,Bar soap with paper packaging,Paper packaging still requires resources,Use fully and recycle packaging if accepted,"Check inks, coatings, and local recycling acceptance",60,60,75,70,65
25,Fast-fashion denim jeans,Clothing,Cotton and elastane blend,Paper tag,Everyday denim trousers,Fast trends and heavy water consumption during production,"Buy classic cuts, wash less frequently, and repair denim when worn",Blend fibers complicate recycling,45,60,70,75,40
26,Thrifted vintage denim jeans,Clothing,Pre-owned cotton denim,Minimal tag,Secondhand durable denim jeans,Previous wear may require minor tailoring,"Inspect seams and wash before wear",Extends product lifecycle and avoids new manufacturing,90,85,90,95,85
27,Disposable plastic razor,Personal care,Mixed plastics and steel,Blister pack,Cheap disposable shaving razor,Entire unit discarded frequently,Switch to safety razor with replaceable steel blades,Mixed plastics are nearly impossible to recycle locally,20,30,25,30,20
28,Metal safety razor,Personal care,Solid brass or stainless steel,Cardboard box,Classic razor using only replaceable steel blades,Blade changes require basic care,"Use for decades, and recycle only small steel blades",Initial learning curve for shaving technique,85,95,90,90,95
29,Wired over-ear headphones,Electronics,"Plastic, copper, and synthetic leather",Cardboard box,Audio headphones with fixed cable,Cable fraying can ruin the entire unit,Look for replaceable audio cables and ear cushions,Mixed materials complicate end-of-life disassembly,45,60,60,75,45
30,Modular headphones with replaceable parts,Electronics,"Aluminum, fabric, and replaceable modules",Recycled cardboard,Headphones designed with snap-on modular parts,Fixed or glued components make internal fixes difficult,"Replacing ear pads or batteries extends lifespan for years",Higher initial cost but significantly lower long-term waste,75,90,85,90,85
31,Disposable paper plates,Food containers,"Pressed paper with wax coating",Plastic shrink wrap,Single-use tableware for parties and events,High volume of soiled single-use paper waste,Use ceramic or reusable plates for gatherings whenever possible,Wax coating prevents standard paper recycling,35,15,25,30,25
32,Bambootensile cutlery set,Food & drink,Natural bamboo,Cotton pouch,Portable lightweight reusable cutlery,Can split if soaked or improperly dried,"Hand wash and oil occasionally, to maintain bamboo integrity",Natural organic material that eventually biodegrades,80,70,85,85,85
33,Single-use wet wipes,Personal care,Synthetic non-woven plastic fibers,Plastic soft pack,Pre-moistened cleansing wipes,Fibers do not break down in plumbing or landfills,Switch to washable cotton cloths and mild soap/water,Causes severe plumbing clogs and microplastic pollution,15,10,20,20,10
34,Washable organic cotton face rounds,Personal care,100% organic cotton,Mesh laundry bag,Reusable makeup remover and toner pads,Staining or loss of small pads in laundry,Wash in mesh bag and air dry,Replaces hundreds of disposable cotton pads over its lifetime,85,80,85,90,80
35,Plastic kitchen sponge,Home cleaning,Synthetic polyurethane foam,Cellophane wrap,Abrasive kitchen cleaning sponge,Traps bacteria and degrades into microplastics quickly,Switch to natural cellulose sponges or loofahs,Synthetic foam cannot be recycled,25,30,35,40,20
36,Natural loofah sponge,Home cleaning,Natural fibrous plant gourd,Paper band,Plant-based biodegradable dish scrubber,Wears down with heavy scrubbing,Sanitize regularly in boiling water and home compost when worn out,Completely natural and zero plastic waste,95,65,90,80,95
37,Conventional LED light bulb,Household,"Glass, aluminum, and electronics",Cardboard box,Standard energy-efficient home light bulb,Premature burnout from power surges or poor heat sinking,Use quality fixtures and proper disposal at e-waste centers,Contains electronics and small amounts of solder,60,70,75,85,50
38,Repairable modular LED bulb,Household,Aluminum heatsink and replaceable LED module,Recycled paper box,Bulb designed so LED driver or board can be swapped,Requires basic twist-lock disassembly,Extends fixture life and lowers electronic waste,Higher manufacturing precision needed,75,85,85,90,80
39,Single-use bubble mailer,Bags,Plastic film bonded to paper,None,Mailer envelope for shipping items,Impossible to separate plastic film from paper for recycling,Save and reuse mailers or switch to paper-only padded mailers,Composite material goes straight to landfill,20,15,30,30,15
40,All-paper honeycomb mailer,Bags,Kraft paper with internal cushioning structure,Paper band,Fully recyclable padded shipping envelope,Paper can tear if exposed to heavy rain,Reuse when possible and recycle with paper waste,100% paper-based circular recycling stream,85,60,85,75,90
41,Plastic ice cube tray,Home cleaning,Flexible polyethylene plastic,Paper sleeve,Tray for freezing water into ice cubes,Plastic becomes brittle and cracks over time,Switch to stainless steel or silicone ice trays,Flexible plastic eventually breaks into fragments,40,50,60,70,45
42,Stainless steel ice cube tray,Home cleaning,Food-grade stainless steel,Cardboard box,Durable metal tray with lever release mechanism,Can be slightly harder to release ice initially,Lasts a lifetime and freezes water quickly,Infinitely recyclable metal with zero plastic degradation,90,95,90,90,95'''

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
    return df, "Loaded built-in errorless dataset (42 products)."

df, data_load_notice = load_data()

# -------------------- Marketplace database setup --------------------

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
        conn.execute("CREATE INDEX IF NOT EXISTS idx_items_status ON items(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_wishes_status ON wishes(status)")

def hash_pin(pin): return hashlib.sha256(pin.encode("utf-8")).hexdigest()
def now_iso(): return datetime.now(timezone.utc).isoformat(timespec="seconds")
def safe_text(value): return html.escape(str(value or ""))

init_db()

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

    spokes_svg = ""
    labels_svg = ""
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

# -------------------- Hero Banner & Live Impact Counter --------------------

with db_connect() as conn:
    donated_count = conn.execute("SELECT COUNT(*) AS n FROM items WHERE status='Donated'").fetchone()["n"]
    available_count = conn.execute("SELECT COUNT(*) AS n FROM items WHERE status='Available'").fetchone()["n"]
    wishes_count = conn.execute("SELECT COUNT(*) AS n FROM wishes WHERE status='Active'").fetchone()["n"]

# Heuristic impact estimates (Avg 1.5kg waste diverted & 4.2kg CO2 saved per rehomed item)
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
    <span class="hero-badge">📌 <b>{wishes_count}</b> Active Community Wishes</span>
  </div>
</div>
""", unsafe_allow_html=True)

tab_explore, tab_wish, tab_ai, tab_browse, tab_donate, tab_manage, tab_track = st.tabs([
    "🌿 Product Explorer", "📌 Wish Board", "🤖 REVORA AI Chat", "🔎 Browse Donations", "🎁 Donate an Item", "📬 Manage Requests", "📦 Track My Request"
])

# -------------------- Tab 1: Product Explorer --------------------

with tab_explore:
    st.markdown("## 🌿 Explore the Product Lifecycle")
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

    search = st.text_input("🔎 Search products by keyword or material", placeholder="Try: bottle, notebook, cable, cleaner, denim...", key="product_search")
    filtered = df.copy()
    if selected_category != "All categories": filtered = filtered[filtered["category"] == selected_category]
    if search.strip(): filtered = filtered[filtered.apply(lambda r: search.lower() in " ".join(map(str, r.values)).lower(), axis=1)]
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
        cols = st.columns(3)
        for idx, (_, row) in enumerate(filtered.head(12).iterrows()):
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
                if st.button("🔬 Analyze waste pattern", key=f"analyze_{row['product_id']}", use_container_width=True):
                    st.session_state.selected_product_id = row["product_id"]

    if "selected_product_id" in st.session_state:
        chosen_matches = df[df["product_id"] == st.session_state.selected_product_id]
        if not chosen_matches.empty:
            chosen = chosen_matches.iloc[0].copy()
            chosen["eco_score"] = score_product(chosen)
            candidates = df.copy()
            candidates["eco_score"] = candidates.apply(score_product, axis=1)

            def intervention_for(prob, name):
                rules = {
                    "Breaks before the rest wears out": ("Prioritize a repairable or modular design", "Look for replaceable parts, accessible fasteners, and repair guides."),
                    "Too much product is dispensed or used": ("Choose controlled-dose or refillable packaging", "A measured dispenser or refill pack reduces overuse."),
                    "Packaging is excessive": ("Prefer right-sized, concentrated, or refill packaging", "Compare packaging per use—not just package size."),
                    "Product is rarely used": ("Borrow, share, or keep using what you own", "Test whether sharing or renting solves the need without a new product."),
                    "Single-use waste builds up": ("Switch to a durable alternative if reuse is frequent", "Compare expected lifetime uses and cleaning needs."),
                    "Hard to recycle or dispose of": ("Choose simpler materials and a known take-back route", "Prefer clearly labelled materials and check local collection rules."),
                }
                return rules[prob]

            def generate_rec(prob, cat, curr, cands):
                t, expl = intervention_for(prob, curr["product_name"])
                if prob == "Product is rarely used":
                    cands = cands[cands["category"] == cat]
                    return t, expl, cands.sort_values("eco_score", ascending=False).head(3)
                sc = cands[cands["category"] == cat].copy()
                if sc.empty: sc = cands.copy()
                sc = sc[sc["product_name"] != curr["product_name"]]
                sc["score_gain"] = sc["eco_score"] - float(curr["eco_score"])
                return t, expl, sc.sort_values(["eco_score", "score_gain"], ascending=False).head(3)

            title, explanation, recs = generate_rec(problem, chosen["category"], chosen, candidates)

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

# -------------------- Tab 2: Community Wish Board --------------------

with tab_wish:
    st.markdown("## 📌 Community Wish Board (Reverse Marketplace)")
    st.write("Looking for a specific item (like textbooks, calculators, or tools)? Post your wish below so community donors can see and fulfill it.")
    
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
            wish_desc = st.text_area("Details / Specifications *", placeholder="Mention model, edition, condition required, or urgency...", max_chars=500)
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
                st.success("Your wish has been posted to the community Wish Board!")
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
                    st.markdown(f"""
                    <div class="result-card" style="margin-bottom:0;">
                        <span class="pill">{icon} {safe_text(wish['category'])}</span> &nbsp;<span class="muted">· Posted by <b>{safe_text(wish['requester_name'])}</b></span>
                        <h3 style="margin:.45rem 0">{safe_text(wish['wish_name'])}</h3>
                        <p>{safe_text(wish['description'])}</p>
                        <div class="muted">📍 {safe_text(wish['location'])} · Contact: <b>{safe_text(wish['requester_contact'])}</b> · {wish['created_at'][:10]}</div>
                    </div>
                    """, unsafe_allow_html=True)

# -------------------- Tab 3: REVORA AI Chat & Object Scanner --------------------

def get_gemini_client():
    try: api_key = st.secrets["GEMINI_API_KEY"]
    except Exception: api_key = ""
    if not api_key: raise KeyError("GEMINI_API_KEY is not configured")
    from google import genai
    return genai.Client(api_key=api_key)

def generate_with_fallback(client, contents, config=None):
    for model_name in ["gemini-2.5-flash", "gemini-3.5-flash-lite", "gemini-2.0-flash"]:
        try: return client.models.generate_content(model=model_name, contents=contents, config=config)
        except Exception: continue
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

with tab_ai:
    st.markdown("## 🤖 REVORA AI: Object Scanner, Voice Search & Chat")
    st.write("Scan any household object to inspect its condition, search using your voice, or chat with REVORA AI.")
    st.markdown("<div class='marketplace-note'><b>REVORA AI Studio</b> combines computer vision, voice recognition, and circular-economy guidance.</div>", unsafe_allow_html=True)

    if "revora_chat_history" not in st.session_state:
        st.session_state.revora_chat_history = []

    with st.expander("📸 Scan an Object (Condition, Repair & Donation Analyzer)", expanded=True):
        scan_mode = st.radio("Choose input method", ["📤 Upload a photo", "📷 Take a picture"], horizontal=True, key="scan_input_mode")
        scanned_file = st.file_uploader("Upload a clear photo", type=["jpg", "jpeg", "png", "webp"], key="object_file_uploader") if scan_mode == "📤 Upload a photo" else st.camera_input("Point camera", key="object_camera_input")
        user_scan_note = st.text_input("Optional context (e.g., 'zipper is stuck')", placeholder="Add any hidden issues...", key="object_scan_note")

        if scanned_file is not None:
            preview_col, result_col = st.columns([1, 1.8])
            with preview_col:
                st.image(scanned_file, caption="Scanned Object", use_container_width=True)
                analyze_btn = st.button("🔍 Analyze Object Condition", type="primary", use_container_width=True)

            if analyze_btn:
                try:
                    client = get_gemini_client()
                    from google.genai import types
                    img_bytes = scanned_file.getvalue()
                    image_part = types.Part.from_bytes(data=img_bytes, mime_type=scanned_file.type or "image/jpeg")
                    scan_prompt = f"""Analyze the object in this image and return a strict JSON object with these keys: object_name, marketplace_category, condition_status (Usable, Needs Minor Repair, Bad Condition), marketplace_condition, condition_score (0-100), object_explanation, recommended_action, action_advice, draft_listing_description. User note: '{user_scan_note}'"""
                    with result_col:
                        with st.spinner("Scanning object materials and wear patterns..."):
                            response = generate_with_fallback(client, contents=[image_part, scan_prompt], config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.2))
                            st.session_state.last_scan_result = json.loads(response.text)
                            res = st.session_state.last_scan_result
                            st.session_state.revora_chat_history.append({"role": "assistant", "content": f"**[Scanned: {res.get('object_name')}]** - **Condition:** {res.get('condition_status')} ({res.get('condition_score')}/100)"})
                except Exception as e: st.error(f"Could not analyze image: {e}")

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
                    </div>
                    """, unsafe_allow_html=True)
                    render_tts_buttons(f"{res.get('object_name')}. Condition {status}. {res.get('action_advice')}", "scan_tts")
                    if status in ["Usable", "Needs Minor Repair"]:
                        if st.button("🎁 Pre-fill 'Donate an Item' Form", use_container_width=True):
                            st.session_state.prefill_item_name = res.get("object_name", "")
                            st.session_state.prefill_category = res.get("marketplace_category", "Other")
                            st.session_state.prefill_condition = res.get("marketplace_condition", "Good")
                            st.success("Details copied to Donate tab!")

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
            if message["role"] == "assistant": render_tts_buttons(message["content"], f"hist_{idx}")

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
            if new_voice_bytes: st.audio(new_voice_bytes)

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
                    else: contents_payload = system_context + "\n\n" + transcript
                    response = generate_with_fallback(client, contents=contents_payload)
                    answer = response.text or "I couldn't generate a response."
                st.markdown(answer)
                render_tts_buttons(answer, "latest_reply")
            st.session_state.revora_chat_history.append({"role": "assistant", "content": answer})
        except Exception as e: st.error(f"Error connecting to Gemini: {e}")

# -------------------- Tab 4: Browse Donations ----------------

with tab_browse:
    st.markdown("## ♻️ Browse Community Donations")
    items = get_items(status="Available")
    if not items: st.info("No matching donations yet.")
    else:
        for item in items:
            icon = CATEGORY_ICONS.get(item["category"], "🎁")
            with st.container(border=True):
                left, right = st.columns([2.6, 1.2])
                with left:
                    st.markdown(f"""
                    <div class="result-card" style="margin-bottom:0;">
                        <span class="pill">{icon} {safe_text(item['category'])}</span> &nbsp;<span class="muted">· Condition: <b>{safe_text(item['item_condition'])}</b></span>
                        <h3 style="margin:.45rem 0">{safe_text(item['item_name'])}</h3>
                        <p>{safe_text(item['description'])}</p>
                        <div class="muted">📍 {safe_text(item['location'])} · Listed by <b>{safe_text(item['donor_name'])}</b></div>
                    </div>
                    """, unsafe_allow_html=True)
                with right:
                    with st.form(f"request_form_{item['id']}"):
                        st.markdown("**✋ Request this item**")
                        req_name = st.text_input("Your name", key=f"req_name_{item['id']}")
                        req_contact = st.text_input("Your email/phone", key=f"req_contact_{item['id']}")
                        req_message = st.text_area("Message to donor", key=f"req_msg_{item['id']}")
                        confirm = st.checkbox("I will arrange a safe handover.", key=f"req_confirm_{item['id']}")
                        submitted = st.form_submit_button("Send request", use_container_width=True)
                    if submitted:
                        if not req_name.strip() or not req_contact.strip() or not req_message.strip(): st.error("Complete all required fields.")
                        elif not confirm: st.error("Confirm safe handover.")
                        else:
                            with db_connect() as conn:
                                cursor = conn.execute("INSERT INTO requests (item_id, requester_name, requester_contact, message, status, created_at) VALUES (?, ?, ?, ?, 'Pending', ?)", (item["id"], req_name.strip(), req_contact.strip(), req_message.strip(), now_iso()))
                                st.success(f"Request sent! ID: REV-R{cursor.lastrowid:05d}")

# -------------------- Tab 5: Donate an Item --------------------

with tab_donate:
    st.markdown("## 🎁 Give a Useful Item a Second Life")
    with st.form("donate_item_form", clear_on_submit=True):
        d1, d2 = st.columns(2)
        with d1:
            cat_options = ["Clothing & shoes", "Books & education", "Electronics", "Home & kitchen", "Toys & games", "Sports & outdoors", "Other"]
            cond_options = ["Like new", "Good", "Used but working", "Needs minor repair"]
            default_cat = st.session_state.get("prefill_category", "Clothing & shoes")
            default_cond = st.session_state.get("prefill_condition", "Good")

            item_name = st.text_input("Item name *", value=st.session_state.get("prefill_item_name", ""))
            item_category = st.selectbox("Category *", cat_options, index=cat_options.index(default_cat) if default_cat in cat_options else 0)
            item_condition = st.selectbox("Condition *", cond_options, index=cond_options.index(default_cond) if default_cond in cond_options else 1)
            item_location = st.text_input("Area / city *")
        with d2:
            donor_name = st.text_input("Your name *")
            donor_contact = st.text_input("Your email or phone *")
            contact_type = st.selectbox("Contact preference", ["Email", "Phone / WhatsApp", "Either"])
            listing_pin = st.text_input("Private listing PIN (6+ chars) *", type="password")
        item_description = st.text_area("Description *", value=st.session_state.get("prefill_description", ""))
        safety_confirm = st.checkbox("I confirm this item is legal and safe.")
        submit_donation = st.form_submit_button("🌱 Publish Donation Listing", use_container_width=True)
    if submit_donation:
        if not all([item_name.strip(), item_location.strip(), donor_name.strip(), donor_contact.strip(), item_description.strip(), listing_pin]) or len(listing_pin) < 6:
            st.error("Please complete all fields and use a 6+ character PIN.")
        else:
            with db_connect() as conn:
                cursor = conn.execute("INSERT INTO items (item_name, category, item_condition, location, description, donor_name, donor_contact, contact_type, pin_hash, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Available', ?)", (item_name.strip(), item_category, item_condition, item_location.strip(), item_description.strip(), donor_name.strip(), donor_contact.strip(), contact_type, hash_pin(listing_pin), now_iso()))
                new_id = cursor.lastrowid
            st.success(f"Listed successfully! Listing ID: **REV-{new_id:05d}**. Save your PIN to manage requests.")

# -------------------- Tab 6: Manage Requests --------------------

with tab_manage:
    st.markdown("## 📬 Manage Your Donation Requests")
    with st.form("manage_listing_form"):
        manage_id_text = st.text_input("Listing ID", placeholder="e.g. REV-00012")
        manage_pin = st.text_input("Private listing PIN", type="password")
        load_listing = st.form_submit_button("🔑 View Requests", use_container_width=True)
    if load_listing:
        try:
            listing_id = int(manage_id_text.strip().upper().replace("REV-", ""))
            listing = get_item(listing_id)
            if not listing or not secrets.compare_digest(listing["pin_hash"], hash_pin(manage_pin)):
                st.error("Incorrect Listing ID or PIN.")
            else: st.session_state.managed_listing_id = listing_id
        except Exception: st.error("Enter a valid listing ID like REV-00012.")

    if st.session_state.get("managed_listing_id"):
        listing = get_item(st.session_state.managed_listing_id)
        if listing:
            st.markdown(f"### {safe_text(listing['item_name'])}")
            with db_connect() as conn:
                requests = conn.execute("SELECT * FROM requests WHERE item_id = ? ORDER BY created_at DESC", (listing["id"],)).fetchall()
            for req in requests:
                with st.container(border=True):
                    st.markdown(f"**Request from {safe_text(req['requester_name'])}** ({req['status']})")
                    st.write(req["message"])
                    if req["status"] == "Pending" and listing["status"] == "Available":
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("Approve", key=f"app_{req['id']}"):
                                with db_connect() as conn:
                                    conn.execute("UPDATE requests SET status='Approved' WHERE id=?", (req["id"],))
                                    conn.execute("UPDATE items SET status='Reserved' WHERE id=?", (listing["id"],))
                                st.rerun()
                        with c2:
                            if st.button("Decline", key=f"dec_{req['id']}"):
                                with db_connect() as conn: conn.execute("UPDATE requests SET status='Declined' WHERE id=?", (req["id"],))
                                st.rerun()

            if listing["status"] == "Reserved":
                if st.button("Mark as Donated / Completed", key=f"complete_{listing['id']}"):
                    with db_connect() as conn:
                        conn.execute("UPDATE items SET status='Donated' WHERE id=?", (listing["id"],))
                    st.success("Marked as donated! Impact metrics updated.")
                    st.rerun()

# -------------------- Tab 7: Track Request --------------------

with tab_track:
    st.markdown("## 📦 Track Your Request")
    with st.form("track_request_form"):
        track_id_text = st.text_input("Request ID", placeholder="e.g. REV-R00012")
        track_contact = st.text_input("Your email or phone")
        track_submit = st.form_submit_button("🔎 Check Status", use_container_width=True)
    if track_submit:
        try:
            req_id = int(track_id_text.strip().upper().replace("REV-R", ""))
            tracked = get_request_for_tracking(req_id, track_contact)
            if not tracked: st.error("Request not found.")
            else:
                st.markdown(f"### {safe_text(tracked['item_name'])}")
                st.markdown(f"**Status:** {tracked['status']}")
                if tracked["status"] == "Approved":
                    st.success(f"Donor Contact: {tracked['donor_contact']} ({tracked['contact_type']})")
        except Exception: st.error("Enter a valid request ID like REV-R00012.")

st.markdown("---")
st.markdown("### 🌍 Small actions, less waste")
st.caption("REVORA is a community reuse prototype. Arrange handovers in safe, public places.")
