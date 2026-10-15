import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(
    page_title="REVORA | Waste-to-Design Intelligence",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_PATH = Path(__file__).parent / "products.csv"

st.markdown("""
<style>
    .stApp { background: #f6f8f3; }
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
    .section-title { color: #173c2a; }
    div[data-testid="stMetric"] {
        background: white; border: 1px solid #dce7da; padding: 12px 16px; border-radius: 14px;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    df = pd.read_csv(DATA_PATH)
    numeric = ["material_score", "lifecycle_score", "packaging_score", "usage_score", "end_of_life_score"]
    for col in numeric:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(50).clip(0, 100)
    return df

df = load_data()

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
            "Look for replaceable parts, accessible fasteners, spare-part availability, and a repair guide. "
            "Avoid replacing the whole product when one component fails."
        ),
        "Too much product is dispensed or used": (
            "Choose controlled-dose or refillable packaging",
            "A measured dispenser, adjustable opening, or refill pack may reduce overuse and packaging. "
            "Check that the refill format is actually available locally."
        ),
        "Packaging is excessive": (
            "Prefer right-sized, concentrated, or refill packaging",
            "Compare packaging per use—not just package size. Concentrates and refills help only when "
            "they reduce total material and are used as intended."
        ),
        "Product is rarely used": (
            "Borrow, share, or keep using what you own",
            "Before buying a greener replacement, test whether sharing, renting, repairing, or changing "
            "your routine solves the need without a new product."
        ),
        "Single-use waste builds up": (
            "Switch to a durable alternative if reuse is frequent",
            "Compare expected lifetime uses, cleaning needs, and end-of-life options. A reusable product "
            "is most helpful when it replaces many single-use items."
        ),
        "Hard to recycle or dispose of": (
            "Choose simpler materials and a known take-back route",
            "Prefer clearly labelled materials and check local collection rules. 'Compostable' does not "
            "necessarily mean it can go in a home compost or local bin."
        ),
    }
    return rules[problem]

def generate_recommendation(problem, category, current_row, candidates):
    title, explanation = intervention_for(problem, current_row["product_name"])
    if problem == "Product is rarely used":
        candidates = candidates[candidates["category"] == category]
        return title, explanation, candidates.sort_values("eco_score", ascending=False).head(3)

    # Prefer alternatives with a strong score and a category match.
    same_category = candidates[candidates["category"] == category].copy()
    if same_category.empty:
        same_category = candidates.copy()
    current_score = float(current_row["eco_score"])
    same_category = same_category[same_category["product_name"] != current_row["product_name"]]
    same_category["score_gain"] = same_category["eco_score"] - current_score
    same_category = same_category.sort_values(["eco_score", "score_gain"], ascending=False)
    return title, explanation, same_category.head(3)

if "search_text" not in st.session_state:
    st.session_state.search_text = ""

with st.sidebar:
    st.markdown("## 🌱 REVORA")
    st.caption("Waste-to-Design Intelligence")
    st.markdown("---")
    st.markdown("### Find a better design")
    categories = ["All categories"] + sorted(df["category"].unique().tolist())
    selected_category = st.selectbox("Product category", categories)
    problem_options = [
        "Single-use waste builds up",
        "Breaks before the rest wears out",
        "Too much product is dispensed or used",
        "Packaging is excessive",
        "Product is rarely used",
        "Hard to recycle or dispose of",
    ]
    problem = st.selectbox("Main waste problem", problem_options)
    priority = st.selectbox(
        "Your priority",
        ["Overall sustainability", "Longer lifespan", "Less packaging", "Repairability", "Reuse potential"],
    )
    st.markdown("---")
    st.caption("Prototype scores are heuristic estimates, not verified lifecycle assessment results.")

st.markdown("""
<div class="hero">
  <div class="pill">WASTE-TO-DESIGN INTELLIGENCE</div>
  <h1>REVORA</h1>
  <p>Turn waste into better design.</p>
  <p style="font-size:.94rem">Discover why products create waste. Find practical alternatives. Rethink what needs to be bought.</p>
</div>
""", unsafe_allow_html=True)

m1, m2, m3 = st.columns(3)
with m1:
    st.metric("Products in prototype", len(df))
with m2:
    st.metric("Product categories", df["category"].nunique())
with m3:
    st.metric("Design interventions", 6)

st.markdown("## Explore the product lifecycle")
search = st.text_input("Search products", placeholder="Try: bottle, notebook, cable, cleaner...")
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
                <div class="muted">{row['category']}</div>
                <h3 style="margin:.35rem 0">{row['product_name']}</h3>
                <div class="big-score">{row['eco_score']:.0f}<span style="font-size:.9rem;color:#627268"> / 100 EcoScore</span></div>
                <p style="min-height:3.2rem">{row['description']}</p>
                <span class="pill">{row['material']}</span>
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

        current_category = chosen["category"]
        candidates = df.copy()
        candidates["eco_score"] = candidates.apply(score_product, axis=1)
        if selected_category != "All categories":
            candidates = candidates[candidates["category"] == current_category]
        heading, details, recs = generate_recommendation(problem, current_category, chosen, candidates)
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
                      <div class="muted">{rec['category']}</div>
                      <h4>{rec['product_name']}</h4>
                      <div class="big-score">{rec['eco_score']:.0f}<span style="font-size:.8rem;color:#627268"> / 100</span></div>
                      <p>{rec['description']}</p>
                      <p><b>Trade-off:</b> {rec['tradeoff']}</p>
                    </div>
                    """, unsafe_allow_html=True)
        st.caption("Recommendations are based on the included demo dataset. Verify product claims, local recycling rules, and lifecycle evidence before making real-world comparisons.")

st.markdown("---")
st.markdown("## How REVORA decides")
with st.expander("View scoring model and limitations"):
    st.write("EcoScore is a weighted heuristic score designed for a hackathon prototype.")
    st.latex(r"EcoScore = 0.25M + 0.25L + 0.15P + 0.20U + 0.15E")
    st.write("M = materials and sourcing; L = durability and lifespan; P = packaging; U = usage and reuse; E = repairability and end-of-life.")
    st.warning("The included values are illustrative demo inputs, not measured carbon footprints or certified environmental claims. Missing or uncertain data should be marked and validated in a production system.")

st.markdown("""
<div style="text-align:center;color:#718076;padding:1rem 0">
  <b>REVORA</b> · Turn Waste Into Better Design<br/>
  <span style="font-size:.82rem">Hackathon prototype · Evidence-aware sustainability recommendations</span>
</div>
""", unsafe_allow_html=True)
