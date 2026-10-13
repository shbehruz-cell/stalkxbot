# Telegram Business Audit Bot

Python asosidagi Telegram bot: Business xabarlarining nusxasini audit uchun saqlaydi va faqat xabar tahrirlanganda yoki o'chirilganda egasiga bildirishnoma yuboradi.

## Muhim cheklovlar

- Bot foydalanuvchining barcha Telegram chatlarini ko'ra olmaydi. Faqat Telegram Business orqali botga ruxsat berilgan va Telegram Bot API yetkazadigan hodisalar keladi.
- Xabar o'chirilgani haqidagi `deleted_business_messages` hodisasi xabar ID raqamlarini beradi, ammo asl xabar matnini bermaydi. Matnni keyin tiklash imkoni yo'q.
- Telegram barcha holatlarda manba havolasini bermaydi. Ochiq username'li supergroup/kanal xabarlariga havola tuzish mumkin; shaxsiy chatlar uchun odatda universal havola yo'q.
- Business ulanishidagi huquqlar va Telegram API versiyasi xatti-harakatga ta'sir qilishi mumkin.
- Faqat o'zingiz boshqaradigan akkauntlar va rozilik berilgan suhbatlar uchun foydalaning. Maxfiylik va mahalliy qonunlarga rioya qiling.

## Imkoniyatlar

- `/start` — yo'riqnoma
- `/help` — yordam
- `/status` — bot ko'rgan Business ulanishlari holati
- SQLite bazasida ulanishlar va bot ko'rgan xabarlarning oxirgi nusxasini saqlash
- Tahrirlangan xabar uchun eski/yangi holatni ko'rsatish; yangi/almashtirilgan qismlar qalin yoziladi, o'chirilgan qism `...` bilan belgilanadi
- O'chirilgan xabar hodisasida bazadagi saqlangan nusxani ko'rsatish
- Yangi Business xabarlari bildirishnomasiz bazaga saqlanadi; faqat tahrirlash yoki o'chirish holatida egasiga xabar yuboriladi
- Log yozish, sozlamalarni `.env` orqali boshqarish
- HTML injeksiyasidan himoya: xabarlar oddiy matn ko'rinishida yuboriladi
- Ulanish holati ham bildirishnomasiz qayd etiladi; mazmuni o'zgarmagan tahrir hodisalari e'tiborsiz qoldiriladi

## Talablar

- Python 3.11+
- Telegram BotFather tokeni
- Bot bilan shaxsiy chatda `/start` yuborilgan bo'lishi kerak
- Telegram ilovasida Business akkaunt va Business Chatbots bo'limi mavjud bo'lishi kerak

## O'rnatish

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

`.env` faylini ochib `BOT_TOKEN` qiymatini o'zingizning tokeningizga almashtiring.

```powershell
python -m app.main
```

### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
cp .env.example .env
```

`.env` faylida `BOT_TOKEN` ni sozlang:

```bash
python -m app.main
```

## Telegram Business'ga ulash

1. BotFather'da bot yarating va token oling.
2. Botga shaxsiy chatdan `/start` yuboring.
3. Telegram ilovasida Settings → Telegram Business → Chatbots bo'limini oching (nomlanish ilova versiyasiga qarab farq qilishi mumkin).
4. Shu botni tanlang, Telegram ko'rsatgan chatlar va ruxsatlarni diqqat bilan ko'rib chiqing.
5. Kerakli ruxsatlarni o'zingiz tanlab, ulanishni tasdiqlang.
6. `/status` buyrug'i orqali bot olgan ulanish holatini tekshiring.

Bot faqat Telegram tomonidan yetkazilgan yangilanishlarni qayta ishlaydi. Business sozlamalaridagi barcha chatlar avtomatik ravishda botga ko'rinadi degani emas.

## Konfiguratsiya

`.env`:
- `BOT_TOKEN` — majburiy
- `DATABASE_PATH` — SQLite fayli (default `data/bot.sqlite3`)
- `LOG_LEVEL` — `INFO`, `DEBUG`, `WARNING` va boshqalar
- `MAX_MESSAGE_CHARS` — bildirishnomada ko'rsatiladigan matnning maksimal uzunligi (default 2500)
- `OWNER_NOTIFY` — `true` bo'lsa hodisalarni Business akkaunt egasiga yuboradi (default `true`)

## Ma'lumotlar va xavfsizlik

- Tokenni hech qachon GitHub, skrinshot yoki ommaviy chatga joylamang.
- `.env` va SQLite bazasi maxfiy hisoblanadi; ularga kirishni cheklang.
- Botni doimiy ishlatish uchun VPS/server va process manager (systemd/Docker) tavsiya etiladi.
- Bazaning zaxira nusxasini himoyalangan joyda saqlang.
- Bot taqqoslash va keyinchalik o'chirilgan xabarni ko'rsatish uchun Business xabarlarining oxirgi matnini SQLite bazasida saqlaydi. Bu maxfiy ma'lumot bo'lishi mumkin: server/faylga kirishni cheklang va bazani kerak bo'lsa o'chiring.
- Agar hodisalar ko'paysa, rate limit va navbat mexanizmini qo'shish kerak.

## Diagnostika

- Bot javob bermasa: tokenni, internet aloqasini va loglarni tekshiring.
- `/status` ulanish yo'q desa: Business Chatbots sozlamalarida bot haqiqatan ulanganini va kerakli ruxsatlar tanlanganini tekshiring.
- Hodisa kelmasa: bu API/ulanish huquqlari bilan bog'liq bo'lishi mumkin; botni barcha chatlar uchun universal kuzatuv vositasi deb hisoblamang.
- `Conflict: terminated by other getUpdates request` chiqsa, ayni token bilan boshqa polling jarayoni ishlamayotganini tekshiring.

## Testlar

```bash
python -m unittest discover -s tests -v
```

## Papkalar

```text
telegram_business_audit_bot/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── handlers.py
│   └── main.py
├── tests/
│   └── test_database.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```


## Tahrirlash va o'chirish arxivi

Bot ko'rgan yangi Business xabari va uning matni SQLite bazasiga yoziladi. Xabar tahrirlanganda bot bazadagi oldingi nusxa bilan yangi matnni taqqoslaydi:
- eski holat to'liq ko'rsatiladi;
- yangi holatda qo'shilgan/almashtirilgan matn qalin yoziladi;
- o'chirib tashlangan bo'lak yangi ko'rinishda `...` bilan belgilanadi.

Xabar o'chirilganda bot bazada mavjud nusxani bildirishnomada ko'rsatadi, so'ng o'sha snapshot yozuvini o'chiradi. Agar bot xabarni avval ko'rmagan bo'lsa, eski matnni tiklab bo'lmaydi.

**Maxfiylik:** bu funksiya xabar matnlarini saqlaydi. Faqat kerakli Business chatlari uchun ruxsat bering va SQLite bazasini begonalardan himoya qiling.


## Media fayllarini yetkazish

Rasm/video/fayl kabi media yangi xabar kelganida bildirishnomasiz saqlanadi. Media nusxasi faqat xabar tahrirlanganda (media o'zgargan bo'lsa) yoki xabar o'chirilganda audit xabariga qo'shimcha ravishda yuborishga uriniladi. Qo'llab-quvvatlanadigan media turlari:
- rasm, video, GIF/animatsiya;
- hujjat va boshqa Telegram fayllari;
- audio, ovozli xabar, video-xabar;
- stiker.

Tahrirlangan media uchun `copy_message` ishlamasa, bot bazada saqlangan Telegram `file_id` orqali mediani qayta yuborishga urinadi. Bu usul fayllarni serverga yuklab olishni talab qilmaydi va disk joyini tejaydi. Bot xabar o'chirilgandan keyin ham bazadagi `file_id` orqali media nusxasini yuborishga harakat qiladi. Telegram ba'zi fayllar uchun `file_id`dan qayta foydalanishni rad etsa, xabarnomada bu haqida yoziladi.

Matnli caption/izoh audit bildirishnomasida ham ko'rsatiladi. Albomdagi har bir media Telegram tomonidan alohida update sifatida kelishi mumkin, shuning uchun har biri alohida yuborilishi mumkin.

## Ko'p foydalanuvchiga moslash

- Telegram update'larini bir vaqtda qayta ishlash limiti 16 qilib sozlangan.
- HTTP ulanishlar havzasi 32 ta ulanishgacha kengaytirilgan.
- SQLite WAL rejimi va indekslardan foydalanadi.
- Media fayllari diskka yuklanmaydi; `file_id` saqlanadi.

Bu sozlamalar kichik va o'rta yuklama uchun yordam beradi. Juda katta trafikda bir nechta server nusxasini ishga tushirishdan oldin SQLite o'rniga PostgreSQL, navbat (masalan, Redis) va webhook/deploy arxitekturasiga o'tish kerak. Bitta polling bot tokeni bilan bir nechta nusxani bir vaqtda ishga tushirmang.

**Muhim:** bu Telegram API imkoniyatlariga bog'liq; bot faqat Business ulanishi ruxsat bergan va Telegram yuborgan hodisalarni oladi. Media xabarlarini foydalanuvchiga yuborishdan oldin akkaunt egasi bu audit funksiyasini ongli ravishda yoqishi va chat ruxsatlarini tekshirishi kerak.
