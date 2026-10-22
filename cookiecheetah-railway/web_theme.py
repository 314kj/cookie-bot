"""ธีมเว็บร้าน Cookie Cheetah — พื้นดำเลื่อมชมพู · หน้าต่างแบบ Win95 · ปุ่มเม็ดยาไล่สี · ฟอนต์พิกเซล (VT323)

สีทั้งหมดเป็นตัวแปร (--teal = สีหลัก ค่าเริ่มต้นชมพูมิกุ, --glit = สีเลื่อม) — สีธีมที่แก้บนเว็บมาทับใน :root ทีหลัง
"""

# เลื่อม: ฝุ่นละเอียด (A, ไทล์ 240px) + ดาวประกาย (B, ไทล์ 380px กระพริบ) — SVG สีขาวใช้เป็น mask, สีจริง = --glit
GLIT_A = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='240' height='240'%3E%3Ccircle cx='108.8' cy='134.1' r='1.2' fill-opacity='0.75'/%3E%3Ccircle cx='121.9' cy='140.6' r='0.8' fill-opacity='1'/%3E%3Ccircle cx='114.3' cy='146.9' r='0.8' fill-opacity='0.25'/%3E%3Ccircle cx='107.4' cy='35.5' r='1.5' fill-opacity='0.25'/%3E%3Ccircle cx='142.5' cy='95.5' r='1.2' fill-opacity='1'/%3E%3Ccircle cx='155.4' cy='149.1' r='1.5' fill-opacity='0.25'/%3E%3Ccircle cx='16.1' cy='46.9' r='0.8' fill-opacity='1'/%3E%3Ccircle cx='9.1' cy='111.5' r='1.2' fill-opacity='1'/%3E%3Ccircle cx='200.8' cy='124.5' r='1' fill-opacity='0.75'/%3E%3Ccircle cx='3.1' cy='22.1' r='1' fill-opacity='0.75'/%3E%3Ccircle cx='237.4' cy='237.0' r='0.6' fill-opacity='0.55'/%3E%3Ccircle cx='76.4' cy='56.2' r='1' fill-opacity='0.25'/%3E%3Ccircle cx='18.6' cy='182.8' r='1.2' fill-opacity='0.25'/%3E%3Ccircle cx='201.8' cy='93.2' r='0.6' fill-opacity='0.25'/%3E%3Ccircle cx='52.4' cy='220.8' r='0.6' fill-opacity='0.75'/%3E%3Ccircle cx='90.6' cy='169.3' r='1.2' fill-opacity='0.25'/%3E%3Ccircle cx='135.6' cy='48.8' r='1' fill-opacity='0.55'/%3E%3Ccircle cx='22.6' cy='80.5' r='1.2' fill-opacity='0.25'/%3E%3Ccircle cx='33.8' cy='168.9' r='0.6' fill-opacity='0.25'/%3E%3Ccircle cx='111.7' cy='116.9' r='1.5' fill-opacity='0.4'/%3E%3Ccircle cx='107.6' cy='47.0' r='0.8' fill-opacity='0.75'/%3E%3Ccircle cx='153.9' cy='29.5' r='1.2' fill-opacity='0.4'/%3E%3Ccircle cx='2.1' cy='206.0' r='1.5' fill-opacity='0.55'/%3E%3Ccircle cx='237.5' cy='6.6' r='0.8' fill-opacity='0.75'/%3E%3Ccircle cx='237.0' cy='144.1' r='1.5' fill-opacity='0.25'/%3E%3Ccircle cx='11.9' cy='36.5' r='1.2' fill-opacity='0.55'/%3E%3Ccircle cx='4.3' cy='146.0' r='1' fill-opacity='0.75'/%3E%3Ccircle cx='19.3' cy='23.3' r='1.5' fill-opacity='0.4'/%3E%3Ccircle cx='5.7' cy='89.0' r='1.5' fill-opacity='0.75'/%3E%3Ccircle cx='32.0' cy='140.6' r='1.5' fill-opacity='0.4'/%3E%3Ccircle cx='206.5' cy='45.1' r='0.8' fill-opacity='0.55'/%3E%3Ccircle cx='216.4' cy='195.0' r='0.8' fill-opacity='0.4'/%3E%3Ccircle cx='39.4' cy='150.4' r='1.5' fill-opacity='0.4'/%3E%3Ccircle cx='164.1' cy='93.6' r='1.2' fill-opacity='1'/%3E%3Ccircle cx='20.5' cy='13.2' r='0.6' fill-opacity='0.25'/%3E%3Ccircle cx='122.9' cy='62.2' r='1.2' fill-opacity='0.55'/%3E%3Ccircle cx='101.3' cy='215.5' r='1.2' fill-opacity='0.55'/%3E%3Ccircle cx='124.7' cy='221.3' r='0.6' fill-opacity='0.4'/%3E%3Ccircle cx='55.9' cy='134.0' r='1.5' fill-opacity='1'/%3E%3Ccircle cx='19.5' cy='52.1' r='0.8' fill-opacity='0.25'/%3E%3Ccircle cx='18.3' cy='99.1' r='0.8' fill-opacity='0.25'/%3E%3Ccircle cx='13.0' cy='68.5' r='1.5' fill-opacity='1'/%3E%3Ccircle cx='231.6' cy='23.8' r='0.8' fill-opacity='0.75'/%3E%3Ccircle cx='233.4' cy='157.0' r='1.5' fill-opacity='1'/%3E%3Ccircle cx='225.5' cy='141.2' r='0.6' fill-opacity='0.75'/%3E%3Ccircle cx='216.8' cy='167.4' r='0.6' fill-opacity='0.25'/%3E%3Ccircle cx='143.2' cy='19.7' r='0.6' fill-opacity='0.55'/%3E%3Ccircle cx='77.3' cy='237.8' r='0.6' fill-opacity='0.75'/%3E%3Ccircle cx='130.9' cy='175.9' r='0.8' fill-opacity='0.55'/%3E%3Ccircle cx='85.0' cy='163.7' r='0.6' fill-opacity='0.75'/%3E%3Ccircle cx='224.8' cy='9.1' r='1.2' fill-opacity='1'/%3E%3Ccircle cx='5.4' cy='158.3' r='1.2' fill-opacity='1'/%3E%3Ccircle cx='4.9' cy='19.1' r='0.6' fill-opacity='0.25'/%3E%3Ccircle cx='236.4' cy='209.6' r='1' fill-opacity='0.75'/%3E%3Ccircle cx='222.5' cy='165.8' r='1.2' fill-opacity='0.75'/%3E%3Ccircle cx='111.2' cy='129.7' r='1.5' fill-opacity='1'/%3E%3Ccircle cx='9.0' cy='143.9' r='1.2' fill-opacity='0.25'/%3E%3Ccircle cx='56.3' cy='166.8' r='1.2' fill-opacity='1'/%3E%3Ccircle cx='157.8' cy='116.8' r='0.6' fill-opacity='0.55'/%3E%3Ccircle cx='73.0' cy='162.0' r='0.8' fill-opacity='1'/%3E%3Ccircle cx='42.0' cy='215.8' r='1.2' fill-opacity='0.75'/%3E%3Ccircle cx='212.4' cy='79.2' r='1' fill-opacity='0.4'/%3E%3Ccircle cx='151.7' cy='191.7' r='0.8' fill-opacity='0.4'/%3E%3Ccircle cx='92.7' cy='139.6' r='1' fill-opacity='0.4'/%3E%3Ccircle cx='34.1' cy='119.2' r='0.6' fill-opacity='0.25'/%3E%3Ccircle cx='226.2' cy='67.3' r='0.8' fill-opacity='0.25'/%3E%3Ccircle cx='108.4' cy='66.9' r='0.8' fill-opacity='0.75'/%3E%3Ccircle cx='92.3' cy='124.7' r='1' fill-opacity='1'/%3E%3Ccircle cx='108.8' cy='19.6' r='0.6' fill-opacity='0.55'/%3E%3Ccircle cx='208.0' cy='11.8' r='1' fill-opacity='1'/%3E%3Ccircle cx='85.6' cy='155.2' r='1.5' fill-opacity='0.25'/%3E%3Ccircle cx='153.3' cy='97.6' r='0.8' fill-opacity='0.25'/%3E%3Ccircle cx='183.5' cy='64.9' r='0.8' fill-opacity='0.25'/%3E%3Ccircle cx='234.2' cy='29.2' r='0.6' fill-opacity='1'/%3E%3Ccircle cx='156.6' cy='192.5' r='0.6' fill-opacity='0.4'/%3E%3Ccircle cx='49.0' cy='114.1' r='0.8' fill-opacity='0.25'/%3E%3Ccircle cx='180.2' cy='128.2' r='0.6' fill-opacity='0.4'/%3E%3Ccircle cx='55.4' cy='185.7' r='1.5' fill-opacity='1'/%3E%3Ccircle cx='120.1' cy='237.2' r='0.8' fill-opacity='0.75'/%3E%3Ccircle cx='202.3' cy='167.2' r='0.8' fill-opacity='0.25'/%3E%3Ccircle cx='98.9' cy='212.7' r='1.2' fill-opacity='0.4'/%3E%3Ccircle cx='108.3' cy='48.5' r='0.6' fill-opacity='0.75'/%3E%3Ccircle cx='131.8' cy='156.0' r='1.5' fill-opacity='0.55'/%3E%3Ccircle cx='111.4' cy='155.7' r='0.8' fill-opacity='0.25'/%3E%3Ccircle cx='172.4' cy='195.1' r='0.6' fill-opacity='0.4'/%3E%3Ccircle cx='59.2' cy='94.1' r='0.6' fill-opacity='0.55'/%3E%3Ccircle cx='128.7' cy='188.6' r='1' fill-opacity='0.55'/%3E%3Ccircle cx='216.8' cy='204.0' r='1' fill-opacity='1'/%3E%3Ccircle cx='21.5' cy='106.1' r='1.5' fill-opacity='0.75'/%3E%3Ccircle cx='183.3' cy='117.0' r='0.6' fill-opacity='0.4'/%3E%3Ccircle cx='193.0' cy='17.1' r='0.6' fill-opacity='0.4'/%3E%3Ccircle cx='127.8' cy='164.0' r='0.8' fill-opacity='0.75'/%3E%3Ccircle cx='37.1' cy='123.9' r='1.5' fill-opacity='0.75'/%3E%3Ccircle cx='225.2' cy='118.2' r='0.6' fill-opacity='0.4'/%3E%3Ccircle cx='105.7' cy='133.9' r='1.5' fill-opacity='0.4'/%3E%3Ccircle cx='125.4' cy='201.1' r='1.5' fill-opacity='0.55'/%3E%3Ccircle cx='75.6' cy='92.0' r='1.5' fill-opacity='0.4'/%3E%3Ccircle cx='73.9' cy='35.3' r='1.5' fill-opacity='1'/%3E%3Ccircle cx='66.4' cy='119.4' r='1.2' fill-opacity='1'/%3E%3Ccircle cx='29.0' cy='3.2' r='1.2' fill-opacity='0.25'/%3E%3Ccircle cx='129.0' cy='12.4' r='1.2' fill-opacity='1'/%3E%3Ccircle cx='191.1' cy='134.8' r='1.2' fill-opacity='0.25'/%3E%3Ccircle cx='165.1' cy='17.6' r='1.5' fill-opacity='0.75'/%3E%3Ccircle cx='99.7' cy='227.8' r='1.2' fill-opacity='0.55'/%3E%3Ccircle cx='60.1' cy='118.4' r='1' fill-opacity='0.75'/%3E%3Ccircle cx='214.6' cy='222.8' r='1.2' fill-opacity='1'/%3E%3Ccircle cx='76.9' cy='47.2' r='1.5' fill-opacity='0.25'/%3E%3Ccircle cx='220.4' cy='32.6' r='0.6' fill-opacity='0.25'/%3E%3Ccircle cx='47.8' cy='55.6' r='1' fill-opacity='0.55'/%3E%3Ccircle cx='172.8' cy='59.7' r='1.2' fill-opacity='0.25'/%3E%3Ccircle cx='119.9' cy='139.4' r='1.5' fill-opacity='1'/%3E%3Ccircle cx='61.1' cy='48.7' r='1.5' fill-opacity='0.75'/%3E%3Ccircle cx='7.5' cy='151.4' r='1.5' fill-opacity='1'/%3E%3Ccircle cx='39.7' cy='50.2' r='1.5' fill-opacity='0.4'/%3E%3Ccircle cx='127.0' cy='202.9' r='1.5' fill-opacity='1'/%3E%3Ccircle cx='204.2' cy='56.9' r='1' fill-opacity='0.4'/%3E%3Ccircle cx='76.5' cy='76.3' r='0.8' fill-opacity='0.4'/%3E%3Ccircle cx='185.7' cy='47.9' r='0.6' fill-opacity='0.4'/%3E%3Ccircle cx='211.8' cy='33.3' r='0.6' fill-opacity='0.55'/%3E%3Ccircle cx='93.5' cy='104.6' r='1.2' fill-opacity='1'/%3E%3Ccircle cx='188.4' cy='31.7' r='1.2' fill-opacity='0.25'/%3E%3Ccircle cx='24.7' cy='136.5' r='1' fill-opacity='0.55'/%3E%3Ccircle cx='29.2' cy='121.3' r='1' fill-opacity='1'/%3E%3Ccircle cx='237.7' cy='198.6' r='0.6' fill-opacity='0.75'/%3E%3Ccircle cx='27.1' cy='10.8' r='1.5' fill-opacity='1'/%3E%3Ccircle cx='123.5' cy='136.2' r='0.8' fill-opacity='0.4'/%3E%3Ccircle cx='45.6' cy='50.1' r='0.8' fill-opacity='0.55'/%3E%3Ccircle cx='220.7' cy='24.5' r='0.6' fill-opacity='0.4'/%3E%3Ccircle cx='226.6' cy='111.0' r='0.6' fill-opacity='0.55'/%3E%3Ccircle cx='94.2' cy='102.6' r='1' fill-opacity='0.75'/%3E%3Ccircle cx='51.6' cy='90.1' r='0.6' fill-opacity='0.4'/%3E%3Ccircle cx='44.8' cy='109.1' r='1' fill-opacity='0.75'/%3E%3Ccircle cx='219.6' cy='144.7' r='0.6' fill-opacity='1'/%3E%3Ccircle cx='189.0' cy='78.4' r='0.6' fill-opacity='0.75'/%3E%3Ccircle cx='136.4' cy='47.1' r='1.5' fill-opacity='0.55'/%3E%3Ccircle cx='191.9' cy='63.0' r='0.6' fill-opacity='0.4'/%3E%3Ccircle cx='194.3' cy='97.7' r='1' fill-opacity='1'/%3E%3Ccircle cx='166.0' cy='183.1' r='0.8' fill-opacity='0.75'/%3E%3Ccircle cx='50.8' cy='45.6' r='1' fill-opacity='0.55'/%3E%3Ccircle cx='112.6' cy='4.5' r='1' fill-opacity='1'/%3E%3Ccircle cx='13.7' cy='66.4' r='1' fill-opacity='0.55'/%3E%3Ccircle cx='53.0' cy='97.8' r='0.8' fill-opacity='1'/%3E%3Ccircle cx='20.1' cy='123.5' r='1.2' fill-opacity='0.4'/%3E%3Ccircle cx='167.5' cy='181.8' r='1.5' fill-opacity='0.25'/%3E%3Ccircle cx='29.1' cy='27.5' r='0.8' fill-opacity='0.55'/%3E%3Ccircle cx='106.7' cy='121.1' r='0.8' fill-opacity='0.75'/%3E%3Ccircle cx='4.5' cy='63.0' r='1' fill-opacity='0.55'/%3E%3Ccircle cx='131.8' cy='121.8' r='1.5' fill-opacity='1'/%3E%3Ccircle cx='201.7' cy='25.5' r='1.2' fill-opacity='0.25'/%3E%3Ccircle cx='131.7' cy='159.7' r='0.6' fill-opacity='0.75'/%3E%3Cpath d='M214.6 40.7L215.6 44.2L219.1 45.2L215.6 46.2L214.6 49.7L213.6 46.2L210.1 45.2L213.6 44.2Z' fill-opacity='0.7'/%3E%3Cpath d='M198.2 123.7L199.5 128.0L203.7 129.2L199.5 130.4L198.2 134.7L197.0 130.4L192.7 129.2L197.0 128.0Z' fill-opacity='0.7'/%3E%3Cpath d='M104.5 114.3L105.5 117.8L109.0 118.8L105.5 119.8L104.5 123.3L103.5 119.8L100.0 118.8L103.5 117.8Z' fill-opacity='1'/%3E%3Cpath d='M97.7 73.2L98.9 77.5L103.2 78.7L98.9 79.9L97.7 84.2L96.5 79.9L92.2 78.7L96.5 77.5Z' fill-opacity='0.85'/%3E%3Cpath d='M116.3 64.8L117.3 68.4L120.8 69.3L117.3 70.3L116.3 73.8L115.3 70.3L111.8 69.3L115.3 68.4Z' fill-opacity='1'/%3E%3Cpath d='M167.7 71.6L168.4 74.4L171.2 75.1L168.4 75.9L167.7 78.6L166.9 75.9L164.2 75.1L166.9 74.4Z' fill-opacity='0.7'/%3E%3C/svg%3E"
GLIT_B = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='380' height='380'%3E%3Ccircle cx='222.3' cy='240.0' r='2' fill-opacity='1'/%3E%3Ccircle cx='148.6' cy='339.5' r='2.4' fill-opacity='0.85'/%3E%3Ccircle cx='20.9' cy='373.8' r='2' fill-opacity='0.6'/%3E%3Ccircle cx='301.9' cy='86.1' r='2.4' fill-opacity='0.85'/%3E%3Ccircle cx='96.3' cy='286.1' r='1.6' fill-opacity='1'/%3E%3Ccircle cx='39.0' cy='306.6' r='2' fill-opacity='0.6'/%3E%3Ccircle cx='370.0' cy='309.1' r='2.4' fill-opacity='1'/%3E%3Ccircle cx='45.3' cy='236.7' r='2' fill-opacity='0.6'/%3E%3Ccircle cx='78.6' cy='21.6' r='2.4' fill-opacity='0.6'/%3E%3Ccircle cx='48.7' cy='168.5' r='2.4' fill-opacity='0.85'/%3E%3Ccircle cx='173.3' cy='100.6' r='2.4' fill-opacity='1'/%3E%3Ccircle cx='159.7' cy='294.5' r='2.4' fill-opacity='0.6'/%3E%3Ccircle cx='360.2' cy='278.1' r='1.6' fill-opacity='0.85'/%3E%3Ccircle cx='44.8' cy='337.7' r='2.4' fill-opacity='1'/%3E%3Ccircle cx='320.3' cy='105.3' r='2.4' fill-opacity='1'/%3E%3Ccircle cx='274.6' cy='264.8' r='1.6' fill-opacity='1'/%3E%3Ccircle cx='106.8' cy='92.0' r='1.6' fill-opacity='1'/%3E%3Ccircle cx='370.4' cy='346.3' r='2.4' fill-opacity='0.6'/%3E%3Ccircle cx='238.3' cy='5.6' r='2' fill-opacity='0.85'/%3E%3Ccircle cx='12.1' cy='16.3' r='1.6' fill-opacity='1'/%3E%3Ccircle cx='106.6' cy='286.2' r='2.4' fill-opacity='0.6'/%3E%3Ccircle cx='209.0' cy='239.3' r='2' fill-opacity='0.85'/%3E%3Cpath d='M182.3 75.8L184.5 83.6L192.3 85.8L184.5 88.0L182.3 95.8L180.1 88.0L172.3 85.8L180.1 83.6Z' fill-opacity='0.85'/%3E%3Cpath d='M278.1 305.9L279.5 310.6L284.1 311.9L279.5 313.2L278.1 317.9L276.8 313.2L272.1 311.9L276.8 310.6Z' fill-opacity='0.7'/%3E%3Cpath d='M171.0 297.9L172.8 304.2L179.0 305.9L172.8 307.7L171.0 313.9L169.3 307.7L163.0 305.9L169.3 304.2Z' fill-opacity='0.85'/%3E%3Cpath d='M162.8 94.9L164.5 101.1L170.8 102.9L164.5 104.7L162.8 110.9L161.0 104.7L154.8 102.9L161.0 101.1Z' fill-opacity='0.85'/%3E%3Cpath d='M65.2 301.1L67.4 308.9L75.2 311.1L67.4 313.3L65.2 321.1L63.0 313.3L55.2 311.1L63.0 308.9Z' fill-opacity='0.85'/%3E%3Cpath d='M207.5 270.6L209.3 276.8L215.5 278.6L209.3 280.4L207.5 286.6L205.7 280.4L199.5 278.6L205.7 276.8Z' fill-opacity='0.85'/%3E%3Cpath d='M245.4 206.0L248.2 216.2L258.4 219.0L248.2 221.9L245.4 232.0L242.5 221.9L232.4 219.0L242.5 216.2Z' fill-opacity='0.85'/%3E%3Cpath d='M38.3 26.9L41.1 37.0L51.3 39.9L41.1 42.7L38.3 52.9L35.4 42.7L25.3 39.9L35.4 37.0Z' fill-opacity='1'/%3E%3Cpath d='M176.9 300.5L178.2 305.1L182.9 306.5L178.2 307.8L176.9 312.5L175.5 307.8L170.9 306.5L175.5 305.1Z' fill-opacity='0.7'/%3E%3Cpath d='M121.7 331.8L123.0 336.5L127.7 337.8L123.0 339.2L121.7 343.8L120.3 339.2L115.7 337.8L120.3 336.5Z' fill-opacity='1'/%3E%3Cpath d='M119.4 261.0L121.6 268.8L129.4 271.0L121.6 273.2L119.4 281.0L117.2 273.2L109.4 271.0L117.2 268.8Z' fill-opacity='0.85'/%3E%3C/svg%3E"

CSS = """
:root{--page:#050507;--bg:#0A0A0E;--panel:#111117;--card:#17171F;--card2:#21212B;--line:#2A2A36;--line2:#3C3C4C;
--ink:#F7F1F8;--muted:#BDB2C6;--dim:#857A90;--outline:#000;--teal:#FF4FB0;--teal2:#FF7DC6;--teal-d:#9E1F64;--on-teal:#1B0011;
--pink:#39C5BB;--gold:#FFE45C;--bad:#FF5468;--chrome:#C9C9CF;--chrome-d:#6F6F7A;--glit:#FF6FBF;--paper:#F2F1F5;--paper-dot:#C8C5D0;
--wt2:#9D4DFF;--f-ui:"Chakra Petch","IBM Plex Sans Thai",sans-serif;--f-px:"VT323","Chakra Petch",monospace;--side:204px;--rail:300px}
*{box-sizing:border-box}
[hidden]{display:none!important}
.sr{position:absolute!important;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;margin:-1px}
html{color-scheme:dark;scroll-padding-top:80px}
body{margin:0;min-height:100vh;color:var(--ink);font:15px/1.6 "IBM Plex Sans Thai","Chakra Petch",system-ui,sans-serif;
background:radial-gradient(1100px 650px at 8% -8%,color-mix(in srgb,var(--glit) 26%,transparent),transparent 62%) fixed,
radial-gradient(900px 620px at 104% 106%,color-mix(in srgb,var(--glit) 18%,transparent),transparent 62%) fixed,var(--page)}
button,input,select,textarea{font:inherit;color:inherit}
a{color:var(--teal2)}
:focus-visible{outline:3px solid var(--gold);outline-offset:2px}
.c0{background:#2BB8AE}.c1{background:#FF4FB0}.c2{background:#F5C431}.c3{background:#8B63FF}.c4{background:#FF8A3D}
.c5{background:#F0453F}.c6{background:#39B34A}
img.ck{display:inline-block;vertical-align:middle;flex-shrink:0;filter:drop-shadow(0 1px 0 rgba(0,0,0,.6))}
svg.px{flex-shrink:0;display:inline-block;vertical-align:middle}
.k{font:20px/1 var(--f-px);color:var(--teal);letter-spacing:.04em}
/* เลื่อม */
.glit{position:fixed;inset:0;z-index:0;pointer-events:none;--ga:url("__GLIT_A__");--gb:url("__GLIT_B__")}
.glit::before,.glit::after{content:"";position:absolute;inset:0;background:var(--glit);
-webkit-mask:var(--ga) 0 0/240px 240px repeat;mask:var(--ga) 0 0/240px 240px repeat;opacity:.9}
.glit::after{-webkit-mask:var(--gb) 90px 40px/380px 380px repeat;mask:var(--gb) 90px 40px/380px 380px repeat;
animation:tw 2.8s ease-in-out infinite alternate}
@keyframes tw{from{opacity:.3}to{opacity:1}}
.dbg{position:fixed;inset:0;z-index:0;background:center/cover no-repeat;pointer-events:none}
.dcorner{position:fixed;bottom:0;z-index:4;pointer-events:none;max-height:30vh;max-width:18vw;object-fit:contain}
.dcorner.l{left:0;object-position:left bottom}.dcorner.r{right:0;object-position:right bottom}
/* หน้าต่าง Win95 */
.win{position:relative;background:var(--panel);border:3px solid var(--chrome);box-shadow:inset 3px 3px 0 #000,0 0 0 1px #000,6px 6px 0 rgba(0,0,0,.55)}
.wt{display:flex;align-items:center;gap:8px;min-height:32px;padding:3px 5px 3px 9px;background:linear-gradient(90deg,var(--teal),var(--wt2));
color:#fff;font:21px/1 var(--f-px);letter-spacing:.02em;white-space:nowrap;overflow:hidden}
.wt .tt{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis}
.wb{display:flex;gap:3px;flex-shrink:0}
.wb i{width:21px;height:19px;display:grid;place-items:center;background:var(--chrome);color:#000;font:17px/1 var(--f-px);font-style:normal;
box-shadow:inset -2px -2px 0 var(--chrome-d),inset 2px 2px 0 #fff}
.wc{padding:16px}
.wb .wx{width:24px;height:22px;display:grid;place-items:center;border:0;padding:0;background:var(--chrome);color:#000;cursor:pointer;
font:20px/1 var(--f-px);box-shadow:inset -2px -2px 0 var(--chrome-d),inset 2px 2px 0 #fff}
.wb .wx:active{box-shadow:inset 2px 2px 0 var(--chrome-d),inset -2px -2px 0 #fff}
.paper{background:var(--paper) radial-gradient(var(--paper-dot) 1.2px,transparent 1.7px) 0 0/14px 14px;color:#111}
/* กรอบหลัก */
.frame{position:relative;z-index:2;max-width:1560px;margin:0 auto;display:grid;grid-template-columns:var(--side) minmax(0,1fr)}
/* แถบซ้าย */
.side{position:sticky;top:0;align-self:start;height:100vh;overflow:auto;display:flex;flex-direction:column;gap:14px;
padding:14px 10px;background:rgba(6,6,9,.82);border-right:2px solid var(--line);scrollbar-width:thin}
.slot{position:relative}
.logo{display:flex;align-items:center;justify-content:center;gap:10px;min-height:70px;text-decoration:none;color:var(--ink);
font:700 22px/1.1 var(--f-ui);text-align:center}
.logo img{width:100%;max-width:178px;height:auto;display:block;filter:drop-shadow(0 4px 0 rgba(0,0,0,.5))}
.logo img:hover{transform:rotate(-2deg)}
.qtiles{display:flex;flex-wrap:wrap;justify-content:center;gap:18px;margin:20px 0 4px}
.qtiles>.slot{width:calc((100% - 54px)/4)}
.qtile{position:relative;display:block;text-decoration:none;color:var(--ink);transition:transform .15s}
.qtile:hover{transform:rotate(-2deg) scale(1.03)}
.qtile img{display:block;width:100%;height:auto;filter:drop-shadow(4px 4px 0 rgba(0,0,0,.55))}
.qtile.plain{border:3px solid var(--chrome);box-shadow:inset 3px 3px 0 #000,4px 4px 0 rgba(0,0,0,.55)}
.qtile.plain .im{aspect-ratio:1/1;display:grid;place-items:center;color:#2b2233}
.qtile.plain b{display:block;text-align:center;font:24px/1 var(--f-px);font-weight:400;padding:4px 4px 6px;color:var(--teal);background:var(--paper)}
.slab{font:19px/1 var(--f-px);color:var(--teal);padding:0 8px;margin:4px 0 -6px;letter-spacing:.04em}
.snav{display:grid;gap:2px}
.snav a{display:flex;align-items:center;gap:8px;padding:6px 8px;color:var(--muted);text-decoration:none;font:600 14.5px var(--f-ui);
border:2px solid transparent;min-width:0}
.snav a span{flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.snav a small{font:18px/1 var(--f-px);color:var(--dim)}
.snav a:hover{color:var(--ink);background:var(--card);border-color:var(--line2)}
.snav a.on{color:var(--on-teal);background:var(--teal);border-color:#000}
.snav a.on small{color:var(--on-teal)}
.sdiv{height:2px;background:var(--line);margin:2px 4px}
.sfoot{margin-top:auto;display:grid;gap:8px}
.help{display:flex;align-items:center;gap:8px;padding:8px 10px;background:var(--card);border:2px solid var(--line2);color:var(--ink);
text-decoration:none;font:600 14px var(--f-ui)}
.help:hover{border-color:var(--teal)}
.sfoot small{color:var(--dim);font:16px/1.2 var(--f-px);padding:0 4px}
.mob-only{display:none!important}
.sedit{position:absolute;top:6px;right:6px;z-index:6;width:34px;height:34px;display:none;place-items:center;border:2px solid #000;
background:var(--gold);color:#000;cursor:pointer;box-shadow:inset -2px -2px 0 #8a7a00,inset 2px 2px 0 #fff}
body.editing .sedit{display:grid}
/* แถบบน */
.wrap{min-width:0;display:flex;flex-direction:column}
.topbar{position:sticky;top:0;z-index:15;display:flex;align-items:center;gap:10px;padding:12px 22px;background:rgba(6,6,9,.86);
border-bottom:2px solid var(--line);backdrop-filter:blur(6px)}
.qbtn{display:inline-flex;align-items:center;gap:8px;height:40px;padding:0 18px 0 8px;border-radius:999px;color:#22061a;text-decoration:none;
font:700 15px var(--f-ui);white-space:nowrap;background:linear-gradient(180deg,#FFC2EC,#FF5BB8 60%,#F2409F);box-shadow:inset 0 2px 0 rgba(255,255,255,.55)}
.qbtn.yl{color:#1c1800;background:linear-gradient(180deg,#FFFFC0,#FAF22A 60%,#EEE600)}
.qbtn.on{outline:3px solid #fff;outline-offset:2px}
.qbtn:hover{filter:brightness(1.07)}
.tsp{flex:1}
.round{width:42px;height:42px;display:inline-grid;place-items:center;border:2px solid var(--line2);flex-shrink:0;background:var(--card);
color:var(--ink);cursor:pointer;text-decoration:none;position:relative}
.round:hover{border-color:var(--teal);color:var(--teal2)}
.round[aria-pressed=true]{background:var(--gold);border-color:#000;color:#000}
.round .nb{position:absolute;top:-8px;right:-8px;min-width:22px;height:22px;padding:0 5px;background:var(--teal);color:#fff;
border:2px solid #000;font:18px/18px var(--f-px);text-align:center}
.pill{display:inline-flex;align-items:center;gap:7px;height:42px;padding:0 14px 0 8px;background:#000;border:2px solid var(--teal);
font:26px/1 var(--f-px);white-space:nowrap;box-shadow:0 0 14px color-mix(in srgb,var(--teal) 40%,transparent)}
.who{display:flex;align-items:center;gap:10px;min-width:0}
.who span{display:flex;flex-direction:column;line-height:1.15;min-width:0}
.who b{font:700 14.5px var(--f-ui);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:150px}
.who small{color:var(--teal);font:16px/1 var(--f-px)}
.avatar{width:42px;height:42px;border:2px solid var(--chrome);background:var(--card2);object-fit:cover;flex-shrink:0;image-rendering:auto}
.login{display:inline-flex;align-items:center;gap:8px;height:42px;padding:0 20px;border-radius:999px;color:#0b0f2a;text-decoration:none;
font:700 15px var(--f-ui);white-space:nowrap;background:linear-gradient(180deg,#B3BDFF,#6474F7 60%,#5566EE);box-shadow:inset 0 2px 0 rgba(255,255,255,.5)}
.login:hover{filter:brightness(1.07)}
#sideBtn{display:none}
.notice{display:flex;align-items:center;gap:10px;margin:14px 22px 0;padding:10px 14px;background:var(--card);border:2px solid var(--line2);
border-left:8px solid var(--bad);font-size:14.5px}
.notice.ann{border-left-color:var(--teal);background:color-mix(in srgb,var(--teal) 12%,var(--card))}
.notice a{color:inherit;font-weight:600}
/* เนื้อหา + แถบขวา */
.content{display:grid;grid-template-columns:minmax(0,1fr) var(--rail);gap:24px;padding:20px 22px 30px;align-items:start}
.content.norail{grid-template-columns:minmax(0,1fr)}
.main{min-width:0}
.rail{display:grid;gap:18px;position:sticky;top:84px}
.card{background:var(--panel);border:2px solid var(--line2)}
footer{text-align:center;color:var(--dim);font:17px var(--f-px);padding:0 16px 22px;position:relative;z-index:2}
/* แบนเนอร์ */
.herowin{margin-bottom:6px}.herowin .hbox{padding:0}
.hero{position:relative;aspect-ratio:2/1;overflow:hidden;background:#000}
.slide{position:absolute;inset:0;display:flex;align-items:center;opacity:0;visibility:hidden;transition:opacity .45s,visibility .45s}
.slide.on{opacity:1;visibility:visible}
.slide .bgimg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:50% 45%}
.slide .pat{position:absolute;inset:0;opacity:.2;background-image:radial-gradient(#000 2px,transparent 2.4px);background-size:22px 22px}
.slide .cover-link{position:absolute;inset:0;z-index:2}
.slide .art{position:absolute;right:3%;bottom:0;height:92%;max-width:50%;display:flex;align-items:flex-end;justify-content:flex-end;z-index:1}
.slide .art img{max-height:100%;max-width:100%;object-fit:contain;display:block;filter:drop-shadow(6px 6px 0 rgba(0,0,0,.4))}
.slide .txt{position:relative;z-index:3;max-width:56%;padding:30px 0 30px 38px;color:#fff;pointer-events:none}
.slide .txt a{pointer-events:auto}
.slide h1,.slide h2{margin:0;font:italic 700 clamp(30px,3.6vw,56px)/1.02 var(--f-ui);text-transform:uppercase;
text-shadow:3px 3px 0 #000,-1px -1px 0 #000;overflow-wrap:anywhere}
.slide p{margin:12px 0 0;font-size:16.5px;max-width:44ch;text-shadow:0 2px 0 rgba(0,0,0,.6)}
.slide .go{margin-top:20px}
.dots{position:absolute;right:16px;bottom:14px;z-index:4;display:flex;gap:6px}
.dots button{width:14px;height:14px;border:2px solid #000;background:var(--chrome);padding:0;cursor:pointer;box-shadow:inset -2px -2px 0 var(--chrome-d)}
.dots button[aria-current=true]{width:34px;background:var(--teal)}
.herowin .sedit{top:44px;right:12px}
.ccards .sedit{top:36px;right:8px}
/* หัวข้อส่วน */
.sech{display:flex;align-items:flex-end;gap:12px;margin:30px 0 14px}
.sech h2{margin:0;font:700 26px/1.1 var(--f-ui);display:flex;flex-direction:column;gap:2px}
.sech h2 .k{font-size:20px}
.sech .sp{flex:1}
.arrow{width:38px;height:36px;display:grid;place-items:center;border:0;background:var(--chrome);color:#000;cursor:pointer;
box-shadow:inset -2px -2px 0 var(--chrome-d),inset 2px 2px 0 #fff}
.arrow:active{box-shadow:inset 2px 2px 0 var(--chrome-d),inset -2px -2px 0 #fff}
.chipbtn{display:inline-flex;align-items:center;height:36px;padding:0 16px;border-radius:999px;color:#111;font:700 14px var(--f-ui);
cursor:pointer;text-decoration:none;background:linear-gradient(180deg,#F7F7FA,#BFBFC9);box-shadow:inset 0 2px 0 rgba(255,255,255,.6)}
/* การ์ดหมวดใหญ่ */
.ccards{display:grid;grid-auto-flow:column;grid-auto-columns:calc((100% - 54px)/4);gap:18px;overflow-x:auto;scroll-snap-type:x mandatory;
scrollbar-width:none;padding:2px 8px 10px 2px}
.ccards::-webkit-scrollbar{display:none}
.ccard{display:flex;flex-direction:column;text-decoration:none;color:var(--ink);cursor:pointer;scroll-snap-align:start;transition:transform .15s}
.ccard:hover{transform:translateY(-3px) rotate(-.6deg)}
.ccard .wt{font-size:19px;min-height:28px}
.ccard .paper{position:relative;aspect-ratio:1/1;display:grid;place-items:center;overflow:hidden}
.cv-img{width:100%;height:100%;object-fit:contain;padding:7%}
.cv-stk{max-width:88%;max-height:62%;object-fit:contain;transform:rotate(-4deg);filter:drop-shadow(3px 4px 0 rgba(0,0,0,.15))}
.stk{display:inline-flex;align-items:center;gap:6px;max-width:88%;padding:6px 14px 8px;font:italic 700 24px/1 var(--f-ui);color:#fff;
border:4px solid #fff;border-radius:8px;transform:rotate(-5deg) skewX(-6deg);box-shadow:4px 5px 0 rgba(0,0,0,.18);text-align:center;
text-transform:uppercase;overflow-wrap:anywhere;text-shadow:2px 2px 0 rgba(0,0,0,.25)}
.stk svg.px{color:#fff}
.ccard .cnt{position:absolute;top:8px;left:8px;padding:0 8px;background:#000;color:var(--gold);font:18px/22px var(--f-px)}
.ccard .lbl{display:flex;align-items:center;gap:8px;padding:8px 8px 8px 12px;background:var(--panel);border-top:3px solid #000}
.ccard .lbl b{flex:1;min-width:0;font:700 16px/1.2 var(--f-ui);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ccard .lbl i{width:34px;height:30px;border-radius:999px;display:grid;place-items:center;color:#22061a;
background:linear-gradient(180deg,#FFC2EC,#FF5BB8 60%,#F2409F)}
/* มาใหม่ */
.feat{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}
.fcard{display:flex;gap:12px;padding:10px;background:var(--card);border:2px solid var(--line2);cursor:pointer;min-width:0;text-align:left;
color:var(--ink);box-shadow:4px 4px 0 rgba(0,0,0,.5)}
.fcard:hover{border-color:var(--teal)}
.fcard .im{width:88px;height:88px;flex-shrink:0;display:grid;place-items:center;overflow:hidden;border:2px solid #000;color:#8E8499}
.fcard .im img{width:100%;height:100%;object-fit:contain;padding:6px}
.fcard .bd{min-width:0;display:flex;flex-direction:column;gap:2px}
.fcard .k{font-size:17px}
.fcard b{font:700 16px/1.25 var(--f-ui);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.fcard small{color:var(--muted);font-size:13px;display:-webkit-box;-webkit-line-clamp:1;-webkit-box-orient:vertical;overflow:hidden}
.fcard .pr{margin-top:auto;display:flex;align-items:center;gap:6px;font:28px/1 var(--f-px)}
/* ค้นหา + ตัวกรอง */
.search{display:flex;align-items:center;gap:10px;padding:0 10px 0 14px;height:50px;background:#0D0D12;border:2px solid var(--line2)}
.search:focus-within{border-color:var(--teal);box-shadow:0 0 0 3px color-mix(in srgb,var(--teal) 30%,transparent)}
.search svg{color:var(--teal);flex-shrink:0}
.search input{flex:1;min-width:0;border:0;background:none;outline:0;font-size:16px;height:100%}
.search kbd{font:18px/1 var(--f-px);color:var(--dim);border:2px solid var(--line2);padding:2px 8px}
.tools{display:flex;gap:10px;align-items:center}
.tools .search{flex:1;min-width:0}
.tools .round{width:50px;height:50px}
.filters{margin-top:12px;padding:14px 16px;display:grid;gap:12px}
.frow{display:flex;flex-wrap:wrap;align-items:center;gap:10px 12px}
.flab{color:var(--teal);font:19px/1 var(--f-px);min-width:60px}
.range{display:flex;align-items:center;gap:8px}
.range input,.sel{width:110px;height:38px;padding:0 12px;border:2px solid var(--line2);background:#0D0D12}
.sel{width:auto;min-width:190px;cursor:pointer}
.range input:focus,.sel:focus,.fld input:focus,.fld textarea:focus,.ing:focus{outline:0;border-color:var(--teal)}
.tog{display:inline-flex;align-items:center;gap:7px;height:36px;padding:0 14px 0 10px;border:2px solid var(--line2);background:#0D0D12;
color:var(--muted);cursor:pointer;font:600 14px var(--f-ui)}
.tog:hover{color:var(--ink);border-color:var(--teal)}
.tog[aria-pressed=true]{background:var(--teal);border-color:#000;color:var(--on-teal)}
.seg{display:inline-flex;flex-wrap:wrap;border:2px solid var(--line2);background:#0D0D12}
.seg button{border:0;background:none;color:var(--muted);height:32px;padding:0 13px;cursor:pointer;font:600 14px var(--f-ui)}
.seg button[aria-pressed=true]{background:var(--teal);color:var(--on-teal)}
.linkbtn{border:0;background:none;color:var(--teal2);cursor:pointer;font-size:14px;padding:4px 2px;text-decoration:underline;
text-underline-offset:3px}
.resbar{display:flex;align-items:center;justify-content:space-between;gap:10px;margin:14px 2px 12px;color:var(--muted);
font:19px/1.2 var(--f-px);flex-wrap:wrap}
.resbar b{color:var(--teal2);font-weight:400}
.active{display:flex;flex-wrap:wrap;gap:6px}
.active button{border:2px solid var(--line2);background:var(--card);color:var(--ink);font:13px var(--f-ui);padding:2px 10px;cursor:pointer}
.active button:after{content:" ×";color:var(--teal)}
/* การ์ดของ */
.grid{display:grid;gap:16px;grid-template-columns:repeat(auto-fill,minmax(200px,1fr))}
.item{position:relative;display:flex;flex-direction:column;overflow:hidden;background:var(--card);border:2px solid var(--line2);cursor:pointer;
box-shadow:4px 4px 0 rgba(0,0,0,.5);transition:transform .12s}
.item:hover{border-color:var(--teal);transform:translateY(-2px)}
.item.in{border-color:var(--teal);box-shadow:0 0 0 2px var(--teal),4px 4px 0 rgba(0,0,0,.5)}
.item.off{opacity:.5}
.pic{position:relative;aspect-ratio:4/3;display:grid;place-items:center;border-bottom:3px solid #000;color:#8E8499;
background:var(--paper) radial-gradient(var(--paper-dot) 1.2px,transparent 1.7px) 0 0/14px 14px}
.pic img{width:100%;height:100%;object-fit:contain;padding:12px}
.badge{position:absolute;top:8px;left:8px;padding:0 8px;font:19px/24px var(--f-px);background:#000;color:#fff;border:2px solid #fff}
.badge.hot{background:var(--bad)}
.badge.soon{background:var(--gold);color:#000;border-color:#000}
.badge.hide{left:auto;right:52px;background:var(--chrome);color:#000;border-color:#000}
.ebtn{position:absolute;top:8px;right:8px;width:38px;height:38px;display:none;place-items:center;border:2px solid #000;background:var(--gold);
color:#000;cursor:pointer;z-index:2;box-shadow:inset -2px -2px 0 #8a7a00,inset 2px 2px 0 #fff}
body.editing .ebtn{display:grid}
.body{padding:10px 14px 8px;display:flex;flex-direction:column;gap:5px;flex:1}
.cat{align-self:flex-start;font:18px/1 var(--f-px);color:var(--teal);letter-spacing:.03em}
.item h2{margin:0;font:700 17px/1.3 var(--f-ui)}
.desc{margin:0;color:var(--muted);font-size:13.5px;white-space:pre-line;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;
overflow:hidden}
.meta{display:flex;flex-wrap:wrap;gap:5px;margin-top:auto;padding-top:6px}
.meta span{display:inline-flex;align-items:center;gap:4px;font-size:12px;background:var(--card2);padding:1px 8px 1px 6px;color:var(--muted);
border:1px solid var(--line2)}
.meta span svg.px{color:var(--teal)}
.price{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:8px 12px 12px 14px;min-height:60px}
.price b,.money{display:inline-flex;align-items:center;gap:6px;white-space:nowrap}
.price b{font:34px/1 var(--f-px);font-weight:400;color:#fff;text-shadow:0 0 12px color-mix(in srgb,var(--teal) 55%,transparent)}
.buy{display:flex;justify-content:flex-end}
/* ปุ่มเม็ดยา (ตามชุด asset) */
.btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;height:40px;padding:0 20px;border:0;border-radius:999px;
font:700 15px var(--f-ui);color:#08240c;cursor:pointer;text-decoration:none;white-space:nowrap;
background:linear-gradient(180deg,#C2FFBC,#45E856 58%,#24CF3A);box-shadow:inset 0 2px 0 rgba(255,255,255,.55),0 3px 0 rgba(0,0,0,.45)}
.btn:hover{filter:brightness(1.08)}
.btn:active{transform:translateY(1px);box-shadow:inset 0 2px 0 rgba(255,255,255,.4)}
.btn[disabled]{background:#34343E;color:#8F87A0;box-shadow:none;cursor:not-allowed;filter:none;transform:none}
.btn.alt{color:#111;background:linear-gradient(180deg,#FAFAFC,#BFBFC9)}
.btn.danger{color:#2a0505;background:linear-gradient(180deg,#FFA4A4,#F04343 60%,#E22B2B)}
.btn.yl{color:#1c1800;background:linear-gradient(180deg,#FFFFC0,#FAF22A 60%,#EEE600)}
.btn.bl{color:#0b0f2a;background:linear-gradient(180deg,#B3BDFF,#6474F7 60%,#5566EE)}
.btn.pk{color:#26001d;background:linear-gradient(180deg,#FFC4FF,#F658EF 60%,#EB3EE3)}
.btn.big{height:50px;padding:0 24px;font-size:18px}
.btn.sm{height:34px;padding:0 14px;font-size:14px}
.step{display:inline-flex;align-items:center;border-radius:999px;overflow:hidden;background:linear-gradient(180deg,#C2FFBC,#45E856 58%,#24CF3A);
box-shadow:inset 0 2px 0 rgba(255,255,255,.5)}
.step button{width:36px;height:36px;border:0;background:none;color:#08240c;font:26px/1 var(--f-px);cursor:pointer}
.step button[disabled]{opacity:.35;cursor:not-allowed}
.step output{min-width:30px;text-align:center;font:26px/36px var(--f-px);color:#08240c;background:rgba(255,255,255,.35);height:36px}
.empty{grid-column:1/-1;text-align:center;color:var(--muted);padding:40px 10px}
.empty img{display:inline-block;margin-bottom:6px}
.grid.list{grid-template-columns:1fr}
.grid.list .item{flex-direction:row;align-items:stretch}
.grid.list .pic{width:150px;aspect-ratio:auto;flex-shrink:0;border-bottom:0;border-right:3px solid #000}
.grid.list .body{padding:12px 16px}
.grid.list .price{border-left:2px dashed var(--line2);flex-direction:column;justify-content:center;min-width:170px}
.qb{position:absolute;top:8px;right:8px;min-width:32px;height:30px;padding:0 6px;background:var(--teal);color:#fff;border:2px solid #000;
font:22px/26px var(--f-px);text-align:center}
body.editing .qb{right:52px}
/* หน้าหมวด */
.cathead{margin-bottom:22px}
.cathead .wc{display:grid;grid-template-columns:190px minmax(0,1fr);gap:20px}
.cathead .cover{aspect-ratio:1/1;display:grid;place-items:center;overflow:hidden;border:3px solid #000}
.cathead .cover .stk{font-size:30px}
.back{display:inline-flex;align-items:center;gap:6px;border:0;background:none;color:var(--teal2);cursor:pointer;padding:0 0 6px;
font:20px var(--f-px)}
.back:hover{color:#fff}
.cathead h1{margin:0;font:italic 700 40px/1.05 var(--f-ui);text-transform:uppercase}
.cathead .ct{color:var(--muted);font:19px var(--f-px);margin:2px 0 10px}
.cdesc{display:grid;gap:8px;font-size:14.5px}
.cdesc p{margin:0}
.cdesc .warn,.cdesc .info{padding:7px 11px;border:2px solid #000;font-weight:600}
.cdesc .warn{background:var(--bad);color:#fff}
.cdesc .info{background:var(--teal);color:var(--on-teal)}
.cdesc .soft{color:var(--muted)}
.typebox h3,.pick{margin:0 0 12px;font:700 22px var(--f-ui)}
.types{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;margin-bottom:20px}
.type{display:flex;align-items:center;justify-content:center;gap:8px;min-height:46px;padding:6px 12px;background:var(--card);
border:2px solid var(--line2);color:var(--ink);cursor:pointer;font:600 14.5px var(--f-ui)}
.type svg.px{color:var(--teal)}
.type:hover{border-color:var(--teal)}
.type[aria-pressed=true]{background:var(--teal);border-color:#000;color:var(--on-teal)}
.type[aria-pressed=true] svg.px{color:var(--on-teal)}
body.catmode .homeonly,body:not(.catmode) .catonly{display:none!important}
body.catmode .grid{grid-template-columns:repeat(auto-fill,minmax(165px,1fr))}
body.catmode .item{text-align:center}
body.catmode .item .pic{aspect-ratio:1/1}
body.catmode .item .body{padding:8px 10px 0;align-items:center;gap:2px}
body.catmode .item .desc,body.catmode .item .meta,body.catmode .item .cat,body.catmode .item .buy{display:none}
body.catmode .item h2{font-size:15px}
body.catmode .item .price{justify-content:center;padding:4px 10px 12px;min-height:0;border:0;flex-direction:row;min-width:0}
body.catmode .grid.list .item{flex-direction:column}
body.catmode .grid.list .pic{width:auto;border-right:0;border-bottom:3px solid #000}
/* แถบขวา */
.bal{padding:2px 4px 6px}
.bal .lab{display:flex;justify-content:space-between;align-items:baseline;color:var(--muted);font-size:14px}
.bal .lab .k{font-size:20px}
.bal .lab b{font:17px var(--f-px);color:var(--dim);font-weight:400}
.bal .big{margin:6px 0 10px;font:64px/1 var(--f-px);display:flex;align-items:center;gap:12px;color:#fff;
text-shadow:0 0 18px color-mix(in srgb,var(--teal) 60%,transparent)}
.stats{display:grid;grid-template-columns:repeat(3,1fr);border-top:2px dashed var(--line2);padding-top:10px}
.stats div{display:flex;flex-direction:column}
.stats span{font-size:12.5px;color:var(--muted)}
.stats b{font:28px/1.1 var(--f-px);font-weight:400}
.spin{display:flex;align-items:center;gap:10px;margin-top:12px;padding:8px 12px;background:#000;border:2px solid var(--line2);font-size:14px}
.spin svg.px{color:var(--gold)}
.spin span{flex:1}
.spin b{font:24px/1 var(--f-px);font-weight:400;color:var(--gold)}
.spin a{font-weight:700;text-decoration:none}
.promo{position:relative;display:flex;flex-direction:column;justify-content:space-between;gap:10px;min-height:156px;padding:16px;
border:4px solid #fff;border-radius:10px;overflow:hidden;color:#fff;text-decoration:none;transform:rotate(-1.4deg);
box-shadow:5px 6px 0 rgba(0,0,0,.6);transition:transform .15s}
.rail .slot:nth-of-type(even) .promo{transform:rotate(1.2deg)}
.promo:hover{transform:rotate(0) scale(1.02)!important}
.promo .bgimg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.promo .pat{position:absolute;inset:0;opacity:.16;background-image:radial-gradient(#000 2px,transparent 2.4px);background-size:20px 20px}
.promo .art{position:absolute;right:-16px;bottom:-4px;width:54%;max-height:92%;object-fit:contain;object-position:right bottom;transform:rotate(-9deg);filter:drop-shadow(4px 4px 0 rgba(0,0,0,.35))}
.promo .tx{position:relative;z-index:1;max-width:62%}
.promo h3{margin:0;font:italic 700 28px/1 var(--f-ui);text-transform:uppercase;text-shadow:3px 3px 0 rgba(0,0,0,.35)}
.promo p{margin:6px 0 0;font-size:13.5px;font-weight:600;text-shadow:0 1px 0 rgba(0,0,0,.4)}
.promo .go{position:relative;z-index:1;align-self:flex-start;height:34px;padding:0 16px;font-size:14px}
.hist .wc{padding:10px 14px 12px}
.hist ul{list-style:none;margin:0;padding:0;max-height:330px;overflow:auto}
.hist li{display:grid;grid-template-columns:14px 1fr;gap:0 10px;padding:8px 0;border-top:2px dashed var(--line2)}
.hist li:first-child{border-top:0}
.dot{grid-row:1/3;width:12px;height:12px;margin-top:6px;border:2px solid #000;background:var(--dim)}
.dot.ok{background:#45E856;padding:0}.dot.wait{background:var(--gold)}.dot.bad{background:var(--bad)}.dot.off{background:var(--line2)}
.hist li .t{font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.hist li .s{font-size:12.5px;color:var(--muted)}
.hist .none{color:var(--dim);font-size:14px;margin:4px 0 0}
.guest .wc{text-align:center}
.guest img.mascot{width:130px;height:auto;margin:-4px auto 0;display:block;filter:drop-shadow(4px 4px 0 rgba(0,0,0,.5))}
.guest p{color:var(--muted);margin:8px 0 14px}
/* ตะกร้า (ลิ้นชักขวา · มือถือ = แผ่นเลื่อนขึ้น) */
.cart{position:fixed;top:0;right:0;bottom:0;z-index:31;width:min(420px,100vw);display:flex;flex-direction:column;background:var(--panel);
border:3px solid var(--chrome);border-right:0;box-shadow:inset 3px 3px 0 #000,-8px 0 0 rgba(0,0,0,.4);
transform:translateX(106%);transition:transform .22s,visibility .22s;visibility:hidden}
.cart.open{transform:none;visibility:visible}
.cart-head{display:flex;align-items:center;gap:10px;min-height:40px;padding:4px 6px 4px 12px;background:linear-gradient(90deg,var(--teal),var(--wt2));
color:#fff}
.cart-head h2{margin:0;font:24px/1 var(--f-px);font-weight:400;flex:1}
.cart-head .pill{height:26px;padding:0 8px;font-size:20px;background:#000;border-color:#fff;box-shadow:none}
.cart-head .x{background:var(--chrome);color:#000;width:28px;height:26px;box-shadow:inset -2px -2px 0 var(--chrome-d),inset 2px 2px 0 #fff;
font:22px/1 var(--f-px)}
.cart-scroll{overflow:auto;padding:4px 18px;flex:1;min-height:90px}
.line{display:grid;grid-template-columns:1fr auto;gap:2px 10px;padding:12px 0;border-bottom:2px dashed var(--line2)}
.line .n{font:700 15.5px var(--f-ui);display:flex;align-items:center;gap:4px;flex-wrap:wrap}
.line .p{color:var(--muted);font:18px/1.2 var(--f-px);display:flex;align-items:center;gap:4px;flex-wrap:wrap}
.line .ctl{grid-row:1/3;grid-column:2;display:flex;align-items:center;gap:4px}
.x{width:34px;height:34px;border:0;background:none;color:var(--muted);font:24px/1 var(--f-px);cursor:pointer}
.x:hover{background:var(--card2);color:var(--ink)}
.x[disabled]{opacity:.35;cursor:not-allowed}
.cart-empty{color:var(--dim);text-align:center;padding:24px 6px;font-size:14px}
.cart-empty img{display:block;margin:0 auto 8px;width:110px;height:auto}
label.ing-l{display:block;margin:14px 0 2px;font-weight:600;font-size:14px}
label.ing-l small{display:block;font-weight:400;color:var(--muted);font-size:12.5px}
.ing{width:100%;height:44px;padding:0 14px;border:2px solid var(--line2);background:#0D0D12;margin-top:6px}
.err{color:var(--bad);margin:10px 0 0;font-size:14px}
.sum{padding:12px 18px;border-top:2px solid var(--line2);display:grid;gap:4px}
.sum div{display:flex;justify-content:space-between;align-items:center}
.sum .t b{font:36px/1 var(--f-px);font-weight:400}
.sum .neg{color:var(--bad)}
.acts{display:flex;gap:10px;justify-content:flex-end;padding:6px 18px 18px;flex-wrap:wrap}
.acts .btn.big{flex:1}
.okbox{padding:12px 0}
.okbox h4{margin:0 0 4px;font:28px/1.1 var(--f-px);font-weight:400;color:#45E856}
.okbox p{margin:6px 0;display:flex;align-items:center;gap:5px;flex-wrap:wrap}
.okbox ul{list-style:none;padding:0;margin:8px 0}
.okbox li{display:grid;grid-template-columns:14px 1fr auto;gap:10px;align-items:start;padding:8px 0;border-bottom:2px dashed var(--line2);font-size:14px}
.okbox li .dot{grid-row:auto;margin-top:5px}
.okbox li span:last-child{color:var(--muted);text-align:right}
.bar{position:fixed;left:16px;right:16px;bottom:16px;z-index:20;max-width:640px;margin:0 auto;display:none;align-items:center;
justify-content:space-between;gap:12px;padding:8px 8px 8px 16px;background:#000;color:#fff;border:3px solid var(--teal);
box-shadow:0 0 18px color-mix(in srgb,var(--teal) 45%,transparent)}
.bar b{font:24px var(--f-px);font-weight:400;display:inline-flex;align-items:center;gap:4px}
.scrim{position:fixed;inset:0;z-index:29;background:rgba(0,0,0,.72)}
.toast{position:fixed;left:50%;bottom:26px;z-index:50;transform:translateX(-50%);padding:9px 16px;background:#000;color:#fff;
border:2px solid var(--teal);font:20px/1.2 var(--f-px);max-width:calc(100vw - 32px);box-shadow:4px 4px 0 rgba(0,0,0,.6)}
/* โหมดแก้ไข (แถบงานแบบ Win95) */
body:not(.editing) .adm-only{display:none!important}
body.editing .pub-only{display:none!important}
.etools{position:fixed;left:0;right:0;bottom:0;z-index:28;display:none;align-items:center;gap:6px;padding:6px 10px;background:var(--chrome);
box-shadow:inset 0 2px 0 #fff;overflow-x:auto}
body.editing .etools{display:flex}
.etools b{display:inline-flex;align-items:center;gap:6px;height:34px;padding:0 12px;font:21px/1 var(--f-px);font-weight:400;color:#fff;
white-space:nowrap;background:linear-gradient(90deg,var(--teal),var(--wt2));border:2px solid #000}
.etools button{display:inline-flex;align-items:center;gap:6px;height:34px;padding:0 12px;border:0;background:var(--chrome);color:#000;
cursor:pointer;font:700 13.5px var(--f-ui);white-space:nowrap;box-shadow:inset -2px -2px 0 var(--chrome-d),inset 2px 2px 0 #fff}
.etools button:active{box-shadow:inset 2px 2px 0 var(--chrome-d),inset -2px -2px 0 #fff}
body.editing{padding-bottom:56px}
body.editing .bar{bottom:66px}
dialog{width:min(660px,calc(100vw - 24px));max-height:calc(100vh - 32px);padding:0;border:3px solid var(--chrome);border-radius:0;
background:var(--panel);color:var(--ink);box-shadow:inset 3px 3px 0 #000,8px 8px 0 rgba(0,0,0,.6)}
dialog::backdrop{background:rgba(0,0,0,.75)}
.dlg{display:flex;flex-direction:column;max-height:calc(100vh - 38px)}
.dlg h3{margin:0;padding:6px 44px 6px 12px;font:24px/1.1 var(--f-px);font-weight:400;color:#fff;background:linear-gradient(90deg,var(--teal),var(--wt2))}
.dlg .scroll{overflow:auto;padding:14px 20px;display:grid;gap:12px;grid-template-columns:1fr 1fr}
.fld{display:flex;flex-direction:column;gap:5px;font-size:14px;color:var(--muted)}
.fld.w,.w{grid-column:1/-1}
.fld input,.fld textarea,.fld select{color:var(--ink);background:#0D0D12;border:2px solid var(--line2);padding:9px 12px;font-size:15px}
.fld textarea{min-height:76px;resize:vertical}
.fld small{color:var(--dim)}
.chk{flex-direction:row;align-items:center;gap:8px;color:var(--ink)}
.chk input{width:18px;height:18px;accent-color:var(--teal)}
.imgrow{display:flex;gap:12px;align-items:center}
.imgrow img{width:84px;height:84px;object-fit:contain;border:2px solid #000;background:var(--paper)}
.imgrow input[type=file]{flex:1;min-width:0;padding:7px;font-size:13.5px;color:var(--muted)}
.imgrow input[type=file]::file-selector-button{margin-right:10px;border:0;border-radius:999px;padding:7px 16px;font-weight:700;cursor:pointer;
color:#26001d;background:linear-gradient(180deg,#FFC4FF,#F658EF 60%,#EB3EE3)}
.swatches{display:flex;flex-wrap:wrap;gap:8px}
.swatches label{position:relative;cursor:pointer}
.swatches input{position:absolute;opacity:0;inset:0}
.swatches span{display:block;width:34px;height:34px;border:2px solid #000}
.swatches input:checked+span{box-shadow:0 0 0 3px #fff}
.swatches input:focus-visible+span{outline:3px solid var(--gold);outline-offset:2px}
.presets{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:8px}
.presets label{position:relative;display:flex;align-items:center;gap:10px;padding:8px 10px;border:2px solid var(--line2);cursor:pointer;color:var(--ink)}
.presets input{position:absolute;opacity:0}
.presets label:has(input:checked){border-color:var(--teal)}
.presets i{display:flex;width:48px;height:28px;overflow:hidden;border:2px solid #000}
.presets i b{flex:1}
.hexrow{display:flex;gap:8px;align-items:center}
.hexrow input[type=color]{width:46px;height:42px;padding:2px;border:2px solid var(--line2);background:#0D0D12}
.hexrow input[type=text]{flex:1}
.dlg .acts{border-top:2px solid var(--line2);padding-top:14px}
.dlg .acts .btn.danger{margin-right:auto}
/* รายละเอียดของ */
.idlg{position:relative}
.idtop{display:grid;grid-template-columns:160px 1fr;gap:16px;padding:18px 20px 8px}
.idpic{aspect-ratio:1/1;display:grid;place-items:center;overflow:hidden;border:3px solid #000;color:#8E8499;
background:var(--paper) radial-gradient(var(--paper-dot) 1.2px,transparent 1.7px) 0 0/14px 14px}
.idpic img{width:100%;height:100%;object-fit:contain;padding:8px}
.idpic .cv-img{padding:0;object-fit:cover}
.dlg .idinfo h3{margin:2px 0 8px;padding:0;font:700 26px/1.15 var(--f-ui);color:var(--ink);background:none}
.idprice{display:inline-flex;align-items:center;gap:8px;margin-top:10px;font:44px/1 var(--f-px);font-weight:400}
.idprice img.ck{width:34px;height:34px}
.idbody{padding:0 20px}
.idbody p{margin:0 0 10px;white-space:pre-line;color:var(--muted)}
.qty{display:flex;align-items:center;gap:10px;margin-right:auto}
.qty span{color:var(--muted);font-size:14px}
/* จอเล็กลง */
@media (max-width:1240px){.content{grid-template-columns:minmax(0,1fr)}.rail{position:static;grid-template-columns:repeat(2,minmax(0,1fr))}
.ccards{grid-auto-columns:calc((100% - 36px)/3)}}
@media (max-width:900px){.frame{grid-template-columns:1fr}
.side{position:fixed;left:0;top:0;bottom:0;z-index:41;width:236px;height:auto;background:#07070A;transform:translateX(-106%);
transition:transform .22s,visibility .22s;visibility:hidden;border-right:3px solid var(--chrome)}
.side.open{transform:none;visibility:visible}
#sideScrim{z-index:40}
#sideBtn{display:inline-grid}.topbar{padding:8px 10px;gap:8px}.qbtn span{display:none}.qbtn{padding:0 9px}
.who span{display:none}.content{padding:14px 12px 22px}.notice{margin:12px 12px 0}
.slide .txt{max-width:100%;padding:18px 18px 40px}.slide h1,.slide h2{font-size:28px}.slide p{font-size:14px;max-width:30ch}
.ccards{grid-auto-columns:calc((100% - 18px)/2.15)}.feat{grid-template-columns:1fr}
.cathead .wc{grid-template-columns:96px 1fr;gap:4px 14px}.cathead .cdesc{grid-column:1/-1}.cathead h1{font-size:28px}
.rail{grid-template-columns:1fr}.dcorner{display:none}
.qtiles{gap:14px}.qtiles>.slot{width:calc((100% - 14px)/2);max-width:220px}}
@media (max-width:620px){.grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.price{flex-direction:column;align-items:stretch}.price b{font-size:28px}.buy .btn,.buy .step{width:100%}.step{justify-content:space-between}
.dlg .scroll{grid-template-columns:1fr}.grid.list .pic{width:96px}.grid.list .price{min-width:0}.pill{padding:0 10px 0 6px;font-size:22px}
.range input{width:92px}.sel{min-width:0;width:100%}.item h2{font-size:15.5px}.bal .big{font-size:52px}
body.catmode .grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.types{grid-template-columns:1fr 1fr}.idtop{grid-template-columns:100px 1fr}.dlg .idinfo h3{font-size:21px}
.cart{top:auto;left:0;width:auto;max-height:86vh;border-right:3px solid var(--chrome);transform:translateY(106%)}
.search kbd{display:none}.wt{font-size:19px}.who,.topbar .tlogout{display:none}
.topbar{gap:6px;padding:8px}.topbar .round{width:38px;height:38px}.qbtn{height:38px;padding:0 5px}.pill{height:38px;font-size:21px;gap:4px;padding:0 8px 0 4px}.pill img.ck{width:24px;height:24px}.mob-only{display:flex!important}
.toast{bottom:auto;top:72px}}
@media (max-width:900px){body.has-cart .bar{display:flex}body.has-cart{padding-bottom:84px}}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
"""
CSS = CSS.replace("__GLIT_A__", GLIT_A).replace("__GLIT_B__", GLIT_B)
