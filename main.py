import re
import asyncio
import os
import subprocess
import json
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# --- KONFIGURASI ---
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
SESSION_STRING = os.getenv('SESSION_STRING')

TUJUAN = -1002183727075
TOPIC_ID_TUJUAN = 153
LAST_ID_FILE = "last_ids.json"

# Inisialisasi Client
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

def get_last_ids():
    if os.path.exists(LAST_ID_FILE):
        with open(LAST_ID_FILE, "r") as f:
            try: return json.load(f)
            except: return {}
    return {}

def save_last_id(channel_id, message_id):
    data = get_last_ids()
    data[str(channel_id)] = message_id
    with open(LAST_ID_FILE, "w") as f:
        json.dump(data, f, indent=4)
    
    # Push update ke GitHub agar history tetap sinkron
    try:
        subprocess.run(["git", "config", "user.name", "GitHub Actions"])
        subprocess.run(["git", "config", "user.email", "actions@github.com"])
        subprocess.run(["git", "add", LAST_ID_FILE])
        subprocess.run(["git", "commit", "-m", f"Update ID {channel_id}: {message_id} [skip ci]"])
        subprocess.run(["git", "push"])
    except: pass

def bersihkan_konten(teks, sumber):
    if not teks: return ""
    
    # 1. Hapus Link & Username agar rapi
    teks = re.sub(r'https?://\S+', '', teks)
    teks = re.sub(r't\.me/\S+', '', teks)
    teks = re.sub(r'@' + re.escape(str(sumber)), '', teks, flags=re.IGNORECASE)
    
    # 2. Hapus tanda kurung di awal judul (Instruksi: [DL NIME])
    teks = re.sub(r'^\[.*?\]\s*', '', teks)
    
    # 3. Mapping Penggantian & Penghapusan Teks Khusus
    mapping = {
        "New TV Show Added!": "Series Update",
        "New Movie Added!": "Movie Update",
        "New Episode Released": "Episode Baru Tersedia",
        "Download Via": "silakan Request ke Mimin",
        "WGFILM21": ""  # Ini akan menghapus kata WGFILM21 secara total
    }
    
    for lama, baru in mapping.items():
        teks = teks.replace(lama, baru)
        
    return teks.strip()

async def proses_dan_kirim(message, channel_id):
    chat = await message.get_chat()
    username_asal = getattr(chat, 'username', "Sumber")
    teks_clean = bersihkan_konten(message.message, str(username_asal))
    
    try:
        if message.media:
            path = await message.download_media()
            await client.send_file(TUJUAN, path, caption=teks_clean, reply_to=TOPIC_ID_TUJUAN)
            if os.path.exists(path): os.remove(path)
        elif teks_clean:
            await client.send_message(TUJUAN, teks_clean, reply_to=TOPIC_ID_TUJUAN)
        
        save_last_id(channel_id, message.id)
        print(f"✅ Terkirim ID {message.id} dari {channel_id}")
    except Exception as e:
        print(f"❌ Gagal: {e}")

# Monitoring Real-time
@client.on(events.NewMessage(chats=[-1002186281759, -1002183727075])) # Ganti ID kedua dengan sumber asli
async def handler(event):
    # Filter: Jika dari channel pertama, hanya terima yang dari topic 151
    if event.chat_id == -1002186281759:
        if event.message.reply_to and event.message.reply_to.reply_to_msg_id == 151:
            await proses_dan_kirim(event.message, event.chat_id)
    else:
        # Untuk channel kedua (umum), langsung proses
        await proses_dan_kirim(event.message, event.chat_id)

async def main():
    await client.start()
    last_ids = get_last_ids()
    
    # DAFTAR TUGAS
    tugas = [
        {"id": -1002186281759, "start": 8823, "topic": 151}, # KHUSUS TOPIK
        {"id": -1002233445566, "start": 33570, "topic": None} # UMUM
    ]

    for t in tugas:
        ch_id = t["id"]
        # Ambil ID terakhir dari JSON, kalau tidak ada pakai start default
        current_min = int(last_ids.get(str(ch_id), t["start"]))
        
        print(f"⏳ Menarik history {ch_id} (Filter Topic: {t['topic']}) mulai ID {current_min}...")
        
        async for msg in client.iter_messages(ch_id, min_id=current_min, reply_to=t["topic"], reverse=True):
            await proses_dan_kirim(msg, ch_id)
            await asyncio.sleep(2)

    print("📡 Monitoring Aktif...")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
