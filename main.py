import re
import asyncio
import os
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# --- KONFIGURASI DARI GITHUB SECRETS ---
# Data ini diambil otomatis dari Settings > Secrets > Actions di GitHub kamu
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
SESSION_STRING = os.getenv('SESSION_STRING')

# --- KONFIGURASI TUJUAN & SUMBER ---
TUJUAN = -1002183727075
TOPIC_ID = 153
SUMBER_CHANNELS = [-1002186281759]

# Inisialisasi Client
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

def bersihkan_konten(teks, sumber):
    """Fungsi untuk merapikan pesan sesuai instruksi KaK"""
    if not teks: return ""
    
    # 1. Hapus Link & Username agar rapi
    teks = re.sub(r'https?://\S+', '', teks)
    teks = re.sub(r't\.me/\S+', '', teks)
    teks = re.sub(r'@' + re.escape(str(sumber)), '', teks, flags=re.IGNORECASE)
    
    # 2. Hapus tanda kurung di awal judul (Contoh: [DL NIME] Judul -> Judul)
    teks = re.sub(r'^\[.*?\]\s*', '', teks)
    
    # 3. Mapping Penggantian Teks Khusus
    mapping = {
        "New TV Show Added!": "Series Update",
        "New Movie Added!": "Movie Update",
        "New Episode Released": "Episode Baru Tersedia",
        "Download Via": "silakan Request ke Mimin"
    }
    
    for lama, baru in mapping.items():
        teks = teks.replace(lama, baru)
        
    return teks.strip()

async def proses_dan_kirim(message, username_asal):
    """Logika pengiriman pesan baik media maupun teks"""
    teks_clean = bersihkan_konten(message.message, username_asal)
    
    try:
        if message.media:
            # Download media ke server sementara GitHub
            path = await message.download_media()
            await client.send_file(TUJUAN, path, caption=teks_clean, reply_to=TOPIC_ID)
            if os.path.exists(path): os.remove(path)
        elif teks_clean:
            await client.send_message(TUJUAN, teks_clean, reply_to=TOPIC_ID)
        return True
    except Exception as e:
        print(f"❌ Gagal mengirim: {e}")
        return False

# --- HANDLER MONITORING REAL-TIME ---
@client.on(events.NewMessage(chats=SUMBER_CHANNELS))
async def handler(event):
    chat = await event.get_chat()
    username_asal = getattr(chat, 'username', "Sumber")
    await proses_dan_kirim(event.message, str(username_asal))
    print(f"✨ Pesan baru terdeteksi dan diteruskan!")

# --- FUNGSI TARIK HISTORY AWAL ---
async def tarik_history():
    print("⏳ Memulai penarikan history awal...")
    
    # 1. Tarik dari ID 8823 (Khusus Topic 151)
    print("--- Menarik History Topic 151 ---")
    async for msg in client.iter_messages(SUMBER_CHANNELS[0], min_id=8823, reply_to=151, reverse=True):
        await proses_dan_kirim(msg, "Sumber")
        await asyncio.sleep(1.5) # Jeda aman agar tidak kena limit
        
    # 2. Tarik dari ID 33570 (Umum/Tanpa Topic)
    print("--- Menarik History Umum (ID 33570) ---")
    async for msg in client.iter_messages(SUMBER_CHANNELS[0], min_id=33570, reverse=True):
        # Hanya ambil yang bukan bagian dari reply/topic tertentu jika ingin dipisah
        if not msg.reply_to:
            await proses_dan_kirim(msg, "Sumber")
            await asyncio.sleep(1.5)

    print("✅ Semua history berhasil ditarik.")

async def main():
    print("🚀 Bot SHeJUa sedang login...")
    await client.start()
    
    # Jalankan penarikan history dulu sebelum standby
    await tarik_history()
    
    print("📡 Bot sekarang STANDBY dan MONITORING REAL-TIME...")
    await client.run_until_disconnected()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("👋 Bot dimatikan.")
