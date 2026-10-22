"""หน้า Donate บนเว็บ — เลือกแพ็ก/ของ → จ่ายเงินบนเว็บได้เลย (Stripe: PromptPay QR / บัตร)

บอทโพสต์สรุปรายการ + สถานะ (รอจ่าย → จ่ายแล้ว → ส่งของ) ในห้อง Donate ส่วนตัวบน Discord ให้เอง
คนแก้ร้านเพิ่ม/แก้/ลบรายการ Donate + รูป + เรตเติมคุกกี้ได้บนหน้านี้เลย (โหมดแก้ไข)
ไฟล์นี้สร้างแค่ HTML/CSS/JS — ข้อมูลทั้งหมดมาจาก backend ใน bot.py (donate_catalog / donate_orders)
"""
import html

import web_art
import web_site
from web_art import art, cookie, px
from web_ui import category_list, img_url, notices, promos_html, shell, win

# ประเภท → (รูป, สีพื้น, ชื่อ)
KIND = {"pack": ("jar", "c2", "แพ็กคุกกี้"), "game": ("parcel", "c0", "ของส่งเข้าเกม"),
        "manual": ("admin", "c3", "แอดมินส่งให้")}


def baht(satang) -> str:
    satang = int(satang or 0)
    return f"฿{satang // 100:,}" if satang % 100 == 0 else f"฿{satang / 100:,.2f}"


DCSS = """
.dmain{display:grid;gap:20px;min-width:0}
.dpanel .wc{padding:18px 20px}
.dhero{position:relative;display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:center;gap:18px;min-height:220px;padding:26px 30px;
overflow:hidden;color:#fff}
.dhero .bgimg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.dhero .pat{position:absolute;inset:0;opacity:.18;background-image:radial-gradient(#000 2px,transparent 2.4px);background-size:22px 22px}
.dhero .tx{position:relative;z-index:1;min-width:0}
.dhero h1{margin:0;font:italic 700 clamp(36px,4.4vw,64px)/1 var(--f-ui);text-transform:uppercase;text-shadow:4px 4px 0 #000,-1px -1px 0 #000}
.dhero p{margin:10px 0 0;max-width:52ch;font-size:15.5px;font-weight:600;text-shadow:0 2px 0 rgba(0,0,0,.5)}
.dhero ol{margin:16px 0 0;padding:0;list-style:none;display:flex;flex-wrap:wrap;gap:8px;counter-reset:h}
.dhero ol li{counter-increment:h;display:flex;align-items:center;gap:8px;padding:4px 12px 4px 4px;background:#000;border:2px solid #fff;
font-size:13.5px;font-weight:600}
.dhero ol li::before{content:counter(h);width:24px;height:24px;display:grid;place-items:center;background:var(--gold);color:#000;
font:22px/1 var(--f-px)}
.dhero .art{position:relative;z-index:1;width:290px;transform:rotate(-8deg);filter:drop-shadow(6px 7px 0 rgba(0,0,0,.45))}
.dhero .art img{width:100%;height:auto;display:block}
.dhwin .hbox{padding:0}
.dhwin .sedit{top:44px;right:12px}
.dgrid{grid-template-columns:repeat(auto-fill,minmax(172px,1fr));gap:14px}
.dtile{text-align:center;cursor:pointer}
.dtile:focus-visible{outline:3px solid var(--gold);outline-offset:2px}
.dtile .pic{aspect-ratio:1/1}
.dtile .cover{width:100%;height:100%;display:grid;place-items:center;color:#7E6F8C}
.dtile .cover img{width:100%;height:100%;object-fit:contain;padding:10%}
.dtile .cover img.ck-foil{padding:16%}
.dtile .body{padding:8px 10px 0;align-items:center;gap:4px}
.dtile h2{font:700 16px/1.3 var(--f-ui)}
.dtile .desc{display:none}
.dtile .meta{justify-content:center;margin-top:0;padding-top:2px}
.dtile .price,.grid .dtile .price{justify-content:center;align-items:center;flex-direction:row;padding:4px 10px 12px;min-height:0}
.dtile .price b{font-size:32px}
.idpic .cover{width:100%;height:100%;display:grid;place-items:center;color:#7E6F8C}
.idpic .cover img{width:100%;height:100%;object-fit:contain;padding:10%}
.idpic .cover svg{width:96px;height:96px}
.meta .gain{color:#000;background:var(--gold);border-color:#000;font-weight:600}
.dorders .none{color:var(--dim);margin:0}
.dlist{list-style:none;margin:0;padding:0;display:grid;gap:14px;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));align-items:start}
.dord{display:flex;flex-direction:column;background:var(--card);border:2px solid var(--line2);padding:14px 16px;box-shadow:4px 4px 0 rgba(0,0,0,.5)}
.dord.st-pending,.dord.st-review,.dord.st-expired{border-color:var(--teal)}
.dord.st-cancelled{opacity:.65}
.dord .da{margin-top:auto;padding-top:10px}
.dh{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.dh b{font:26px/1 var(--f-px);font-weight:400;color:var(--teal2)}
.tag{font:17px/22px var(--f-px);padding:0 8px;border:2px solid #000;white-space:nowrap}
.tag.wait{background:var(--gold);color:#000}.tag.ok{background:#45E856;color:#000}
.tag.go{background:var(--teal);color:var(--on-teal)}.tag.off{background:var(--line2);color:var(--ink)}
.amt{margin-left:auto;font:26px var(--f-px)}
.steps{display:flex;list-style:none;margin:14px 0 4px;padding:0;counter-reset:s}
.steps li{flex:1;position:relative;text-align:center;font-size:12.5px;color:var(--dim);padding-top:30px;min-width:0}
.steps li::before{content:counter(s);counter-increment:s;position:absolute;top:0;left:50%;margin-left:-13px;width:26px;height:26px;
background:var(--card2);border:2px solid var(--line2);font:22px/22px var(--f-px);color:var(--muted);z-index:1;box-sizing:border-box}
.steps li::after{content:"";position:absolute;top:11px;right:50%;width:100%;height:4px;background:var(--line);z-index:0}
.steps li:first-child::after{display:none}
.steps li.done,.steps li.cur{color:var(--ink)}
.steps li.done::before{content:"✓";background:#45E856;border-color:#000;color:#000;font-family:var(--f-ui);font-size:15px}
.steps li.cur::before{background:var(--gold);border-color:#000;color:#000}
.steps li.done::after,.steps li.cur::after{background:#45E856}
.st-expired .steps li.cur::before{background:var(--line2);color:var(--ink)}
.dl{font-size:13.5px;color:var(--muted);margin:6px 0 0}
.when{font:16px var(--f-px);color:var(--dim)}
.exp{font-size:12.5px;color:var(--gold);margin:4px 0 0}
.prog{list-style:none;padding:0;margin:8px 0 0}
.prog li{display:flex;gap:8px;align-items:flex-start;font-size:13.5px;padding:3px 0}
.prog .dot{margin-top:5px;flex-shrink:0}
.da{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.btn.ghost{color:var(--muted);background:transparent;box-shadow:inset 0 0 0 2px var(--line2)}
.btn.ghost:hover{color:var(--bad);box-shadow:inset 0 0 0 2px var(--bad)}
.btn.ghost.arm{color:#2a0505;background:linear-gradient(180deg,#FFA4A4,#F04343 60%,#E22B2B);box-shadow:none}
.da .linkbtn{color:var(--muted);text-decoration:none;display:inline-flex;align-items:center;gap:4px;margin-left:auto}
.da .linkbtn:hover{color:var(--ink)}
.oerr{color:var(--bad);font-size:13.5px;margin:8px 0 0}
.oname{display:grid;gap:4px;margin-top:10px;font-size:13.5px;color:var(--muted)}
.oname .ing{height:38px;margin:0}
.dnote{margin:0;padding:12px 16px;border:2px solid #000;background:#45E856;color:#05220a;font-weight:600;display:flex;align-items:center;gap:12px;
box-shadow:4px 4px 0 rgba(0,0,0,.5)}
.dnote.wait{background:var(--card);color:var(--ink);border-color:var(--line2);border-left:8px solid var(--gold);font-weight:400}
.dnote.bad{background:var(--card);color:var(--ink);border-color:var(--line2);border-left:8px solid var(--bad);font-weight:400}
.minnote{font-size:13px;color:var(--muted)}
.minnote.neg{color:var(--bad)}
.paynote{display:flex;align-items:center;justify-content:center;gap:8px;width:100%;font-size:12.5px;color:var(--muted);margin-top:-2px}
.paynote svg.px{color:var(--gold)}
.pend{margin:10px 0 0;padding:10px 12px;background:var(--card);border:2px solid var(--line2);font-size:13.5px}
.fixbox{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}
.tbox{display:grid;gap:8px;padding:0 20px 6px}
.tbox .row{display:flex;align-items:center;gap:10px}
.tbox input{flex:1;min-width:0;height:50px;padding:0 14px;border:2px solid var(--line2);background:#0D0D12;font:32px var(--f-px)}
.tbox input:focus{outline:0;border-color:var(--teal)}
.tbox .get{display:flex;align-items:center;gap:6px;font:28px var(--f-px);color:var(--gold)}
.tbox small{color:var(--dim)}
.quick{display:flex;flex-wrap:wrap;gap:6px}
.quick button{border:0;border-radius:999px;padding:2px 14px;cursor:pointer;font:22px var(--f-px);color:#111;
background:linear-gradient(180deg,#FAFAFC,#BFBFC9);box-shadow:inset 0 2px 0 rgba(255,255,255,.6)}
.quick button:hover{filter:brightness(1.08)}
.off-card .wc{padding:28px 22px;text-align:center}
.off-card img{display:block;margin:0 auto 8px}
.off-card h2{margin:0;font:700 24px var(--f-ui)}
.off-card p{color:var(--muted)}
.how{margin:0;padding-left:24px;display:grid;gap:6px;font-size:14px}
.how li::marker{font:20px var(--f-px);color:var(--teal)}
.rinfo .info{margin:12px 0 0;padding:8px 11px;border:2px solid #000;background:var(--teal);color:var(--on-teal);font-weight:600;font-size:13.5px}
.rinfo small{display:block;margin-top:8px;color:var(--dim);font:17px/1.2 var(--f-px)}
.guest .heart{color:var(--teal)}
@media (max-width:900px){.dlist{grid-template-columns:1fr}.dhero{grid-template-columns:1fr;padding:22px;min-height:180px}
.dhero .art{position:absolute;right:-30px;bottom:-14px;width:200px;opacity:.55}}
@media (max-width:620px){.dgrid{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.dtile h2{font-size:14.5px}
.dtile .price b{font-size:27px}.dpanel .wc{padding:14px 12px}}
"""

DJS = r"""
(()=>{
const S=JSON.parse(document.getElementById('state').textContent);
const $=(s,el=document)=>el.querySelector(s);const $$=(s,el=document)=>[...el.querySelectorAll(s)];
const fmt=n=>Number(n).toLocaleString('th-TH');
const baht=s=>{s=Math.round(+s||0);return '฿'+(s%100?(s/100).toLocaleString('th-TH',{minimumFractionDigits:2,maximumFractionDigits:2}):fmt(s/100));};
const CKT=document.getElementById('ckTpl');const ck=()=>CKT.content.firstElementChild.cloneNode(true);
const store={get(k,d){try{const v=localStorage.getItem(k);return v===null?d:JSON.parse(v);}catch(e){return d;}},
 set(k,v){try{if(v===null)localStorage.removeItem(k);else localStorage.setItem(k,JSON.stringify(v));}catch(e){}}};
const el=(tag,props={},kids=[])=>{const e=document.createElement(tag);for(const[k,v]of Object.entries(props)){
 if(k==='text')e.textContent=v;else if(k==='on')for(const[ev,f]of Object.entries(v))e.addEventListener(ev,f);
 else if(v!==false&&v!=null)e.setAttribute(k,v===true?'':v);}for(const c of kids)if(c)e.append(c);return e;};
const safeUrl=u=>typeof u==='string'&&/^https:\/\//.test(u);
const C=S.catalog;let ITEMS=Object.fromEntries(C.items.map(i=>[i.code,i]));const U=S.user;
const TH_M=['ม.ค.','ก.พ.','มี.ค.','เม.ย.','พ.ค.','มิ.ย.','ก.ค.','ส.ค.','ก.ย.','ต.ค.','พ.ย.','ธ.ค.'];
const when=ts=>{if(!ts)return'';const d=new Date(ts*1000);return `${d.getDate()} ${TH_M[d.getMonth()]} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;};
const left=ts=>{const m=Math.round((ts*1000-Date.now())/60000);return m>=60?`${Math.floor(m/60)} ชม. ${m%60} นาที`:`${Math.max(1,m)} นาที`;};
const editing=()=>document.body.classList.contains('editing');
// ------------------------------------------------------------------ ประเภท
const grid=$('#dgrid');const tiles=grid?$$('.dtile',grid):[];let dtype='';
const TYPES=new Set($$('[data-dtype]').map(b=>b.dataset.dtype));
(()=>{const t=new URLSearchParams(location.search).get('t');if(t&&TYPES.has(t))dtype=t;})();
function applyType(){let n=0;tiles.forEach(t=>{const show=(!dtype||t.dataset.kind===dtype)&&(!t.classList.contains('adm-only')||editing());
  t.hidden=!show;if(show)n++;});
 $$('[data-dtype]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.dtype===dtype));const em=$('#dempty');if(em)em.hidden=!!n||!tiles.length;}
$$('[data-dtype]').forEach(b=>b.addEventListener('click',()=>{dtype=b.dataset.dtype;applyType();}));
document.addEventListener('cc-edit',applyType);
applyType();
// ------------------------------------------------------------------ รายละเอียด (กดที่การ์ด)
const idlg=$('#itemDlg');let actions=null;
function openItem(code){const card=grid.querySelector(`.dtile[data-code="${CSS.escape(code)}"]`);if(!card)return;
 const pic=$('#idPic');pic.replaceChildren();const cv=$('.cover',card);if(cv)pic.append(cv.cloneNode(true));
 $('#idCat').textContent=card.dataset.label||'';$('#idName').textContent=card.dataset.name||'';
 const m=$('#idMeta');m.replaceChildren();const mm=$('.meta',card);if(mm)[...mm.children].forEach(x=>m.append(x.cloneNode(true)));
 $('#idPrice').textContent=code==='TOPUP'?'ตามยอดที่ใส่':(ITEMS[code]?baht(ITEMS[code].price):'');
 const ds=$('.desc',card);$('#idDesc').textContent=ds?ds.textContent:'';$('#idErr').textContent='';
 const act=$('#idAct');act.replaceChildren();$('#tBox').hidden=code!=='TOPUP'||!U;
 if(actions)actions(code,act);
 else if(S.login)act.append(el('a',{class:'btn big',href:'/login?next=/donate',text:'ล็อกอินเพื่อ Donate'}));
 else act.append(el('span',{class:'minnote',text:'Donate ได้ที่ห้อง Donate บน Discord'}));
 if(!idlg.open)idlg.showModal();const f=code==='TOPUP'?$('#tAmt'):$('#idAct .btn.big');if(f&&!$('#tBox').hidden||f&&code!=='TOPUP')f.focus();}
if(grid){grid.addEventListener('click',e=>{if(e.target.closest('.ebtn'))return;const t=e.target.closest('.dtile[data-code]');if(t)openItem(t.dataset.code);});
 grid.addEventListener('keydown',e=>{if(e.key!=='Enter'&&e.key!==' ')return;if(e.target.closest('.ebtn'))return;const t=e.target.closest('.dtile[data-code]');
  if(t){e.preventDefault();openItem(t.dataset.code);}});}
$$('[data-close]').forEach(b=>b.addEventListener('click',()=>b.closest('dialog').close()));
const tAmt=$('#tAmt');
function tGet(){const v=tAmt?Math.floor(+tAmt.value):0;return v>0?v:0;}
function tSync(){const g=$('#tGet');if(!g)return;const b=tGet();g.replaceChildren('ได้ ',fmt(Math.floor(b*C.rate)),ck());}
if(tAmt){tAmt.addEventListener('input',tSync);$$('#tQuick [data-amt]').forEach(b=>b.addEventListener('click',()=>{tAmt.value=b.dataset.amt;tSync();}));}
// ------------------------------------------------------------------ แก้รายการ Donate (คนแก้ร้านเท่านั้น)
if(S.dadmin){const dlg=$('#dEditDlg'),form=$('#dEditForm'),err=$('#dEditErr');let delArm=0,tm=0,prevURL=null;
 function openEdit(code){const raw=code?S.dadmin[code]:null;form.reset();err.textContent='';delArm=0;clearTimeout(tm);
  const f=form.elements;f.original.value=code||'';
  const v=raw||{code:'',name:'',price:'',cookies:0,ckx:'',description:'',active:true,sort:0,image_url:''};
  for(const k of['code','name','price','cookies','ckx','description','sort'])f[k].value=v[k]==null?'':v[k];
  f.active.checked=!!v.active;f.remove_image.checked=false;if(prevURL){URL.revokeObjectURL(prevURL);prevURL=null;}
  const pv=$('#dImgPrev');pv.hidden=!v.image_url;if(v.image_url)pv.src=v.image_url;$('#dRemWrap').hidden=!v.image_url;
  $('#dDel').hidden=!code;$('#dDel').textContent='ลบรายการนี้';$('#dEditTitle').textContent=code?'แก้รายการ Donate: '+(v.name||code):'เพิ่มรายการ Donate';
  dlg.showModal();f.name.focus();}
 $$('.ebtn[data-dedit]').forEach(b=>b.addEventListener('click',e=>{e.stopPropagation();openEdit(b.dataset.dedit);}));
 $$('[data-add-ditem]').forEach(b=>b.addEventListener('click',()=>openEdit(null)));
 form.elements.image.addEventListener('change',()=>{const fl=form.elements.image.files[0];const pv=$('#dImgPrev');
  if(fl){if(prevURL)URL.revokeObjectURL(prevURL);prevURL=URL.createObjectURL(fl);pv.src=prevURL;pv.hidden=false;}});
 const post=async(url,body,isForm)=>{const r=await fetch(url,{method:'POST',credentials:'same-origin',
  headers:isForm?{'X-CSRF-Token':S.csrf}:{'Content-Type':'application/json','X-CSRF-Token':S.csrf},body:isForm?body:JSON.stringify(body)});
  let d={};try{d=await r.json();}catch(e){}if(r.status===401)location.reload();return{ok:r.ok&&d.ok,d};};
 const done=()=>{store.set('cc-edit',1);location.reload();};
 form.addEventListener('submit',async e=>{e.preventDefault();err.textContent='';const fd=new FormData(form);
  fd.set('active',form.elements.active.checked?'1':'0');fd.set('remove_image',form.elements.remove_image.checked?'1':'0');
  const fl=form.elements.image.files[0];if(!fl)fd.delete('image');else if(fl.size>8*1024*1024){err.textContent='รูปใหญ่เกิน 8 MB';return;}
  const b=$('#dSave');b.disabled=true;
  try{const r=await post('/api/admin/donate-item',fd,true);if(r.ok)return done();err.textContent=r.d.error||'บันทึกไม่สำเร็จ';}
  catch(x){err.textContent='เน็ตหลุด ลองใหม่อีกครั้ง';}b.disabled=false;});
 $('#dDel').addEventListener('click',async()=>{const b=$('#dDel');if(!delArm){delArm=1;b.textContent='กดอีกครั้งเพื่อลบจริง';
  tm=setTimeout(()=>{delArm=0;b.textContent='ลบรายการนี้';},4000);return;}
  try{const r=await post('/api/admin/donate-item/delete',{code:form.elements.original.value});if(r.ok)return done();
   err.textContent=r.d.error||'ลบไม่สำเร็จ';}catch(x){err.textContent='เน็ตหลุด ลองใหม่อีกครั้ง';}});}
if(!U||!$('#cart'))return;
// ------------------------------------------------------------------ ตะกร้า Donate
const KEY='cc-dcart-'+U.id,PKEY=KEY+'-pending';let cart={items:{},topup:0},busy=false,mem=null;
const getPending=()=>mem||store.get(PKEY,null);
function setPending(p){mem=p;store.set(PKEY,p||null);}
function clean(){const out={};let n=0;for(const[c,q]of Object.entries(cart.items||{})){const v=parseInt(q,10);
  if(ITEMS[c]&&v>0&&n<C.max_lines){out[c]=Math.min(v,C.max_qty);n++;}}
 cart.items=out;let t=parseInt(cart.topup,10)||0;if(C.rate<=0||t<0||n>=C.max_lines)t=0;cart.topup=Math.min(t,C.topup_max);}
function load(){const p=getPending();
 if(p&&Array.isArray(p.items)){cart={items:{},topup:+p.topup||0};p.items.forEach(l=>{if(l&&typeof l.code==='string'&&l.qty>0)cart.items[l.code]=l.qty;});
  if(p.ingame)$('#ing').value=p.ingame;return;}
 const v=store.get(KEY,null);cart=v&&typeof v==='object'?{items:v.items||{},topup:v.topup||0}:{items:{},topup:0};clean();}
const save=()=>store.set(KEY,cart);
const nlines=()=>Object.keys(cart.items).length+(cart.topup?1:0);
const total=()=>Object.entries(cart.items).reduce((t,[c,q])=>t+(ITEMS[c]?ITEMS[c].price*q:0),0)+cart.topup*100;
const needsName=()=>Object.keys(cart.items).some(c=>ITEMS[c]&&ITEMS[c].ckx);
const locked=()=>busy||!!getPending();
const LOCKMSG='ตะกร้านี้ส่งไปแล้วแต่ยังไม่รู้ผล — กด "ส่งอีกครั้ง" ก่อน (ไม่สร้างบิลซ้ำ)';
function showErr(t){$('#err').replaceChildren(t||'');}
const added=n=>{if(window.CC_toast&&!$('#cart').classList.contains('open'))CC_toast('ใส่ตะกร้า Donate แล้ว · '+n);};
function setQty(c,q){if(locked()){showErr(busy?'กำลังสร้างบิล รอสักครู่':LOCKMSG);openCart();return false;}
 q=Math.max(0,Math.min(q,C.max_qty));const had=cart.items[c]||0;
 if(q>0&&!had&&nlines()>=C.max_lines){showErr(`ใส่ได้สูงสุด ${C.max_lines} รายการต่อรอบ — ส่งรอบนี้ก่อนแล้วค่อยสั่งเพิ่ม`);return false;}
 showErr('');if(q>0)cart.items[c]=q;else delete cart.items[c];save();render();if(q>had)added((ITEMS[c]||{}).name||'');return true;}
function setTopup(b){if(locked()){showErr(LOCKMSG);return false;}
 if(b>0&&!cart.topup&&nlines()>=C.max_lines){showErr(`ใส่ได้สูงสุด ${C.max_lines} รายการต่อรอบ`);return false;}
 showErr('');const had=cart.topup;cart.topup=Math.max(0,Math.min(b,C.topup_max));save();render();if(cart.topup&&!had)added('เติมคุกกี้');return true;}
function stepper(c){const q=cart.items[c]||0,lk=locked();return el('span',{class:'step'},[
 el('button',{type:'button','aria-label':'ลด',text:'−',disabled:lk,on:{click:()=>setQty(c,q-1)}}),el('output',{text:String(q)}),
 el('button',{type:'button','aria-label':'เพิ่ม',text:'+',disabled:lk||q>=C.max_qty,on:{click:()=>setQty(c,q+1)}})]);}
function renderTiles(){tiles.forEach(t=>{const c=t.dataset.code;const q=c==='TOPUP'?(cart.topup?1:0):(cart.items[c]||0);
 const pic=$('.pic',t);let qb=$('.qb',pic);if(q){if(!qb){qb=el('span',{class:'qb'});pic.append(qb);}qb.textContent=c==='TOPUP'?'✓':'×'+q;}
 else if(qb)qb.remove();t.classList.toggle('in',!!q);});}
function renderCart(){const box=$('#lines');box.replaceChildren();
 for(const[c,q]of Object.entries(cart.items)){const it=ITEMS[c];if(!it)continue;
  box.append(el('div',{class:'line'},[el('span',{class:'n',text:it.name}),
   el('span',{class:'p',text:`${baht(it.price)} × ${q} = ${baht(it.price*q)}`}),
   el('span',{class:'ctl'},[stepper(c),el('button',{class:'x',type:'button','aria-label':'เอาออก',text:'×',disabled:locked(),
    on:{click:()=>setQty(c,0)}})])]));}
 if(cart.topup){const n=Math.floor(cart.topup*C.rate);
  box.append(el('div',{class:'line'},[el('span',{class:'n'},['เติมคุกกี้ ',fmt(n),ck()]),
   el('span',{class:'p',text:baht(cart.topup*100)}),
   el('span',{class:'ctl'},[el('button',{class:'btn alt sm',type:'button',text:'แก้ยอด',disabled:locked(),on:{click:()=>{closeCart();openItem('TOPUP');}}}),
    el('button',{class:'x',type:'button','aria-label':'เอาออก',text:'×',disabled:locked(),on:{click:()=>setTopup(0)}})])]));}
 const n=nlines(),t=total(),pend=getPending();
 $('#cartEmpty').hidden=!!n;$('#cartCount').textContent=fmt(n);$('#cartCount').hidden=!n;
 const nb=$('#cartBadge');if(nb){nb.textContent=fmt(n);nb.hidden=!n;}
 $('#sumTotal').textContent=baht(t);const mn=$('#minNote');
 if(n&&t<C.min){mn.textContent=`ขั้นต่ำต่อรอบ ${baht(C.min)} — เพิ่มอีก ${baht(C.min-t)}`;mn.classList.add('neg');}
 else{mn.textContent=`${fmt(n)}/${C.max_lines} รายการ · ชิ้นละไม่เกิน ${C.max_qty}`;mn.classList.remove('neg');}
 $('#ingWrap').hidden=!needsName();$('#ing').disabled=locked();$('#pend').hidden=!pend||busy;
 const go=$('#go');go.disabled=busy||(!pend&&(!n||t<C.min));if(!busy)go.textContent=pend?'ส่งอีกครั้ง':'ไปจ่ายเงิน';
 document.body.classList.toggle('has-cart',!!n);$('#barCount').textContent=fmt(n)+' รายการ';$('#barTotal').textContent=baht(t);}
function render(){if(!getPending())clean();renderTiles();renderCart();syncInert();}
function syncInert(){const c=$('#cart');if(!c.classList.contains('open'))c.setAttribute('inert','');else c.removeAttribute('inert');}
function openCart(){$('#cart').classList.add('open');$('#scrim').hidden=false;syncInert();const x=$('#cartClose');if(x)x.focus();}
function closeCart(){$('#cart').classList.remove('open');$('#scrim').hidden=true;syncInert();}
actions=(c,box)=>{const err=$('#idErr');
 if(c==='TOPUP'){if(C.rate<=0){err.textContent='ตอนนี้ปิดเติมคุกกี้ตามยอดอยู่';return;}
  if(tAmt){tAmt.value=cart.topup||'';tSync();}
  if(cart.topup)box.append(el('button',{class:'btn alt',type:'button',text:'เอาออก',on:{click:()=>{setTopup(0);idlg.close();}}}));
  box.append(el('button',{class:'btn big',type:'button',text:cart.topup?'อัปเดตตะกร้า':'ใส่ตะกร้า',on:{click:()=>{
   const b=tGet();if(b*100<C.min){err.textContent=`ขั้นต่ำ ${baht(C.min)}`;return;}
   if(b>C.topup_max){err.textContent=`สูงสุด ${baht(C.topup_max*100)} ต่อรอบ`;return;}
   if(setTopup(b))idlg.close();else err.textContent=$('#err').textContent;}}}));return;}
 const it=ITEMS[c];if(!it){err.textContent='รายการนี้ปิดไปแล้ว';return;}
 if(locked()){err.textContent=LOCKMSG;return;}
 const inCart=cart.items[c]||0;if(!inCart&&nlines()>=C.max_lines){err.textContent=`ตะกร้าเต็ม ${C.max_lines} รายการแล้ว`;return;}
 let q=Math.max(1,inCart||1);const out=el('output',{text:String(q)});
 const minus=el('button',{type:'button','aria-label':'ลด',text:'−'}),plus=el('button',{type:'button','aria-label':'เพิ่ม',text:'+'});
 const sync=()=>{out.textContent=String(q);minus.disabled=q<=1;plus.disabled=q>=C.max_qty;};
 minus.addEventListener('click',()=>{q=Math.max(1,q-1);sync();});plus.addEventListener('click',()=>{q=Math.min(C.max_qty,q+1);sync();});sync();
 box.append(el('div',{class:'qty'},[el('span',{text:'จำนวน'}),el('span',{class:'step'},[minus,out,plus])]));
 if(inCart)box.append(el('button',{class:'btn alt',type:'button',text:'เอาออก',on:{click:()=>{setQty(c,0);idlg.close();}}}));
 box.append(el('button',{class:'btn big',type:'button',text:inCart?'อัปเดตตะกร้า':'ใส่ตะกร้า',on:{click:()=>{if(setQty(c,q))idlg.close();}}}));};
// ------------------------------------------------------------------ คุยกับเซิฟ
async function post(url,body){try{const r=await fetch(url,{method:'POST',credentials:'same-origin',
  headers:{'Content-Type':'application/json','X-CSRF-Token':S.csrf},body:JSON.stringify(body)});
 let d=null;try{d=await r.json();}catch(e){}
 if(r.status===401){location.reload();return{kind:'reload',d};}
 if(r.ok&&d&&d.ok)return{kind:'ok',d};
 if(d&&d.ok===false&&r.status>=400&&r.status<500)return{kind:'refused',d};
 return{kind:'unknown',d};}catch(e){return{kind:'unknown',d:null};}}
const uuid=()=>crypto.randomUUID?crypto.randomUUID():String(Date.now())+Math.random().toString(16).slice(2);
function setGo(t){const g=$('#go');g.disabled=true;g.textContent=t;}
function goPay(url){if(!safeUrl(url))return false;busy=true;render();setGo('กำลังไปหน้าจ่ายเงิน…');location.href=url;return true;}
async function checkout(){if(busy)return;showErr('');let body=getPending();
 if(!body){const name=$('#ing').value.trim();
  if(needsName()&&!name){showErr('ใส่ชื่อในเกมก่อน (ชื่อที่ใช้ล็อกอินเข้าเซิฟ)');$('#ing').focus();return;}
  body={nonce:uuid(),ingame:name,topup:cart.topup,expected_total:total(),
   items:Object.entries(cart.items).map(([code,qty])=>({code,qty}))};setPending(body);}
 busy=true;render();setGo('กำลังสร้างบิล…');
 const r=await post('/api/donate/checkout',body);busy=false;if(r.kind==='reload')return;
 if(r.d&&r.d.order)upsert(r.d.order);
 if(r.kind==='ok'){setPending(null);cart={items:{},topup:0};save();if(goPay(r.d.pay_url))return;
  note(r.d.paid?`รายการ ${r.d.order.label} จ่ายแล้ว ✅`:'สร้างรายการแล้ว','ok');render();return;}
 if(r.kind==='refused'){setPending(null);showErr(r.d.error||'สั่งไม่สำเร็จ');
  if(r.d.code==='open_bill'&&r.d.order)offerReplace(r.d.order);
  if(r.d.code==='changed')$('#err').append(' ',el('button',{class:'linkbtn',type:'button',text:'โหลดรายการใหม่',on:{click:()=>location.reload()}}));
  render();return;}
 showErr((r.d&&r.d.error)||'ยังไม่รู้ผล (เน็ต/เซิฟสะดุด) — กดส่งอีกครั้ง ระบบจะไม่สร้างบิลซ้ำ');render();}
function offerReplace(o){const box=el('div',{class:'fixbox'});
 if(o.pay_url&&safeUrl(o.pay_url))box.append(el('a',{class:'btn sm',href:o.pay_url,text:'จ่ายบิลเดิม '+o.label}));
 box.append(el('button',{class:'btn alt sm',type:'button',text:'ยกเลิกบิลเดิมแล้วสั่งใหม่',on:{click:async()=>{
  const r=await post('/api/donate/cancel',{id:o.id});if(r.d&&r.d.order)upsert(r.d.order);
  if(r.kind==='ok'){showErr('');checkout();}else showErr((r.d&&r.d.error)||'ยกเลิกไม่สำเร็จ ลองใหม่');}}}));
 $('#err').append(box);}
$('#go').addEventListener('click',checkout);
$('#pendDrop').addEventListener('click',()=>{setPending(null);showErr('');render();});
$$('[data-open-cart]').forEach(b=>b.addEventListener('click',openCart));$('#cartClose').addEventListener('click',closeCart);
$('#scrim').addEventListener('click',closeCart);
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeCart();});
if(!$('#ing').value)$('#ing').value=U.ingame||'';
// ------------------------------------------------------------------ Donate ของฉัน
let ORDERS=S.orders||[];
const TAG={review:'wait',pending:'go',expired:'off',paid:'wait',delivered:'ok',cancelled:'off'};
function upsert(o){const i=ORDERS.findIndex(x=>x.id===o.id);const was=i>=0?ORDERS[i].step:0;
 if(i>=0)ORDERS[i]=o;else ORDERS.unshift(o);renderOrders();if(o.step>=2&&was<2)balance();}
async function balance(){try{const r=await fetch('/api/me',{credentials:'same-origin',cache:'no-store'});if(!r.ok)return;
 const d=await r.json();if(d.user){U.balance=d.user.balance;const t=$('#topBal');if(t)t.textContent=fmt(d.user.balance);}}catch(e){}}
function note(t,k){const n=$('#dnote');n.className='dnote'+(k&&k!=='ok'?' '+k:'');n.replaceChildren(t);n.hidden=!t;}
const EXT=()=>{const t=document.getElementById('extTpl');return t.content.firstElementChild.cloneNode(true);};
function orderCard(o){const li=el('li',{class:'dord st-'+o.status,id:'o'+o.id});
 li.append(el('div',{class:'dh'},[el('b',{text:o.label}),el('span',{class:'tag '+(TAG[o.status]||'off'),text:o.text}),
  el('span',{class:'amt',text:baht(o.total)})]));
 if(o.status!=='cancelled')li.append(el('ol',{class:'steps','aria-label':'ขั้นตอน'},['สั่งแล้ว','จ่ายเงิน','ส่งของ'].map((s,i)=>
  el('li',{class:i<o.step?'done':(i===o.step&&o.step<3?'cur':''),text:s}))));
 li.append(el('p',{class:'dl',text:o.lines.map(l=>`${l.name} × ${l.qty}`).join(' · ')}));
 li.append(el('span',{class:'when',text:(o.web?'สั่งจากเว็บ · ':'สั่งใน Discord · ')+when(o.created)}));
 if(o.expires)li.append(el('p',{class:'exp',text:'บิลหมดอายุในอีก '+left(o.expires)}));
 if(o.progress&&o.progress.length){const ul=el('ul',{class:'prog'});o.progress.forEach(p=>ul.append(el('li',{},[
  el('span',{class:'dot '+(p.k==='ok'?'ok':p.k==='bad'?'bad':'wait')}),el('span',{text:p.t})])));li.append(ul);}
 const acts=o.actions||[];let nameIn=null;
 if(o.needs_name&&(acts.includes('pay')||acts.includes('renew'))){nameIn=el('input',{class:'ing',maxlength:'40',autocomplete:'off',
  spellcheck:'false',value:U.ingame||'','aria-label':'ชื่อในเกม'});
  li.append(el('label',{class:'oname'},['ชื่อในเกมที่จะรับของ',nameIn]));}
 const err=el('p',{class:'oerr',role:'alert'});const row=el('div',{class:'da'});
 const run=async(btn,url,body,label)=>{btn.disabled=true;const old=btn.textContent;btn.textContent=label;err.textContent='';
  const r=await post(url,body);btn.disabled=false;btn.textContent=old;if(r.kind==='reload')return r;
  if(r.d&&r.d.order){upsert(r.d.order);}if(r.kind!=='ok'){const e2=$('#o'+o.id+' .oerr');if(e2)e2.textContent=(r.d&&r.d.error)||'ทำไม่สำเร็จ ลองใหม่อีกครั้ง';}
  return r;};
 if(acts.includes('pay')&&o.pay_url&&safeUrl(o.pay_url))row.append(el('a',{class:'btn sm',href:o.pay_url,text:'จ่ายเงิน'}));
 else if(acts.includes('pay')||acts.includes('renew')){const b=el('button',{class:'btn sm',type:'button',
  text:acts.includes('renew')?'สร้างบิลใหม่':'ยืนยันและจ่าย'});b.addEventListener('click',async()=>{
   const body={id:o.id};if(nameIn){body.ingame=nameIn.value.trim();if(!body.ingame){err.textContent='ใส่ชื่อในเกมก่อน';nameIn.focus();return;}}
   const r=await run(b,'/api/donate/pay',body,'กำลังสร้างบิล…');if(r.kind==='ok'&&!goPay(r.d.pay_url)&&r.d.paid)note(`รายการ ${o.label} จ่ายแล้ว ✅`,'ok');});
  row.append(b);}
 if(acts.includes('check')){const b=el('button',{class:'btn alt sm',type:'button',text:'เช็คสถานะ'});
  b.addEventListener('click',async()=>{const r=await run(b,'/api/donate/check',{id:o.id},'กำลังเช็ค…');
   if(r.kind==='ok')note(r.d.order.step>=2?`ได้รับยอด ${r.d.order.label} แล้ว ✅ ขอบคุณที่สนับสนุนเซิฟ`:`ยังไม่ได้รับยอด ${r.d.order.label} — ถ้าจ่ายแล้วรอสักครู่`,r.d.order.step>=2?'ok':'wait');});row.append(b);}
 if(acts.includes('cancel')){const b=el('button',{class:'btn ghost sm',type:'button',text:'ยกเลิก'});let arm=0,tm=0;
  b.addEventListener('click',async()=>{if(!arm){arm=1;b.classList.add('arm');b.textContent='กดอีกครั้งเพื่อยกเลิก';
   tm=setTimeout(()=>{arm=0;b.classList.remove('arm');b.textContent='ยกเลิก';},4000);return;}clearTimeout(tm);
   await run(b,'/api/donate/cancel',{id:o.id},'กำลังยกเลิก…');});row.append(b);}
 if(o.thread_url&&safeUrl(o.thread_url))row.append(el('a',{class:'linkbtn',href:o.thread_url,target:'_blank',rel:'noopener'},['ห้อง Donate ',EXT()]));
 li.append(row,err);return li;}
function renderOrders(){const ul=$('#donList');if(!ul)return;ul.replaceChildren();let off=0;
 ORDERS.forEach(o=>{if(o.status==='cancelled'&&++off>2)return;ul.append(orderCard(o));});$('#donNone').hidden=!!ORDERS.length;}
async function refreshOrders(){try{const r=await fetch('/api/donate',{credentials:'same-origin',cache:'no-store'});
 if(r.status===401){location.reload();return;}if(!r.ok)return;const d=await r.json();
 if(Array.isArray(d.orders)){const before=Object.fromEntries(ORDERS.map(o=>[o.id,o.step]));ORDERS=d.orders;renderOrders();
  if(ORDERS.some(o=>o.step>=2&&(before[o.id]||0)<2))balance();}}catch(e){}}
// กลับมาจากหน้าจ่ายเงิน (?paid=ID) → เช็คยอดถี่ ๆ จนเห็นว่าจ่ายแล้ว · ?order=ID (กดย้อนกลับ) → เลื่อนไปที่รายการ
(()=>{const p=new URLSearchParams(location.search);const paid=+p.get('paid')||0,focus=+p.get('order')||0;
 if(paid||focus)try{history.replaceState(null,'',location.pathname);}catch(e){}
 renderOrders();const id=paid||focus;const tgt=id&&$('#o'+id);if(tgt)tgt.scrollIntoView({block:'center'});
 if(!paid||!ORDERS.some(o=>o.id===paid))return;
 const o=ORDERS.find(x=>x.id===paid);if(o.step>=2){note(`ได้รับยอด ${o.label} แล้ว ✅ ขอบคุณที่สนับสนุนเซิฟ 🍪`,'ok');return;}
 note(`กำลังเช็คยอด ${o.label} กับระบบจ่ายเงิน…`,'wait');let k=0;
 const tick=async()=>{const r=await post('/api/donate/check',{id:paid});const x=r.d&&r.d.order;if(x)upsert(x);
  if(x&&x.step>=2){note(`ได้รับยอด ${x.label} แล้ว ✅ ขอบคุณที่สนับสนุนเซิฟ 🍪 — ดูสถานะส่งของได้ที่ Donate ของฉัน`,'ok');return;}
  if(++k>=30){note(`ยังไม่เห็นยอด ${o.label} — ถ้าจ่ายแล้ว รอสักครู่แล้วกด "เช็คสถานะ" (บอทเช็คให้ทุก ~20 วินาทีด้วย)`,'wait');return;}
  setTimeout(tick,4000);};tick();})();
let polls=0;setInterval(()=>{if(polls>90||document.hidden)return;if(!ORDERS.some(o=>['pending','paid'].includes(o.status)))return;
 polls++;refreshOrders();},10000);
load();render();
})();
"""


def _tile(i: dict, e, editor: bool = False, adm_only: bool = False) -> str:
    key, color, label = KIND[i["kind"]]
    meta = []
    if i["cookies"]:
        meta.append(f"<span class='gain'>ได้ {i['cookies']:,}{cookie(16)}</span>")
    if i["ckx"]:
        meta.append(f"<span>{px('truck', 12)}ส่งเข้าเกมเอง</span>")
    elif not i["cookies"]:
        meta.append(f"<span>{px('user', 12)}แอดมินส่งให้</span>")
    if adm_only:
        meta.append("<span>ปิดอยู่</span>")
    if i.get("image_url"):
        cover = f"<img src='{e(i['image_url'])}' alt='' loading='lazy'>"
    elif i["kind"] == "pack":
        cover = f"<img src='{web_art.COOKIE_PACK}' alt='' loading='lazy'>"
    else:
        cover = art(key, 48)
    desc = f"<p class='desc'>{e(i['description'])}</p>" if i.get("description") else ""
    edit = (f"<button class='ebtn' type='button' data-dedit='{e(i['code'])}' aria-label='แก้ {e(i['name'])}'>"
            f"{px('edit', 24)}</button>" if editor else "")
    return (f"<article class='item dtile{' adm-only' if adm_only else ''}' tabindex='0' data-code='{e(i['code'])}' "
            f"data-kind='{i['kind']}' data-name='{e(i['name'])}' data-label='{e(label)}'>"
            f"<div class='pic'><span class='cover'>{cover}</span>{edit}</div>"
            f"<div class='body'><h2>{e(i['name'])}</h2>{desc}<div class='meta'>{''.join(meta)}</div></div>"
            f"<div class='price'><b>{baht(i['price'])}</b></div></article>")


def render_donate(catalog: dict, meta: dict, user: dict = None, csrf: str = "", login: bool = False,
                  notice: str = "", nonce: str = "", orders: list = None, enabled: bool = True,
                  admin_items: list = None) -> str:
    """catalog: backend.donate_catalog() · orders: donate_brief ของคนนี้ · user: backend.me() (None = ยังไม่ล็อกอิน)
    admin_items: รายการ Donate ทั้งหมดพร้อมค่าดิบ — ส่งมาเฉพาะคนแก้ร้าน"""
    e = html.escape
    orders = orders or []
    editor = bool(user and user.get("editor") and admin_items is not None)
    site = meta.get("site") or web_site.load("")
    meta = dict(meta, site=site, donate_on=True)
    items = catalog.get("items") or []
    rate = int(catalog.get("rate") or 0)
    min_text = baht(catalog.get("min") or 0)
    cats = category_list([], None, site, {}, False)
    if meta.get("shop_items") is not None:
        cats = category_list(meta["shop_items"], None, site, meta.get("cat_info") or {}, False)

    # ---- หัวหน้า Donate (แก้รูป/ข้อความ/เรตได้)
    d = site["donate"]
    intro = d.get("intro") or meta.get("intro") or ""
    bg = f"<img class='bgimg' src='{e(img_url(d['img']))}' alt=''>" if d.get("img") else "<span class='pat'></span>"
    hero = win("DONATE.EXE",
               f"<div class='dhero {e(d.get('color') or 'c1')}'>{bg}<div class='tx'><h1>{e(d.get('title') or 'Donate')}</h1>"
               + (f"<p>{e(intro)}</p>" if intro else "")
               + "<ol><li>เลือกแพ็ก / ของ ใส่ตะกร้า</li><li>จ่าย PromptPay หรือบัตร บนเว็บ</li>"
                 "<li>คุกกี้เข้ากระเป๋า · ของส่งเข้าเกมให้เอง</li></ol></div>"
               + ("" if d.get("img") else f"<span class='art'><img src='{web_art.COOKIE_BAR}' alt='' width='640' height='342'></span>")
               + "</div>"
               + (f"<button class='sedit' type='button' data-slot='donate' title='แก้หัวหน้า Donate' "
                  f"aria-label='แก้หัวหน้า Donate'>{px('edit', 24)}</button>" if editor else ""),
               "dhwin", inner="hbox")

    # ---- รายการ
    kinds = {i["kind"] for i in items}
    tiles = []
    if rate > 0:
        tiles.append(f"<article class='item dtile' tabindex='0' data-code='TOPUP' data-kind='pack' "
                     f"data-name='เติมคุกกี้ตามยอด' data-label='เติมคุกกี้'>"
                     f"<div class='pic'><span class='cover'><img class='ck-foil' src='{web_art.COOKIE_FOIL}' alt=''></span></div>"
                     f"<div class='body'><h2>เติมคุกกี้ตามยอด</h2>"
                     f"<p class='desc'>ใส่ยอดเองได้ · 1 บาท = {rate:,} คุกกี้</p>"
                     f"<div class='meta'><span class='gain'>1 บาท = {rate:,}{cookie(16)}</span></div></div>"
                     f"<div class='price'><b>ตามยอด</b></div></article>")
        kinds.add("pack")
    tiles += [_tile(i, e, editor) for i in items]
    if editor:
        public = {i["code"] for i in items}
        tiles += [_tile(i, e, True, adm_only=True) for i in admin_items if i["code"] not in public]
    type_btns = ["<button class='type' type='button' data-dtype='' aria-pressed='true'>ทั้งหมด</button>"]
    for k in ("pack", "game", "manual"):
        if k in kinds:
            key, _, label = KIND[k]
            type_btns.append(f"<button class='type' type='button' data-dtype='{k}' aria-pressed='false'>"
                             f"{art(key, 24)}{label}</button>")
    off = win("ERROR.EXE", f"<img src='{web_art.MASCOT}' width='120' height='120' alt=''><h2>ระบบ Donate ยังไม่เปิด</h2>"
              "<p>แอดมินกำลังตั้งค่า กลับมาใหม่เร็ว ๆ นี้นะ</p><a class='btn' href='/'>กลับไปร้านคุกกี้</a>",
              "dpanel off-card", tag="div")
    if not enabled and not editor:
        main = f"<div class='dmain'>{off}</div>"
    else:
        empty = "" if tiles else "<p class='empty'>ยังไม่มีรายการให้ Donate — รอแอดมินเพิ่มก่อนนะ</p>"
        shop = win("SHOP.EXE",
                   f"<section class='typebox'><h3 class='pick'>เลือกประเภท</h3><div class='types' role='group' aria-label='ประเภท'>"
                   f"{''.join(type_btns)}</div></section>"
                   f"<h3 class='pick'>เลือกรายการที่ต้องการ</h3><div class='grid dgrid' id='dgrid'>{''.join(tiles)}</div>"
                   f"<p class='empty' id='dempty' hidden>ไม่มีรายการในประเภทนี้</p>{empty}",
                   "dpanel", attrs=" aria-label='รายการ Donate'")
        mine = ""
        if user:
            mine = win("<span id='myDonT'>MY_DONATE.LOG</span>",
                       "<ul class='dlist' id='donList'></ul><p class='none' id='donNone'>ยังไม่เคย Donate</p>",
                       "dpanel dorders", attrs=" id='myDon' aria-labelledby='myDonT'")
        active = any(o.get("status") in ("review", "pending", "expired", "paid") for o in orders)
        # มีรายการค้าง/กำลังส่ง → โชว์ Donate ของฉันก่อน (กลับมาจากหน้าจ่ายเห็นสถานะทันที)
        body = mine + shop if active else shop + mine
        if not enabled:  # คนแก้ร้านเตรียมรายการไว้ก่อนเปิดระบบได้ (คนทั่วไปเห็นแค่ "ยังไม่เปิด")
            body = off + shop
        main = f"<div class='dmain'>{hero}<p class='dnote' id='dnote' role='status' hidden></p>{body}</div>"

    # ---- แถบขวา
    rail = [win("HOW_TO.TXT", "<ol class='how'>"
                "<li>เลือกแพ็กหรือของที่อยากได้ ใส่ตะกร้า</li>"
                "<li>กด <b>ไปจ่ายเงิน</b> แล้วสแกน PromptPay หรือจ่ายด้วยบัตร</li>"
                "<li>จ่ายเสร็จ คุกกี้เข้ากระเป๋า / ของส่งเข้าเกมให้อัตโนมัติ</li></ol>"
                "<p class='info'>บอทโพสต์สรุปและสถานะให้ในห้อง Donate ส่วนตัวบน Discord ด้วย ไม่ต้องพิมพ์เอง</p>"
                f"<small>ขั้นต่ำต่อรอบ {min_text} · บิลมีอายุ {int(meta.get('minutes') or 60)} นาที</small>",
                "rinfo", attrs=" aria-label='วิธี Donate'")]
    if not user and login:
        rail.insert(0, win("WELCOME.EXE", f"<img class='mascot' src='{web_art.MASCOT}' width='130' height='130' alt=''>"
                           "<p>ล็อกอินด้วย Discord เพื่อ Donate และจ่ายเงินบนเว็บได้เลย</p>"
                           "<a class='login' href='/login?next=/donate'>เข้าสู่ระบบด้วย Discord</a>", "guest"))
    rail.append(promos_html(site, meta, user, editor, "donate"))

    # ---- ตะกร้า Donate
    cart = ""
    if user and enabled:
        cart = (
            "<aside class='cart' id='cart' aria-label='ตะกร้า Donate' inert>"
            f"<div class='cart-head'>{px('gift', 24)}<h2>DONATE CART</h2><span class='pill' id='cartCount' hidden></span>"
            "<button class='x close' id='cartClose' type='button' aria-label='ปิดตะกร้า'>×</button></div>"
            "<div class='cart-scroll'><div id='lines'></div>"
            f"<p class='cart-empty' id='cartEmpty'><img src='{web_art.COOKIE_FOIL}' width='110' height='108' alt=''>"
            "ยังไม่มีรายการ<br>กดเลือกแพ็กที่อยากได้</p>"
            "<div id='ingWrap' hidden><label class='ing-l' for='ing'>ชื่อในเกมที่จะรับของ"
            "<small>ชื่อที่ใช้ล็อกอินเข้าเซิฟ (ไม่ใช่ชื่อตัวละคร)</small></label>"
            "<input class='ing' id='ing' maxlength='40' autocomplete='off' spellcheck='false'></div>"
            "<div class='pend' id='pend' hidden>ส่งไปแล้วแต่ยังไม่รู้ผล กด <b>ส่งอีกครั้ง</b> ได้เลย ระบบจะไม่สร้างบิลซ้ำ · "
            "<button class='linkbtn' type='button' id='pendDrop'>ยกเลิกแล้วแก้ตะกร้า</button></div>"
            "<div class='err' id='err' role='alert'></div></div>"
            "<div class='sum' id='sum'><div class='t'><span>ยอด Donate</span><b id='sumTotal'>฿0</b></div>"
            "<div><span class='minnote' id='minNote'></span></div></div>"
            "<div class='acts'><button class='btn big' id='go' type='button' disabled>ไปจ่ายเงิน</button>"
            f"<span class='paynote'>{px('coin', 12)}จ่ายผ่าน Stripe · PromptPay / บัตร</span></div></aside>"
            "<div class='bar' id='bar'><span><span id='barCount'></span> · <b id='barTotal'></b></span>"
            "<button class='btn' type='button' data-open-cart>ดูตะกร้า</button></div>"
            "<div class='scrim' id='scrim' hidden></div>")

    quick = "".join(f"<button type='button' data-amt='{a}'>฿{a:,}</button>" for a in (50, 100, 200, 500, 1000)
                    if a * 100 >= int(catalog.get("min") or 0))
    dialogs = (
        "<dialog id='itemDlg' aria-labelledby='idName'><div class='dlg idlg'>"
        "<div class='wt'><span class='tt'>DONATE_ITEM.EXE</span><span class='wb'><button class='wx' type='button' data-close "
        "aria-label='ปิด'>×</button></span></div>"
        "<div class='idtop'><div class='idpic' id='idPic'></div><div class='idinfo'><span class='cat' id='idCat'></span>"
        "<h3 id='idName'></h3><div class='meta' id='idMeta'></div><b class='idprice' id='idPrice'></b></div></div>"
        "<div class='idbody'><p id='idDesc'></p></div>"
        "<div class='tbox' id='tBox' hidden><label class='flab' for='tAmt'>ยอด Donate (บาท)</label>"
        f"<div class='row'><input id='tAmt' type='number' inputmode='numeric' min='1' step='1' placeholder='เช่น 100'>"
        f"<span class='get' id='tGet'></span></div><div class='quick' id='tQuick'>{quick}</div>"
        f"<small>ขั้นต่ำ {min_text} · สูงสุด ฿{int(catalog.get('topup_max') or 0):,} ต่อรอบ</small></div>"
        "<div class='idbody'><p class='err' id='idErr' role='alert'></p></div>"
        "<div class='acts' id='idAct'></div></div></dialog>") if enabled or editor else ""
    state = {"catalog": catalog, "user": user, "csrf": csrf, "login": bool(login), "orders": orders}
    if editor:
        state["dadmin"] = {i["code"]: i["raw"] for i in admin_items}
        dialogs += (
            "<dialog id='dEditDlg' aria-labelledby='dEditTitle'><form class='dlg' id='dEditForm' method='dialog'>"
            "<h3 id='dEditTitle'>รายการ Donate</h3><div class='scroll'><input type='hidden' name='original'>"
            "<label class='fld'>รหัส<input name='code' required maxlength='20' pattern='[A-Za-z0-9_\\-]{1,20}'>"
            "<small>อังกฤษ/ตัวเลข/_ - เช่น P100</small></label>"
            "<label class='fld'>ราคา (บาท)<input name='price' required inputmode='decimal' placeholder='เช่น 100 หรือ 49.50'></label>"
            "<label class='fld w'>ชื่อที่ผู้เล่นเห็น<input name='name' required maxlength='80'></label>"
            "<label class='fld'>ได้คุกกี้ (แพ็ก)<input name='cookies' type='number' min='0' max='10000000'>"
            "<small>0 = ไม่ใช่แพ็กคุกกี้</small></label>"
            "<label class='fld'>ลำดับ (น้อยขึ้นก่อน)<input name='sort' type='number'></label>"
            "<label class='fld w'>รหัส Cookie Express (ของในเกม)<textarea name='ckx' rows='2' "
            "placeholder='CX-79MN-V4KT*2 CV-AMMF-Z6LF'></textarea><small>จ่ายแล้วส่งเข้าเกมเอง · ว่าง = ไม่มีของในเกม "
            "(ถ้าไม่ใช่แพ็กด้วย = แอดมินส่งเอง)</small></label>"
            "<label class='fld w'>คำอธิบาย<textarea name='description' maxlength='200'></textarea></label>"
            "<div class='fld w'>รูป (ไม่ใส่ = รูปเริ่มต้นตามประเภท)<div class='imgrow'><img id='dImgPrev' alt='' hidden>"
            "<input name='image' type='file' accept='image/png,image/jpeg,image/webp,image/gif'></div>"
            "<label class='fld chk' id='dRemWrap'><input type='checkbox' name='remove_image'>ลบรูปเดิม</label></div>"
            "<label class='fld chk w'><input type='checkbox' name='active'>เปิดให้ Donate (ไม่ติ๊ก = ซ่อน)</label>"
            "<p class='err w' id='dEditErr' role='alert'></p></div>"
            "<div class='acts'><button class='btn danger' id='dDel' type='button'>ลบรายการนี้</button>"
            "<button class='btn alt' type='button' data-close>ยกเลิก</button>"
            "<button class='btn' id='dSave' type='submit'>บันทึก</button></div></form></dialog>")
    return shell(active="donate", title=f"{d.get('title') or 'Donate'} · {meta.get('title') or 'Cookie Shop'}", user=user,
                 meta=meta, login=login, editor=editor, main=main, rail="".join(rail), cats=cats, state=state,
                 page_js=DJS if enabled or editor else "", nonce=nonce, notice_html=notices(meta, notice),
                 cart_html=cart, dialogs=dialogs, extra_css=DCSS, body_cls="dpage")
