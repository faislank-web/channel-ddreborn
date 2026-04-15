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
client = TelegramClient(
    StringSession(SESSION_STRING), 
    API_ID, 
    API_HASH,
    connection_retries=15,
    retry_delay=10
)

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
    
    try:
        subprocess.run(["git", "config", "user.name", "GitHub Actions"])
        subprocess.run(["git", "config", "user.email", "actions@github.com"])
        subprocess.run(["git", "add", LAST_ID_FILE])
        subprocess.run(["git", "commit", "-m", f"Update ID {channel_id}: {message_id} [skip ci]"])
        subprocess.run(["git", "push"])
    except: pass

def bersihkan_konten(teks, sumber):
    if not teks: return ""
    # Hapus semua link http/https dan t.me
    teks = re.sub(r'https?://\S+', '', teks)
    teks = re.sub(r't\.me/\S+', '', teks)
    teks = re.sub(r'@' + re.escape(str(sumber)), '', teks, flags=re.IGNORECASE)
    
    # Hapus tanda kurung di awal judul (Contoh: [DL NIME])
    teks = re.sub(r'^\[.*?\]\s*', '', teks)
    
    mapping = {
        "New TV Show Added!": "Series Update",
        "New Movie Added!": "Movie Update",
        "New Episode Released": "Episode Baru Tersedia",
        "Download Via": "silakan Request ke Mimin",
        "WGFILM21": "" # Membersihkan kata WGFILM21
    }
    for lama, baru in mapping.items():
        teks = teks.replace(lama, baru)
    return teks.strip()

async def proses_dan_kirim(message, channel_id):
    chat = await message.get_chat()
    username_asal = getattr(chat, 'username', "Sumber")
    teks_clean = bersihkan_konten(message.message, str(username_asal))
    
    try:
        # Kirim ke Topic 153 di channel tujuan
        if message.media:
            path = await message.download_media()
            await client.send_file(TUJUAN, path, caption=teks_clean, reply_to=TOPIC_ID_TUJUAN)
            if os.path.exists(path): os.remove(path)
        elif teks_clean:
            await client.send_message(TUJUAN, teks_clean, reply_to=TOPIC_ID_TUJUAN)
        
        save_last_id(channel_id, message.id)
        print(f"✅ Berhasil Kirim: ID {message.id}")
    except Exception as e:
        print(f"❌ Error saat kirim: {e}")

# Handler untuk pesan baru (Real-time)
@client.on(events.NewMessage(chats=[-1002186281759, -1002233445566]))
async def handler(event):
    if event.chat_id == -1002186281759:
        # Hanya ambil jika pesan masuk ke Topic 153
        if event.message.reply_to and event.message.reply_to.reply_to_msg_id == 153:
            await proses_dan_kirim(event.message, event.chat_id)
    else:
        # Channel kedua (Umum) ambil semua
        await proses_dan_kirim(event.message, event.chat_id)

async def run_bot():
    print("🚀 Mencoba login ke Telegram...")
    await client.start()
    print("✅ Login Berhasil!")
    
    last_ids = get_last_ids()
    # Topic disetel ke 153 sesuai link yang KaK berikan
    tugas = [
        {"id": -1002186281759, "start": 8823, "topic": 153},
        {"id": -1002233445566, "start": 33570, "topic": None}
    ]

    for t in tugas:
        ch_id = t["id"]
        current_min = int(last_ids.get(str(ch_id), t["start"]))
        print(f"⏳ Menarik history {ch_id} (Topik {t['topic']}) mulai ID {current_min}...")
        
        async for msg in client.iter_messages(ch_id, min_id=current_min, reverse=True):
            if t["topic"] is not None:
                # Filter manual agar hanya mengambil dari Topik 153
                if msg.reply_to and msg.reply_to.reply_to_msg_id == t["topic"]:
                    await proses_dan_kirim(msg, ch_id)
                    await asyncio.sleep(4)
            else:
                await proses_dan_kirim(msg, ch_id)
                await asyncio.sleep(4)

    print("📡 Bot SHeJUa Standby memantau pesan baru...")
    await client.run_until_disconnected()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(run_bot())
    except Exception as e:
        print(f"⚠️ Terhenti karena: {e}")
