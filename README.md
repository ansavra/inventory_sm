# 📦 ប្រព័ន្ធគ្រប់គ្រងស្តុកតាម Telegram (Telegram Inventory Management System)

ប្រព័ន្ធនេះត្រូវបានបង្កើតឡើងដោយប្រើប្រាស់ភាសា **Python** រួមជាមួយ **SQLite Database** និងភ្ជាប់ទៅកាន់ **Telegram Bot API** ដើម្បីជួយឱ្យការគ្រប់គ្រងទំនិញ នាំចូល-នាំចេញ ពិនិត្យស្តុក និងជូនដំណឹងស្តុកជិតអស់ មានភាពរហ័ស ងាយស្រួល និងអាចបញ្ជាការងារបានគ្រប់ទីកន្លែងតាមទូរសព្ទដៃ។

---

## 🌟 មុខងារសំខាន់ៗ (Key Features)

1. **📦 ពិនិត្យស្តុក (Check Stock):**
   - មើលបញ្ជីទំនិញក្នុងស្តុកទាំងអស់ និងចំនួនជាក់ស្តែង
   - ស្វែងរកទំនិញរហ័សតាមឈ្មោះ ឬលេខកូដ (SKU/Barcode)
   - មើលព័ត៌មានលម្អិត ទីតាំងទុកដាក់ និងតម្លៃ

2. **📥 នាំចូលទំនិញ (Stock In):**
   - បញ្ចូលចំនួនទំនិញទិញចូលបន្ថែម
   - កត់ត្រាតម្លៃទិញចូលក្នុង ១ឯកតា និងគណនាចំណាយសរុប
   - កត់ត្រាប្រភពផ្គត់ផ្គង់ ឬលេខវិក្កយបត្រ

3. **📤 នាំចេញ / កាត់ស្តុក (Stock Out):**
   - កាត់ស្តុកពេលលក់ចេញ ឬខូចខាត
   - ប្រព័ន្ធការពារមិនឱ្យកាត់លើសចំនួនស្តុកដែលមានជាក់ស្តែង (Prevent Negative Stock)
   - គណនាចំណូល និងកត់ត្រាមូលហេតុ

4. **➕ បន្ថែមទំនិញថ្មី (Add New Product):**
   - បង្កើតមុខទំនិញថ្មីដោយកំណត់ កូដ, ឈ្មោះ, ប្រភេទ, ខ្នាត, តម្លៃដើម, តម្លៃលក់, ចំនួនដំបូង, ទីតាំង និងកម្រិតសុវត្ថិភាព

5. **⚠️ ការជូនដំណឹងស្តុកជិតអស់ (Low Stock Alert):**
   - ជូនដំណឹងស្វ័យប្រវត្តិភ្លាមៗនៅពេលកាត់ស្តុកដល់កម្រិតកំណត់ (Reorder Level)
   - ប៊ូតុងពិនិត្យបញ្ជីទំនិញដែលត្រូវការទិញចូលបន្ថែមជាបន្ទាន់

6. **📊 របាយការណ៍សង្ខេប (Reports):**
   - របាយការណ៍សង្ខេបប្រចាំថ្ងៃ (ចំនួនដងនាំចូល/នាំចេញ, បរិមាណសរុប, ចំណាយ/ចំណូលសរុប)
   - ប្រវត្តិប្រតិបត្តិការចុងក្រោយ (Transaction Logs)

7. **📷 ស្កេន Barcode / QR Code ពីរូបថត:**
   - អាចថតរូប Barcode ឬ QR code លើកញ្ចប់ទំនិញផ្ញើចូល Bot វានឹងស្វែងរកទំនិញនោះភ្លាមៗ

8. **🔐 កំណត់សិទ្ធិប្រើប្រាស់ (Admin & Staff):**
   - **Admin (ម្ចាស់ហាង/អ្នកគ្រប់គ្រង):** មើលឃើញតម្លៃដើម ចំណេញ/ខាត ចំណាយសរុប បន្ថែមទំនិញថ្មី និងមើលបញ្ជីបុគ្គលិក
   - **Staff (បុគ្គលិក):** ពិនិត្យស្តុក នាំចូល នាំចេញ និងស្កេនទំនិញ

---

## 🛠️ របៀបតម្លើង និងដំណើរការ (Installation & Setup)

### ជំហានទី ១៖ យក Telegram Bot Token និង User ID
1. ចូលទៅកាន់ Telegram ហើយស្វែងរក **[@BotFather](https://t.me/BotFather)**
2. វាយពាក្យ `/newbot` រួចធ្វើតាមការណែនាំដើម្បីបង្កើត Bot និងទទួលបាន **API Token**
3. ដើម្បីដឹងពី **Telegram User ID** របស់អ្នក៖ ចូលទៅកាន់ **[@userinfobot](https://t.me/userinfobot)** រួចចុច Start វានឹងបង្ហាញលេខ ID របស់អ្នក (ឧ. `123456789`)

### ជំហានទី ២៖ កំណត់ឯកសារ `.env`
ចម្លងឯកសារ `.env.example` ទៅជា `.env` រួចបំពេញព័ត៌មាន៖
```env
TELEGRAM_BOT_TOKEN=លេខ_BOT_TOKEN_របស់អ្នក
ADMIN_USER_IDS=លេខ_USER_ID_របស់អ្នក
DATABASE_PATH=inventory.db
```

### ជំហានទី ៣៖ ដំឡើងបណ្ណាល័យ Python (Dependencies)
បើក Command Prompt ឬ PowerShell ក្នុងថតគម្រោង រួចដំណើរការ៖
```bash
# បង្កើត Virtual Environment (ប្រសិនបើមិនទាន់មាន)
python -m venv .venv

# Activate Virtual Environment
.venv\Scripts\activate

# តម្លើងបណ្ណាល័យចាំបាច់
pip install -r requirements.txt
```

### ជំហានទី ៤៖ សាកល្បងដំណើរការតេស្ត Database
```bash
python test_database.py
```

### ជំហានទី ៥៖ ដំណើរការ Bot
```bash
python main.py
```
បន្ទាប់មកចូលទៅកាន់ Bot របស់អ្នកលើ Telegram ហើយចុច `/start`!

---

## 📁 រចនាសម្ព័ន្ធឯកសារក្នុងគម្រោង

```
d:/Telegrambot inventory system SM/
│
├── config.py                 # ផ្ទុកការកំណត់ Token, Admin IDs, Database Path
├── database.py               # SQLite Database Logic & CRUD Functions
├── keyboards.py              # ប៊ូតុងបញ្ជាលើអេក្រង់ជាភាសាខ្មែរ
├── handlers/
│   ├── common.py             # /start, /help, Cancel handler
│   ├── inventory.py          # ពិនិត្យស្តុក & ស្វែងរកទំនិញ
│   ├── stock_in.py           # ដំណើរការនាំចូលទំនិញ (Stock In Flow)
│   ├── stock_out.py          # ដំណើរការនាំចេញ/កាត់ស្តុក (Stock Out Flow)
│   ├── product_mgmt.py       # ដំណើរការបន្ថែមទំនិញថ្មី (Add Product)
│   ├── reports.py            # របាយការណ៍សង្ខេបប្រចាំថ្ងៃ និងប្រវត្តិ
│   ├── barcode_scanner.py    # ស្កេនរូបថត Barcode/QR Code
│   └── admin.py              # គ្រប់គ្រងអ្នកប្រើប្រាស់សម្រាប់ Admin
├── main.py                   # ឯកសារមេសម្រាប់ដំណើរការ Bot (Entry Point)
├── requirements.txt          # បញ្ជី Packages
├── test_database.py          # Script តេស្តប្រព័ន្ធ Database ដោយស្វ័យប្រវត្តិ
├── .env.example              # គំរូឯកសារបរិស្ថាន
└── README.md                 # សៀវភៅណែនាំ
```

## ☁️ រក្សាទុកទិន្នន័យអចិន្ត្រៃយ៍លើ Render (Persistent Disk)

Container លើ Render ត្រូវបាន rebuild រាល់ពេល deploy ដូច្នេះ SQLite ក្នុង container នឹងបាត់។ ដើម្បីរក្សាទុក៖

1. Render Dashboard → service → **Disks** → **Add Disk**
   - Name: `inventory-data`, Mount Path: `/data`, Size: `1 GB` (ត្រូវការ plan Starter ឡើងទៅ)
2. **Environment** → Add: `DATABASE_PATH` = `/data/inventory.db`
3. **Manual Deploy → Deploy latest commit**

លើកដំបូង ប្រព័ន្ធនឹងចម្លង `inventory.db` ពី repo ទៅ `/data/` ដោយស្វ័យប្រវត្តិ (seed) បន្ទាប់មកទិន្នន័យទាំងអស់នឹងរក្សាទុកនៅលើ disk ជាអចិន្ត្រៃយ៍។

## 🚀 បើកកម្មវិធីដោយមិនបង្ហាញផ្ទាំង CMD (Hidden Mode)

| ឯកសារ | មុខងារ |
|---|---|
| `បើកកម្មវិធី.vbs` | បើក **Web Dashboard តែប៉ុណ្ណោះ** (Local/Wi-Fi) ដោយលាក់ផ្ទាំង CMD (browser បើកដោយស្វ័យប្រវត្តិ) — Telegram Bot **មិន**ត្រូវបានបើកទេ ដើម្បីជៀសវាង `telegram.error.Conflict` ពេល Bot token ដូចគ្នាកំពុងដំណើរការនៅ Cloud |
| `START_SYSTEM_HIDDEN.vbs` | Web Dashboard + Telegram Bot + Cloudflare Tunnel (Internet) |
| `STOP_SYSTEM.bat` | បិទប្រព័ន្ធទាំងអស់ (Web + Bot + Tunnel) |
| `run.bat` / `START_SYSTEM.bat` | របៀបចាស់ — បង្ហាញផ្ទាំង CMD (ចុច Ctrl+C ដើម្បីបិទ) |

🤖 **ចង់បើក Telegram Bot ក្នុង Local ផង?** កំណត់ environment variable `SM_WITH_BOT=1` មុនពេលរត់ `run_local.py` (ឧ. `set SM_WITH_BOT=1` ក្នុង CMD) ឬកែ `បើកកម្មវិធី.vbs` ដោយបន្ថែមបន្ទាត់ `sh.Environment("PROCESS")("SM_WITH_BOT") = "1"` នៅក្រោមបន្ទាត់ `SM_HIDDEN`។ ពេល Bot បិទ, navbar នៅលើ Dashboard នឹងបង្ហាញ "💻 Local Mode (គ្មាន Bot)" (ការជូនដំណឹងទៅ Telegram តាម `notifier.py` នៅតែដំណើរការធម្មតា)។

ក្នុង Hidden mode, output ទាំងអស់ត្រូវសរសេរទៅ `logs/launcher.log`, `logs/web.log` និង `logs/bot.log` (បើ Bot បើក)។
💡 ចង់ឱ្យបើកដោយស្វ័យប្រវត្តិពេលបើកកុំព្យូទ័រ៖ ចុចស្តាំលើ `បើកកម្មវិធី.vbs` → Create shortcut → ដាក់ shortcut ចូល folder `shell:startup`។

## ☁️ Vercel + Supabase (Cloud)

### ១. Supabase (ទិន្នន័យ)
តារាងទាំងអស់ស្ថិតក្នុង schema **`sm`** (ដាច់ពីតារាងផ្សេងក្នុង project ដដែល) ហើយបើក RLS រួចរាល់។

1. Supabase Dashboard → Project Settings → Database → Connection string → **URI** → **Transaction pooler**
2. ដាក់ក្នុង `.env`៖ `DATABASE_URL=postgresql://postgres.<ref>:<PASSWORD>@...pooler.supabase.com:6543/postgres`
3. រត់៖ `.venv\Scripts\python.exe setup_supabase.py --from inventory.db`

ពេលមាន `DATABASE_URL` ប្រព័ន្ធប្រើ Supabase ដោយស្វ័យប្រវត្តិ (ទាំង local និង cloud); បើគ្មាន វាប្រើ SQLite ដដែល។

### ២. Vercel (Web Dashboard)
1. vercel.com → **Add New → Project** → Import repo `ansavra/inventory_sm`
2. Environment Variables ត្រូវបន្ថែម៖

| Key | តម្លៃ |
|---|---|
| `DATABASE_URL` | Connection string ពី Supabase (Transaction pooler) |
| `DB_SCHEMA` | `sm` |
| `APP_TZ` | `Asia/Phnom_Penh` |
| `TELEGRAM_BOT_TOKEN` | Token ពី @BotFather |
| `ADMIN_USER_IDS` | Telegram ID របស់អ្នកគ្រប់គ្រង |
| `TELEGRAM_WEBHOOK_SECRET` | អក្សរចៃដន្យវែងៗ (ឧ. 32 តួ) |

3. Deploy រួច → Login → tab **គ្រប់គ្រងបុគ្គលិក** → កាត **🔗 Telegram Bot Webhook** → ចុច «ចុះឈ្មោះ Webhook»

### ៣. Telegram Bot
- **លើ Vercel**៖ ប្រើ Webhook (state នៃសន្ទនារក្សាក្នុងតារាង `bot_state`)
- **ក្នុង local**៖ ប្រើ Polling — ត្រូវចុច «លុប Webhook» ជាមុនសិន បើមិនដូច្នេះវានឹងប៉ះទង្គិចគ្នា
- ការស្កេន Barcode/QR ដំណើរការតែក្នុង local (Vercel គ្មាន library `libzbar`)
