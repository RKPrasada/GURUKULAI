# Contributing to VidyaBot

## Quickstart
```bash
git clone https://github.com/[username]/vidyabot && cd vidyabot
pip install -r requirements.txt && cp .env.example .env
# Fill: GEMINI_API_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
# Generate ENCRYPTION_KEY:
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Start the API + Frontend
```bash
# Option 1: Use the launcher (opens browser automatically)
python launcher.py

# Option 2: Start separately
uvicorn api.main:app --reload --port 8000 &
cd web && npm run dev              # → http://localhost:3000
```

## Evals
```bash
pytest evals/ -v                   # all
pytest evals/test_security.py -v  # security only
python -m evals.eval_runner        # summary report
```

## Demo
```bash
python launcher.py                 # → http://localhost:3000
```

## Security smoke test
```bash
python -c "
from security.injection_detector import InjectionDetector; import json
d = InjectionDetector()
for c in json.load(open('data/demo/security_test_cases.json'))['injection_attempts']:
    print(f'[{\"PASS\" if d.detect(c[\"input\"]) else \"FAIL\"}] {c[\"id\"]}: {c[\"input\"][:55]}')
"
```

## Flutter Mobile App
```bash
cd mobile_app
flutter pub get
flutter run                       # Android/iOS emulator
flutter build apk                 # Android APK
flutter build ios                 # iOS (requires Xcode on macOS)
```

## Desktop Build
```bash
# macOS
bash packaging/build_mac.sh

# Linux
bash packaging/build_linux.sh

# Windows
packaging\build_windows.bat
```

## Style
```bash
ruff check . && black .   # both run in CI
```

## Project structure
See `docs/architecture.md` for full architecture diagram.
