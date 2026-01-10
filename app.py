from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app)
load_dotenv()

@app.route("/send", methods=["POST"])
def send_message():
    data = request.json
    text = data.get("text", "")
    print ("Text Received", flush=True)
    gemini_response = gemini_prompt(text)
    print ("Gemini Responded", flush=True)
    return jsonify({
        "reply": gemini_response
    })


def gemini_prompt(prompt):
    api_key = os.getenv("GEMINI_KEY")

    headers = {
        "Content-Type": "application/json"
    }

    completion = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ]
    }

    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/gemini-3-flash-preview:generateContent?key={api_key}"
    )

    response = requests.post(url, headers=headers, json=completion).json()

    return response["candidates"][0]["content"]["parts"][0]["text"]

if __name__ == "__main__":
    app.run(port=5000)

