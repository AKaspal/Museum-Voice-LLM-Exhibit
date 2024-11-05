// frontend/src/App.js

import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { FaRobot, FaMicrophone, FaStop } from 'react-icons/fa';
import './App.css';

function App() {
  const [personalities, setPersonalities] = useState({});
  const [selectedPersonality, setSelectedPersonality] = useState(null);
  const [recording, setRecording] = useState(false);
  const [rawAudioURL, setRawAudioURL] = useState(null); // URL for the raw recorded audio
  const [convertedAudioURL, setConvertedAudioURL] = useState(null); // URL for the converted WAV audio
  const [transcript, setTranscript] = useState("");
  const [conversation, setConversation] = useState([]);
  const [language, setLanguage] = useState('en');

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  useEffect(() => {
    // Fetch personalities from backend
    axios.get('http://127.0.0.1:5000/api/personalities')
      .then(response => {
        setPersonalities(response.data);
      })
      .catch(error => {
        console.error("Error fetching personalities:", error);
      });
  }, []);

  const handlePersonalitySelect = (key) => {
    setSelectedPersonality(key);
    setTranscript("");
    setRawAudioURL(null);
    setConvertedAudioURL(null);
    setConversation([]);
  };

  const handleLanguageChange = (e) => {
    setLanguage(e.target.value);
  };

  const startRecording = () => {
    if (!selectedPersonality) {
      alert("Please select a scientist first!");
      return;
    }

    navigator.mediaDevices.getUserMedia({ audio: true })
      .then(stream => {
        const mediaRecorder = new MediaRecorder(stream);
        mediaRecorderRef.current = mediaRecorder;
        audioChunksRef.current = [];

        mediaRecorder.start();
        setRecording(true);
        console.log("Recording started...");

        mediaRecorder.ondataavailable = event => {
          console.log("Data available:", event.data.size);
          audioChunksRef.current.push(event.data);
        };

        mediaRecorder.onstop = async () => {
          console.log("Recording stopped.");
          const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });

          // Create a URL for the raw audio and set it for playback
          const rawURL = URL.createObjectURL(audioBlob);
          setRawAudioURL(rawURL);
          console.log("Raw audio URL set.");

          try {
            const wavBlob = await convertBlobToWav(audioBlob);
            if (!wavBlob) {
              alert("Failed to convert audio to WAV format.");
              return;
            }

            // Create a URL for the converted WAV audio and set it for playback
            const convertedURL = URL.createObjectURL(wavBlob);
            setConvertedAudioURL(convertedURL);
            console.log("Converted WAV audio URL set.");

            const formData = new FormData();
            formData.append("audio", wavBlob, 'audio.wav');

            // Send audio to backend
            axios.post('http://127.0.0.1:5000/api/recognize', formData, {
              headers: {
                'Content-Type': 'multipart/form-data'
              }
            })
              .then(response => {
                const { transcription } = response.data;
                console.log("Transcription received:", transcription);
                if (!transcription) {
                  alert("No speech detected. Please try again.");
                  return;
                }
                setTranscript(transcription);
                setConversation(prev => [...prev, { speaker: "User", text: transcription }]);
                sendToBackend(transcription);
              })
              .catch(error => {
                console.error("Error recognizing speech:", error);
                if (error.response && error.response.data && error.response.data.error) {
                  alert(`Error recognizing speech: ${error.response.data.error}`);
                } else {
                  alert("Error recognizing speech. Please check the backend logs.");
                }
              });

            setRecording(false);
          } catch (error) {
            console.error("Error converting audio:", error);
            alert("Error processing audio.");
            setRecording(false);
          }
        };

        // Optionally, provide a way to stop recording manually
        // For simplicity, we'll stop after 5 seconds
        setTimeout(() => {
          if (mediaRecorder.state !== "inactive") {
            mediaRecorder.stop();
          }
        }, 5000); // Adjust the duration as needed
      })
      .catch(error => {
        console.error("Error accessing microphone:", error);
        alert("Microphone access denied or not available.");
      });
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && recording) {
      mediaRecorderRef.current.stop();
      setRecording(false);
      console.log("Manual stop of recording.");
    }
  };

  const convertBlobToWav = (blob) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = async () => {
        try {
          const arrayBuffer = reader.result;
          const audioContext = new (window.AudioContext || window.webkitAudioContext)();
          const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);

          console.log("Original AudioBuffer Sample Rate:", audioBuffer.sampleRate);
          console.log("Original AudioBuffer Channels:", audioBuffer.numberOfChannels);

          // Resample to 16kHz
          const numberOfChannels = 1; // Mono
          const offlineContext = new OfflineAudioContext(
            numberOfChannels,
            audioBuffer.duration * 16000,
            16000
          );

          const source = offlineContext.createBufferSource();
          source.buffer = audioBuffer;

          // If the original audio is stereo, mix down to mono
          if (audioBuffer.numberOfChannels > 1) {
            console.log("Mixing down to mono.");
            const channelData = audioBuffer.getChannelData(0);
            const channelData1 = audioBuffer.getChannelData(1);
            for (let i = 0; i < channelData.length; i++) {
              channelData[i] = (channelData[i] + channelData1[i]) / 2;
            }
          }

          source.connect(offlineContext.destination);
          source.start(0);

          const resampledBuffer = await offlineContext.startRendering();

          console.log("Resampled AudioBuffer Sample Rate:", resampledBuffer.sampleRate);
          console.log("Resampled AudioBuffer Channels:", resampledBuffer.numberOfChannels);

          // Convert to WAV
          const wavBlob = audioBufferToWavBlob(resampledBuffer);
          resolve(wavBlob);
        } catch (error) {
          console.error("Error decoding audio data:", error);
          reject(error);
        }
      };
      reader.onerror = (error) => {
        console.error("FileReader error:", error);
        reject(error);
      };
      reader.readAsArrayBuffer(blob);
    });
  };

  const audioBufferToWavBlob = (audioBuffer) => {
    const numOfChannels = 1; // Mono
    const sampleRate = 16000; // 16kHz
    const format = 1; // PCM
    const bitsPerSample = 16;
    const bytesPerSample = bitsPerSample / 8;

    const channelData = audioBuffer.getChannelData(0); // Mono

    const buffer = new ArrayBuffer(44 + channelData.length * bytesPerSample);
    const view = new DataView(buffer);

    // RIFF identifier
    writeString(view, 0, 'RIFF');
    // File length
    view.setUint32(4, 36 + channelData.length * bytesPerSample, true);
    // RIFF type
    writeString(view, 8, 'WAVE');
    // Format chunk identifier
    writeString(view, 12, 'fmt ');
    // Format chunk length
    view.setUint32(16, 16, true);
    // Sample format (raw)
    view.setUint16(20, format, true);
    // Channel count
    view.setUint16(22, numOfChannels, true);
    // Sample rate
    view.setUint32(24, sampleRate, true);
    // Byte rate (sample rate * block align)
    view.setUint32(28, sampleRate * numOfChannels * bytesPerSample, true);
    // Block align (channel count * bytes per sample)
    view.setUint16(32, numOfChannels * bytesPerSample, true);
    // Bits per sample
    view.setUint16(34, bitsPerSample, true);
    // Data chunk identifier
    writeString(view, 36, 'data');
    // Data chunk length
    view.setUint32(40, channelData.length * bytesPerSample, true);

    // Write PCM samples
    let offset = 44;
    for (let i = 0; i < channelData.length; i++, offset += 2) {
      let s = Math.max(-1, Math.min(1, channelData[i]));
      s = s < 0 ? s * 0x8000 : s * 0x7FFF;
      view.setInt16(offset, s, true);
    }

    return new Blob([buffer], { type: 'audio/wav' });
  };

  const writeString = (view, offset, string) => {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i));
    }
  };

  const handleTextSubmit = () => {
    if (!selectedPersonality || !transcript) {
      alert("Please select a scientist and enter a question first!");
      return;
    }
    setConversation(prev => [...prev, { speaker: "User", text: transcript }]);
    sendToBackend(transcript);
    setTranscript(""); // Clear the transcript after submitting
  };

  const sendToBackend = (text) => {
    axios.post('http://127.0.0.1:5000/api/respond', {
      user_input: text,
      personality: selectedPersonality,
      language: language
    })
      .then(response => {
        const { ai_text, audio } = response.data;

        if (!ai_text) {
          alert("AI did not return any text.");
          return;
        }

        // Update conversation with AI response
        setConversation(prev => [...prev, { speaker: personalities[selectedPersonality].name, text: ai_text }]);

        if (audio) {
          // Convert base64 to Blob and create URL
          const audioBlob = base64ToBlob(audio, 'audio/mpeg');
          if (!audioBlob) {
            alert("Failed to process AI audio.");
            return;
          }
          const url = URL.createObjectURL(audioBlob);
          setConvertedAudioURL(url);

          // Play audio
          const audioPlayer = new Audio(url);
          audioPlayer.play();
        } else {
          alert("AI did not return any audio.");
        }
      })
      .catch(error => {
        console.error("Error getting AI response:", error);
        if (error.response && error.response.data && error.response.data.error) {
          alert(`Error getting AI response: ${error.response.data.error}`);
        } else {
          alert("Error getting AI response. Please check the backend logs.");
        }
      });
  };

  // Helper function to convert base64 to Blob
  const base64ToBlob = (base64, type) => {
    try {
      const byteCharacters = atob(base64);
      const byteNumbers = new Array(byteCharacters.length);
      for (let i = 0; i < byteCharacters.length; i++) {
          byteNumbers[i] = byteCharacters.charCodeAt(i);
      }
      const byteArray = new Uint8Array(byteNumbers);
      return new Blob([byteArray], {type: type});
    } catch (error) {
      console.error("Error converting base64 to Blob:", error);
      return null;
    }
  };

  // Optional: Download audio for debugging
  const downloadAudio = (audioBlob) => {
    const url = URL.createObjectURL(audioBlob);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.download = 'converted_audio.wav';
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
  };

  return (
    <div className="App">
      <h1>Museum AI Scientist Interaction</h1>

      <div className="language-selector">
        <label htmlFor="language">Language:</label>
        <select id="language" value={language} onChange={handleLanguageChange}>
          <option value="en">English</option>
          <option value="es">Spanish</option>
          <option value="fr">French</option>
          {/* Add more languages as needed */}
        </select>
      </div>

      <div className="personalities">
        {Object.keys(personalities).map(key => (
          <div
            key={key}
            className={`personality-card ${selectedPersonality === key ? 'selected' : ''}`}
            onClick={() => handlePersonalitySelect(key)}
          >
            <FaRobot size={50} />
            <h3>{personalities[key].name}</h3>
            <p>{personalities[key].description}</p>
          </div>
        ))}
      </div>

      <div className="conversation">
        {conversation.map((msg, index) => (
            <div key={index} className={`message ${msg.speaker === "User" ? "user" : "ai"}`}>
                <strong>{msg.speaker}:</strong> {msg.text}
            </div>
        ))}
      </div>

      <div className="interaction">
        <button
          onClick={recording ? stopRecording : startRecording}
          disabled={recording}
          className={recording ? 'active' : ''}
        >
          {recording ? <FaStop size={20} /> : <FaMicrophone size={20} />}
          {recording ? "Listening..." : "Speak"}
        </button>
        {rawAudioURL && (
          <div>
            <h4>Recorded Audio:</h4>
            <audio controls src={rawAudioURL}></audio>
          </div>
        )}
        {convertedAudioURL && (
          <div>
            <h4>Converted WAV Audio:</h4>
            <audio controls src={convertedAudioURL}></audio>
          </div>
        )}
      </div>

      {/* Add a text input and button for submitting text manually */}
      <div className="text-input">
        <input
          type="text"
          value={transcript}
          onChange={(e) => setTranscript(e.target.value)}
          placeholder="Type your question here..."
        />
        <button onClick={handleTextSubmit}>Submit</button>
      </div>
    </div>
  );
}

export default App;
