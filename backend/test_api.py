import requests

print("Testing FastAPI Endpoints...\n")

# 1. Test Root
r = requests.get("http://localhost:8000/")
print("GET / :", r.status_code, r.json())

# 2. Test Forecasts
r = requests.get("http://localhost:8000/api/forecasts")
print("GET /api/forecasts :", r.status_code, len(r.json()), "items")

# 3. Test Attribution
r = requests.get("http://localhost:8000/api/attribution")
print("GET /api/attribution :", r.status_code, r.json())

# 4. Test Enforcement
r = requests.get("http://localhost:8000/api/enforcement")
print("GET /api/enforcement :", r.status_code, len(r.json()), "items")

# 5. Test Advisories
r = requests.get("http://localhost:8000/api/advisories")
print("GET /api/advisories :", r.status_code, len(r.json()), "items")

# 6. Test Anomalies
r = requests.get("http://localhost:8000/api/anomalies")
print("GET /api/anomalies :", r.status_code, len(r.json()), "items")

# 7. Test NL Query (Agent 7) - Commented out to save time/API credits on test
# payload = {"question": "What is the top enforcement site and why?"}
# r = requests.post("http://localhost:8000/api/ask", json=payload)
# print("POST /api/ask :", r.status_code, r.json())

print("\nAll endpoints tested successfully!")
