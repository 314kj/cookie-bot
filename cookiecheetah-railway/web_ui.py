"""หน้าตาเว็บร้านคุกกี้ (Cookie Cheetah) — ธีมดำเลื่อมชมพู · หน้าต่าง Win95 · ปุ่มเม็ดยา · ไอคอนพิกเซล

โครงหน้า: แถบซ้าย (โลโก้ · ไทล์ REDEEM/DONATE · เมนูหมวด) · แถบบน (ปุ่มลัด · คุกกี้ · ตะกร้า)
· กลาง (แบนเนอร์ → หมวด → มาใหม่ → ของทั้งหมด) · ขวา (กระเป๋า · การ์ดสติกเกอร์ · ประวัติ)
· ตะกร้าเป็นลิ้นชักด้านขวา (มือถือ = แผ่นเลื่อนขึ้น)
รูป/ข้อความ/สี/ของตกแต่งทุกช่องแก้บนเว็บได้ (คนแก้ร้านเท่านั้น) — ค่าเก็บใน web_site · ช่องที่ยังไม่ใส่รูป = ใช้รูปในตัว (assets/web)
render_page() / shell() สร้าง HTML ทั้งหน้า · ไม่แตะฐานข้อมูล/Discord (ข้อมูลมาจาก backend ใน bot.py)
CSS อยู่ใน web_theme.py
"""
import html
import json
from datetime import datetime, timedelta, timezone

import web_art
import web_site
from urllib.parse import quote

from web_art import art, cat_art, cookie, px, sticker
from web_theme import CSS

THAI_MONTHS = ("ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค.")
STATE_TEXT = {"soon": "เร็วๆ นี้", "ended": "หมดเวลา", "soldout": "หมดแล้ว", "hot": "ใกล้หมดเวลา"}


def thai_date(dt: datetime) -> str:
    return f"{dt.day} {THAI_MONTHS[dt.month - 1]} {dt.strftime('%H:%M')}"


def json_for_html(data) -> str:
    """JSON ที่ฝังใน <script type=application/json> ได้ปลอดภัย"""
    return (json.dumps(data, ensure_ascii=False, separators=(",", ":"))
            .replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e"))


# ไอคอนในหน้า (ชื่อเดิม → ไอคอนพิกเซล)
ICON = {"home": "home", "clock": "clock", "wallet": "wallet", "filter": "sliders", "list": "view-list", "plus": "plus",
        "search": "search", "chat": "message", "pen": "edit", "cart": "cart", "logout": "logout", "page": "info-box",
        "chev": "chevron-left", "next": "chevron-right", "heart": "heart", "ext": "external-link", "menu": "menu",
        "play": "play", "brush": "paint-bucket", "image": "image", "help": "message", "gift": "gift"}

CAT_COLOR = {"weapon": "c3", "ammo": "c4", "vehicle": "c0", "outfit": "c1", "bag": "c1", "food": "c5", "med": "c1",
             "tool": "c4", "material": "c2", "book": "c0", "chat": "c3", "event": "c4", "special": "c5", "misc": "c0",
             "cookie": "c6"}

WB = "<span class='wb' aria-hidden='true'><i>_</i><i>□</i><i>×</i></span>"


def icon(name: str, size: int = 24) -> str:
    return px(ICON.get(name, name), size)


def img_url(name: str) -> str:
    return f"/img/{name}" if name else ""


def win(title: str, body: str, cls: str = "", tag: str = "section", attrs: str = "", inner: str = "wc") -> str:
    """หน้าต่างแบบ Win95 (title = HTML ที่ escape แล้ว)"""
    return (f"<{tag} class='win {cls}'{attrs}><div class='wt'><span class='tt'>{title}</span>{WB}</div>"
            f"<div class='{inner}'>{body}</div></{tag}>")


SHELL_JS = r"""
(()=>{
const $=(s,el=document)=>el.querySelector(s);const $$=(s,el=document)=>[...el.querySelectorAll(s)];
const store={get(k,d){try{const v=localStorage.getItem(k);return v===null?d:JSON.parse(v);}catch(e){return d;}},
 set(k,v){try{if(v===null)localStorage.removeItem(k);else localStorage.setItem(k,JSON.stringify(v));}catch(e){}}};
const side=$('#side'),sb=$('#sideBtn'),ss=$('#sideScrim');
function sideOpen(o){side.classList.toggle('open',o);ss.hidden=!o;if(sb)sb.setAttribute('aria-expanded',o);}
if(sb)sb.addEventListener('click',()=>sideOpen(!side.classList.contains('open')));if(ss)ss.addEventListener('click',()=>sideOpen(false));
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&side.classList.contains('open'))sideOpen(false);});
side.addEventListener('click',e=>{if(e.target.closest('a[data-go],a[data-home]'))sideOpen(false);});
// แบนเนอร์เลื่อนเอง
const slides=$$('.hero .slide'),dots=$$('.hero .dots button');let si=0,tm=0,hold=false;
function show(i){if(!slides.length)return;si=(i+slides.length)%slides.length;
 slides.forEach((s,k)=>{s.classList.toggle('on',k===si);if(k===si)s.removeAttribute('inert');else s.setAttribute('inert','');});
 dots.forEach((d,k)=>d.setAttribute('aria-current',k===si));}
dots.forEach((d,k)=>d.addEventListener('click',()=>{show(k);restart();}));
const calm=matchMedia('(prefers-reduced-motion:reduce)').matches;
function restart(){clearInterval(tm);if(slides.length>1&&!calm)tm=setInterval(()=>{if(!hold&&!document.body.classList.contains('editing'))show(si+1);},7000);}
const hero=$('.hero');if(hero){hero.addEventListener('mouseenter',()=>hold=true);hero.addEventListener('mouseleave',()=>hold=false);
 hero.addEventListener('focusin',()=>hold=true);hero.addEventListener('focusout',()=>hold=false);}
show(0);restart();
// ปุ่มลูกศรเลื่อนการ์ด
$$('[data-scroll]').forEach(b=>b.addEventListener('click',()=>{const t=document.getElementById(b.dataset.scroll);
 if(t)t.scrollBy({left:(+b.dataset.dir||1)*t.clientWidth*.9,behavior:calm?'auto':'smooth'});}));
// โหมดแก้ไข (คนแก้ร้านเท่านั้น)
const tg=$('#editToggle');
if(tg){const set=on=>{document.body.classList.toggle('editing',on);tg.setAttribute('aria-pressed',on);store.set('cc-edit',on?1:null);
  document.dispatchEvent(new CustomEvent('cc-edit'));};
 tg.addEventListener('click',()=>set(!document.body.classList.contains('editing')));set(!!store.get('cc-edit',0));}
window.CC_toast=t=>{const el=document.createElement('div');el.className='toast';el.setAttribute('role','status');el.textContent=t;
 document.body.append(el);setTimeout(()=>el.remove(),2200);};
})();
"""

# ---------------------------------------------------------------- JS แก้หน้าเว็บ (คนแก้ร้านเท่านั้น)

SITE_JS = r"""
(()=>{
const S=JSON.parse(document.getElementById('state').textContent);if(!S.siteEdit)return;
const $=(s,el=document)=>el.querySelector(s);const $$=(s,el=document)=>[...el.querySelectorAll(s)];
const el=(tag,props={},kids=[])=>{const e=document.createElement(tag);for(const[k,v]of Object.entries(props)){
 if(k==='text')e.textContent=v;else if(k==='on')for(const[ev,f]of Object.entries(v))e.addEventListener(ev,f);
 else if(v!==false&&v!=null)e.setAttribute(k,v===true?'':v);}for(const c of kids)if(c)e.append(c);return e;};
const V=S.siteEdit.values,P=S.siteEdit.presets,COLORS=['c0','c1','c2','c3','c4','c5','c6'];
const SL={
 logo:{t:'โลโก้',f:[['text','ข้อความใต้โลโก้ (ว่าง = ไม่มี)','text',40]],i:[['img','รูปโลโก้','PNG พื้นใส · กว้างราว 640px']]},
 tiles:{t:'ปุ่มลัด (ใต้แบนเนอร์)',f:[['label','ชื่อปุ่ม (ตอนมีรูป ใช้เป็นชื่อให้โปรแกรมอ่านจอ)','text',24],['link','กดแล้วไปที่','link'],['color','สีพื้น (ตอนไม่มีรูป)','color']],
  i:[['img','รูปปุ่ม','จัตุรัส ราว 400×400 · ใส่ตัวหนังสือในรูปได้เลย']],list:1},
 hero:{t:'แบนเนอร์',f:[['title','หัวข้อ (ว่าง = ชื่อร้าน)','text',70],['sub','คำโปรย','area',220],['btn','ข้อความปุ่ม (ว่าง = ไม่มีปุ่ม)','text',24],
  ['link','ปุ่มไปที่','link'],['color','สีพื้น (ตอนไม่มีรูปพื้นหลัง)','color']],
  i:[['bg','รูปพื้นหลัง','แนวนอน 2:1 ราว 1600×800 · หัวข้อว่าง = ไม่มีตัวหนังสือทับรูป'],['art','รูปตัวละคร / ของ ทางขวา','PNG พื้นใส สูงราว 600px']],list:1},
 promos:{t:'การ์ดโปรโมต (แถบขวา)',f:[['title','หัวข้อ','text',40],['text','ข้อความ','area',160],['btn','ข้อความปุ่ม','text',24],
  ['link','กดแล้วไปที่','link'],['color','สีพื้น (ตอนไม่มีรูป)','color']],i:[['img','รูปประกอบการ์ด','PNG พื้นใส (สติกเกอร์) ราว 400×300 · วางมุมขวาล่าง']],list:1},
 cats:{t:'หมวด',f:[['color','สีสติกเกอร์ชื่อหมวด (หมวดที่ไม่มีรูป)','color'],['desc','คำอธิบายหมวด · ขึ้นต้น ! = กล่องเตือนสีแดง · * = กล่องไฮไลต์','area',1500]],
  i:[['img','รูปหน้าปกหมวด','สติกเกอร์ PNG พื้นใส หรือรูปจัตุรัส ราว 600×600']]},
 deco:{t:'ของตกแต่ง',f:[],i:[['bg','ภาพพื้นหลังทั้งหน้า (หลังกรอบเว็บ)','ใหญ่ ราว 1920×1080 · GIF ขยับได้'],
  ['left','ตกแต่งมุมซ้ายล่าง','PNG พื้นใส สูงราว 300px · ซ่อนในมือถือ'],['right','ตกแต่งมุมขวาล่าง','PNG พื้นใส สูงราว 300px · ซ่อนในมือถือ']]},
 theme:{t:'สีธีม',f:[['preset','โทนพื้นหลัง','preset'],['accent','สีหลัก (ไฮไลต์/แถบหัวหน้าต่าง/เลื่อม) — ว่าง = ตามโทน','hex'],
  ['accent2','สีรอง — ว่าง = ตามโทน','hex']],i:[]},
 donate:{t:'หัวหน้า Donate',f:[['title','หัวข้อ','text',60],['intro','ข้อความแนะนำ (ว่าง = ข้อความเริ่มต้น)','area',400],
  ['color','สีพื้น (ตอนไม่มีรูป)','color'],['rate','เติมคุกกี้ตามยอด: 1 บาท = กี่คุกกี้ (0 = ปิด)','num']],i:[['img','รูปหัวหน้า','แนวนอน ราว 1400×520']]}};
const LINKS=[['spin','ห้องหมุนวงล้อ'],['donate','หน้า Donate'],['wallet','กระเป๋าคุกกี้'],['discord','เข้าดิส'],['#all','ของทั้งหมด'],['/','หน้าแรก']];
const dlg=$('#siteDlg'),form=$('#siteForm'),box=$('#siteFields'),err=$('#siteErr');let cur=null,delArm=0;
function valueOf(slot,key){if(slot==='cats'){const c=(S.cats||[]).find(x=>x.name===key)||{};
  return Object.assign({color:c.color||'c0',img:'',desc:c.desc||''},V.cats[key]||{});}
 if(['tiles','hero','promos'].includes(slot))return key==='new'?{}:(V[slot][key]||{});
 const v=Object.assign({},V[slot]||{});if(slot==='donate')v.rate=S.siteEdit.rate;return v;}
function field([k,label,kind,max],v){
 if(kind==='color'){const g=el('div',{class:'swatches',role:'radiogroup','aria-label':label});
  COLORS.forEach(c=>g.append(el('label',{title:c},[el('input',{type:'radio',name:k,value:c,checked:(v[k]||'c0')===c,'aria-label':'สี '+c}),el('span',{class:c})])));
  return el('div',{class:'fld w'},[el('span',{text:label}),g]);}
 if(kind==='preset'){const g=el('div',{class:'presets',role:'radiogroup','aria-label':label});
  for(const[name,p]of Object.entries(P))g.append(el('label',{},[el('input',{type:'radio',name:k,value:name,checked:(v[k]||'glitter')===name}),
   el('i',{},[el('b',{style:'background:'+p.page}),el('b',{style:'background:'+(p.glit==='transparent'?p.card2:p.glit)}),el('b',{style:'background:'+(p.teal||'#FF4FB0')})]),el('span',{text:p.label})]));
  return el('div',{class:'fld w'},[el('span',{text:label}),g]);}
 if(kind==='hex'){const t=el('input',{type:'text',name:k,value:v[k]||'',placeholder:k==='accent'?'#FF4FB0':'#39C5BB',maxlength:'7',spellcheck:'false'});
  const c=el('input',{type:'color',value:/^#[0-9a-fA-F]{6}$/.test(v[k]||'')?v[k]:(k==='accent'?'#ff4fb0':'#39c5bb'),'aria-label':label});
  c.addEventListener('input',()=>t.value=c.value.toUpperCase());
  return el('label',{class:'fld w'},[label,el('span',{class:'hexrow'},[c,t])]);}
 if(kind==='area')return el('label',{class:'fld w'},[label,el('textarea',{name:k,maxlength:String(max)},[document.createTextNode(v[k]||'')])]);
 if(kind==='num')return el('label',{class:'fld w'},[label,el('input',{type:'number',name:k,min:'0',max:'1000000',value:v[k]==null?'':String(v[k])})]);
 if(kind==='link'){const id='dl-'+k;const i=el('input',{name:k,value:v[k]||'',maxlength:'300',list:id,spellcheck:'false',placeholder:'spin / donate / /?c=หมวด / https://...'});
  const d=el('datalist',{id});LINKS.forEach(([a,b])=>d.append(el('option',{value:a,label:b})));
  return el('label',{class:'fld w'},[label,i,d,el('small',{text:'spin = ห้องหมุนวงล้อ · donate = หน้า Donate · wallet = กระเป๋า · discord = เข้าดิส · หรือใส่ลิงก์ https://'})]);}
 return el('label',{class:'fld w'},[label,el('input',{name:k,value:v[k]||'',maxlength:String(max)})]);}
let prev=[];
function imageField([k,label,hint],v){const pv=el('img',{alt:'',hidden:!v[k]});if(v[k])pv.src='/img/'+v[k];
 const fi=el('input',{type:'file',name:k,accept:'image/png,image/jpeg,image/webp,image/gif','aria-label':label});
 fi.addEventListener('change',()=>{const f=fi.files[0];if(f){const u=URL.createObjectURL(f);prev.push(u);pv.src=u;pv.hidden=false;}});
 const kids=[el('span',{text:label}),el('div',{class:'imgrow'},[pv,fi]),el('small',{text:hint+' · ไม่เกิน 8 MB'})];
 if(v[k])kids.push(el('label',{class:'fld chk'},[el('input',{type:'checkbox',name:'rm_'+k}),'ลบรูปนี้ (กลับไปใช้รูปเริ่มต้น)']));
 return el('div',{class:'fld w'},kids);}
function open(addr){const m=/^([a-z]+)(?::([\s\S]*))?$/.exec(addr||'');if(!m)return;const slot=m[1];const key0=m[2];const sp=SL[slot];if(!sp)return;
 const key=key0===undefined?null:(sp.list&&/^\d+$/.test(key0)?+key0:key0);
 cur={addr,slot,key};prev.forEach(u=>URL.revokeObjectURL(u));prev=[];form.reset();err.textContent='';delArm=0;box.replaceChildren();
 const v=valueOf(slot,key);
 $('#siteTitle').textContent=(key==='new'?'เพิ่ม':'แก้')+sp.t+(slot==='cats'?' '+key:'')+(sp.list&&key!=='new'?' #'+(key+1):'');
 sp.f.forEach(f=>box.append(field(f,v)));sp.i.forEach(i=>box.append(imageField(i,v)));
 const del=$('#siteDel'),mv=$('#siteMove');
 del.hidden=key==='new';del.textContent=sp.list?'ลบอันนี้':'รีเซ็ตเป็นค่าเริ่มต้น';
 mv.hidden=!sp.list||key==='new';$('#siteSave').disabled=false;dlg.showModal();
 const f1=$('input:not([type=radio]):not([type=file]):not([type=color]),textarea',box);if(f1)f1.focus();}
async function send(action){err.textContent='';const fd=new FormData(form);fd.set('slot',cur.addr);fd.set('action',action);
 fd.set('rev',S.siteEdit.rev||'');if(cur.slot==='donate')fd.set('rate_loaded',String(S.siteEdit.rate));
 for(const[k]of[...fd.entries()])if(k.startsWith('rm_'))fd.set(k,'1');
 for(const[k,v]of[...fd.entries()])if(v instanceof File&&!v.size)fd.delete(k);
 const big=[...fd.values()].find(v=>v instanceof File&&v.size>8*1024*1024);if(big){err.textContent='รูปใหญ่เกิน 8 MB';return;}
 const desc=fd.get('desc');fd.delete('desc');
 const b=$('#siteSave');b.disabled=true;
 try{let r=await fetch('/api/admin/site',{method:'POST',credentials:'same-origin',headers:{'X-CSRF-Token':S.csrf},body:fd});
  let d={};try{d=await r.json();}catch(e){}if(r.status===401){location.reload();return;}
  if(r.ok&&d.ok&&cur.slot==='cats'&&action==='save'&&desc!==null){
   r=await fetch('/api/admin/category',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':S.csrf},
    body:JSON.stringify({name:cur.key,desc:String(desc)})});d={};try{d=await r.json();}catch(e){}}
  if(r.ok&&d.ok){try{localStorage.setItem('cc-edit','1');}catch(e){}location.reload();return;}
  err.textContent=d.error||'บันทึกไม่สำเร็จ';}catch(x){err.textContent='เน็ตหลุด ลองใหม่อีกครั้ง';}b.disabled=false;}
form.addEventListener('submit',e=>{e.preventDefault();send('save');});
$('#siteDel').addEventListener('click',()=>{const b=$('#siteDel');if(!delArm){delArm=1;b.textContent='กดอีกครั้งเพื่อยืนยัน';return;}send('delete');});
$$('#siteMove button').forEach(b=>b.addEventListener('click',()=>send(b.dataset.mv)));
document.addEventListener('click',e=>{const b=e.target.closest('[data-slot]');if(!b||!b.dataset.slot)return;
 e.preventDefault();e.stopPropagation();open(b.dataset.slot);},true);
})();
"""

# ---------------------------------------------------------------- JS หน้าร้าน

JS = r"""
(()=>{
const S=JSON.parse(document.getElementById('state').textContent);
const $=(s,el=document)=>el.querySelector(s);const $$=(s,el=document)=>[...el.querySelectorAll(s)];
const fmt=n=>Number(n).toLocaleString('th-TH');
const CKT=document.getElementById('ckTpl');const ck=()=>CKT.content.firstElementChild.cloneNode(true);
const money=n=>{const s=document.createElement('span');s.className='money';s.append(fmt(n),ck());return s;};
const DOT={claimed:'ok',done:'ok',partial:'ok',failed:'bad',problem:'bad',refunded:'off',cancelled:'off'};
const dot=k=>{const s=document.createElement('span');s.className='dot '+(DOT[k]||'wait');return s;};
const store={get(k,d){try{const v=localStorage.getItem(k);return v===null?d:JSON.parse(v);}catch(e){return d;}},
 set(k,v){try{if(v===null)localStorage.removeItem(k);else localStorage.setItem(k,JSON.stringify(v));}catch(e){}}};
const el=(tag,props={},kids=[])=>{const e=document.createElement(tag);for(const[k,v]of Object.entries(props)){
 if(k==='text')e.textContent=v;else if(k==='on')for(const[ev,f]of Object.entries(v))e.addEventListener(ev,f);
 else if(v!==false&&v!=null)e.setAttribute(k,v===true?'':v);}for(const c of kids)if(c)e.append(c);return e;};
const U=S.user;
// ------------------------------------------------------------------ ค้นหา / กรอง / เรียง
const grid=$('#grid');
const ITEMS=$$('.item[data-code]',grid).map((e,i)=>({el:e,code:e.dataset.code,text:e.dataset.text||'',
 price:+e.dataset.price,cat:e.dataset.cat||'',state:e.dataset.state,ckx:e.dataset.ckx==='1',limit:+e.dataset.limit||0,
 stock:e.dataset.stock===''?null:+e.dataset.stock,end:+e.dataset.end||0,upd:+e.dataset.upd||0,idx:i,adm:e.classList.contains('adm-only'),
 name:e.dataset.name||''}));
const DEF={q:'',cat:'*',min:'',max:'',afford:false,ship:'',st:'',lim:false,stk:false,sort:'rec'};
const F=Object.assign({},DEF);
const SORTS_KEYS={rec:1,asc:1,desc:1,name:1,new:1,end:1};
const hasSort=v=>Object.prototype.hasOwnProperty.call(SORTS_KEYS,v);
const CATL=S.cats||[];const CATS=new Set(CATL.map(c=>c.name));
const OK={sort:hasSort,st:v=>['','open','hot','soon','soldout'].includes(v),
 ship:v=>['','game','manual'].includes(v),cat:v=>CATS.has(v),min:v=>/^\d{0,9}$/.test(v),max:v=>/^\d{0,9}$/.test(v),
 q:v=>v.length<=100};
(()=>{const p=new URLSearchParams(location.search);for(const k of Object.keys(DEF)){if(!p.has(k))continue;
 const v=p.get(k);if(typeof DEF[k]==='boolean')F[k]=v==='1';else if(!OK[k]||OK[k](v))F[k]=v;}})();
const editing=()=>document.body.classList.contains('editing');
const affordable=it=>U&&U.can_redeem&&it.price<=U.balance&&((U.caps||{})[it.code]||0)>0;
function match(it){if(it.adm&&!editing())return false;
 if(F.cat!=='*'&&it.cat!==F.cat)return false;
 if(F.q){const terms=F.q.toLowerCase().split(/\s+/).filter(Boolean);if(!terms.every(t=>it.text.includes(t)))return false;}
 if(F.min!==''&&it.price<+F.min)return false;if(F.max!==''&&it.price>+F.max)return false;
 if(F.afford&&!affordable(it))return false;
 if(F.ship==='game'&&!it.ckx)return false;if(F.ship==='manual'&&it.ckx)return false;
 if(F.st==='open'&&!(it.state==='open'||it.state==='hot'))return false;
 if(F.st&&F.st!=='open'&&it.state!==F.st)return false;
 if(F.lim&&!it.limit)return false;if(F.stk&&it.stock===null)return false;return true;}
const SORTS={rec:(a,b)=>a.idx-b.idx,asc:(a,b)=>a.price-b.price||a.idx-b.idx,desc:(a,b)=>b.price-a.price||a.idx-b.idx,
 name:(a,b)=>a.name.localeCompare(b.name,'th'),new:(a,b)=>b.upd-a.upd||a.idx-b.idx,
 end:(a,b)=>(a.end||9e12)-(b.end||9e12)||a.idx-b.idx};
const LABEL={afford:'แลกได้ตอนนี้',lim:'จำกัดต่อคน',stk:'มีสต็อกจำกัด',game:'ส่งเข้าเกมเอง',manual:'แอดมินส่งให้',
 open:'เปิดอยู่',hot:'ใกล้หมดเวลา',soon:'เร็วๆ นี้',soldout:'หมดแล้ว'};
function syncControls(){const q=$('#q');if(q&&q.value!==F.q)q.value=F.q;
 $$('[data-type]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.type===typeOf()));
 const mn=$('#pmin'),mx=$('#pmax');if(mn)mn.value=F.min;if(mx)mx.value=F.max;
 $$('[data-tog]').forEach(b=>b.setAttribute('aria-pressed',!!F[b.dataset.tog]));
 $$('[data-ship]').forEach(b=>b.setAttribute('aria-pressed',F.ship===b.dataset.ship));
 $$('[data-st]').forEach(b=>b.setAttribute('aria-pressed',F.st===b.dataset.st));
 const so=$('#sort');if(so)so.value=F.sort;}
function apply(){try{applyNow();}catch(e){console.error(e);Object.assign(F,DEF);try{applyNow();}catch(x){}}}
function applyNow(){const shown=ITEMS.filter(match).sort(hasSort(F.sort)?SORTS[F.sort]:SORTS.rec);const set=new Set(shown);
 ITEMS.forEach(it=>{it.el.hidden=!set.has(it);});shown.forEach(it=>grid.append(it.el));
 const total=ITEMS.filter(it=>(!it.adm||editing())&&(F.cat==='*'||it.cat===F.cat)).length;
 const cnt=$('#count');if(cnt)cnt.replaceChildren('พบ ',el('b',{text:fmt(shown.length)}),` จาก ${fmt(total)} รายการ`);
 $('#noMatch').hidden=!!shown.length||!total;
 const act=$('#activeChips');if(act){act.replaceChildren();const add=(t,fn)=>act.append(el('button',{type:'button',text:t,
  'aria-label':'เอาตัวกรอง '+t+' ออก',on:{click:()=>{fn();changed();}}}));
  if(F.q)add('“'+F.q+'”',()=>F.q='');
  if(F.min!==''||F.max!=='')add(`ราคา ${F.min||0}–${F.max||'∞'}`,()=>{F.min='';F.max='';});
  for(const k of['afford','lim','stk'])if(F[k])add(LABEL[k],()=>F[k]=false);
  if(F.ship)add(LABEL[F.ship],()=>F.ship='');if(F.st)add(LABEL[F.st],()=>F.st='');}
 const p=new URLSearchParams();if(curCat)p.set('c',curCat);
 for(const[k,v]of Object.entries(F))if(k!=='cat'&&v!==DEF[k])p.set(k,typeof v==='boolean'?'1':v);
 const qs=p.toString();if(location.search!==(qs?'?'+qs:''))try{history.replaceState(history.state,'',qs?'?'+qs:location.pathname);}catch(e){}}
function changed(){syncControls();apply();}
let qTimer;const q=$('#q');if(q)q.addEventListener('input',()=>{clearTimeout(qTimer);qTimer=setTimeout(()=>{F.q=q.value.trim();apply();},120);});
document.addEventListener('keydown',e=>{if(e.key==='/'&&!/INPUT|TEXTAREA|SELECT/.test((document.activeElement||{}).tagName||'')){e.preventDefault();q&&q.focus();}});
// ---- หน้าแรก / หน้าหมวด
let curCat=null;
function typeOf(){if(F.afford)return'afford';if(F.ship)return F.ship;if(F.st==='hot')return'hot';return'';}
function setType(t){F.afford=t==='afford';F.ship=(t==='game'||t==='manual')?t:'';F.st=t==='hot'?'hot':'';F.lim=false;F.stk=false;
 F.min='';F.max='';}
function fillCat(c){const cv=$('#ciCover');cv.replaceChildren();
 const t=document.getElementById('cv-'+c.tpl);if(t)cv.append(t.content.cloneNode(true));$('#ciBar').textContent=c.name;
 $('#ciName').textContent=c.name;$('#ciCount').textContent=c.count+' รายการ';const d=$('#ciDesc');d.replaceChildren();
 const lines=(c.desc||'').split('\n').map(x=>x.trim()).filter(Boolean);
 if(!lines.length)d.append(el('p',{class:'soft',text:'กดที่ของเพื่อดูรายละเอียดแล้วใส่ตะกร้า'}));
 lines.forEach(x=>{if(x[0]==='!')d.append(el('p',{class:'warn',text:x.slice(1).trim()}));
  else if(x[0]==='*')d.append(el('p',{class:'info',text:x.slice(1).trim()}));else d.append(el('p',{text:x}));});
 const ce=$('#ciEdit');if(ce)ce.dataset.slot='cats:'+c.name;}
function markNav(){$$('.snav a[data-go]').forEach(a=>a.classList.toggle('on',a.dataset.go===curCat));
 $$('.snav a[data-home]').forEach(a=>a.classList.toggle('on',!curCat));}
function showCat(name,push){const c=CATL.find(x=>x.name===name);if(!c)return showHome(push);curCat=name;F.cat=name;
 if(push){setType('');F.q='';try{history.pushState({c:name},'','?c='+encodeURIComponent(name));}catch(e){}}
 document.body.classList.add('catmode');fillCat(c);markNav();changed();if(push)scrollTo(0,0);}
function showHome(push,keep){const was=curCat;curCat=null;F.cat='*';
 if(push){setType('');try{history.pushState({},'',location.pathname);}catch(e){}}
 document.body.classList.remove('catmode');markNav();changed();if(push&&was&&!keep)scrollTo(0,0);}
document.addEventListener('click',e=>{const a=e.target.closest('a[data-go]');if(!a||e.target.closest('[data-slot]'))return;
 if(e.button||e.ctrlKey||e.metaKey||e.shiftKey)return;e.preventDefault();showCat(a.dataset.go,true);});
$$('a[data-home]').forEach(a=>a.addEventListener('click',e=>{if(e.button||e.ctrlKey||e.metaKey)return;e.preventDefault();showHome(true);}));
$$('a[href="#all"],a[href="/#all"]').forEach(a=>a.addEventListener('click',e=>{e.preventDefault();if(curCat)showHome(true,true);
 const t=$('#all');if(t)t.scrollIntoView({behavior:'smooth'});}));
(()=>{const c=new URLSearchParams(location.search).get('c');if(c&&CATS.has(c)){curCat=c;F.cat=c;document.body.classList.add('catmode');
 fillCat(CATL.find(x=>x.name===c));}markNav();})();
const bh=$('#backHome');if(bh)bh.addEventListener('click',()=>showHome(true));
$$('[data-type]').forEach(b=>b.addEventListener('click',()=>{setType(b.dataset.type);changed();}));
addEventListener('popstate',()=>{const c=new URLSearchParams(location.search).get('c');if(c&&CATS.has(c))showCat(c,false);
 else{setType('');showHome(false);}});
for(const[id,key]of[['pmin','min'],['pmax','max']]){const i=$('#'+id);if(i)i.addEventListener('input',()=>{
 F[key]=i.value===''||isNaN(+i.value)?'':String(Math.max(0,Math.floor(+i.value)));apply();});}
$$('[data-tog]').forEach(b=>b.addEventListener('click',()=>{F[b.dataset.tog]=!F[b.dataset.tog];changed();}));
$$('[data-ship]').forEach(b=>b.addEventListener('click',()=>{F.ship=F.ship===b.dataset.ship?'':b.dataset.ship;changed();}));
$$('[data-st]').forEach(b=>b.addEventListener('click',()=>{F.st=b.dataset.st;changed();}));
const so=$('#sort');if(so)so.addEventListener('change',()=>{F.sort=hasSort(so.value)?so.value:'rec';apply();});
$$('[data-clear]').forEach(b=>b.addEventListener('click',()=>{Object.assign(F,DEF);if(curCat)F.cat=curCat;changed();}));
const fb=$('#filterBtn'),fp=$('#filters');
if(fb&&fp){const open=F.min||F.max||F.lim||F.stk||(F.st&&F.st!=='hot')||F.sort!=='rec'||F.afford||F.ship;fp.hidden=!open;
 fb.setAttribute('aria-expanded',!!open);fb.addEventListener('click',()=>{fp.hidden=!fp.hidden;fb.setAttribute('aria-expanded',!fp.hidden);});}
const vb=$('#viewBtn');function setView(v){grid.classList.toggle('list',v==='list');if(vb){vb.setAttribute('aria-pressed',v==='list');
 vb.title=v==='list'?'มุมมองตาราง':'มุมมองรายการ';}store.set('cc-view',v);}
if(vb){setView(store.get('cc-view','grid'));vb.addEventListener('click',()=>setView(grid.classList.contains('list')?'grid':'list'));}
document.addEventListener('cc-edit',()=>apply());
// ------------------------------------------------------------------ แก้ของในร้าน (เฉพาะคนแก้ร้าน)
if(S.admin){
 const dlg=$('#editDlg'),form=$('#editForm'),err=$('#editErr');let delArm=0,delTimer=0,prevURL=null;
 const post=async(url,body,isForm)=>{const r=await fetch(url,{method:'POST',credentials:'same-origin',
  headers:isForm?{'X-CSRF-Token':S.csrf}:{'Content-Type':'application/json','X-CSRF-Token':S.csrf},
  body:isForm?body:JSON.stringify(body)});let d={};try{d=await r.json();}catch(e){}if(r.status===401)location.reload();
  return{ok:r.ok&&d.ok,d};};
 const done=()=>{store.set('cc-edit',1);location.reload();};
 function openEdit(code){const raw=code?S.admin.items[code]:null;form.reset();err.textContent='';delArm=0;
  const f=form.elements;f.original.value=code||'';
  const v=raw||{code:'',name:'',price:'',ckx:'',description:'',category:curCat||'',limit:0,stock:-1,start:'',end:'',active:true,sort:0,image_url:''};
  for(const k of['code','name','price','ckx','description','category','limit','stock','start','end','sort'])f[k].value=v[k]==null?'':v[k];
  f.stock_loaded.value=code?String(v.stock):'';clearTimeout(delTimer);if(prevURL){URL.revokeObjectURL(prevURL);prevURL=null;}
  f.active.checked=!!v.active;f.remove_image.checked=false;const pv=$('#imgPrev');pv.hidden=!v.image_url;if(v.image_url)pv.src=v.image_url;
  $('#remWrap').hidden=!v.image_url;$('#delBtn').hidden=!code;$('#delBtn').textContent='ลบของนี้';
  $('#editTitle').textContent=code?'แก้ของ: '+(v.name||code):'เพิ่มของใหม่';dlg.showModal();f.name.focus();}
 $$('.ebtn').forEach(b=>b.addEventListener('click',e=>{e.stopPropagation();openEdit(b.dataset.edit);}));
 $$('[data-add-item]').forEach(b=>b.addEventListener('click',()=>openEdit(null)));
 form.elements.image.addEventListener('change',()=>{const fl=form.elements.image.files[0];const pv=$('#imgPrev');
  if(fl){if(prevURL)URL.revokeObjectURL(prevURL);prevURL=URL.createObjectURL(fl);pv.src=prevURL;pv.hidden=false;}});
 form.addEventListener('submit',async e=>{e.preventDefault();err.textContent='';const fd=new FormData(form);
  fd.set('active',form.elements.active.checked?'1':'0');fd.set('remove_image',form.elements.remove_image.checked?'1':'0');
  const fl=form.elements.image.files[0];if(!fl)fd.delete('image');
  else if(fl.size>8*1024*1024){err.textContent='รูปใหญ่เกิน 8 MB';return;}
  const b=$('#saveBtn');b.disabled=true;b.textContent='กำลังบันทึก…';
  try{const r=await post('/api/admin/item',fd,true);if(r.ok)return done();err.textContent=r.d.error||'บันทึกไม่สำเร็จ';}
  catch(x){err.textContent='เน็ตหลุด ลองใหม่อีกครั้ง';}b.disabled=false;b.textContent='บันทึก';});
 $('#delBtn').addEventListener('click',async()=>{const b=$('#delBtn');if(!delArm){delArm=1;b.textContent='กดอีกครั้งเพื่อลบจริง';
  clearTimeout(delTimer);delTimer=setTimeout(()=>{delArm=0;b.textContent='ลบของนี้';},4000);return;}
  try{const r=await post('/api/admin/item/delete',{code:form.elements.original.value});if(r.ok)return done();
   err.textContent=r.d.error||'ลบไม่สำเร็จ';}catch(x){err.textContent='เน็ตหลุด ลองใหม่อีกครั้ง';}});
 const pd=$('#pageDlg'),pf=$('#pageForm');
 $$('[data-page-edit]').forEach(b=>b.addEventListener('click',()=>{for(const k of['title','subtitle','notice'])pf.elements[k].value=S.page[k]||'';
  $('#pageErr').textContent='';pd.showModal();}));
 pf.addEventListener('submit',async e=>{e.preventDefault();const body={};for(const k of['title','subtitle','notice'])body[k]=pf.elements[k].value;
  try{const r=await post('/api/admin/page',body);if(r.ok)return done();$('#pageErr').textContent=r.d.error||'บันทึกไม่สำเร็จ';}
  catch(x){$('#pageErr').textContent='เน็ตหลุด ลองใหม่อีกครั้ง';}});}
// ---- รายละเอียดของ (กดที่การ์ด)
let itemActions=null;const idlg=$('#itemDlg');
function openItem(code){const card=grid.querySelector(`.item[data-code="${CSS.escape(code)}"]`);if(!card)return;
 const pic=$('#idPic');pic.replaceChildren();const im=$('.pic img',card);
 if(im)pic.append(el('img',{src:im.getAttribute('src'),alt:''}));else{const sv=$('.pic svg',card);if(sv){const k=sv.cloneNode(true);k.setAttribute('width','96');k.setAttribute('height','96');pic.append(k);}}
 $('#idCat').textContent=card.dataset.cat||'';$('#idName').textContent=card.dataset.name;
 const m=$('#idMeta');m.replaceChildren();const mm=$('.meta',card);if(mm)[...mm.children].forEach(x=>m.append(x.cloneNode(true)));
 const st=$('.badge',card);if(st)m.prepend(el('span',{text:st.textContent}));
 $('#idPrice').replaceChildren(money(+card.dataset.price));const ds=$('.desc',card);$('#idDesc').textContent=ds?ds.textContent:'';
 $('#idErr').textContent='';const act=$('#idAct');act.replaceChildren();
 if(itemActions)itemActions(code,act);else if(S.login)act.append(el('a',{class:'btn big',href:'/login',text:'ล็อกอินเพื่อแลก'}));
 if(!idlg.open)idlg.showModal();const main=$('#idAct .btn.big')||$('#idAct .btn');if(main)main.focus();}
grid.addEventListener('click',e=>{if(e.target.closest('button,a,input,select,.step'))return;
 const card=e.target.closest('.item[data-code]');if(card)openItem(card.dataset.code);});
$$('.fcard[data-open]').forEach(b=>b.addEventListener('click',()=>openItem(b.dataset.open)));
$$('[data-close]').forEach(b=>b.addEventListener('click',()=>b.closest('dialog').close()));
syncControls();apply();
if(!U)return;
// ------------------------------------------------------------------ ตะกร้า
const KEY='cc-cart-'+U.id;const PKEY=KEY+'-pending';let cart={};let busy=false;let memPending=null;
const cap=c=>(U.caps&&U.caps[c])||0;
const total=skip=>Object.entries(cart).reduce((t,[c,q])=>c===skip||!S.items[c]?t:t+S.items[c].price*q,0);
const count=()=>Object.values(cart).reduce((a,b)=>a+b,0);
const maxFor=c=>{const it=S.items[c];if(!it||!U.can_redeem)return 0;
 return Math.max(0,Math.min(cap(c),Math.floor((U.balance-total(c))/Math.max(1,it.price))));};
function clean(){for(const c of Object.keys(cart)){const q=parseInt(cart[c],10);
 if(!S.items[c]||!(q>0)||cap(c)<1)delete cart[c];else cart[c]=Math.min(q,cap(c));}}
function load(){const p=getPending();
 if(p&&Array.isArray(p.items)){cart={};p.items.forEach(l=>{if(l&&typeof l.code==='string'&&l.qty>0)cart[l.code]=l.qty;});
  if(p.ingame)$('#ing').value=p.ingame;return;}  // ตะกร้าที่ค้างผล = ตะกร้าที่ส่งไปจริง
 const v=store.get(KEY,{});cart=v&&typeof v==='object'?v:{};clean();}
function save(){store.set(KEY,cart);}
function getPending(){return memPending||store.get(PKEY,null);}
function setPending(p){memPending=p;store.set(PKEY,p||null);}
function syncInert(){const c=$('#cart');if(!c.classList.contains('open'))c.setAttribute('inert','');else c.removeAttribute('inert');}
function openCart(){$('#cart').classList.add('open');$('#scrim').hidden=false;syncInert();const x=$('#cartClose');if(x)x.focus();}
function closeCart(){$('#cart').classList.remove('open');$('#scrim').hidden=true;syncInert();}
const locked=()=>busy||!!getPending();
function setQty(c,q){if(locked()){showErr(busy?'กำลังแลกอยู่ รอสักครู่':'ตะกร้านี้ส่งไปแล้วแต่ยังไม่รู้ผล — กด "ส่งตะกร้าเดิมอีกครั้ง" ก่อน (ไม่โดนหักซ้ำ)');openCart();return;}
 if($('#done').childElementCount)resetDone();const had=cart[c]||0;q=Math.max(0,Math.min(q,maxFor(c)));
 if(q>0)cart[c]=q;else delete cart[c];save();render();
 if(q>had&&window.CC_toast&&!$('#cart').classList.contains('open'))CC_toast('ใส่ตะกร้าแล้ว · '+((S.items[c]||{}).name||''));}
function stepper(c){const q=cart[c]||0,lk=locked();return el('span',{class:'step'},[
 el('button',{type:'button','aria-label':'ลด',text:'−',disabled:lk,on:{click:()=>setQty(c,q-1)}}),
 el('output',{text:String(q)}),
 el('button',{type:'button','aria-label':'เพิ่ม',text:'+',disabled:lk||maxFor(c)<=q,on:{click:()=>setQty(c,q+1)}})]);}
function renderCards(){$$('.item[data-code]').forEach(card=>{const c=card.dataset.code;
 const pic=$('.pic',card);let qb=$('.qb',pic);if(cart[c]){if(!qb){qb=el('span',{class:'qb'});pic.append(qb);}qb.textContent='×'+cart[c];}
 else if(qb)qb.remove();
 const slot=$('.buy',card);if(!slot)return;slot.replaceChildren();card.classList.toggle('in',!!cart[c]);
 const it=S.items[c];if(!it)return;
 if(!U.can_redeem){slot.append(el('button',{class:'btn',disabled:true,text:'แลกไม่ได้'}));return;}
 if(cart[c]){slot.append(stepper(c));return;}
 const why=(U.why&&U.why[c])||'';const m=maxFor(c);
 if(cap(c)<1){slot.append(el('button',{class:'btn',disabled:true,text:why||'แลกไม่ได้'}));return;}
 if(m<1){slot.append(el('button',{class:'btn',disabled:true,text:'คุกกี้ไม่พอ'}));return;}
 slot.append(el('button',{class:'btn',type:'button',text:'ใส่ตะกร้า',disabled:locked(),on:{click:()=>setQty(c,1)}}));});}
function renderWallet(){for(const id of['bal','topBal'])if($('#'+id))$('#'+id).textContent=fmt(U.balance);
 const st=U.stats||{};if($('#stCount'))$('#stCount').textContent=fmt(st.count||0);
 if($('#stSpent'))$('#stSpent').textContent=fmt(st.spent||0);if($('#stPending'))$('#stPending').textContent=fmt(st.pending||0);
 const ul=$('#histList');if(!ul)return;ul.replaceChildren();
 (U.recent||[]).forEach(r=>ul.append(el('li',{},[dot(r.key),
  el('span',{class:'t',text:`${r.name} × ${r.qty}`}),el('span',{class:'s',text:`${r.status}  (${r.rid}${r.cart?', ตะกร้า '+r.cart:''})`})])));
 $('#histNone').hidden=!!(U.recent||[]).length;}
function needsName(){return Object.keys(cart).some(c=>S.items[c]&&S.items[c].ckx);}
function renderCart(){const box=$('#lines');box.replaceChildren();const done=!!$('#done').childElementCount;
 for(const[c,q]of Object.entries(cart)){const it=S.items[c];if(!it)continue;
  box.append(el('div',{class:'line'},[el('span',{class:'n',text:it.name}),
   el('span',{class:'p'},[money(it.price),` × ${q} = `,money(it.price*q)]),
   el('span',{class:'ctl'},[stepper(c),el('button',{class:'x',type:'button','aria-label':'เอาออก',text:'×',
    disabled:locked(),on:{click:()=>setQty(c,0)}})])]));}
 const n=count(),t=total(),left=U.balance-t;
 $('#cartEmpty').hidden=!!n||done;$('#cartCount').textContent=fmt(n);$('#cartCount').hidden=!n;
 const nb=$('#cartBadge');if(nb){nb.textContent=fmt(n);nb.hidden=!n;}
 $('#sumTotal').replaceChildren(money(t));const l=$('#sumLeft');l.replaceChildren(money(left));l.classList.toggle('neg',left<0);
 $('#ingWrap').hidden=!needsName()||done;$('#ing').disabled=locked();
 const pend=getPending();$('#go').disabled=busy||(!n&&!pend)||(!pend&&left<0)||!U.can_redeem;
 if(!busy)$('#go').textContent=pend?'ส่งตะกร้าเดิมอีกครั้ง':'ยืนยันแลก';
 document.body.classList.toggle('has-cart',!!n&&!done);$('#barCount').textContent=fmt(n)+' ชิ้น';$('#barTotal').replaceChildren(money(t));}
function render(){if(!getPending())clean();renderCards();renderWallet();renderCart();apply();syncInert();}
function showErr(t){$('#err').textContent=t||'';}
async function refresh(){try{const r=await fetch('/api/me',{credentials:'same-origin',cache:'no-store'});
 if(r.status===401){location.reload();return;}if(!r.ok)return;const d=await r.json();
 if(d.user){Object.assign(U,d.user);if(d.items)S.items=d.items;render();updateDone();}}catch(e){}}
let lastCart=null;let poll=null;
function updateDone(){if(!lastCart)return;const by=Object.fromEntries((U.recent||[]).map(r=>[r.rid,r]));
 const ul=$('#doneList');if(!ul)return;ul.replaceChildren();
 lastCart.lines.forEach(l=>{const r=by[l.rid]||l;ul.append(el('li',{},[dot(r.key),el('span',{text:`${l.name} × ${l.qty}`}),
  el('span',{text:r.status})]));});}
function resetDone(){$('#done').replaceChildren();lastCart=null;clearInterval(poll);$('#cartBody').hidden=false;$('#sum').hidden=false;
 $('#go').hidden=false;$('#more').hidden=true;}
function showDone(c){lastCart=c;$('#done').replaceChildren(el('div',{class:'okbox'},[
 el('h4',{text:`แลกสำเร็จ ตะกร้า ${c.label}`}),
 el('p',{},['ใช้ไป ',money(c.total),'เหลือ ',money(U.balance)]),
 el('ul',{id:'doneList'}),
 el('p',{text:c.has_ckx?'ของที่ส่งเข้าเกมเอง: เข้าเกมแล้วกดรับที่ปุ่มบ้านคุกกี้':'แอดมินจะส่งของให้เร็วๆ นี้'}),
 U.wallet_url?el('p',{},[el('a',{href:U.wallet_url,target:'_blank',rel:'noopener',text:'ดูสถานะในกระเป๋าคุกกี้บน Discord'})]):null]));
 updateDone();$('#cartBody').hidden=true;$('#sum').hidden=true;$('#go').hidden=true;$('#more').hidden=false;openCart();
 clearInterval(poll);let k=0;poll=setInterval(()=>{if(++k>20||!lastCart){clearInterval(poll);return;}refresh();},6000);}
async function send(body){try{const r=await fetch('/api/checkout',{method:'POST',credentials:'same-origin',
  headers:{'Content-Type':'application/json','X-CSRF-Token':S.csrf},body:JSON.stringify(body)});
 let d=null;try{d=await r.json();}catch(e){}
 if(r.status===401){location.reload();return{kind:'reload'};}
 if(d&&d.state){Object.assign(U,d.state);if(d.items)S.items=d.items;}
 if(r.ok&&d&&d.ok)return{kind:'ok',d};
 if(d&&d.ok===false&&r.status>=400&&r.status<500)return{kind:'refused',d};
 return{kind:'unknown',d};}catch(e){return{kind:'unknown',d:null};}}
function finish(res){if(res.kind==='ok'){setPending(null);cart={};save();showDone(res.d.cart);}
 else if(res.kind==='refused'){setPending(null);save();showErr(res.d.error||'แลกไม่สำเร็จ ลองใหม่อีกครั้ง');}
 else if(res.kind==='unknown')showErr((res.d&&res.d.error)||'ยังไม่รู้ผล (เน็ต/เซิฟสะดุด) — กดยืนยันอีกครั้ง ระบบจะเช็คให้ ไม่โดนหักซ้ำ');}
async function checkout(){if(busy)return;showErr('');let body=getPending();
 if(!body){const name=$('#ing').value.trim();
  if(needsName()&&!name){showErr('ใส่ชื่อในเกมก่อน (ชื่อที่ใช้ล็อกอินเข้าเซิฟ)');$('#ing').focus();return;}
  const id=crypto.randomUUID?crypto.randomUUID():String(Date.now())+Math.random().toString(16).slice(2);
  body={nonce:id,ingame:name,expected_total:total(),items:Object.entries(cart).map(([code,qty])=>({code,qty}))};
  setPending(body);}
 busy=true;render();$('#go').disabled=true;$('#go').textContent='กำลังแลก…';
 const res=await send(body);busy=false;finish(res);render();}
async function resume(){const p=getPending();if(!p)return;const res=await send(p);if(res.kind==='reload')return;
 if(res.kind==='ok'){finish(res);render();}else if(res.kind==='refused'){setPending(null);render();}}
itemActions=(c,box)=>{const it=S.items[c];const err=$('#idErr');
 if(!it){err.textContent=(U.why&&U.why[c])||'ตอนนี้แลกชิ้นนี้ไม่ได้';return;}
 if(!U.can_redeem){err.textContent=U.reason||'ตอนนี้ยังแลกของไม่ได้';return;}
 const max=maxFor(c);const inCart=cart[c]||0;let q=Math.max(1,Math.min(inCart||1,max||1));
 if(cap(c)<1){err.textContent=(U.why&&U.why[c])||'แลกชิ้นนี้ไม่ได้แล้ว';return;}
 if(max<1&&!inCart){err.textContent='คุกกี้ไม่พอ';return;}
 if(locked()){err.textContent='รอผลตะกร้าเดิมก่อน แล้วค่อยเพิ่มของ';return;}
 const out=el('output',{text:String(q)});const minus=el('button',{type:'button','aria-label':'ลด',text:'−'});
 const plus=el('button',{type:'button','aria-label':'เพิ่ม',text:'+'});
 const sync=()=>{out.textContent=String(q);minus.disabled=q<=1;plus.disabled=q>=max;};
 minus.addEventListener('click',()=>{q=Math.max(1,q-1);sync();});plus.addEventListener('click',()=>{q=Math.min(max,q+1);sync();});sync();
 box.append(el('div',{class:'qty'},[el('span',{text:'จำนวน'}),el('span',{class:'step'},[minus,out,plus])]));
 if(inCart)box.append(el('button',{class:'btn alt',type:'button',text:'เอาออก',on:{click:()=>{setQty(c,0);idlg.close();}}}));
 box.append(el('button',{class:'btn big',type:'button',text:inCart?'อัปเดตตะกร้า':'ใส่ตะกร้า',
  on:{click:()=>{setQty(c,q);idlg.close();}}}));};
$$('[data-open-cart]').forEach(b=>b.addEventListener('click',openCart));$('#go').addEventListener('click',checkout);
$('#cartClose').addEventListener('click',closeCart);$('#scrim').addEventListener('click',closeCart);
$('#more').addEventListener('click',()=>{resetDone();render();closeCart();});
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeCart();});
if(!$('#ing').value)$('#ing').value=U.ingame||'';
load();render();resume();
})();
"""


# ---------------------------------------------------------------- ชิ้นส่วน HTML ร่วม

def site_links(meta: dict, user) -> dict:
    return {"spin_url": meta.get("spin_url") or "", "invite_url": meta.get("invite_url") or "",
            "discord_url": meta.get("discord_url") or "", "wallet_url": (user or {}).get("wallet_url") or ""}


def _href(link: str, ctx: dict) -> str:
    """ลิงก์จากช่องที่แก้ได้ → attribute href (+ target) ที่ escape แล้ว · ว่าง = ''"""
    href, external = web_site.resolve_link(link, ctx)
    if not href:
        return ""
    e = html.escape
    return f" href='{e(href)}'" + (" target='_blank' rel='noopener'" if external else "")


def _sedit(slot: str, label: str = "แก้") -> str:
    return (f"<button class='sedit' type='button' data-slot='{html.escape(slot)}' title='{html.escape(label)}' "
            f"aria-label='{html.escape(label)}'>{px('edit', 24)}</button>")


# รูปในตัวตามลิงก์ของปุ่ม/การ์ด (ตอนยังไม่อัปรูปเอง)
TILE_IMG = {"#all": web_art.TILE_REDEEM, "/#all": web_art.TILE_REDEEM,
            "/donate": web_art.TILE_DONATE, "donate": web_art.TILE_DONATE}
TILE_ICON = {"spin": "dice", "wallet": "wallet", "discord": "message", "#all": "grid", "/": "store"}
PROMO_IMG = {"spin": web_art.COOKIE_FOIL, "/donate": web_art.COOKIE_BAR, "donate": web_art.COOKIE_BAR,
             "wallet": web_art.COOKIE_STICKER, "#all": web_art.COOKIE_PACK}


def _hidden(link: str, meta: dict, editor: bool):
    """ปุ่ม/การ์ดที่ลิงก์ไป Donate ตอนปิดระบบ Donate: คนทั่วไปไม่เห็น · คนแก้ร้านเห็นตอนโหมดแก้ไข — คืน None = ไม่ต้องแสดง"""
    if link in ("/donate", "donate") and not meta.get("donate_on"):
        return " adm-only" if editor else None
    return ""


def sidebar(site: dict, meta: dict, user, active: str, cats: list, editor: bool) -> str:
    e = html.escape
    ctx = site_links(meta, user)
    logo = site["logo"]
    name = logo["text"] or meta.get("title") or "Cookie Cheetah"
    src = img_url(logo["img"]) if logo["img"] else web_art.LOGO
    inner = f"<img src='{e(src)}' alt='{e(name)}' width='640' height='283'>"
    if logo["text"]:
        inner = f"<span style='display:grid;gap:4px;justify-items:center'>{inner}<span>{e(logo['text'])}</span></span>"
    out = [f"<div class='slot'><a class='logo' href='/' data-home>{inner}</a>{_sedit('logo', 'แก้โลโก้') if editor else ''}</div>"]
    nav = [f"<a href='/' data-home class='{'on' if active == 'shop' else ''}'>{px('home', 24)}<span>หน้าแรก</span></a>"]
    for c in cats:
        if not c["count"] and not editor:
            continue
        nav.append(f"<a href='/?c={e(quote(c['name']))}' data-go='{e(c['name'])}'{' class=adm-only' if not c['count'] else ''}>"
                   f"{art(c['art'], 24)}<span>{e(c['name'])}</span><small>{c['count']}</small></a>")
    out.append(f"<span class='slab'>&gt; CATEGORIES</span><nav class='snav' aria-label='หมวดหมู่'>{''.join(nav)}</nav>")
    more = []
    if meta.get("donate_on"):
        more.append(f"<a href='/donate' class='{'on' if active == 'donate' else ''}'>{px('heart', 24)}<span>Donate</span></a>")
    if user and active == "shop":
        more.append(f"<a href='#hist'>{px('clock', 24)}<span>ประวัติการแลก</span></a>")
    if user and user.get("wallet_url"):
        more.append(f"<a href='{e(user['wallet_url'])}' target='_blank' rel='noopener'>{px('wallet', 24)}"
                    f"<span>กระเป๋าคุกกี้</span>{px('external-link', 12)}</a>")
    if ctx["spin_url"]:
        more.append(f"<a href='{e(ctx['spin_url'])}' target='_blank' rel='noopener'>{px('dice', 24)}"
                    f"<span>หมุนวงล้อ</span>{px('external-link', 12)}</a>")
    if more:
        out.append(f"<div class='sdiv'></div><nav class='snav' aria-label='เมนูอื่น'>{''.join(more)}</nav>")
    foot = []
    support = meta.get("support_url") or meta.get("invite_url")
    if support:
        foot.append(f"<a class='help' href='{e(support)}' target='_blank' rel='noopener'>{px('message', 24)}"
                    "ติดต่อแอดมิน</a>")
    if user:  # มือถือ: ปุ่มออกจากระบบย้ายมาอยู่ในเมนู (แถบบนแคบ)
        foot.append(f"<a class='help mob-only' href='/logout'>{px('logout', 24)}ออกจากระบบ ({e(user.get('name') or '')})</a>")
    foot.append(f"<small>{e(meta.get('footer') or '')}</small>")
    out.append(f"<div class='sfoot'>{''.join(foot)}</div>")
    return (f"<aside class='side' id='side' aria-label='เมนูหลัก'>{''.join(out)}</aside>"
            "<div class='scrim' id='sideScrim' hidden></div>")


def tiles_html(site: dict, meta: dict, user, editor: bool) -> str:
    """ไทล์ปุ่มลัด (REDEEM / DONATE …) ใต้แบนเนอร์หน้าแรก"""
    e = html.escape
    ctx = site_links(meta, user)
    tiles = []
    for i, t in enumerate(site["tiles"]):
        hide = _hidden(t["link"], meta, editor)
        if hide is None:
            continue
        href = _href(t["link"], ctx) or " href='/'"
        src = img_url(t["img"]) if t["img"] else TILE_IMG.get(t["link"], "")
        if src:
            body = f"<a class='qtile'{href} aria-label='{e(t['label'])}'><img src='{e(src)}' alt='' width='352' height='352'></a>"
        else:
            body = (f"<a class='qtile plain'{href}><span class='im paper'><span class='stk {e(t['color'])}'>"
                    f"{px(TILE_ICON.get(t['link'], 'zap'), 36)}</span></span><b>{e(t['label'])}</b></a>")
        tiles.append(f"<div class='slot{hide}'>{body}{_sedit(f'tiles:{i}', 'แก้ปุ่มลัด') if editor else ''}</div>")
    return f"<nav class='qtiles' aria-label='ปุ่มลัด'>{''.join(tiles)}</nav>" if tiles else ""


def topbar(user, meta: dict, login: bool, active: str, editor: bool = False, cart: bool = False) -> str:
    """แถบบน: ปุ่มเมนู (มือถือ) · ปุ่มลัด · คุกกี้ · ตะกร้า · บัญชี"""
    e = html.escape
    parts = [f"<button class='round' id='sideBtn' type='button' aria-controls='side' aria-expanded='false' "
             f"aria-label='เมนู'>{px('menu', 24)}</button>"]
    parts.append(f"<a class='qbtn{' on' if active == 'shop' else ''}' href='/' data-home>{cookie(30)}<span>ร้านคุกกี้</span></a>")
    if meta.get("donate_on"):
        parts.append(f"<a class='qbtn yl{' on' if active == 'donate' else ''}' href='/donate'>"
                     f"<img class='ck' src='{web_art.COOKIE_FOIL}' width='30' height='30' alt=''><span>Donate</span></a>")
    parts.append("<span class='tsp'></span>")
    if editor:
        parts.append(f"<button class='round' id='editToggle' type='button' aria-pressed='false' title='โหมดแก้ไขหน้าเว็บ' "
                     f"aria-label='โหมดแก้ไขหน้าเว็บ'>{px('edit', 24)}</button>")
    if user:
        parts.append(f"<span class='pill' title='คุกกี้ของฉัน'>{cookie(28)}<span id='topBal'>"
                     f"{int(user.get('balance') or 0):,}</span></span>")
        if cart:
            parts.append(f"<button class='round' type='button' data-open-cart aria-label='ตะกร้า' title='ตะกร้า'>"
                         f"{px('gift' if active == 'donate' else 'cart', 24)}<span class='nb' id='cartBadge' hidden>0</span></button>")
        avatar = (f"<img class='avatar' src='{e(user['avatar'])}' alt=''>" if user.get("avatar")
                  else f"<span class='avatar' style='display:grid;place-items:center'>{cookie(28)}</span>")
        parts.append(f"<span class='who'>{avatar}<span><b>{e(user.get('name') or '')}</b>"
                     f"<small>{'EDITOR' if editor else 'MEMBER'}</small></span></span>")
        parts.append(f"<a class='round tlogout' href='/logout' title='ออกจากระบบ' aria-label='ออกจากระบบ'>{px('logout', 24)}</a>")
    elif login:
        nxt = "?next=/donate" if active == "donate" else ""
        parts.append(f"<a class='login' href='/login{nxt}'>เข้าสู่ระบบด้วย Discord</a>")
    return f"<header class='topbar'>{''.join(parts)}</header>"


def notices(meta: dict, notice: str, extra: list = None) -> str:
    e = html.escape
    out = []
    if meta.get("notice"):
        out.append(f"<p class='notice ann'>{px('notification', 24)}<span>{e(meta['notice'])}</span></p>")
    if notice:
        invite = meta.get("invite_url")
        more = (f" · <a href='{e(invite)}' target='_blank' rel='noopener'>เข้าดิส</a>"
                if invite and "ดิส" in notice else "")
        out.append(f"<p class='notice' role='status'>{px('info-box', 24)}<span>{e(notice)}{more}</span></p>")
    for text in extra or []:
        out.append(f"<p class='notice'>{px('info-box', 24)}<span>{e(text)}</span></p>")
    return "".join(out)


def promos_html(site: dict, meta: dict, user, editor: bool, page: str = "shop") -> str:
    """การ์ดสติกเกอร์ในแถบขวา · หน้า Donate ไม่โชว์การ์ดที่ลิงก์มาหน้า Donate เอง (คนแก้ร้านยังเห็นตอนโหมดแก้ไข)"""
    e = html.escape
    ctx = site_links(meta, user)
    out = []
    for i, p in enumerate(site["promos"]):
        hide = _hidden(p["link"], meta, editor)
        if page == "donate" and p["link"] in ("/donate", "donate"):
            hide = " adm-only" if editor else None
        if hide is None:
            continue
        href = _href(p["link"], ctx)
        tag = "a" if href else "div"
        src = img_url(p["img"]) if p["img"] else PROMO_IMG.get(p["link"], web_art.COOKIE_STICKER)
        out.append(f"<div class='slot{hide}'><{tag} class='promo {e(p['color'])}'{href}><span class='pat'></span>"
                   f"<img class='art' src='{e(src)}' alt=''><span class='tx'>"
                   f"<h3>{e(p['title'])}</h3>" + (f"<p>{e(p['text'])}</p>" if p["text"] else "") + "</span>"
                   + (f"<span class='btn yl go'>{e(p['btn'])}</span>" if p["btn"] else "")
                   + f"</{tag}>{_sedit(f'promos:{i}', 'แก้การ์ดโปรโมต') if editor else ''}</div>")
    return "".join(out)


def _exe(title: str) -> str:
    """ชื่อร้าน → ชื่อไฟล์บนแถบหน้าต่าง (COOKIE_SHOP.EXE)"""
    name = "_".join((title or "COOKIE SHOP").split()).upper()[:28]
    return html.escape(name) + ".EXE"


def hero_html(slides: list, meta: dict, user, editor: bool, default_title: str, default_sub: str) -> str:
    """แบนเนอร์ในหน้าต่าง · แบนเนอร์แรกที่ยังไม่ใส่รูป = รูป COOKIE MARKET ในตัว
    หัวข้อว่าง + มีรูปพื้นหลัง = ไม่มีตัวหนังสือทับรูป (หัวข้อยังอยู่ให้โปรแกรมอ่านจอ)"""
    e = html.escape
    ctx = site_links(meta, user)
    out, dots = [], []
    for i, s in enumerate(slides):
        bg_src = img_url(s.get("bg") or "") or (web_art.BANNER if i == 0 and not s.get("art") else "")
        bg = f"<img class='bgimg' src='{e(bg_src)}' alt=''>" if bg_src else "<span class='pat'></span>"
        if s.get("art"):
            pic = f"<span class='art'><img src='{e(img_url(s['art']))}' alt=''></span>"
        elif not bg_src:
            pic = f"<span class='art'><img src='{web_art.MASCOT}' alt=''></span>"
        else:
            pic = ""
        bare = bool(bg_src) and not s.get("title")
        title = s.get("title") or default_title
        sub = "" if bare else (s.get("sub") or (default_sub if i == 0 else ""))
        href = _href(s.get("link") or "", ctx)
        btn = (f"<a class='btn big go'{href}>{e(s['btn'])}{px('play', 24)}</a>" if s.get("btn") and href else "")
        cover = f"<a class='cover-link'{href} aria-label='{e(title)}' tabindex='-1'></a>" if bare and href else ""
        tag = "h1" if i == 0 else "h2"
        out.append(f"<div class='slide {e(s.get('color') or 'c0')}{' on' if i == 0 else ''}'{'' if i == 0 else ' inert'}>"
                   f"{bg}{pic}{cover}<div class='txt'><{tag}{' class=sr' if bare else ''}>{e(title)}</{tag}>"
                   + (f"<p>{e(sub)}</p>" if sub else "") + f"{btn}</div>"
                   + (_sedit(f"hero:{i}", "แก้แบนเนอร์นี้") if editor else "") + "</div>")
        dots.append(f"<button type='button' aria-label='แบนเนอร์ {i + 1}' aria-current='{'true' if i == 0 else 'false'}'></button>")
    dots_html = f"<div class='dots'>{''.join(dots)}</div>" if len(slides) > 1 else ""
    return win(_exe(default_title), f"<div class='hero'>{''.join(out)}{dots_html}</div>", "herowin",
               attrs=" aria-label='แบนเนอร์'", inner="hbox")


def edit_tools(page: str) -> str:
    """แถบเครื่องมือตอนเปิดโหมดแก้ไข (แบบแถบงาน Win95)"""
    b = []
    if page == "shop":
        b.append(f"<button type='button' data-add-item>{px('plus', 12)}เพิ่มของ</button>")
        b.append(f"<button type='button' data-slot='hero:new'>{px('image', 12)}เพิ่มแบนเนอร์</button>")
    else:
        b.append(f"<button type='button' data-add-ditem>{px('plus', 12)}เพิ่มรายการ Donate</button>")
        b.append(f"<button type='button' data-slot='donate'>{px('image', 12)}หัวหน้า Donate / เรต</button>")
    b.append(f"<button type='button' data-slot='promos:new'>{px('plus', 12)}การ์ดโปรโมต</button>")
    if page == "shop":
        b.append(f"<button type='button' data-slot='tiles:new'>{px('plus', 12)}ปุ่มลัด</button>")
    b.append(f"<button type='button' data-slot='deco'>{px('paint-bucket', 12)}ของตกแต่ง</button>")
    b.append(f"<button type='button' data-slot='theme'>{px('paint-bucket', 12)}สีธีม</button>")
    if page == "shop":
        b.append(f"<button type='button' data-page-edit>{px('info-box', 12)}ชื่อร้าน / ประกาศ</button>")
    return f"<div class='etools' role='toolbar' aria-label='เครื่องมือแก้หน้าเว็บ'><b>{px('edit', 12)}EDIT MODE</b>{''.join(b)}</div>"


SITE_DIALOG = (
    "<dialog id='siteDlg' aria-labelledby='siteTitle'><form class='dlg' id='siteForm' method='dialog'>"
    "<h3 id='siteTitle'>แก้หน้าเว็บ</h3><div class='scroll' id='siteFields'></div>"
    "<div class='idbody'><p class='err' id='siteErr' role='alert'></p></div>"
    "<div class='acts'><button class='btn danger' id='siteDel' type='button'>ลบ</button>"
    "<span id='siteMove' style='display:flex;gap:6px'><button class='btn alt sm' type='button' data-mv='up' "
    "title='ย้ายไปก่อน' aria-label='ย้ายไปก่อน'>◀</button>"
    "<button class='btn alt sm' type='button' data-mv='down' title='ย้ายไปหลัง' aria-label='ย้ายไปหลัง'>▶</button></span>"
    "<button class='btn alt' type='button' data-close>ยกเลิก</button>"
    "<button class='btn' id='siteSave' type='submit'>บันทึก</button></div></form></dialog>")


def head_html(title: str, nonce: str = "") -> str:
    return ("<!doctype html><html lang='th'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<meta name='theme-color' content='#050507'>"
            f"<title>{html.escape(title)}</title>"
            f"<link rel='icon' href='{web_art.asset('cookie-64.webp')}'>"
            "<link rel='preconnect' href='https://fonts.googleapis.com'>"
            "<link href='https://fonts.googleapis.com/css2?family=Chakra+Petch:ital,wght@0,400;0,600;0,700;1,700"
            "&family=IBM+Plex+Sans+Thai:wght@400;600&family=VT323&display=swap' rel='stylesheet'>")


def shell(*, active: str, title: str, user, meta: dict, login: bool, editor: bool, main: str, rail: str,
          cats: list, state: dict, page_js: str, nonce: str, notice_html: str = "", cart_html: str = "",
          dialogs: str = "", templates: str = "", extra_css: str = "", body_cls: str = "") -> str:
    """ทั้งหน้า: เลื่อม + ของตกแต่ง · แถบซ้าย · แถบบน · เนื้อหา + แถบขวา · ตะกร้า · dialog · script"""
    e = html.escape
    site = meta.get("site") or web_site.load("")
    deco = site["deco"]
    deco_html = "<div class='glit' aria-hidden='true'></div>"
    if deco["bg"]:
        deco_html += f"<div class='dbg' style=\"background-image:url('{e(img_url(deco['bg']))}')\"></div>"
    for key, cls in (("left", "l"), ("right", "r")):
        if deco[key]:
            deco_html += f"<img class='dcorner {cls}' src='{e(img_url(deco[key]))}' alt=''>"
    if editor:
        state = dict(state, siteEdit={"values": site, "rate": meta.get("cookie_rate", 0), "presets": web_site.PRESETS,
                                      "rev": meta.get("site_rev") or ""})
        dialogs = dialogs + SITE_DIALOG
    script_attr = f" nonce='{e(nonce)}'" if nonce else ""
    content_cls = "content" if rail else "content norail"
    return (
        head_html(title, nonce)
        + f"<style>{CSS}{extra_css}{web_site.theme_css(site['theme'])}</style></head>"
        f"<body class='{e(body_cls)}'>{deco_html}<div class='frame'>"
        f"{sidebar(site, meta, user, active, cats, editor)}"
        f"<div class='wrap'>{topbar(user, meta, login, active, editor, bool(cart_html))}{notice_html}"
        f"<div class='{content_cls}'><main class='main' id='main'>{main}</main>"
        + (f"<aside class='rail' aria-label='ข้อมูลเพิ่มเติม'>{rail}</aside>" if rail else "")
        + f"</div><footer>{e(meta.get('footer') or '')}</footer></div></div>"
        f"{cart_html}{edit_tools(active) if editor else ''}{dialogs}"
        f"<template id='ckTpl'>{cookie(20)}</template><template id='extTpl'>{px('external-link', 12)}</template>{templates}"
        f"<script type='application/json' id='state'>{json_for_html(state)}</script>"
        f"<script{script_attr}>{SHELL_JS}</script><script{script_attr}>{page_js}</script>"
        + (f"<script{script_attr}>{SITE_JS}</script>" if editor else "")
        + "</body></html>")


def cat_cover(c: dict, big: bool = False) -> str:
    """หน้าปกหมวด: รูปที่อัปเอง → สติกเกอร์ในตัว → สติกเกอร์ตัวหนังสือ (สีหมวด + ไอคอนพิกเซล)"""
    e = html.escape
    if c.get("img"):
        return f"<img class='cv-img' src='{e(c['img'])}' alt='' loading='lazy'>"
    src = sticker(c["art"])
    if src:
        return f"<img class='cv-stk' src='{e(src)}' alt='' loading='lazy'>"
    return f"<span class='stk {e(c['color'])}'>{art(c['art'], 36 if big else 24)}<span>{e(c['name'])}</span></span>"


def category_list(items: list, admin_items, site: dict, info: dict, editor: bool) -> list:
    cats: dict = {}
    for i in items:
        if i.get("category"):
            cats[i["category"]] = cats.get(i["category"], 0) + 1
    if editor and admin_items:
        for i in admin_items:
            if i.get("category") and i["category"] not in cats:
                cats[i["category"]] = 0
    out = []
    for n, c in enumerate(sorted(cats)):
        key = cat_art(c)
        custom = site["cats"].get(c) or {}
        out.append({"name": c, "art": key, "color": custom.get("color") or CAT_COLOR.get(key, "c0"), "count": cats[c],
                    "desc": info.get(c, ""), "img": img_url(custom.get("img") or ""), "tpl": n})
    return out


def sech(kicker: str, title: str, tid: str, extra: str = "", sid: str = "") -> str:
    """หัวข้อส่วน: คำเล็กพิกเซล + หัวข้อไทย"""
    sid_attr = f" id='{sid}'" if sid else ""
    return (f"<div class='sech'{sid_attr}><h2 id='{tid}'><span class='k'>&gt; {kicker}</span>{title}</h2>"
            f"<span class='sp'></span>{extra}</div>")


# ---------------------------------------------------------------- หน้าร้าน

def _card(i: dict, e, buy_default: str, editor: bool, adm_only: bool = False) -> str:
    state = i.get("state") or "open"
    pic = (f"<img src='{e(i['image_url'])}' alt='' loading='lazy'>" if i.get("image_url")
           else art(cat_art(i.get("category") or ""), 72))
    badge = f"<span class='badge {state}'>{STATE_TEXT[state]}</span>" if state in STATE_TEXT else ""
    if adm_only:
        badge += "<span class='badge hide'>ซ่อนอยู่</span>" if not i.get("active", True) else ""
    edit = (f"<button class='ebtn' type='button' data-edit='{e(i['code'])}' aria-label='แก้ {e(i['name'])}'>"
            f"{px('edit', 24)}</button>" if editor else "")
    chips = []
    if i.get("limit"):
        chips.append(f"แลกได้ {i['limit']} ครั้ง/คน")
    if i.get("stock") is not None and i["stock"] >= 0:
        chips.append(f"เหลือ {i['stock']} ชิ้น")
    if i.get("start") and state == "soon":
        chips.append(f"เริ่ม {thai_date(i['start'])}")
    if i.get("end") and state in ("open", "hot"):
        chips.append(f"ถึง {thai_date(i['end'])}")
    meta = "".join(f"<span>{e(c)}</span>" for c in chips)
    meta += (f"<span>{px('truck', 12)}ส่งเข้าเกมเอง</span>" if i.get("ckx")
             else f"<span>{px('user', 12)}แอดมินส่งให้</span>")
    cat = f"<span class='cat'>{e(i['category'])}</span>" if i.get("category") else ""
    desc = f"<p class='desc'>{e(i['description'])}</p>" if i.get("description") else ""
    off = " off" if state in ("ended", "soldout") else ""
    buy = buy_default if state not in ("ended", "soldout", "soon") and not adm_only else ""
    text = " ".join([i["name"], i.get("description") or "", i.get("category") or "", i["code"]]).lower()
    data = {"code": i["code"], "cat": i.get("category") or "", "name": i["name"], "text": text, "price": i["price"],
            "state": state, "ckx": "1" if i.get("ckx") else "0", "limit": i.get("limit") or 0,
            "stock": "" if i.get("stock") is None else i["stock"], "end": i.get("end_ts") or 0,
            "upd": i.get("updated_ts") or 0}
    attrs = " ".join(f"data-{k}='{e(str(v))}'" for k, v in data.items())
    cls = "item" + off + (" adm-only" if adm_only else "")
    return (f"<article class='{cls}' {attrs}>"
            f"<div class='pic'>{pic}{badge}{edit}</div>"
            f"<div class='body'>{cat}<h2>{e(i['name'])}</h2>{desc}<div class='meta'>{meta}</div></div>"
            f"<div class='price'><b>{i['price']:,}{cookie(26)}</b><div class='buy'>{buy}</div></div></article>")


def render_page(items: list, meta: dict, user: dict = None, csrf: str = "", login: bool = False,
                notice: str = "", nonce: str = "", admin_items: list = None) -> str:
    """items: ของที่โชว์ (dict จาก web_item ใน bot.py) · user: ผลจาก backend.me() (None = ยังไม่ล็อกอิน)
    admin_items: ของทุกชิ้นพร้อมค่าดิบ — ส่งมาเฉพาะคนแก้ร้าน"""
    e = html.escape
    editor = bool(user and user.get("editor") and admin_items is not None)
    site = meta.get("site") or web_site.load("")
    meta = dict(meta, site=site)
    title = meta.get("title") or "Cookie Shop"
    info = meta.get("cat_info") or {}
    cats = category_list(items, admin_items, site, info, editor)

    # ---- แบนเนอร์
    if user and user.get("can_redeem"):
        sub = meta.get("subtitle_user") or ""
    elif login:
        sub = meta.get("subtitle_login") or ""
    else:
        sub = meta.get("subtitle") or ""
    hero = hero_html(site["hero"], meta, user, editor, title, sub)

    # ---- การ์ดหมวด (หน้าต่าง + กระดาษจุด + สติกเกอร์)
    ccards = []
    for c in cats:
        ccards.append(f"<div class='slot{' adm-only' if not c['count'] else ''}'><a class='ccard win' "
                      f"href='/?c={e(quote(c['name']))}' data-go='{e(c['name'])}'><span class='wt'><span class='tt'>"
                      f"{e(c['name'])}</span>{WB}</span><span class='paper'>{cat_cover(c)}"
                      f"<span class='cnt'>{c['count']} ITEM{'' if c['count'] == 1 else 'S'}</span></span></a>"
                      + (_sedit(f"cats:{c['name']}", f"แก้หมวด {c['name']}") if editor else "") + "</div>")
    arrows = ("<button class='arrow' type='button' data-scroll='ccards' data-dir='-1' aria-label='เลื่อนซ้าย'>"
              f"{px('chevron-left', 24)}</button><button class='arrow' type='button' data-scroll='ccards' data-dir='1' "
              f"aria-label='เลื่อนขวา'>{px('chevron-right', 24)}</button>") if len(cats) > 4 else ""
    cat_sec = (f"<section class='homeonly' aria-labelledby='catT'>"
               + sech("CATEGORIES", "หมวดหมู่", "catT", f"{arrows}<a class='chipbtn' href='#all'>ดูทั้งหมด</a>")
               + f"<div class='ccards' id='ccards'>{''.join(ccards)}</div></section>" if ccards else "")

    # ---- มาใหม่ (อัปเดตล่าสุด 3 ชิ้นที่แลกได้)
    live = [i for i in items if (i.get("state") or "open") in ("open", "hot")]
    newest = sorted(live, key=lambda i: i.get("updated_ts") or 0, reverse=True)[:3]
    feat = []
    for i in newest:
        pic = (f"<img src='{e(i['image_url'])}' alt='' loading='lazy'>" if i.get("image_url")
               else art(cat_art(i.get("category") or ""), 36))
        feat.append(f"<button class='fcard' type='button' data-open='{e(i['code'])}'><span class='im paper'>{pic}</span>"
                    f"<span class='bd'><span class='k'>NEW!</span><b>{e(i['name'])}</b>"
                    f"<small>{e(i.get('description') or i.get('category') or '')}</small>"
                    f"<span class='pr'>{i['price']:,}{cookie(22)}</span></span></button>")
    feat_sec = (f"<section class='homeonly' aria-labelledby='newT'>" + sech("NEW ARRIVALS", "มาใหม่", "newT")
                + f"<div class='feat'>{''.join(feat)}</div></section>" if len(newest) >= 2 else "")

    # ---- ของทั้งหมด
    buy_default = "<a class='btn bl sm' href='/login'>ล็อกอินเพื่อแลก</a>" if (not user and login) else ""
    cards = [_card(i, e, buy_default, editor) for i in items]
    if editor:
        public = {i["code"] for i in items}
        cards += [_card(i, e, "", True, adm_only=True) for i in admin_items if i["code"] not in public]
    empty = ("<p class='empty' id='noMatch' hidden>ไม่เจอของที่ตรงกับตัวกรอง · "
             "<button class='linkbtn' type='button' data-clear>ล้างตัวกรอง</button></p>")
    if not items:
        cls = "empty pub-only" if editor else "empty"
        cards.append(f"<p class='{cls}'><img src='{web_art.MASCOT}' width='120' height='120' alt=''><br>"
                     "ยังไม่มีของในร้าน รอแอดมินเติมของก่อนนะ</p>")
    afford = (f"<button class='tog' type='button' data-tog='afford' aria-pressed='false'>{cookie(20)}แลกได้ตอนนี้</button>"
              if user else "")
    filters = (
        "<div class='card filters' id='filters'>"
        "<div class='frow'><span class='flab'>PRICE</span><div class='range'>"
        "<input id='pmin' type='number' inputmode='numeric' min='0' placeholder='ต่ำสุด' aria-label='ราคาต่ำสุด'>"
        "<span>–</span><input id='pmax' type='number' inputmode='numeric' min='0' placeholder='สูงสุด' "
        "aria-label='ราคาสูงสุด'></div>"
        f"{afford}<button class='tog' type='button' data-tog='lim' aria-pressed='false'>จำกัดต่อคน</button>"
        "<button class='tog' type='button' data-tog='stk' aria-pressed='false'>มีสต็อกจำกัด</button></div>"
        "<div class='frow'><span class='flab'>SHIP</span>"
        f"<button class='tog' type='button' data-ship='game' aria-pressed='false'>{px('truck', 24)}ส่งเข้าเกมเอง</button>"
        f"<button class='tog' type='button' data-ship='manual' aria-pressed='false'>{px('user', 24)}แอดมินส่งให้</button></div>"
        "<div class='frow'><span class='flab'>STATUS</span><div class='seg' role='group' aria-label='สถานะ'>"
        "<button type='button' data-st='' aria-pressed='true'>ทั้งหมด</button>"
        "<button type='button' data-st='open' aria-pressed='false'>เปิดอยู่</button>"
        "<button type='button' data-st='hot' aria-pressed='false'>ใกล้หมดเวลา</button>"
        "<button type='button' data-st='soon' aria-pressed='false'>เร็วๆ นี้</button>"
        "<button type='button' data-st='soldout' aria-pressed='false'>หมดแล้ว</button></div></div>"
        "<div class='frow'><span class='flab'>SORT</span><select class='sel' id='sort' aria-label='เรียงตาม'>"
        "<option value='rec'>แนะนำ</option><option value='asc'>ราคาน้อยไปมาก</option>"
        "<option value='desc'>ราคามากไปน้อย</option><option value='name'>ชื่อ ก–ฮ</option>"
        "<option value='new'>อัปเดตล่าสุด</option><option value='end'>ใกล้หมดเวลา</option></select>"
        "<button class='linkbtn' type='button' data-clear>ล้างตัวกรองทั้งหมด</button></div></div>")
    tools = (f"<div class='tools'><label class='search'>{px('search', 24)}<input id='q' type='search' autocomplete='off' "
             "placeholder='ค้นหาชื่อ คำอธิบาย หมวด หรือรหัสของ…' aria-label='ค้นหาของ'><kbd>/</kbd></label>"
             f"<button class='round' id='filterBtn' type='button' aria-controls='filters' aria-expanded='false' "
             f"title='ตัวกรอง' aria-label='ตัวกรอง'>{px('sliders', 24)}</button>"
             f"<button class='round' id='viewBtn' type='button' aria-pressed='false' title='มุมมองรายการ' "
             f"aria-label='สลับมุมมอง'>{px('view-list', 24)}</button></div>")
    afford_t = (f"<button class='type' type='button' data-type='afford' aria-pressed='false'>{cookie(22)}แลกได้ตอนนี้</button>"
                if user else "")
    cathead = (
        "<section class='win cathead catonly' aria-live='polite'><div class='wt'><span class='tt' id='ciBar'></span>"
        f"{WB}</div><div class='wc'><div class='slot'><div class='cover paper' id='ciCover'></div>"
        + (f"<button class='sedit' type='button' id='ciEdit' data-slot='' title='แก้หมวด' aria-label='แก้หมวด'>{px('edit', 24)}</button>"
           if editor else "")
        + f"</div><div><button class='back' type='button' id='backHome'>{px('chevron-left', 24)}BACK</button>"
        "<h1 id='ciName'></h1><p class='ct' id='ciCount'></p><div class='cdesc' id='ciDesc'></div></div></div></section>"
        "<section class='typebox catonly'><h3 class='pick'>เลือกประเภท</h3><div class='types' role='group' aria-label='ประเภท'>"
        "<button class='type' type='button' data-type='' aria-pressed='true'>ทั้งหมดในหมวดนี้</button>"
        f"{afford_t}<button class='type' type='button' data-type='game' aria-pressed='false'>{px('truck', 24)}"
        "ส่งเข้าเกมเอง</button>"
        f"<button class='type' type='button' data-type='manual' aria-pressed='false'>{px('user', 24)}แอดมินส่งให้</button>"
        f"<button class='type' type='button' data-type='hot' aria-pressed='false'>{px('clock', 24)}ใกล้หมดเวลา</button></div></section>")
    all_title = "<span class='homeonly'>ของทั้งหมด</span><span class='catonly'>เลือกสินค้าที่ต้องการ</span>"
    main = (f"<div class='homeonly'>{hero}{tiles_html(site, meta, user, editor)}</div>{cathead}{cat_sec}{feat_sec}"
            f"<section aria-labelledby='allT'>" + sech("ALL ITEMS", all_title, "allT", sid="all")
            + f"{tools}{filters}<div class='resbar'><span id='count'></span><div class='active' id='activeChips'></div></div>"
            f"<div class='grid' id='grid'>{''.join(cards)}</div>{empty}</section>")

    # ---- แถบขวา
    rail = []
    if user:
        st = user.get("stats") or {}
        spin = user.get("spin_today")
        spin_html = (f"<div class='spin'>{px('dice', 24)}<span>วันนี้หมุนได้</span><b>+{int(spin):,}</b></div>"
                     if spin is not None
                     else (f"<div class='spin'>{px('dice', 24)}<span>วันนี้ยังไม่ได้หมุนวงล้อ</span>"
                           f"<a class='btn yl sm' href='{e(user['spin_url'])}' target='_blank' rel='noopener'>ไปหมุน</a></div>"
                           if user.get("spin_url") else ""))
        today = datetime.now(timezone(timedelta(hours=7)))
        rail.append(
            "<section class='bal' aria-label='คุกกี้ของฉัน'>"
            f"<div class='lab'><span class='k'>&gt; MY COOKIES</span><b>{today.day} {THAI_MONTHS[today.month - 1]} {today.year + 543}</b></div>"
            f"<div class='big'>{cookie(56)}<span id='bal'>{int(user.get('balance') or 0):,}</span></div>"
            "<div class='stats'>"
            f"<div><span>แลกแล้ว</span><b id='stCount'>{int(st.get('count') or 0):,}</b></div>"
            f"<div><span>ใช้ไป</span><b id='stSpent'>{int(st.get('spent') or 0):,}</b></div>"
            f"<div><span>รอรับ</span><b id='stPending'>{int(st.get('pending') or 0):,}</b></div></div>{spin_html}</section>")
    elif login:
        rail.append(win("WELCOME.EXE", f"<img class='mascot' src='{web_art.MASCOT}' width='130' height='130' alt=''>"
                        "<p>ล็อกอินด้วย Discord เพื่อดูคุกกี้ของคุณ ใส่ตะกร้า แล้วแลกของเข้าเกมได้เลย</p>"
                        "<a class='login' href='/login'>เข้าสู่ระบบด้วย Discord</a>", "guest"))
    else:
        cta = f"<a class='btn' href='{e(meta['redeem_url'])}'>ไปแลกใน Discord</a>" if meta.get("redeem_url") else ""
        rail.append(win("WELCOME.EXE", f"<img class='mascot' src='{web_art.MASCOT}' width='130' height='130' alt=''>"
                        f"<p>ดูของในร้านได้ที่นี่ กดแลกได้ในห้องร้านบน Discord</p>{cta}", "guest"))
    rail.append(promos_html(site, meta, user, editor))
    if user:
        rail.append(win("HISTORY.LOG", "<ul id='histList'></ul><p class='none' id='histNone'>ยังไม่เคยแลกของ</p>",
                        "hist", attrs=" id='hist' aria-label='ของที่แลกล่าสุด'"))

    # ---- ตะกร้า
    cart = ""
    if user:
        cart = (
            "<aside class='cart' id='cart' aria-label='ตะกร้า' inert>"
            f"<div class='cart-head'>{px('cart', 24)}<h2>CART</h2><span class='pill' id='cartCount' hidden></span>"
            "<button class='x close' id='cartClose' type='button' aria-label='ปิดตะกร้า'>×</button></div>"
            "<div class='cart-scroll'><div id='cartBody'><div id='lines'></div>"
            f"<p class='cart-empty' id='cartEmpty'><img src='{web_art.COOKIE_STICKER}' width='110' height='113' alt=''>"
            "ยังไม่มีของในตะกร้า<br>กดที่ของที่อยากได้ แล้วกด <b>ใส่ตะกร้า</b></p>"
            "<div id='ingWrap' hidden><label class='ing-l' for='ing'>ชื่อในเกมที่จะรับของ"
            "<small>ชื่อที่ใช้ล็อกอินเข้าเซิฟ (ไม่ใช่ชื่อตัวละคร)</small></label>"
            "<input class='ing' id='ing' maxlength='40' autocomplete='off' spellcheck='false'></div>"
            "<p class='err' id='err' role='alert'></p></div><div id='done'></div></div>"
            "<div class='sum' id='sum'><div class='t'><span>รวม</span><b id='sumTotal'>0</b></div>"
            "<div><span>คุกกี้เหลือหลังแลก</span><span id='sumLeft'></span></div></div>"
            "<div class='acts'><button class='btn alt' id='more' type='button' hidden>แลกต่อ</button>"
            "<button class='btn big' id='go' type='button'>ยืนยันแลก</button></div></aside>"
            "<div class='bar' id='bar'><span><span id='barCount'></span> ในตะกร้า <b id='barTotal'></b></span>"
            "<button class='btn' type='button' data-open-cart>ดูตะกร้า</button></div>"
            "<div class='scrim' id='scrim' hidden></div>")

    # ---- dialog
    dialogs = (
        "<dialog id='itemDlg' aria-labelledby='idName'><div class='dlg idlg'>"
        "<div class='wt'><span class='tt'>ITEM_INFO.EXE</span><span class='wb'><button class='wx' type='button' data-close "
        "aria-label='ปิด'>×</button></span></div>"
        "<div class='idtop'><div class='idpic' id='idPic'></div><div class='idinfo'><span class='cat' id='idCat'></span>"
        "<h3 id='idName'></h3><div class='meta' id='idMeta'></div><b class='idprice' id='idPrice'></b></div></div>"
        "<div class='idbody'><p id='idDesc'></p><p class='err' id='idErr' role='alert'></p></div>"
        "<div class='acts' id='idAct'></div></div></dialog>")
    state = {"items": {i["code"]: {"name": i["name"], "price": i["price"], "ckx": bool(i.get("ckx"))}
                       for i in items if (i.get("state") or "open") in ("open", "hot")},
             "user": user, "csrf": csrf, "cats": cats, "login": bool(login)}
    if editor:
        state["admin"] = {"items": {i["code"]: i["raw"] for i in admin_items}}
        state["page"] = {"title": meta.get("title") if meta.get("title") != "Cookie Shop" else "",
                         "subtitle": meta.get("subtitle_raw") or "", "notice": meta.get("notice") or ""}
        cat_opts = "".join(f"<option value='{e(c['name'])}'>" for c in cats)
        dialogs += (
            "<dialog id='editDlg' aria-labelledby='editTitle'><form class='dlg' id='editForm' method='dialog'>"
            "<h3 id='editTitle'>แก้ของ</h3><div class='scroll'><input type='hidden' name='original'><input type='hidden' name='stock_loaded'>"
            "<label class='fld'>รหัสของ<input name='code' required maxlength='20' pattern='[A-Za-z0-9_\\-]{1,20}'>"
            "<small>อังกฤษ/ตัวเลข/_ - (ใช้ใน log)</small></label>"
            "<label class='fld'>ราคา (คุกกี้)<input name='price' type='number' min='1' max='100000000' required></label>"
            "<label class='fld w'>ชื่อที่ผู้เล่นเห็น<input name='name' required maxlength='80'></label>"
            "<label class='fld w'>รหัส Cookie Express<textarea name='ckx' rows='2' "
            "placeholder='CX-79MN-V4KT*2 CV-AMMF-Z6LF'></textarea><small>หลายชิ้นเว้นวรรค · ว่าง = แอดมินส่งเอง</small></label>"
            "<label class='fld w'>คำอธิบาย<textarea name='description' maxlength='500'></textarea></label>"
            "<label class='fld'>หมวด<input name='category' maxlength='40' list='catList'></label>"
            f"<datalist id='catList'>{cat_opts}</datalist>"
            "<label class='fld'>ลำดับ (น้อยขึ้นก่อน)<input name='sort' type='number'></label>"
            "<label class='fld'>จำกัดต่อคน<input name='limit' type='number' min='0' max='999' required>"
            "<small>0 = ไม่จำกัด</small></label>"
            "<label class='fld'>สต็อกทั้งหมด<input name='stock' type='number' min='-1' max='1000000' required>"
            "<small>-1 = ไม่จำกัด</small></label>"
            "<label class='fld'>เริ่มแลกได้ (เวลาไทย)<input name='start' type='datetime-local'></label>"
            "<label class='fld'>แลกได้ถึง<input name='end' type='datetime-local'></label>"
            "<div class='fld w'>รูป<div class='imgrow'><img id='imgPrev' alt='' hidden>"
            "<input name='image' type='file' accept='image/png,image/jpeg,image/webp,image/gif'></div>"
            "<label class='fld chk' id='remWrap'><input type='checkbox' name='remove_image'>ลบรูปเดิม</label></div>"
            "<label class='fld chk w'><input type='checkbox' name='active'>โชว์ในร้าน (ไม่ติ๊ก = ซ่อน)</label>"
            "<p class='err w' id='editErr' role='alert'></p></div>"
            "<div class='acts'><button class='btn danger' id='delBtn' type='button'>ลบของนี้</button>"
            "<button class='btn alt' type='button' data-close>ยกเลิก</button>"
            "<button class='btn' id='saveBtn' type='submit'>บันทึก</button></div></form></dialog>"
            "<dialog id='pageDlg' aria-labelledby='pageTitle'><form class='dlg' id='pageForm' method='dialog'>"
            "<h3 id='pageTitle'>ชื่อร้าน / ประกาศ</h3><div class='scroll'>"
            "<label class='fld w'>ชื่อร้าน (ชื่อแท็บ + หัวข้อแบนเนอร์ที่มีตัวหนังสือ)<input name='title' maxlength='60' placeholder='Cookie Shop'></label>"
            "<label class='fld w'>คำโปรย (แบนเนอร์แรกที่มีตัวหนังสือ)<textarea name='subtitle' maxlength='200' "
            "placeholder='(ว่าง = ข้อความเริ่มต้น)'></textarea></label>"
            "<label class='fld w'>ประกาศ (แถบบนสุด)<textarea name='notice' maxlength='300' "
            "placeholder='เช่น ของพิเศษก่อนอีเวนต์เสาร์นี้ 18:00 · ว่าง = ไม่โชว์'></textarea></label>"
            "<p class='err w' id='pageErr' role='alert'></p></div>"
            "<div class='acts'><button class='btn alt' type='button' data-close>ยกเลิก</button>"
            "<button class='btn' type='submit'>บันทึก</button></div></form></dialog>")
    extra = [user.get("reason") or "ตอนนี้ยังแลกของไม่ได้"] if user and not user.get("can_redeem") else []
    templates = "".join(f"<template id='cv-{c['tpl']}'>{cat_cover(c, True)}</template>" for c in cats)
    return shell(active="shop", title=title, user=user, meta=meta, login=login, editor=editor, main=main,
                 rail="".join(rail), cats=cats, state=state, page_js=JS, nonce=nonce,
                 notice_html=notices(meta, notice, extra), cart_html=cart, dialogs=dialogs, templates=templates)
