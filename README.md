# 🌱 REVORA — Waste-to-Design Intelligence & Circular Reuse Platform

**Rethink materials. Reuse what works. Revive everyday objects before they become waste.**

REVORA is a full-stack circular-economy web application built with **Python, Streamlit, SQLite, and the Google Gemini API**. It combines lifecycle sustainability analytics, multimodal AI object inspection, anti-greenwashing verification, and a privacy-first hyper-local reuse marketplace in a single biomorphic interface.

---

## ✨ Complete Feature Suite

### 1. 🌿 Product Lifecycle Explorer & 5-Pillar EcoScore
* **42+ Everyday Products Catalog:** Built-in, fault-tolerant dataset spanning 10+ categories (`Drinkware`, `Electronics`, `Clothing`, `Home cleaning`, `Personal care`, `Food containers`, `Bags`, `Stationery`, `Household`, and `Food & drink`).
* **Customizable 5-Pillar EcoScore ($0\text{--}100$):** Dynamically weights **Materials & Sourcing (25%)**, **Durability & Lifespan (25%)**, **Usage & Reuse (20%)**, **Packaging Impact (15%)**, and **Repair & End-of-Life (15%)** via interactive sidebar sliders.
* **🕸️ 5-Axis SVG Radar Comparison:** Zero-dependency vector radar chart comparing any selected product against higher-scoring category alternatives across all five lifecycle dimensions.

### 2. ⚖️ Break-Even Reuse Calculator
* Calculates the exact number of uses and weeks required for a durable, reusable product to offset its manufacturing footprint compared to single-use disposables.
* Projects multi-year disposable units avoided, net carbon savings ($\text{kg CO}_2$), and landfill waste diverted ($\text{kg}$) based on weekly usage frequency.

### 3. 🤖 REVORA AI Studio (Multimodal Vision, Upcycling & Anti-Greenwashing)
* **📸 AI Object Condition Scanner:** Upload or snap a photo of any household item using `gemini-2.5-flash` vision to receive an automated **Condition Score ($0\text{--}100$)**, triage status (`Usable`, `Needs Minor Repair`, `Bad Condition`), and a **1-click pre-fill** into the community donation form.
* **🛠️ DIY Upcycling Blueprint Generator:** Automatically generates step-by-step creative upcycling guides, required tool lists, and safe material disassembly instructions for worn or broken items.
* **🕵️‍♂️ AI Greenwashing Claim Detector:** Audits product marketing claims and label text to flag vague eco-buzzwords, evaluate third-party certifications, and assign a **Trust Score ($0\text{--}100$)** (includes an offline heuristic analyzer fallback).
* **🎙️ Voice Search & 🔊 Read Aloud Accessibility:** Supports hands-free multilingual voice queries via `st.audio_input` and native browser Text-to-Speech (`window.speechSynthesis`) playback on all AI outputs.

### 4. 🤝 Privacy-First Community Reuse Marketplace
* **🔎 Browse & Request Donations:** Discover available neighborhood items and submit pickup requests without exposing donor phone numbers or emails publicly.
* **🔒 PIN-Protected Donor Management:** Donors secure their listings with a **SHA-256 hashed PIN** (`REV-000xx`) and constant-time verification (`secrets.compare_digest`) to approve or decline requests.
* **🎫 Cryptographic SVG QR Handover Pass:** Approving a request automatically generates a deterministic SVG verification matrix and pickup pass (`REV-PASS-XXXXXXXX`) for safe, verifiable public handovers.
* **🏆 Donor Leaderboard & Milestone Badges:** Gamifies community reuse by awarding dynamic badges as users rehome items:
  * 🌱 **Seedling Starter** ($1+$ listed or rehomed)
  * 🌿 **Circular Guardian** ($2+$ rehomed)
  * 🌳 **Zero-Waste Champion** ($5+$ rehomed)
  * 👑 **REVORA Earth Legend** ($10+$ rehomed)

### 5. 📌 Community Wish Board & 📊 Live Impact Counter
* **Reverse Marketplace (Wish Board):** Allows students and neighbors to post specific items they need (e.g., scientific calculators, textbooks, tools) so donors with surplus items can fulfill requests directly.
* **Live Ecological Impact Ticker:** Real-time hero banner metrics tracking cumulative community waste diverted ($\text{kg}$) and carbon emissions prevented ($\text{kg CO}_2$).

### 6. 🛠️ Local Repair & Certified E-Waste Directory
* Filterable neighborhood directory of tailors, electronics repair cafes, cobblers, campus makerspaces, and authorized e-waste drop-off centers.
* Community-extensible SQLite table allowing users to submit new local repair shops and collection bins.

### 7. 🎨 Biomorphic Glass UI & Midnight Forest Dark Mode
* Custom CSS3 glassmorphic cards, animated SVG leaf splash screen, responsive pill tabs, and a instant sidebar toggle between **Botanical Light Mode** and **Midnight Forest Dark Mode**.

---

## 🏗️ System Architecture & Tech Stack

| Layer | Technology / Implementation |
| :--- | :--- |
| **Frontend & UI** | Python, Streamlit, Biomorphic Glassmorphism CSS3, Custom Inline SVG Graphics |
| **Multimodal AI Engine** | Google GenAI SDK (`google-genai`) — `gemini-2.5-flash` with fallback to `gemini-3.5-flash-lite` & `gemini-2.0-flash` |
| **Voice & Accessibility** | Streamlit `st.audio_input` + HTML5 Web `SpeechSynthesis` API |
| **Database & Persistence** | SQLite3 (`revora_marketplace.db`) with parameterized SQL queries across 4 relational tables |
| **Data & Analytics** | Pandas (`products.csv` + embedded 42-product errorless fallback catalog) |
| **Security & Privacy** | `hashlib.sha256` PIN hashing, `secrets.compare_digest`, `html.escape` XSS sanitization |

---

## 🗄️ Database Schema (`revora_marketplace.db`)

REVORA automatically initializes four SQLite tables on startup:
1. **`items`** — Stores community donation listings, condition, location, hashed donor PINs, and status (`Available`, `Reserved`, `Donated`).
2. **`requests`** — Tracks item requests (`REV-R000xx`), requester messages, and approval status (`Pending`, `Approved`, `Declined`).
3. **`wishes`** — Powers the Community Wish Board with active neighborhood item requests.
4. **`repair_hubs`** — Stores verified local tailors, electronics repair shops, and e-waste drop-off centers (pre-seeded on first launch).

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
* **Heuristic EcoScores:** Lifecycle scores and break-even profiles are educational decision-support estimates rather than certified ISO lifecycle assessments (LCAs).
* **Safe Handovers:** Always arrange community item pickups in well-lit, public locations and verify your digital `REV-PASS` code upon handover.
