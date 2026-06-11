import os
import logging

# Centralized Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

# Centralized Business Logic Constants - No hardcoded years anywhere else.
LAST_ACTUAL_YEAR: int = 2023
FORECAST_START_YEAR: int = 2027
FORECAST_END_YEAR: int = 2031

# Separate year providers
HISTORICAL_YEARS: list[int] = list(range(1961, LAST_ACTUAL_YEAR + 1))
FORECAST_YEARS: list[int] = list(range(FORECAST_START_YEAR, FORECAST_END_YEAR + 1))

# Allowed forecast range
ALLOWED_FORECAST_YEARS: set[int] = set(FORECAST_YEARS)

# Validation helper to detect invalid intermediate years (2024, 2025, 2026)
INVALID_YEARS: set[int] = {2024, 2025, 2026}

