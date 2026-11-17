# DataMind AI

DataMind AI is an adaptive data analytics MVP using **Next.js on Vercel**, **Supabase**, **Python FastAPI on Railway**, and the **Claude API**.

## Features
- Email/password authentication via Supabase.
- CSV/XLSX upload with per-user dataset storage.
- Genuine data quality profiling, descriptive statistics, and Pearson correlations computed in Python.
- Dataset and analysis result records persisted in Supabase.
- Claude explanations grounded in computed numeric summaries.
- Downloadable JSON report. No simulated results.

## Deployment
1. Configure Vercel root directory to `web`.
2. Configure Railway service root directory to `analytics`.
3. Set `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, and `NEXT_PUBLIC_ANALYTICS_URL` on Vercel.
4. Set `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `ALLOWED_ORIGINS`, and `ANTHROPIC_API_KEY` on Railway. Do not expose server secrets to the browser.
5. Create the database tables and private datasets bucket using the Supabase setup in `supabase/schema.sql`.
6. Start Python locally: `cd analytics && pip install -r requirements.txt && uvicorn main:app --reload`.
7. Start frontend locally: `cd web && npm install && npm run dev`.

The MVP is not a full autonomous ML platform. It does not yet include cross-validation pipelines, background processing, or forecasting.
