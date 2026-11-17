import pandas as pd
import streamlit as st
import plotly.express as px
import requests
from analytics import suggest, parse_awards, quality_report

SOURCE = "https://financesone.worldbank.org/contract-awards-in-investment-project-financing-afghanistan-projects/DS01061"
st.set_page_config(page_title="Aidlytics | Afghanistan Development Investment Explorer", page_icon="🌍", layout="wide")
st.markdown("""<style>
:root { --brand:#123C4A; --accent:#C46E37; }
.block-container { padding-top: 1.6rem; max-width: 1250px; }
h1, h2, h3 { letter-spacing: -0.035em; }
h1 { color: #123C4A; font-weight: 750; }
div[data-testid="stMetric"] { background:#F5F8F8; border:1px solid #DDE7E8; padding:1.05rem 1.15rem; border-radius:12px; min-height:115px; }
div[data-testid="stMetricLabel"] { color:#50616B; }
div[data-testid="stMetricValue"] { color:#123C4A; }
.aid-kicker { color:#C46E37; font-weight:700; font-size:.78rem; letter-spacing:.12em; text-transform:uppercase; }
.aid-subtitle { color:#63737C; max-width:900px; margin-top:-.5rem; }
</style>""", unsafe_allow_html=True)
st.markdown('<p class="aid-kicker">AIDLYTICS / PUBLIC DATA EXPLORER</p>', unsafe_allow_html=True)
st.title("Afghanistan Development Investment Explorer")
st.markdown('<p class="aid-subtitle">Explore World Bank-financed project contract awards through transparent public data. Values reflect source records, not donor disbursements or programme outcomes.</p>', unsafe_allow_html=True)
st.caption("World Bank Investment Project Financing · Prototype · Source values in USD where verified")


WORLD_BANK_API = "https://datacatalogapi.worldbank.org/dexapps/fone/api/view"
@st.cache_data(ttl=86400, show_spinner=False)
def fetch_world_bank_data():
    rows = []
    limit = 1000
    for skip in range(0, 100000, limit):
        response = requests.get(WORLD_BANK_API, params={
            "viewId": "DS01061", "type": "json", "top": limit, "skip": skip
        }, timeout=35)
        response.raise_for_status()
        payload = response.json()
        page = payload.get("data") if isinstance(payload, dict) else payload
        if not isinstance(page, list):
            raise ValueError("World Bank API returned an unexpected format.")
        rows.extend(page)
        if len(page) < limit:
            expected = payload.get("count") if isinstance(payload, dict) else None
            if expected is not None and len(rows) < int(expected):
                raise ValueError(f"Incomplete API response: received {len(rows)} of {expected} records.")
            break
    else:
        raise ValueError("API pagination exceeded the expected record limit.")
    result = pd.DataFrame(rows)
    if result.empty or "supplier_contract_amount_usd" not in result.columns:
        raise ValueError("No usable World Bank records were returned.")
    return result

with st.sidebar:
    st.subheader("Data source")
    st.markdown(f"[Original World Bank dataset]({SOURCE})")
    source_mode = st.radio("Choose source", ["World Bank live API", "Upload CSV / Excel"], index=0)
    st.caption("Automatic source updates are cached for 24 hours. Data is subject to the World Bank's published revisions.")

df = None
if source_mode == "World Bank live API":
    try:
        with st.spinner("Loading public records from the World Bank..."):
            df = fetch_world_bank_data()
        st.success(f"Loaded {len(df):,} World Bank records automatically.")
        if "as_of_date" in df.columns:
            dates = pd.to_datetime(df["as_of_date"], errors="coerce").dropna()
            if not dates.empty:
                st.caption("World Bank data as of " + str(dates.max().date()))
    except Exception as exc:
        st.error("World Bank data could not be loaded automatically. Choose 'Upload CSV / Excel' in the sidebar to use a public downloaded copy.")
        st.caption(f"Technical detail: {exc}")
        st.stop()
else:
    uploaded = st.file_uploader("Upload public procurement dataset", type=["csv", "xlsx", "xls"])
    if uploaded is None:
        st.info("Select a public CSV or Excel export from the official World Bank dataset.")
        st.stop()
    try:
        if uploaded.name.lower().endswith(".csv"):
            try:
                df = pd.read_csv(uploaded)
            except UnicodeDecodeError:
                uploaded.seek(0)
                df = pd.read_csv(uploaded, encoding="latin-1")
        else:
            df = pd.read_excel(uploaded)
    except Exception as exc:
        st.error(f"Could not read this file: {exc}")
        st.stop()

if df.empty:
    st.warning("The uploaded file contains no rows.")
    st.stop()

df.columns = [str(c).strip() for c in df.columns]
fields = list(df.columns)
choices = ["(not available)"] + fields

def choose_field(label, kind):
    match = suggest(fields, kind)
    return st.selectbox(label, choices, index=choices.index(match) if match else 0)

with st.expander("Data settings and column mappings", expanded=False):
    st.caption("Mapping is automatic for standard World Bank data. Review or adjust it when using a different export.")
    a, b, c = st.columns(3)
    with a:
        project = choose_field("Project", "project")
        year = choose_field("Fiscal year", "year")
    with b:
        sector = choose_field("Sector / category", "category")
        amount = choose_field("Supplier contract award value", "award")
    with c:
        contract = choose_field("Contract number / identifier", "contract")
        currency = choose_field("Currency (optional for USD-labelled fields)", "currency")

filtered = df.copy()
st.subheader("Explore the data")
st.caption("Choose one or more filter values; totals and charts update together.")
for label, field in [("Fiscal year", year), ("Project", project), ("Sector", sector)]:
    if field != "(not available)":
        values = sorted(filtered[field].dropna().astype(str).unique().tolist())
        if len(values) <= 500:
            selected = st.multiselect(label, values)
            if selected:
                filtered = filtered[filtered[field].astype(str).isin(selected)]
        else:
            st.caption(f"{label}: over 500 distinct values; filter using downloaded records.")

is_usd = amount != "(not available)" and ("usd" in amount.lower() or "us$" in amount.lower())
currency_label = "USD" if is_usd and currency == "(not available)" else "not verified"
if currency != "(not available)":
    currencies = sorted(filtered[currency].dropna().astype(str).unique().tolist())
    if currencies:
        picked = st.selectbox("Select currency", currencies) if len(currencies) > 1 else currencies[0]
        filtered = filtered[filtered[currency].astype(str) == picked]
        currency_label = picked
    else:
        st.warning("No currency values are available in the selected records.")

can_sum = amount != "(not available)" and currency_label != "not verified"
if amount != "(not available)":
    numeric = parse_awards(filtered[amount])
    filtered = filtered.assign(_award_value=numeric)
    if numeric.isna().sum():
        st.warning(f"{numeric.isna().sum():,} missing/non-numeric award values are excluded from calculations.")
    if not can_sum:
        st.warning("Map an explicit currency column or a USD-labelled amount column to enable financial totals.")
if contract != "(not available)":
    duplicates = filtered[contract].dropna().duplicated().sum()
    if duplicates:
        st.warning(f"{duplicates:,} repeated non-null contract identifiers found. These may be multi-supplier or joint-venture awards; verify before interpreting totals.")

def short_money(value):
    if abs(value) >= 1e9:
        return f"$ {value/1e9:,.2f}B"
    if abs(value) >= 1e6:
        return f"$ {value/1e6:,.2f}M"
    if abs(value) >= 1e3:
        return f"$ {value/1e3:,.1f}K"
    return f"$ {value:,.2f}"

st.markdown("### Overview")
k1, k2, k3 = st.columns(3)
k1.metric("Contract-award source rows", f"{len(filtered):,}")
k2.metric("Unique projects", f"{filtered[project].nunique():,}" if project != "(not available)" else "Unmapped")
if can_sum:
    k3.metric("Total award value (USD)", short_money(filtered["_award_value"].sum()) if currency_label.upper()=="USD" else f"{filtered['_award_value'].sum():,.2f} {currency_label}")
    st.caption(f"Exact filtered source-row sum: {filtered['_award_value'].sum():,.2f} {currency_label}. No deduplication or inflation adjustment.")
else:
    k3.metric("Total award value", "Currency unverified")
if can_sum and not filtered.empty:
    st.markdown("### Where awards are recorded")
    def get_group(field):
        if field == "(not available)":
            return None
        result = filtered.groupby(field, dropna=False)["_award_value"].sum().reset_index()
        result[field] = result[field].fillna("Not classified").astype(str)
        return result
    yearly = get_group(year)
    categories = get_group(sector)
    left, right = st.columns([1.1, 1])
    with left:
        if yearly is not None:
            yearly["_sort"] = pd.to_numeric(yearly[year], errors="coerce")
            yearly = yearly.sort_values(["_sort", year], na_position="last")
            fig = px.bar(yearly, x=year, y="_award_value", title="Awards by fiscal year",
                labels={year:"Fiscal year", "_award_value":f"Award value ({currency_label})"}, color_discrete_sequence=["#1B6672"])
            fig.update_layout(margin=dict(l=5,r=10,t=50,b=15),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",xaxis_type="category")
            fig.update_yaxes(tickformat="~s", showgrid=True, gridcolor="#E7ECEE")
            st.plotly_chart(fig, use_container_width=True)
    with right:
        if categories is not None:
            categories = categories.sort_values("_award_value",ascending=True)
            fig = px.bar(categories, x="_award_value", y=sector, orientation="h", title="Awards by procurement category",
                labels={sector:"", "_award_value":f"Award value ({currency_label})"}, color_discrete_sequence=["#C46E37"])
            fig.update_layout(margin=dict(l=5,r=10,t=50,b=15),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",height=max(330,len(categories)*42))
            fig.update_xaxes(tickformat="~s", showgrid=True, gridcolor="#E7ECEE")
            st.plotly_chart(fig, use_container_width=True)
    if project != "(not available)":
        projects = get_group(project).nlargest(12, "_award_value").sort_values("_award_value")
        fig = px.bar(projects, x="_award_value", y=project, orientation="h",
            title="Top 12 projects by source-row award value", labels={project:"", "_award_value":f"Award value ({currency_label})"},
            color_discrete_sequence=["#1B6672"])
        fig.update_layout(margin=dict(l=5,r=10,t=55,b=15),height=470,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)")
        fig.update_xaxes(tickformat="~s", gridcolor="#E7ECEE")
        st.plotly_chart(fig, use_container_width=True)
st.subheader("Data-quality summary")
report = quality_report(filtered.drop(columns=["_award_value"], errors="ignore"), amount if amount != "(not available)" else None, contract if contract != "(not available)" else None)
q1, q2, q3 = st.columns(3)
q1.metric("Repeated contract IDs", f'{report.get("duplicate_contract_identifiers", 0):,}')
q2.metric("Missing or invalid award values", f'{report.get("missing_or_invalid_amounts", 0):,}')
q3.metric("Exact duplicate rows", f'{report["exact_duplicate_rows"]:,}')
if report.get("negative_amounts", 0):
    st.warning(f'{report["negative_amounts"]:,} negative award values need review before interpretation.')
if report["exact_duplicate_rows"]:
    st.warning("Exact duplicate source rows detected. They have not been removed automatically.")
st.subheader("Filtered source records")
st.dataframe(filtered.drop(columns=["_award_value"], errors="ignore"), use_container_width=True)
st.download_button("Download filtered records (CSV)", filtered.drop(columns=["_award_value"], errors="ignore").to_csv(index=False).encode("utf-8-sig"), file_name="aidlytics_filtered_awards.csv", mime="text/csv")
with st.expander("Methodology and limitations", expanded=True):
    st.markdown("""**Source:** World Bank Group, Contract Awards in Investment Project Financing — Afghanistan Projects. Consult the linked dataset for dates, field definitions, licence and coverage.

- **Unit of analysis:** source rows, not necessarily distinct contracts. Repeated identifiers can reflect joint ventures, suppliers or amendments.
- **Contract awards are not** donor commitments, disbursements, expenditures, completed projects, or development outcomes.
- **Currency:** no exchange-rate conversion is performed. Verify USD-labelled amount fields and any currency selections.
- **Fiscal years:** World Bank fiscal years are not calendar years.
- **Coverage:** records do not represent all aid or development financing in Afghanistan.
- **Validation:** review the actual World Bank file and any duplicated or missing values before publishing conclusions.
- **Privacy:** upload only publicly shareable data; the hosting platform processes files during the active session.
""")
