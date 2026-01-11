from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import requests
from dotenv import load_dotenv

app = Flask(__name__, static_folder="static")
CORS(app)
load_dotenv()

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

OPENROUTER_MODEL = "openai/gpt-4o-mini"  # cheapest solid model


@app.route("/")
def index():
    return send_from_directory("static", "index.html")

def openrouter_prompt(prompt):
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "HTTP-Referer": "http://localhost:5000",  # required by OpenRouter
            "X-Title": "Lecture Assistant"
        }

        payload = {
            "model": OPENROUTER_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7
        }

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )

        response.raise_for_status()
        data = response.json()

        # Debug
        print("OpenRouter response keys:", data.keys())

        return data["choices"][0]["message"]["content"]

    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return f"Connection error: {str(e)}"
    except Exception as e:
        print(f"Unexpected error in openrouter_prompt: {e}")
        return f"Error: {str(e)}"


@app.route("/send", methods=["POST"])
def send_message():
    data = request.json
    text = data.get("text", "")
    full_text = data.get("full_text", "")

    response = openrouter_prompt(
        f"""
Answer the user's question using the lecture context.

Task:
- Give a direct, correct answer.
- If the lecture is unclear or contradictory, say so.

Style:
- Casual, conversational, mildly gossipy.
- Friendly but not dramatic.
- No emojis unless it truly fits (0–1 max).

Length:
- 2–3 sentences.
- ~200 characters max (unless more is required. This is flexible based off of user question.).

User question:
{text}

Lecture context:
{full_text}
"""
    )

    return jsonify({"reply": response})


@app.route("/summary", methods=["POST"])
def summarize():
    full_text = request.json.get("full_text", "")
    new_chunk = request.json.get("new_chunk", "")

    response = openrouter_prompt(
        f"""
You are generating LIVE lecture side-notes.

Task:
- React ONLY to the NEW chunk below. Explain/summarize the new information in context of the entire lecture (and add in cool facts too). Add in interesting outside information if relevant and attention-grabbing. 
- Point out: new facts, repetition, errors, or clarifications.
- Do NOT restate everything.

Style:
- Casual, dry, slightly gossipy.
- Think: smart friend whispering during class.
- No ALL CAPS.
- Max 1 emoji, optional.
- No fake drama or invented stakes.

Length:
- 1–3 short sentences.
- ~150–200 characters max.

New lecture chunk:
{new_chunk}

Previous lecture (context only, do not summarize):
{full_text}
"""
    )

    print(response)
    return jsonify({"reply": response})


@app.route("/quiz", methods=["POST"])
def quiz():
    data = request.json
    text = data.get("text", "")

    prompt = f"""
Generate a 7-question multiple choice quiz from the following transcript.
Return ONLY valid JSON with this exact format:

{{
  "quiz": [
    {{
      "question": "Question text here",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "answer": "Option A"
    }}
  ]
}}

Transcript:
{text}

Important: Return ONLY the JSON object, no additional text.
"""

    try:
        quiz_json_text = openrouter_prompt(prompt)

        import json
        import re

        quiz_json_text = re.sub(r'```json\s*|\s*```', '', quiz_json_text).strip()
        quiz_data = json.loads(quiz_json_text)

        if "quiz" in quiz_data and isinstance(quiz_data["quiz"], list):
            return jsonify(quiz_data)
        else:
            return jsonify({"quiz": quiz_data})

    except json.JSONDecodeError:
        try:
            match = re.search(r'\{.*\}', quiz_json_text, re.DOTALL)
            if match:
                quiz_data = json.loads(match.group())
                return jsonify(quiz_data)
        except:
            pass

        print("Failed to parse JSON. Raw response:", quiz_json_text)
        return jsonify({
            "error": "Failed to parse quiz JSON",
            "message": "Please try again with a longer transcript",
            "quiz": []
        }), 400

    except Exception as e:
        print("Quiz generation error:", str(e))
        return jsonify({
            "error": "Quiz generation failed",
            "message": str(e),
            "quiz": []
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


