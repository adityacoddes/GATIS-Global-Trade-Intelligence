import unittest
from fastapi.testclient import TestClient
from main import app
from app.config import LAST_ACTUAL_YEAR, INVALID_YEARS, HISTORICAL_YEARS, FORECAST_YEARS

class TestGatisAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_endpoint(self):
        """Verifies health check returns healthy status code."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "healthy")

    def test_template_rendering_routes(self):
        """Verifies that all page routes serve HTML successfully."""
        routes = ["/", "/country", "/forecast", "/map"]
        for r in routes:
            response = self.client.get(r)
            self.assertEqual(response.status_code, 200, f"Route {r} failed to load")
            self.assertIn("text/html", response.headers["content-type"], f"Route {r} did not return HTML")

    def test_options_contains_correct_year_providers(self):
        """Validates that options has distinct, correct historical and forecast lists and no leak of 2024-2026."""
        response = self.client.get("/api/options")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn("historical_years", data)
        self.assertIn("forecast_years", data)
        
        h_years = data["historical_years"]
        f_years = data["forecast_years"]
        
        # Ranges check
        self.assertEqual(min(h_years), 1961)
        self.assertEqual(max(h_years), 2023)
        self.assertEqual(min(f_years), 2027)
        self.assertEqual(max(f_years), 2031)
        
        # Excluded years must never leak
        for invalid_y in INVALID_YEARS:
            self.assertNotIn(invalid_y, h_years, f"{invalid_y} leaked in historical years list")
            self.assertNotIn(invalid_y, f_years, f"{invalid_y} leaked in forecast years list")
            self.assertNotIn(invalid_y, data.get("years", []), f"{invalid_y} leaked in years list")

    def test_crop_rejection_for_invalid_years(self):
        """Ensures that /api/crop endpoint rejects invalid years and accepts historical and forecast years."""
        # 1. Invalid years should be rejected
        for test_year in [2024, 2025, 2026, 1960, 2035]:
            response = self.client.get(f"/api/crop?name=Wheat&year={test_year}")
            self.assertEqual(response.status_code, 400)

        # 2. Forecast year should succeed
        response = self.client.get("/api/crop?name=Wheat&year=2030")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["crop"], "Wheat")
        self.assertEqual(data["year"], 2030)
        self.assertGreater(len(data["data"]), 0)

    def test_historical_top_crops_rejection_greater_than_2023(self):
        """Ensures that historical /api/country/top-crops endpoint rejects queries > 2023."""
        for test_year in [2024, 2025, 2027, 2030]:
            response = self.client.get(f"/api/country/top-crops?country=India&year={test_year}")
            self.assertEqual(response.status_code, 400)
            self.assertIn("Historical endpoints only support year <= 2023", response.json()["detail"])

    def test_valid_historical_crop_query(self):
        """Checks if normal query with years <= 2023 returns successful payload."""
        response = self.client.get("/api/crop?name=Wheat&year=2020")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["crop"], "Wheat")
        self.assertEqual(data["year"], 2020)
        self.assertGreater(len(data["data"]), 0)

    def test_map_embed_validation(self):
        """Checks that the map embed endpoint allows historical and forecast years but rejects 2024-2026."""
        # 1. Valid historical year
        response = self.client.get("/map/embed?crop=Wheat&year=2020")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        
        # 2. Valid forecast year
        response = self.client.get("/map/embed?crop=Wheat&year=2030")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        
        # 3. Invalid years
        for y in INVALID_YEARS:
            response = self.client.get(f"/map/embed?crop=Wheat&year={y}")
            self.assertEqual(response.status_code, 400)

if __name__ == "__main__":
    unittest.main()
