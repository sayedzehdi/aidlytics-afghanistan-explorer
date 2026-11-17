"""Pure, testable data operations for Aidlytics Explorer. No network access."""
import re
import pandas as pd

ALIASES = {
 "project": ["project name", "project title", "project id", "project"],
 "year": ["fiscal year", "fiscal_year", "fiscal-year"],
 "category": ["project global practice", "procurement category", "sector", "category"],
 "award": ["supplier contract amount (usd)", "supplier contract amount usd", "supplier_contract_amount_usd", "contract amount", "contract value", "award amount"],
 "contract": ["wb contract number", "wb_contract_number", "contract id", "contract number", "contract reference"],
 "currency": ["currency"]
}
def suggest(columns, kind):
    """Prefer exact case-insensitive aliases; only match longer aliases as substrings."""
    columns = list(columns)
    lower = {str(c).strip().casefold(): c for c in columns}
    for alias in ALIASES[kind]:
        if alias in lower:
            return lower[alias]
    for alias in ALIASES[kind]:
        if len(alias) >= 7:
            for c in columns:
                if alias in str(c).casefold():
                    return c
    return None

def parse_awards(values):
    """Return numeric values, avoiding partial parsing of malformed amounts."""
    s = values.astype("string").str.strip().str.replace(",", "", regex=False)
    s = s.str.replace(r"^\$", "", regex=True).str.strip()
    s = s.replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
    return pd.to_numeric(s, errors="coerce")

def apply_filters(df, selections):
    """selections is a mapping of {column: iterable of allowed string values}."""
    out = df.copy()
    for column, selected in selections.items():
        if selected:
            out = out[out[column].astype("string").isin([str(v) for v in selected])]
    return out

def quality_report(df, amount=None, contract=None):
    report = {"rows": len(df), "exact_duplicate_rows": int(df.duplicated().sum())}
    if contract:
        report["duplicate_contract_identifiers"] = int(df[contract].dropna().duplicated().sum())
    if amount:
        values = parse_awards(df[amount])
        report["missing_or_invalid_amounts"] = int(values.isna().sum())
        report["negative_amounts"] = int((values < 0).sum())
    return report
