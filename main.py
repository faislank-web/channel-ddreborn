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

# TUJUAN: Channel Penerbangan Terakhir
TUJUAN_ID = -1003767837442 

LAST_ID_FILE = "last_ids.json"

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

def save_last_id(label, message_id):
    data = get_last_ids()
    data[str(label)] = message_id
    with open(LAST_ID_FILE, "w") as f:
        json.dump(data, f, indent=4)
    
    try:
        subprocess.run(["git", "config", "user.name", "GitHub Actions"])
        subprocess.run(["git", "config", "user.email", "actions@github.com"])
        subprocess.run(["git", "add", LAST_ID_FILE])
        subprocess.run(["git", "commit", "-m", f"Update {label}: {message_id} [skip ci]"])
        subprocess.run(["git", "push"])
    except: pass

def bersihkan_konten(teks, label):
    if not teks: return ""
    teks = re.sub(r'https?://\S+', '', teks)
    teks = re.sub(r't\.me/\S+', '', teks)
    teks = re.sub(r'@\S+', '', teks)
    
    # Hapus tanda kurung di awal judul (Contoh: [DL NIME])
    teks = re.sub(r'^\[.*?\]\s*', '', teks)
    
    mapping = {
        "New TV Show Added!": "Series Update",
        "New Movie Added!": "Movie Update",
        "New Episode Released": "Episode Baru Tersedia",
        "Download Via": "silakan Request ke Mimin",
    }
    for lama, baru in mapping.items():
        teks = teks.replace(lama, baru)
    return teks.strip()

async def proses_dan_kirim(message, label):
    teks_clean = bersihkan_konten(message.message, label)
    
    try:
        if message.media:
            path = await message.download_media()
            await client.send_file(TUJUAN_ID, path, caption=teks_clean)
            if os.path.exists(path): os.remove(path)
        elif teks_clean:
            await client.send_message(TUJUAN_ID, teks_clean)
        
        save_last_id(label, message.id)
        print(f"✅ Berhasil: {label} -> ID {message.id}")
    except Exception as e:
        print(f"❌ Error {label}: {e}")

# Handler Pesan Baru
@client.on(events.NewMessage(chats=[-1002183727075, -1002186281759]))
async def handler(event):
    # wgfilm21 -> Hanya Topik 153
    if event.chat_id == -1002183727075:
        if event.message.reply_to and event.message.reply_to.reply_to_msg_id == 153:
            await proses_dan_kirim(event.message, "wgfilm21")
    # Lulacloud Drama -> Umum
    elif event.chat_id == -1002186281759:
        await proses_dan_kirim(event.message, "lulacloud")

async def run_bot():
    print("🚀 Mencoba login ke Telegram...")
    await client.start()
    print("✅ Login Berhasil!")
    
    last_ids = get_last_ids()
    tugas = [
        {"id": -1002183727075, "start": 8823, "topic": 153, "label": "wgfilm21"},
        {"id": -1002186281759, "start": 33570, "topic": None, "label": "lulacloud"}
    ]

    for t in tugas:
        try:
            entity = await client.get_entity(t["id"])
            current_min = int(last_ids.get(t["label"], t["start"]))
            print(f"⏳ History {t['label']} mulai ID {current_min}...")
            
            async for msg in client.iter_messages(entity, min_id=current_min, reverse=True):
                if t["topic"]:
                    if msg.reply_to and msg.reply_to.reply_to_msg_id == t["topic"]:
                        await proses_dan_kirim(msg, t["label"])
                        await asyncio.sleep(4)
                else:
                    await proses_dan_kirim(msg, t["label"])
                    await asyncio.sleep(4)
        except Exception as e:
            print(f"⚠️ Melewati {t['label']}: {e}")

    print("📡 Bot SHeJUa Standby: Jalur ID Terverifikasi...")
    await client.run_until_disconnected()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(run_bot())
    except Exception as e:
        print(f"⚠️ Terhenti: {e}")
