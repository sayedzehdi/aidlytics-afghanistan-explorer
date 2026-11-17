# Afghanistan Development Investment Explorer

A public-data Streamlit dashboard by **Aidlytics**, using World Bank investment-project contract-award records for Afghanistan.

**Status:** Prototype. Financial totals are only displayed after the user uploads and checks an official CSV or Excel export; no figures are preloaded or invented.

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
5. Open the official [World Bank Afghanistan procurement dataset](https://financesone.worldbank.org/contract-awards-in-investment-project-financing-afghanistan-projects/DS01061), download the data as CSV/Excel and upload it to the deployed dashboard.
6. Review detected field mapping and compare the results with the original source before publishing financial claims.

The app needs no secrets or paid API keys. Uploaded files are processed by Streamlit during a session; use only public non-sensitive data.

## Data interpretation
- An award is **not** a disbursement, programme outcome or evidence that construction/services have been completed.
- Repeated contract numbers may reflect multiple suppliers/joint ventures: totals are not automatically deduplicated.
- Always distinguish World Bank fiscal years from calendar years.
- Coverage is limited to the World Bank investment project procurement dataset, not all Afghan aid.
- The official field `Supplier Contract Amount (USD)` already specifies USD.

See [VALIDATION.md](VALIDATION.md) for data-quality caveats.

© Aidlytics. Source attribution: World Bank Group.