# 🌱 REVORA — Waste-to-Design Intelligence & Circular Reuse Platform

**Rethink materials. Reuse what works. Revive everyday objects before they become waste.**

REVORA is a full-stack circular-economy web application built with **Python, Streamlit, SQLite, and the Google Gemini API**. It unifies product lifecycle analytics, multimodal AI object inspection, anti-greenwashing verification, peer-to-peer tool lending, and a privacy-first community reuse marketplace inside a single biomorphic interface.

---

## ✨ Complete Feature Suite

### 1. 🌿 Product Lifecycle Explorer & 5-Pillar EcoScore
* **42+ Everyday Products Catalog:** Fault-tolerant built-in dataset spanning 10+ categories (`Drinkware`, `Electronics`, `Clothing`, `Home cleaning`, `Personal care`, `Food containers`, `Bags`, `Stationery`, `Household`, and `Food & drink`).
* **Customizable 5-Pillar EcoScore ($0\text{--}100$):** Dynamically weights **Materials & Sourcing (25%)**, **Durability & Lifespan (25%)**, **Usage & Reuse (20%)**, **Packaging Impact (15%)**, and **Repair & End-of-Life (15%)** via interactive sidebar sliders.
* **🕸️ 5-Axis SVG Radar Comparison:** Zero-dependency vector radar chart comparing any selected product against higher-scoring category alternatives across all five lifecycle dimensions.

### 2. ⚖️ Break-Even Reuse Calculator & ♻️ Plastic Resin Decoder
* **Break-Even Reuse Math:** Calculates the exact number of uses and weeks required for a durable product to offset its manufacturing footprint compared to single-use disposables, projecting multi-year disposable units avoided, net carbon savings ($\text{kg CO}_2$), and waste diverted ($\text{kg}$).
* **Interactive Plastic Resin & Symbol Decoder (`#1–#7` & `WEEE`):** Decodes packaging resin codes (`#1 PET` through `#7 Other`, `PLA Biopolymers`, and `WEEE E-Waste` symbols) to reveal real-world municipal recyclability, chemical leaching risks, and circular material swaps.

### 3. 🤖 REVORA AI Studio (Multimodal Vision, Upcycling & Anti-Greenwashing)
* **📸 AI Object Condition Scanner:** Upload or snap a photo of any household item using `gemini-2.5-flash` vision to receive an automated **Condition Score ($0\text{--}100$)**, triage status (`Usable`, `Needs Minor Repair`, `Bad Condition`), and a **1-click pre-fill** into the donation/lending form.
* **🛠️ DIY Upcycling Blueprint Generator:** Generates step-by-step creative upcycling guides, required tool lists, and safe material disassembly instructions for worn or broken items.
* **🕵️‍♂️ AI Greenwashing Claim Detector:** Audits product marketing claims and label text to flag vague eco-buzzwords, evaluate third-party certifications, and assign a **Trust Score ($0\text{--}100$)** (with an offline heuristic analyzer fallback).
* **🎙️ Voice Search & 🔊 Read Aloud Accessibility:** Supports hands-free voice queries via `st.audio_input` and native browser Text-to-Speech (`window.speechSynthesis`) playback across AI responses.

### 4. 🤝 Privacy-First Donations & 🔄 Peer Tool Library (Borrow & Return)
* **Permanent Donations & Temporary Loans:** Users can list items as a **Permanent Donation** or under **Peer Lending (Borrow & Return)** with a configurable **1–30 day loan duration** for high-utility items like scientific calculators, drafting kits, soldering irons, and power tools.
* **One-Click Tool Relisting:** Once a borrowed tool is returned, the lender can relist it as `Available` in a single click for the next community borrower.
* **🔒 PIN-Protected Donor Management:** Listings are secured with a **SHA-256 hashed PIN** (`REV-000xx`) and constant-time verification (`secrets.compare_digest`). Contact details remain private until a request is explicitly approved.
* **🎫 Cryptographic SVG QR Handover Pass:** Approving a donation or loan request generates a deterministic SVG verification matrix and pickup pass (`REV-PASS-XXXXXXXX`) displaying the handover zone and listing mode.

### 5. 📌 Community Wish Board & 🎯 Smart Wish-to-Donation Matchmaker
* **Reverse Marketplace (Wish Board):** Students and neighbors can post specific items they are looking for (`Books & education`, `Electronics`, etc.) with a 1-click **Fulfill This Wish** button that pre-fills the listing form.
* **Automated Supply-Demand Matchmaker:** Cross-references active Wish Board posts against available marketplace listings using category and keyword token overlap, surfacing live percentage matches (`🎯 85% Match`) and alerting donors immediately upon listing creation.

### 6. 🏆 Donor Leaderboard, Milestone Badges & 📜 Impact Certificates
* **Gamified Milestone Tiers:** Tracks both permanent donations and tool library loans on a live community leaderboard:
  * 🌱 **Seedling Starter** ($1+$ listed or rehomed)
  * 🌿 **Circular Guardian** ($2+$ rehomed)
  * 🌳 **Zero-Waste Champion** ($5+$ rehomed)
  * 👑 **REVORA Earth Legend** ($10+$ rehomed)
* **Downloadable Certificate of Circular Impact:** Exports a personalized, verifiable HTML/printable A4 certificate (`REV-CERT-XXXXXXXXXX`) summarizing items rehomed, tool loans, $\text{kg}$ waste diverted, and $\text{kg CO}_2$ prevented for student portfolios and NSS/service logs.

### 7. 🛠️ Local Repair & Certified E-Waste Directory
* Filterable neighborhood directory of tailors, electronics repair cafes, cobblers, campus makerspaces, and authorized e-waste drop-off centers.
* Community-extensible SQLite table allowing users to add new local repair specialists and collection bins.

### 8. 🎨 Biomorphic Glass UI & Midnight Forest Dark Mode
* Custom CSS3 glassmorphic cards, animated SVG leaf splash screen, live hero impact counters, and an instant sidebar toggle between **Botanical Light Mode** and **Midnight Forest Dark Mode**.

---

## 🏗️ System Architecture & Tech Stack

| Layer | Technology / Implementation |
| :--- | :--- |
| **Frontend & UI** | Python, Streamlit, Biomorphic Glassmorphism CSS3, Custom Inline SVG Graphics |
| **Multimodal AI Engine** | Google GenAI SDK (`google-genai`) — `gemini-2.5-flash` with fallback to `gemini-3.5-flash-lite` & `gemini-2.0-flash` |
| **Voice & Accessibility** | Streamlit `st.audio_input` + HTML5 Web `SpeechSynthesis` API |
| **Database & Persistence** | SQLite3 (`revora_marketplace.db`) with automated schema migration & parameterized SQL queries |
| **Data & Analytics** | Pandas (`products.csv` + embedded 42-product errorless fallback catalog) |
| **Security & Privacy** | `hashlib.sha256` PIN & certificate hashing, `secrets.compare_digest`, `html.escape` XSS sanitization |

---

## 🗄️ Database Schema (`revora_marketplace.db`)

REVORA automatically initializes and migrates four relational SQLite tables on startup:
1. **`items`** — Stores donation and lending listings, condition, location, `listing_mode` (`Permanent Donation` or `Peer Lending`), `loan_days`, hashed donor PINs, and status (`Available`, `Reserved`, `Donated`).
2. **`requests`** — Tracks pickup and borrowing requests (`REV-R000xx`), requester messages, and approval status (`Pending`, `Approved`, `Declined`).
3. **`wishes`** — Powers the Community Wish Board and Smart Matchmaker with active neighborhood item requests.
4. **`repair_hubs`** — Stores verified local tailors, electronics repair shops, and certified e-waste drop-off centers (pre-seeded on first launch).

---

## 🚀 Local Setup & Installation

### 1. Clone the Repository
```bash
git clone [https://github.com/your-username/revora.git](https://github.com/your-username/revora.git)
cd revora
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

*(Ensure `requirements.txt` contains `streamlit>=1.40.0`, `pandas>=2.0.0`, and `google-genai>=1.0.0`.)*

### 3. Configure Your Gemini API Key
Create a `.streamlit/secrets.toml` file in the project root:
```toml
GEMINI_API_KEY = "your_google_gemini_api_key_here"
```

### 4. Run the Application
```bash
streamlit run app.py
```

---

## ☁️ Deploying on Streamlit Community Cloud

1. Push `app.py`, `products.csv`, `requirements.txt`, and `README.md` to your GitHub repository.
2. Sign in to [Streamlit Community Cloud](https://share.streamlit.io/) and click **Create app**.
3. Select your repository, branch (`main`), and main file path (`app.py`).
4. Open **Advanced settings -> Secrets** and paste:
   ```toml
   GEMINI_API_KEY = "your_google_gemini_api_key_here"
   ```
5. Click **Deploy!**

---

## 🛡️ Safety & Disclaimer
* **Heuristic EcoScores:** Lifecycle scores, resin recyclability rates, and break-even profiles are educational decision-support estimates rather than certified ISO lifecycle assessments (LCAs).
* **Safe Handovers:** Always arrange community item pickups and tool returns in well-lit, public locations and verify your digital `REV-PASS` code upon handover.
