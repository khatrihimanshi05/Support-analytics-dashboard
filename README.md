# Customer Support Analytics Dashboard

A Streamlit dashboard analyzing ~5,000 support tickets to surface SLA breach drivers,
agent performance, and at-risk customers.

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

Requires `customer_tickets.csv` in the same folder as `app.py`.

## Deploy (Streamlit Community Cloud)

1. Push this folder to a public GitHub repo (includes `app.py`, `requirements.txt`,
   `customer_tickets.csv`).
2. Go to https://share.streamlit.io, sign in with GitHub, click "New app".
3. Point it at this repo, branch `main`, file `app.py`. Deploy.
4. You'll get a public URL like `https://<your-app>.streamlit.app`.

## Approach

1. **Data quality first.** Before answering any business question, I audited the
   dataset for nulls, duplicates, invalid values, and internal consistency
   (e.g. does `status` line up with `resolved_date` and `csat_score`?). Findings
   and how each was handled are in `BUSINESS_ANSWERS.md` (Q4).
2. **Answered each question with code, not eyeballing.** All numbers in
   `BUSINESS_ANSWERS.md` come from groupby/aggregation queries against the
   cleaned data — the queries are described inline so they're reproducible.
3. **Dashboard mirrors the analysis.** Each section of `app.py` corresponds
   directly to one business question, so the visuals and the written answers
   are backed by the same underlying calculations (no separate "pretty"
   numbers vs. "real" numbers).
4. **Biggest finding drove the design.** The single largest driver of SLA
   breaches turned out to be one agent (AGENT_07), not a category or region —
   so the dashboard leads with category/region views (matching the literal
   question) but immediately follows with the agent-level view that actually
   explains the pattern, rather than burying it.

## Stack

- Streamlit (dashboard/UI)
- Pandas (data wrangling)
- Plotly (charts)
