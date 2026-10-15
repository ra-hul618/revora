# REVORA

REVORA is a Streamlit prototype for sustainability-oriented product exploration and a community donate/request marketplace. It includes a branded animated loading screen, product EcoScores, and an optional Gemini AI chat.

## Deploy on Streamlit Community Cloud
1. Upload `app.py`, `products.csv`, and `requirements.txt` to the root of your GitHub repository.
2. Set the app entry point to `app.py`.
3. To enable the AI chat, add this in Streamlit Cloud → App settings → Secrets:

```toml
GEMINI_API_KEY = "your-gemini-api-key"
```

The app runs without the key; the AI tab will explain that the key is missing.

## Important prototype notes
- EcoScores are illustrative heuristics, not certified lifecycle assessments.
- Marketplace data is stored in a local SQLite database. Streamlit Community Cloud local files may not persist across rebuilds or runtime resets; use a hosted database for durable public use.
- The app is a prototype. Use safe, public handover arrangements and do not send money to strangers.
