import pandas as pd
import streamlit as st
import plotly.express as px
import requests
from analytics import suggest, parse_awards, quality_report

SOURCE = "https://financesone.worldbank.org/contract-awards-in-investment-project-financing-afghanistan-projects/DS01061"
st.set_page_config(page_title="Aidlytics | Afghanistan Development Investment Explorer", page_icon="🌍", layout="wide")
st.title("Afghanistan Development Investment Explorer")
st.caption("World Bank Investment Project Financing • Public contract-award records • Prototype")
st.info("Loads the public World Bank dataset automatically. You can also select manual CSV / Excel upload in the sidebar. Missing financial values are never estimated.")
st.markdown(f"[World Bank dataset and documentation]({SOURCE})")

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

st.subheader("Verify field mappings")
st.caption("Field names differ between exports. Please review all suggested mappings.")
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
st.subheader("Filters")
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

k1, k2, k3 = st.columns(3)
k1.metric("Source rows in selection", f"{len(filtered):,}")
k2.metric("Unique projects", f"{filtered[project].nunique():,}" if project != "(not available)" else "Unmapped")
k3.metric("Sum of selected award values", f"{filtered['_award_value'].sum():,.2f} {currency_label}" if can_sum else "Not validated")
if can_sum and not filtered.empty:
    for field, label in [(year, "Award value by fiscal year"), (sector, "Award value by sector/category"), (project, "Top projects by award value")]:
        if field == "(not available)":
            continue
        grouped = filtered.groupby(field, dropna=False, as_index=False)["_award_value"].sum()
        if field == project:
            grouped = grouped.nlargest(15, "_award_value")
        elif field == year:
            grouped = grouped.sort_values(field, key=lambda x: x.astype(str))
        else:
            grouped = grouped.sort_values("_award_value", ascending=False)
        fig = px.bar(grouped, x="_award_value", y=field, orientation="h", title=label,
                     labels={"_award_value": f"Selected award values ({currency_label})"})
        fig.update_layout(yaxis={"categoryorder": "total ascending"} if field != year else {},
                          height=max(360, min(850, len(grouped) * 28)))
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
