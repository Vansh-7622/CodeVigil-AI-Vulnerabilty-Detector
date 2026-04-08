# CodeVigil Backend - Render Deployment

## Steps:
## 1. Go to render.com → New → Web Service
## 2. Connect your GitHub repo
## 3. Use these settings:

# Name: codevigil-api
# Root Directory: backend
# Runtime: Python 3
# Build Command: pip install -r requirements.txt
# Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
# Instance Type: Free

## 4. Add Environment Variable:
##    Key: GROQ_API_KEY
##    Value: (your Groq API key)
