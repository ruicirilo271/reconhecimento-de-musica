import asyncio
import os
from shazamio import Shazam
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, APIC
from mutagen.mp3 import MP3
import requests

# Reconhecimento via Shazam
async def recognize_mp3(file_path):
    shazam = Shazam()
    try:
        out = await shazam.recognize(file_path)
        if not out.get("track"):
            print(f"❌ Não foi possível reconhecer: {os.path.basename(file_path)}")
            return None

        track = out["track"]
        title = track["title"]
        artist = track["subtitle"]
        album = next((item for item in track["sections"][0]["metadata"] if item["title"] == "Album"), {}).get("text", "Unknown")
        year = next((item for item in track["sections"][0]["metadata"] if item["title"] == "Released"), {}).get("text", "Unknown")
        album_cover_url = track["images"]["coverart"]

        print(f"✅ Reconhecido: {title} - {artist}")

        return {
            "title": title,
            "artist": artist,
            "album": album,
            "year": year,
            "cover_url": album_cover_url
        }
    except Exception as e:
        print(f"⚠️ Erro ao reconhecer '{os.path.basename(file_path)}': {e}")
        return None

# Gravar tags ID3
def write_id3_tags(mp3_path, metadata):
    audio = MP3(mp3_path, ID3=ID3)

    try:
        audio.add_tags()
    except:
        pass

    audio.tags["TIT2"] = TIT2(encoding=3, text=metadata["title"])
    audio.tags["TPE1"] = TPE1(encoding=3, text=metadata["artist"])
    audio.tags["TALB"] = TALB(encoding=3, text=metadata["album"])
    audio.tags["TDRC"] = TDRC(encoding=3, text=metadata["year"])

    # Capa do álbum
    try:
        img_data = requests.get(metadata["cover_url"]).content
        audio.tags["APIC"] = APIC(
            encoding=3,
            mime='image/jpeg',
            type=3,
            desc='Capa',
            data=img_data
        )
    except:
        print("⚠️ Erro ao descarregar a imagem da capa.")

    audio.save()
    print(f"🎵 Tags gravadas: {os.path.basename(mp3_path)}\n")

# Processa todos os ficheiros MP3 de uma pasta
async def process_folder(folder_path):
    mp3_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".mp3")]

    if not mp3_files:
        print("❌ Nenhum ficheiro MP3 encontrado na pasta.")
        return

    for filename in mp3_files:
        full_path = os.path.join(folder_path, filename)
        print(f"\n🔍 A processar: {filename}")
        metadata = await recognize_mp3(full_path)
        if metadata:
            write_id3_tags(full_path, metadata)

# --- EXECUÇÃO PRINCIPAL ---
if __name__ == "__main__":
    pasta = input("📁 Caminho da pasta com os MP3: ").strip()
    if not os.path.isdir(pasta):
        print("❌ Pasta inválida.")
    else:
        asyncio.run(process_folder(pasta))
