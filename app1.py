import asyncio
import os
from shazamio import Shazam
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, APIC
from mutagen.mp3 import MP3
import requests

async def recognize_mp3(file_path):
    shazam = Shazam()
    out = await shazam.recognize(file_path)
    if not out.get("track"):
        print("Não foi possível reconhecer a música.")
        return None

    track = out["track"]
    title = track["title"]
    artist = track["subtitle"]
    album = next((item for item in track["sections"][0]["metadata"] if item["title"] == "Album"), {}).get("text", "Unknown")
    year = next((item for item in track["sections"][0]["metadata"] if item["title"] == "Released"), {}).get("text", "Unknown")
    album_cover_url = track["images"]["coverart"]

    print(f"🎵 Título: {title}")
    print(f"👤 Artista: {artist}")
    print(f"💿 Álbum: {album}")
    print(f"📅 Ano: {year}")
    print(f"🖼️ Capa: {album_cover_url}")

    return {
        "title": title,
        "artist": artist,
        "album": album,
        "year": year,
        "cover_url": album_cover_url
    }

def write_id3_tags(mp3_path, metadata):
    audio = MP3(mp3_path, ID3=ID3)

    # Adiciona tags ID3 se não existirem
    try:
        audio.add_tags()
    except:
        pass

    audio.tags["TIT2"] = TIT2(encoding=3, text=metadata["title"])
    audio.tags["TPE1"] = TPE1(encoding=3, text=metadata["artist"])
    audio.tags["TALB"] = TALB(encoding=3, text=metadata["album"])
    audio.tags["TDRC"] = TDRC(encoding=3, text=metadata["year"])

    # Download da capa
    img_data = requests.get(metadata["cover_url"]).content
    audio.tags["APIC"] = APIC(
        encoding=3,
        mime='image/jpeg',
        type=3,  # capa da frente
        desc=u'Capa',
        data=img_data
    )

    audio.save()
    print("✅ Tags ID3 gravadas com sucesso no ficheiro MP3!")

# --- EXECUÇÃO PRINCIPAL ---

if __name__ == "__main__":
    mp3_file = input("🔍 Caminho do ficheiro MP3: ").strip()
    if not os.path.exists(mp3_file):
        print("❌ Ficheiro não encontrado.")
    else:
        loop = asyncio.get_event_loop()
        metadata = loop.run_until_complete(recognize_mp3(mp3_file))
        if metadata:
            write_id3_tags(mp3_file, metadata)
