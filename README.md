# CyberSentinel AI

CyberSentinel AI is a Kivy/KivyMD mobile application that acts as an AI-powered cybersecurity assistant. It supports online and offline Q&A, scheduled vulnerability scans (simulated for mobile), and persistent history with SQLite. The project is production-ready for Android packaging via Buildozer.

## Features

- Modern cyber-themed UI using KivyMD (dark mode, neon accents)
- Chatbot with a friendly professional "cyber" personality
- Offline AI Q&A powered by a lightweight local knowledge base (and optional GPT4All)
- Online AI support: OpenAI and HuggingFace Inference (easily extendable to IBM Watson / Microsoft Copilot)
- Persistent SQLite memory of chats and scan logs
- Unanswered queue stored offline; auto-answers once online
- Periodic device scan (simulated): detects and isolates threats, notifies the user
- User controls for scan schedule, approvals, and API keys
- Animated avatar and cyber grid background

## Project Structure

```
.
├── app
│   ├── backend
│   │   ├── ai_providers.py
│   │   ├── connectivity.py
│   │   ├── database.py
│   │   ├── persona.py
│   │   ├── scanner.py
│   │   └── scheduler.py
│   ├── main.py
│   └── ui
│       └── cybersentinel.kv
├── assets
│   ├── avatars
│   │   └── avatar.svg
│   └── icons
│       └── cybersentinel_icon.svg
├── data
│   └── local_knowledge_base.json
├── scripts
│   └── setup_db.py
├── buildozer.spec
├── requirements.txt
└── README.md
```

## Local Development

### 1) Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip wheel setuptools
pip install -r requirements.txt
```

### 2) Initialize the database (optional)

```bash
python scripts/setup_db.py
```

The app will auto-create tables on first run as well.

### 3) Run the app on desktop

```bash
python app/main.py
```

Notes:
- The UI, scanning, and storage all work on desktop for development.
- Offline answers use the local knowledge base. For a local LLM, optionally install `gpt4all` and place models according to its documentation.

## API Configuration

Open the Settings tab to set any available API keys. The app can use:
- OpenAI API (`OPENAI_API_KEY`)
- HuggingFace Inference API (`HUGGINGFACE_API_KEY`)

The app is architected to be extended to IBM Watson (watsonx) and Microsoft Copilot endpoints. You can add providers in `app/backend/ai_providers.py`.

## Android Build (Buildozer)

Ensure you have the Android SDK/NDK and Buildozer installed. On Ubuntu:

```bash
sudo apt update
sudo apt install -y python3-pip build-essential git zip unzip openjdk-17-jdk
pipx install buildozer
pipx ensurepath
# Or install via pip if preferred:
# pip install --user buildozer
```

Then build the APK:

```bash
cd /workspace
buildozer android debug
```

The first build can take a while. The output APK will be under `bin/`.

### Buildozer Spec Notes

- Requirements: `python3,kivy,kivymd,requests,schedule,psutil,pillow,numpy`
- Permissions: INTERNET, READ/WRITE EXTERNAL STORAGE (for demo isolation log)
- Orientation: portrait
- KV files are included automatically

If you plan to use GPT4All offline models on Android, you will need to:
- Add `gpt4all` and its dependencies to the buildozer `requirements`
- Bundle and load a small model that runs on-device (ensure size/performance fit)
- Adjust any necessary JNI/NDK options

## Security Disclaimer

This app simulates scanning and isolation for demonstration only. It does not perform invasive or privileged operations. Do not rely on it for real endpoint protection.

## Troubleshooting

- If the app fails to build on Android, try clearing the build cache:

```bash
buildozer android clean
```

- Ensure Java 17+ and recent SDK/NDK
- If OpenAI/HuggingFace requests time out, verify internet connectivity
- On desktop, window resizing may affect the animated grid; it is cosmetic only

## License

MIT
