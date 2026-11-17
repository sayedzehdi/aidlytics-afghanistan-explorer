# Afghanistan Development Investment Explorer

A public-data Streamlit dashboard by **Aidlytics**, using World Bank investment-project contract-award records for Afghanistan.

**Status:** Prototype. The app automatically loads the public World Bank API (DS01061), paginated at 1,000 rows per request and cached for 24 hours. Manual CSV / Excel upload is also supported. Results must be validated against the original source before publication of analytical claims.

## Run locally
```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

## Deploy to Streamlit Community Cloud
1. Visit https://share.streamlit.io/ and sign in with GitHub.
2. Select **Create app > Deploy a public app from GitHub**.
3. Select `sayedzehdi/aidlytics-afghanistan-explorer`, branch `main`, and main file `app.py`.
4. Deploy and check the app loads. Copy the assigned `*.streamlit.app` URL.
5. The dashboard defaults to loading public World Bank data automatically. If the API is unavailable, select manual CSV / Excel upload in the sidebar.
6. Review the detected mapping and reporting date, and compare summary figures with the official source before publishing claims.

The app needs no secrets or paid API keys. Uploaded files are processed by Streamlit during a session; use only public non-sensitive data. The World Bank API may update and historical snapshot totals may change.

## Data interpretation
- An award is **not** a disbursement, programme outcome or evidence that construction/services have been completed.
- Repeated contract numbers may reflect multiple suppliers/joint ventures: totals are not automatically deduplicated.
- Always distinguish World Bank fiscal years from calendar years.
- Coverage is limited to the World Bank investment project procurement dataset, not all Afghan aid.
- The official field `Supplier Contract Amount (USD)` already specifies USD.

See [VALIDATION.md](VALIDATION.md) for data-quality caveats.

© Aidlytics. Source attribution: World Bank Group.