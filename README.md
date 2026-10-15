# REVORA — Waste-to-Design Intelligence

REVORA is an 8-hour hackathon MVP that maps product waste problems to practical design interventions and sustainable alternatives.

## Features
- Search and filter a sample product dataset
- Weighted EcoScore with visible criteria
- Waste-problem selector and design intervention suggestions
- Ranked alternative product cards with trade-offs
- Transparent caveats about heuristic scores and lifecycle data

## Run locally
1. Install Python 3.10 or newer.
2. Open a terminal in this folder.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run:
   ```bash
   streamlit run app.py
   ```

## Deploy on Streamlit Community Cloud
1. Create a GitHub repository and upload `app.py`, `products.csv`, and `requirements.txt`.
2. In Streamlit Community Cloud, choose the repository and set the main file to `app.py`.
3. Deploy.

## Important limitations
- Product scores in `products.csv` are illustrative demo inputs, not verified environmental measurements.
- The design recommendations are rule-based. They do not establish that a proposed design is novel or commercially available.
- For a real deployment, add cited product specifications, data confidence, local disposal rules, and lifecycle assessment evidence.
