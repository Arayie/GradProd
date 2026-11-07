# STEP-BY-STEP GUIDE: BACKEND ON RENDER & FRONTEND ON STREAMLIT CLOUD
**Repository:** `https://github.com/Arayie/GradProd.git`  
**Architecture:**  
- **Backend (Render):** Managed PostgreSQL Database + Optional Python Backend API  
- **Frontend (Streamlit Cloud):** Interactive 16-page Research Discovery Engine  

---

## PART 1: SETUP BACKEND ON RENDER (POSTGRESQL DATABASE)

Render hosts the persistent database that stores all 3,798 customer reviews, 1,532 AI evidence records, and 7 ranked opportunities.

### Step 1: Create PostgreSQL Database on Render
1. Go to [dashboard.render.com](https://dashboard.render.com/) and sign in with your GitHub account.
2. Click the blue **New +** button in the top right and select **PostgreSQL**.
3. Fill in the database details:
   - **Name:** `growww-db`
   - **Database:** `growww_discovery`
   - **User:** `growww_user`
   - **Region:** Oregon (US West) or Frankfurt (choose nearest)
   - **Plan:** **Free** (or Starter)
4. Click **Create Database**.

### Step 2: Copy the External Connection String
1. Wait ~30 seconds until the database status turns to **Available**.
2. Scroll down to **Connections**.
3. Locate **External Database URL** (it looks like `postgresql://growww_user:PASSWORD@dpg-xxxxxx.oregon-postgres.render.com/growww_discovery`).
4. Click the **Copy** icon next to **External Database URL**.

### Step 3: Populate the Render Database (One Command)
In your local terminal inside `/Users/aradhyayadav/Downloads/GradProd`, run the automated migration command (replace `<EXTERNAL_DATABASE_URL>` with your copied string):

```bash
PYTHONPATH=.:./lib python3 scripts/migrate_sqlite_to_postgres.py \
    --pg-url "<EXTERNAL_DATABASE_URL>"
```

*(Alternatively, if you have `psql` installed: `psql "<EXTERNAL_DATABASE_URL>" -f data/growww_discovery_postgres.sql`)*

This loads all tables, indexes, constraints, 3,798 reviews, and 7 opportunities into Render PostgreSQL.

---

## (OPTIONAL) PART 1B: DEPLOY PYTHON BACKEND SERVICE ON RENDER

If you also want a live REST backend service running on Render (for health checks, JSON API endpoints, and scheduled review refresh):

1. On Render Dashboard, click **New +** -> **Web Service**.
2. Select your GitHub repository: `Arayie/GradProd`.
3. Configure the service:
   - **Name:** `growww-backend-api`
   - **Runtime:** `Python`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python3 api_backend.py`
   - **Plan:** **Free**
4. Under **Environment Variables**, add:
   - `DATABASE_URL`: paste your Render External (or Internal) Database URL
   - `APP_ENV`: `production`
5. Click **Create Web Service**.

Render will deploy your backend API at `https://growww-backend-api.onrender.com/healthz`.

---

## PART 2: SETUP FRONTEND ON STREAMLIT COMMUNITY CLOUD

Streamlit Community Cloud hosts the user-facing web dashboard and connects securely to Render.

### Step 1: Go to Streamlit Community Cloud
1. Open [share.streamlit.io](https://share.streamlit.io/) in your browser.
2. Sign in with the same GitHub account (`Arayie`).

### Step 2: Deploy New App
1. Click **Create app** (or **New app** button in the top right).
2. Choose **"I already have an app"**.
3. Fill in the repository details:
   - **Repository:** `Arayie/GradProd`
   - **Branch:** `main`
   - **Main file path:** `app.py`
   - **App URL:** Customize if desired (e.g. `growww-investor-discovery.streamlit.app`)

### Step 3: Configure Database URL & Secrets
1. Before clicking deploy, expand **Advanced settings...** (or click **Settings** -> **Secrets**):
2. In the **Secrets** text box, paste the following configuration:

```toml
# Render PostgreSQL Database Connection String
DATABASE_URL = "postgresql://growww_user:YOUR_RENDER_PASSWORD@dpg-xxxxx.oregon-postgres.render.com/growww_discovery"

# Production Access Configuration
REQUIRE_AUTH = "true"
ADMIN_PASSWORD = "Admin@Growww2026!"
RESEARCHER_PASSWORD = "Research@Growww2026!"
VIEWER_PASSWORD = "Viewer@Growww2026!"
AUDITOR_PASSWORD = "Auditor@Growww2026!"
```

*(Note: If you ever deploy without setting `DATABASE_URL`, the app automatically falls back to the embedded SQLite database `growww_discovery.db` that is already committed in your repo!)*

### Step 4: Click Deploy!
1. Click the **Deploy!** button.
2. Streamlit Cloud will display the build logs as it installs packages from `requirements.txt`.
3. In ~60 to 90 seconds, your app will be live on the web!

---

## PART 3: LOGGING IN & USING YOUR APPLICATION

Once deployed on Streamlit Cloud:
1. Navigate to your app URL.
2. Enter your credentials on the private gateway:
   - **Username:** `researcher`  
   - **Password:** `Research@Growww2026!`  
   *(or `admin` / `Admin@Growww2026!`)*
3. You now have the complete 16-page Growww AI-Powered Investor Discovery Engine running 24/7 on the cloud!
