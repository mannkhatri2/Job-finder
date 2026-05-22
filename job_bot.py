from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import requests
import os

app = Flask(__name__)

# =========================
# API KEYS
# =========================

RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")
HF_API_TOKEN = os.environ.get("HF_API_TOKEN")

HF_API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"

# =========================
# SIMPLE MEMORY
# =========================

user_states = {}

# =========================
# HUGGING FACE AI
# =========================

def ask_free_ai(prompt):

    if not HF_API_TOKEN:
        return "⚠️ Hugging Face token missing."

    headers = {
        "Authorization": f"Bearer {HF_API_TOKEN}"
    }

    formatted_prompt = f"""
<s>[INST]
You are a concise AI Career Coach on WhatsApp.

Give:
- short answers
- actionable advice
- friendly tone
- bullet points

User request:
{prompt}
[/INST]
"""

    payload = {
        "inputs": formatted_prompt,
        "parameters": {
            "max_new_tokens": 250,
            "temperature": 0.5,
            "return_full_text": False
        }
    }

    try:
        response = requests.post(
            HF_API_URL,
            headers=headers,
            json=payload,
            timeout=20
        )

        response.raise_for_status()

        result = response.json()

        if isinstance(result, list) and len(result) > 0:
            return result[0].get("generated_text", "").strip()

        return "⚠️ AI couldn't generate a response."

    except requests.exceptions.Timeout:
        return (
            "⚠️ AI coach is currently busy.\n\n"
            "Please try again in 20 seconds."
        )

    except Exception as e:
        print("HF ERROR:", e)

        return (
            "⚠️ AI service temporarily unavailable.\n\n"
            "Please try again shortly."
        )

# =========================
# JOB SEARCH
# =========================

def fetch_jobs(query):

    url = "https://jsearch.p.rapidapi.com/search"

    querystring = {
        "query": query,
        "page": "1",
        "num_pages": "1"
    }

    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }

    try:

        response = requests.get(
            url,
            headers=headers,
            params=querystring,
            timeout=5
        )

        response.raise_for_status()

        data = response.json()

        jobs = data.get("data", [])

        if not jobs:
            return (
                f"❌ No active jobs found for:\n"
                f"'{query}'"
            )

        result_text = "🎯 *Top Matches For You:*\n\n"

        for job in jobs[:2]:

            title = job.get("job_title", "Role")
            employer = job.get("employer_name", "Company")

            city = job.get("job_city", "")
            country = job.get("job_country", "")

            location_parts = [
                part for part in [city, country] if part
            ]

            location = (
                ", ".join(location_parts)
                if location_parts
                else "Remote 🏠"
            )

            apply_link = job.get(
                "job_apply_link",
                "No link"
            )

            result_text += (
                f"*{title}*\n"
                f"🏢 {employer}\n"
                f"📍 {location}\n"
                f"🔗 {apply_link}\n\n"
            )

        result_text += (
            "💡 Want interview prep for this role?\n"
            "Reply with: YES"
        )

        return result_text

    except requests.exceptions.Timeout:

        return (
            "⏳ Job API is slow right now.\n\n"
            "Try again in 20 seconds."
        )

    except Exception as e:

        print("JOB ERROR:", e)

        return (
            "⚠️ Unable to fetch jobs right now."
        )

# =========================
# HOME ROUTE
# =========================

@app.route("/")
def home():
    return "AI Career Coach is running!"

# =========================
# WHATSAPP ROUTE
# =========================

@app.route("/whatsapp", methods=["POST"])
def whatsapp_reply():

    incoming_msg = request.values.get("Body", "").strip()

    msg_lower = incoming_msg.lower()

    user_number = request.values.get("From")

    resp = MessagingResponse()

    # =========================
    # GREETING
    # =========================

    if msg_lower in ["hi", "hello", "hey", "start", "help"]:

        greeting = (
            "👋 *Hi! I'm your AI Career Coach.*\n\n"
            "I can help you with:\n\n"
            "🔍 Job Search\n"
            "📄 Resume Review\n"
            "🎙️ Interview Prep\n"
            "💰 Salary Advice\n\n"
            "Try:\n"
            "'Remote Python Developer'\n"
            "or\n"
            "'Interview questions for Java Developer'"
        )

        resp.message(greeting)

        return str(resp)

    # =========================
    # HANDLE YES
    # =========================

    if msg_lower in ["yes", "yeah", "yep"]:

        previous_state = user_states.get(user_number)

        if previous_state:

            if previous_state["intent"] == "job_search":

                role = previous_state["query"]

                interview_prompt = (
                    f"Give top interview questions and preparation tips "
                    f"for a {role} role."
                )

                ai_response = ask_free_ai(interview_prompt)

                resp.message(ai_response)

                return str(resp)

        resp.message(
            "Please tell me what you'd like help with 😊"
        )

        return str(resp)

    # =========================
    # AI ROUTING
    # =========================

    ai_keywords = [
        "interview",
        "resume",
        "cv",
        "ats",
        "salary",
        "career",
        "skills",
        "advice"
    ]

    if any(keyword in msg_lower for keyword in ai_keywords):

        ai_response = ask_free_ai(incoming_msg)

        resp.message(ai_response)

        return str(resp)

    # =========================
    # JOB SEARCH
    # =========================

    user_states[user_number] = {
        "intent": "job_search",
        "query": incoming_msg
    }

    jobs_response = fetch_jobs(incoming_msg)

    resp.message(jobs_response)

    return str(resp)

# =========================
# RUN APP
# =========================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port,
        threaded=True
    )