import tkinter as tk
from tkinter import ttk, filedialog
from deep_translator import GoogleTranslator
from langdetect import detect
from elevenlabs import play
from elevenlabs.client import ElevenLabs
from tkinter import messagebox
import subprocess  # For FFmpeg
import tempfile  # For temporary file management
import subprocess
import tempfile
import threading
import os
import time
import psutil

# Initialize ElevenLabs client
client = ElevenLabs(api_key='sk_9c08cdc6ad0193589b2dab54e8f2b9acd9d95c971d78256b')

# Fetch available voices
voice_map = {
    "Adam (Calm)": "pNInz6obpgDQGcFmaJgB",
    "Chris (Serious)": "ErXwobaYiN019PkySvjV",
    "Bill (Warm)": "EXAVITQu4vr4xnSDxMaL",
    "Domi (Energetic)": "21m00Tcm4TlvDq8ikWAM",
    "Elli (Cheerful)": "AZnzlk1XvdvUeBnXmlld",
    "Josh (Deep)": "TxGEqnHWrfWFTfGW9XjX",
    "Rachel (Friendly)": "MF3mGyEYCl7XYWbV9V6O",
    "Sam (Balanced)": "yoZ06aMxZJJ28mfd3POQ",
    "Ethan (ASMR)": "g5CIjZEefAph4nQFvHAz",
    "Nicole (ASMR)": "piTKgcLEGmPE4e6mEKli",
    "River (social media)": "SAz9YHcvj6GT2YYXdXww",
    "Will (social media)": "bIHbv24MWmeRgasZH58o",
    "Aria (Energetic)": "9BWtsMINqrJLrRacOk9x",
    "Brian (Narration)": "nPczCjzI2devNBz1zQrb",
    "Calluum (Calm)": "N2lVS1w4EtoT3dr4eOWO",
    "Daniel (News)": "onwK4e9ZLuTAKqWW03F9",
    "Domi (Narration)": "AZnzlk1XvdvUeBnXmlld",
    "Dorothy (Narration)": "ThT5KcBeYPX3keUQqHPh",
    "George (Audiobook)": "Yko7PKHZNXotIFUBG7I9",
    "Gigi (Animation)": "jBpfuIE2acCO8z3wKNLl",
    "Jessica (Conversational)": "cgSgspJ2msm6clMCkdW9",
    "Joseph (British)": "Zlb1dXrM653N07WRdFW3",
    "Lily (British)": "pFZP5JQG7iQjIQuC4Bku",
    "Josh (American)": "TxGEqnHWrfWFTfGW9XjX",
    "Mimi (Swedish)": "zrHiDhphv9ZnVXBqCLjz",
    "Santa Claus": "knrPHWnBmmDHMoiMeP3l"
}

# Function to handle text-to-speech
# Global Variables
is_paused = False
current_audio_path = None
playback_process = None
paused_position = 0  # Stores playback position in seconds
start_time = None  # Timestamp when playback starts


def speak_text():
    """Function to play or resume audio seamlessly"""
    global is_paused, playback_process, paused_position, current_audio_path, start_time

    user_text = text_box.get("1.0", "end-1c").strip()
    if not user_text or user_text == "Enter your Message here":
        return

    detected_lang = detect(user_text)
    target_lang = language_map.get(target_lang_var.get(), "en")
    translated_text = GoogleTranslator(source=detected_lang, target=target_lang).translate(user_text)
    selected_voice = voice_map.get(persona_var.get(), "EXAVITQu4vr4xnSDxMaL")

    speed_value = speed_slider.get()
    speed_multiplier = 0.5 + (speed_value * 0.25)

    if is_paused and current_audio_path:
        # Resume playback
        is_paused = False
        resume_audio()
        return

    try:
        # Generate temporary audio file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio:
            audio = client.text_to_speech.convert(
                text=translated_text,
                voice_id=selected_voice,
                model_id="eleven_multilingual_v1"
            )

            for chunk in audio:
                temp_audio.write(chunk)

            current_audio_path = temp_audio.name  # Store the file path

        # Adjust speed using FFmpeg
        output_audio_path = tempfile.mktemp(suffix=".mp3")
        ffmpeg_command = [
            "ffmpeg", "-i", current_audio_path,
            "-filter:a", f"atempo={speed_multiplier}",
            "-y", output_audio_path
        ]
        subprocess.run(ffmpeg_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        current_audio_path = output_audio_path  # Set processed file as the one to play
        paused_position = 0  # Reset position

        # Start playing audio
        play_audio()

    except Exception as e:
        print("Error:", e)


def play_audio():
    """Plays audio from the last known position or the beginning"""
    global playback_process, paused_position, start_time

    stop_audio()  # Stop any ongoing playback

    start_time = time.time() - paused_position  # Store the starting time

    playback_process = subprocess.Popen(
        ["ffplay", "-nodisp", "-autoexit", "-ss", str(paused_position), current_audio_path],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )


def pause_audio():
    """Pauses the currently playing audio and saves position"""
    global is_paused, playback_process, paused_position, start_time

    if playback_process:
        process = psutil.Process(playback_process.pid)
        process.suspend()  # Pause without terminating
        is_paused = True

        # Calculate elapsed time since playback started
        if start_time:
            paused_position += time.time() - start_time  # Store the current playback position


def resume_audio():
    """Resumes audio from the paused position"""
    global playback_process, start_time

    if playback_process:
        process = psutil.Process(playback_process.pid)
        process.resume()  # Resume without restarting
        is_paused = False
        start_time = time.time() - paused_position  # Adjust start time


def stop_audio():
    """Stops any currently playing audio and resets position"""
    global playback_process, is_paused, paused_position, start_time

    if playback_process:
        playback_process.terminate()
        playback_process = None

    is_paused = False
    paused_position = 0
    start_time = None

def terminate_all_processes():
    """Terminates all running audio processes."""
    global playback_process, is_paused, paused_position, current_audio_path

    if playback_process:
        playback_process.terminate()
        playback_process = None

    # Reset states
    is_paused = False
    paused_position = 0
    current_audio_path = None



# Function to download the audio file
def download_audio():
    selected_format = format_var.get().lower() if format_var.get() != "Enter your option" else "mp3"
    save_path = filedialog.asksaveasfilename(
        defaultextension=f".{selected_format}",
        filetypes=[
            ("MP3 Files", "*.mp3"),
            ("WAV Files", "*.wav"),
            ("OGG Files", "*.ogg"),
            ("FLAC Files", "*.flac"),
        ]
    )

    if save_path:
        speak_text(save_path=save_path, download_mode=True)
        print(f"✅ Audio downloaded successfully as: {save_path}")

# Initialize main window
root = tk.Tk()
root.title("SpeakEase")
root.geometry("800x620")
root.configure(bg="#C6E5B1")
root.resizable(False, False)

style = ttk.Style()
style.theme_use('clam')

# Fonts
header_font = ("Irish Grover", 36, "bold")
headline_font = ("Aoboshi One", 10, "bold")
box_font = ("Aoboshi One", 10)
button_font = ("Irish Grover", 14, "bold")

# Title
title_label = tk.Label(root, text="SpeakEase", font=header_font, bg="#C6E5B1")
title_label.place(x=20, y=10)

divider = tk.Frame(root, height=2, width=760, bg="black")
divider.place(x=20, y=70)

# Text Input Box
text_box = tk.Text(root, height=22, width=40, font=box_font, bd=2, relief="ridge")
text_box.place(x=30, y=100)
text_box.insert("1.0", "Enter your Message here")

# Language Selection
tk.Label(root, text="Input Language", font=headline_font, bg="#C6E5B1").place(x=400, y=90)
tk.Label(root, text="Target Language", font=headline_font, bg="#C6E5B1").place(x=400, y=155)

# Language Selection
supported_languages = GoogleTranslator().get_supported_languages()
language_map = {lang.capitalize(): lang for lang in supported_languages}
formatted_languages = list(language_map.keys())

input_lang_var = tk.StringVar()
target_lang_var = tk.StringVar()
input_lang_var.set("English (United Kingdom)")
target_lang_var.set("English (United Kingdom)")

input_lang_dropdown = ttk.Combobox(root, textvariable=input_lang_var, values=formatted_languages, width=55)
target_lang_dropdown = ttk.Combobox(root, textvariable=target_lang_var, values=formatted_languages, width=55)

input_lang_dropdown.place(x=400, y=115)
target_lang_dropdown.place(x=400, y=180)

# Additional Dropdowns
def create_dropdown(label, options, y_position):
    tk.Label(root, text=label, font=headline_font, bg="#C6E5B1").place(x=400, y=y_position)
    var = tk.StringVar()
    var.set("Enter your option")
    dropdown = ttk.Combobox(root, textvariable=var, values=options, width=55)
    dropdown.place(x=400, y=y_position + 25)
    return var

persona_var = create_dropdown("Persona", list(voice_map.keys()), 210)
format_var = create_dropdown("Format", ["MP3", "WAV", "OGG", "FLAC"], 355)
bitrate_var = create_dropdown("Bitrate", ["64 kbps", "128 kbps", "192 kbps", "320 kbps"], 405)

# Speed Slider
speed_label = tk.Label(root, text="Speed", font=headline_font, bg="#C6E5B1")
speed_label.place(x=400, y=265)
speed_slider = tk.Scale(root, from_=0, to=5, orient="horizontal", tickinterval=1)
speed_slider.place(x=400, y=290, width=350)
speed_slider.set(2)

# Play Button
play_btn = tk.Button(root, text="Play ▶", font=button_font, width=8, height=2, command=speak_text)
play_btn.place(x=640, y=465)

# Pause Button
pause_btn = tk.Button(root, text="Pause ⏸", font=button_font, width=8, height=2, command=pause_audio)
pause_btn.place(x=520, y=465)

# Stop Button
stop_btn = tk.Button(root, text="STOP", font=button_font, width=24, height=1, command=terminate_all_processes)
stop_btn.place(x=425, y=545)

# Download Button
download_btn = tk.Button(root, text="Download", font=button_font, width=8, height=2, command=download_audio)
download_btn.place(x=400, y=465)


# Disclaimer Label for Internet Requirement
disclaimer_label = tk.Label(root, text="⚠️ Internet connection required for functionality", font=("Aoboshi One", 10, "italic"), bg="#C6E5B1", fg="red")
disclaimer_label.place(x=30, y=530)

# Info Button
def show_info_popup():
    tk.messagebox.showinfo("About SpeakEase", "SpeakEase 1.1\nD.H Projects\ndevenhirlekar05@gmail.com")

info_button = tk.Button(root, text=" ℹ ", font=("Irish Grover", 10, "bold"), command=show_info_popup)
info_button.place(x=740, y=20)
# Run the app
root.mainloop()
