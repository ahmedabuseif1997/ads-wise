
document.documentElement.classList.add("js");
/* ================= CONFIG ================= */
const SIGNUP_URL = "/signup";
const LOGIN_URL = "/app";
const PRIVACY_URL = "/privacy";
const CONTACT_EMAIL = "info@ads-wise.com";

const AR={"nav.how": "كيف يعمل", "nav.platform": "المنصة", "nav.control": "التحكم", "nav.privacy": "الخصوصية", "nav.login": "تسجيل الدخول", "cta.create": "أنشئ مساحة عملك", "cta.how": "شاهد كيف يعمل", "hero.tag": "نظام تشغيل التسويق بالذكاء الاصطناعي", "hero.l1": "كل إشارة.", "hero.l2": "خطوة واحدة واضحة.", "hero.sub": "مساحة عمل واحدة بالذكاء الاصطناعي للبحث وبناء الحملات واعتمادها وقياسها عبر Google وMeta وTikTok.", "hero.t1": "مساحات عمل خاصة", "hero.t2": "النشر بعد الموافقة", "hero.t3": "تحليلات عبر المنصات", "hero.scroll": "مرّر — وشاهد الضجيج يتحول إلى خطوة", "st.ey": "كيف يعمل", "st.h": "خمس مراحل. مسار واحد.", "s1.k": "الإشارة", "s1.h": "شاهد ما يحدث فعلاً.", "s1.d": "أداء الحملات وسياق نشاطك في عرض واحد — بفلاتر لأمس وهذا الأسبوع والأسبوع الماضي وآخر ٣٠ يوماً.", "s2.k": "الاستراتيجية", "s2.h": "حوّل البحث إلى اتجاه.", "s2.d": "عرضك وسوقك وموقعك وميزانيتك وصفحة الهبوط تتحول إلى جماهير ورسائل ومحتوى مقترح — مع الأدلة والافتراضات.", "s3.k": "البناء", "s3.h": "الحملات والجماهير والمحتوى — معاً.", "s3.d": "استوديو حملات موجّه: اختر جمهوراً أو ابدأ من اقتراح، ثم أضف المحتوى والتسليم والميزانية.", "s4.k": "الإطلاق", "s4.h": "تحرك بسرعة دون فقدان السيطرة.", "s4.d": "المالك يعتمد الميزانيات والنشر. تُنشأ الحملات متوقفة ليراجعها الفريق قبل أي إنفاق.", "s5.k": "التعلّم", "s5.h": "اعرف أفضل خطوة تالية.", "s5.d": "لوحة تحوّل النقرات والإنفاق والتحويلات والاتجاهات إلى قرارات قابلة للتنفيذ.", "w.f1": "أمس", "w.f2": "هذا الأسبوع", "w.f3": "الأسبوع الماضي", "w.f4": "آخر ٣٠ يوماً", "w.qi": "تفاعلاً مؤهلاً", "w.live": "إشارات مباشرة", "w.in1": "العرض", "w.in2": "السوق", "w.in3": "الموقع", "w.in4": "الميزانية", "w.in5": "صفحة الهبوط", "w.o1": "الجماهير", "w.o2": "الرسائل", "w.o3": "المحتوى", "w.ev": "الأدلة مرفقة", "w.b1": "الجمهور", "w.b2": "المحتوى الإبداعي", "w.b3": "التسليم", "w.b2d": "نص · صورة · فيديو", "w.b3d": "الميزانية · المنصة · التواريخ", "w.b1d": "مقترح أو من اختيارك", "w.camp": "الحملة جاهزة", "w.l1": "تم اعتماد الميزانية", "w.l2": "تم اعتماد النشر", "w.l3": "أُنشئت متوقفة", "w.paused": "متوقفة · بانتظار المالك", "w.appr": "جاهزة للموافقة", "w.nss": "لا إنفاق مفاجئ", "w.nbm": "أفضل خطوة تالية", "w.scale": "توسيع البحث", "w.conf": "نسبة الثقة", "w.clicks": "النقرات", "w.spend": "الإنفاق", "w.conv": "التحويلات", "pl.ey": "المنصة", "pl.h1": "مساحة عمل واحدة.", "pl.h2": "كل المنصات.", "pl.lead": "خطط واعتمد وانشر وقِس عبر أهم منصات الإعلان — دون التنقل بين التبويبات.", "pl.1": "سياق نشاطك أولاً", "pl.1d": "كل اقتراح يبدأ من عرضك وسوقك وميزانيتك.", "pl.2": "أدلة يمكنك مراجعتها", "pl.2d": "الجماهير والرسائل تصل مع أسبابها.", "pl.3": "استوديو حملات موجّه", "pl.3d": "الجمهور والمحتوى والتسليم بخطوات واضحة.", "pl.4": "قرارات لا مجرد لوحات", "pl.4d": "النقرات والإنفاق والتحويلات تتحول إلى الخطوة التالية.", "ct.ey": "التحكم", "ct.h1": "سريع.", "ct.h2": "ولا يخرج عن السيطرة.", "ct.lead": "جرّبها: لا شيء يُنشر دون موافقة، وزر واحد يوقف كل شيء.", "ct.live": "مباشر", "ct.stopped": "تم إيقاف كل النشاط", "ct.stop": "إيقاف طارئ", "ct.resume": "استئناف", "ct.log": "سجل التدقيق", "c1": "معزولة لكل نشاط", "c2": "بموافقة بشرية", "c3": "تحت الإشراف", "c4": "متوقفة افتراضياً", "c5": "اعتماد الميزانية", "c6": "صلاحيات الأدوار", "c7": "سجل التدقيق", "c8": "إيقاف طارئ", "lg1": "المالك اعتمد الميزانية", "lg2": "تم إنشاء الحملة — متوقفة", "lg3": "المحلل اطلع على الإشارات الأسبوعية", "lg4": "تم اعتماد النشر", "lg5": "تم تحديث المحتوى", "lg6": "تم استخدام الإيقاف الطارئ", "lg7": "تم استئناف النشاط", "pv.ey": "الخصوصية", "pv.h1": "منصة واحدة.", "pv.h2": "مساحات عمل خاصة.", "pv.lead": "كل نشاط في مساحة عمل مغلقة خاصة به — لا يختلط مستخدموه وحملاته واتصالاته مع أي أحد آخر.", "pv.a": "نشاط أ", "pv.b": "نشاط ب", "pv.c": "نشاط ج", "pv.1": "معزولة", "pv.1d": "مستخدمون وحملات واتصالات منفصلة لكل نشاط.", "pv.2": "بموافقة بشرية", "pv.2d": "سير موافقات حسب الأدوار.", "pv.3": "تحت الإشراف", "pv.3d": "سجل تدقيق وزر إيقاف طارئ.", "go.ey": "ابدأ الآن", "go.h1": "اجعل تسويقك", "go.h2": "حاسماً.", "go.lead": "أنشئ مساحة عملك خلال دقائق — أو أرسل بياناتك وسنرتب لك عرضاً موجّهاً.", "g1": "أنشئ مساحة عملك", "g2": "أضف سياق نشاطك", "g3": "راجع وابنِ", "g4": "اعتمد وتعلّم", "f.name": "الاسم", "f.biz": "اسم النشاط", "f.phone": "الهاتف / واتساب", "f.spend": "الإنفاق الإعلاني الشهري", "f.s1": "أقل من ١٠٬٠٠٠ درهم", "f.s2": "١٠٬٠٠٠ – ٥٠٬٠٠٠ درهم", "f.s3": "أكثر من ٥٠٬٠٠٠ درهم", "f.s4": "لم نبدأ بعد", "f.send": "اطلب عرضاً موجّهاً", "ft.tag": "عمليات تسويق بالذكاء الاصطناعي للأعمال الطموحة.", "ft.loc": "دبي، الإمارات", "demo": "عروض توضيحية للمنتج — الأرقام من معاينة adwise."};
Object.assign(AR,{"ft.head1":"حملات أوضح.","ft.head2":"نمو أهدأ.","ft.desc":"ابحث وابنِ واعتمد وقِس إعلاناتك عبر Google وMeta وTikTok.","ft.product":"المنتج","ft.studio":"استوديو الحملات","ft.analytics":"التحليلات","ft.campaigns":"الحملات","ft.access":"اطلب الوصول","ft.capabilities":"الإمكانات","ft.audience":"بحث الجمهور","ft.assets":"المحتوى الإبداعي","ft.approvals":"سير الموافقات","ft.budgets":"ضوابط الميزانية","ft.workspaces":"مساحات عمل خاصة","ft.safety":"التدقيق والأمان","ft.platforms":"المنصات","ft.cross":"تحليلات عبر المنصات","ft.uae":"مصمم للإمارات","ft.aed":"ميزانيات بالدرهم","ft.owner":"موافقات المالك","ft.languages":"حملات عربية وإنجليزية","ft.questions":"الأسئلة","ft.company":"الشركة","ft.contact":"تواصل معنا"});
Object.assign(AR,{"nav.features":"الميزات","fx.ey":"كل شيء متصل","fx.h1":"مساحة عمل","fx.h2":"تسويقية متكاملة.","fx.lead":"من ظهورك في البحث إلى اعتماد الحملات، يجمع Adwise العمل والأدلة في نظام آمن لكل نشاط.","fx.1":"استوديو الحملات","fx.1d":"خطط لحملات Google وMeta وTikTok مع الجمهور والميزانية والنص والمحتوى.","fx.2":"بحث الجمهور بالذكاء الاصطناعي","fx.2d":"اقتراح الاستهداف والمواضع والرسائل من بيانات النشاط والبحث الحالي.","fx.3":"تحليلات عبر المنصات","fx.3d":"راجع أمس وهذا الأسبوع والأسبوع الماضي وآخر ٣٠ يوماً في عرض واضح.","fx.4":"وحدة تحسين الظهور","fx.4d":"شاهد نقرات وعبارات وصفحات Search Console الموثقة وأرسل خرائط الموقع.","fx.5":"إحصاءات GA4","fx.5d":"اختر الموقع الصحيح وراقب المستخدمين والجلسات والأحداث وأهم الصفحات.","fx.6":"ملف النشاط التجاري","fx.6d":"راجع حسابات Google Business Profile والمواقع المملوكة لكل نشاط.","fx.7":"البكسلات والتتبع","fx.7d":"نظّم إعدادات تتبع وتحويل Google وMeta وTikTok.","fx.8":"إطلاق بعد الموافقة","fx.8d":"راجع الميزانيات والمحتوى قبل إنشاء الحملات متوقفة.","fx.9":"مساحات عمل خاصة","fx.9d":"اعزل مستخدمي وحملات وتكاملات وبيانات كل نشاط.","fx.10":"تحكم المشرف العام","fx.10d":"أشرف على وصول العملاء وطلبات الموافقة والسياسات والنشاط.","fx.11":"الميزانيات وسجل التدقيق","fx.11d":"حدد حدود الموافقة وسجل الإجراءات وأوقف النشاط عند الحاجة.","fx.12":"تطبيق ويب قابل للتثبيت","fx.12d":"استخدم Adwise كتطبيق سريع على الكمبيوتر والهاتف."});
const EN={}; document.querySelectorAll("[data-i18n]").forEach(e=>{ if(!(e.dataset.i18n in EN)) EN[e.dataset.i18n]=e.textContent; });
const sg=k=>{try{return localStorage.getItem(k)}catch(e){return null}}, ss=(k,v)=>{try{localStorage.setItem(k,v)}catch(e){}};
const cl=(v,a=0,b=1)=>Math.min(b,Math.max(a,v)), ez=x=>1-Math.pow(1-x,3), eio=x=>x<.5?4*x*x*x:1-Math.pow(-2*x+2,3)/2, lerp=(a,b,t)=>a+(b-a)*t;
const reduce=matchMedia("(prefers-reduced-motion: reduce)").matches, touch=matchMedia("(hover: none)").matches;
const css=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const rgb=h=>{h=h.replace("#",""); return [0,2,4].map(i=>parseInt(h.substr(i,2),16)).join(",");};
let lang="en", C={};
const LOGO=["1,112,252","131,54,251","172,86,251","41,244,226"], HOT=["246,70,133","252,128,77"];
function pal(){ C={acc:rgb(css("--acc")),acc2:rgb(css("--acc2")),text:rgb(css("--text")),muted:rgb(css("--muted"))}; }

/* ---------- split headings into words for the reveal ---------- */
function split(){ document.querySelectorAll("[data-split]").forEach(el=>{ const txt=el.textContent; el.innerHTML=txt.split(/(\s+)/).map(w=>/^\s+$/.test(w)?w:`<span class="w"><span>${w}</span></span>`).join(""); }); }
/* ---------- language / theme ---------- */
function applyLang(l){ lang=l; const d=l==="ar"?AR:EN; document.documentElement.lang=l; document.documentElement.dir=l==="ar"?"rtl":"ltr";
 document.querySelectorAll("[data-i18n]").forEach(e=>{ const v=d[e.dataset.i18n]; if(v!==undefined) e.textContent=v; });
 split(); document.getElementById("langBtn").textContent=l==="ar"?"EN":"ع"; ss("adw2_lang",l); if(window.__field) window.__field(); document.querySelectorAll("[data-split]").forEach(e=>{ if(e.closest(".on")||e.classList.contains("on")) e.classList.add("on"); }); }
document.getElementById("langBtn").onclick=()=>applyLang(lang==="en"?"ar":"en");
const SUN='<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>', MOON='<path d="M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z"/>';
function applyTheme(th){ document.documentElement.dataset.theme=th; document.getElementById("themeIco").innerHTML=th==="dark"?SUN:MOON; document.querySelector('meta[name="theme-color"]').content=th==="dark"?"#05060F":"#F6F7FD"; ss("adw2_theme",th); pal(); }
document.getElementById("themeBtn").onclick=()=>applyTheme(document.documentElement.dataset.theme==="dark"?"light":"dark");
/* ---------- links + form ---------- */
document.querySelectorAll("[data-signup]").forEach(a=>a.href=SIGNUP_URL||"#start"); document.querySelectorAll("[data-login]").forEach(a=>a.href=LOGIN_URL||"#start"); document.querySelectorAll("[data-privacy]").forEach(a=>a.href=PRIVACY_URL||"#privacy");
document.getElementById("dform").addEventListener("submit",e=>{ e.preventDefault(); const f=e.target; let ok=true; f.querySelectorAll("[required]").forEach(i=>{ if(!i.value.trim()){ i.style.borderColor="#ff6b6b"; ok=false; } else i.style.borderColor=""; }); if(!ok) return;
 const d=new FormData(f), ar=lang==="ar", sp=f.spend.options[f.spend.selectedIndex].textContent;
 const subject=ar?"طلب عرض توضيحي — adwise":"Guided demo request — adwise";
 const body=(ar?"الاسم: ":"Name: ")+d.get("name")+"\n"+(ar?"النشاط: ":"Business: ")+d.get("biz")+"\n"+(ar?"الهاتف: ":"Phone: ")+d.get("phone")+"\n"+(ar?"الإنفاق الشهري: ":"Monthly spend: ")+sp;
 window.location.href=`mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`; });
/* ---------- nav: hides on scroll down ---------- */
(function(){ const nv=document.getElementById("nav"), mm=document.getElementById("mm"); let ly=scrollY,acc=0;
 addEventListener("scroll",()=>{ const y=scrollY,d=y-ly; ly=y; if(mm.classList.contains("open")){nv.classList.remove("hide");return;} acc=(Math.sign(d)===Math.sign(acc))?acc+d:d; if(y<100||acc<-14) nv.classList.remove("hide"); else if(acc>14) nv.classList.add("hide"); },{passive:true});
 document.getElementById("burger").onclick=()=>mm.classList.toggle("open"); mm.querySelectorAll("a").forEach(a=>a.onclick=()=>mm.classList.remove("open")); })();
document.getElementById("yr").textContent=new Date().getFullYear();
document.addEventListener("click",event=>{ const target=event.target.closest("button,a,[role='button']"); if(!target) return; target.classList.remove("tap-feedback"); void target.offsetWidth; target.classList.add("tap-feedback"); setTimeout(()=>target.classList.remove("tap-feedback"),240); });
/* ---------- cursor glow + magnetic buttons ---------- */
let mx=innerWidth/2,my=innerHeight/2; addEventListener("pointermove",e=>{mx=e.clientX;my=e.clientY},{passive:true});
const cur=document.querySelector(".cursor"); let cx=mx,cy=my;
document.querySelectorAll(".mag").forEach(b=>{ b.addEventListener("pointermove",e=>{ if(touch) return; const r=b.getBoundingClientRect(); b.style.transform=`translate(${(e.clientX-r.left-r.width/2)*.25}px,${(e.clientY-r.top-r.height/2)*.35}px)`; }); b.addEventListener("pointerleave",()=>b.style.transform=""); });
/* ---------- reveals ---------- */
const io=new IntersectionObserver(es=>es.forEach(en=>{ if(en.isIntersecting){ en.target.classList.add("on"); } }),{threshold:.18,rootMargin:"0px 0px -8% 0px"});
function watch(){ document.querySelectorAll(".rv,[data-split],.go").forEach(e=>io.observe(e)); }

/* =========== HERO: particle field — noise becomes one clear move =========== */
const hero=document.getElementById("hero"), hA=document.getElementById("hA"), hB=document.getElementById("hB");
(function(){ const cv=document.getElementById("field"), x=cv.getContext("2d"); let W,H,P=[],TG=[],CH=[];
 const LABELS=["Google","Meta","TikTok","CTR","CPC","Leads","ROAS","Reach","Spend","Clicks","Conv."];
 function setup(){ const d=Math.min(devicePixelRatio||1,2); W=cv.clientWidth; H=cv.clientHeight; cv.width=W*d; cv.height=H*d; x.setTransform(d,0,0,d,0,0);
  const n=W<640?520:1300, rtl=document.documentElement.dir==="rtl";
  // target: one rising arrow line across the right side of the screen
  const x0=W*(W<640?.06:.42), y0=H*.86, x1=W*.94, y1=H*.2, pts=[];
  const L=Math.hypot(x1-x0,y1-y0), ang=Math.atan2(y1-y0,x1-x0);
  for(let i=0;i<n;i++){ let px,py; const r=Math.random();
   if(r<.78){ const t=i/n, wob=Math.sin(t*Math.PI*3)*H*.035; px=x0+(x1-x0)*t-Math.sin(ang)*wob; py=y0+(y1-y0)*t+Math.cos(ang)*wob; px+= (Math.random()-.5)*4; py+=(Math.random()-.5)*4; }
   else { const s=Math.random()<.5?1:-1, t=Math.random(), hl=L*.07; const a=ang+Math.PI+s*.55; px=x1+Math.cos(a)*hl*t; py=y1+Math.sin(a)*hl*t; }
   if(rtl) px=W-px; pts.push([px,py]); }
  P=pts.map(([tx,ty],i)=>{ const u=i/n, head=i>=n*.78||u>.93; return {tx,ty,x:Math.random()*W,y:Math.random()*H,vx:0,vy:0,ph:Math.random()*6.28,s:Math.random()<.12?2.2:1.3,col:LOGO[Math.floor(Math.random()*4)],col2:head?HOT[Math.random()<.5?0:1]:LOGO[Math.min(3,Math.floor(u*4))]}; });
  CH=LABELS.map((l,i)=>({l,x:Math.random()*W,y:Math.random()*H,ph:Math.random()*6,sp:.2+Math.random()*.3})); pal(); }
 window.__field=setup;
 let k=0;
 function draw(now){ const t=now/1000, r=hero.getBoundingClientRect(), p=cl(-r.top/(r.height-innerHeight)); k+=(eio(cl(p/.85))-k)*.08;
  x.clearRect(0,0,W,H);
  // noise field particles
  for(const q of P){ const nx=q.x+Math.cos(q.ph+t*.3+q.y*.004)*1.2, ny=q.y+Math.sin(q.ph*1.3+t*.25+q.x*.004)*1.2;
   const fx=lerp(nx,q.tx+Math.sin(t*1.6+q.ph)*1.5,k*.18+(k>0.02?0:0)), fy=lerp(ny,q.ty+Math.cos(t*1.4+q.ph)*1.5,k*.18);
   q.vx+=(fx-q.x)*(.04+k*.12); q.vy+=(fy-q.y)*(.04+k*.12);
   if(!touch){ const dx=q.x-mx, dy=q.y-my, dd=dx*dx+dy*dy; if(dd<130*130){ const f=(1-Math.sqrt(dd)/130)*(1.6-k); q.vx+=dx/Math.sqrt(dd+1)*f; q.vy+=dy/Math.sqrt(dd+1)*f; } }
   q.vx*=.82; q.vy*=.82; q.x+=q.vx; q.y+=q.vy;
   if(k<.05){ if(q.x<-10) q.x=W+10; if(q.x>W+10) q.x=-10; if(q.y<-10) q.y=H+10; if(q.y>H+10) q.y=-10; }
   const al=(.18+.5*k)*(.6+.4*Math.sin(t*2+q.ph)); x.fillStyle=`rgba(${k>.45?q.col2:q.col},${al})`; x.fillRect(q.x,q.y,q.s+k*.6,q.s+k*.6); }
  // signal labels drift then fade into the line
  x.font="600 12px Space Grotesk, Inter, sans-serif"; x.textAlign="center";
  for(const c of CH){ c.x+=Math.cos(t*c.sp+c.ph)*.4; c.y+=Math.sin(t*c.sp*1.2+c.ph)*.3; const a=(1-k)*.55; if(a<=.01) continue; x.fillStyle=`rgba(${C.muted},${a})`; x.fillText(c.l,c.x,c.y); }
  if(!reduce) requestAnimationFrame(draw); }
 (document.fonts?document.fonts.ready:Promise.resolve()).then(()=>{ setup(); requestAnimationFrame(draw); });
 let rt; addEventListener("resize",()=>{ clearTimeout(rt); rt=setTimeout(setup,200); }); })();

/* =========== STAGES: horizontal pinned journey with scrubbed widgets =========== */
const stS=document.getElementById("how"), track=document.getElementById("track"), stProg=document.getElementById("stProg"), dials=[...document.querySelectorAll(".dl-i")], stages=[...document.querySelectorAll(".stage")];
dials.forEach(b=>b.onclick=()=>{ const i=+b.dataset.go, top=stS.getBoundingClientRect().top+scrollY; scrollTo({top:top+(i/4)*(stS.offsetHeight-innerHeight)+2,behavior:"smooth"}); });
const WG=[...document.querySelectorAll(".wg")];
function countTo(el,p){ const to=+el.dataset.to; el.textContent=Math.round(to*ez(cl(p))).toLocaleString(lang==="ar"?"ar-AE":"en-US"); }
function widget(i,p){ const w=WG[i]; if(!w) return; p=cl(p);
 if(i===0){ w.querySelectorAll(".line,.line2").forEach(l=>l.style.strokeDashoffset=1000*(1-ez(cl(p*1.3)))); w.querySelector(".area").style.opacity=ez(cl(p*1.3-.2)); countTo(w.querySelector(".count"),p*1.2);
  const ch=[...w.querySelectorAll(".chips span")], a=Math.min(3,Math.floor(p*4)); ch.forEach((c,k)=>c.classList.toggle("on",k===a)); }
 if(i===1){ const ins=[...w.querySelectorAll(".ins .in")]; ins.forEach((e,k)=>e.classList.toggle("on",p>k*.12)); w.querySelectorAll(".ln").forEach((l,k)=>l.style.strokeDashoffset=400*(1-ez(cl((p-.15-k*.04)*2.2)))); [...w.querySelectorAll(".out")].forEach((o,k)=>o.classList.toggle("on",p>.45+k*.12)); w.querySelector(".evi").classList.toggle("on",p>.85); }
 if(i===2){ [...w.querySelectorAll(".tile")].forEach((e,k)=>{ const q=ez(cl((p-k*.15)*2.4)); e.style.opacity=.15+.85*q; e.style.transform=`translate3d(0,${(1-q)*60}px,${(1-q)*-120}px) rotateX(${(1-q)*30}deg)`; }); w.querySelector(".camp").classList.toggle("on",p>.75); }
 if(i===3){ [...w.querySelectorAll(".appr li")].forEach((li,k)=>li.classList.toggle("on",p>.2+k*.2)); w.classList.toggle("ok",p>.82); }
 if(i===4){ w.querySelectorAll(".metrics .bars").forEach((b,k)=>b.style.setProperty("--k",ez(cl((p-k*.1)*1.8)))); w.querySelectorAll(".metrics .bars i").forEach(e=>e.style.setProperty("--k",getComputedStyle(e.parentElement).getPropertyValue("--k"))); w.querySelector(".g-fg").style.strokeDashoffset=314.16*(1-.92*ez(cl((p-.25)*1.6))); countTo(w.querySelector(".count"),(p-.25)*1.6); }
}
function stagesFx(){ const mobile=innerWidth<=1000;
 if(mobile){ stages.forEach((s,i)=>{ const r=s.querySelector(".wg").getBoundingClientRect(); widget(i,(innerHeight*.95-r.top)/(innerHeight*.75)); }); return; }
 const r=stS.getBoundingClientRect(), p=cl(-r.top/(r.height-innerHeight)), n=stages.length, pos=p*(n-1);
 track.style.transform=`translate3d(${-pos*innerWidth}px,0,0)`; stProg.style.transform=`scaleX(${p})`;
 const a=Math.round(pos); dials.forEach((d,k)=>d.classList.toggle("on",k===a));
 stages.forEach((s,i)=>{ const d=i-pos, w=WG[i]; w.style.transform=`rotateY(${d*-28}deg) translateZ(${-Math.abs(d)*160}px) scale(${1-Math.min(.12,Math.abs(d)*.12)})`;
  const c=s.querySelector(".st-copy"); c.style.opacity=cl(1-Math.abs(d)*1.4); c.style.transform=`translateX(${d*-80}px)`;
  widget(i,cl(1-Math.abs(d)*1.15)*1.0 + (d<0?0:0)); if(Math.abs(d)<.5) s.querySelector(".st-h").classList.add("on"); });
}

/* =========== PLATFORM: 3D orbit + data packets =========== */
const orbit=document.getElementById("orbit"), plane=document.getElementById("orbPlane"), nodes=[...orbit.querySelectorAll(".node")];
const pk=document.getElementById("pkt"), px=pk.getContext("2d"); let PW,PH,pkts=[];
function pkSize(){ const d=Math.min(devicePixelRatio||1,2); PW=pk.clientWidth; PH=pk.clientHeight; pk.width=PW*d; pk.height=PH*d; px.setTransform(d,0,0,d,0,0); } pkSize(); addEventListener("resize",pkSize);
function orbitFx(t){ const r=orbit.getBoundingClientRect(); if(r.bottom<-50||r.top>innerHeight+50) return; const sp=cl((innerHeight-r.top)/(innerHeight+r.height));
 const tilt=lerp(72,58,sp), R=.42, cxp=PW/2, cyp=PH/2; plane.style.transform=`rotateX(${tilt}deg) rotateZ(${t*8}deg)`;
 const pos=[]; nodes.forEach((n,i)=>{ const a=t*.35+i*2.094, ex=Math.cos(a)*R*PW, ey=Math.sin(a)*R*PH*Math.cos(tilt*Math.PI/180); const z=Math.sin(a); n.style.transform=`translate(${ex}px,${ey}px) scale(${.82+.22*(z+1)/2})`; n.style.zIndex=z>0?5:1; n.style.opacity=.6+.4*(z+1)/2; pos.push([cxp+ex,cyp+ey]); });
 if(Math.random()<.18) pkts.push({i:Math.floor(Math.random()*3),t:0,dir:Math.random()<.6?1:-1});
 px.clearRect(0,0,PW,PH); pos.forEach(([a,b])=>{ px.strokeStyle=`rgba(${C.acc},.18)`; px.lineWidth=1; px.beginPath(); px.moveTo(a,b); px.lineTo(cxp,cyp); px.stroke(); });
 pkts=pkts.filter(q=>q.t<1); for(const q of pkts){ q.t+=.022; const [a,b]=pos[q.i], f=q.dir>0?q.t:1-q.t, xx=lerp(a,cxp,f), yy=lerp(b,cyp,f); px.fillStyle=`rgba(${q.dir>0?LOGO[3]:HOT[1]},${1-Math.abs(.5-q.t)})`; px.beginPath(); px.arc(xx,yy,2.6,0,7); px.fill(); } }

/* =========== CONTROL: emergency stop + live audit log =========== */
const con=document.getElementById("console"), estop=document.getElementById("estop"), logEl=document.getElementById("log"), bars=[...document.querySelectorAll("#csBars i")];
const LOGS=["lg1","lg2","lg3","lg4","lg5"]; let li=0;
function now(){ const d=new Date(); return String(d.getHours()).padStart(2,"0")+":"+String(d.getMinutes()).padStart(2,"0")+":"+String(d.getSeconds()).padStart(2,"0"); }
function addLog(k){ const el=document.createElement("li"); el.innerHTML=`<time>${now()}</time><span data-i18n="${k}"></span>`; el.querySelector("span").textContent=(lang==="ar"?AR:EN)[k]||AR[k]; logEl.prepend(el); while(logEl.children.length>6) logEl.lastChild.remove(); }
EN.lg6="Emergency stop used"; EN.lg7="Activity resumed"; ["lg1","lg2","lg3","lg4","lg5"].forEach((k,i)=>EN[k]=EN[k]||["Owner approved budget","Campaign created — paused","Analyst viewed weekly signal","Publishing approved","Creative updated"][i]);
addLog("lg1"); addLog("lg2");
setInterval(()=>{ if(con.classList.contains("stopped")) return; const r=con.getBoundingClientRect(); if(r.bottom<0||r.top>innerHeight) return; addLog(LOGS[li++%LOGS.length]); bars.forEach(b=>b.style.height=(35+Math.random()*60)+"%"); },2200);
estop.onclick=()=>{ const s=con.classList.toggle("stopped"); estop.setAttribute("aria-pressed",s); estop.querySelector(".e1").dataset.i18n=s?"ct.resume":"ct.stop"; estop.querySelector(".e1").textContent=(lang==="ar"?AR:EN)[s?"ct.resume":"ct.stop"]||"Resume"; addLog(s?"lg6":"lg7"); if(!s) bars.forEach(b=>b.style.height=(35+Math.random()*60)+"%"); };
EN["ct.resume"]=EN["ct.resume"]||"Resume";

/* =========== PRIVACY: three sealed pods, particles never cross =========== */
(function(){ const cv=document.getElementById("pods"), x=cv.getContext("2d"); let W,H,Pp=[];
 function setup(){ const d=Math.min(devicePixelRatio||1,2); W=cv.clientWidth; H=cv.clientHeight; cv.width=W*d; cv.height=H*d; x.setTransform(d,0,0,d,0,0);
  Pp=[]; for(let c=0;c<3;c++) for(let i=0;i<(W<640?14:26);i++) Pp.push({c,x:0,y:0,vx:(Math.random()-.5)*1.4,vy:(Math.random()-.5)*1.4,r:2+Math.random()*2.5,init:false}); }
 setup(); addEventListener("resize",setup);
 function draw(now){ const t=now/1000; const r=cv.getBoundingClientRect(); if(!(r.bottom<0||r.top>innerHeight)){
   x.clearRect(0,0,W,H); const pw=W/3, pad=18, cols=[LOGO[0],LOGO[2],LOGO[3]];
   for(let c=0;c<3;c++){ const x0=c*pw+pad, y0=48, w=pw-pad*2, h=H-48-pad; x.strokeStyle=`rgba(${cols[c]},.35)`; x.lineWidth=1.4; x.setLineDash([]); x.beginPath(); x.roundRect(x0,y0,w,h,20); x.stroke();
    x.fillStyle=`rgba(${cols[c]},.04)`; x.fill(); x.save(); x.strokeStyle=`rgba(${cols[c]},.5)`; x.setLineDash([4,6]); x.lineDashOffset=-t*20; x.beginPath(); x.roundRect(x0-6,y0-6,w+12,h+12,24); x.stroke(); x.restore(); }
   for(const q of Pp){ const x0=q.c*pw+pad+8, y0=56, w=pw-pad*2-16, h=H-56-pad-8; if(!q.init){ q.x=x0+Math.random()*w; q.y=y0+Math.random()*h; q.init=true; }
    q.x+=q.vx; q.y+=q.vy; if(q.x<x0||q.x>x0+w){ q.vx*=-1; q.x=cl(q.x,x0,x0+w); } if(q.y<y0||q.y>y0+h){ q.vy*=-1; q.y=cl(q.y,y0,y0+h); }
    x.fillStyle=`rgba(${cols[q.c]},.85)`; x.beginPath(); x.arc(q.x,q.y,q.r,0,7); x.fill(); }
   for(let i=0;i<Pp.length;i++) for(let j=i+1;j<Pp.length;j++){ const a=Pp[i],b=Pp[j]; if(a.c!==b.c) continue; const d=Math.hypot(a.x-b.x,a.y-b.y); if(d<60){ x.strokeStyle=`rgba(${cols[a.c]},${(1-d/60)*.3})`; x.lineWidth=1; x.beginPath(); x.moveTo(a.x,a.y); x.lineTo(b.x,b.y); x.stroke(); } } }
  if(!reduce) requestAnimationFrame(draw); } requestAnimationFrame(draw); })();

/* =========== GET STARTED: the clear-move line draws itself =========== */
(function(){ const cv=document.getElementById("goline"), x=cv.getContext("2d"), box=document.getElementById("go"); let W,H;
 function setup(){ const d=Math.min(devicePixelRatio||1,2); W=cv.clientWidth; H=cv.clientHeight; cv.width=W*d; cv.height=H*d; x.setTransform(d,0,0,d,0,0); } setup(); addEventListener("resize",setup);
 function draw(now){ const t=now/1000, r=box.getBoundingClientRect(); if(!(r.bottom<0||r.top>innerHeight)){ const p=cl((innerHeight-r.top)/(innerHeight*.9)); x.clearRect(0,0,W,H);
   const rtl=document.documentElement.dir==="rtl", N=80; x.lineWidth=2.5; const gr=x.createLinearGradient(0,H,W,0); gr.addColorStop(0,"rgba(1,112,252,.7)"); gr.addColorStop(.5,"rgba(172,86,251,.7)"); gr.addColorStop(.85,"rgba(41,244,226,.7)"); gr.addColorStop(1,"rgba(252,128,77,.8)"); x.strokeStyle=gr; x.beginPath();
   for(let i=0;i<=N*ez(p);i++){ const u=i/N, xx=(rtl?1-u:u)*W, yy=H*(.92-.75*u)+Math.sin(u*9+t)*H*.02*(1-u); i?x.lineTo(xx,yy):x.moveTo(xx,yy); } x.stroke();
   const u=ez(p), hx=(rtl?1-u:u)*W, hy=H*(.92-.75*u); x.fillStyle=`rgba(${HOT[1]},.95)`; x.beginPath(); x.arc(hx,hy,5,0,7); x.fill(); x.fillStyle=`rgba(${HOT[0]},.22)`; x.beginPath(); x.arc(hx,hy,14+Math.sin(t*3)*4,0,7); x.fill(); }
  if(!reduce) requestAnimationFrame(draw); } requestAnimationFrame(draw); })();

/* =========== main loop =========== */
function frame(now){ const t=now/1000;
 const r=hero.getBoundingClientRect(), hp=cl(-r.top/(r.height-innerHeight));
 hA.style.opacity=cl(1-hp*1.6); hA.style.filter=`blur(${hp*8}px)`; hB.style.transform=`translateY(${-hp*10}px) scale(${1+hp*.04})`;
 stagesFx(); orbitFx(t);
 if(!touch){ cx+=(mx-cx)*.12; cy+=(my-cy)*.12; cur.style.transform=`translate(${cx}px,${cy}px)`; }
 requestAnimationFrame(frame); }
applyTheme(sg("adw2_theme")||"dark");
applyLang(sg("adw2_lang")||"en"); watch();
requestAnimationFrame(frame);
