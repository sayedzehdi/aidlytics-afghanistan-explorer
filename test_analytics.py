import unittest
import pandas as pd
from analytics import suggest, parse_awards, apply_filters, quality_report

class ExplorerTests(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({
            "Project Name": ["Canal", "Canal", "Clinic", "School"],
            "Fiscal Year": [2024, 2025, 2025, 2026],
            "Procurement Category": ["Works", "Goods", "Works", "Services"],
            "Supplier Contract Amount (USD)": ["1,250.00", "500", "700", None],
            "WB Contract Number": ["A", "B", "C", "C"]
        })
    def test_official_columns_detected(self):
        for kind, expected in [("project","Project Name"),("year","Fiscal Year"),
            ("category","Procurement Category"),("award","Supplier Contract Amount (USD)"),
            ("contract","WB Contract Number")]:
            self.assertEqual(suggest(self.df.columns,kind),expected)
    def test_do_not_guess_generic_value_or_currency(self):
        self.assertIsNone(suggest(["Total Impact Value","Fiscal Adjustment"],"award"))
        self.assertIsNone(suggest(self.df.columns,"currency"))
    def test_filtering(self):
        result = apply_filters(self.df, {"Fiscal Year": ["2025"],"Procurement Category":["Works"]})
        self.assertEqual(result["Project Name"].tolist(),["Clinic"])
        self.assertEqual(len(apply_filters(self.df, {"Project Name":["Canal"]})),2)
    def test_money_parsing_and_totals(self):
        numbers = parse_awards(self.df["Supplier Contract Amount (USD)"])
        self.assertEqual(numbers.sum(),2450)
        self.assertEqual(numbers.isna().sum(),1)
        self.assertTrue(pd.isna(parse_awards(pd.Series(["12bad"]))[0]))
    def test_qa(self):
        report=quality_report(self.df,"Supplier Contract Amount (USD)","WB Contract Number")
        self.assertEqual(report["duplicate_contract_identifiers"],1)
        self.assertEqual(report["missing_or_invalid_amounts"],1)
        self.assertEqual(report["negative_amounts"],0)
    def test_export_rows(self):
        result=apply_filters(self.df,{"Fiscal Year":["2025"]})
        restored=pd.read_csv(__import__("io").StringIO(result.to_csv(index=False)))
        self.assertEqual(len(restored),2)

if __name__ == "__main__":
    unittest.main()
