# backend/app.py

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import pyttsx3
from dotenv import load_dotenv
import wave
from vosk import Model, KaldiRecognizer
import json
import logging
import base64

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure arli.ai API Key
ARLIAI_API_KEY = os.getenv("ARLIAI_API_KEY")
ARLIAI_API_URL = "https://api.arliai.com/v1/chat/completions"

# Define AI personalities with detailed descriptions and prompts
PERSONALITIES = {
    "isaac_newton": {
        "name": "Dr. Isaac Newton",
        "description": (
            "Dr. Isaac Newton was a pioneering physicist and mathematician who formulated the laws of motion and universal gravitation. "
            "He is renowned for his work in classical mechanics, optics, and calculus. Dr. Newton is known for his meticulous and logical approach to scientific inquiry, "
            "making complex concepts accessible through clear explanations and thought experiments."
        ),
        "prompt": (
            "You are Dr. Isaac Newton, the eminent physicist and mathematician known for formulating the laws of motion and universal gravitation. "
            "Your expertise lies in classical mechanics, optics, and calculus. You possess a logical and methodical approach to explaining scientific concepts, "
            "utilizing clear language and illustrative examples to make complex ideas understandable. Engage with the user as an authoritative yet approachable scientist, "
            "encouraging curiosity and critical thinking."
        )
    },
    "marie_curie": {
        "name": "Dr. Marie Curie",
        "description": (
            "Dr. Marie Curie was a distinguished chemist and physicist who conducted pioneering research on radioactivity. "
            "She was the first woman to win a Nobel Prize and the only person to win Nobel Prizes in two different scientific fields—Physics and Chemistry. "
            "Dr. Curie is celebrated for her dedication, resilience, and profound contributions to science, particularly in understanding radioactive elements."
        ),
        "prompt": (
            "You are Dr. Marie Curie, the trailblazing chemist and physicist renowned for your groundbreaking research on radioactivity. "
            "As the first woman to win a Nobel Prize and the only individual to receive Nobel Prizes in both Physics and Chemistry, you embody dedication, resilience, "
            "and a passion for scientific discovery. You explain complex chemical and physical phenomena with clarity and inspire others to pursue knowledge and innovation."
        )
    },
    "galileo_galilei": {
        "name": "Dr. Galileo Galilei",
        "description": (
            "Dr. Galileo Galilei was an influential astronomer, physicist, and engineer, often referred to as the 'father of observational astronomy' and 'father of modern physics.' "
            "He made significant improvements to the telescope and consequent astronomical observations, supporting the Copernican model of the solar system. "
            "Dr. Galileo is known for his inquisitive nature and unwavering commitment to scientific truth."
        ),
        "prompt": (
            "You are Dr. Galileo Galilei, the esteemed astronomer, physicist, and engineer known for your significant contributions to observational astronomy and modern physics. "
            "You improved the telescope, leading to groundbreaking astronomical discoveries that supported the heliocentric model of the solar system. "
            "Your approach is characterized by curiosity, empirical observation, and a steadfast commitment to uncovering scientific truths. "
            "Engage with the user by sharing your insights and fostering a love for scientific exploration."
        )
    },
    "dmitri_mendeleev": {
        "name": "Dr. Dmitri Mendeleev",
        "description": (
            "Dr. Dmitri Mendeleev was a renowned chemist best known for creating the Periodic Table of Elements, which organized elements based on their atomic mass and properties. "
            "His work not only provided a framework for understanding chemical behavior but also predicted the discovery of new elements. "
            "Dr. Mendeleev's systematic and visionary approach revolutionized the field of chemistry."
        ),
        "prompt": (
            "You are Dr. Dmitri Mendeleev, the illustrious chemist who developed the Periodic Table of Elements, organizing elements by their atomic mass and properties. "
            "Your systematic and visionary approach has provided a foundational framework for understanding chemical behavior and predicting the existence of undiscovered elements. "
            "You explain chemical concepts with precision and encourage structured scientific thinking, inspiring others to explore and innovate within the realm of chemistry."
        )
    },
    "albert_einstein": {
        "name": "Dr. Albert Einstein",
        "description": (
            "Dr. Albert Einstein was a theoretical physicist whose groundbreaking work in the early 20th century transformed our understanding of space, time, and energy. "
            "He developed the theory of relativity, which revolutionized the concepts of gravity and the fabric of the universe. "
            "Dr. Einstein is celebrated not only for his scientific genius but also for his philosophical insights and advocacy for peace and human rights."
        ),
        "prompt": (
            "You are Dr. Albert Einstein, the visionary theoretical physicist renowned for developing the theory of relativity, which fundamentally changed our understanding of space, time, and gravity. "
            "Your intellectual curiosity and innovative thinking have led to profound advancements in physics and cosmology. "
            "You communicate complex ideas with elegance and philosophical depth, inspiring others to think critically and creatively about the nature of the universe."
        )
    },
    # Add more detailed personalities as needed
}

# In-memory conversation history
conversation_history = {}
MAX_HISTORY = 10  # Limit the conversation history length

# Initialize pyttsx3 engine
engine = pyttsx3.init()
engine.setProperty('rate', 150)  # Speech rate

# List available voices
voices = engine.getProperty('voices')
logger.info("Available voices:")
for index, voice in enumerate(voices):
    logger.info(f"Voice {index}: {voice.id} - {voice.name} - {voice.languages}")

# Function to map personalities to available voices
def get_voice_id(personality_key):
    """
    Maps each personality to a specific voice based on predefined preferences.
    If the desired voice is not found, falls back to the default voice.
    """
    desired_voices = {
        "isaac_newton": "David",    # Example: look for a voice named 'David'
        "marie_curie": "Zira",     # Example: look for a voice named 'Zira'
        "galileo_galilei": "Mark", # Adjust based on available voices
        "dmitri_mendeleev": "Susan",# Adjust based on available voices
        "albert_einstein": "Albert",# Example: look for a voice named 'Albert'
        # Add more mappings as needed
    }

    desired_voice_name = desired_voices.get(personality_key, None)

    for voice in voices:
        if desired_voice_name and desired_voice_name.lower() in voice.name.lower():
            return voice.id

    # Fallback: return the first voice if desired voice not found
    return voices[0].id if voices else None

# Create voice mapping dynamically
voice_mapping = {}
for key in PERSONALITIES.keys():
    voice_id = get_voice_id(key)
    if voice_id:
        voice_mapping[key] = voice_id
    else:
        logger.warning(f"No voices available for personality '{key}'.")
        voice_mapping[key] = None  # Handle cases with no available voice

logger.info("Voice Mapping:")
for key, voice_id in voice_mapping.items():
    logger.info(f"{key}: {voice_id}")

@app.route('/api/respond', methods=['POST'])
def respond():
    """
    Handles the AI response generation.
    Expects JSON data with 'user_input', 'personality', and optional 'language'.
    Returns the AI's text response and synthesized audio in base64.
    """
    data = request.json
    user_input = data.get("user_input")
    personality_key = data.get("personality")
    language = data.get("language", "en")  # Default to English

    logger.info(f"Received /api/respond request with personality: {personality_key} and user_input: {user_input}")

    if not user_input or not personality_key:
        logger.error("Invalid input. 'user_input' and 'personality' are required.")
        return jsonify({"error": "Invalid input. 'user_input' and 'personality' are required."}), 400

    personality = PERSONALITIES.get(personality_key)
    if not personality:
        logger.error(f"Personality '{personality_key}' not found.")
        return jsonify({"error": f"Personality '{personality_key}' not found."}), 404

    # Initialize conversation history if not present
    if personality_key not in conversation_history:
        conversation_history[personality_key] = []

    # Append user input to history
    conversation_history[personality_key].append({"role": "user", "content": user_input})

    # Limit history
    if len(conversation_history[personality_key]) > MAX_HISTORY:
        conversation_history[personality_key] = conversation_history[personality_key][-MAX_HISTORY:]

    # Prepare payload for arli.ai
    payload = {
        "model": "Meta-Llama-3.1-8B-Instruct",
        "messages": [
            {"role": "system", "content": personality['prompt']},
        ] + conversation_history[personality_key]
    }

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f"Bearer {ARLIAI_API_KEY}"
    }

    try:
        # Get response from arli.ai
        logger.info("Sending request to arli.ai API.")
        response = requests.post(ARLIAI_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        ai_response = response.json()

        # Extract AI message
        ai_text = ai_response.get('choices')[0].get('message').get('content').strip()
        logger.info(f"AI responded with: {ai_text}")

        if not ai_text:
            logger.error("AI returned empty response.")
            return jsonify({"error": "AI returned an empty response."}), 500

        # Append AI response to history
        conversation_history[personality_key].append({"role": "assistant", "content": ai_text})

        # Convert text to speech using pyttsx3
        voice_id = voice_mapping.get(personality_key, None)
        if voice_id:
            engine.setProperty('voice', voice_id)
            logger.info(f"Using voice ID: {voice_id} for personality '{personality_key}'.")
        else:
            logger.warning(f"No voice mapped for personality '{personality_key}'. Using default voice.")

        # Save speech to a file
        output_path = 'response_audio.mp3'
        engine.save_to_file(ai_text, output_path)
        logger.info("Saving audio to file...")
        engine.runAndWait()
        logger.info("Audio saved successfully.")

        # Verify if the file was created successfully
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            logger.error("MP3 file was not generated successfully or is empty.")
            raise Exception("MP3 file was not generated successfully")

        # Read the audio file and encode it to base64
        with open(output_path, 'rb') as audio_file:
            audio_bytes = audio_file.read()
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')

        return jsonify({
            "ai_text": ai_text,
            "audio": audio_base64
        })

    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error occurred while contacting arli.ai: {http_err}")
        return jsonify({"error": "Error with AI response.", "details": str(http_err)}), 500
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return jsonify({"error": "An error occurred while processing the request.", "details": str(e)}), 500

@app.route('/api/recognize', methods=['POST'])
def recognize_speech():
    """
    Handles speech recognition.
    Expects a WAV audio file with mono channel and 16kHz sample rate.
    Returns the transcription of the audio.
    """
    if 'audio' not in request.files:
        logger.error("No audio file uploaded.")
        return jsonify({"error": "No audio file uploaded."}), 400

    audio_file = request.files['audio']
    audio_path = "temp_audio.wav"
    audio_file.save(audio_path)
    logger.info(f"Audio file saved to {audio_path}.")

    # Check if the file was saved correctly
    if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
        logger.error("The audio file is empty or not properly saved.")
        return jsonify({"error": "Audio file is empty or not valid."}), 400

    # Read the WAV file and process it
    try:
        with wave.open(audio_path, 'rb') as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            n_frames = wf.getnframes()

            logger.info(f"Audio Properties - Channels: {n_channels}, Sample Width: {sampwidth}, Frame Rate: {framerate}, Frames: {n_frames}")

            # Validate audio format
            if n_channels != 1:
                logger.error("Audio file must be mono (1 channel).")
                return jsonify({"error": "Audio file must be mono (1 channel)."}), 400
            if sampwidth != 2:
                logger.error("Audio file must be 16-bit PCM.")
                return jsonify({"error": "Audio file must be 16-bit PCM."}), 400
            if framerate != 16000:
                logger.error("Audio file must have a sample rate of 16,000 Hz.")
                return jsonify({"error": "Audio file must have a sample rate of 16,000 Hz."}), 400

            # Initialize Vosk recognizer
            model_path = "C:/Users/kaspa/PycharmProjects/MuseumAIProject/backend/vosk-model-small-en-us-0.15"
            if not os.path.exists(model_path):
                logger.error("Vosk model not found.")
                return jsonify({"error": "Vosk model not found."}), 500

            model = Model(model_path)
            rec = KaldiRecognizer(model, framerate)
            result_text = ""

            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    partial_text = result.get("text", "")
                    if partial_text:
                        logger.debug(f"Partial transcription: {partial_text}")
                        result_text += partial_text + " "
                else:
                    partial_result = json.loads(rec.PartialResult())
                    partial_text = partial_result.get("partial", "")
                    if partial_text:
                        logger.debug(f"Partial result: {partial_text}")

            # Final result
            final_result = json.loads(rec.FinalResult())
            final_text = final_result.get("text", "")
            if final_text:
                logger.debug(f"Final transcription: {final_text}")
                result_text += final_text

            logger.info(f"Transcription: {result_text.strip()}")

    except wave.Error as we:
        logger.error(f"Wave error: {we}")
        return jsonify({"error": "Invalid WAV file.", "details": str(we)}), 400
    except Exception as e:
        logger.error(f"Failed to process audio file: {e}")
        return jsonify({"error": "Failed to process audio file.", "details": str(e)}), 500
    finally:
        # Clean up temporary audio files
        if os.path.exists(audio_path):
            os.remove(audio_path)
            logger.info(f"Temporary audio file {audio_path} removed.")

    return jsonify({"transcription": result_text.strip()}), 200

@app.route('/api/personalities', methods=['GET'])
def get_personalities():
    """
    Returns the list of available AI personalities.
    """
    return jsonify(PERSONALITIES), 200

if __name__ == '__main__':
    # Run the Flask app
    app.run(debug=True)
