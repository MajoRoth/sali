import json
from main import app

with open("../openapi/supermarkets_openapi.json", "w") as f:
    json.dump(app.openapi(), f, indent=2)
