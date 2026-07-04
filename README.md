# Global Agronomy & Trade Intelligence System (GATIS)

GATIS is an enterprise-grade agricultural intelligence platform that parses, cleans, and forecasts global crop production data. It leverages a dataset of **1.1 million rows of historical FAOSTAT records** (1961–2023) covering **203 countries** and **280 crops** to deliver interactive global market share visualizations and outlier-robust machine learning forecasts through 2031.

---

## 📖 Table of Contents
1. [Core Features](#-core-features)
2. [Agronomic Logic & Business Rules](#-agronomic-logic--business-rules)
3. [Technical Architecture](#-technical-architecture)
4. [Memory Optimization Deep Dive](#-memory-optimization-deep-dive)
5. [Forecasting Methodology](#-forecasting-methodology)
6. [Getting Started (Local & Docker)](#-getting-started-local--docker)
7. [API Reference Documentation](#-api-reference-documentation)
8. [Testing & Quality Control](#-testing--quality-control)

---

## ✨ Core Features

* **Interactive Choropleth Maps:** Plotly-driven global maps showing country production shares dynamically.
* **SVG Timeline Renderers:** Fast, lightweight custom SVG timelines built with vanilla JavaScript on the frontend.
* **Country Agricultural Profiles:** Ranked crop production tables and detailed metrics (historical peaks, units, shares) for any country.
* **Outlier-Robust Projections:** Dynamic machine learning forecasts that handle crop volatility and weather anomalies.
* **FastAPI Backend:** Clean, modular API routes with Pydantic type checking.

---

## 🚫 Agronomic Logic & Business Rules

GATIS implements strict real-world agricultural constraints to maintain database and mathematical integrity:

1. **Observed Historical Window (<= 2023):** 
   - Historical records are bounded by the year **2023**.
   - API endpoints serving historical metrics reject queries for years greater than 2023.
2. **Allowed Forecast Window (2027–2031):**
   - Machine learning projections are available strictly from **2027** to **2031**.
3. **Invalid Interval Isolation (2024–2026):**
   - Years **2024, 2025, and 2026** are designated as invalid gap years.
   - The data loader, backend services, and frontend UI selectors omit these years to prevent timeline leaks.

---

## 🏗️ Technical Architecture

The project is designed with a strict **Separation of Concerns (SoC)** model:

```
GATIS/
├── app/
│   ├── api/             # FastAPI routing controllers & page rendering endpoints
│   ├── services/        # Centralized business logic (crop and market share calculations)
│   ├── models/          # Type-safe validation schemas using Pydantic
│   ├── utils/           # Optimized CSV loaders and startup database routines
│   └── config.py        # Centralized business logic constants & logging setups
├── data/
│   ├── raw/             # Raw agronomic inputs
│   ├── processed/       # Sanitized historical crop database (cleaned_faostat.csv)
│   └── forecasts/       # Huber regression forecast output database (forecast_results.csv)
├── frontend/
│   ├── templates/       # Modular, clean HTML analytical interfaces
│   └── static/          # Shared semantic styles and scripts
├── tests/               # Backend endpoint integration & validation checks
├── requirements.txt     # Python production dependencies
└── main.py              # Server lifespans manager & entry point
```

---

## ⚡ Memory Optimization Deep Dive

Deploying GATIS to standard cloud platforms (such as Render's free tier) requires operating within a strict **512 MB memory limit**.

Initially, loading the raw CSV files (`cleaned_faostat.csv` ~89MB and `forecast_results.csv` ~19MB) into memory using standard Pandas configurations caused memory usage to climb to **over 428 MB**. Combined with package startup overhead (Plotly, FastAPI, Scikit-learn), this regularly triggered Out of Memory (OOM) crashes (502 Bad Gateway).

### The Solution: Categorical Typing
In `app/utils/data_loader.py`, high-cardinality string columns are explicitly cast to Pandas `category` types at read-time:

```python
CATEGORICAL_COLS = {
    "Area": "category",
    "Item Code (CPC)": "category",
    "Item": "category",
    "Element": "category",
    "Unit": "category",
    "ISO3": "category",
    "Area Code (M49)": "category"
}

df_hist = pd.read_csv(DATA_FILE, dtype=CATEGORICAL_COLS)
```

**Results:**
* **Memory footprint reduced by 90%** (RAM usage dropped from **428.22 MB** to **47.74 MB**).
* **1.0 second faster** test suite execution times due to accelerated category comparisons.
* Plentiful memory overhead running on Render's standard resource allocation.

---

## 🔮 Forecasting Methodology

Crop yields are highly volatile and subject to major weather events, resulting in extreme outlier years. Standard linear regression models are easily skewed by these anomalies, resulting in unrealistic predictions.

To solve this, GATIS utilizes an outlier-robust pipeline:
1. **Model:** A `HuberRegressor` (Huber loss robust regression with L2 Ridge regularization) is fit for each individual country-crop pair.
2. **Features:** Time features are mapped using **degree-2 polynomial transforms** to capture gentle curvatures in productivity changes without overfitting.
3. **Constraints:** The model log-transforms production values for training and clips negative output predictions, keeping the 2027–2031 projections realistic and non-negative.

---

## 🚀 Getting Started

### Option 1: Running Locally (Python)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/adityacoddes/GATIS-Global-Trade-Intelligence.git
   cd GATIS-Global-Trade-Intelligence
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the server:**
   ```bash
   python main.py
   ```
   The backend will bootstrap, load the datasets, and serve the application on [http://localhost:8000](http://localhost:8000).

### Option 2: Running with Docker

1. **Build the image:**
   ```bash
   docker build -t gatis .
   ```

2. **Run the container:**
   ```bash
   docker run -d -p 8000:8000 --name gatis_app gatis
   ```
   Access the application in your browser at [http://localhost:8000](http://localhost:8000).

---

## 🔌 API Reference Documentation

### 1. Retrieve UI Field Options
* **Path:** `GET /api/options`
* **Description:** Returns the complete list of unique countries, crops, and permitted historical/forecast years (excluding 2024–2026).
* **Sample Response:**
  ```json
  {
    "default_crop": "Wheat",
    "default_country": "India",
    "default_year": 2023,
    "crops": ["Wheat", "Maize", "Rice", "..."],
    "countries": ["India", "United States", "China", "..."],
    "years": [2031, 2030, 2029, 2028, 2027, 2023, 2022, "..."],
    "historical_years": [1961, 1962, "...", 2023],
    "forecast_years": [2027, 2028, 2029, 2030, 2031]
  }
  ```

### 2. Global Crop Market Share
* **Path:** `GET /api/crop?name={crop_name}&year={year}`
* **Description:** Retrieves the national market share breakdown for a specific crop in a historical or forecast year.
* **Sample Response:**
  ```json
  {
    "crop": "Wheat",
    "year": 2023,
    "data": [
      { "Area Code (M49)": "156", "Area": "China", "Percentage_Share": 17.5 },
      { "Area Code (M49)": "356", "Area": "India", "Percentage_Share": 13.8 }
    ]
  }
  ```

### 3. Country Top Crops
* **Path:** `GET /api/country/top-crops?country={country_name}&year={year}&limit={limit}`
* **Description:** Returns ranked agricultural contributions for a specific country and historical year.
* **Sample Response:**
  ```json
  {
    "country_query": "India",
    "matched_countries": ["India"],
    "year": 2023,
    "total_records": 10,
    "total_production": 350000000.0,
    "top_crops": [
      { "Rank": 1, "Area": "India", "Item": "Rice", "Production_Value": 135000000.0, "Unit": "t", "Country_Share": 38.5 }
    ]
  }
  ```

### 4. Consolidated Crop Timelines
* **Path:** `GET /api/country/crop-history?country={country_name}&crop={crop_name}`
* **Description:** Returns continuous production timeline combined from historical data and ML predictions, excluding gap years.
* **Sample Response:**
  ```json
  {
    "country_query": "India",
    "matched_countries": ["India"],
    "crop": "Wheat",
    "first_year": 1961,
    "latest_year": 2023,
    "latest_production": 110000000.0,
    "latest_unit": "t",
    "peak_year": 2023,
    "peak_production": 110000000.0,
    "peak_unit": "t",
    "history": [
      { "Year": 1961, "Area": "India", "Item": "Wheat", "Production_Value": 1100000.0, "Unit": "t" },
      { "Year": 2023, "Area": "India", "Item": "Wheat", "Production_Value": 110000000.0, "Unit": "t" },
      { "Year": 2027, "Area": "India", "Item": "Wheat", "Production_Value": 115000000.0, "Unit": "t" }
    ]
  }
  ```

---

## 🧪 Testing & Quality Control

The project includes unit and integration tests under the `/tests` folder. The tests verify zero gap-year leakage (2024–2026), correct historical limits, and JSON endpoint schema conformity.

Run the tests locally:
```bash
python -m unittest discover tests/
```

**Test Scenarios Covered:**
* **Zero Leakage Checks:** Ensures that gap years (2024–2026) are never returned in timelines.
* **Historical Isolation:** Confirms that querying historical endpoints with years > 2023 throws validation payload errors.
* **Redirect Integrity:** Validates that legacy static page URLs (e.g. `/country.html`) are redirected to the clean routing endpoints (`/country`).
* **API Health & Conformity:** Validates health statuses and schema conformity on options and map endpoints.
