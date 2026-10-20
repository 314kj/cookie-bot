"""หน้าร้านคุกกี้บนเว็บ — บอทเปิดเองใน service เดิมบน Railway (ไม่ต้อง host เพิ่ม)

GET  /               หน้าร้าน · ล็อกอินด้วย Discord แล้วใส่ตะกร้า กดแลกได้เลย
GET  /login          ไปหน้าอนุญาตของ Discord (ขอแค่ identify)
GET  /auth/callback  Discord ส่งกลับมา → เช็คว่าอยู่ในเซิฟ → ตั้ง session
GET  /logout
GET  /api/me         ยอดคุกกี้ · แลกได้กี่ชิ้นต่อของ · ประวัติล่าสุด
POST /api/checkout   แลกทั้งตะกร้า (ผ่านทุกชิ้นหรือไม่ได้สักชิ้น)
GET  /img/<ไฟล์>     รูปของ (เก็บใน Volume)
GET  /health         ให้ Railway เช็คว่าบอทยังอยู่

ไฟล์นี้ไม่แตะ Discord / ฐานข้อมูลเอง — ทุกอย่างผ่าน backend ที่ bot.py ส่งมา (ทดสอบแยกได้)
backend ต้องมี: login_enabled() client_id() client_secret redirect_uri() secure public_url secret()
               catalog() page_meta() async oauth_user(code) async me(uid) async checkout(uid, data)
"""
import base64
import hashlib
import hmac
import html
import json
import logging
import re
import secrets
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

from aiohttp import web

log = logging.getLogger("cookiebot.web")

IMAGE_RE = re.compile(r"^[A-Za-z0-9_\-]{1,40}\.(png|jpe?g|webp|gif)$", re.IGNORECASE)
THAI_MONTHS = ("ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค.")
SESSION_COOKIE = "cc_sess"
OAUTH_COOKIE = "cc_oauth"
SESSION_DAYS = 7
AUTHORIZE_URL = "https://discord.com/oauth2/authorize"
LOGIN_NOTICE = {
    "denied": "ยกเลิกการล็อกอินแล้ว",
    "failed": "ล็อกอินไม่สำเร็จ ลองใหม่อีกครั้ง",
    "notmember": "บัญชี Discord นี้ไม่ได้อยู่ในเซิฟของเรา — เข้าดิสก่อนแล้วค่อยล็อกอินใหม่",
    "left": "บัญชีนี้ไม่ได้อยู่ในเซิฟ Discord แล้ว ล็อกอินใหม่อีกครั้ง",
}


def thai_date(dt: datetime) -> str:
    return f"{dt.day} {THAI_MONTHS[dt.month - 1]} {dt.strftime('%H:%M')}"


# ---------------------------------------------------------------- cookie ที่เซ็นแล้ว (แก้เองไม่ได้)

def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def same(a, b) -> bool:
    """เทียบแบบเวลาคงที่ (รับภาษาไทย/อักษรแปลกได้ ไม่ throw)"""
    return hmac.compare_digest(str(a).encode("utf-8", "replace"), str(b).encode("utf-8", "replace"))


def sign(secret: bytes, payload: dict) -> str:
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    sig = _b64(hmac.new(secret, body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}"


def unsign(secret: bytes, token: str, kind: str):
    """คืน dict ถ้าลายเซ็นถูก ชนิดตรง และยังไม่หมดอายุ — ไม่งั้น None"""
    if not token or token.count(".") != 1 or len(token) > 2048:
        return None
    body, sig = token.split(".")
    good = _b64(hmac.new(secret, body.encode(), hashlib.sha256).digest())
    if not same(sig, good):
        return None
    try:
        data = json.loads(_unb64(body))
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict) or data.get("t") != kind or float(data.get("exp", 0)) < time.time():
        return None
    return data


# ---------------------------------------------------------------- หน้าเว็บ

CSS = """
:root{--bg:#fff8ef;--card:#ffffff;--ink:#3b2a20;--muted:#8a7464;--line:#f0e2d2;--brown:#8b5a2b;
--pink:#f06292;--pink-soft:#fde4ec;--mint:#2fbf8f;--amber:#e6a23c;--grey:#b9aa9c;--chip:#f7ecdf;
--spot:rgba(139,90,43,.07);--bad:#d64545;--shadow:0 10px 30px rgba(59,42,32,.14)}
@media (prefers-color-scheme:dark){:root{--bg:#1d1714;--card:#28201b;--ink:#f6ebe0;--muted:#bfa995;
--line:#3a2e26;--brown:#e0a96d;--pink:#ff8ab0;--pink-soft:#3e2430;--chip:#352a22;--spot:rgba(224,169,109,.06);
--bad:#ff7b7b;--shadow:0 10px 30px rgba(0,0,0,.45)}}
*{box-sizing:border-box}
[hidden]{display:none!important}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 "IBM Plex Sans Thai","Sarabun",system-ui,sans-serif}
body.has-cart{padding-bottom:84px}
button{font:inherit}
.top{display:flex;justify-content:flex-end;align-items:center;gap:10px;max-width:1120px;margin:0 auto;padding:12px 16px 0;
min-height:52px;flex-wrap:wrap}
.who{display:flex;align-items:center;gap:10px;background:var(--card);border:1px solid var(--line);border-radius:999px;
padding:5px 6px 5px 5px}
.who img{width:34px;height:34px;border-radius:50%;background:var(--chip)}
.who .nm{font-weight:600;max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.who .bal{font:600 17px "Mitr",sans-serif;color:var(--brown);background:var(--chip);border-radius:999px;padding:3px 12px}
.ghost{color:var(--muted);font-size:14px;text-decoration:none;padding:6px 10px;border-radius:999px}
.ghost:hover{background:var(--chip)}
.login{display:inline-flex;align-items:center;gap:8px;padding:9px 16px;border-radius:999px;background:#5865f2;color:#fff;
text-decoration:none;font-weight:600}
.login:hover{filter:brightness(1.07)}
.notice{max-width:1088px;margin:12px auto 0;padding:11px 16px;border-radius:14px;background:var(--pink-soft);color:var(--ink);
font-size:15px}
.notice a{color:inherit;font-weight:600}
header{position:relative;overflow:hidden;padding:30px 20px 28px;text-align:center;border-bottom:1px solid var(--line);
background-image:radial-gradient(var(--spot) 18%,transparent 19%),radial-gradient(var(--spot) 12%,transparent 13%);
background-size:46px 46px,46px 46px;background-position:0 0,23px 23px}
h1{margin:0;font:600 clamp(28px,6vw,44px)/1.1 "Mitr",sans-serif;color:var(--brown);letter-spacing:.5px}
h1 span{display:inline-block;transform:rotate(-8deg)}
.sub{margin:10px auto 0;max-width:560px;color:var(--muted)}
.cta{display:inline-flex;gap:8px;align-items:center;margin-top:20px;padding:11px 20px;border-radius:999px;
background:var(--pink);color:#fff;text-decoration:none;font-weight:600;box-shadow:0 6px 18px rgba(240,98,146,.28)}
.cta:hover{filter:brightness(1.05)}
details.hist{max-width:1088px;margin:14px auto 0;background:var(--card);border:1px solid var(--line);border-radius:16px;
padding:0 16px}
details.hist summary{cursor:pointer;padding:12px 0;font-weight:600}
.hist ul{list-style:none;margin:0;padding:0 0 12px}
.hist li{display:flex;gap:10px;justify-content:space-between;padding:7px 0;border-top:1px dashed var(--line);font-size:14px}
.hist li span:last-child{color:var(--muted);text-align:right}
nav{display:flex;gap:8px;flex-wrap:wrap;justify-content:center;padding:18px 16px 4px}
nav button{border:1px solid var(--line);background:var(--card);color:var(--ink);padding:7px 14px;border-radius:999px;
font-size:14px;cursor:pointer}
nav button[aria-pressed=true]{background:var(--brown);border-color:var(--brown);color:#fff}
main{max-width:1120px;margin:0 auto;padding:16px 16px 56px;display:grid;gap:18px;
grid-template-columns:repeat(auto-fill,minmax(240px,1fr))}
.item{background:var(--card);border:1px solid var(--line);border-radius:18px;overflow:hidden;display:flex;flex-direction:column}
.item.in{border-color:var(--pink);box-shadow:0 0 0 2px var(--pink-soft)}
.pic{aspect-ratio:1/1;background:var(--chip);display:grid;place-items:center;position:relative}
.pic img{width:100%;height:100%;object-fit:contain}
.pic .ph{font-size:64px;opacity:.55}
.state{position:absolute;top:10px;left:10px;padding:3px 10px;border-radius:999px;font-size:12px;font-weight:600;color:#fff}
.state.soon{background:var(--amber)}.state.ended,.state.soldout{background:var(--grey)}.state.hot{background:var(--pink)}
.body{padding:14px 16px 12px;display:flex;flex-direction:column;gap:8px;flex:1}
.cat{align-self:flex-start;font-size:12px;color:var(--muted);background:var(--chip);padding:2px 9px;border-radius:999px}
h2{margin:0;font:600 18px/1.3 "Mitr",sans-serif}
.desc{margin:0;color:var(--muted);font-size:14px;white-space:pre-line}
.meta{display:flex;flex-wrap:wrap;gap:6px;margin-top:auto;padding-top:6px}
.meta span{font-size:12px;border:1px dashed var(--line);padding:2px 8px;border-radius:8px;color:var(--muted)}
.price{display:flex;justify-content:space-between;align-items:center;gap:10px;border-top:1px solid var(--line);
padding:12px 14px 12px 16px;min-height:62px}
.price b{font:600 20px "Mitr",sans-serif;color:var(--brown);white-space:nowrap}
.price small{color:var(--muted);font-size:12px}
.buy{display:flex;justify-content:flex-end}
.btn{border:0;border-radius:999px;padding:9px 16px;background:var(--pink);color:#fff;font-weight:600;cursor:pointer;
text-decoration:none;white-space:nowrap;display:inline-flex;align-items:center;gap:6px}
.btn:hover{filter:brightness(1.05)}
.btn[disabled]{background:var(--chip);color:var(--muted);cursor:not-allowed;filter:none}
.btn.alt{background:var(--chip);color:var(--ink)}
.btn.big{padding:12px 22px;font-size:17px}
.step{display:inline-flex;align-items:center;border:1px solid var(--line);border-radius:999px;overflow:hidden;background:var(--card)}
.step button{border:0;background:transparent;color:var(--ink);width:36px;height:36px;font-size:20px;cursor:pointer}
.step button[disabled]{color:var(--grey);cursor:not-allowed}
.step output{min-width:30px;text-align:center;font-weight:600}
.item.off{opacity:.62}
.empty{grid-column:1/-1;text-align:center;color:var(--muted);padding:60px 0}
footer{text-align:center;color:var(--muted);font-size:13px;padding:0 16px 32px}
.bar{position:fixed;left:16px;right:16px;bottom:16px;max-width:720px;margin:0 auto;display:flex;align-items:center;
justify-content:space-between;gap:12px;padding:10px 10px 10px 18px;border-radius:999px;background:var(--brown);color:#fff;
box-shadow:var(--shadow);z-index:5}
.bar[hidden]{display:none}
.bar b{font:600 17px "Mitr",sans-serif}
.bar .btn{background:#fff;color:var(--brown)}
dialog{width:min(560px,calc(100vw - 32px));max-height:calc(100vh - 48px);border:0;border-radius:22px;padding:0;
background:var(--card);color:var(--ink);box-shadow:var(--shadow)}
dialog::backdrop{background:rgba(29,23,20,.55)}
.dlg{display:flex;flex-direction:column;max-height:calc(100vh - 48px)}
.dlg h3{margin:0;padding:18px 20px 12px;font:600 21px "Mitr",sans-serif;border-bottom:1px solid var(--line)}
.dlg .scroll{overflow:auto;padding:6px 20px}
.line{display:grid;grid-template-columns:1fr auto;gap:4px 12px;padding:12px 0;border-bottom:1px dashed var(--line)}
.line .n{font-weight:600}
.line .p{color:var(--muted);font-size:14px}
.line .ctl{grid-row:1/3;grid-column:2;display:flex;align-items:center;gap:6px}
.x{border:0;background:transparent;color:var(--muted);font-size:20px;cursor:pointer;width:32px;height:32px;border-radius:50%}
.x:hover{background:var(--chip)}
label.ing{display:block;margin:14px 0 4px;font-weight:600}
label.ing small{display:block;font-weight:400;color:var(--muted)}
input.ing{width:100%;padding:11px 14px;border-radius:12px;border:1px solid var(--line);background:var(--bg);color:var(--ink);
font:inherit;margin-top:6px}
.sum{padding:14px 20px;border-top:1px solid var(--line);display:grid;gap:4px}
.sum div{display:flex;justify-content:space-between}
.sum .t b{font:600 20px "Mitr",sans-serif;color:var(--brown)}
.sum .neg{color:var(--bad)}
.err{color:var(--bad);margin:8px 0 0;min-height:0}
.acts{display:flex;gap:10px;justify-content:flex-end;padding:0 20px 18px;flex-wrap:wrap}
.ok{padding:8px 0 4px}
.ok p{margin:6px 0}
.ok ul{list-style:none;padding:0;margin:8px 0}
.ok li{padding:8px 0;border-bottom:1px dashed var(--line);display:flex;justify-content:space-between;gap:10px;font-size:15px}
.ok li span:last-child{color:var(--muted);text-align:right}
.ok a{color:var(--pink);font-weight:600}
@media (max-width:520px){.who .nm{display:none}.price{flex-wrap:wrap}.buy{width:100%}.buy .btn,.buy .step{width:100%;
justify-content:center}.step{justify-content:space-between}}
"""

JS = r"""
(()=>{
const S=JSON.parse(document.getElementById('state').textContent);
const fmt=n=>Number(n).toLocaleString('th-TH');
const $=(s,el=document)=>el.querySelector(s);
const el=(tag,props={},kids=[])=>{const e=document.createElement(tag);for(const[k,v]of Object.entries(props)){
 if(k==='text')e.textContent=v;else if(k==='on')for(const[ev,f]of Object.entries(v))e.addEventListener(ev,f);
 else if(v!==false&&v!=null)e.setAttribute(k,v===true?'':v);}for(const c of kids)if(c)e.append(c);return e;};
// หมวด
const navBtns=[...document.querySelectorAll('nav button')];
navBtns.forEach(b=>b.addEventListener('click',()=>{navBtns.forEach(x=>x.setAttribute('aria-pressed',x===b));
 const c=b.dataset.cat;document.querySelectorAll('.item').forEach(e=>{e.hidden=!(c==='*'||e.dataset.cat===c)});}));
if(!S.user)return;
const U=S.user;const KEY='cc-cart-'+U.id;const PKEY=KEY+'-pending';let cart={};let busy=false;let memPending=null;
const cap=c=>(U.caps&&U.caps[c])||0;
const total=skip=>Object.entries(cart).reduce((t,[c,q])=>c===skip||!S.items[c]?t:t+S.items[c].price*q,0);
const count=()=>Object.values(cart).reduce((a,b)=>a+b,0);
const maxFor=c=>{const it=S.items[c];if(!it||!U.can_redeem)return 0;
 return Math.max(0,Math.min(cap(c),Math.floor((U.balance-total(c))/Math.max(1,it.price))));};
function clean(){for(const c of Object.keys(cart)){const q=parseInt(cart[c],10);
 if(!S.items[c]||!(q>0)||cap(c)<1)delete cart[c];else cart[c]=Math.min(q,cap(c));}}
function load(){try{const v=JSON.parse(localStorage.getItem(KEY)||'{}');cart=v&&typeof v==='object'?v:{};}catch(e){cart={};}clean();}
function save(){try{localStorage.setItem(KEY,JSON.stringify(cart));}catch(e){}}
// ตะกร้าที่กดยืนยันไปแล้วแต่ยังไม่รู้ผล (เน็ตหลุด/เซิฟสะดุด) — ส่งซ้ำด้วย nonce เดิมเสมอ ไม่โดนหักซ้ำ
function getPending(){if(memPending)return memPending;try{return JSON.parse(localStorage.getItem(PKEY)||'null');}catch(e){return null;}}
function setPending(p){memPending=p;try{if(p)localStorage.setItem(PKEY,JSON.stringify(p));else localStorage.removeItem(PKEY);}catch(e){}}
function setQty(c,q){q=Math.max(0,Math.min(q,maxFor(c)));
 if(q>0)cart[c]=q;else delete cart[c];save();render();}
function stepper(c,big){const q=cart[c]||0;return el('span',{class:'step'},[
 el('button',{type:'button','aria-label':'ลด',text:'−',on:{click:()=>setQty(c,q-1)}}),
 el('output',{text:String(q)}),
 el('button',{type:'button','aria-label':'เพิ่ม',text:'+',disabled:maxFor(c)<=q,on:{click:()=>setQty(c,q+1)}})]);}
function renderCards(){document.querySelectorAll('.item[data-code]').forEach(card=>{const c=card.dataset.code;
 const slot=$('.buy',card);if(!slot)return;slot.replaceChildren();card.classList.toggle('in',!!cart[c]);
 const it=S.items[c];if(!it)return;
 if(!U.can_redeem){slot.append(el('button',{class:'btn',disabled:true,text:'แลกไม่ได้'}));return;}
 if(cart[c]){slot.append(stepper(c));return;}
 const why=(U.why&&U.why[c])||'';const m=maxFor(c);
 if(cap(c)<1){slot.append(el('button',{class:'btn',disabled:true,text:why||'แลกไม่ได้'}));return;}
 if(m<1){slot.append(el('button',{class:'btn',disabled:true,text:'คุกกี้ไม่พอ'}));return;}
 slot.append(el('button',{class:'btn',type:'button',text:'ใส่ตะกร้า',on:{click:()=>setQty(c,1)}}));});}
function renderBar(){const n=count();const bar=$('#bar');bar.hidden=!n;document.body.classList.toggle('has-cart',!!n);
 $('#barCount').textContent=fmt(n)+' ชิ้น';$('#barTotal').textContent=fmt(total())+' 🍪';}
function renderHead(){const b=$('#bal');if(b)b.textContent=fmt(U.balance)+' 🍪';
 const h=$('#hist');if(!h)return;const ul=$('ul',h);ul.replaceChildren();
 (U.recent||[]).forEach(r=>ul.append(el('li',{},[el('span',{text:`${r.icon} ${r.name} × ${r.qty}`}),
  el('span',{text:`${r.rid}${r.cart?' · '+r.cart:''} · ${r.status}`})])));h.hidden=!(U.recent||[]).length;}
function needsName(){return Object.keys(cart).some(c=>S.items[c]&&S.items[c].ckx);}
function renderCart(){const box=$('#lines');box.replaceChildren();
 for(const[c,q]of Object.entries(cart)){const it=S.items[c];if(!it)continue;
  box.append(el('div',{class:'line'},[el('span',{class:'n',text:it.name}),
   el('span',{class:'p',text:`${fmt(it.price)} 🍪 × ${q} = ${fmt(it.price*q)} 🍪`}),
   el('span',{class:'ctl'},[stepper(c),el('button',{class:'x',type:'button','aria-label':'เอาออก',text:'×',
    on:{click:()=>setQty(c,0)}})])]));}
 const t=total();$('#sumTotal').textContent=fmt(t)+' 🍪';const left=U.balance-t;
 const l=$('#sumLeft');l.textContent=fmt(left)+' 🍪';l.classList.toggle('neg',left<0);
 $('#ingWrap').hidden=!needsName();$('#go').disabled=busy||(!count()&&!getPending())||left<0;
 if(!count()&&!getPending()&&!$('#done').childElementCount&&!$('#err').textContent)$('#cartDlg').close();}
function render(){clean();renderCards();renderBar();renderHead();if($('#cartDlg').open)renderCart();}
function showErr(t){$('#err').textContent=t||'';}
async function refresh(){try{const r=await fetch('/api/me',{credentials:'same-origin',cache:'no-store'});
 if(r.status===401){location.reload();return;}if(!r.ok)return;const d=await r.json();
 if(d.user){Object.assign(U,d.user);if(d.items)S.items=d.items;render();updateDone();}}catch(e){}}
let lastCart=null;let poll=null;
function updateDone(){if(!lastCart)return;const by=Object.fromEntries((U.recent||[]).map(r=>[r.rid,r]));
 const ul=$('#doneList');if(!ul)return;ul.replaceChildren();
 lastCart.lines.forEach(l=>{const r=by[l.rid]||l;ul.append(el('li',{},[el('span',{text:`${r.icon} ${l.name} × ${l.qty}`}),
  el('span',{text:`${l.rid} · ${r.status}`})]));});}
function showDone(c){lastCart=c;const d=$('#done');d.replaceChildren(el('div',{class:'ok'},[
 el('p',{},[el('b',{text:`🎉 แลกแล้ว · ตะกร้า ${c.label}`})]),
 el('p',{text:`ใช้ไป ${fmt(c.total)} 🍪 · เหลือ ${fmt(U.balance)} 🍪`}),
 el('ul',{id:'doneList'}),
 el('p',{text:c.has_ckx?'ของที่ส่งเข้าเกมเอง: เข้าเกมแล้วกดรับที่ปุ่มบ้านคุกกี้ 🍪':'แอดมินจะส่งของให้เร็วๆ นี้'}),
 U.wallet_url?el('p',{},[el('a',{href:U.wallet_url,target:'_blank',rel:'noopener',text:'ดูสถานะในกระเป๋าคุกกี้บน Discord →'})]):null]));
 updateDone();$('#cartBody').hidden=true;$('#sum').hidden=true;$('#go').hidden=true;$('#more').hidden=false;
 clearInterval(poll);let n=0;poll=setInterval(()=>{if(++n>20||!$('#cartDlg').open){clearInterval(poll);return;}refresh();},6000);}
async function send(body){try{const r=await fetch('/api/checkout',{method:'POST',credentials:'same-origin',
  headers:{'Content-Type':'application/json','X-CSRF-Token':S.csrf},body:JSON.stringify(body)});
 let d=null;try{d=await r.json();}catch(e){}
 if(r.status===401){location.reload();return{kind:'reload'};}
 if(d&&d.state){Object.assign(U,d.state);if(d.items)S.items=d.items;}
 if(r.ok&&d&&d.ok)return{kind:'ok',d};
 if(d&&d.ok===false&&r.status>=400&&r.status<500)return{kind:'refused',d};
 return{kind:'unknown',d};}catch(e){return{kind:'unknown',d:null};}}
function finish(res){if(res.kind==='ok'){setPending(null);cart={};save();showDone(res.d.cart);}
 else if(res.kind==='refused'){setPending(null);showErr(res.d.error||'แลกไม่สำเร็จ ลองใหม่อีกครั้ง');}
 else if(res.kind==='unknown')showErr((res.d&&res.d.error)||'ยังไม่รู้ผล (เน็ต/เซิฟสะดุด) — กดยืนยันอีกครั้ง ระบบจะเช็คให้ ไม่โดนหักซ้ำ');}
async function checkout(){if(busy)return;showErr('');let body=getPending();
 if(!body){const name=$('#ing').value.trim();
  if(needsName()&&!name){showErr('ใส่ชื่อในเกมก่อน (ชื่อที่ใช้ล็อกอินเข้าเซิฟ)');$('#ing').focus();return;}
  const id=crypto.randomUUID?crypto.randomUUID():String(Date.now())+Math.random().toString(16).slice(2);
  body={nonce:id,ingame:name,expected_total:total(),items:Object.entries(cart).map(([code,qty])=>({code,qty}))};
  setPending(body);}
 busy=true;$('#go').disabled=true;$('#go').textContent='กำลังแลก…';
 const res=await send(body);busy=false;$('#go').textContent='ยืนยันแลก';finish(res);render();}
async function resume(){const p=getPending();if(!p)return;const res=await send(p);if(res.kind==='reload')return;
 if(res.kind==='ok'){openCart();finish(res);render();}else if(res.kind==='refused'){setPending(null);render();}}
function openCart(){$('#done').replaceChildren();lastCart=null;$('#cartBody').hidden=false;$('#sum').hidden=false;$('#go').hidden=false;
 $('#more').hidden=true;showErr('');if(!$('#ing').value)$('#ing').value=U.ingame||'';$('#cartDlg').showModal();renderCart();}
$('#open').addEventListener('click',openCart);
$('#go').addEventListener('click',checkout);
$('#close').addEventListener('click',()=>$('#cartDlg').close());
$('#more').addEventListener('click',()=>$('#cartDlg').close());
$('#cartDlg').addEventListener('close',()=>{clearInterval(poll);render();});
load();render();resume();
})();
"""

STATE_TEXT = {"soon": "เร็วๆ นี้", "ended": "หมดเวลา", "soldout": "หมดแล้ว", "hot": "ใกล้หมดเวลา"}


def _json_for_html(data) -> str:
    """JSON ที่ฝังใน <script type=application/json> ได้ปลอดภัย"""
    return (json.dumps(data, ensure_ascii=False, separators=(",", ":"))
            .replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e"))


def render_page(items: list, meta: dict, user: dict = None, csrf: str = "", login: bool = False,
                notice: str = "", nonce: str = "") -> str:
    """items: dict (code name description price category image_url limit stock start end state ckx)
    user: ผลจาก backend.me() ของคนที่ล็อกอิน (None = ยังไม่ล็อกอิน)"""
    e = html.escape
    cats = sorted({i["category"] for i in items if i.get("category")})
    nav = ""
    if cats:
        nav = "<nav aria-label='หมวด'><button data-cat='*' aria-pressed='true'>ทั้งหมด</button>" + "".join(
            f"<button data-cat='{e(c)}' aria-pressed='false'>{e(c)}</button>" for c in cats) + "</nav>"
    if user:
        buy_default = ""  # JS ใส่ปุ่มเอง
    elif login:
        buy_default = "<a class='btn alt' href='/login'>ล็อกอินเพื่อแลก</a>"
    else:
        buy_default = ""
    cards = []
    for i in items:
        state = i.get("state") or "open"
        pic = (f"<img src='{e(i['image_url'])}' alt='{e(i['name'])}' loading='lazy'>" if i.get("image_url")
               else "<div class='ph' aria-hidden='true'>🍪</div>")
        badge = f"<span class='state {state}'>{STATE_TEXT[state]}</span>" if state in STATE_TEXT else ""
        chips = []
        if i.get("limit"):
            chips.append(f"แลกได้ {i['limit']} ครั้ง/คน")
        if i.get("stock") is not None and i["stock"] >= 0:
            chips.append(f"เหลือ {i['stock']} ชิ้น")
        if i.get("start") and state == "soon":
            chips.append(f"เริ่ม {thai_date(i['start'])}")
        if i.get("end") and state in ("open", "hot"):
            chips.append(f"ถึง {thai_date(i['end'])}")
        chips.append("📦 ส่งเข้าเกมเอง" if i.get("ckx") else "🙋 แอดมินส่งให้")
        meta_html = "".join(f"<span>{e(c)}</span>" for c in chips)
        cat = f"<span class='cat'>{e(i['category'])}</span>" if i.get("category") else ""
        desc = f"<p class='desc'>{e(i['description'])}</p>" if i.get("description") else ""
        off = " off" if state in ("ended", "soldout") else ""
        buy = buy_default if state not in ("ended", "soldout", "soon") else ""
        cards.append(
            f"<article class='item{off}' data-cat='{e(i.get('category') or '')}' data-code='{e(i['code'])}'>"
            f"<div class='pic'>{pic}{badge}</div>"
            f"<div class='body'>{cat}<h2>{e(i['name'])}</h2>{desc}<div class='meta'>{meta_html}</div></div>"
            f"<div class='price'><b>{i['price']:,} 🍪</b><div class='buy'>{buy}</div></div></article>")
    if not cards:
        cards.append("<p class='empty'>ยังไม่มีของในร้าน รอแอดมินเติมของก่อนนะ 🍪</p>")
    title = e(meta.get("title") or "Cookie Shop")

    if user:
        avatar = f"<img src='{e(user.get('avatar') or '')}' alt=''>" if user.get("avatar") else ""
        top = (f"<div class='who'>{avatar}<span class='nm'>{e(user.get('name') or '')}</span>"
               f"<span class='bal' id='bal'>{int(user.get('balance') or 0):,} 🍪</span></div>"
               f"<a class='ghost' href='/logout'>ออกจากระบบ</a>")
    elif login:
        top = "<a class='login' href='/login'>เข้าสู่ระบบด้วย Discord</a>"
    else:
        top = ""
    notices = []
    if notice:
        invite = meta.get("invite_url")
        extra = (f" · <a href='{e(invite)}' target='_blank' rel='noopener'>เข้าดิส</a>"
                 if invite and "ดิส" in notice else "")
        notices.append(f"<p class='notice' role='status'>{e(notice)}{extra}</p>")
    if user and not user.get("can_redeem"):
        notices.append(f"<p class='notice'>{e(user.get('reason') or 'ตอนนี้ยังแลกของไม่ได้')}</p>")
    if user and user.get("can_redeem"):
        sub = meta.get("subtitle_user") or "เลือกของใส่ตะกร้า แล้วกดยืนยันแลกได้เลย"
    elif login:
        sub = meta.get("subtitle_login") or "ล็อกอินด้วย Discord เพื่อดูคุกกี้ของคุณและแลกของ"
    else:
        sub = meta.get("subtitle") or ""
    cta = ""
    if not login and meta.get("redeem_url"):
        cta = f"<a class='cta' href='{e(meta['redeem_url'])}'>🛍️ ไปแลกใน Discord</a>"
    hist = ("<details class='hist' id='hist' hidden><summary>📜 ของที่แลกล่าสุด</summary><ul></ul></details>"
            if user else "")

    state = {"items": {i["code"]: {"name": i["name"], "price": i["price"], "ckx": bool(i.get("ckx"))}
                       for i in items if (i.get("state") or "open") in ("open", "hot")},
             "user": user, "csrf": csrf}
    cart_ui = ""
    if user:
        cart_ui = (
            "<div class='bar' id='bar' hidden><span>🛒 <span id='barCount'></span> · <b id='barTotal'></b></span>"
            "<button class='btn' id='open' type='button'>ดูตะกร้า</button></div>"
            "<dialog id='cartDlg' aria-labelledby='cartTitle'><div class='dlg'>"
            "<h3 id='cartTitle'>🛒 ตะกร้าของคุณ</h3>"
            "<div class='scroll'><div id='cartBody'><div id='lines'></div>"
            "<div id='ingWrap'><label class='ing' for='ing'>ชื่อในเกมที่จะรับของ"
            "<small>ชื่อที่ใช้ล็อกอินเข้าเซิฟ (ไม่ใช่ชื่อตัวละคร)</small></label>"
            "<input class='ing' id='ing' maxlength='40' autocomplete='off' spellcheck='false'></div>"
            "<p class='err' id='err' role='alert'></p></div><div id='done'></div></div>"
            "<div class='sum' id='sum'><div class='t'><span>รวม</span><b id='sumTotal'></b></div>"
            "<div><span>คุกกี้เหลือหลังแลก</span><span id='sumLeft'></span></div></div>"
            "<div class='acts'><button class='btn alt' id='close' type='button'>ปิด</button>"
            "<button class='btn alt' id='more' type='button' hidden>แลกต่อ</button>"
            "<button class='btn big' id='go' type='button'>ยืนยันแลก</button></div>"
            "</div></dialog>")
    script_attr = f" nonce='{e(nonce)}'" if nonce else ""
    return (
        "<!doctype html><html lang='th'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{title}</title>"
        "<link rel='preconnect' href='https://fonts.googleapis.com'>"
        "<link href='https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@400;600&family=Mitr:wght@500;600"
        "&display=swap' rel='stylesheet'>"
        f"<style>{CSS}</style></head><body>"
        f"<div class='top'>{top}</div>{''.join(notices)}"
        f"<header><h1>{title} <span>🍪</span></h1>"
        f"<p class='sub'>{e(sub)}</p>{cta}</header>{hist}"
        f"{nav}<main>{''.join(cards)}</main>"
        f"<footer>{e(meta.get('footer') or '')}</footer>{cart_ui}"
        f"<script type='application/json' id='state'>{_json_for_html(state)}</script>"
        f"<script{script_attr}>{JS}</script></body></html>")


# ---------------------------------------------------------------- เว็บแอป

def create_app(backend, images_dir: Path) -> web.Application:
    images_dir = Path(images_dir)

    def cookie_opts(max_age):
        return {"max_age": max_age, "httponly": True, "secure": bool(backend.secure), "samesite": "Lax", "path": "/"}

    def session_of(request):
        if not backend.login_enabled():
            return None
        data = unsign(backend.secret(), request.cookies.get(SESSION_COOKIE, ""), "s")
        if (data and str(data.get("u", "")).isdigit() and data.get("c")
                and data.get("v") == backend.session_version(int(data["u"]))):
            return data
        return None

    def redirect(location):
        return web.Response(status=302, headers={"Location": location, "Cache-Control": "no-store"})

    def no_store(resp):
        resp.headers["Cache-Control"] = "no-store"
        return resp

    async def index(request):
        sess = session_of(request)
        user, notice, drop = None, LOGIN_NOTICE.get(request.query.get("login", ""), ""), False
        if sess:
            try:
                st = await backend.me(int(sess["u"]))
            except Exception:  # noqa: BLE001 — Discord ล่มชั่วคราว: ให้ดูร้านแบบยังไม่ล็อกอินไปก่อน
                log.exception("โหลดข้อมูลผู้ใช้เว็บไม่ได้")
                st, notice = None, "ดึงข้อมูลบัญชีไม่ได้ชั่วคราว ลองรีเฟรชอีกครั้ง"
            if st and st.get("member"):
                user = st
            elif st is not None:
                notice, drop = LOGIN_NOTICE["left"], True
        nonce = secrets.token_urlsafe(12)
        page = render_page(backend.catalog(), backend.page_meta(), user=user, csrf=sess["c"] if user else "",
                           login=backend.login_enabled(), notice=notice, nonce=nonce)
        resp = web.Response(text=page, content_type="text/html", charset="utf-8")
        resp.headers.update({
            "Cache-Control": "no-store",
            "Content-Security-Policy": (
                "default-src 'self'; img-src 'self' data: https://cdn.discordapp.com https://media.discordapp.net; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; "
                f"script-src 'nonce-{nonce}'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; "
                "form-action 'self'"),
            "Referrer-Policy": "same-origin",
            "X-Content-Type-Options": "nosniff"})
        if drop:
            resp.del_cookie(SESSION_COOKIE, path="/")
        return resp

    async def login(request):
        if not backend.login_enabled():
            return redirect("/")
        state = secrets.token_urlsafe(24)
        url = AUTHORIZE_URL + "?" + urlencode({
            "client_id": backend.client_id(), "response_type": "code", "redirect_uri": backend.redirect_uri(),
            "scope": "identify", "state": state})
        resp = redirect(url)
        resp.set_cookie(OAUTH_COOKIE, sign(backend.secret(), {"t": "o", "s": state, "exp": time.time() + 600}),
                        **cookie_opts(600))
        return resp

    async def callback(request):
        if not backend.login_enabled():
            return redirect("/")
        q = request.query
        saved = unsign(backend.secret(), request.cookies.get(OAUTH_COOKIE, ""), "o")
        if not saved or not q.get("state") or not same(saved.get("s", ""), q["state"]):
            return redirect("/?login=failed")
        if q.get("error") or not q.get("code"):
            return redirect("/?login=denied")
        try:
            user = await backend.oauth_user(q["code"])
            uid = int(user["id"])
            st = await backend.me(uid)
        except Exception:  # noqa: BLE001
            log.exception("ล็อกอิน Discord ไม่สำเร็จ")
            return redirect("/?login=failed")
        if not st.get("member"):
            resp = redirect("/?login=notmember")
            resp.del_cookie(OAUTH_COOKIE, path="/")
            return resp
        resp = redirect("/")
        resp.del_cookie(OAUTH_COOKIE, path="/")
        resp.set_cookie(SESSION_COOKIE, sign(backend.secret(), {
            "t": "s", "u": str(uid), "c": secrets.token_urlsafe(18), "v": backend.session_version(uid),
            "exp": time.time() + SESSION_DAYS * 86400}),
                        **cookie_opts(SESSION_DAYS * 86400))
        log.info("เว็บ: %s ล็อกอิน", uid)
        return resp

    async def logout(request):
        sess = session_of(request)
        if sess:  # cookie ที่ก๊อปไปไว้ที่อื่นก็ใช้ไม่ได้แล้ว
            backend.end_sessions(int(sess["u"]))
        resp = redirect("/")
        resp.del_cookie(SESSION_COOKIE, path="/")
        return resp

    async def api_me(request):
        sess = session_of(request)
        if not sess:
            return no_store(web.json_response({"error": "login"}, status=401))
        st = await backend.me(int(sess["u"]))
        if not st.get("member"):
            resp = no_store(web.json_response({"error": "login"}, status=401))
            resp.del_cookie(SESSION_COOKIE, path="/")
            return resp
        return no_store(web.json_response({"user": st, "items": backend.item_map()}))

    async def api_checkout(request):
        sess = session_of(request)
        if not sess:
            return no_store(web.json_response({"error": "ล็อกอินใหม่อีกครั้ง"}, status=401))
        origin = request.headers.get("Origin")
        if origin and backend.public_url and origin.rstrip("/") != backend.public_url.rstrip("/"):
            return no_store(web.json_response({"error": "forbidden"}, status=403))
        if not same(request.headers.get("X-CSRF-Token", ""), sess["c"]):
            return no_store(web.json_response({"error": "หน้าเว็บเก่าไป รีเฟรชแล้วลองใหม่"}, status=403))
        if request.content_type != "application/json":
            return no_store(web.json_response({"error": "bad request"}, status=415))
        try:
            data = json.loads(await request.text())
        except (ValueError, RecursionError):
            return no_store(web.json_response({"ok": False, "error": "bad request"}, status=400))
        try:
            status, body = await backend.checkout(int(sess["u"]), data)
        except Exception:  # noqa: BLE001 — ไม่รู้ว่าแลกไปแล้วหรือยัง → ให้กดใหม่ด้วย nonce เดิม (ไม่หักซ้ำ)
            log.exception("แลกตะกร้าพัง")
            status, body = 503, {"ok": False, "code": "retry",
                                 "error": "ระบบสะดุดชั่วคราว กดยืนยันอีกครั้ง (ไม่โดนหักซ้ำ)"}
        resp = no_store(web.json_response(body, status=status))
        if status == 401:
            resp.del_cookie(SESSION_COOKIE, path="/")
        return resp

    async def image(request):
        name = request.match_info["name"]
        if not IMAGE_RE.match(name):
            raise web.HTTPNotFound()
        path = images_dir / name
        if not path.is_file():
            raise web.HTTPNotFound()
        return web.FileResponse(path, headers={"Cache-Control": "public, max-age=86400"})

    async def health(request):
        return web.Response(text="ok")

    app = web.Application(client_max_size=64 * 1024)
    app.router.add_get("/", index)
    app.router.add_get("/login", login)
    app.router.add_get("/auth/callback", callback)
    app.router.add_get("/logout", logout)
    app.router.add_get("/api/me", api_me)
    app.router.add_post("/api/checkout", api_checkout)
    app.router.add_get("/img/{name}", image)
    app.router.add_get("/health", health)
    return app
