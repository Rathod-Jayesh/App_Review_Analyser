# GROWW App Review Analyser

Automated pipeline that turns Play Store reviews into a **weekly pulse note** with top themes, real user quotes, and action ideas — then emails it to your team.

## Who This Helps

- **Product / Growth Teams** — understand what to fix next
- **Support Teams** — know what users are saying & acknowledge trends
- **Leadership** — quick weekly health pulse in one page

## Architecture

The project is built in **6 phases**, each handling a specific part of the pipeline:

| Phase | What It Does | LLM Used |
|-------|-------------|----------|
| **Phase 1** | Scrape Play Store reviews, filter (language, word count), scrub PII | — |
| **Phase 2a** | Discover 3–5 recurring themes from reviews | Groq (`llama-3.3-70b`) |
| **Phase 2b** | Classify every review into a theme | Groq (`llama-3.1-8b`) |
| **Phase 3** | Generate a one-page Weekly Review Pulse note | Gemini (`gemini-2.5-flash`) |
| **Phase 4** | Draft & send email with the pulse note | — |
| **Phase 5** | Dashboard UI + CLI for pipeline control | — |
| **Phase 6** | Weekly scheduler (local + GitHub Actions) | — |

## Tech Stack

- **Backend:** Python, FastAPI
- **Frontend:** Static SPA — Alpine.js, TailwindCSS, Marked.js (served via FastAPI)
- **LLMs:** Groq (theme discovery & classification), Google Gemini (note generation)
- **Email:** Gmail SMTP with App Password
- **Scheduler:** Python `schedule` library + GitHub Actions cron
- **PDF:** `xhtml2pdf` for pulse note PDF export

## Quick Start

### 1. Clone & install

```bash
git clone https://github.com/Rathod-Jayesh/App_Review_Analyser.git
cd App_Review_Analyser
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

### 2. Configure environment

Copy the example and fill in your API keys:

```bash
cp .env.example .env
```

| Variable | Description |
|----------|-------------|
| `GROQ_API_KEY` | API key from [Groq Console](https://console.groq.com) |
| `GEMINI_API_KEY` | API key from [Google AI Studio](https://aistudio.google.com) |
| `EMAIL_SENDER` | Your Gmail address |
| `EMAIL_PASSWORD` | Gmail App Password ([how to get one](https://support.google.com/accounts/answer/185833)) |

### 3. Run the dashboard

```bash
uvicorn main:app --reload --port 8000
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

### 4. Run via CLI

```bash
# Full pipeline: fetch → themes → classify → generate note → send email
python cli.py run-all --recipient you@example.com --name "Your Name" --weeks 8 --max-reviews 1000 --send

# Individual phases
python cli.py fetch --weeks 8 --max-reviews 1000
python cli.py themes
python cli.py classify
python cli.py generate
python cli.py email --recipient you@example.com --name "Your Name" --send
```

### 5. Scheduler (automated weekly runs)

```bash
# Start scheduler — runs every Monday at 12:35 PM IST
python scheduler.py

# Run immediately once, then continue on schedule
python scheduler.py --run-now

# Custom day/time
python scheduler.py --day wednesday --time 10:00
```

## GitHub Actions

The pipeline also runs automatically via GitHub Actions every **Monday at 12:35 PM IST**.

### Setup

1. Go to your repo **Settings → Secrets and variables → Actions**
2. Add these secrets:
   - `GROQ_API_KEY`
   - `GEMINI_API_KEY`
   - `EMAIL_SENDER`
   - `EMAIL_PASSWORD`

### Manual trigger

Go to **Actions → Weekly Review Pulse → Run workflow** to trigger manually with custom week range and review count.

## Project Structure

```
├── main.py                  # FastAPI app entry point
├── cli.py                   # CLI for running pipeline phases
├── scheduler.py             # Weekly scheduler
├── requirements.txt         # Python dependencies
├── .env.example             # Environment template
├── .github/workflows/       # GitHub Actions workflow
├── ARCHITECTURE.md          # Detailed architecture document
├── static/
│   ├── index.html           # Dashboard SPA
│   └── app.js               # Frontend logic (Alpine.js)
└── src/
    ├── common/              # Shared models, clients, constants
    │   ├── models.py
    │   ├── groq_client.py
    │   ├── gemini_client.py
    │   ├── constants.py
    │   ├── pii_scrubber.py
    │   └── storage.py
    ├── phase1/              # Review scraping & filtering
    ├── phase2/              # Theme discovery & classification
    ├── phase3/              # Weekly note generation
    ├── phase4/              # Email composition & delivery
    └── phase5/              # Dashboard API routes
```

## Dashboard Preview

The dashboard provides three main views:

- **Dashboard** — Review stats, rating distribution, discovered themes
- **Pipeline** — Run the full pipeline with configurable week range and review count
- **Weekly Pulse** — View generated notes, download PDF, send emails

## License

MIT
