/* Reaction rate page (Atlas v2).  dG‡, the Eyring rate constant, half-life,
   Arrhenius parameters, the t½(dG‡) line, the isotope effect and the Wigner
   correction come from quas_atlas.core.kinetics (kin.state, kin.custom);
   this script formats and draws. */
// ---------- страница «Скорость реакции: переходное состояние» ----------
const NS='http://www.w3.org/2000/svg',$=id=>document.getElementById(id);
function el(tag,a,p,t){const e=document.createElementNS(NS,tag);for(const k in a)e.setAttribute(k,a[k]);if(t!=null)e.textContent=t;if(p)p.appendChild(e);return e}
const fmt=(x,d=2)=>{if(x==null||!isFinite(x))return '—';if(Math.abs(x)<0.5*Math.pow(10,-d))x=0;return x.toFixed(d).replace('.',',').replace('-','−')};
const SUP=s=>String(s).split('').map(c=>c==='-'?'⁻':'⁰¹²³⁴⁵⁶⁷⁸⁹'[+c]).join('');
function sci(x){if(!isFinite(x))return '—';if(x===0)return '0';const e=Math.floor(Math.log10(Math.abs(x)));if(e>=-2&&e<4)return fmt(x,e>=2?0:e>=0?2:3);const m=x/Math.pow(10,e);return fmt(m,2)+'·10'+SUP(e)}
const tok=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const Q={T:298.15,n:1};
function human(t){if(!isFinite(t))return '—';if(t<1e-3)return sci(t)+' с';if(t<1)return fmt(t*1000,t<0.01?2:0)+' мс';if(t<60)return fmt(t,1)+' с';if(t<3600)return fmt(t/60,1)+' мин';if(t<86400)return fmt(t/3600,1)+' ч';if(t<3.156e7)return fmt(t/86400,1)+' сут';return sci(t/3.156e7)+' лет'}
function chips(box,labels,cur,on){box.innerHTML='';labels.forEach((t,i)=>{const b=document.createElement('button');b.type='button';b.className='chip';b.innerHTML=t;b.setAttribute('aria-pressed',i===cur);b.onclick=()=>on(i);box.appendChild(b)})}
function mark(box,i){[...box.children].forEach((b,j)=>b.setAttribute('aria-pressed',j===i))}
chips($('mG'),['мономолекулярная, A → P','бимолекулярная, A + B → P'],0,i=>{Q.n=i+1;mark($('mG'),i);draw()});
['dH','dS','nu','im'].forEach(id=>$(id).oninput=draw);
$('T').value=298;$('T').oninput=()=>{Q.T=+$('T').value;draw()};$('bT298').textContent=fmt(298.15,2)+' K';$('bT298').onclick=()=>{Q.T=298.15;$('T').value=298;draw()};
const liveK=QC.live('kin.state');
async function draw(){const dH=+$('dH').value,dS=+$('dS').value,T=Q.T,bi=Q.n===2,nu=+$('nu').value,im=+$('im').value;
  let Z;try{Z=await liveK({dH,dS,T,n:Q.n,nu,im})}catch(e){return}const dG=Z.dG,k=Z.k;
  $('dHv').textContent=fmt(dH,1)+' кДж/моль';$('dSv').textContent=fmt(dS,0)+' Дж/(моль·К)';$('Tv').textContent=fmt(T,T===298.15?2:0)+' K';
  const t=Z.t,Ea=Z.Ea,A=Z.A;
  const card=(a,b,c)=>'<div class="card"><span class="t">'+a+'</span><b>'+b+'</b>'+(c?'<small>'+c+'</small>':'')+'</div>';
  $('cards').innerHTML=card('ΔG<sup>‡</sup> = ΔH<sup>‡</sup> − TΔS<sup>‡</sup>',fmt(dG,1)+' кДж/моль',fmt(dG/4.184,1)+' ккал/моль')+card('константа скорости k',sci(k)+(bi?' л/(моль·с)':' с⁻¹'),bi?'стандартное состояние 1 моль/л':'')
    +card('период полупревращения',human(t),bi?'при начальных концентрациях 1 моль/л':'')+card('по Аррениусу',fmt(Ea,1)+' кДж/моль','A = '+sci(A)+(bi?' л/(моль·с)':' с⁻¹'));
  $('eyNote').innerHTML='Энергия активации Аррениуса E<sub>a</sub> = ΔH<sup>‡</sup> + RT (для мономолекулярных реакций и реакций в растворе), предэкспонента A = (e·k<sub>B</sub>T/h)·exp(ΔS<sup>‡</sup>/R). Отрицательная ΔS<sup>‡</sup> — упорядоченное переходное состояние (циклическое, бимолекулярное) — уменьшает A: каждые −19 Дж/(моль·К) замедляют реакцию в 10 раз.';
  chart(dG,T,bi,Z.chart);
  const r=Z.kie.r,nD=Z.kie.nD,kie=Z.kie.kie;$('nuv').textContent=fmt(nu,0);
  $('kie').innerHTML='ν(C–D) = ν(C–H) / √<span class=fr><span>μ<sub>D</sub></span><span>μ<sub>H</sub></span></span> = '+fmt(nu,0)+'/'+fmt(r,3)+' = '+fmt(nD,0)+' см⁻¹. Теряется половина разности квантов, '+fmt(Z.kie.half,0)+' см⁻¹ = '+fmt(Z.kie.halfkJ,2)+' кДж/моль. При '+fmt(T,0)+' K: <b>k<sub>H</sub>/k<sub>D</sub> ≈ '+fmt(kie,1)+'</b>. Наблюдаемые первичные эффекты обычно 2–8; значения заметно больше 7–10 при комнатной температуре — признак туннелирования.';
  const w=Z.tun.w,kap=Z.tun.kap;$('imv').textContent=fmt(im,0)+'i';
  $('tun').innerHTML='hcν<sup>‡</sup>/k<sub>B</sub>T = '+fmt(w,2)+'; <b>κ = '+fmt(kap,2)+'</b>. '+(kap<1.5?'Поправка мала, оценка Вигнера здесь разумна.':kap<2.5?'Поправка уже заметна; оценку Вигнера стоит проверить более точной моделью (Эккарт, полуклассические методы).':'Поправка большая — оценка Вигнера за пределами применимости: туннелирование существенно, нужна модель Эккарта или полуклассический расчёт.')}
function chart(dG,T,bi,C){const svg=$('chart');svg.innerHTML='';const W=960,Hh=300,L=64,Rr=110,Tp=14,B=38,g0=40,g1=140;
  const y0=C.y0,y1=C.y1;
  const X=g=>L+(g-g0)/(g1-g0)*(W-L-Rr),Y=v=>Tp+(y1-v)/(y1-y0)*(Hh-B-Tp);const ax=tok('--line'),mu=tok('--muted');
  [['1 с',0],['1 мин',Math.log10(60)],['1 ч',Math.log10(3600)],['1 сут',Math.log10(86400)],['1 год',Math.log10(3.156e7)],['1000 лет',Math.log10(3.156e10)],['1 мкс',-6]].forEach(([n,v])=>{if(v<y0||v>y1)return;el('line',{x1:L,x2:W-Rr,y1:Y(v),y2:Y(v),stroke:ax},svg);el('text',{x:W-Rr+6,y:Y(v)+4},svg,n)});
  for(let g=40;g<=140;g+=20)el('text',{x:X(g),y:Hh-B+16,'text-anchor':'middle'},svg,String(g));
  el('text',{x:(L+W-Rr)/2,y:Hh-4,'text-anchor':'middle'},svg,'ΔG‡, кДж/моль');el('text',{x:8,y:Tp+4},svg,'lg t½');
  for(let v=Math.ceil(y0/5)*5;v<=y1;v+=5)el('text',{x:L-6,y:Y(v)+4,'text-anchor':'end'},svg,String(v).replace('-','−'));
  el('path',{d:[g0,g1].map((g,i)=>(i?'L':'M')+X(g).toFixed(1)+' '+Y([C.lt0,C.lt1][i]).toFixed(1)).join(''),stroke:tok('--accent'),'stroke-width':2.4,fill:'none'},svg);
  if(dG>=g0&&dG<=g1)el('circle',{cx:X(dG),cy:Y(C.ltG),r:6,fill:tok('--accent'),stroke:tok('--panel'),'stroke-width':2},svg)}
// ---------- своя реакция ----------
const num=s=>Number(String(s).trim().replace(',','.').replace('−','-'));
$('bCalc').onclick=async()=>{const msg=$('cMsg'),Gr=num($('cGr').value),Gt=num($('cGt').value),T=num($('cT').value),n=+$('cN').value,sol=$('cSS').value==='sol',ims=$('cIm').value.trim(),im=ims?Math.abs(num(ims)):0;
  if(!isFinite(Gr)||!isFinite(Gt)||!(T>0)||(ims&&!isFinite(im))){msg.textContent='Проверьте числа: энергии в хартри, температура в кельвинах.';return}
  let C;try{C=await QC.api('kin.custom',{Gr,Gt,T,n,sol,im})}catch(e){return}const dG=C.dG,corr=C.corr||0;
  if(dG<=0){msg.textContent='ΔG‡ = '+fmt(dG,1)+' кДж/моль ≤ 0: переходное состояние не выше исходных веществ. Проверьте, те ли энергии введены (и одинаковы ли метод и базис).';return}
  const k=C.k,t=C.t,kap=C.kap;
  msg.innerHTML='ΔG<sup>‡</sup> = <b>'+fmt(dG,1)+' кДж/моль</b> ('+fmt(dG/4.184,1)+' ккал/моль)'+(corr?'; включён переход к 1 моль/л: '+fmt(corr,2)+' кДж/моль':'')+'. k = '+sci(k)+(n===2?(sol?' л/(моль·с)':' бар⁻¹·с⁻¹ (= '+sci(C.kc)+' л/(моль·с))'):' с⁻¹')+', t½ ≈ '+human(t)+'.'+(im?' С поправкой Вигнера (κ = '+fmt(kap,2)+'): k = '+sci(C.kk)+'.'+(kap>2?' κ > 2 — оценка ненадёжна.':''):'')+(n===2&&!sol?' Для реакции в растворе выберите стандартное состояние 1 моль/л: энергии из выходного файла относятся к газу при 1 бар.':'')};
draw();matchMedia('(prefers-color-scheme: dark)').addEventListener('change',draw);
