# 🤖 AI Interview System

An intelligent interview platform that conducts automated job interviews using AI. The system analyzes candidate resumes, asks relevant questions, and provides detailed feedback and scoring.

## ✨ Features

- **Resume Analysis**: Upload your PDF resume and get key highlights extracted automatically
- **Personalized Questions**: AI generates interview questions based on your resume and the job description
- **Voice Interaction**: Speak your answers naturally - the system will transcribe and analyze them
- **Real-time Chat**: Beautiful chat interface showing the conversation flow
- **Video Feeds**: See yourself and the AI interviewer during the interview
- **Intelligent Scoring**: Get detailed feedback and scores for each answer
- **Complete Evaluation**: Receive an overall interview score and comprehensive report

## 🚀 Tech Stack

### Backend
- **FastAPI**: Modern Python web framework
- **OpenAI GPT-4o mini**: For AI question generation and analysis
- **OpenAI Whisper**: For speech-to-text transcription

### Frontend
- **React**: UI library
- **Vite**: Build tool
- **Modern CSS**: Beautiful, responsive design

## 📋 Prerequisites

- Python 3.8+
- Node.js 16+
- OpenAI API key
- Microphone and camera access

## 🛠️ Setup Instructions

### 1. Backend Setup

```bash
# Navigate to project directory
cd AI-Interview-System

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Edit .env and add your API keys
# OPENAI_API_KEY=your_actual_api_key_here
# SPEECHMATICS_API_KEY=your_speechmatics_api_key_here
```

### 2. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install
```

### 3. Running the Application

#### Start Backend (Terminal 1)

```bash
# From project root
python api.py
# Or using uvicorn directly:
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

The backend will run on `http://localhost:8000`

#### Start Frontend (Terminal 2)

```bash
# From frontend directory
cd frontend
npm run dev
```

The frontend will run on `http://localhost:3000`

## 🎯 How to Use

1. **Upload Resume**: 
   - Go to `http://localhost:3000`
   - Upload your PDF resume
   - Paste the job description
   - Configure interview settings (max questions, AI voice)
   - Click "Submit"

2. **Start Interview**:
   - Click "Start Interview" button
   - Allow camera and microphone access when prompted

3. **Answer Questions**:
   - Listen to or read each question
   - Click the microphone button to record your answer
   - Or type your answer in the text input
   - Click send or stop recording when done

4. **Review Results**:
   - After completing all questions, view your feedback
   - See your overall score and detailed evaluation

## 📁 Project Structure

```
AI-Interview-System/
├── api.py                 # FastAPI backend server
├── frontend/              # React frontend
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── App.jsx        # Main app component
│   │   └── main.jsx       # Entry point
│   └── package.json
├── utils/                 # Utility functions
│   ├── llm_call.py        # OpenAI LLM integration
│   ├── transcript_audio.py # Whisper transcription
│   ├── analyze_candidate.py # Interview analysis
│   └── ...
├── requirements.txt       # Python dependencies
└── README.md
```

## 🔧 API Endpoints

- `POST /api/upload-resume` - Upload resume and create session
- `POST /api/start-interview` - Start interview session
- `POST /api/transcribe-audio` - Transcribe audio file
- `POST /api/process-answer` - Process candidate answer and get next question
- `GET /api/interview-status/{session_id}` - Get interview status
- `GET /api/interview-results/{session_id}` - Get final results

## 🎨 Interface Features

- **Left Panel**: Chat interface with conversation history
- **Right Panel**: Video feeds showing candidate and interviewer
- **Timer**: Real-time interview timer
- **Recording Indicator**: Visual feedback when recording
- **Responsive Design**: Works on different screen sizes

## 🔐 Environment Variables

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_openai_api_key_here
LLM_MODEL=gpt-4o-mini
```

## 📝 Notes

- Make sure both backend and frontend are running
- The backend API runs on port 8000
- The frontend runs on port 3000
- Camera and microphone permissions are required
- Chrome browser is recommended for best audio recording experience

## 🐛 Troubleshooting

**Backend not starting:**
- Check if port 8000 is available
- Verify Python virtual environment is activated
- Ensure all dependencies are installed

**Frontend not connecting:**
- Verify backend is running on port 8000
- Check browser console for errors
- Ensure CORS is properly configured

**Audio recording issues:**
- Grant microphone permissions in browser
- Use Chrome browser for best compatibility
- Check browser console for errors

## 📄 License

This project is open source and available for educational purposes.

---

*Ready to ace your next interview? Upload your resume and get started!*
