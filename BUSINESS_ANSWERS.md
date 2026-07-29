# Business Answers

Candidate name:
Date: 2026-07-29

---

## Q1. Which category or region has the worst SLA breach rate, and what's actually driving it?

**Answer:**

Taken at face value, `Account Access` has the highest category breach rate (66.9%) and
`West` the highest region breach rate (66.6%). But those numbers are almost meaningless
on their own: the overall breach rate across *all* tickets is 65.2%, and every category
(63.8%–66.9%) and every region (62.6%–66.6%) sits within a few points of that baseline.
There is no category or region that stands out as "the problem" — SLA breaches are a
broad, structural issue, not a localized one.

The real driver is agent-level, not category/region-level. Breach rate by agent ranges
from ~62%–66% for 14 of 15 agents — except **AGENT_07, who breaches SLA on 91.9%** of
their tickets (309 tickets, so not a small-sample fluke). AGENT_07's ticket mix is
proportionally spread across all 5 regions and all 5 categories (not concentrated
anywhere), and their first-response time is normal (12.7 hrs vs. 13.5 hrs company
average). What's abnormal is resolution time once a ticket is picked up: **474 hours
average vs. 79.5 hours company-wide — roughly 6x**. This single agent is the actual
driver of the SLA problem, and it would be invisible if you only sliced by
category/region as the question first suggests.

**How you checked it (query/method):**
```python
df['breach'] = df['sla_breached'].eq('Yes').astype(int)
df.groupby('category')['breach'].mean()
df.groupby('region')['breach'].mean()
df.groupby('agent_id')['breach'].agg(['mean','count'])
df[df.agent_id=='AGENT_07'][['region','category']].value_counts(normalize=True)  # checked for concentration - found none
df.groupby('agent_id')[['resolution_time_hours','first_response_time_hours']].mean()
```

---

## Q2. Is there a relationship between priority and resolution time? Which agent(s) deviate, and by how much?

**Answer:**

Yes — the relationship is exactly what you'd expect from working priority triage
correctly. Median resolution time by priority:

| Priority | Median resolution time |
|---|---|
| Critical | 5.5 hrs |
| High | 18.3 hrs |
| Medium | 51.1 hrs |
| Low | 98.5 hrs |

That's a clean, monotonic relationship (negative rows excluded — see Q4).

**AGENT_07 is the one clear outlier**, and it's not a mild deviation: across every
single priority level, their median resolution time is **8.5x–9.4x** the company
median for that priority (e.g. Critical tickets that should resolve in ~5.5 hrs take
this agent ~48 hrs on average). Every other agent falls within roughly 0.8x–1.15x of
the norm — normal variance, nothing structural. This is the same agent flagged in Q1,
and it's consistent: the SLA breach problem and the resolution-time problem are the
same underlying issue.

**How you checked it (query/method):**
```python
clean = df[df['resolution_time_hours'] >= 0]  # drop 88 impossible negative values
overall_median = clean.groupby('priority')['resolution_time_hours'].median()
agent_median = clean.groupby(['agent_id','priority'])['resolution_time_hours'].median().unstack()
ratio = agent_median.div(overall_median, axis=1)  # >1 = slower than company median
```

---

## Q3. Which customer(s) show frequent reopened tickets or low CSAT scores? Agent-driven, category-driven, or something else?

**Answer:**

Filtering to customers with ≥5 tickets (150 customers, ~33 tickets each on average, so
this isn't small-sample noise):

- Highest reopen rates: **CUST_057 (24.1%), CUST_058 (23.8%), CUST_133 (22.2%)** — all
  well above the 10.2% company-wide reopen rate.
- Lowest CSAT: **CUST_089 (3.36), CUST_037 (3.50), CUST_012 (3.52)** — vs. 3.97 company
  average.

Notably, the reopen-rate leaders and the low-CSAT leaders are almost entirely
**different customers** — reopens and dissatisfaction aren't the same phenomenon here.

Is it agent- or category-driven? No, and I checked directly rather than assuming:
- Each flagged customer's tickets are spread across **10–15 different agents** (of 15
  total) — no single agent is disproportionately handling their cases.
- Category mix for flagged customers is roughly proportional to the company-wide mix
  (e.g. CUST_089 skews slightly toward Billing — 44% vs. 31% baseline — but not
  dramatically, and every other flagged customer looks close to average).
- Ticket volume itself doesn't explain it either: correlation between ticket count and
  reopen rate is ~0.08, and with CSAT is ~-0.09 — both negligible.

Honest conclusion: this looks **customer-specific rather than agent- or
category-driven** — these customers are harder to satisfy or have genuinely more
complex issues, and it isn't traceable to one bad agent or one broken process. With
~25–45 tickets per flagged customer it's more than noise, but the underlying "why" would
need account-level context (contract size, industry, tenure) that isn't in this
dataset — worth flagging to account management rather than to the support team.

**How you checked it (query/method):**
```python
cust = df.groupby('customer_id').agg(
    tickets=('ticket_id','count'),
    reopened=('status', lambda s: (s=='Reopened').sum()),
    avg_csat=('csat_score','mean'),
    n_agents=('agent_id','nunique'))
cust['reopen_rate'] = cust['reopened']/cust['tickets']
cust[cust.tickets>=5].sort_values('reopen_rate', ascending=False)
cust['tickets'].corr(cust['reopen_rate'])  # volume isn't a confound
```

---

## Q4. What data quality issues did you find, and how did you handle them?

**Answer:**

1. **15 exact duplicate rows** (same `ticket_id` and all fields). Dropped via
   `drop_duplicates(subset='ticket_id')` before any analysis.
2. **88 negative `resolution_time_hours` values** (as low as -19.9 hrs) — physically
   impossible. These aren't explained by `resolved_date < created_date` (date order was
   fine in every case), so it's noise in that specific field, not a date-logic bug.
   Excluded these rows from resolution-time calculations (Q2) rather than imputing —
   flipping the sign would be a guess I can't justify.
3. **Missing `resolved_date` (1,040 rows) and `resolution_time_hours` (1,278 rows).**
   Partly structural — `Open` tickets correctly have no resolved date. But 381
   `Resolved` and 94 `Closed` tickets are *also* missing a resolved date, and ~677
   tickets that *do* have a resolved date are still missing resolution time. This subset
   looks close to randomly distributed across categories (17–18% missing in each), so I
   treated it as missing-at-random and excluded from time-based averages rather than
   imputing a value.
4. **`csat_score` missing for 1,023 rows — but this is not a data quality bug.** It's
   missing for exactly (and only) `Open` and `Reopened` tickets — i.e., tickets that
   haven't been rated yet because they're not closed. Every `Resolved`/`Closed` ticket
   has a CSAT score. Worth stating explicitly so it isn't mistaken for a gap.
5. **73 missing `created_date`.** No clean way to recover these; excluded from any
   date/time-trend analysis (didn't affect the 5 questions above, which don't use
   `created_date` directly).
6. **`sla_breached` is always "No" for every `Open` ticket (512/512).** This is a
   business-logic gap, not a formatting issue: an open ticket that's already overdue
   should arguably be flagged as breaching, but the field appears to only get set at
   resolution. I did not "fix" this (would require assuming a breach threshold not in
   the data) but flagged it — it means the breach rates in this report likely
   *understate* the true current breach rate, since open-and-already-late tickets aren't
   counted yet.
7. **Categorical fields are clean** — checked `region`, `channel`, `category`,
   `priority`, `status`, `sla_breached` for typos/casing/whitespace issues via
   `value_counts()`; no inconsistencies found.

---

## Q5. If you could track exactly one metric weekly to catch support problems early, what would it be and why?

**Answer:**

**Median resolution time per agent, this week vs. trailing 8-week baseline, flagged
when any agent's ratio exceeds ~2x.**

Not overall breach rate, and not average CSAT — both are lagging and both would have
taken months to visibly move given AGENT_07 was buried inside an otherwise-normal
65% company-wide breach rate. Resolution time is the earliest and most agent-specific
signal available: it isolates *this agent, this week* from company-wide noise, doesn't
depend on volume (first-response time was normal for AGENT_07, so that metric wouldn't
have caught it), and would have flagged the AGENT_07 pattern in the first week or two
of drift rather than after ~300 tickets had already accumulated at a 92% breach rate.
It's also actionable: a resolution-time spike for one agent points a manager directly
at that person, rather than at a vague "category is underperforming" finding that sends
someone chasing the wrong root cause.

---

## Anything else you'd flag if this were a real dataset at FreightFox?

- I'd want a way to distinguish "genuinely difficult ticket" from "agent is stuck" in
  resolution time — e.g., agent notes or escalation flags — since right now AGENT_07's
  474-hour average could be one true outlier skewing the mean rather than a systemic
  slowdown. (I used both mean and median throughout specifically to guard against this,
  and the pattern holds under median too, but a manager conversation with AGENT_07
  would resolve it in five minutes.)
- The `sla_breached=No` default on all `Open` tickets (Q4, point 6) means any dashboard
  built on this data will always understate current-state risk. I'd fix that at the
  source (compute breach status live off elapsed time vs. SLA target) rather than only
  at resolution.
- With 150 customers and ~33 tickets each, this data is suspiciously uniform (real
  ticket volume per customer is almost never this evenly distributed) — if this were
  live data I'd sanity-check it against the billing/CRM system before presenting these
  findings externally.
