# GROWW App Review Analyser — Detailed Architecture

## Project Overview

Turn recent App Store / Play Store reviews for **GROWW** into a **one-page weekly pulse** containing top themes, real user quotes, and three action ideas — then draft an email with the weekly note.

### Who This Helps

| Audience | Value |
|----------|-------|
| **Product / Growth Teams** | Understand what to fix next |
| **Support Teams** | Know what users are saying & acknowledge issues |
| **Leadership** | Quick weekly health pulse |

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **Framework** | Next.js 14 (App Router) | Single codebase for frontend + API routes |
| **Language** | TypeScript | Type safety across the entire pipeline |
| **Styling** | TailwindCSS + Shadcn/UI | Modern, accessible, rapid UI development |
| **LLM (Phase 1-2)** | Groq API (`llama-3.3-70b-versatile`, `llama-3.1-8b-instant`) | Fast inference for theme discovery & review classification |
| **LLM (Phase 3+)** | Google Gemini API (`gemini-2.0-flash`) | Generous free-tier token limits; ideal for weekly note generation |
| **Review Scraping** | `google-play-scraper` + `app-store-scraper` (npm) | Battle-tested Node.js packages for store reviews |
| **Email** | Nodemailer (SMTP) or Resend API | Simple email drafting & delivery |
| **Storage** | JSON file-based (MVP) → SQLite/Prisma (scale) | Zero setup for MVP; easy migration path |
| **Scheduling** | `node-cron` or Vercel Cron Jobs (optional) | Automate weekly runs |

---

## High-Level System Flow

The **Dashboard UI** is the primary control surface — every phase is triggered, monitored, and consumed from the browser. No CLI required.

```
                        ┌─────────────────────────────────────────────┐
                        │           DASHBOARD UI (Next.js)            │
                        │                                             │
                        │   ┌─────────┐  ┌──────────┐  ┌──────────┐  │
                        │   │ Trigger │  │ Preview  │  │  Send    │  │
                        │   │ Buttons │  │ & Edit   │  │  Email   │  │
                        │   └────┬────┘  └─────┬────┘  └─────┬────┘  │
                        └────────┼─────────────┼─────────────┼────────┘
                                 │             │             │
                    ┌────────────▼─────────────▼─────────────▼────────────┐
                    │                   API ROUTES (Next.js)               │
                    └────────────────────────┬────────────────────────────┘
                                             │
         ┌───────────┬───────────┬───────────┼───────────┬───────────┐
         ▼           ▼           ▼           ▼           ▼           ▼
   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
   │ Phase 1  │ │ Phase 1b │ │ Phase 2a │ │ Phase 2b │ │ Phase 3  │ │ Phase 4  │
   │ SCRAPE   │ │ CLEAN    │ │ DISCOVER │ │ CLASSIFY │ │ GENERATE │ │ EMAIL    │
   │ Reviews  │ │ + PII    │ │ Themes   │ │ Reviews  │ │ Note     │ │ Draft &  │
   │          │ │ Scrub    │ │ (Groq)   │ │ (Groq)   │ │ (Groq)   │ │ Send     │
   └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

---

## Complete Folder Structure

```
app-review-analyser/
├── public/
│   └── groww-logo.svg
├── src/
│   ├── app/
│   │   ├── layout.tsx                          # Root layout (sidebar + header)
│   │   ├── page.tsx                            # Dashboard home
│   │   ├── globals.css                         # Tailwind base styles
│   │   ├── reviews/
│   │   │   └── page.tsx                        # Browse & filter all reviews
│   │   ├── weekly-pulse/
│   │   │   └── page.tsx                        # Generate, view & email weekly notes
│   │   ├── pipeline/
│   │   │   └── page.tsx                        # Full pipeline control center (wizard)
│   │   ├── settings/
│   │   │   └── page.tsx                        # Configure email, API keys
│   │   └── api/
│   │       ├── reviews/
│   │       │   ├── fetch/route.ts              # POST — trigger scraping
│   │       │   └── route.ts                    # GET  — return stored reviews
│   │       ├── themes/
│   │       │   ├── generate/route.ts           # POST — run theme discovery
│   │       │   ├── classify/route.ts           # POST — classify reviews into themes
│   │       │   └── route.ts                    # GET  — return themes + grouped reviews
│   │       ├── weekly-note/
│   │       │   ├── generate/route.ts           # POST — generate weekly note
│   │       │   ├── latest/route.ts             # GET  — most recent note
│   │       │   └── [weekId]/route.ts           # GET  — specific week's note
│   │       └── email/
│   │           ├── draft/route.ts              # POST — generate email HTML preview
│   │           └── send/route.ts               # POST — send email
│   ├── components/
│   │   ├── ui/                                 # Shadcn/UI primitives (button, card, etc.)
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx
│   │   │   └── Header.tsx
│   │   ├── pipeline/
│   │   │   ├── PipelineStepper.tsx             # Step-by-step wizard for entire pipeline
│   │   │   ├── StepFetchReviews.tsx            # Step 1 UI — scrape config & trigger
│   │   │   ├── StepGenerateThemes.tsx          # Step 2 UI — theme discovery trigger
│   │   │   ├── StepClassifyReviews.tsx         # Step 3 UI — classification trigger
│   │   │   ├── StepGenerateNote.tsx            # Step 4 UI — weekly note generation
│   │   │   ├── StepEmailPreview.tsx            # Step 5 UI — preview & send email
│   │   │   └── PipelineStatusBar.tsx           # Live progress indicator
│   │   └── dashboard/
│   │       ├── RatingDistributionChart.tsx
│   │       ├── ThemeCard.tsx
│   │       ├── QuoteCard.tsx
│   │       ├── ActionIdeaCard.tsx
│   │       ├── WeeklyPulsePreview.tsx
│   │       ├── EmailPreviewModal.tsx
│   │       └── OnePagerView.tsx                # Rendered one-page note (print-ready)
│   ├── hooks/
│   │   ├── usePipeline.ts                      # Pipeline state machine hook
│   │   ├── useReviews.ts                       # Fetch & filter reviews
│   │   ├── useThemes.ts                        # Theme data hook
│   │   ├── useWeeklyNote.ts                    # Weekly note data hook
│   │   └── useEmail.ts                         # Email draft & send hook
│   ├── lib/
│   │   ├── scrapers/
│   │   │   ├── playStoreScraper.ts             # Google Play Store review fetcher
│   │   │   ├── appStoreScraper.ts              # Apple App Store review fetcher
│   │   │   └── reviewNormalizer.ts             # Unify both sources into common schema
│   │   ├── llm/
│   │   │   ├── groqClient.ts                   # Groq SDK initialization & helpers
│   │   │   ├── themeGenerator.ts               # Step 1: Discover 3–5 themes
│   │   │   ├── reviewClassifier.ts             # Step 2: Classify reviews into themes
│   │   │   └── weeklyNoteGenerator.ts          # Step 3: Generate weekly pulse note
│   │   ├── email/
│   │   │   ├── emailComposer.ts                # Build HTML email from WeeklyNote
│   │   │   └── emailSender.ts                  # SMTP / Resend send logic
│   │   └── utils/
│   │       ├── piiScrubber.ts                  # Remove emails, phones, names from text
│   │       ├── dateHelpers.ts                  # Week range calculations
│   │       └── constants.ts                    # App IDs, config constants
│   ├── types/
│   │   ├── review.ts                           # Review interfaces
│   │   ├── theme.ts                            # Theme interfaces
│   │   ├── weeklyNote.ts                       # Weekly note interfaces
│   │   ├── email.ts                            # Email interfaces
│   │   └── pipeline.ts                         # Pipeline state & step interfaces
│   └── data/                                   # File-based storage (MVP)
│       ├── reviews.json
│       ├── themes.json
│       └── weekly-notes/
│           └── 2026-W11.json
├── .env.local                                  # Environment variables (never commit)
├── .env.example                                # Template for env vars
├── .gitignore
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── next.config.js
├── postcss.config.js
├── ARCHITECTURE.md                             # This file
└── README.md
```

---

## Phase 1: Review Ingestion & PII Scrubbing

### 1.1 Objective

Import reviews from the last **8–12 weeks** for GROWW from both Google Play Store and Apple App Store, normalize them into a unified schema, scrub PII, and store locally.

> **Note:** The `google-play-scraper` and `app-store-scraper` npm packages have practical limits of ~200 reviews per source per fetch. The implementation caps at **200 reviews per source** (up to ~400 total from both stores combined). This is sufficient for weekly pulse generation.

### 1.2 Data Models

```typescript
// src/types/review.ts

type ReviewSource = "play_store" | "app_store";

interface RawPlayStoreReview {
  id: string;
  userName: string;
  score: number;
  title: string | null;
  text: string;
  date: string;
  version: string | null;
  thumbsUp: number;
  replyDate: string | null;
  replyText: string | null;
}

interface RawAppStoreReview {
  id: string;
  userName: string;
  score: number;
  title: string;
  text: string;
  date: string;
  version: string | null;
}

interface Review {
  id: string;
  source: ReviewSource;
  rating: number;            // 1–5
  title: string | null;
  text: string;              // Original text
  scrubbedText: string;      // PII-removed version (used for LLM)
  date: string;              // ISO 8601 date
  version: string | null;
  weekLabel: string;         // e.g. "2026-W11"
}
```

### 1.3 Play Store Scraper (`playStoreScraper.ts`)

```typescript
import gplay from "google-play-scraper";

const PLAY_STORE_APP_ID = "com.nextbillion.groww";

const fetchPlayStoreReviews = async (weeks: number = 12): Promise<RawPlayStoreReview[]> => {
  const cutoffDate = new Date();
  cutoffDate.setDate(cutoffDate.getDate() - weeks * 7);

  let allReviews: RawPlayStoreReview[] = [];
  let nextToken: string | undefined;

  do {
    const result = await gplay.reviews({
      appId: PLAY_STORE_APP_ID,
      sort: gplay.sort.NEWEST,
      num: 150,
      paginate: true,
      nextPaginationToken: nextToken,
    });

    const reviews = result.data;
    nextToken = result.nextPaginationToken;

    const filtered = reviews.filter(
      (r) => new Date(r.date) >= cutoffDate
    );
    allReviews = [...allReviews, ...filtered];

    // Stop if we've gone past the cutoff date
    if (filtered.length < reviews.length) break;
  } while (nextToken);

  return allReviews;
};
```

### 1.4 App Store Scraper (`appStoreScraper.ts`)

```typescript
import store from "app-store-scraper";

const APP_STORE_ID = 1404871703; // GROWW App Store ID

const fetchAppStoreReviews = async (weeks: number = 12): Promise<RawAppStoreReview[]> => {
  const cutoffDate = new Date();
  cutoffDate.setDate(cutoffDate.getDate() - weeks * 7);

  let allReviews: RawAppStoreReview[] = [];

  // App Store scraper paginates by page (1–10)
  for (let page = 1; page <= 10; page++) {
    const reviews = await store.reviews({
      id: APP_STORE_ID,
      sort: store.sort.RECENT,
      page,
      country: "in",
    });

    if (reviews.length === 0) break;

    const filtered = reviews.filter(
      (r: RawAppStoreReview) => new Date(r.date) >= cutoffDate
    );
    allReviews = [...allReviews, ...filtered];

    if (filtered.length < reviews.length) break;
  }

  return allReviews;
};
```

### 1.5 Review Normalizer (`reviewNormalizer.ts`)

```typescript
const normalizeReviews = (
  playStoreReviews: RawPlayStoreReview[],
  appStoreReviews: RawAppStoreReview[]
): Review[] => {
  const normalized: Review[] = [];

  for (const r of playStoreReviews) {
    normalized.push({
      id: `ps_${r.id}`,
      source: "play_store",
      rating: r.score,
      title: r.title,
      text: r.text,
      scrubbedText: scrubPII(r.text),
      date: new Date(r.date).toISOString(),
      version: r.version,
      weekLabel: getWeekLabel(new Date(r.date)),
    });
  }

  for (const r of appStoreReviews) {
    normalized.push({
      id: `as_${r.id}`,
      source: "app_store",
      rating: r.score,
      title: r.title,
      text: r.text,
      scrubbedText: scrubPII(r.text),
      date: new Date(r.date).toISOString(),
      version: r.version,
      weekLabel: getWeekLabel(new Date(r.date)),
    });
  }

  return normalized.sort(
    (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()
  );
};
```

### 1.6 PII Scrubber (`piiScrubber.ts`)

```typescript
const PII_PATTERNS = [
  // Email addresses
  { pattern: /\b[\w.-]+@[\w.-]+\.\w{2,}\b/gi, replacement: "[EMAIL]" },
  // Phone numbers (Indian + international)
  { pattern: /(\+?\d{1,3}[-.\s]?)?\(?\d{3,5}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}/g, replacement: "[PHONE]" },
  // Aadhaar-like numbers (12 digits)
  { pattern: /\b\d{4}\s?\d{4}\s?\d{4}\b/g, replacement: "[ID_NUMBER]" },
  // PAN card numbers
  { pattern: /\b[A-Z]{5}\d{4}[A-Z]\b/g, replacement: "[PAN]" },
  // UPI IDs
  { pattern: /\b[\w.-]+@[\w]+\b/gi, replacement: "[UPI_ID]" },
];

const scrubPII = (text: string): string => {
  let scrubbed = text;
  for (const { pattern, replacement } of PII_PATTERNS) {
    scrubbed = scrubbed.replace(pattern, replacement);
  }
  return scrubbed;
};
```

### 1.7 API Routes

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/reviews/fetch` | Trigger scraping from both stores. Query param `?weeks=12`. Returns `{ count, sources }`. |
| `GET` | `/api/reviews` | Return stored reviews. Query params: `?source=`, `?minRating=`, `?maxRating=`, `?weekLabel=`. |

### 1.8 Storage

For MVP, reviews are persisted to `src/data/reviews.json`:

```json
{
  "lastFetched": "2026-03-13T10:00:00Z",
  "totalCount": 842,
  "reviews": [ /* Review[] */ ]
}
```

---

## Phase 2: Theme Discovery & Review Classification (LLM)

### 2.1 Objective

Use Groq LLM in a **two-step process**: first discover 3–5 themes from a representative sample, then classify every review into one of those themes.

### 2.2 Data Models

```typescript
// src/types/theme.ts

interface Theme {
  id: string;                // e.g. "app_crashes"
  name: string;              // e.g. "App Crashes & Freezes"
  description: string;       // Brief description of what this theme covers
  reviewCount: number;       // Number of reviews in this theme
  averageRating: number;     // Average rating of reviews in this theme
  sentiment: {
    positive: number;
    negative: number;
    neutral: number;
  };
}

interface ClassifiedReview {
  reviewId: string;
  themeId: string;
  confidence: number;        // 0–1 confidence score from LLM
}

interface ThemeResult {
  generatedAt: string;
  themes: Theme[];
  classifications: ClassifiedReview[];
}
```

### 2.3 Groq Client (`groqClient.ts`)

```typescript
import Groq from "groq-sdk";

const groqClient = new Groq({
  apiKey: process.env.GROQ_API_KEY!,
});

const MODEL_HIGH_QUALITY = "llama-3.3-70b-versatile";    // Theme discovery, weekly note
const MODEL_FAST = "llama-3.1-8b-instant";               // Batch classification

interface LLMRequest {
  systemPrompt: string;
  userPrompt: string;
  model?: string;
  temperature?: number;
  maxTokens?: number;
  jsonMode?: boolean;
}

const callGroq = async (request: LLMRequest): Promise<string> => {
  const completion = await groqClient.chat.completions.create({
    model: request.model ?? MODEL_HIGH_QUALITY,
    messages: [
      { role: "system", content: request.systemPrompt },
      { role: "user", content: request.userPrompt },
    ],
    temperature: request.temperature ?? 0.3,
    max_tokens: request.maxTokens ?? 4096,
    response_format: request.jsonMode ? { type: "json_object" } : undefined,
  });

  return completion.choices[0]?.message?.content ?? "";
};
```

### 2.4 Step 1 — Theme Discovery (`themeGenerator.ts`)

**Strategy:** Sample ~80 reviews (stratified by rating) so the LLM sees the full spectrum of feedback.

```typescript
const THEME_DISCOVERY_SYSTEM_PROMPT = `
You are an expert product analyst specializing in fintech apps.
You will analyze user reviews for GROWW, a popular Indian stock trading
and mutual fund investment app.

Your task: Identify exactly 3 to 5 recurring themes from the reviews.
Themes should be specific and actionable (not generic like "good app" or "bad app").

RULES:
- Each theme must have a short id (snake_case), a human-readable name, and a description
- Themes should cover the majority of reviews
- Focus on product-relevant themes (UX issues, feature requests, bugs, praise areas)
- Return valid JSON only
`;

const THEME_DISCOVERY_USER_PROMPT = (reviews: string) => `
Analyze these ${reviews.split("\n").length} user reviews and identify 3–5 recurring themes.

Reviews:
${reviews}

Return JSON in this exact format:
{
  "themes": [
    {
      "id": "snake_case_id",
      "name": "Human Readable Name",
      "description": "What this theme covers"
    }
  ]
}
`;
```

**Sampling strategy:**

```typescript
const sampleReviews = (reviews: Review[], sampleSize: number = 80): Review[] => {
  const byRating: Record<number, Review[]> = { 1: [], 2: [], 3: [], 4: [], 5: [] };

  for (const r of reviews) {
    byRating[r.rating]?.push(r);
  }

  const perBucket = Math.ceil(sampleSize / 5);
  const sampled: Review[] = [];

  for (let rating = 1; rating <= 5; rating++) {
    const bucket = byRating[rating];
    const shuffled = bucket.sort(() => Math.random() - 0.5);
    sampled.push(...shuffled.slice(0, perBucket));
  }

  return sampled;
};
```

### 2.5 Step 2 — Review Classification (`reviewClassifier.ts`)

**Strategy:** Batch reviews in groups of 25 to stay within Groq token limits. Use the faster model for classification.

```typescript
const CLASSIFICATION_SYSTEM_PROMPT = `
You are a review classifier for GROWW app reviews.
You will be given a set of themes and a batch of reviews.
Classify each review into exactly ONE theme.

RULES:
- Every review MUST be assigned to a theme
- If a review could fit multiple themes, pick the most dominant one
- Return valid JSON only
`;

const CLASSIFICATION_USER_PROMPT = (
  themes: Theme[],
  reviewBatch: Review[]
) => `
THEMES:
${themes.map((t) => `- ${t.id}: ${t.name} — ${t.description}`).join("\n")}

REVIEWS:
${reviewBatch.map((r) => `[${r.id}] (${r.rating}★) ${r.scrubbedText}`).join("\n")}

Classify each review. Return JSON:
{
  "classifications": [
    { "reviewId": "review_id_here", "themeId": "theme_id_here", "confidence": 0.95 }
  ]
}
`;
```

**Batching logic:**

```typescript
const BATCH_SIZE = 25;

const classifyAllReviews = async (
  themes: Theme[],
  reviews: Review[]
): Promise<ClassifiedReview[]> => {
  const allClassifications: ClassifiedReview[] = [];

  for (let i = 0; i < reviews.length; i += BATCH_SIZE) {
    const batch = reviews.slice(i, i + BATCH_SIZE);
    const result = await callGroq({
      systemPrompt: CLASSIFICATION_SYSTEM_PROMPT,
      userPrompt: CLASSIFICATION_USER_PROMPT(themes, batch),
      model: MODEL_FAST,
      jsonMode: true,
    });

    const parsed = JSON.parse(result);
    allClassifications.push(...parsed.classifications);
  }

  return allClassifications;
};
```

### 2.6 API Routes

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/themes/generate` | Run theme discovery on sampled reviews. Returns `Theme[]`. |
| `POST` | `/api/themes/classify` | Classify all reviews into discovered themes. Returns `ClassifiedReview[]`. |
| `GET` | `/api/themes` | Return themes with grouped review counts and sentiment. |

### 2.7 Token Budget Estimation

| Step | Model | Input Tokens | Output Tokens | Requests |
|------|-------|-------------|--------------|----------|
| Theme Discovery | `llama-3.3-70b` | ~8,000 (80 reviews) | ~500 | 1 |
| Classification | `llama-3.1-8b` | ~2,500 per batch | ~400 | ~34 (for 850 reviews) |
| **Total** | — | **~93,000** | **~14,100** | **~35** |

Groq free tier allows **14,400 requests/day** and **6,000 tokens/minute** — well within limits.

---

## Phase 3: Weekly Note Generation (Gemini LLM)

> **LLM:** Google Gemini (`gemini-2.5-flash`) — generous free-tier token limits,
> single-request generation without batching.

### 3.1 Objective

Generate a one-page weekly pulse note (under 400 words) with: top 3 themes, 3 verbatim
user quotes, and 3 actionable ideas. Output as Markdown (`.md`) and plain-text (`.txt`).

### 3.2 Data Models

```typescript
// src/types/weeklyNote.ts

interface WeeklyNote {
  id: string;                // e.g. "2026-W11"
  weekStarting: string;      // ISO date
  weekEnding: string;        // ISO date
  totalReviews: number;
  averageRating: number;
  ratingDistribution: Record<number, number>;  // { 1: 23, 2: 45, ... }
  themes: ThemeSummary[];
  quotes: UserQuote[];
  actionIdeas: ActionIdea[];
  generatedAt: string;
}

interface ThemeSummary {
  rank: number;
  name: string;
  reviewCount: number;
  percentageOfTotal: number;
  sentimentBreakdown: {
    positive: number;
    negative: number;
    neutral: number;
  };
  summary: string;          // 1–2 sentence summary
}

interface UserQuote {
  text: string;              // PII-scrubbed, verbatim
  rating: number;
  source: ReviewSource;
  theme: string;
  date: string;
}

interface ActionIdea {
  title: string;
  description: string;      // 1–2 sentences
  relatedTheme: string;
  priority: "high" | "medium" | "low";
  estimatedImpact: string;  // e.g. "Could reduce 1-star reviews by ~15%"
}
```

### 3.3 Data Aggregator (`weeklyDataAggregator.ts`)

Before calling the LLM, aggregate the raw data for the target week:

```typescript
interface WeeklyAggregation {
  weekLabel: string;
  weekStart: Date;
  weekEnd: Date;
  reviews: Review[];
  totalCount: number;
  averageRating: number;
  ratingDistribution: Record<number, number>;
  themeBreakdown: {
    theme: Theme;
    reviews: Review[];
    avgRating: number;
  }[];
}

const aggregateWeeklyData = (
  allReviews: Review[],
  themes: Theme[],
  classifications: ClassifiedReview[],
  weekLabel: string
): WeeklyAggregation => {
  const weekReviews = allReviews.filter((r) => r.weekLabel === weekLabel);

  // Build rating distribution
  const ratingDist: Record<number, number> = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 };
  for (const r of weekReviews) ratingDist[r.rating]++;

  const avgRating =
    weekReviews.reduce((sum, r) => sum + r.rating, 0) / weekReviews.length;

  // Group by theme
  const classMap = new Map(classifications.map((c) => [c.reviewId, c.themeId]));
  const themeBreakdown = themes.map((theme) => {
    const themeReviews = weekReviews.filter(
      (r) => classMap.get(r.id) === theme.id
    );
    return {
      theme,
      reviews: themeReviews,
      avgRating:
        themeReviews.reduce((s, r) => s + r.rating, 0) /
        (themeReviews.length || 1),
    };
  });

  return {
    weekLabel,
    weekStart: getWeekStart(weekLabel),
    weekEnd: getWeekEnd(weekLabel),
    reviews: weekReviews,
    totalCount: weekReviews.length,
    averageRating: avgRating,
    ratingDistribution: ratingDist,
    themeBreakdown: themeBreakdown.sort(
      (a, b) => b.reviews.length - a.reviews.length
    ),
  };
};
```

### 3.4 Weekly Note LLM Prompt (Gemini — `note_generator.py`)

```typescript
const WEEKLY_NOTE_SYSTEM_PROMPT = `
You are a senior product strategist at GROWW, an Indian fintech app for stock
trading and mutual fund investments.

You generate concise weekly pulse notes from app review data.

RULES:
- Pick the TOP 3 themes by review volume
- Select 3 real, verbatim user quotes that are most representative
  (one positive, one critical, one insightful) — NEVER fabricate quotes
- Generate 3 specific, actionable ideas tied to the themes
- Assign priority (high/medium/low) based on review volume and sentiment
- Keep everything concise — this is a ONE-PAGE note
- NEVER include any PII — all text has been pre-scrubbed
- Return valid JSON only
`;

const WEEKLY_NOTE_USER_PROMPT = (agg: WeeklyAggregation) => `
WEEK: ${agg.weekLabel} (${agg.weekStart.toLocaleDateString()} – ${agg.weekEnd.toLocaleDateString()})
TOTAL REVIEWS: ${agg.totalCount}
AVERAGE RATING: ${agg.averageRating.toFixed(2)} / 5
RATING DISTRIBUTION: ${JSON.stringify(agg.ratingDistribution)}

THEME BREAKDOWN:
${agg.themeBreakdown
  .map(
    (tb) =>
      `## ${tb.theme.name} (${tb.reviews.length} reviews, avg ${tb.avgRating.toFixed(1)}★)
Sample reviews:
${tb.reviews
  .slice(0, 10)
  .map((r) => `- (${r.rating}★) "${r.scrubbedText}"`)
  .join("\n")}`
  )
  .join("\n\n")}

Generate the weekly pulse note. Return JSON:
{
  "themes": [
    {
      "rank": 1,
      "name": "Theme Name",
      "reviewCount": 42,
      "percentageOfTotal": 35.5,
      "sentimentBreakdown": { "positive": 10, "negative": 28, "neutral": 4 },
      "summary": "One-line summary of this theme's sentiment."
    }
  ],
  "quotes": [
    {
      "text": "Exact verbatim quote from reviews above",
      "rating": 4,
      "source": "play_store",
      "theme": "Theme Name",
      "date": "2026-03-10"
    }
  ],
  "actionIdeas": [
    {
      "title": "Short Action Title",
      "description": "1-2 sentence description of what to do.",
      "relatedTheme": "Theme Name",
      "priority": "high",
      "estimatedImpact": "Could reduce 1★ reviews by ~15%"
    }
  ]
}
`;
```

### 3.5 API Routes

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/weekly-note/generate?report_date=YYYY-MM-DD` | Generate pulse note for a given date (default: today). |
| `GET` | `/api/weekly-note/latest` | Return the most recently generated pulse note. |
| `GET` | `/api/weekly-note/list` | List all generated pulse note dates. |
| `GET` | `/api/weekly-note/{report_date}` | Return a specific pulse note by date. |

### 3.6 Output & Storage

Each generation produces three files in `data/weekly-notes/`:
- `pulse-YYYY-MM-DD.md` — Markdown version (for rendering / sharing)
- `pulse-YYYY-MM-DD.txt` — Plain-text version (for email body)
- `pulse-YYYY-MM-DD.json` — Structured metadata (for API retrieval)

### 3.7 LLM Prompt Design

- **Role:** "You are a product communications writer at GROWW."
- **Task:** Write a concise Weekly Review Pulse note from themed review data.
- **Sections:** Top Themes (top 3), Real User Quotes (3 verbatim), Action Ideas (3 actionable).
- **Rules:** Under 400 words; no PII (names → `[User]`); quotes must be verbatim; Markdown output.
- **Model:** `gemini-2.5-flash` via `GEMINI_API_KEY`.

---

## Phase 4: Email Delivery

### 4.1 Objective

Produce a draft email (and optionally send it) containing the weekly pulse note.
Dry-run by default (saves `.eml` file); send mode via SMTP when credentials are present.

### 4.2 Data Models

```typescript
// src/types/email.ts

interface EmailDraft {
  to: string;
  subject: string;
  htmlBody: string;
  plainTextBody: string;
  generatedAt: string;
  weeklyNoteId: string;
}
```

### 4.3 Email Template (`emailComposer.ts`)

The email follows this visual structure:

```
┌─────────────────────────────────────────────────────────┐
│  GROWW WEEKLY APP REVIEW PULSE                          │
│  Week of Mar 3 – Mar 9, 2026                           │
│  156 reviews  |  Avg ★ 3.7                              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  📊 RATING SNAPSHOT                                     │
│  ★★★★★  ████████████  42 (27%)                         │
│  ★★★★   ████████      31 (20%)                         │
│  ★★★    ██████        25 (16%)                         │
│  ★★     ████████████  38 (24%)                         │
│  ★      ████          20 (13%)                         │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  🔥 TOP THEMES                                          │
│                                                         │
│  1. App Crashes & Performance (52 reviews)              │
│     "App freezes during market hours, losing trades"    │
│     Sentiment: 🔴 85% negative                         │
│                                                         │
│  2. UX & Navigation Issues (38 reviews)                 │
│     "Hard to find portfolio summary after update"       │
│     Sentiment: 🟡 60% negative                         │
│                                                         │
│  3. Great Investment Experience (31 reviews)            │
│     "Best app for SIP and mutual funds in India"        │
│     Sentiment: 🟢 90% positive                         │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  💬 USER VOICES                                         │
│                                                         │
│  "Crashes every morning at 9:15 when market opens.      │
│   Lost a trade because of this."  — ★★ Play Store      │
│                                                         │
│  "Love how easy it is to start SIPs. Best fintech      │
│   app in India hands down."  — ★★★★★ App Store         │
│                                                         │
│  "After the last update, the portfolio page takes       │
│   10 seconds to load."  — ★★★ Play Store               │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  💡 ACTION IDEAS                                        │
│                                                         │
│  🔴 [HIGH] Stress-test trading engine for market open   │
│     → Related: App Crashes & Performance                │
│     → Impact: Could reduce 1★ reviews by ~20%          │
│                                                         │
│  🟡 [MED] Audit navigation flow post-recent update      │
│     → Related: UX & Navigation Issues                   │
│     → Impact: Improve retention for power users         │
│                                                         │
│  🟡 [MED] Add "portfolio summary" widget to home screen │
│     → Related: UX & Navigation Issues                   │
│     → Impact: Most-requested feature in 3★ reviews     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 4.4 Email Sending (`emailSender.ts`)

**Option A — Nodemailer (SMTP/Gmail):**

```typescript
import nodemailer from "nodemailer";

const transporter = nodemailer.createTransport({
  host: process.env.SMTP_HOST,         // smtp.gmail.com
  port: Number(process.env.SMTP_PORT), // 587
  secure: false,
  auth: {
    user: process.env.SMTP_USER,
    pass: process.env.SMTP_PASS,       // Gmail App Password
  },
});

const sendEmail = async (draft: EmailDraft): Promise<void> => {
  await transporter.sendMail({
    from: `"GROWW Review Pulse" <${process.env.SMTP_USER}>`,
    to: draft.to,
    subject: draft.subject,
    html: draft.htmlBody,
    text: draft.plainTextBody,
  });
};
```

**Option B — Resend API:**

```typescript
import { Resend } from "resend";

const resend = new Resend(process.env.RESEND_API_KEY);

const sendEmail = async (draft: EmailDraft): Promise<void> => {
  await resend.emails.send({
    from: "GROWW Pulse <pulse@yourdomain.com>",
    to: [draft.to],
    subject: draft.subject,
    html: draft.htmlBody,
  });
};
```

### 4.5 Email Subject Line Format

```
📊 GROWW Weekly Pulse — Week of Mar 3, 2026 | ★ 3.7 avg | 156 reviews
```

### 4.6 API Routes (Python / FastAPI)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/email/draft` | Dry-run: compose email and save as `.eml`. Body: `{ report_date?, recipient?, recipient_name? }`. |
| `POST` | `/api/email/send` | Compose and optionally send. Body: `{ report_date?, recipient?, recipient_name?, send: true }`. |

### 4.7 Config (`.env`)

| Variable | Purpose |
|----------|---------|
| `EMAIL_SENDER` | From address (e.g. Gmail) |
| `EMAIL_PASSWORD` | Gmail App Password — never logged or stored beyond env |
| `SMTP_HOST` | SMTP server (default: `smtp.gmail.com`) |
| `SMTP_PORT` | SMTP port (default: `587`) |
| `EMAIL_RECIPIENT` | Fallback To address when not supplied by caller |

### 4.8 Output

- `data/weekly-notes/pulse-YYYY-MM-DD.eml` — RFC 2822 email file (openable in any email client)
- Body is **multipart/alternative**: plain-text + HTML
- HTML is Markdown → HTML via the `markdown` library, wrapped in a styled template
- Personalised greeting `"Hi {name},"` when `recipient_name` is provided

---

## Phase 5: Dashboard UI & Pipeline Control Center

> **This is NOT a bonus phase.** The UI is the primary interface for triggering every step — scraping, theme generation, weekly note creation, email preview, and sending. No CLI or manual API calls needed.

### 5.1 Pages

| Route | Component | Description |
|-------|-----------|-------------|
| `/` | `DashboardPage` | Overview: total reviews, avg rating trend, latest themes, **one-click "Generate This Week's Pulse" button** |
| `/pipeline` | `PipelinePage` | **Full pipeline wizard** — step-by-step control to run each phase from UI |
| `/reviews` | `ReviewsPage` | Browse, filter, search all scraped reviews |
| `/weekly-pulse` | `WeeklyPulsePage` | View past notes, **render one-pager**, preview email, **send email** |
| `/settings` | `SettingsPage` | Configure Groq API key, email recipient, SMTP/Resend settings |

### 5.2 Pipeline Control Center (`/pipeline`)

This is the **heart of the UI** — a guided, step-by-step wizard that lets users run the entire pipeline from the browser.

#### 5.2.1 Pipeline State Machine

```typescript
// src/types/pipeline.ts

type PipelineStepId =
  | "fetch_reviews"
  | "generate_themes"
  | "classify_reviews"
  | "generate_note"
  | "preview_email"
  | "send_email";

type StepStatus = "idle" | "running" | "success" | "error";

interface PipelineStep {
  id: PipelineStepId;
  label: string;
  description: string;
  status: StepStatus;
  result: unknown | null;       // Step-specific output data
  error: string | null;
  startedAt: string | null;
  completedAt: string | null;
}

interface PipelineState {
  currentStep: number;           // 0-indexed, which step is active
  steps: PipelineStep[];
  isRunning: boolean;
  canProceed: boolean;           // True if current step succeeded
}
```

#### 5.2.2 Pipeline Steps — UI Breakdown

```
┌─────────────────────────────────────────────────────────────────────────┐
│  PIPELINE CONTROL CENTER                                                │
│                                                                         │
│  ● Step 1        ○ Step 2        ○ Step 3       ○ Step 4      ○ Step 5  │
│  Fetch Reviews   Gen Themes      Classify       Gen Note      Email     │
│  ✅ Done         🔄 Running      ⏳ Waiting     ⏳ Waiting    ⏳ Waiting │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─── STEP 2: GENERATE THEMES ───────────────────────────────────────┐  │
│  │                                                                   │  │
│  │  Reviews loaded: 842 (Play Store: 612 | App Store: 230)          │  │
│  │  Date range: Jan 1, 2026 – Mar 13, 2026                         │  │
│  │                                                                   │  │
│  │  Sampling: 80 reviews (stratified by rating)                     │  │
│  │  Model: llama-3.3-70b-versatile                                  │  │
│  │                                                                   │  │
│  │  ┌──────────────────────────────────────────────────────────┐    │  │
│  │  │  🔄  Discovering themes...  (elapsed: 3.2s)              │    │  │
│  │  │  ████████████████░░░░░░░░  65%                           │    │  │
│  │  └──────────────────────────────────────────────────────────┘    │  │
│  │                                                                   │  │
│  │  [← Back]                                        [Next Step →]   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Each step panel contains:**

| Step | UI Elements | API Called | Output Displayed |
|------|------------|------------|-----------------|
| **1. Fetch Reviews** | Week range selector (8/10/12 weeks), source toggle (Play/App/Both), **"Fetch Reviews" button**, progress bar | `POST /api/reviews/fetch` | Review count, source breakdown, date range |
| **2. Generate Themes** | Sample size slider (40–120), model selector, **"Discover Themes" button**, loading spinner | `POST /api/themes/generate` | Theme cards with id, name, description |
| **3. Classify Reviews** | Batch size config, estimated time, **"Classify All" button**, batch progress (e.g. "Batch 12/34") | `POST /api/themes/classify` | Classification summary — count per theme, confidence stats |
| **4. Generate Note** | Week selector dropdown, **"Generate Weekly Pulse" button** | `POST /api/weekly-note/generate` | **Rendered one-pager** (inline preview) with themes, quotes, action ideas |
| **5. Email Preview & Send** | **Rendered email preview** (HTML iframe), recipient input (pre-filled from settings), **"Send Email" button**, success/failure toast | `POST /api/email/draft` then `POST /api/email/send` | Email preview + send confirmation |

#### 5.2.3 Pipeline Hook (`usePipeline.ts`)

```typescript
// src/hooks/usePipeline.ts

interface UsePipelineReturn {
  state: PipelineState;
  handleFetchReviews: (config: FetchConfig) => Promise<void>;
  handleGenerateThemes: () => Promise<void>;
  handleClassifyReviews: () => Promise<void>;
  handleGenerateNote: (weekLabel: string) => Promise<void>;
  handleDraftEmail: () => Promise<void>;
  handleSendEmail: (recipient: string) => Promise<void>;
  handleRunAll: () => Promise<void>;       // One-click full pipeline
  handleReset: () => void;
  goToStep: (step: number) => void;
}

const usePipeline = (): UsePipelineReturn => {
  const [state, setState] = useState<PipelineState>(initialPipelineState);

  const handleFetchReviews = async (config: FetchConfig) => {
    updateStepStatus("fetch_reviews", "running");
    try {
      const res = await fetch("/api/reviews/fetch", {
        method: "POST",
        body: JSON.stringify(config),
      });
      const data = await res.json();
      updateStepStatus("fetch_reviews", "success", data);
      advanceStep();
    } catch (err) {
      updateStepStatus("fetch_reviews", "error", null, err.message);
    }
  };

  // ... similar for each step

  const handleRunAll = async () => {
    // Sequentially execute all steps
    await handleFetchReviews(defaultConfig);
    await handleGenerateThemes();
    await handleClassifyReviews();
    await handleGenerateNote(getCurrentWeekLabel());
    await handleDraftEmail();
    // Pause at email send — user must confirm
  };

  return { state, handleFetchReviews, /* ... */ };
};
```

### 5.3 One-Pager View (`OnePagerView.tsx`)

A **print-ready, shareable one-page view** rendered directly in the browser. This is the same content that goes into the email, but displayed as a standalone page.

```
┌───────────────────────────────────────────────────────────────┐
│                                                               │
│  ┌──── GROWW WEEKLY APP REVIEW PULSE ──────────────────────┐  │
│  │  Week of Mar 3 – Mar 9, 2026                           │  │
│  │  156 reviews  |  Avg ★ 3.7  |  ▲ 0.2 vs last week     │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌──── RATING SNAPSHOT ─────────────────────────────────────┐ │
│  │  ★★★★★  ████████████  42 (27%)                          │ │
│  │  ★★★★   ████████      31 (20%)                          │ │
│  │  ★★★    ██████        25 (16%)                          │ │
│  │  ★★     ████████████  38 (24%)                          │ │
│  │  ★      ████          20 (13%)                          │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌──── TOP THEMES ──────────────────────────────────────────┐ │
│  │  1. App Crashes & Performance (52 reviews, 85% neg)     │ │
│  │  2. UX & Navigation Issues (38 reviews, 60% neg)        │ │
│  │  3. Great Investment Experience (31 reviews, 90% pos)    │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌──── USER VOICES ─────────────────────────────────────────┐ │
│  │  "Crashes every morning at 9:15..."   — ★★ Play Store   │ │
│  │  "Best app for SIP and mutual funds"  — ★★★★★ App Store │ │
│  │  "Portfolio page takes 10s to load"   — ★★★ Play Store  │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌──── ACTION IDEAS ────────────────────────────────────────┐ │
│  │  🔴 [HIGH] Stress-test trading engine for market open    │ │
│  │  🟡 [MED]  Audit navigation flow post-recent update      │ │
│  │  🟡 [MED]  Add portfolio summary widget to home screen   │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌────────────────────────────────────────────────────────── │ │
│  │  [📧 Email This]  [📄 Export PDF]  [📋 Copy to Clipboard]│ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

**Actions available on the one-pager:**

| Button | Behavior |
|--------|----------|
| **Email This** | Opens `EmailPreviewModal` with pre-composed email → confirm recipient → send |
| **Export PDF** | Uses browser `window.print()` with `@media print` styles for clean one-page PDF |
| **Copy to Clipboard** | Copies a plain-text version of the one-pager to clipboard |

### 5.4 Weekly Pulse Page (`/weekly-pulse`)

This page lets users **generate and manage weekly notes** without going through the full pipeline wizard (useful when reviews and themes are already up-to-date).

```
┌─────────────────────────────────────────────────────────────┐
│  WEEKLY PULSE NOTES                                          │
│                                                              │
│  ┌─── Generate New ──────────────────────────────────────┐  │
│  │  Week: [2026-W11 ▼]   [🔄 Generate Weekly Pulse]     │  │
│  │                                                        │  │
│  │  ⚠️  Reviews last fetched: 2 hours ago (842 reviews)  │  │
│  │  ⚠️  Themes last generated: 2 hours ago (4 themes)    │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─── Past Notes ────────────────────────────────────────┐  │
│  │                                                        │  │
│  │  📄 Week 11 (Mar 10–16)  ★ 3.8  156 reviews           │  │
│  │     [View One-Pager]  [📧 Email]  [📄 PDF]            │  │
│  │                                                        │  │
│  │  📄 Week 10 (Mar 3–9)   ★ 3.5  178 reviews            │  │
│  │     [View One-Pager]  [📧 Email]  [📄 PDF]            │  │
│  │                                                        │  │
│  │  📄 Week 9 (Feb 24–Mar 2) ★ 3.9  134 reviews          │  │
│  │     [View One-Pager]  [📧 Email]  [📄 PDF]            │  │
│  │                                                        │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 5.5 Email Flow from UI

The complete email flow triggered from the UI:

```
User clicks "Email This"
        │
        ▼
┌──────────────────────────┐
│  EmailPreviewModal opens │
│                          │
│  To: [user@email.com]    │  ← Pre-filled from settings
│                          │
│  Subject:                │
│  📊 GROWW Weekly Pulse   │
│  — Week of Mar 3, 2026  │
│                          │
│  ┌─── Email Preview ──┐ │
│  │  (rendered HTML     │ │  ← Live HTML iframe preview
│  │   of the one-pager) │ │
│  └─────────────────────┘ │
│                          │
│  [Cancel]  [✉️ Send Now] │  ← Calls POST /api/email/send
│                          │
└──────────────────────────┘
        │
        ▼ (on success)
┌──────────────────────────┐
│  ✅ Toast Notification   │
│  "Email sent to          │
│   user@email.com"        │
└──────────────────────────┘
```

### 5.6 Dashboard Home Page (`/`)

The dashboard provides a high-level overview and **quick-action buttons** so users don't have to navigate to subpages for common tasks.

```
┌─────────────────────────────────────────────────────────────┐
│  GROWW APP REVIEW PULSE                          [Settings]  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─── Quick Stats ──────────────────────────────────────┐   │
│  │  📦 842 Reviews   |  ★ 3.7 Avg  |  📊 4 Themes      │   │
│  │  Last fetched: 2h ago  |  Last pulse: Week 11        │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─── Quick Actions ────────────────────────────────────┐   │
│  │                                                       │   │
│  │  [🔄 Fetch Latest Reviews]                            │   │
│  │  [⚡ Generate This Week's Pulse]     ← runs full pipe │   │
│  │  [📧 Email Latest Pulse]             ← email last note│   │
│  │  [🛠️ Open Pipeline Wizard]                            │   │
│  │                                                       │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─── Latest Themes ───────┐  ┌─── Rating Trend ────────┐  │
│  │ 🔴 App Crashes (52)     │  │  ★ 3.7 ─ ★ 3.5 ─ ★ 3.9 │  │
│  │ 🟡 UX Issues (38)       │  │  W11      W10      W9   │  │
│  │ 🟢 Great UX (31)        │  │  [line chart]            │  │
│  │ 🟡 Feature Reqs (25)    │  │                          │  │
│  └──────────────────────────┘  └──────────────────────────┘  │
│                                                              │
│  ┌─── Latest Pulse Preview (Week 11) ───────────────────┐   │
│  │  (Compact inline preview of the one-pager)            │   │
│  │  [View Full]  [📧 Email]  [📄 PDF]                    │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 5.7 Key Components

| Component | Description |
|-----------|-------------|
| `PipelineStepper` | Horizontal stepper (Step 1 → 2 → 3 → 4 → 5) with status icons per step |
| `StepFetchReviews` | Week range selector, source toggle, fetch button, progress bar |
| `StepGenerateThemes` | Sample size config, trigger button, theme cards output |
| `StepClassifyReviews` | Batch progress bar (e.g. "Batch 12/34"), classification summary |
| `StepGenerateNote` | Week selector, trigger button, inline one-pager preview |
| `StepEmailPreview` | Email preview iframe, recipient input, send button |
| `PipelineStatusBar` | Compact status bar showing current step + elapsed time |
| `OnePagerView` | Full one-page rendered note, with Email / PDF / Copy actions |
| `EmailPreviewModal` | Modal overlay with email HTML preview + send controls |
| `RatingDistributionChart` | Horizontal bar chart (1–5★) using `recharts` |
| `ThemeCard` | Theme name, review count, sentiment bar, summary |
| `QuoteCard` | Styled user quote with rating stars and source badge |
| `ActionIdeaCard` | Priority badge (HIGH/MED/LOW), description, impact estimate |
| `WeeklyPulsePreview` | Compact card preview of a weekly note |

### 5.8 UI Design Principles

- **Dark sidebar** with navigation icons (Home, Pipeline, Reviews, Pulse, Settings)
- **Card-based layout** for the dashboard grid
- **Color coding**: Red for negative/high-priority, green for positive, yellow for neutral/medium
- **Rating stars** rendered as filled/empty star SVGs via `lucide-react`
- **Responsive**: Works on desktop and tablet (min-width: 768px)
- **Loading states**: Skeleton loaders for cards, shimmer for text, spinners for buttons
- **Toast notifications**: Success/error toasts for all async actions (use Shadcn `sonner`)
- **Accessibility**: All interactive elements have `aria-label`, `tabIndex`, keyboard navigation

---

## Environment Variables

```env
# ──────────────── Groq LLM ────────────────
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx

# ──────────────── App Store IDs ────────────────
PLAY_STORE_APP_ID=com.nextbillion.groww
APP_STORE_APP_ID=1404871703

# ──────────────── Email (Option A: SMTP) ────────────────
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-gmail-app-password
EMAIL_RECIPIENT=your-email@gmail.com

# ──────────────── Email (Option B: Resend) ────────────────
# RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxx

# ──────────────── App Config ────────────────
REVIEW_WEEKS=12
MAX_THEMES=5
BATCH_SIZE=25
```

---

## Security & Privacy Checklist

- [x] **PII scrubbing** runs BEFORE any data is sent to Groq
- [x] **Groq API key** stored in `.env.local`, never committed
- [x] **Email credentials** stored in `.env.local`, never committed
- [x] **`.gitignore`** includes `.env.local`, `src/data/`, `node_modules/`
- [x] **No user names** are stored in the normalized `Review` schema
- [x] **Scrubbed text** is used for all LLM calls and email content

---

## Execution Pipeline (End-to-End — UI-Driven)

All steps are triggered from the **Dashboard UI** via the Pipeline Wizard or quick-action buttons.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  DASHBOARD UI — Pipeline Wizard                                             │
│                                                                             │
│  Step 1         Step 2         Step 3        Step 4        Step 5           │
│  [Fetch]  ────▶ [Themes] ────▶ [Classify] ──▶ [Generate] ──▶ [Email]       │
│                                                                             │
└────┬────────────────┬──────────────┬────────────┬────────────┬──────────────┘
     │                │              │            │            │
     ▼                ▼              ▼            ▼            ▼
┌──────────┐   ┌──────────┐   ┌──────────┐ ┌──────────┐ ┌──────────────────┐
│ SCRAPE   │   │ DISCOVER │   │ CLASSIFY │ │ GENERATE │ │ COMPOSE & SEND   │
│ + CLEAN  │   │ Themes   │   │ Reviews  │ │ One-Page │ │                  │
│          │   │          │   │          │ │ Note     │ │ Preview in modal │
│ Fetch    │   │ Sample   │   │ Batch    │ │          │ │ → Confirm        │
│ reviews  │   │ → Groq   │   │ classify │ │ Aggregate│ │ → Send to self   │
│ 8–12 wks │   │ → 3–5    │   │ via Groq │ │ → Groq   │ │                  │
│ Scrub PII│   │ themes   │   │          │ │ → render │ │ Success toast ✅ │
└──────────┘   └──────────┘   └──────────┘ └──────────┘ └──────────────────┘

                          ── OR ──

┌─────────────────────────────────────────────────────────────────────────────┐
│  DASHBOARD HOME — One-Click                                                 │
│                                                                             │
│  [⚡ Generate This Week's Pulse]  → runs all 5 steps sequentially           │
│  [📧 Email Latest Pulse]          → opens email modal for last note         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Order & Estimates

| # | Phase | Key Deliverables | Effort |
|---|-------|-----------------|--------|
| 1 | **Project Setup** | Next.js scaffold, deps, TailwindCSS, Shadcn/UI, folder structure | ~1 hr |
| 2 | **Phase 1: Ingestion** | Scrapers, normalizer, PII scrubber, storage, API routes | ~3–4 hrs |
| 3 | **Phase 2: Themes** | Groq client, theme discovery, batch classification, API routes | ~3–4 hrs |
| 4 | **Phase 3: Weekly Note** | Data aggregator, note generator, storage, API routes | ~2–3 hrs |
| 5 | **Phase 4: Email** | Email composer (HTML template), sender, API routes | ~2–3 hrs |
| 6 | **Phase 5: Dashboard & Pipeline UI** | Layout, sidebar, dashboard page with quick actions | ~3–4 hrs |
| 7 | **Phase 5: Pipeline Wizard** | PipelineStepper, all 5 step components, usePipeline hook, status bar | ~4–5 hrs |
| 8 | **Phase 5: One-Pager & Email UI** | OnePagerView, EmailPreviewModal, PDF export, weekly pulse page | ~3–4 hrs |
| 9 | **Phase 5: Reviews Page** | Review list, filters, search, theme badges | ~2–3 hrs |
| 10 | **Phase 5: Settings Page** | API key config, email settings, scraping preferences | ~1–2 hrs |
| | **Total** | | **~22–32 hrs** |

---

## Dependencies (`package.json`)

```json
{
  "dependencies": {
    "next": "^14.2.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "groq-sdk": "^0.10.0",
    "google-play-scraper": "^9.1.0",
    "app-store-scraper": "^0.17.0",
    "nodemailer": "^6.9.0",
    "recharts": "^2.12.0",
    "lucide-react": "^0.400.0",
    "sonner": "^1.7.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.3.0",
    "class-variance-authority": "^0.7.0"
  },
  "devDependencies": {
    "typescript": "^5.4.0",
    "@types/node": "^20.12.0",
    "@types/react": "^18.3.0",
    "@types/nodemailer": "^6.4.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0"
  }
}
```

---

## Phase 6: Weekly Scheduler

> Automated weekly execution of the full pipeline — no manual intervention needed.

### 6.1 Objective

Run the complete pipeline (Fetch → Themes → Classify → Generate Note → Send Email) automatically every week at a fixed time, delivering the Weekly Review Pulse to a configured recipient without human intervention.

### 6.2 Implementation

| Component | Detail |
|-----------|--------|
| **File** | `scheduler.py` |
| **Library** | `schedule` (Python) |
| **Trigger** | Every **Monday at 12:35 PM IST** (configurable via CLI flags) |
| **Execution** | Invokes `cli.py run-all --recipient EMAIL --name NAME --weeks 8 --max-reviews 1000 --send` as a subprocess |
| **Reviews** | Last **8 weeks**, max **1,000 reviews** (hardcoded in scheduler constants) |
| **Recipient** | Fixed: `travelerjayesh@gmail.com` (hardcoded in scheduler) |
| **Timeout** | 30 minutes per pipeline run |
| **Logging** | Timestamped console logs with `[SCHEDULER]` prefix |

### 6.3 How It Works

```
scheduler.py starts
        │
        ▼
Schedule registered: every Monday at 12:35 IST
        │
        ▼ (at 12:35 IST on Monday)
subprocess.run("python cli.py run-all --recipient ... --weeks 8 --max-reviews 1000 --send")
        │
        ├── Phase 1: Fetch reviews from Play Store
        ├── Phase 2a: Discover themes (Groq)
        ├── Phase 2b: Classify reviews (Groq)
        ├── Phase 3: Generate weekly pulse note (Gemini)
        └── Phase 4: Send email via SMTP
        │
        ▼
Log result (success / failure)
Sleep until next Monday 12:35
```

### 6.4 CLI Usage

```bash
# Start the scheduler (runs in foreground, waits for Monday 12:35 IST)
python scheduler.py

# Run immediately once, then continue on schedule
python scheduler.py --run-now

# Change the day (default: monday)
python scheduler.py --day friday

# Change the time (default: 12:35)
python scheduler.py --time 09:00

# Combine flags
python scheduler.py --day wednesday --time 10:00 --run-now
```

### 6.5 Configuration

| Setting | Value | How to Change |
|---------|-------|---------------|
| Recipient email | `travelerjayesh@gmail.com` | Edit `RECIPIENT_EMAIL` in `scheduler.py` |
| Recipient name | `Jayesh` | Edit `RECIPIENT_NAME` in `scheduler.py` |
| Week range | 8 weeks | Edit `FETCH_WEEKS` in `scheduler.py` |
| Max reviews | 1,000 | Edit `MAX_REVIEWS` in `scheduler.py` |
| Day of week | Monday | `--day` CLI flag |
| Time (IST) | 12:35 | `--time` CLI flag |
| SMTP credentials | From `.env` | `EMAIL_SENDER`, `EMAIL_PASSWORD` |

### 6.6 Deployment Notes

- The scheduler runs as a **foreground process** — keep the terminal open, or use a process manager (`nohup`, `pm2`, `systemd`, Windows Task Scheduler).
- On Windows, you can also create a **Scheduled Task** that runs `python scheduler.py --run-now` weekly as an alternative to keeping the process alive.
- All pipeline logs (fetch counts, theme names, errors) are printed to stdout with timestamps.
- If any pipeline step fails, the scheduler logs the error and waits for the next scheduled run.

### 6.7 GitHub Actions Integration

The scheduler is also available as a **GitHub Actions workflow** (`.github/workflows/weekly-pulse.yml`) so the pipeline can run in the cloud with zero local infrastructure.

#### 6.7.1 How It Works

| Aspect | Detail |
|--------|--------|
| **File** | `.github/workflows/weekly-pulse.yml` |
| **Trigger** | `cron: "5 7 * * 1"` — every Monday at 07:05 AM UTC (12:35 PM IST) |
| **Manual trigger** | `workflow_dispatch` — run from GitHub UI with configurable `weeks` and `max_reviews` |
| **Runner** | `ubuntu-latest`, Python 3.13, pip cache enabled |
| **Timeout** | 30 minutes |
| **Command** | `python cli.py run-all --recipient travelerjayesh@gmail.com --name Jayesh --weeks 8 --max-reviews 1000 --send` |
| **Artifacts** | Pulse `.md`, `.txt`, `.json`, `.eml` files uploaded and retained for 30 days |

#### 6.7.2 Required GitHub Secrets

These must be set in **Settings → Secrets and variables → Actions** on the GitHub repository:

| Secret | Value |
|--------|-------|
| `GROQ_API_KEY` | Groq API key for theme discovery and classification |
| `GEMINI_API_KEY` | Google Gemini API key for weekly note generation |
| `EMAIL_SENDER` | Gmail address used as the sender |
| `EMAIL_PASSWORD` | Gmail App Password for SMTP |

#### 6.7.3 Manual Trigger

From the GitHub repository:

1. Go to **Actions** tab
2. Select **"Weekly Review Pulse"** workflow
3. Click **"Run workflow"**
4. Optionally change `weeks` (default: 8) and `max_reviews` (default: 1000)
5. Click **"Run workflow"** to start

The pipeline runs, sends the email, and uploads all generated files as downloadable artifacts.

#### 6.7.4 Workflow Flow

```
GitHub Actions cron (Monday 07:05 UTC / 12:35 PM IST)
        │
        ▼
Checkout repo → Setup Python 3.13 → pip install
        │
        ▼
python cli.py run-all --recipient ... --weeks 8 --max-reviews 1000 --send
        │
        ├── Phase 1: Fetch 1000 reviews (last 8 weeks)
        ├── Phase 2a: Discover themes (Groq)
        ├── Phase 2b: Classify reviews (Groq)
        ├── Phase 3: Generate pulse note (Gemini)
        └── Phase 4: Send email to travelerjayesh@gmail.com
        │
        ▼
Upload artifacts (pulse-*.md, .txt, .json, .eml) → retained 30 days
```

---

*Architecture document generated for GROWW App Review Analyser — March 2026*
