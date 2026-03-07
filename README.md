# EduVerse AI Backend

## Setup

1. **Install `uv`** (if not installed):

```powershell
pip install uv
```

2. **Create a virtual environment**:

```powershell
uv venv .venv
```

3. **Activate the virtual environment**:

```powershell
.venv\Scripts\activate
```

> On Linux/macOS, use: `source .venv/bin/activate`

4. **Install project dependencies**:

```powershell
uv sync
```

---

## Run the App

Start the FastAPI server:

```powershell
uvicorn app.main:app --reload
```

Open your browser at [http://127.0.0.1:8000](http://127.0.0.1:8000) to see the app running.

---

## Notes

* Make sure you are in the project root (`EduVerse-AI-Backend-main`) when running Uvicorn.
* Keep `main.py` inside the `app/` folder for proper imports.
---