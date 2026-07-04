from app.config import LAST_ACTUAL_YEAR, INVALID_YEARS, HISTORICAL_YEARS, FORECAST_YEARS

def test_health_endpoint(client):
    """Verifies health check returns healthy status code."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_template_rendering_routes(client):
    """Verifies that all page routes serve HTML successfully."""
    routes = ["/", "/country", "/forecast", "/map"]
    for r in routes:
        response = client.get(r)
        assert response.status_code == 200, f"Route {r} failed to load"
        assert "text/html" in response.headers["content-type"], f"Route {r} did not return HTML"

def test_options_contains_correct_year_providers(client):
    """Validates that options has distinct, correct historical and forecast lists and no leak of 2024-2026."""
    response = client.get("/api/options")
    assert response.status_code == 200
    data = response.json()
    
    assert "historical_years" in data
    assert "forecast_years" in data
    
    h_years = data["historical_years"]
    f_years = data["forecast_years"]
    
    # Ranges check
    assert min(h_years) == 1961
    assert max(h_years) == 2023
    assert min(f_years) == 2027
    assert max(f_years) == 2031
    
    # Excluded years must never leak
    for invalid_y in INVALID_YEARS:
        assert invalid_y not in h_years, f"{invalid_y} leaked in historical years list"
        assert invalid_y not in f_years, f"{invalid_y} leaked in forecast years list"
        assert invalid_y not in data.get("years", []), f"{invalid_y} leaked in years list"

def test_crop_rejection_for_invalid_years(client):
    """Ensures that /api/crop endpoint rejects invalid years and accepts historical and forecast years."""
    # 1. Invalid years should be rejected
    for test_year in [2024, 2025, 2026, 1960, 2035]:
        response = client.get(f"/api/crop?name=Wheat&year={test_year}")
        assert response.status_code == 400

    # 2. Forecast year should succeed
    response = client.get("/api/crop?name=Wheat&year=2030")
    assert response.status_code == 200
    data = response.json()
    assert data["crop"] == "Wheat"
    assert data["year"] == 2030
    assert len(data["data"]) > 0

def test_historical_top_crops_rejection_greater_than_2023(client):
    """Ensures that historical /api/country/top-crops endpoint rejects queries > 2023."""
    for test_year in [2024, 2025, 2027, 2030]:
        response = client.get(f"/api/country/top-crops?country=India&year={test_year}")
        assert response.status_code == 400
        assert "Historical endpoints only support year <= 2023" in response.json()["detail"]

def test_valid_historical_crop_query(client):
    """Checks if normal query with years <= 2023 returns successful payload."""
    response = client.get("/api/crop?name=Wheat&year=2020")
    assert response.status_code == 200
    data = response.json()
    assert data["crop"] == "Wheat"
    assert data["year"] == 2020
    assert len(data["data"]) > 0

def test_map_embed_validation(client):
    """Checks that the map embed endpoint allows historical and forecast years but rejects 2024-2026."""
    # 1. Valid historical year
    response = client.get("/map/embed?crop=Wheat&year=2020")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    
    # 2. Valid forecast year
    response = client.get("/map/embed?crop=Wheat&year=2030")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    
    # 3. Invalid years
    for y in INVALID_YEARS:
        response = client.get(f"/map/embed?crop=Wheat&year={y}")
        assert response.status_code == 400

def test_html_redirects(client):
    """Verifies that requests to .html routes are redirected to their clean routes."""
    redirect_map = {
        "/index.html": "/",
        "/country.html": "/country",
        "/forecast.html": "/forecast",
        "/map.html": "/map",
        "/frontend/templates/index.html": "/",
        "/frontend/templates/country.html": "/country",
        "/frontend/templates/forecast.html": "/forecast",
        "/frontend/templates/map.html": "/map"
    }
    for path, target in redirect_map.items():
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 301
        assert response.headers["location"] == target

def test_static_file_serving(client):
    """Checks if static files (shared.css) are served correctly with 200 OK."""
    response = client.get("/static/shared.css")
    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]
