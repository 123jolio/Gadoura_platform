# Gadoura Monitoring — Deployment Guide

## Architecture

> Runtime decision: **code is deployed from this repository**, while Google Drive is used only for data (`field data/`, `satellite data/`).
> `drive_sync.py` intentionally skips `.py` files, so do not rely on `/tmp/gadoura/code/*.py`.

```
Google Drive (shared folder)
        │
        │  Drive API (service account)
        ▼
  /tmp/gadoura/              ← GADOURA_PLATFORM_ROOT
  ├── field data/            ← GADOURA_FIELD_DATA_ROOT
  │   └── *.xlsx
  └── satellite data/        ← GADOURA_SATELLITE_DATA_ROOT
      ├── DATA/              ← GADOURA_DATA_ROOT
      │   ├── *.csv
      │   └── VALIDATED_*.csv
      ├── BGR/GeoTIFFs/
      ├── Chlorophyl_validated/
      └── ...
```

### Sync strategy

| File type | When downloaded |
|-----------|----------------|
| `.csv`, `.xlsx` (< 20 MB) | **Eager** — on container startup |
| GeoTIFF `.tif` | **Lazy** — only when a user selects that date |

---

## Step 1 — Google Drive setup

1. In Drive, create (or confirm) your top-level folder, e.g. **Gadoura Platform**.
   Its sub-structure must match the layout above.

2. Note the **folder ID** from the URL:
   `https://drive.google.com/drive/folders/`**`1AbCdEfGhIjKlMnOpQrStUv`**

3. Create a **Service Account**:
   - [console.cloud.google.com](https://console.cloud.google.com) → IAM & Admin → Service Accounts
   - Create → download JSON key
   - Enable the **Google Drive API** for your project

4. Share your Drive folder with the service account email
   (`xxx@project-id.iam.gserviceaccount.com`) — **Viewer** role is enough.

---

## Step 2 — Required environment variables

| Variable | Value |
|----------|-------|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Full contents of the downloaded JSON key |
| `GADOURA_DRIVE_ROOT_FOLDER_ID` | Folder ID from Step 1 |
| `GADOURA_PLATFORM_ROOT` | `/tmp/gadoura` |
| `GADOURA_FIELD_DATA_ROOT` | `/tmp/gadoura/field data` |
| `GADOURA_SATELLITE_DATA_ROOT` | `/tmp/gadoura/satellite data` |
| `GADOURA_DATA_ROOT` | `/tmp/gadoura/satellite data/DATA` |

**Never** commit the service-account JSON to Git.

---

## Option A — Render.com (easiest)

1. Push this repo to GitHub (private).
2. [render.com](https://render.com) → New → Blueprint → connect repo.
   Render detects `render.yaml` automatically.
3. In the Render dashboard → your service → **Environment**:
   - Add `GOOGLE_SERVICE_ACCOUNT_JSON` (paste full JSON)
   - Add `GADOURA_DRIVE_ROOT_FOLDER_ID`
4. Deploy. URL: `https://gadoura-monitoring.onrender.com`

**Cost**: Starter plan ~$7/mo. Upgrade to Standard ($25/mo) for 2 GB RAM
if many large GeoTIFFs are loaded simultaneously.

---

## Option B — Railway.app

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login & create project
railway login
railway init

# Set secrets
railway variables set GOOGLE_SERVICE_ACCOUNT_JSON="$(cat service-account.json)"
railway variables set GADOURA_DRIVE_ROOT_FOLDER_ID=1AbCdEfGhI...
railway variables set GADOURA_PLATFORM_ROOT=/tmp/gadoura
railway variables set GADOURA_FIELD_DATA_ROOT="/tmp/gadoura/field data"
railway variables set GADOURA_SATELLITE_DATA_ROOT="/tmp/gadoura/satellite data"
railway variables set GADOURA_DATA_ROOT="/tmp/gadoura/satellite data/DATA"

# Deploy
railway up
```

**Cost**: ~$5/mo for a hobby project.

---

## Option C — Google Cloud Run (most scalable)

```bash
# One-time setup
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Store service-account JSON as a Secret Manager secret
gcloud secrets create gadoura-sa-json \
  --data-file=service-account.json

# Grant Cloud Run SA access to the secret
gcloud secrets add-iam-policy-binding gadoura-sa-json \
  --member="serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Deploy (builds + deploys in one step)
gcloud builds submit --config cloudbuild.yaml \
  --substitutions _DRIVE_FOLDER_ID=1AbCdEfGhI...
```

**Cost**: Scales to zero when idle. ~$0 if traffic is light.
First 2M requests/month free.

---

## Local development (no Drive sync)

```bash
# Point directly at your real data on disk
export DRIVE_SYNC_DISABLE=1
export GADOURA_PLATFORM_ROOT=/path/to/your/local/data
export GADOURA_FIELD_DATA_ROOT="$GADOURA_PLATFORM_ROOT/field data"
export GADOURA_SATELLITE_DATA_ROOT="$GADOURA_PLATFORM_ROOT/satellite data"
export GADOURA_DATA_ROOT="$GADOURA_SATELLITE_DATA_ROOT/DATA"

streamlit run data_presentation_1.py
```

---

## File layout expected in Drive

```
Gadoura Platform/              ← GADOURA_DRIVE_ROOT_FOLDER_ID points here
├── field data/
│   └── ΑΠΟΤΕΛΕΣΜΑΤΑ_...xlsx
└── satellite data/
    ├── DATA/
    │   ├── VALIDATED_CHLOROPHYL.csv
    │   ├── VALIDATED_AVERAGED CHLOROPHYLL.csv
    │   ├── charts_turbidity/
    │   │   ├── homvoller turbidity.csv
    │   │   └── average turbidity.csv
    │   └── *level*.csv  (or *υψος*.csv)
    ├── BGR/GeoTIFFs/
    ├── Burned Areas/GeoTIFFs/
    ├── Burned Areas_large/GeoTIFFs/
    ├── Chlorophyl_validated/code/GeoTIFFs/
    ├── Chlorophyll/GeoTIFFs/
    ├── Θολότητα/GeoTIFFs/
    ├── Turbidity validated/code/GeoTIFFs/
    └── Πραγματικό/GeoTIFFs/
```

The folder names must match exactly (including Greek characters).
