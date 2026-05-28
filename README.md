# PhamilyOps — Complete Deployment Guide
**Built by: Akilan Manivannan & Akila Lourdes Miriyala Francis**

AI-Native HR & Operations Platform for Phamily (Jaan Health)

---

## System Architecture

```
Browser (phamilyops.html)
        │
        │  REST / SSE streaming
        ▼
FastAPI Backend (Railway)
  ├── /screener    → HuggingFace NER + Claude scoring + bias audit
  ├── /copilot     → pgvector search + Claude streaming + RAGAS eval
  ├── /audit       → scoring algorithm + Claude roadmap
  ├── /automations → workflow engine + Claude design
  └── /analytics   → real Supabase queries
        │
        ├── Anthropic Claude API
        ├── HuggingFace (dslim/bert-base-NER + all-MiniLM-L6-v2)
        └── Supabase (PostgreSQL + pgvector)
```

---

## Step 1 — Supabase Setup (5 minutes)

1. Go to [supabase.com](https://supabase.com) → New Project
2. Open **SQL Editor**
3. Run `backend/database/schema.sql` — creates all tables + RLS + seeds HR policy data
4. Run `backend/database/pgvector_function.sql` — creates semantic search function
5. Go to **Settings → API** → copy:
   - `Project URL` → your `SUPABASE_URL`
   - `service_role` key → your `SUPABASE_SERVICE_KEY`

---

## Step 2 — Railway Backend Deploy (5 minutes)

1. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
2. Push the `backend/` folder to a GitHub repo
3. Railway auto-detects FastAPI from `Procfile`
4. Set environment variables in Railway dashboard:
   ```
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_SERVICE_KEY=your-service-role-key
   FRONTEND_URL=*
   ENVIRONMENT=production
   ```
5. Railway gives you: `https://phamilyops-backend.railway.app`

---

## Step 3 — Embed HR Policy Documents (one-time, 30 seconds)

After backend is live, call this once to generate semantic embeddings:

```bash
curl -X POST https://your-app.railway.app/copilot/embed-documents \
  -H "Content-Type: application/json" \
  -d '{"confirm": true}'
```

This runs `all-MiniLM-L6-v2` on all HR policy documents and stores 384-dim vectors in pgvector.

---

## Step 4 — Connect Frontend

Open `frontend/phamilyops.html` and update line 1 of the API script:

```js
const API_BASE = 'https://your-app.railway.app';
```

Open the file in any browser — all 6 modules now call the live backend.

---

## Step 5 — Verify Everything Works

```bash
# Health check
curl https://your-app.railway.app/health

# Expected:
# {"status":"healthy","database":"connected","environment":"production"}

# Test screener
curl -X POST https://your-app.railway.app/screener/screen \
  -H "Content-Type: application/json" \
  -d '{"resume_text":"Python, PyTorch, Claude API...","candidate_name":"Test Candidate","role":"HR, AI Automation Intern"}'

# Test copilot
curl -X POST https://your-app.railway.app/copilot/chat/sync \
  -H "Content-Type: application/json" \
  -d '{"message":"What is Phamily PTO policy?"}'
```

---

## API Endpoints — Complete Reference

### Screener
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/screener/screen` | Screen a candidate — NLP + Claude + bias audit |
| GET | `/screener/candidates` | All candidates from Supabase |
| PATCH | `/screener/candidates/{id}/status` | Update status, trigger automation |

### HR Copilot
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/copilot/chat` | Streaming chat (SSE) |
| POST | `/copilot/chat/sync` | Non-streaming chat |
| POST | `/copilot/embed-documents` | Run embeddings on policy docs |
| GET | `/copilot/quality-metrics` | Live RAGAS scores |

### Audit
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/audit/analyze` | Score processes + Claude roadmap |
| GET | `/audit/history` | Past audits from Supabase |

### Automations
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/automations/trigger` | Trigger onboarding/scheduling/travel/routing |
| POST | `/automations/design` | Claude designs a custom workflow |
| GET | `/automations/runs` | All automation runs + time saved |
| GET | `/automations/templates` | Available workflow templates |

### Analytics
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/analytics/dashboard` | Full dashboard data from Supabase |
| GET | `/analytics/funnel` | Recruiting funnel live counts |
| GET | `/analytics/impact` | Before vs. after comparison |

---

## What's Real vs. Simulated

| Feature | Status | Notes |
|---------|--------|-------|
| Claude API responses | ✅ Real | Calls `claude-sonnet-4-5` |
| HuggingFace NER | ✅ Real | `dslim/bert-base-NER` on CPU |
| Skill extraction | ✅ Real | Taxonomy matching |
| Culture fit | ✅ Real | Zero-shot `bart-large-mnli` |
| pgvector search | ✅ Real | Cosine similarity on 384-dim vectors |
| RAGAS evaluation | ✅ Real | Claude-as-judge scoring |
| PII redaction | ✅ Real | Regex patterns |
| Bias audit | ✅ Real | Claude evaluates decisions |
| Supabase persistence | ✅ Real | All data stored |
| Slack/Gmail/Calendar | 🔧 Stubbed | Needs OAuth app setup |

---

## Phamily's 5 Principles in This System

- **Care** — PII redaction protects candidate privacy by default
- **Curiosity** — RAGAS continuously measures and improves response quality  
- **Clarity** — Every automation is documented with an auto-generated runbook
- **Co-Creation** — Workflow builder crosses HR, Ops, IT, Clinical teams
- **Craftsmanship** — Bias audits on every AI screening decision

---

*Built specifically for Phamily (Jaan Health) — PhamilyOps internship project*
