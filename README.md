# Global Agronomy & Trade Intelligence System (GATIS)

GATIS is an enterprise-grade agricultural intelligence platform providing historical agronomic production analysis and advanced machine-learning projections. 

Developed utilizing a structured **Separation of Concerns** architecture, the platform houses robust data parsing pipelines, Huber loss robust regression models, and fully documented REST API endpoints.

---

## 🏗️ Technical Architecture

This repository has been refactored into a standardized, clean development structure:

```
GATIS/
├── app/
│   ├── api/             # REST controllers & path routing (FastAPI)
│   ├── services/        # Centralized agronomic & trade domain services
│   ├── models/          # Type safe payload validation (Pydantic schemas)
│   └── utils/           # Outlier robust CSV loader & data integrity tools
├── data/
│   ├── raw/             # Raw agronomic inputs
│   ├── processed/       # Sanitized and normalized historical crops
│   └── forecasts/       # Huber regression forecast output datasets
├── frontend/
│   ├── templates/       # Modular, clean HTML analytical interfaces
│   └── static/          # Shared semantic stylesheets
├── tests/               # Sequential unit and endpoint integration checks
├── README.md            # Enterprise engineering documentation
├── requirements.txt     # Python deployment dependencies
└── main.py              # Application entrypoint & lifespan managers
```

---

## 🚫 Critical Agronomic Rules

GATIS adheres strictly to real-world dataset limits and forecasting standards:

1. **Historical Records Window (<= 2023):** 
   - The latest actual observed historical year is strictly **2023**.
   - Any historical request for years after 2023 is explicitly blocked and returns a validation payload error.
2. **Forecast Window (2027–2031):**
   - Forecasting starts safely at **2027** and extends up to **2031**.
3. **Invalid Interval Isolation (2024–2026):**
   - Years **2024, 2025, and 2026** must not be populated in any timeline. 
   - These years are designated as invalid gaps and are prevented from leaking into calculations or UI selectors.

---

## 🔌 API Reference

### 1. Unified Options choices
* **Path:** `GET /api/options`
* **Response:** Collection of unique crops, countries, and permitted query years (excluding 2024–2026).

### 2. Crop market shares (Historical)
* **Path:** `GET /api/crop?name=Wheat&year=2020`
* **Response:** National production contributions sorted descending (market share percentages). Restricted strictly to `year <= 2023`.

### 3. Country Top Crops (Historical)
* **Path:** `GET /api/country/top-crops?country=India&year=2023&limit=10`
* **Response:** Sorted top crop listings. Restricted strictly to `year <= 2023`.

### 4. Consolidated Crop Timelines
* **Path:** `GET /api/country/crop-history?country=India&crop=Wheat`
* **Response:** Continuous historical + forecast timeline. Validated to ensure years 2024, 2025, and 2026 are never leaked.

### 5. Historical Choropleth Maps
* **Path:** `GET /map?crop=Wheat&year=2022`
* **Response:** Plotly-driven choropleth HTML markup visualizing production shares. Restricted strictly to `year <= 2023`.

---

## 🧪 Testing and Quality Control

Unit and integration tests reside in the `/tests` folder. Ensure environment requirements are installed, then execute:

```bash
python -m unittest discover tests/
```

Test coverage targets include:
- Zero leakage checks for forbidden gap years (2024–2026).
- Rejection verification for query requests of years after 2023 on historical endpoints.
- Basic API health and JSON schema conformity.
