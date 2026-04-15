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

# TUJUAN: Channel Penerbangan Terakhir (Tanpa Topik)
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

def bersihkan_konten(teks, sumber_username):
    if not teks: return ""
    teks = re.sub(r'https?://\S+', '', teks)
    teks = re.sub(r't\.me/\S+', '', teks)
    teks = re.sub(r'@' + re.escape(str(sumber_username)), '', teks, flags=re.IGNORECASE)
    
    # Menghapus tanda kurung di awal judul (Contoh: [DL NIME]) sesuai permintaan KaK
    teks = re.sub(r'^\[.*?\]\s*', '', teks)
    
    mapping = {
        "New TV Show Added!": "Series Update",
        "New Movie Added!": "Movie Update",
        "New Episode Released": "Episode Baru Tersedia",
        "Download Via": "silakan Request ke Mimin",
        "WGFILM21": "",
        "lulacloud_drama": ""
    }
    for lama, baru in mapping.items():
        teks = teks.replace(lama, baru)
    return teks.strip()

async def proses_dan_kirim(message, channel_label):
    chat = await message.get_chat()
    username_asal = getattr(chat, 'username', channel_label)
    teks_clean = bersihkan_konten(message.message, username_asal)
    
    try:
        # Kirim langsung ke channel tujuan (Penerbangan Terakhir) tanpa topik
        if message.media:
            path = await message.download_media()
            await client.send_file(TUJUAN_ID, path, caption=teks_clean)
            if os.path.exists(path): os.remove(path)
        elif teks_clean:
            await client.send_message(TUJUAN_ID, teks_clean)
        
        save_last_id(channel_label, message.id)
        print(f"✅ Berhasil Kirim ke Penerbangan Terakhir: ID {message.id} dari {channel_label}")
    except Exception as e:
        print(f"❌ Error saat kirim: {e}")

# Handler untuk pesan baru
@client.on(events.NewMessage(chats=['wgfilm21', -1002186281759]))
async def handler(event):
    if 'wgfilm21' in str(event.chat):
        # Sumber 1: Hanya jika masuk ke Topik 153
        if event.message.reply_to and event.message.reply_to.reply_to_msg_id == 153:
            await proses_dan_kirim(event.message, 'wgfilm21')
    else:
        # Sumber 2: Ambil semua pesan
        await proses_dan_kirim(event.message, 'lulacloud_drama')

async def run_bot():
    print("🚀 Mencoba login ke Telegram...")
    await client.start()
    print("✅ Login Berhasil!")
    
    last_ids = get_last_ids()
    tugas = [
        {"id": 'wgfilm21', "start": 8823, "topic": 153},
        {"id": -1002186281759, "start": 33570, "topic": None} # lulacloud_drama
    ]

    for t in tugas:
        try:
            entity = await client.get_entity(t["id"])
            current_min = int(last_ids.get(str(t["id"]), t["start"]))
            print(f"⏳ Menarik history {t['id']} mulai ID {current_min}...")
            
            async for msg in client.iter_messages(entity, min_id=current_min, reverse=True):
                if t["topic"]:
                    if msg.reply_to and msg.reply_to.reply_to_msg_id == t["topic"]:
                        await proses_dan_kirim(msg, str(t["id"]))
                        await asyncio.sleep(4)
                else:
                    await proses_dan_kirim(msg, str(t["id"]))
                    await asyncio.sleep(4)
        except Exception as e:
            print(f"⚠️ Gagal akses sumber {t['id']}: {e}")

    print("📡 Bot Standby: Memantau wgfilm21 & lulacloud -> Penerbangan Terakhir...")
    await client.run_until_disconnected()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(run_bot())
    except Exception as e:
        print(f"⚠️ Terhenti: {e}")
