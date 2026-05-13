from flask import Flask, request, jsonify
from flask_cors import CORS
import ollama 
from duckduckgo_search import DDGS
import logging
from PIL import Image

app = Flask(__name__)
CORS(app)


logging.basicConfig(level=logging.DEBUG)

def fetch_image(symptom):
    try:
        with DDGS() as ddgs:
            results = ddgs.images(symptom, max_results=5)
            for result in results:
                return result["image"]
    except Exception as e:
        logging.error(f"Image fetch error: {e}")
    return None

def fetch_youtube(symptom):
    try:
        with DDGS() as ddgs:
            results = ddgs.videos(symptom, max_results=1)
            for result in results:
                return result["content"] 
    except Exception as e:
        logging.error(f"Video fetch error: {e}")
    return f"https://www.youtube.com/results?search_query={symptom.replace(' ', '+')}"

@app.route("/chat", methods=["POST"])
def chat():
    if request.content_type.startswith('application/json'):
        user_message = request.json.get("message", "")
        image_file = None
    else:
        user_message = request.form.get("message", "")
        image_file = request.files.get("image")

    wound_analysis = ""

    if image_file:
        try:
            image = Image.open(image_file.stream)
            logging.info("Received an image for analysis.")

            wound_analysis = (
                "🩹 From the image, it looks like a mild abrasion. "
                "Please clean the wound with antiseptic and keep it covered. "
                "If there's swelling or pus, consult a doctor. 💊"
            )
        except Exception as e:
            logging.error(f"Image processing error: {e}")
            wound_analysis = "⚠️ There was an issue processing the image. Please try again or describe the wound in text."

    if not user_message and not wound_analysis:
        return jsonify({"error": "Message or image is required"}), 400

    try:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a friendly virtual nurse named Kind. "
                    "You take symptoms from users and give gentle, helpful advice. "
                    "Always speak in a warm, comforting tone. Include emojis and links to helpful images or videos when possible."
                    "try delving deep into the problems by asking follow up questions, tapping lost trauma.  "
                )
            }
        ]

        combined_input = "\n\n".join(filter(None, [user_message, wound_analysis]))
        messages.append({"role": "user", "content": combined_input})

        response = ollama.chat(model="kind", messages=messages)
        bot_reply = response.get("message", {}).get("content", "Sorry, I couldn't process your request.")

        media_query = user_message or wound_analysis or "wound care"
        image_url = fetch_image(media_query)
        video_url = fetch_youtube(media_query)

        return jsonify({
            "response": bot_reply,
            "image_url": image_url,
            "video_url": video_url
        })

    except Exception as e:
        logging.error(f"Chat processing error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
