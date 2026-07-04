from app.config import FORECAST_START_YEAR, FORECAST_END_YEAR, INVALID_YEARS

def test_crop_history_contains_no_forbidden_years(client):
    """Verifies that the merged timelines returned in /api/country/crop-history don't contain 2024, 2025, 2026."""
    response = client.get("/api/country/crop-history?country=India&crop=Wheat")
    assert response.status_code == 200
    
    data = response.json()
    assert "history" in data
    history_list = data["history"]
    
    years_present = [item["Year"] for item in history_list]
    
    # Omitted intermediate intermediate years MUST be absent
    for invalid_y in INVALID_YEARS:
        assert invalid_y not in years_present, f"Unified curves must not leak the forbidden intermediate year {invalid_y}"
        
    # Forecast years should be present if they fall inside allowed range
    expected_forecast_years = list(range(FORECAST_START_YEAR, FORECAST_END_YEAR + 1))
    for y in expected_forecast_years:
        assert y in years_present, f"Timeline should offer ML forecast for year {y}"
