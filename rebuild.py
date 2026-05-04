import subprocess
import sys
from pathlib import Path

BASE_PATH = Path(r"C:\Сторонние\АСУ_ПГР_(репо)")
AI_BOT_PATH = BASE_PATH / "tetepfgr" / "ai-bot"

print("=" * 60)
print("🔄 Rebuilding AI Bot with new code")
print("=" * 60)
print()

# Build
print("🔨 Building ai-bot image...")
result = subprocess.run(
    ["docker-compose", "build", "ai-bot"],
    cwd=str(AI_BOT_PATH),
    capture_output=False,
    text=True
)

if result.returncode != 0:
    print("❌ Build failed!")
    sys.exit(1)

print()
print("✅ Build successful!")
print()
print("🛑 Stopping containers...")
subprocess.run(
    ["docker-compose", "down"],
    cwd=str(AI_BOT_PATH),
    capture_output=False
)

print()
print("🚀 Starting containers...")
subprocess.run(
    ["docker-compose", "up", "-d"],
    cwd=str(AI_BOT_PATH),
    capture_output=False
)

print()
print("⏳ Waiting 25 seconds for startup...")
import time
time.sleep(25)

print()
print("=" * 60)
print("✅ Containers ready!")
print("=" * 60)
print()
print("Now run reindexing:")
print('Invoke-WebRequest -Uri "http://localhost:8000/api/index?mode=full" -Method POST -Headers @{"X-API-Key"="change-me-in-production"} -UseBasicParsing')
