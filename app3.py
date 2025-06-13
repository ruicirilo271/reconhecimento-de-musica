import asyncio
import os
import re
from shazamio import Shazam
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, APIC
from mutagen.mp3 import MP3, HeaderNotFoundError
import requests
from tkinter import Tk, filedialog

async def recognize_mp3(file_path):
    shazam = Shazam()
    out = await shazam.recognize(file_path)
    if not out.get("track"):
        print("❌ Não foi possível reconhecer a música.")
        return None

    track = out["track"]
    title = track.get("title", "Unknown")
    artist = track.get("subtitle", "Unknown")

    # Tentativa de obter álbum e ano, se existirem
    album = "Unknown"
    year = "Unknown"
    sections = track.get("sections", [])
    if sections and "metadata" in sections[0]:
        for item in sections[0]["metadata"]:
            if item.get("title") == "Album":
                album = item.get("text", album)
            elif item.get("title") == "Released":
                year = item.get("text", year)

    # Obter capa, se existir
    cover_url = None
    if "images" in track and "coverart" in track["images"]:
        cover_url = track["images"]["coverart"]

    print(f"🎵 Título: {title}")
    print(f"👤 Artista: {artist}")
    print(f"💿 Álbum: {album}")
    print(f"📅 Ano: {year}")
    print(f"🖼️ Capa: {cover_url if cover_url else 'Sem capa'}")

    return {
        "title": title,
        "artist": artist,
        "album": album,
        "year": year,
        "cover_url": cover_url
    }

def sanitize_filename(name):
    # Remove caracteres inválidos para nomes de ficheiros no Windows
    return re.sub(r'[\\/*?:"<>|]', '', name)

def rename_file(mp3_path, metadata):
    folder = os.path.dirname(mp3_path)
    title = sanitize_filename(metadata["title"])
    artist = sanitize_filename(metadata["artist"])

    new_name = f"{artist} - {title}.mp3"
    new_path = os.path.join(folder, new_name)

    if mp3_path == new_path:
        print("ℹ️ Nome do ficheiro já está correto.")
        return

    # Evitar sobrescrever ficheiros existentes
    count = 1
    base, ext = os.path.splitext(new_path)
    while os.path.exists(new_path):
        new_path = f"{base} ({count}){ext}"
        count += 1

    try:
        os.rename(mp3_path, new_path)
        print(f"📁 Ficheiro renomeado: {new_path}")
    except Exception as e:
        print(f"❌ Erro a renomear ficheiro: {e}")

def write_id3_tags(mp3_path, metadata):
    try:
        audio = MP3(mp3_path, ID3=ID3)
    except HeaderNotFoundError:
        print(f"❌ Ficheiro não é MP3 válido ou está corrompido: {os.path.basename(mp3_path)}")
        return False

    try:
        audio.add_tags()
    except Exception:
        pass

    audio.tags["TIT2"] = TIT2(encoding=3, text=metadata["title"])
    audio.tags["TPE1"] = TPE1(encoding=3, text=metadata["artist"])
    audio.tags["TALB"] = TALB(encoding=3, text=metadata["album"])
    audio.tags["TDRC"] = TDRC(encoding=3, text=metadata["year"])

    if metadata.get("cover_url"):
        try:
            img_data = requests.get(metadata["cover_url"]).content
            audio.tags["APIC"] = APIC(
                encoding=3,
                mime='image/jpeg',
                type=3,  # capa da frente
                desc=u'Capa',
                data=img_data
            )
        except Exception as e:
            print(f"⚠️ Erro ao descarregar a capa: {e}")
    else:
        print("ℹ️ Sem capa para adicionar.")

    audio.save()
    print("✅ Tags ID3 gravadas com sucesso!")
    return True

async def process_folder(folder_path):
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".mp3"):
            full_path = os.path.join(folder_path, filename)
            print(f"\n🎵 A processar: {filename}")

            try:
                audio = MP3(full_path, ID3=ID3)
                title_tag = audio.tags.get("TIT2")
                artist_tag = audio.tags.get("TPE1")
                if title_tag and artist_tag:
                    existing = {
                        "title": title_tag.text[0],
                        "artist": artist_tag.text[0]
                    }
                    print("🔁 Já tem tags. A renomear apenas...")
                    rename_file(full_path, existing)
                    continue
            except Exception:
                pass

            metadata = await recognize_mp3(full_path)
            if metadata:
                wrote = write_id3_tags(full_path, metadata)
                if wrote:
                    rename_file(full_path, metadata)

if __name__ == "__main__":
    print("🎧 Seleciona a pasta com os ficheiros MP3...")

    # Janela para escolher pasta
    root = Tk()
    root.withdraw()
    pasta = filedialog.askdirectory(title="Seleciona a pasta com MP3s")
    root.destroy()

    if not pasta:
        print("❌ Nenhuma pasta selecionada. A sair...")
        exit()

    asyncio.run(process_folder(pasta))
