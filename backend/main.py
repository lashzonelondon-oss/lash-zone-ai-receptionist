# build-bump: 1780305982087
"""
Lash Zone London AI Receptionist - Entry Point
Railway deployment entry point for FastAPI app
"""
import os
import sys

# Add the backend directory to path so 'app' package is importable
sys.path.insert(0, os.path.dirname(__file__))

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.api.routes:app", host="0.0.0.0", port=port, reload=False)

# redeploy 1780305014333
