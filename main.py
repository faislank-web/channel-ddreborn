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
TOPIC_ID = 153

# Definisi Sumber dan ID Mulai masing-masing
# Format: { ID_CHANNEL: ID_PESAN_MULAI }
SUMBER_CONFIG = {
    -1002186281759: 8823,   # Sumber 1 (Pakai Topic 151)
    -1002233445566: 33570   # Contoh Sumber 2 (Ganti dengan ID channel kedua kamu)
}

LAST_ID_FILE = "last_ids.json"

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

def get_last_ids():
    """Mengambil data ID terakhir dari file JSON"""
    if os.path.exists(LAST_ID_FILE):
        with open(LAST_ID_FILE, "r") as f:
            return json.load(f)
    # Jika file belum ada, gunakan ID mulai dari konfigurasi
    return {str(k): v for k, v in SUMBER_CONFIG.items()}

def save_last_id(channel_id, message_id):
    """Menyimpan ID terakhir ke JSON dan push ke GitHub"""
    data = get_last_ids()
    data[str(channel_id)] = message_id
    
    with open(LAST_ID_FILE, "w") as f:
        json.dump(data, f)
    
    try:
        subprocess.run(["git", "config", "user.name", "GitHub Actions"])
        subprocess.run(["git", "config", "user.email", "actions@github.com"])
        subprocess.run(["git", "add", LAST_ID_FILE])
        subprocess.run(["git", "commit", "-m", f"Update ID {channel_id}: {message_id} [skip ci]"])
        subprocess.run(["git", "push"])
    except:
        pass

def bersihkan_konten(teks, sumber):
    if not teks: return ""
    teks = re.sub(r'https?://\S+', '', teks)
    teks = re.sub(r't\.me/\S+', '', teks)
    teks = re.sub(r'@' + re.escape(str(sumber)), '', teks, flags=re.IGNORECASE)
    teks = re.sub(r'^\[.*?\]\s*', '', teks)
    
    mapping = {
        "New TV Show Added!": "Series Update",
        "New Movie Added!": "Movie Update",
        "New Episode Released": "Episode Baru Tersedia",
        "Download Via": "silakan Request ke Mimin"
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
            await client.send_file(TUJUAN, path, caption=teks_clean, reply_to=TOPIC_ID)
            if os.path.exists(path): os.remove(path)
        elif teks_clean:
            await client.send_message(TUJUAN, teks_clean, reply_to=TOPIC_ID)
        
        # Simpan ID terakhir untuk channel ini
        save_last_id(channel_id, message.id)
    except Exception as e:
        print(f"❌ Gagal: {e}")

# Monitoring Real-time untuk semua sumber
@client.on(events.NewMessage(chats=list(SUMBER_CONFIG.keys())))
async def handler(event):
    await proses_dan_kirim(event.message, event.chat_id)

async def main():
    await client.start()
    last_ids = get_last_ids()
    
    print("⏳ Menarik history dari berbagai sumber...")
    
    for ch_id, start_id in SUMBER_CONFIG.items():
        # Ambil ID terakhir yang tersimpan, jika tidak ada pakai start_id
        current_min = max(int(last_ids.get(str(ch_id), 0)), start_id)
        
        print(f"--- Channel {ch_id} mulai dari ID {current_min} ---")
        
        # Logika khusus jika channel tertentu butuh filter topic (seperti yang 151)
        reply_filter = 151 if ch_id == -1002186281759 else None
        
        async for msg in client.iter_messages(ch_id, min_id=current_min, reply_to=reply_filter, reverse=True):
            await proses_dan_kirim(msg, ch_id)
            await asyncio.sleep(2)

    print("📡 Semua history selesai. Bot Standby...")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
