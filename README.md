# REVORA — Sustainable Product Recommendations + Donate & Request Marketplace

REVORA helps people explore sustainable product choices and keep usable goods in circulation through a community donation marketplace.

## Features
- Product EcoScore explorer and waste-to-design recommendations.
- Browse available donated items by category or keyword/location.
- Publish donation listings with category, condition, location, description, and private listing PIN.
- Request an item with a message and contact details.
- Donors can review requests and approve or decline them.
- Requesters can track request status with their request ID and the same contact detail they submitted.
- Approval reserves the item, shares donor contact details only with the approved requester, and declines other pending requests.
- Donors can mark a reserved item as donated/completed or unlist an available item.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy to Streamlit Community Cloud
1. Upload `app.py`, `products.csv`, `requirements.txt`, and `README.md` to your GitHub repository.
2. In Streamlit Community Cloud, select the repository and set the main file to `app.py`.
3. Deploy.

## Important storage note
The marketplace uses SQLite (`revora_marketplace.db`) as a simple MVP database. It is shared by users connected to the same running app instance, but local Streamlit Community Cloud storage is not durable and may be reset on rebuild/restart. For a public launch or a judged demo where data must persist, connect a hosted database such as Supabase/Postgres and keep credentials in Streamlit Secrets.

## Privacy and safety notes
- Donor contact details are hidden from the public browse view and shown only after donor approval.
- A listing PIN is used to manage requests. Donors should keep it private.
- This is a hackathon prototype, not a verified identity or secure authentication system. Use only test contact information for demos.
- Meet safely, inspect items, and never send money to strangers.
- EcoScores in the product explorer are illustrative heuristic values, not certified lifecycle assessments.
