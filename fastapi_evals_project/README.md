# 📊 Evals Processor

A comprehensive evaluation system with FastAPI backend and Gradio frontend interface.

## 🚀 Quick Start

### Prerequisites
```bash
# Activate your virtual environment
source /Users/kshitij/Desktop/evals_experiment/venv/bin/activate

# Make sure you're in the project directory
cd /Users/kshitij/Desktop/evals_experiment/Evals/fastapi_evals_project
```

### Option 1: Run with Script (Recommended)
```bash
./start.sh
```

Or:
```bash
python run_app.py
```

This starts both the FastAPI backend and Gradio frontend automatically.

### Option 2: Run Separately (For Debugging)

**Terminal 1 - Backend:**
```bash
source /Users/kshitij/Desktop/evals_experiment/venv/bin/activate
cd /Users/kshitij/Desktop/evals_experiment/Evals/fastapi_evals_project
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 - Frontend:**
```bash
source /Users/kshitij/Desktop/evals_experiment/venv/bin/activate
cd /Users/kshitij/Desktop/evals_experiment/Evals/fastapi_evals_project
python gradio_interface.py
```

## 🌐 Access Points

Once running, open your browser to:
- **Gradio Interface:** http://localhost:7860
- **FastAPI Backend:** http://localhost:8000
- **API Documentation:** http://localhost:8000/docs

## 📋 Features

### 5 Main Workflows:

1. **📤 Upload Excel to Dataset** - Add Excel files to universal dataset
2. **✍️ Add Manual Entry** - Add individual records via text fields
3. **👁️ View Dataset** - Display all accumulated data
4. **⚙️ Process Dataset** - Run evaluation pipeline on universal dataset
5. **⚡ Quick Process** - Upload and process immediately (bypasses dataset)

## 📂 Project Structure

```
fastapi_evals_project/
├── main.py                 # FastAPI entry point
├── gradio_interface.py     # Gradio UI
├── run_app.py             # Unified launcher
├── start.sh               # Bash launcher
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
├── app/
│   ├── api/
│   │   ├── controllers/   # Business logic
│   │   └── routes/        # API endpoints
│   ├── core/
│   │   └── config.py      # Configuration
│   ├── models/
│   │   └── schema.py      # Pydantic models
│   └── services/
│       ├── data_store.py  # Universal dataset storage
│       ├── evals_service.py
│       ├── feedback_service.py
│       └── transcript_client.py
└── outputs/               # Generated files
    ├── universal_dataset.xlsx
    └── *_evaluated.xlsx
```

## 🔧 Configuration

### Environment Variables
Edit `.env` file:
```bash
# OpenAI Configuration (if needed)
OPENAI_API_KEY=your-key-here
```

### Data Format
Excel files should contain these columns:
- `client_code`
- `transcript`
- `lead_data`
- `latest_message`
- `expected_output`

## 🛠️ Troubleshooting

### Backend won't start
1. Check if port 8000 is available:
   ```bash
   lsof -i :8000
   ```
2. If occupied, kill the process or change port in code

### Frontend won't start
1. Check if port 7860 is available:
   ```bash
   lsof -i :7860
   ```
2. Check if gradio is installed:
   ```bash
   pip install gradio
   ```

### Connection refused errors
1. Make sure backend starts first
2. Wait a few seconds before accessing frontend
3. Check backend logs for errors

### Module not found errors
```bash
pip install -r requirements.txt
```

## 📊 API Endpoints

### Core Routes:
- `POST /api/evals/upload` - Upload & process Excel (original)
- `POST /api/evals/read-excel` - Add Excel to dataset
- `POST /api/evals/text-fields` - Add manual entry
- `GET /api/evals/display_data_set` - View dataset
- `POST /api/evals/process_universal_dataset` - Process dataset

See full documentation at: http://localhost:8000/docs

## 📖 Detailed Guide

See `GRADIO_GUIDE.md` for complete usage instructions and workflows.

## 🔍 Development

### Run tests
```bash
python test_backend.py
```

### View logs
Backend and frontend logs will display in the terminal when using `run_app.py`.

---

**Built with:** FastAPI, Gradio, Pandas, OpenPyXL

