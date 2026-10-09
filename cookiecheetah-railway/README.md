# CookieCheetah Bot (Railway)

บอทตัวใหม่แทน CHEF — ไม่ใช้ akapanel แล้ว ทุกอย่างอยู่ใน Discord

- **ข้อความต้อนรับ** แบบเดิม (รูปหัว + 3 ขั้นตอน + ปุ่ม 📜 กฎ-ข้อต้องห้าม + ปุ่ม 🍪 Join)
- **Join / เปิด Ticket → เลือกหมวด**: 📝 ขอ White List (เฉพาะคนที่ยังไม่มี) · 💝 Donate · 🐛 แจ้งบั๊ก · 🚨 รีพอร์ต · 💬 ติดต่อแอดมิน
- ทุก ticket เป็น **thread ส่วนตัวในห้อง ticket ห้องเดียว** (ไม่สร้างห้องใหม่) เห็นแค่เจ้าของ + ทีมแอดมิน
- **White List + เช็ค Steam**: ผู้เล่นพิมพ์ Steam ID/ลิงก์ → บอทเช็คกับ Steam (มีจริงไหม, อายุบัญชี, มีเกม PZ ไหม, เคยโดนแบนไหม, Steam นี้มีคนใช้แล้วไหม) → แอดมินกด ✅ อนุมัติ / ❌ ไม่ผ่าน
- **Donate ผ่าน Stripe**: ใส่รหัส+จำนวน (สูงสุด 5 รายการต่อรอบ) → การ์ดสรุป → ✅ ยืนยัน → บิล PromptPay QR / บัตร → จ่ายแล้วมีการ์ดยืนยัน + ปุ่ม 📦 ให้แอดมินติ๊กว่าส่งของแล้ว
- แอดมินจัดการรายการ Donate เองใน Discord ด้วย `/item` (ตั้งรหัสเอง แก้ชื่อ/ยอด/เปิด-ปิดได้หมด)

---

## 1. เอาไฟล์ขึ้น GitHub (ทับของเก่า)

**ลบไฟล์เก่าใน repo `bot-discord-main` ทั้งหมด** — ไฟล์พวกนี้ไม่ใช้แล้ว:

```
orchestra_bot.py  main.py  panel_db.py  routes_addon.py  steam_utils.py
admin_cog.py  channel_shop_cog.py  event_cog.py  market_cog.py  member_cog.py
order_receipt_cog.py  pass_cog.py  roles_cog.py  shop_cog.py  spin_cog.py
steam_cog.py  topup_cog.py  welcome_cog.py
bot_shared.py  bot_shared_addon.py  bot_shared_addon_v3.py
bot_shared_member.py  bot_shared_onboarding.py  bot_shared_pass.py
```

แล้ววางไฟล์ชุดนี้แทน (`Dockerfile`, `railway.toml`, `requirements.txt`, `.gitignore` ทับของเดิมได้เลย):

```
bot.py
requirements.txt
Dockerfile
railway.toml
.env.example        ← ตัวอย่าง Variables (ไม่มีรหัสจริง อัปขึ้นได้)
.gitignore
.dockerignore
assets/README.txt   ← วาง banner.png ในโฟลเดอร์นี้ถ้าอยากได้รูปหัวข้อความต้อนรับ
README.md
```

> ⚠️ อย่าอัปไฟล์ `.env` ที่มีรหัสจริงขึ้น GitHub — รหัสทั้งหมดใส่ใน Railway Variables

ถ้าใช้ git:

```bash
git rm -q orchestra_bot.py main.py panel_db.py routes_addon.py steam_utils.py *_cog.py bot_shared*.py
# ก๊อปไฟล์ชุดใหม่มาวางทับในโฟลเดอร์ repo
git add -A
git commit -m "เปลี่ยนเป็นบอทใหม่: ticket thread + Steam + Donate Stripe"
git push
```

(หรือใช้หน้าเว็บ GitHub: ลบทีละไฟล์ แล้ว **Add file → Upload files** ลากไฟล์ใหม่ใส่)

---

## 2. ตั้งค่า Railway

### 2.1 Variables

service บอท → **Variables**

**ลบ** (ของบอทเก่า/akapanel ไม่ใช้แล้ว):
`PANEL_URL` `BOT_API_KEY` `PANEL_PORT` `PORT` `OWNER_USERNAME` `OWNER_PASSWORD` `SLIP2GO_API_KEY` `DATABASE_PATH` `UPLOAD_DIR`

**เก็บไว้**: `DISCORD_TOKEN` `STEAM_API_KEY`

**เพิ่ม**: กด **Raw Editor** → วางเนื้อหาจาก `.env.example` → ใส่ค่า (ตัวที่มีอยู่แล้วไม่ต้องใส่ซ้ำ) → **Update Variables**

ต้องมีอย่างน้อย:

| Variable | ใส่อะไร |
|---|---|
| `GUILD_ID` | ID เซิฟ Discord |
| `ROLE_SURVIVOR` | role ที่ได้หลังผ่าน White List |
| `ROLE_STAFF` | role ทีมแอดมิน (หลายอันคั่นด้วย `,`) |
| `TICKET_CHANNEL_ID` | ห้อง ticket ห้องเดียว (ห้องข้อความ ไม่ใช่ category) |
| `TRANSCRIPT_CHANNEL_ID` | ห้องเก็บบทสนทนาตอนปิด ticket |
| `STRIPE_SECRET_KEY` | ใส่เมื่อพร้อมเปิด Donate (ดูข้อ 4) |

แนะนำเพิ่ม: `RULES_CHANNEL_ID` (ปุ่ม 📜 จะลิงก์ไปห้องนี้), `MOD_LOG_CHANNEL_ID`, `WHITELIST_LOG_CHANNEL_ID`, `DONATE_LOG_CHANNEL_ID`, `SECRET_CODE`, `CONNECT_INFO_CHANNEL_ID`

> หา ID: Discord → User Settings → Advanced → เปิด **Developer Mode** → คลิกขวาที่ห้อง/role/เซิฟ → **Copy ID**

### 2.2 Volume (สำคัญ — ไม่งั้นข้อมูลหายทุกครั้งที่ deploy)

หน้า Project → คลิกขวาที่ service บอท → **Attach Volume** (หรือกด Ctrl+K พิมพ์ `volume`) → Mount path: `/data`

บอทเก็บ ticket, White List, Steam ที่ผูกไว้, รายการ Donate, ออร์เดอร์ ไว้ใน Volume นี้ (ถ้า service เดิมมี Volume อยู่แล้วก็ใช้ต่อได้เลย)

### 2.3 Deploy

push ขึ้น GitHub แล้ว Railway จะ build ใหม่เอง → ดู **Deploy Logs** ต้องเห็น:

```
ออนไลน์แล้ว: CHEF#xxxx
เซิฟ: CookieCheetah — พิมพ์ /check ใน Discord เพื่อตรวจสิทธิ์
```

ถ้าขึ้น `Variables ใน Railway ยังไม่ครบ / ไม่ถูกต้อง` บอทจะบอกว่าขาดตัวไหน
(ถ้า Settings → Deploy → Start Command ยังเป็น `python orchestra_bot.py` ให้ลบออก — ไฟล์ `railway.toml` ตั้งเป็น `python bot.py` ให้แล้ว)

Public Domain ของ service เดิม (ที่เคยใช้กับ panel) ลบได้ บอทตัวนี้ไม่ต้องใช้

---

## 3. ตั้งค่า Discord

### 3.1 Developer Portal
https://discord.com/developers/applications → บอท → **Bot** → เปิด **MESSAGE CONTENT INTENT** (ใช้ทำ transcript)

### 3.2 role บอท
Server Settings → Roles → ลาก role บอท **ขึ้นไปไว้เหนือ** Survivor (และ Member ถ้าใช้) — ไม่งั้นแจก role ไม่ได้

### 3.3 ห้อง ticket (ห้องเดียว ทุก ticket อยู่ในนี้)
สร้างห้องข้อความ เช่น `🎫ticket` → Edit Channel → Permissions:

| ใคร | ✅ อนุญาต | ❌ ปิด |
|---|---|---|
| @everyone | View Channel · Send Messages in Threads · Read Message History | Send Messages · Create Public Threads · Create Private Threads |
| role ทีมแอดมิน | View Channel · Send Messages in Threads · **Manage Threads** · Read Message History | |
| role บอท | View Channel · Send Messages · Send Messages in Threads · **Create Private Threads** · **Manage Threads** · Embed Links · Attach Files · Read Message History | |

- **Manage Threads** = ทีมแอดมินเห็น thread ส่วนตัวทุกอัน (คนอื่นเห็นแค่ของตัวเอง)
- @everyone ต้องเห็นห้องนี้ เพราะคนที่ยังไม่มี role ต้องคุยใน ticket ขอ White List ของตัวเองได้

### 3.4 ห้องอื่นๆ
ห้อง transcript / log ทั้งหลาย: ให้ role บอท View Channel + Send Messages + Embed Links + Attach Files (และปิดไม่ให้ผู้เล่นเห็น)

### 3.5 ตรวจด้วย /check
พิมพ์ `/check` ในเซิฟ → บอทบอกทุกจุดที่ขาด (สิทธิ์ห้อง, ลำดับ role, Steam key, Stripe, Volume) แก้ตามที่บอกจนเป็น ✅

---

## 4. ตั้งค่า Stripe (Donate)

1. บัญชี Stripe ต้องเป็น **ประเทศไทย** (PromptPay ใช้ได้เฉพาะบัญชีไทย สกุล THB)
2. Stripe Dashboard → **Settings → Payments → Payment methods** → เปิด **PromptPay** (และ Cards ถ้าต้องการ)
3. **Developers → API keys** → ก๊อป **Secret key**
   - ทดสอบก่อน: เปิด **Test mode** → key ขึ้นต้น `sk_test_...`
   - ใช้จริง: ปิด Test mode → `sk_live_...`
   - (ทางเลือกปลอดภัยกว่า) **Create restricted key** → ให้สิทธิ์ **Checkout Sessions: Write** อย่างเดียว → ได้ `rk_live_...`
4. ใส่ใน Railway Variables → `STRIPE_SECRET_KEY=...` → บอท restart เอง
5. `/check` ต้องขึ้น `✅ Stripe ต่อได้ — โหมดทดสอบ (test)` หรือ `โหมดจริง (live)`

> ไม่ต้องตั้ง Webhook หรือโดเมน — บอทเช็คบิลกับ Stripe เองทุก ~20 วินาที (ผู้เล่นกด 🔄 เช็คสถานะ ได้ทันที)
>
> ตอน Test mode หน้าจ่ายเงินจะมีปุ่มให้กดจำลองว่า "จ่ายสำเร็จ" — ลองทั้ง flow ก่อนเปลี่ยนเป็น `sk_live_`

---

## 5. ใช้งาน

### ส่งข้อความต่างๆ ลงห้อง
| คำสั่ง | ทำอะไร |
|---|---|
| `/panel kind:welcome` | ข้อความต้อนรับ + ปุ่ม 📜 กฎ / 🍪 Join (ใช้ในห้อง welcome) |
| `/panel kind:ticket` | ปุ่ม 🎫 เปิด Ticket (เลือกหมวด) — วางในห้อง ticket ได้เลย |
| `/panel kind:donate` | รายการ Donate + วิธีใช้ + ปุ่ม 💝 Donate (ห้องสาธารณะ) |

ใส่ `channel:` เพื่อส่งไปห้องอื่นได้ · รูปหัวข้อความต้อนรับ: วาง `assets/banner.png` ใน repo หรือใส่ลิงก์ใน `WELCOME_BANNER_URL`

> ข้อความ `/panel donate` เป็นภาพ ณ ตอนส่ง — แก้รายการแล้วอยากให้ป้ายอัปเดต ลบอันเก่าแล้วส่ง `/panel kind:donate` ใหม่ (ในห้อง Donate ส่วนตัวของผู้เล่นจะดึงรายการล่าสุดเสมอ)

### จัดการรายการ Donate (`/item` — แอดมิน)
```
/item add    code:A01 name:ปืนพก M9 + กระสุน price:50 description:ส่งในเกมภายใน 24 ชม. sort:1
/item edit   code:A01 price:59            ← ใส่เฉพาะช่องที่จะแก้
/item edit   code:A01 new_code:GUN1       ← เปลี่ยนรหัส
/item edit   code:A01 active:False        ← ปิดชั่วคราว (ผู้เล่นไม่เห็น)
/item edit   code:A01 description:-       ← ลบคำอธิบาย
/item remove code:A01
/item list                                 ← ดูทั้งหมดรวมที่ปิดอยู่
```
รหัสใช้ อังกฤษ/ตัวเลข/`_`/`-` ไม่เกิน 20 ตัว (ไม่สนตัวพิมพ์เล็กใหญ่) · ราคาใส่เป็นบาท เช่น `50` หรือ `49.50`

### ออร์เดอร์ (`/order` — ทีมแอดมิน)
```
/order list                    ← จ่ายแล้ว รอส่งของ (เลือกสถานะอื่นได้)
/order deliver order_id:12     ← ติ๊กว่าส่งของแล้ว (เหมือนกดปุ่ม 📦)
/order check order_id:12       ← เช็คกับ Stripe ทันที
```

### ticket / White List / Steam
```
/ticket add member:@x · /ticket remove member:@x · /ticket close reason:...
/whitelist remove member:@x (หรือ username:...)   ← ถอด role + ให้คำสั่ง removeuserfromwhitelist
/whitelist info member:@x
/steam info member:@x · /steam lookup steam_id:... · /steam unlink member:@x
```

> คำสั่งแอดมินซ่อนจากผู้เล่นทั่วไป (`/check /panel /item /rcon` เห็นเฉพาะคนมี Manage Server, ที่เหลือเห็นเฉพาะคนมี Manage Threads) — ปรับได้ที่ Server Settings → Integrations → บอท

---

## 6. Flow ฝั่งผู้เล่น

**ขอ White List**
1. กด 🍪 **Join** → เลือก 📝 ขอ White List
2. กรอก: Steam ID/ลิงก์ · Username ในเกม · ช่วงเวลาที่ออน · รู้จักจากไหน · รหัสลับ
3. บอทเช็ค Steam — ไม่ผ่าน (ไม่มีบัญชี / มีคนใช้แล้ว) จะเด้งให้แก้แล้วส่งใหม่
4. ได้ thread `wl-0001 ชื่อ` + ผลเช็คอัตโนมัติให้แอดมินดู
5. แอดมินกด ✅ **อนุมัติ** → ใส่ username / password (สุ่มให้แล้ว) → บอท DM รหัสให้ผู้เล่น + ให้ role Survivor + ขึ้นคำสั่ง `adduser "ชื่อ" "รหัส"` ให้แอดมิน **ก๊อปไปวางในคอนโซลเซิฟ** → ปิด thread + เก็บ transcript

**Donate**
1. กด 🍪 Join / 🎫 เปิด Ticket / 💝 Donate → ได้ thread `donate-0001 ชื่อ` ที่มีวิธีใช้ + รายการพร้อมรหัส
2. กด 💝 **Donate** → ใส่ **รหัส** + **จำนวน** → บอทโชว์ชื่อ + ยอดต่อชิ้น
3. การ์ดตะกร้า: ➕ เพิ่มรายการ (สูงสุด 5) · ➖ ลบรายการ · 📨 ส่ง · ❌ ยกเลิก
4. 📨 **ส่ง** → การ์ดสรุป → ✅ **ยืนยัน** (หรือ 📝 แก้ไข / ❌ ยกเลิก)
5. ได้บิล: 💳 **จ่ายเงิน** → หน้า Stripe เลือก PromptPay สแกน QR (หรือบัตร) · บิลหมดอายุใน 60 นาที (หมดแล้วกด 🔁 สร้างบิลใหม่ได้)
6. จ่ายแล้ว ~20 วินาที → การ์ด **ได้รับยอด Donate แล้ว** + แท็กทีมแอดมิน + log ในห้อง donate-log
7. แอดมินส่งของในเกม → กด 📦 **ยืนยันส่งของแล้ว** → การ์ดเป็นสีเขียว + บอทแจ้งผู้เล่น

ห้อง Donate เปิดค้างไว้ได้ Donate รอบต่อไปในห้องเดิมได้เลย

---

## 7. เก็บกวาดของบอทเก่า

- ลบข้อความเก่าของ CHEF ที่มีปุ่ม (ข้อความต้อนรับเดิม, quick-start, ร้านค้า, ตลาด, หมุนวงล้อ, pass ฯลฯ) — ปุ่มพวกนั้นจะขึ้น "This interaction failed" แล้ว
- ส่งข้อความใหม่ด้วย `/panel` แทน
- ห้อง/category ที่บอทเก่าสร้าง (pending, ห้องส่วนตัว, ticket เก่า) ลบได้ถ้าไม่ใช้
- slash command เก่าของบอทเดิมจะถูกล้างให้เองตอนบอทใหม่เปิด (ถ้ายังเห็น กด Ctrl+R ใน Discord)

---

## 8. แก้ข้อความ

ข้อความทั้งหมดอยู่บนสุดของ `bot.py` (หมวด "ข้อความที่แก้ได้") เช่น `WELCOME_TITLE`, `WELCOME_STEPS`, `DONATE_HOWTO`, คำถามในฟอร์ม `TICKET_TYPES` — แก้แล้ว push ขึ้น GitHub แล้วส่ง `/panel` ใหม่

> emoji ในปุ่มให้ใช้ตัวเดียวล้วน (เช่น 🍪 ✅ 📜) — ตัวที่มีตัวต่อท้ายอย่าง ⚠️ ✏️ 🗑️ Discord จะปฏิเสธ (Invalid emoji)

---

## 9. ปัญหาที่เจอบ่อย

| อาการ | แก้ |
|---|---|
| บอท restart วนใน Railway | ดู Deploy Logs — บอทบอกว่า Variable ไหนขาด/ผิด |
| `DISCORD_TOKEN ผิด` | Developer Portal → Bot → Reset Token → ใส่ใหม่ |
| `ต้องเปิด MESSAGE CONTENT INTENT` | ข้อ 3.1 |
| กดเปิด ticket แล้ว error สิทธิ์ | `/check` → แก้สิทธิ์ห้อง ticket ตามข้อ 3.3 |
| แอดมินไม่เห็น thread ของผู้เล่น | role แอดมินต้องมี **Manage Threads** ในห้อง ticket |
| ให้ role Survivor ไม่ได้ | ลาก role บอทให้อยู่เหนือ Survivor |
| สร้างบิลไม่สำเร็จ | ดูเหตุผลในห้อง mod-logs — ส่วนใหญ่: ยังไม่เปิด PromptPay, ยอดต่ำกว่า ฿10, key ผิดโหมด |
| จ่ายแล้วการ์ดไม่ขึ้น | กด 🔄 เช็คสถานะ หรือ `/order check` · เช็คใน Stripe Dashboard → Payments |
| ข้อมูลหายหลัง deploy | ยังไม่ได้ต่อ Volume (ข้อ 2.2) |
| ปุ่มในข้อความเก่าไม่ทำงาน | ข้อความของบอทเก่า — ลบแล้ว `/panel` ใหม่ |

---

## 10. ข้อควรรู้

- **Steam ที่พิมพ์มาอาจเป็นของคนอื่น** — บอทกันได้แค่ "Steam หนึ่งบัญชีใช้กับ Discord ได้คนเดียว" และโชว์อายุบัญชี/ชั่วโมงเล่น PZ/ประวัติแบนให้ดู ถ้าสงสัย ให้ผู้เล่นเปลี่ยนชื่อโปรไฟล์ Steam เป็นคำที่แอดมินกำหนดชั่วคราวแล้วเช็คด้วย `/steam info`
- ยอดในบิลล็อกตามราคาตอนใส่ตะกร้า (แก้ราคาทีหลังไม่กระทบบิลที่ส่งไปแล้ว) · ถ้าปิดรายการระหว่างรอยืนยัน บอทจะไม่ยอมออกบิลรายการนั้น
- คืนเงินทำใน Stripe Dashboard → Payments → Refund (บอทไม่ได้จัดการให้)
- บอทเปิด RCON ไม่ได้บน Railway (เซิฟอยู่ที่เครื่องในบ้าน) — คำสั่ง `adduser` / `removeuserfromwhitelist` ต้องวางในคอนโซลเซิฟเอง

### รันในเครื่อง (ทดสอบ)
```bash
pip install -r requirements.txt
cp .env.example .env      # ใส่ค่า
python bot.py
```
