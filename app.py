from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app)
load_dotenv()

GEMINI_KEY = os.getenv("GEMINI_KEY")

def gemini_prompt(prompt):
    try:
        headers = {"Content-Type": "application/json"}
        completion = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        url = (
            "https://generativelanguage.googleapis.com/v1beta/"
            f"models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"
        )
        
        response = requests.post(url, headers=headers, json=completion)
        response.raise_for_status()  # Check for HTTP errors
        
        data = response.json()
        
        # Debug: print the response structure
        print("Gemini API Response keys:", data.keys())
        
        # Check if we have the expected structure
        if "candidates" in data and len(data["candidates"]) > 0:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        elif "error" in data:
            error_msg = data["error"].get("message", "Unknown Gemini API error")
            print(f"Gemini API error: {error_msg}")
            return f"Gemini API error: {error_msg}"
        else:
            # Try alternative response formats
            if "text" in data:
                return data["text"]
            elif "content" in data:
                return data["content"]
            else:
                print(f"Unexpected Gemini response structure: {data}")
                return "Sorry, I received an unexpected response from the AI service."
                
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return f"Connection error: {str(e)}"
    except Exception as e:
        print(f"Unexpected error in gemini_prompt: {e}")
        return f"Error: {str(e)}"

@app.route("/send", methods=["POST"])
def send_message():
    data = request.json
    text = data.get("text", "")
    full_text = data.get("full_text", "")
    gemini_response = gemini_prompt(
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
- ~200 characters max.

User question:
{text}

Lecture context:
{full_text}
"""
)

    return jsonify({"reply": gemini_response})


@app.route("/summary", methods=["POST"])
def summarize():
    full_text = request.json.get("full_text", "")
    new_chunk = request.json.get("new_chunk", "")
    gemini_response = gemini_prompt(
    f"""
You are generating LIVE lecture side-notes, not a summary.

Task:
- React ONLY to the NEW chunk below.
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

    print (gemini_response)
    return jsonify({"reply": gemini_response})


@app.route("/quiz", methods=["POST"])
def quiz():
    data = request.json
    text = data.get("text", "")
    
    # Improved prompt with clearer instructions
    prompt = f"""
Generate a 3-question multiple choice quiz from the following transcript.
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
        quiz_json_text = gemini_prompt(prompt)
        
        # Try to clean the response in case Gemini adds markdown or extra text
        import json
        import re
        
        # Remove any markdown code blocks if present
        quiz_json_text = re.sub(r'```json\s*|\s*```', '', quiz_json_text).strip()
        
        # Try to parse the JSON
        quiz_data = json.loads(quiz_json_text)
        
        # Validate the structure
        if "quiz" in quiz_data and isinstance(quiz_data["quiz"], list):
            return jsonify(quiz_data)
        else:
            # If the response doesn't have the expected structure, try to wrap it
            return jsonify({"quiz": quiz_data})
            
    except json.JSONDecodeError as e:
        # If JSON parsing fails, try to extract JSON from the response
        try:
            # Look for JSON pattern in the response
            import json
            match = re.search(r'\{.*\}', quiz_json_text, re.DOTALL)
            if match:
                quiz_data = json.loads(match.group())
                return jsonify({"quiz": quiz_data} if isinstance(quiz_data, list) else quiz_data)
        except:
            pass
            
        # Log the raw response for debugging
        print("Failed to parse JSON. Raw response:", quiz_json_text)
        return jsonify({
            "error": "Failed to parse quiz JSON", 
            "message": "Please try again with a longer transcript",
            "quiz": []  # Return empty quiz instead of failing
        }), 400
        
    except Exception as e:
        print("Quiz generation error:", str(e))
        return jsonify({
            "error": "Quiz generation failed",
            "message": str(e),
            "quiz": []
        }), 500
    
    
if __name__ == "__main__":
    app.run(port=5000)

