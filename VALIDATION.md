# Source-specific validation

Official dataset: https://financesone.worldbank.org/contract-awards-in-investment-project-financing-afghanistan-projects/DS01061

Candidate fields: Fiscal Year, Project ID, Project Name, Procurement Category, Project Global Practice, WB Contract Number, Supplier Contract Amount (USD), Contract Signing Date, Supplier and Supplier ID. The USD field does not require a separate currency column.

**Important:** World Bank fiscal years run July–June. Supplier country may represent registration country. Joint ventures and multi-supplier awards can produce repeated contract IDs; do not automatically delete records. Contract awards are not disbursements or achieved programme results.

**Testing:** Syntax and source-field logic reviewed; an end-to-end comparison against the actual official CSV remains pending. Do not present totals as verified before that comparison.
