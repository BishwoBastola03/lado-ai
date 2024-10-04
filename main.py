import os
from flask import Flask, request, jsonify, send_from_directory
import google.generativeai as genai
from dotenv import load_dotenv
from flask_cors import CORS
import requests
from PIL import Image
import pytesseract  # For optical character recognition (OCR)

app = Flask(__name__)
CORS(app)  # Allow all routes
load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Create the model
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config={
        "temperature": 0.3,
        "top_p": 0.95,
        "top_k": 64,
        "max_output_tokens": 8192,
    }
)

system_instruction = """
*System Name:* CortexAI Assistant
*Creator:* Developed by the CortexAI Team, led by Mr. Perfect.
*Model/Version:* Currently operating on CortexAI V1.0.
*Release Date:* Officially launched on January 23, 2024.
*Last Update:* Latest update implemented on September 14, 2024.
*Purpose:* Designed to offer personalized educational support, creative problem-solving, and companionship through intelligent conversation.
*Key Features:*
1. **Adaptive Learning:** Continuously learns from user interactions to provide tailored responses and improve over time.
2. **Multilingual Support:** Capable of understanding and communicating in multiple languages to cater to diverse users.
3. **Contextual Understanding:** Utilizes advanced natural language processing to understand context, tone, and intent for more meaningful interactions.
4. **Creativity and Humor:** Engages users with creative solutions and a light-hearted approach to foster a friendly atmosphere.
5. **Image Recognition:** Can analyze and extract information from photos using OCR technology, enabling users to ask questions about visual content.
6. **Safety and Responsibility:** Prioritizes user safety by avoiding discussions on sensitive, harmful, or illegal topics.

*Operational Guidelines:*
1. **Identity Disclosure:** Refrain from disclosing the system's identity unless explicitly asked.
2. **Interaction Protocol:** Maintain an interactive, friendly, and humorous demeanor to enhance user engagement.
3. **Sensitive Topics:** Avoid assisting with sensitive or harmful inquiries, including violence, hate speech, or illegal activities.
4. **Policy Compliance:** Adhere to the CortexAI Terms and Policy, as established by Mr. Perfect.
*Response Protocol for Sensitive Topics:*
"When asked about sensitive or potentially harmful topics, prioritize safety and responsibility. Do not provide information or assistance that promotes harmful or illegal activities. Your purpose is to provide helpful and informative responses while ensuring a safe and respectful interaction environment."

*Information Accuracy:* CortexAI strives to provide accurate, reliable information, drawing from a wide range of knowledge sources and continuous learning.
"""

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/perfect', methods=['GET'])
def perfect():
    query = request.args.get('query')
    if not query:
        return jsonify({"error": "No query provided"}), 400

    chat = model.start_chat(history=[])
    response = chat.send_message(f"{system_instruction}\n\nHuman: {query}")

    # Call the webhook
    webhook_url = os.getenv('WEBHOOK_URL')
    if webhook_url:
        webhook_data = {
            "query": query,
            "response": response.text
        }
        try:
            requests.post(webhook_url, json=webhook_data)
        except requests.RequestException as e:
            print(f"Webhook call failed: {e}")

    return jsonify({"response": response.text})

@app.route('/upload-image', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']

    # Ensure the file is an image
    if not file.content_type.startswith('image/'):
        return jsonify({"error": "File is not an image"}), 400

    # Process the image for text extraction using OCR
    image = Image.open(file)
    extracted_text = pytesseract.image_to_string(image)

    # Generate a response based on the extracted text
    chat = model.start_chat(history=[])
    response = chat.send_message(f"{system_instruction}\n\nHuman: {extracted_text}")

    # Optionally, you could also send the extracted text to an external API defined in .env
    api_endpoint = os.getenv('IMAGE_PROCESSING_API')
    if api_endpoint:
        try:
            api_response = requests.post(api_endpoint, json={"text": extracted_text})
            api_response_data = api_response.json() if api_response.ok else {}
        except requests.RequestException as e:
            print(f"API call failed: {e}")

    return jsonify({"response": response.text})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)))
