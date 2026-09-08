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
