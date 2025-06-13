import asyncio
import json
import os
import platform
import tkinter as tk
from tkinter import Label, Frame
from PIL import Image, ImageTk
from screeninfo import get_monitors
import pyaudio
import wave
import requests
from shazamio import Shazam

# === Audio recording ===
def record_audio(duration):
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    RECORD_SECONDS = duration
    WAVE_OUTPUT_FILENAME = "mic_output.wav"

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=1024)

    print("* Recording...")

    frames = []
    for _ in range(int(RATE / 1024 * RECORD_SECONDS)):
        data = stream.read(1024)
        frames.append(data)

    print("* Done recording")

    stream.stop_stream()
    stream.close()
    p.terminate()

    wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

    print(f"Recording saved as {WAVE_OUTPUT_FILENAME}")

# === Download album art ===
def download_album_art(img_url):
    try:
        response = requests.get(img_url)
        if response.status_code == 200:
            with open('album-cover.png', 'wb') as file:
                file.write(response.content)
            print("Image downloaded and saved as album-cover.png")
        else:
            print("Failed to retrieve the image - default will be used")
    except Exception as e:
        print(f"Error downloading image: {e}")

# === Recognize song with Shazam ===
async def detect():
    shazam = Shazam()
    try:
        out = await shazam.recognize("mic_output.wav")
        os.system("cls" if platform.system() == "Windows" else "clear")

        title = out['track']['title']
        artist = out['track']['subtitle']
        album = next((item for item in out['track']['sections'][0]['metadata'] if item.get("title") == "Album"), {}).get('text', 'Unknown')
        year = next((item for item in out['track']['sections'][0]['metadata'] if item.get("title") == "Released"), {}).get('text', 'Unknown')
        album_cover_url = out['track']['images']['coverart']

        song_data = {
            "title": title,
            "artist": artist,
            "album": album,
            "year": year,
            "album_art": "album-cover.png"
        }
        with open("data.song", "w") as f:
            json.dump(song_data, f)

        download_album_art(album_cover_url)
        print(f"Recognized: {title} - {artist} [{album}, {year}]")
    except Exception as e:
        print(f"Could not recognize track: {e}")
        song_data = {
            'title': 'Unknown',
            'artist': 'Unknown',
            'album': 'Unknown',
            'year': 'Unknown',
            'album_art': 'album-cover-default.png'
        }
        with open("data.song", "w") as f:
            json.dump(song_data, f)
    finally:
        if os.path.exists("mic_output.wav"):
            os.remove("mic_output.wav")

# === Load song data JSON ===
def get_song_data():
    try:
        with open("data.song", "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading song data: {e}")
        return {
            'title': 'Error',
            'artist': 'Error loading data',
            'album': 'The song might not be recognized yet',
            'year': "Check the data.song file",
            'album_art': 'album-cover-default.png'
        }

# === Tkinter UI ===
class MusicApp:
    def __init__(self, root):
        self.root = root
        self.root.configure(background='black')
        self.album_art = None

        # Setup fullscreen on main monitor
        monitors = get_monitors()
        monitor = monitors[0]  # main monitor

        self.root.geometry(f"{monitor.width}x{monitor.height}+{monitor.x}+{monitor.y}")

        if platform.system() == 'Linux':
            self.root.attributes("-fullscreen", True)
        else:
            self.root.overrideredirect(True)
            self.root.geometry(f"{self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}+0+0")

        self.root.bind_all("<Escape>", lambda e: self.close())
        self.root.focus_set()

        # Layout
        content_frame = Frame(self.root, bg='black')
        content_frame.pack(expand=True, pady=(0,0))

        album_art_frame = Frame(content_frame, bg='black')
        album_art_frame.grid(row=0, column=0, padx=(100,50), pady=20, sticky='n')

        text_frame = Frame(content_frame, bg='black')
        text_frame.grid(row=0, column=1, pady=20, sticky='n')

        content_frame.grid_columnconfigure(0, weight=0)
        content_frame.grid_columnconfigure(1, weight=1)

        self.album_art_label = Label(album_art_frame, bg='black')
        self.album_art_label.pack()

        self.title_label = Label(text_frame, fg='white', bg='black', font=('Helvetica', 36, "bold"))
        self.title_label.pack(pady=10, anchor='w')

        self.artist_label = Label(text_frame, fg='white', bg='black', font=('Helvetica', 30))
        self.artist_label.pack(pady=10, anchor='w')

        self.album_label = Label(text_frame, fg='white', bg='black', font=('Helvetica', 24))
        self.album_label.pack(pady=10, anchor='w')

        self.year_label = Label(text_frame, fg='white', bg='black', font=('Helvetica', 24))
        self.year_label.pack(pady=10, anchor='w')

        # Load initial info
        self.update_ui(get_song_data())

        # Start periodic refresh of song info every 5 seconds
        self.root.after(5000, self.refresh_song_info)

    def update_ui(self, song_info):
        # Load album art image
        try:
            img = Image.open(song_info['album_art'])
            img = img.resize((300, 300))
            self.album_art = ImageTk.PhotoImage(img)
            self.album_art_label.config(image=self.album_art)
        except Exception as e:
            print(f"Error loading album art: {e}")
            self.album_art_label.config(image='')

        self.title_label.config(text=song_info['title'])
        self.artist_label.config(text=song_info['artist'])
        self.album_label.config(text=song_info['album'])
        self.year_label.config(text=song_info['year'])

    def refresh_song_info(self):
        song_info = get_song_data()
        self.update_ui(song_info)
        self.root.after(5000, self.refresh_song_info)

    def close(self):
        # Cleanup file if exists
        if os.path.exists("data.song"):
            os.remove("data.song")
        self.root.destroy()

# === Main loop ===
async def main_loop():
    while True:
        record_audio(12)  # grava 12 segundos
        await detect()    # reconhece a música

if __name__ == "__main__":
    # Cria a janela Tkinter
    root = tk.Tk()
    app = MusicApp(root)

    # Executa o reconhecimento de música em paralelo com a UI
    loop = asyncio.get_event_loop()

    # Start asyncio task para reconhecimento
    loop.create_task(main_loop())

    # Start Tkinter mainloop (não bloqueia o loop asyncio)
    # Precisamos integrar Tkinter + asyncio
    # Aqui um hack simples para usar after e rodar o loop asyncio
    def poll_loop():
        loop.stop()
        loop.run_forever()
        root.after(100, poll_loop)

    root.after(100, poll_loop)
    root.mainloop()
