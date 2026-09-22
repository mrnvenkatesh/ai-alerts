# Daily Generative AI News Aggregator & Email Digest

A production-ready, automated daily Generative AI news aggregator and email digest application with scheduled execution.

Every day at **06:00 AM IST (00:30 UTC)**, this service automatically scrapes and filters the most significant Gen AI developments from the last 24 hours, synthesizes them into an executive briefing using Google Gemini (or OpenAI / rule-based engine), and delivers a responsive HTML email briefing to technical leaders and teams.

---

## 🏛️ System Architecture & Components

```
                               ┌──────────────────────────┐
                               │     Authoritative        │
                               │    Gen AI Sources        │
                               │ (ArXiv, HF, Lab Blogs,   │
                               │   Tech News, HN AI)      │
                               └────────────┬─────────────┘
                                            │
                                            ▼
                               ┌──────────────────────────┐
                               │   1. Ingestion &         │
                               │      Deduplication       │
                               │      (fetcher.py)        │
                               └────────────┬─────────────┘
                                            │
                                            ▼
                               ┌──────────────────────────┐
                               │   2. AI Analysis &       │
                               │      Summarization       │
                               │    (synthesizer.py)      │
                               └────────────┬─────────────┘
                                            │
                                            ▼
                               ┌──────────────────────────┐
                               │   3. Email Rendering     │
                               │      & Delivery          │
                               │      (mailer.py)         │
                               └────────────┬─────────────┘
                                            │
                                            ▼
                               ┌──────────────────────────┐
                               │   4. Scheduler / CI      │
                               │ (APScheduler / GitHub    │
                               │  Actions / Docker)       │
                               └──────────────────────────┘
```

1. **Information Ingestion & Scraping (`src/fetcher.py`)**:
   - Scrapes authoritative Gen AI feeds:
     - ArXiv RSS (`cs.AI`, `cs.CL`) & Hugging Face Blog RSS
     - Tech/AI news feeds (TechCrunch AI, VentureBeat, MIT Tech Review, HN Algolia AI search API)
     - Major lab releases (OpenAI News, Google DeepMind Blog)
   - Filters items published within the last 24 hours.
   - Deduplicates items across sources using URL normalization and title Jaccard word set similarity.

2. **Analysis & Summarization Pipeline (`src/synthesizer.py`)**:
   - Ranks items to select 5–8 top stories for executive focus.
   - Generates 2–3 sentence non-fluff summaries explaining what launched and why it matters technically and strategically.
   - Categorizes each story into primary tags: `Research`, `Product`, `Open Source`, or `Industry`.
   - Generates a 2-sentence top-level executive macro overview.
   - Uses `google-genai` SDK (Google Gemini API) or OpenAI API with automatic fallback to an offline synthesizer if no API key is present.

3. **Email Formatting & Delivery (`src/mailer.py`)**:
   - Renders responsive HTML emails using Jinja2 with an executive dark glassmorphism aesthetic.
   - Includes fallback plain-text email formatting.
   - Delivers via SMTP (SendGrid, AWS SES, Gmail, custom SMTP) using secure TLS/SSL authentication.
   - Supports dry-run mode, saving rendered HTML and text output to local `output/` files.

4. **Scheduling & Deployment (`src/scheduler.py`)**:
   - Integrated local scheduler powered by `APScheduler` configured for `0 6 * * *` in `Asia/Kolkata` timezone.
   - Zero-maintenance GitHub Actions workflow (`.github/workflows/daily_briefing.yml`).
   - Production Docker container image for serverless job runners (Google Cloud Run Jobs, AWS Lambda, ECS).

---

## 📁 Directory Structure

```text
alerts/
├── .env.example                # Template for environment configuration
├── .gitignore                  # Git ignore definitions
├── Dockerfile                  # Container definition for serverless/Cron execution
├── README.md                   # Comprehensive documentation & setup guide
├── requirements.txt            # Locked Python dependencies
├── .github/
│   └── workflows/
│       └── daily_briefing.yml  # GitHub Actions daily schedule workflow
└── src/
    ├── __init__.py             # Package marker
    ├── fetcher.py              # Ingestion, RSS parsing, date filtering & deduplication
    ├── synthesizer.py          # GenAI LLM summarization & categorizer
    ├── mailer.py               # Responsive HTML/text rendering & SMTP mailer
    └── scheduler.py            # CLI entry point & APScheduler loop
```

---

## 🚀 Quick Start & Local Setup

### 1. Prerequisites
- Python 3.10+
- Pip package manager

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy `.env.example` to `.env` and fill in your credentials:
```bash
cp .env.example .env
```

Edit `.env`:
```env
# LLM API Keys (Optional: standard offline synthesizer runs if omitted)
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# SMTP Email Configuration
SENDER_EMAIL=digest@yourdomain.com
RECIPIENT_EMAIL=executive@yourdomain.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password

# Settings
TIMEZONE=Asia/Kolkata
MAX_STORIES=8
```

---

## 🧪 Execution Commands

### Run Immediate Dry-Run (No Email Sent, Writes HTML Preview)
```bash
python src/scheduler.py --now --dry-run
```
Output files will be saved in `output/`:
- `output/digest_[date].html` (Viewable in any web browser)
- `output/digest_[date].txt`

### Run Immediate Production Pipeline (Sends Email via SMTP)
```bash
python src/scheduler.py --now
```

### Start Daily Local Scheduler (06:00 AM IST / 00:30 UTC)
```bash
python src/scheduler.py --schedule
```

---

## 🐳 Docker Deployment

Build the container image:
```bash
docker build -t genai-daily-briefing .
```

Run immediate container execution with local `.env` file:
```bash
docker run --rm --env-file .env genai-daily-briefing
```

---

## ⚡ GitHub Actions Automation

The repository includes a ready-to-use GitHub Actions workflow located at `.github/workflows/daily_briefing.yml`.

### Setup Instructions:
1. Push this repository to GitHub.
2. Navigate to **Settings > Secrets and variables > Actions** in your GitHub repository.
3. Add the following repository secrets:
   - `GEMINI_API_KEY`
   - `RECIPIENT_EMAIL`
   - `SENDER_EMAIL`
   - `SMTP_HOST`
   - `SMTP_PORT`
   - `SMTP_USER`
   - `SMTP_PASS`
4. The workflow will automatically run every day at **00:30 UTC (06:00 AM IST)** or can be triggered manually under the **Actions** tab.

---

## ☁️ Deploying to Google Cloud Platform (GCP)

### Recommended GCP Architecture
The application runs as a serverless **Cloud Run Job** triggered daily at **06:00 AM IST** by **Cloud Scheduler**. Estimated cost is **near $0/month** (fits entirely within GCP Free Tier).

```
┌─────────────────────┐       HTTP POST        ┌─────────────────────┐
│   Cloud Scheduler   │ ─────────────────────> │    Cloud Run Job    │
│ (Cron: 30 0 * * *)  │  (06:00 AM IST)        │ (Runs container for │
└─────────────────────┘                        │  ~1 min & exits)    │
                                               └─────────────────────┘
```

### Information Needed from Your Side:
1. **GCP Project ID**
2. **GCP Region** (e.g., `us-central1` or `asia-south1`)
3. **LLM API Key** (`GEMINI_API_KEY` from Google AI Studio or `OPENAI_API_KEY`)
4. **SMTP Credentials** (`SENDER_EMAIL`, `RECIPIENT_EMAIL`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`)

### One-Command Automated GCP Deployment
1. Authenticate with Google Cloud CLI:
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```
2. Populate `.env` with your API keys and SMTP credentials.
3. Run the deployment script:
   ```bash
   ./deploy_gcp.sh
   ```

### Immediate Test Execution in GCP
After deployment, trigger a manual test run in GCP:
```bash
gcloud run jobs execute genai-daily-briefing --region=us-central1
```

---

## 📝 License
MIT License. Built for automated daily GenAI intelligence.
