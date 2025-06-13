import base64
import hashlib
import hmac
import time
import requests
import os
from pydub import AudioSegment
from mutagen.easyid3 import EasyID3

acr_config = {
    "host": "identify-eu-west-1.acrcloud.com",
    "access_key": "SbL8CJQK57oIKSPGA",
    "access_secret": "m2rxo7QzNRztG2PEDthYPpW9BmTmv2ff"
}

def preprocess_audio(file_path: str, temp_pcm_file: str = "sample.wav"):
    audio = AudioSegment.from_file(file_path)
    audio = audio.set_channels(1)
    audio = audio.set_sample_width(2)
    audio = audio.set_frame_rate(44100)
    first_12s = audio[:12000]
    first_12s.export(temp_pcm_file, format="wav")
    return temp_pcm_file

def create_signature(access_secret, string_to_sign):
    return base64.b64encode(hmac.new(
        bytes(access_secret, 'ascii'),
        bytes(string_to_sign, 'ascii'),
        digestmod=hashlib.sha1
    ).digest()).decode('ascii')

def identify_song(audio_file_path, config):
    temp_wav = preprocess_audio(audio_file_path)

    if not os.path.exists(temp_wav):
        raise Exception("Arquivo WAV temporário não gerado.")

    with open(temp_wav, 'rb') as f:
        sample_bytes = f.read()

    os.remove(temp_wav)

    if len(sample_bytes) < 10000:
        raise Exception("Arquivo de áudio gerado é muito pequeno para identificação.")

    http_method = "POST"
    http_uri = "/v1/identify"
    data_type = "audio"
    signature_version = "1"
    timestamp = str(int(time.time()))

    string_to_sign = "\n".join([
        http_method,
        http_uri,
        config["access_key"],
        data_type,
        signature_version,
        timestamp
    ])

    signature = create_signature(config["access_secret"], string_to_sign)

    files = {
        'sample': ('sample.wav', sample_bytes, 'audio/wav')
    }
    data = {
        'access_key': config["access_key"],
        'data_type': data_type,
        'signature_version': signature_version,
        'signature': signature,
        'timestamp': timestamp
    }

    url = f"https://{config['host']}{http_uri}"
    response = requests.post(url, files=files, data=data)
    return response.json()

def update_id3_tags(file_path, title, artist, album):
    audio = EasyID3(file_path)
    audio['title'] = title
    audio['artist'] = artist
    audio['album'] = album
    audio.save()

def process_music_file(file_path: str, config: dict):
    result = identify_song(file_path, config)
    status_code = result.get("status", {}).get("code")

    if status_code == 0:
        metadata = result["metadata"]["music"][0]
        title = metadata.get("title", "Unknown")
        artist = metadata.get("artists", [{}])[0].get("name", "Unknown")
        album = metadata.get("album", {}).get("name", "Unknown")

        update_id3_tags(file_path, title, artist, album)
        return {
            "title": title,
            "artist": artist,
            "album": album,
            "status": "success"
        }
    else:
        return {
            "status": "error",
            "message": result.get("status", {}).get("msg", "Unknown error")
        }

def process_folder(directory: str, config: dict):
    results = []
    for filename in os.listdir(directory):
        if filename.lower().endswith(".mp3"):
            file_path = os.path.join(directory, filename)
            print(f"Processando: {file_path}")
            try:
                result = process_music_file(file_path, config)
                result["file"] = filename
            except Exception as e:
                result = {
                    "file": filename,
                    "status": "error",
                    "message": str(e)
                }
            results.append(result)
    return results

if __name__ == "__main__":
    music_folder = r"C:\Users\ruima\Downloads\app\spotify To Mp3\mp3_files"  # Ajuste para sua pasta
    all_results = process_folder(music_folder, acr_config)
    import json
    print(json.dumps(all_results, indent=4, ensure_ascii=False))


