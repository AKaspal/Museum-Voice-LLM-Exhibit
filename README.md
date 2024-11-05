Museum AI Scientist Interaction
This project is a Museum AI interaction platform that uses Flask and React to simulate conversations with historical scientists, including Isaac Newton, Marie Curie, Galileo Galilei, Dmitri Mendeleev, and Albert Einstein. Users can speak directly with AI-driven personalities, view transcriptions of their speech, and receive synthesized audio responses from the AI. The AI draws responses from detailed personality prompts for each scientist, providing informative and authentic interactions.

Table of Contents
Technologies Used
Setup and Installation
Vosk Speech Recognition Model
Running the Project
Endpoints
Features
Project Structure
License
Technologies Used
Backend: Flask, Flask-CORS, pyttsx3 (for speech synthesis), Vosk (for speech recognition), Python-dotenv (for environment management)
Frontend: React, Axios, react-icons
APIs: Arli.ai for AI-generated responses
Setup and Installation
Clone the Repository

bash
Copy code
git clone https://github.com/AKaspal/Museum-Voice-LLM-Exhibit.git
cd museum-ai-interaction
Backend Dependencies

Install the necessary Python packages by running:
bash
Copy code
pip install -r requirements.txt
Ensure you have the Vosk model for English speech recognition. Download the vosk-model-small-en-us-0.15 model and place it in the designated backend directory.
Frontend Dependencies

Navigate to the frontend directory and install the Node dependencies:
bash
Copy code
cd frontend
npm install
Environment Variables

Create a .env file in the backend folder with your Arli.ai API key:
plaintext
Copy code
ARLIAI_API_KEY=your_api_key_here
Vosk Speech Recognition Model
Download the Vosk model vosk-model-small-en-us-0.15 and place it in the backend folder. This model enables English speech recognition within the Flask app.

Running the Project
Start the Flask Backend

Navigate to the backend directory and run the Flask server:
bash
Copy code
python app.py
The backend will start at http://127.0.0.1:5000.
Start the React Frontend

In a separate terminal, navigate to the frontend directory and run:
bash
Copy code
npm start
The frontend will be available at http://localhost:3000.
Endpoints
/api/respond (POST)
Description: Receives user input and personality selection to generate an AI response and synthesize it to audio.
Request Parameters:
user_input: The user’s text or transcribed speech.
personality: Selected personality (e.g., isaac_newton).
Response: AI-generated text and synthesized audio.
/api/recognize (POST)
Description: Accepts a WAV audio file and returns the transcribed text.
Request Parameters:
audio: The WAV audio file uploaded for transcription.
/api/personalities (GET)
Description: Returns the list of available scientist personalities.
Features
Historical Scientist Personalities: AI personalities modeled after famous scientists, with distinct conversational styles and responses.
Speech Recognition and Text-to-Speech: Users can speak to the AI, receive transcriptions, and hear AI responses in audio.
Multi-language Support: Language options for AI responses.
Project Structure
php
Copy code
museum-ai-interaction/
├── backend/
│   ├── app.py              # Flask backend API
│   ├── requirements.txt    # Python dependencies
│   ├── vosk-model-small-en-us-0.15/  # Speech recognition model folder
├── frontend/
│   ├── src/
│   │   ├── App.js          # React main component
│   │   ├── App.css         # Main stylesheet
│   ├── package.json        # Node dependencies
│   ├── public/             # Static assets
└── README.md
License
This project is licensed under the MIT License.

