import unittest
from fastapi.testclient import TestClient
from main import app
from app.config import FORECAST_START_YEAR, FORECAST_END_YEAR, INVALID_YEARS

class TestGatisForecast(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_crop_history_contains_no_forbidden_years(self):
        """Verifies that the merged timelines returned in /api/country/crop-history don't contain 2024, 2025, 2026."""
        response = self.client.get("/api/country/crop-history?country=India&crop=Wheat")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("history", data)
        history_list = data["history"]
        
        years_present = [item["Year"] for item in history_list]
        
        # Omitted intermediate intermediate years MUST be absent
        for invalid_y in INVALID_YEARS:
            self.assertNotIn(invalid_y, years_present, f"Unified curves must not leak the forbidden intermediate year {invalid_y}")
            
        # Forecast years should be present if they fall inside allowed range
        expected_forecast_years = list(range(FORECAST_START_YEAR, FORECAST_END_YEAR + 1))
        for y in expected_forecast_years:
            self.assertIn(y, years_present, f"Timeline should offer ML forecast for year {y}")

if __name__ == "__main__":
    unittest.main()
