# 🌱 REVORA | Waste-to-Design Intelligence & Community Reuse Marketplace

**REVORA** is a circular-economy web application built with Python, Streamlit, SQLite, and the Google Gemini API. It bridges sustainable product choices with hyper-local community reuse.

## ✨ Key Features
- **🌿 Product Explorer & EcoScore:** Evaluates 24+ everyday products across 5 weighted lifecycle pillars (Materials, Lifespan, Packaging, Usage, and End-of-Life) with actionable design interventions.
- **📸 AI Object Scanner:** Upload or snap a photo of any household item to analyze its physical condition (`0–100` score), get repair vs. donate guidance, and auto-fill donation listings in one click.
- **🎙️ Voice Search & 🔊 Read Aloud:** Speak questions directly to REVORA AI using the built-in microphone and listen to responses with browser Text-to-Speech.
- **🎁 Privacy-First Reuse Marketplace:** Donate usable items with a private 6+ character PIN, approve/decline community requests, and track request statuses (`REV-R000xx`) without exposing donor contact info publicly.

## 🚀 Deploy on Streamlit Community Cloud
1. Upload `app.py`, `products.csv`, and `requirements.txt` to the root of your GitHub repository.
2. Set the app entry point to `app.py`.
3. To enable the AI Scanner, Voice Search, and Chat, add your key in **Streamlit Cloud → App settings → Secrets**:

```toml
GEMINI_API_KEY = "your-gemini-api-key"
```

## ⚠️ Prototype Notes
- EcoScores are illustrative heuristics, not certified lifecycle assessments.
- Marketplace data is stored in a local SQLite database (`revora_marketplace.db`). For permanent production storage across container resets, connect a hosted database (e.g., Supabase).
- Arrange handovers in safe, public places and never send money to strangers.
