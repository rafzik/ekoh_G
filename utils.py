import os
import pyttsx3
import speech_recognition as sr
from dotenv import load_dotenv
from prompt import cpp_system_prompt
from openai import OpenAI

# Load environment variables
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client
client = OpenAI(api_key=api_key)

# 🔊 Text to Speech
def speak(text):
    engine = pyttsx3.init()
    engine.setProperty('rate', 180)
    engine.say(text)
    engine.runAndWait()

# 🎤 Speech to Text
def listen():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening for your C++ question...")
        audio = recognizer.listen(source)
        try:
            return recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            return "Sorry, I couldn't understand your voice."
        except sr.RequestError:
            return "Sorry, speech recognition service is not available."

# 🧠 C++ Response Generator
def get_gpt_response(question):
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # or "gpt-4" if you have access
        messages=[
            {"role": "system", "content": "You are a C++ and cybersecurity expert."},
            {"role": "user", "content": question}
        ]
    )
    return response.choices[0].message.content

# Example usage:
if __name__ == "__main__":
    question = listen()
    print(f"You asked: {question}")
    reply = ask_cpp_question(question)
    print(f"GPT says: {reply}")
    speak(reply)
