import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Support Ops Dashboard", layout="wide")

# ---------- Load & clean ----------
@st.cache_data
def load_data():
    df = pd.read_csv("customer_tickets.csv")
    before = len(df)
    df = df.drop_duplicates(subset="ticket_id")
    dupes_removed = before - len(df)

    df["created_date"] = pd.to_datetime(df["created_date"], errors="coerce")
    df["resolved_date"] = pd.to_datetime(df["resolved_date"], errors="coerce")
    df["breach"] = df["sla_breached"].eq("Yes").astype(int)

    # negative resolution times are impossible -> treat as bad data, keep a "clean" copy for time-based stats
    df["resolution_time_clean"] = df["resolution_time_hours"].where(df["resolution_time_hours"] >= 0)

    return df, dupes_removed

df, dupes_removed = load_data()

st.title("Customer Support Analytics")
st.caption("Ticket-level SLA, resolution-time, and customer-health dashboard")

# ---------- Sidebar filters ----------
st.sidebar.header("Filters")
regions = st.sidebar.multiselect("Region", sorted(df["region"].unique()), default=sorted(df["region"].unique()))
categories = st.sidebar.multiselect("Category", sorted(df["category"].unique()), default=sorted(df["category"].unique()))

f = df[df["region"].isin(regions) & df["category"].isin(categories)]

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Data quality note:** {dupes_removed} duplicate rows removed. "
                     f"{(df['resolution_time_hours']<0).sum()} rows had negative resolution times "
                     f"(excluded from time-based averages).")

# ---------- Top KPIs ----------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Tickets", f"{len(f):,}")
c2.metric("SLA Breach Rate", f"{f['breach'].mean()*100:.1f}%")
c3.metric("Median Resolution Time (hrs)", f"{f['resolution_time_clean'].median():.1f}")
c4.metric("Avg CSAT", f"{f['csat_score'].mean():.2f} / 5")

st.markdown("---")

# ---------- Q1: Breach rate by category/region ----------
st.subheader("1. SLA Breach Rate — Category & Region")
col1, col2 = st.columns(2)
with col1:
    cat_breach = f.groupby("category")["breach"].mean().sort_values(ascending=False).reset_index()
    fig = px.bar(cat_breach, x="category", y="breach", title="Breach rate by category",
                 labels={"breach": "Breach rate"})
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)
with col2:
    reg_breach = f.groupby("region")["breach"].mean().sort_values(ascending=False).reset_index()
    fig = px.bar(reg_breach, x="region", y="breach", title="Breach rate by region",
                  labels={"breach": "Breach rate"})
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)

st.markdown("**What's really driving breaches: agent, not category/region.**")
agent_breach = f.groupby("agent_id")["breach"].agg(["mean", "count"]).reset_index().sort_values("mean", ascending=False)
fig = px.bar(agent_breach, x="agent_id", y="mean", title="Breach rate by agent",
             labels={"mean": "Breach rate"}, hover_data=["count"])
fig.update_yaxes(tickformat=".0%")
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ---------- Q2: Priority vs resolution time ----------
st.subheader("2. Priority vs Resolution Time")
order = ["Critical", "High", "Medium", "Low"]
col1, col2 = st.columns(2)
with col1:
    fig = px.box(f.dropna(subset=["resolution_time_clean"]), x="priority", y="resolution_time_clean",
                 category_orders={"priority": order}, title="Resolution time distribution by priority")
    st.plotly_chart(fig, use_container_width=True)
with col2:
    overall_med = f.groupby("priority")["resolution_time_clean"].median().reindex(order)
    agent_med = f.groupby(["agent_id", "priority"])["resolution_time_clean"].median().unstack().reindex(columns=order)
    ratio = agent_med.div(overall_med, axis=1)
    ratio["avg_ratio"] = ratio.mean(axis=1)
    ratio = ratio.sort_values("avg_ratio", ascending=False).reset_index()
    fig = px.bar(ratio, x="agent_id", y="avg_ratio", title="Agent resolution time vs. company median (1.0 = normal)")
    fig.add_hline(y=1, line_dash="dash")
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ---------- Q3: Customer health ----------
st.subheader("3. Customer Health — Reopens & CSAT")
cust = f.groupby("customer_id").agg(
    tickets=("ticket_id", "count"),
    reopened=("status", lambda s: (s == "Reopened").sum()),
    avg_csat=("csat_score", "mean"),
    n_agents=("agent_id", "nunique"),
).reset_index()
cust["reopen_rate"] = cust["reopened"] / cust["tickets"]
cust = cust[cust["tickets"] >= 5]

col1, col2 = st.columns(2)
with col1:
    top_reopen = cust.sort_values("reopen_rate", ascending=False).head(10)
    fig = px.bar(top_reopen, x="customer_id", y="reopen_rate", title="Top 10 customers by reopen rate")
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)
with col2:
    low_csat = cust.sort_values("avg_csat").head(10)
    fig = px.bar(low_csat, x="customer_id", y="avg_csat", title="Bottom 10 customers by avg CSAT")
    st.plotly_chart(fig, use_container_width=True)

st.caption("Each flagged customer's tickets are spread across 10+ agents and all 5 categories — "
           "no single agent or category explains the pattern.")

st.markdown("---")
st.subheader("Raw data (filtered)")
st.dataframe(f, use_container_width=True, height=300)
