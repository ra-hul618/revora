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
    st.write("🌿 **Explore** 24+ product lifecycles")
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

# -------------------- Dynamic Theme CSS (Botanical Light & Midnight Forest Dark) --------------------

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

    :root {{
        {theme_vars}
    }}

    html, body, [class*="css"] {{
        font-family: 'Plus Jakarta Sans', sans-serif;
        color: var(--text-main);
    }}
    h1, h2, h3, h4, .splash-wordmark {{
        font-family: 'Outfit', sans-serif !important;
        color: var(--text-main);
    }}
    p, li, label, .stMarkdown {{
        color: var(--text-body);
    }}

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

    [data-testid="stSidebar"] {{
        background: var(--bg-sidebar);
        border-right: 1px solid var(--card-border);
    }}

    .hero {{
        position: relative;
        overflow: hidden;
        padding: 2.2rem 2.4rem;
        border-radius: 26px;
        background: linear-gradient(125deg, #0d2e20 0%, #1b563b 48%, #2e7a53 100%);
        color: white;
        margin-bottom: 1.4rem;
        box-shadow: 0 20px 42px -15px rgba(18, 59, 43, 0.38);
        border: 1px solid rgba(255, 255, 255, 0.14);
    }}
    .hero h1 {{
        color: white !important;
        font-size: clamp(2.4rem, 4.5vw, 3.4rem);
        font-weight: 800;
        margin: 0.25rem 0 0;
        letter-spacing: -1px;
    }}
    .hero p {{ color: #e3f3e7 !important; font-size: 1.08rem; margin: .35rem 0 0; max-width: 720px; }}
    .hero-badges {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 1.15rem; }}
    .hero-badge {{
        background: rgba(255, 255, 255, 0.12);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.22);
        color: #f4ffe9;
        padding: 0.38rem 0.85rem;
        border-radius: 999px;
        font-size: 0.82rem;
        font-weight: 600;
    }}

    .pill {{
        display: inline-block;
        padding: .3rem .75rem;
        border-radius: 999px;
        background: var(--pill-bg);
        color: var(--pill-text);
        font-size: .8rem;
        font-weight: 700;
    }}

    .result-card {{
        border: 1px solid var(--card-border);
        border-radius: 20px;
        padding: 1.3rem 1.35rem;
        background: var(--card-bg);
        backdrop-filter: blur(10px);
        height: 100%;
        margin-bottom: 0.65rem;
        box-shadow: 0 8px 22px -8px rgba(0, 0, 0, 0.12);
        transition: transform 0.24s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.24s ease, border-color 0.24s ease;
    }}
    .result-card:hover {{
        transform: translateY(-5px);
        box-shadow: 0 18px 34px -10px rgba(27, 103, 65, 0.25);
        border-color: #4f9369;
    }}
    .muted {{ color: var(--text-muted) !important; font-size: .88rem; font-weight: 500; }}
    .big-score {{ font-size: 2.1rem; font-weight: 800; color: var(--score-color); font-family: 'Outfit', sans-serif; }}

    .eco-bar-track {{
        width: 100%; height: 7px; background: var(--track-bg); border-radius: 999px;
        overflow: hidden; margin: 8px 0 12px;
    }}
    .eco-bar-fill {{ height: 100%; border-radius: 999px; transition: width 0.4s ease; }}

    div[data-baseweb="tab-list"] {{
        gap: 8px;
        background: var(--tab-bar-bg);
        backdrop-filter: blur(10px);
        padding: 8px 10px;
        border-radius: 18px;
        border: 1px solid var(--card-border);
        margin-bottom: 1rem;
    }}
    button[data-baseweb="tab"] {{
        border-radius: 12px !important;
        padding: 9px 16px !important;
        font-weight: 600 !important;
        color: var(--tab-text) !important;
    }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        background: linear-gradient(135deg, #1b6741 0%, #2d8659 100%) !important;
        color: #ffffff !important;
        box-shadow: 0 4px 12px rgba(27, 103, 65, 0.28) !important;
    }}
    div[data-baseweb="tab-highlight"] {{ display: none !important; }}

    div[data-testid="stMetric"] {{
        background: var(--card-bg);
        border: 1px solid var(--card-border);
        padding: 14px 18px;
        border-radius: 18px;
    }}

    .marketplace-note {{
        border: 1px solid var(--card-border);
        border-left: 5px solid #2e8b57;
        border-radius: 16px;
        padding: 1rem 1.2rem;
        background: var(--note-bg);
        margin: .5rem 0 1.1rem;
    }}
</style>
""", unsafe_allow_html=True)

# -------------------- Product recommendation engine & SVG Radar Chart --------------------

_FALLBACK_PRODUCTS_CSV = 'product_id,product_name,category,material,packaging,description,waste_risk,design_opportunity,tradeoff,material_score,lifecycle_score,packaging_score,usage_score,end_of_life_score\n1,Disposable PET water bottle,Drinkware,PET plastic,Single-use plastic bottle,Convenient single-use water container,Repeated single-use packaging,Refill from safe drinking water or use a durable bottle when used frequently,Reusable alternatives require repeated use and cleaning,35,25,20,25,35\n2,Reusable stainless steel bottle,Drinkware,Stainless steel,Minimal or cardboard packaging,Durable bottle designed for repeated use,Can be underused or lost,Use consistently for many refill cycles,Material-intensive manufacture and cleaning needs matter,65,85,80,90,65\n3,Reusable glass bottle,Drinkware,Glass,Cardboard or protective packaging,Reusable bottle for home or office,Breakage can shorten lifespan,Use in settings where breakage risk is low,Heavier transport and breakage risk,70,70,75,80,70\n4,Single-use shopping bag,Bags,Thin plastic,No additional packaging,Lightweight carrier bag,Often discarded after one trip,Reuse bags already owned before acquiring new ones,Some reusable bags require many uses to offset production,25,20,30,25,25\n5,Reusable fabric tote,Bags,Cotton or blended fabric,Minimal packaging,Reusable shopping bag,May accumulate unused bags,Keep a small set and reuse frequently,Cotton production can be resource intensive,55,75,75,80,60\n6,Recycled-content paper bag,Bags,Recycled paper,Paper bag,Paper carrier with recycled content,May tear when wet or overloaded,Reuse when practical and recycle where accepted,Not always lower impact than reusing a bag already owned,70,45,65,50,75\n7,Disposable coffee cup,Food & drink,Paper with possible lining,Single-use cup,Takeaway cup used for one drink,Repeated cups and lids,Bring a cup or use dine-in service when practical,Reusable cup benefits depend on repeated use and washing,45,20,20,25,35\n8,Reusable coffee cup,Food & drink,Stainless steel or durable plastic,Minimal packaging,Reusable cup for takeaway drinks,May be forgotten or rarely used,Store it where it is easy to remember,Manufacture and washing impacts need repeated use,65,80,75,85,60\n9,Conventional toothbrush,Personal care,Plastic,Cardboard and plastic blister,Low-cost toothbrush with replaceable use cycle,Entire handle is often discarded,Consider replaceable-head options if compatible and durable,Material claims and recycling routes vary,35,45,45,55,30\n10,Replaceable-head toothbrush,Personal care,Reusable handle with replaceable head,Compact packaging,Only the brush head needs regular replacement,Replacement heads still create waste,Use compatible heads and check material disposal,Availability and actual material mix vary,60,75,70,80,55\n11,Disposable cleaning spray bottle,Home cleaning,Plastic bottle and trigger,Plastic bottle plus label,Ready-to-use household cleaner,Packaging and leftover liquid can be wasted,Use measured dispensing and refill options,Refills help only when total packaging is reduced,35,50,25,45,35\n12,Refillable cleaning bottle,Home cleaning,Durable plastic or glass,Refill pouch or concentrate,Reusable container with refill format,Refill packaging may still be significant,Compare packaging per volume and follow dilution instructions,Concentrate transport and refill material matter,55,75,65,80,55\n13,Standard notebook,Stationery,Paper and cardboard,Paper wrap,Bound notebook for writing,Unused pages may be discarded with the notebook,Finish existing notebooks and consider refillable formats,Binding and refill availability vary,65,55,70,65,65\n14,Refillable notebook,Stationery,Reusable cover and replaceable paper,Minimal packaging,Reusable cover with refill pages,Refills still use paper,Replace only the pages needed and use both sides,Extra hardware is only beneficial if reused,60,80,75,85,65\n15,Non-repairable charging cable,Electronics,Plastic and copper,Small cardboard or plastic pack,Cable with fixed connector assembly,Failure near one connector can discard the whole cable,Look for reinforced strain relief and repairable modular parts,Modular products may cost more or be hard to find,40,30,45,70,25\n16,Modular repairable cable concept,Electronics,Replaceable connector modules,Compact recyclable packaging,Concept design allowing a failed connector to be replaced,Design is a proposal and may not be commercially available,Prototype replaceable connectors and document repair instructions,Compatibility and safety testing are essential,60,80,75,85,65\n17,Fast-fashion synthetic shirt,Clothing,Polyester blend,Plastic mailer or tag,Low-cost synthetic garment,Short use cycles and difficult fibre recycling,Buy fewer durable items and extend wear life,Recycled fibres do not remove all shedding or end-of-life issues,35,40,35,45,30\n18,Durable repairable shirt,Clothing,Cotton or durable blend,Minimal packaging,Garment intended for repeated wear and repair,May still be discarded due to fit or style changes,Choose versatile fit and repair small damage,Material impact depends on fibre source and production,55,75,70,85,50\n19,Single-use food container,Food containers,Plastic or coated fibre,Single-use container,Takeaway container for one meal,Frequent packaging waste,Choose reusable containers where washing and return are practical,Food safety and cleaning requirements matter,30,25,20,30,30\n20,Reusable food container,Food containers,Durable glass or stainless steel,Minimal packaging,Container designed for repeated meal storage,Can be lost or left unused,Use regularly and maintain the seal,Heavier manufacture and washing must be considered,65,85,80,90,70\n21,Disposable batteries,Household,Primary battery chemistry,Cardboard and plastic pack,Single-use battery for low-drain devices,Repeated battery purchases and disposal,Use rechargeable batteries for compatible frequent-use devices,Rechargeable batteries are not ideal for every device or use,40,40,50,45,35\n22,Rechargeable battery set,Household,Rechargeable battery chemistry,Cardboard pack,Rechargeable cells for repeated use,May be unsuitable for infrequently used devices,Match charger and battery type to the device,Charging electricity and eventual proper recycling matter,55,80,70,85,55\n23,Plastic-wrapped soap bars,Personal care,Soap and plastic film,Plastic wrap,Bar soap in plastic packaging,Packaging after each purchase,Choose paper-wrapped or unpackaged options when hygiene and availability allow,Paper is not automatically better if coatings or waste are high,55,60,35,70,55\n24,Paper-wrapped soap bar,Personal care,Soap and paper,Paper wrap,Bar soap with paper packaging,Paper packaging still requires resources,Use fully and recycle packaging if locally accepted,"Check inks, coatings, and local recycling acceptance",60,60,75,70,65\n'

@st.cache_data
def load_data():
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
            continue

    if df is None:
        df = pd.read_csv(io.StringIO(_FALLBACK_PRODUCTS_CSV))
        load_notice = "Using built-in validated product dataset."

    required_columns = [
        "product_id", "product_name", "category", "material", "packaging",
        "description", "waste_risk", "design_opportunity", "tradeoff",
        "material_score", "lifecycle_score", "packaging_score", "usage_score",
        "end_of_life_score",
    ]
    missing = [column for column in required_columns if column not in df.columns]
    if missing:
        df = pd.read_csv(io.StringIO(_FALLBACK_PRODUCTS_CSV))
        load_notice = "Using built-in validated product dataset."

    numeric = [
        "material_score", "lifecycle_score", "packaging_score",
        "usage_score", "end_of_life_score",
    ]
    for col in numeric:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(50).clip(0, 100)
    return df, load_notice

df, data_load_notice = load_data()

def score_bar_color(score):
    if score >= 70:
        return "linear-gradient(90deg, #1b6741, #48b578)"
    if score >= 45:
        return "linear-gradient(90deg, #b87d14, #f0b429)"
    return "linear-gradient(90deg, #a82828, #e05252)"

def score_badge_label(score):
    if score >= 70:
        return "🌟 High Circularity", "#dcecdf", "#174c31"
    if score >= 45:
        return "⚖️ Moderate Impact", "#fff3cd", "#7a5200"
    return "⚠️ High Waste Risk", "#fde2e2", "#8c1d1d"

def build_svg_radar(primary_row, compare_row=None, is_dark=False):
    """Build a crisp, zero-dependency 5-axis SVG Radar Chart comparing two products."""
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
    dots1_svg = "".join(
        f'<circle cx="{pt(i, primary_row[k])[0]:.1f}" cy="{pt(i, primary_row[k])[1]:.1f}" r="4" fill="#2e8b57"/>'
        for i, (k, _) in enumerate(axes)
    )

    poly2_svg = ""
    legend_2 = ""
    if compare_row is not None:
        p2_pts = " ".join(f"{pt(i, compare_row[k])[0]:.1f},{pt(i, compare_row[k])[1]:.1f}" for i, (k, _) in enumerate(axes))
        poly2_svg = f'<polygon points="{p2_pts}" fill="rgba(240, 180, 41, 0.22)" stroke="#e09f1f" stroke-width="2.2" stroke-dasharray="5,3"/>'
        legend_2 = f'<span style="display:inline-flex;align-items:center;gap:6px;font-size:12px;"><span style="width:12px;height:12px;border-radius:3px;background:#e09f1f;display:inline-block;"></span>{html.escape(str(compare_row["product_name"]))}</span>'

    legend_1 = f'<span style="display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:700;"><span style="width:12px;height:12px;border-radius:3px;background:#2e8b57;display:inline-block;"></span>{html.escape(str(primary_row["product_name"]))}</span>'

    return f"""
    <div class="result-card" style="text-align:center;padding:1rem;">
        <div style="font-weight:700;font-size:.95rem;margin-bottom:4px;">🕸️ 5-Axis Lifecycle Radar Comparison</div>
        <svg viewBox="0 0 370 325" style="width:100%;max-width:360px;height:auto;">
            {rings_svg}
            {spokes_svg}
            {poly2_svg}
            {poly1_svg}
            {dots1_svg}
            {labels_svg}
        </svg>
        <div style="display:flex;justify-content:center;gap:16px;flex-wrap:wrap;margin-top:4px;">
            {legend_1} {legend_2}
        </div>
    </div>
    """

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

# -------------------- Creative Aurora Hero Banner --------------------

st.markdown("""
<div class="hero">
  <span class="pill" style="background:rgba(224,245,189,0.22);color:#e6f9d5;border:1px solid rgba(224,245,189,0.4);">
    🌱 WASTE-TO-DESIGN INTELLIGENCE & COMMUNITY MARKETPLACE
  </span>
  <h1>REVORA</h1>
  <p>Rethink materials. Reuse what works. Revive everyday objects before they become waste.</p>
  <div class="hero-badges">
    <span class="hero-badge">🌿 5-Pillar EcoScore & Radar Chart</span>
    <span class="hero-badge">📸 AI Object Condition Scanner</span>
    <span class="hero-badge">🎙️ Voice Search & Read Aloud</span>
    <span class="hero-badge">🔒 PIN-Protected Community Reuse</span>
  </div>
</div>
""", unsafe_allow_html=True)

tab_explore, tab_ai, tab_browse, tab_donate, tab_manage, tab_track = st.tabs([
    "🌿 Product Explorer", "🤖 REVORA AI Chat", "🔎 Browse Donations", "🎁 Donate an Item", "📬 Manage Requests", "📦 Track My Request"
])

# -------------------- Product Explorer with Interactive SVG Radar Comparison --------------------

with tab_explore:
    st.markdown("## 🌿 Explore the Product Lifecycle")
    with db_connect() as conn:
        total_available = conn.execute("SELECT COUNT(*) AS n FROM items WHERE status='Available'").fetchone()["n"]
        total_donated = conn.execute("SELECT COUNT(*) AS n FROM items WHERE status='Donated'").fetchone()["n"]

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Products in Catalog", len(df))
    with m2:
        st.metric("Product Categories", df["category"].nunique())
    with m3:
        st.metric("Available Donations", int(total_available))
    with m4:
        st.metric("Items Rehomed", int(total_donated))

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

    search = st.text_input("🔎 Search products by keyword or material", placeholder="Try: bottle, notebook, cable, cleaner...", key="product_search")
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
            icon = CATEGORY_ICONS.get(row["category"], "🌱")
            score_val = float(row["eco_score"])
            bar_bg = score_bar_color(score_val)
            badge_text, badge_bg, badge_fg = score_badge_label(score_val)
            with cols[idx % 3]:
                st.markdown(f"""
                <div class="result-card">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <span class="muted">{icon} {safe_text(row['category'])}</span>
                        <span style="background:{badge_bg};color:{badge_fg};padding:3px 9px;border-radius:999px;font-size:.73rem;font-weight:700;">
                            {badge_text}
                        </span>
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
            heading, details, recs = generate_recommendation(problem, chosen["category"], chosen, candidates)

            st.markdown("---")
            st.markdown("## 🔬 Your Waste-to-Design Analysis & Radar Comparison")
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
                title, explanation = intervention_for(problem, chosen["product_name"])
                st.success(f"**Suggested Design Intervention: {title}** — {explanation}")

            with radar_col:
                compare_options = df[df["product_name"] != chosen["product_name"]]["product_name"].tolist()
                default_comp = recs.iloc[0]["product_name"] if not recs.empty else compare_options[0]
                comp_name = st.selectbox(
                    "Compare on Radar Chart against:",
                    compare_options,
                    index=compare_options.index(default_comp) if default_comp in compare_options else 0,
                    key="radar_compare_select",
                )
                comp_row = df[df["product_name"] == comp_name].iloc[0]
                st.markdown(build_svg_radar(chosen, comp_row, is_dark=dark_mode), unsafe_allow_html=True)

            st.markdown("### 📊 Lifecycle Score Breakdown")
            score_cols = st.columns(5)
            for col, key in zip(score_cols, WEIGHTS.keys()):
                with col:
                    st.metric(DISPLAY_NAMES[key], f"{chosen[key]:.0f}/100")
            st.progress(min(1.0, max(0.0, chosen["eco_score"] / 100)))

            st.markdown("### 🔄 Better-Scoring Alternatives in This Category")
            if recs.empty:
                st.info("No alternative in this sample dataset. Try another category or product.")
            else:
                rec_cols = st.columns(min(3, len(recs)))
                for col, (_, rec) in zip(rec_cols, recs.iterrows()):
                    gain = rec["eco_score"] - chosen["eco_score"]
                    gain_str = f"+{gain:.0f} pts" if gain > 0 else f"{gain:.0f} pts"
                    with col:
                        st.markdown(f"""
                        <div class="result-card">
                          <div style="display:flex;justify-content:space-between;">
                            <span class="muted">{safe_text(rec['category'])}</span>
                            <span class="pill">{gain_str}</span>
                          </div>
                          <h4 style="margin:.4rem 0">{safe_text(rec['product_name'])}</h4>
                          <div class="big-score">{rec['eco_score']:.0f}<span style="font-size:.8rem;" class="muted"> / 100</span></div>
                          <p>{safe_text(rec['description'])}</p>
                          <p style="font-size:.88rem;"><b>Trade-off:</b> {safe_text(rec['tradeoff'])}</p>
                        </div>
                        """, unsafe_allow_html=True)

    with st.expander("ℹ️ How the EcoScore works"):
        st.write("EcoScore is a weighted heuristic score designed for this prototype. You can customize the weights live in the left sidebar!")
        st.latex(r"EcoScore = w_M M + w_L L + w_P P + w_U U + w_E E")
        st.write("M = materials and sourcing; L = durability and lifespan; P = packaging; U = usage and reuse; E = repairability and end-of-life.")

# -------------------- Gemini AI chatbox, Object Scanner & Voice Search --------------------

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
            return client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config,
            )
        except Exception:
            continue
    raise RuntimeError("All configured Gemini models failed to respond.")

def render_tts_buttons(text_to_read, key_suffix):
    clean = (
        str(text_to_read)
        .replace("*", "")
        .replace("#", "")
        .replace("`", "")
        .replace("\n", " ")
    )
    js_safe_text = json.dumps(clean)
    components.html(
        f"""
        <div style="display:flex;gap:8px;align-items:center;font-family:sans-serif;margin:0;padding:0;">
            <button onclick='
                window.speechSynthesis.cancel();
                const u = new SpeechSynthesisUtterance({js_safe_text});
                u.rate = 1.0;
                window.speechSynthesis.speak(u);
            ' style="background:#eaf1e7;border:1px solid #b9d9b8;color:#174c31;padding:4px 11px;border-radius:8px;font-size:12px;cursor:pointer;font-weight:600;">
                🔊 Read Aloud
            </button>
            <button onclick='window.speechSynthesis.cancel();'
              style="background:#fdf2f2;border:1px solid #f8d7da;color:#8c1d1d;padding:4px 11px;border-radius:8px;font-size:12px;cursor:pointer;font-weight:600;">
                ⏹️ Stop
            </button>
        </div>
        """,
        height=36,
    )

with tab_ai:
    st.markdown("## 🤖 REVORA AI: Object Scanner, Voice Search & Chat")
    st.write("Scan any household object to inspect its condition, search using your voice, or chat with REVORA AI.")
    st.markdown(
        "<div class='marketplace-note'><b>REVORA AI Studio</b> combines computer vision, voice recognition, and circular-economy guidance. "
        "Always inspect physical safety, electrical integrity, and hygiene in person before donating or repairing an item.</div>",
        unsafe_allow_html=True,
    )

    if "revora_chat_history" not in st.session_state:
        st.session_state.revora_chat_history = []

    with st.expander("📸 Scan an Object (Condition, Repair & Donation Analyzer)", expanded=True):
        scan_mode = st.radio(
            "Choose input method",
            ["📤 Upload a photo", "📷 Take a picture"],
            horizontal=True,
            key="scan_input_mode",
        )

        if scan_mode == "📤 Upload a photo":
            scanned_file = st.file_uploader(
                "Upload a clear photo of the object",
                type=["jpg", "jpeg", "png", "webp"],
                key="object_file_uploader",
            )
        else:
            scanned_file = st.camera_input(
                "Point your camera at the object",
                key="object_camera_input",
            )

        user_scan_note = st.text_input(
            "Optional context (e.g., 'zipper is stuck', 'bought 2 years ago', 'doesn't turn on')",
            placeholder="Add any hidden issues the camera cannot see...",
            key="object_scan_note",
        )

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
                    mime_type = scanned_file.type or "image/jpeg"
                    image_part = types.Part.from_bytes(data=img_bytes, mime_type=mime_type)

                    scan_prompt = f"""You are REVORA's visual sustainability and circular-economy inspector.
Analyze the object in this image and return a strict JSON object with these exact keys:
- "object_name": Short, clear name of the item (string).
- "marketplace_category": Must be one of ["Clothing & shoes", "Books & education", "Electronics", "Home & kitchen", "Toys & games", "Sports & outdoors", "Other"].
- "condition_status": Must be one of ["Usable", "Needs Minor Repair", "Bad Condition"].
- "marketplace_condition": Must be one of ["Like new", "Good", "Used but working", "Needs minor repair"].
- "condition_score": Integer from 0 to 100 estimating physical usability.
- "object_explanation": 2-3 sentences explaining what the object is, its likely material composition, and visible condition details.
- "recommended_action": Must be one of ["Donate on REVORA", "Repair & Reuse", "Upcycle / Recycle Safely"].
- "action_advice": Practical step-by-step advice explaining why you recommend donating, repairing, or recycling it.
- "draft_listing_description": A polite, honest 2-sentence description the user can use if listing this item on REVORA.

User's additional note about the item: "{user_scan_note.strip() or 'None provided'}"
"""
                    with result_col:
                        with st.spinner("Scanning object materials, wear patterns, and reuse potential..."):
                            response = generate_with_fallback(
                                client,
                                contents=[image_part, scan_prompt],
                                config=types.GenerateContentConfig(
                                    response_mime_type="application/json",
                                    temperature=0.2,
                                ),
                            )
                            st.session_state.last_scan_result = json.loads(response.text)

                            res = st.session_state.last_scan_result
                            chat_summary = (
                                f"**[Scanned Object: {res.get('object_name', 'Item')}]**\n"
                                f"- **Condition:** {res.get('condition_status')} ({res.get('condition_score')}/100)\n"
                                f"- **Verdict:** {res.get('recommended_action')}\n"
                                f"- **Analysis:** {res.get('object_explanation')}\n"
                                f"- **Next Steps:** {res.get('action_advice')}"
                            )
                            st.session_state.revora_chat_history.append(
                                {"role": "assistant", "content": chat_summary}
                            )
                except KeyError:
                    st.error("Gemini API key not configured. Add GEMINI_API_KEY in your Streamlit Cloud Settings → Secrets.")
                except Exception as e:
                    st.error(f"Could not analyze the image. Please try another photo or check your API key. ({e})")

            if "last_scan_result" in st.session_state:
                res = st.session_state.last_scan_result
                status = res.get("condition_status", "Usable")
                score = int(res.get("condition_score", 50))

                if status == "Usable":
                    badge_color, badge_bg = "#1b6741", "#dcecdf"
                elif status == "Needs Minor Repair":
                    badge_color, badge_bg = "#855800", "#fff1cc"
                else:
                    badge_color, badge_bg = "#8c1d1d", "#fadddd"

                with result_col:
                    st.markdown(f"""
                    <div class="result-card">
                        <span style="display:inline-block;padding:.3rem .75rem;border-radius:999px;background:{badge_bg};color:{badge_color};font-weight:700;font-size:.85rem;">
                            {safe_text(status)} · {score}/100 Condition Score
                        </span>
                        <h3 style="margin:.5rem 0 .25rem">{safe_text(res.get('object_name', 'Scanned Object'))}</h3>
                        <div class="muted">Suggested Category: {safe_text(res.get('marketplace_category', 'Other'))}</div>
                        <div class="eco-bar-track">
                            <div class="eco-bar-fill" style="width:{min(100, max(5, score))}%;background:{score_bar_color(score)};"></div>
                        </div>
                        <p><b>🔎 About & Condition Details:</b><br>{safe_text(res.get('object_explanation', ''))}</p>
                        <p><b>🌱 Recommendation ({safe_text(res.get('recommended_action', ''))}):</b><br>{safe_text(res.get('action_advice', ''))}</p>
                    </div>
                    """, unsafe_allow_html=True)

                    render_tts_buttons(
                        f"{res.get('object_name', '')}. Condition is {status}, score {score} out of 100. {res.get('object_explanation', '')} Recommendation: {res.get('action_advice', '')}",
                        "scan_tts",
                    )

                    if status in ["Usable", "Needs Minor Repair"]:
                        if st.button("🎁 Pre-fill 'Donate an Item' Form with this Scan", key="prefill_donate_btn", use_container_width=True):
                            st.session_state.prefill_item_name = res.get("object_name", "")
                            st.session_state.prefill_category = res.get("marketplace_category", "Other")
                            st.session_state.prefill_condition = res.get("marketplace_condition", "Good")
                            st.session_state.prefill_description = res.get("draft_listing_description", "")
                            st.success("Details copied! Open the '🎁 Donate an Item' tab above to review and publish your listing.")

    st.markdown("---")
    st.markdown("### 🎙️ Voice Search & AI Chat")

    chat_col, clear_col = st.columns([5, 1])
    with chat_col:
        st.caption("Powered by Google's Gemini API · Click the microphone to ask by voice, or type your question below.")
    with clear_col:
        if st.button("Clear chat", key="clear_revora_chat"):
            st.session_state.revora_chat_history = []
            st.session_state.pop("last_scan_result", None)
            st.session_state.pop("last_voice_hash", None)
            st.rerun()

    for idx, message in enumerate(st.session_state.revora_chat_history):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                render_tts_buttons(message["content"], f"hist_{idx}")

    voice_recording = st.audio_input(
        "🎙️ Voice Search: Click the mic, speak your question, and click stop",
        key="revora_voice_search",
    )

    prompt = st.chat_input(
        "Or type your question about repairing, donating, or sustainability...",
        key="revora_chat_input",
    )

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
            transcript = "\n\n".join(
                ("User" if m["role"] == "user" else "REVORA AI") + ": " + m["content"]
                for m in recent_history
            )
            system_context = """You are REVORA AI, a helpful sustainability and circular-economy assistant inside a community reuse website.

Your goals:
- Give practical, affordable ways to reduce waste, reuse, repair, share, and donate usable items.
- If the user sent a voice recording, first write '**You asked:** "<transcribed question>"' on the first line, and then provide a clear, helpful answer.
- If the user recently scanned an object, help them with specific DIY repair tips, cleaning advice, or how to donate/recycle it safely.
- Explain trade-offs honestly; do not invent exact carbon, water, money, or landfill savings.
- Encourage users to use REVORA's Donate & Request tabs when they want to pass on or request usable items.
- Keep answers friendly, clear, and reasonably concise.
"""
            with st.chat_message("assistant"):
                with st.spinner("REVORA AI is listening and thinking..."):
                    if new_voice_bytes:
                        mime_type = voice_recording.type or "audio/wav"
                        audio_part = types.Part.from_bytes(data=new_voice_bytes, mime_type=mime_type)
                        contents_payload = [
                            audio_part,
                            system_context + "\n\nConversation so far:\n" + transcript + "\n\nTranscribe the user's voice query and answer it helpfully.",
                        ]
                    else:
                        contents_payload = system_context + "\n\nConversation so far:\n" + transcript

                    response = generate_with_fallback(
                        client,
                        contents=contents_payload,
                    )
                    answer = response.text or "I couldn't generate a response this time. Please try asking in a different way."
                st.markdown(answer)
                render_tts_buttons(answer, "latest_reply")

            st.session_state.revora_chat_history.append({"role": "assistant", "content": answer})
        except KeyError:
            st.error("Gemini API key not configured. Add GEMINI_API_KEY in your Streamlit Cloud app Settings → Secrets, then reboot the app.")
        except Exception as e:
            st.error(f"REVORA AI couldn't connect to Gemini. Check that your API key is valid and quota is available. ({e})")

# -------------------- Browse available items and submit requests --------------------

with tab_browse:
    st.markdown("## ♻️ Browse Community Donations")
    st.write("Find useful items nearby and request them directly from the donor.")
    browse_col1, browse_col2, browse_col3 = st.columns([1, 1, 1.2])
    with browse_col1:
        browse_categories = ["All categories", "Clothing & shoes", "Books & education", "Electronics", "Home & kitchen", "Toys & games", "Sports & outdoors", "Other"]
        browse_category = st.selectbox("Category", browse_categories, key="browse_category")
    with browse_col2:
        browse_search = st.text_input("Search items or area", placeholder="e.g. textbooks, Bengaluru", key="browse_search")
    with browse_col3:
        st.caption("🔒 Privacy-First: Donor contact details remain hidden until your request is approved.")
    items = get_items(status="Available", category=browse_category, search_text=browse_search.strip())
    if not items:
        st.info("No matching donations yet. Be the first to list a useful item in the '🎁 Donate an Item' tab!")
    else:
        st.caption(f"Showing {len(items)} available item(s)")
        for item in items:
            icon = CATEGORY_ICONS.get(item["category"], "🎁")
            with st.container(border=True):
                left, right = st.columns([2.6, 1.2])
                with left:
                    st.markdown(f"""
                    <div class="result-card" style="margin-bottom:0;">
                        <span class="pill">{icon} {safe_text(item['category'])}</span>
                        &nbsp;<span class="muted">· Condition: <b>{safe_text(item['item_condition'])}</b></span>
                        <h3 style="margin:.45rem 0">{safe_text(item['item_name'])}</h3>
                        <p>{safe_text(item['description'])}</p>
                        <div class="muted">📍 {safe_text(item['location'])} · Listed by <b>{safe_text(item['donor_name'])}</b> · {item['created_at'][:10]} · 📬 {item_request_count(item['id'])} request(s)</div>
                    </div>
                    """, unsafe_allow_html=True)
                with right:
                    with st.form(f"request_form_{item['id']}"):
                        st.markdown("**✋ Request this item**")
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
    st.markdown("## 🎁 Give a Useful Item a Second Life")
    st.write("List items that are clean, safe, and in usable condition. You can approve or decline requests later.")
    st.markdown("""
    <div class="marketplace-note">
    <b>🔒 Privacy Guarantee:</b> Your contact information is only shown to requesters after you approve their request.
    Keep your listing PIN private; it is used to manage requests for your item.
    </div>
    """, unsafe_allow_html=True)
    with st.form("donate_item_form", clear_on_submit=True):
        d1, d2 = st.columns(2)
        with d1:
            cat_options = ["Clothing & shoes", "Books & education", "Electronics", "Home & kitchen", "Toys & games", "Sports & outdoors", "Other"]
            cond_options = ["Like new", "Good", "Used but working", "Needs minor repair"]
            default_cat = st.session_state.get("prefill_category", "Clothing & shoes")
            default_cond = st.session_state.get("prefill_condition", "Good")

            item_name = st.text_input("Item name *", value=st.session_state.get("prefill_item_name", ""), placeholder="e.g. First-year engineering textbooks", max_chars=100)
            item_category = st.selectbox("Category *", cat_options, index=cat_options.index(default_cat) if default_cat in cat_options else 0)
            item_condition = st.selectbox("Condition *", cond_options, index=cond_options.index(default_cond) if default_cond in cond_options else 1)
            item_location = st.text_input("Area / city *", placeholder="e.g. Kasturi Nagar, Bengaluru", max_chars=120)
        with d2:
            donor_name = st.text_input("Your display name *", placeholder="First name or nickname", max_chars=80)
            donor_contact = st.text_input("Your email or phone *", placeholder="Used to contact you after approval", max_chars=120)
            contact_type = st.selectbox("Contact preference", ["Email", "Phone / WhatsApp", "Either"])
            listing_pin = st.text_input("Create a private 6+ character listing PIN *", type="password", max_chars=64)
        item_description = st.text_area(
            "Description *",
            value=st.session_state.get("prefill_description", ""),
            placeholder="Mention size, model, included accessories, defects, pickup conditions, etc.",
            max_chars=1000,
        )
        safety_confirm = st.checkbox("I confirm this item is legal, safe to give away, and described honestly.")
        submit_donation = st.form_submit_button("🌱 Publish Donation Listing", use_container_width=True)
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
            for k in ["prefill_item_name", "prefill_category", "prefill_condition", "prefill_description"]:
                st.session_state.pop(k, None)
            st.success(f"Your donation is listed! Your listing ID is **REV-{new_id:05d}**. Save this ID and your private PIN to manage requests.")
            st.info("Your contact details are not displayed publicly. They are revealed to a requester only after you approve their request.")
            st.code(f"Listing ID: REV-{new_id:05d}", language=None)

# -------------------- Donor request management --------------------

with tab_manage:
    st.markdown("## 📬 Manage Your Donation Requests")
    st.write("Enter your listing ID and private PIN to view requests and approve or decline them.")
    st.markdown("""
    <div class="marketplace-note">
    <b>How approval works:</b> approving a request shares your contact preference and contact details with that requester, marks the item as reserved, and declines other pending requests for the same item. Final handover is arranged by both people.
    </div>
    """, unsafe_allow_html=True)
    with st.form("manage_listing_form"):
        manage_id_text = st.text_input("Listing ID", placeholder="e.g. REV-00012")
        manage_pin = st.text_input("Private listing PIN", type="password")
        load_listing = st.form_submit_button("🔑 View Requests", use_container_width=True)
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
    st.markdown("## 📦 Track Your Request")
    st.write("Check whether the donor has approved your request. Enter the request ID shown when you submitted it and the same contact detail you used.")
    if st.session_state.get("last_request_id"):
        st.info(f"Your most recent request ID in this session: **REV-R{st.session_state.last_request_id:05d}**")
    with st.form("track_request_form"):
        track_id_text = st.text_input("Request ID", placeholder="e.g. REV-R00012")
        track_contact = st.text_input("Your email or phone used for the request")
        track_submit = st.form_submit_button("🔎 Check Request Status", use_container_width=True)
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
