import pandas as pd
import streamlit as st
import plotly.express as px

SOURCE = "https://financesone.worldbank.org/contract-awards-in-investment-project-financing-afghanistan-projects/DS01061"
st.set_page_config(page_title="Aidlytics | Afghanistan Development Investment Explorer", page_icon="🌍", layout="wide")
st.title("Afghanistan Development Investment Explorer")
st.caption("World Bank Investment Project Financing • Public contract-award records • Prototype")
st.info("Upload an official World Bank CSV or Excel export. No data are bundled and no missing values are estimated.")
st.markdown(f"[World Bank dataset and documentation]({SOURCE})")

uploaded = st.file_uploader("Upload public procurement dataset", type=["csv", "xlsx", "xls"])
if uploaded is None:
    st.subheader("Getting started")
    st.write("Download the original data from the World Bank link, upload it here, and verify the field mappings before analysing the results.")
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

def choose_field(label, suggestions):
    match = next((c for s in suggestions for c in fields if s in c.lower()), None)
    return st.selectbox(label, choices, index=choices.index(match) if match else 0)

st.subheader("Verify field mappings")
st.caption("Field names differ between exports. Please review all suggested mappings.")
a, b, c = st.columns(3)
with a:
    project = choose_field("Project", ["project name", "project title", "project id", "project"])
    year = choose_field("Fiscal year", ["fiscal year", "fiscal_year", "fy", "year"])
with b:
    sector = choose_field("Sector / category", ["project global practice", "procurement category", "sector", "category"])
    amount = choose_field("Supplier contract award value", ["supplier contract amount (usd)", "supplier_contract_amount_usd", "contract amount", "contract value", "award amount", "amount"])
with c:
    contract = choose_field("Contract number / identifier", ["wb contract number", "wb_contract_number", "contract id", "contract number", "contract reference"])
    currency = choose_field("Currency (optional for USD-labelled fields)", ["currency", "curr"])

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
    cleaned = filtered[amount].astype(str).str.replace(",", "", regex=False).str.replace(r"[^0-9.\-]", "", regex=True)
    numeric = pd.to_numeric(cleaned, errors="coerce")
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
