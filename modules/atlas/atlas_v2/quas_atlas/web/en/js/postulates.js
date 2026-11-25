/* Postulates page (Atlas v2).  The state (48 amplitudes), its time evolution,
   |Psi|^2, the observables and every measurement (Born rule, collapse,
   position packet) are computed by quas_atlas.core.postulates; the browser
   keeps the clock, draws, and supplies the uniform random numbers. */
// ---------- страница «Постулаты»: частица в ящике (L = 1, ħ = 1, m = 1; энергии в E₁, время в T₁ = 2πħ/E₁) ----------
const NS='http://www.w3.org/2000/svg',$=id=>document.getElementById(id);
function el(tag,a,p,t){const e=document.createElementNS(NS,tag);for(const k in a)e.setAttribute(k,a[k]);if(t!=null)e.textContent=t;if(p)p.appendChild(e);return e}
const tok=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const fmt=(x,d=3)=>{if(x==null||!isFinite(x))return '—';if(Math.abs(x)<0.5*Math.pow(10,-d))x=0;return x.toFixed(d).replace('-','−')};
const RM=matchMedia('(prefers-reduced-motion: reduce)').matches;
const NMAX=48,NG=401,XS=Array.from({length:NG},(_,i)=>i/(NG-1));
let prep={a:[1,0,0,0],ph:[0,0,0,0]};       // приготовленное состояние (4 амплитуды)
let C=[];                                  // текущие коэффициенты при t = 0 эпохи: [{re,im}] длины NMAX
let lastX=null;/* 2.16.0: the state before the last position measurement and its random number */
let t=0,t0=0,playing=false,raf=null,hist=new Array(NMAX).fill(0),histN=0;
// ---------- рисование ----------
function drawPsi(F){const sv=$('psiSvg');sv.innerHTML='';const W=560,H=280,L=40,R=16,T=12,B=30,pw=W-L-R,ph=H-T-B;
  // the range is [lo, hi] from the curves themselves (|Ψ|² ≥ 0, so the bottom only needs Re Ψ);
  // during the evolution it only grows - a kept range that the curves no longer fit in is not reused
  // 2.16.0: the axes stand still during the evolution — the limits come from the state, not from the curves of the
  // moment: |Ψ(x, t)| ≤ √2·Σ|cₙ| / √(Σ|cₙ|²) at every x and t (|ψₙ| ≤ √2 in the box), so |Ψ|² ≤ A² and Re Ψ ≥ −A;
  // they change only when the state is prepared or measured anew
  const ps2=F.ps2,psr=F.re;let s1=0,s2=0;for(const c of C){const m=Math.hypot(c.re,c.im);s1+=m;s2+=m*m}
  const A=s2>0?Math.SQRT2*s1/Math.sqrt(s2):Math.SQRT2;let hi=Math.max(2.2,A*A*1.04),lo=-Math.max(0.6,A*1.04);
  for(let i=0;i<NG;i++){hi=Math.max(hi,ps2[i]);lo=Math.min(lo,psr[i])}S.ymax=hi;S.ymin=lo;
  const sx=x=>L+x*pw,sy=y=>T+ph*(hi-y)/(hi-lo);
  el('rect',{x:L,y:T,width:pw,height:ph,fill:'none',stroke:tok('--line')},sv);
  el('line',{x1:L,y1:sy(0),x2:L+pw,y2:sy(0),stroke:tok('--line')},sv);
  // no thick dark walls at x = 0 and x = L the frame of the plot marks the box
  let d='M'+sx(0)+','+sy(0);for(let i=0;i<NG;i++)d+=' L'+sx(XS[i]).toFixed(1)+','+sy(ps2[i]).toFixed(1);d+=' L'+sx(1)+','+sy(0)+'Z';
  el('path',{d,fill:tok('--lp-bg'),stroke:tok('--lp'),'stroke-width':2},sv);
  let r='';for(let i=0;i<NG;i++)r+=(i?' L':'M')+sx(XS[i]).toFixed(1)+','+sy(psr[i]).toFixed(1);el('path',{d:r,fill:'none',stroke:tok('--ln'),'stroke-width':1.6,'stroke-dasharray':'5 4'},sv);
  const o=F.obs;el('line',{x1:sx(o.x),y1:T,x2:sx(o.x),y2:T+ph,stroke:tok('--ok'),'stroke-width':2},sv);
  if(S.mark!=null){el('line',{x1:sx(S.mark),y1:T,x2:sx(S.mark),y2:T+ph,stroke:tok('--warn'),'stroke-width':1.5,'stroke-dasharray':'2 3'},sv)}
  [0,0.25,0.5,0.75,1].forEach(x=>el('text',{x:sx(x),y:H-14,'text-anchor':'middle','font-size':12,fill:tok('--muted')},sv,fmt(x,2)));
  el('text',{x:L+pw,y:H-1,'text-anchor':'end','font-size':12,fill:tok('--muted')},sv,'x / L');
  return o}
function drawBars(sv,vals,opt){sv.innerHTML='';const W=520,H=200,L=40,R=10,T=12,B=30,pw=W-L-R,ph=H-T-B;let nShow=4;vals.forEach((v,k)=>{if(v>0.003)nShow=Math.max(nShow,k+1)});nShow=Math.min(NMAX,Math.max(nShow,opt.min||4));
  const bw=pw/nShow;el('line',{x1:L,y1:T+ph,x2:L+pw,y2:T+ph,stroke:tok('--line')},sv);
  [0,0.5,1].forEach(v=>{el('text',{x:L-6,y:T+ph-v*ph+4,'text-anchor':'end','font-size':11,fill:tok('--muted')},sv,fmt(v,1))});
  for(let k=0;k<nShow;k++){const v=vals[k]||0,h=v*ph;el('rect',{x:L+k*bw+bw*0.15,y:T+ph-h,width:bw*0.7,height:Math.max(0,h),fill:k===opt.hot?tok('--warn'):tok(opt.col||'--accent'),rx:2},sv);
    if(opt.ref){const q=opt.ref[k]||0;el('line',{x1:L+k*bw+bw*0.08,y1:T+ph-q*ph,x2:L+k*bw+bw*0.92,y2:T+ph-q*ph,stroke:tok('--ink'),'stroke-width':2},sv)}
    if(nShow<=16||k%Math.ceil(nShow/16)===0)el('text',{x:L+k*bw+bw/2,y:H-12,'text-anchor':'middle','font-size':11,fill:tok('--muted')},sv,String(k+1))}
  el('text',{x:L+pw,y:H-1,'text-anchor':'end','font-size':11,fill:tok('--muted')},sv,'n (E = n²E₁)')}
const S={ymax:0,mark:null};
let rBusy=false,rAgain=false;
/* one frame request at a time; frames requested meanwhile collapse into one */
async function render(){if(!C.length)return;if(rBusy){rAgain=true;return}rBusy=true;
  try{do{rAgain=false;const tt=t;let F;try{F=await QC.api('post.frame',{C,t:tt,t0})}catch(e){return}renderF(F,tt)}while(rAgain)}finally{rBusy=false}}
function renderF(F,t){const o=drawPsi(F);
  $('obsTab').innerHTML='<table class="mtab"><thead><tr><th>quantity</th><th>value</th><th>uncertainty</th></tr></thead><tbody>'+
   '<tr><td>energy ⟨E⟩, E₁</td><td>'+fmt(o.E,3)+'</td><td>ΔE = '+fmt(o.dE,3)+'</td></tr>'+
   '<tr><td>position ⟨x⟩, L</td><td>'+fmt(o.x,3)+'</td><td>Δx = '+fmt(o.dx,3)+'</td></tr>'+
   '<tr><td>momentum ⟨p⟩, ħ/L</td><td>'+fmt(o.p,3)+'</td><td>Δp = '+fmt(o.dp,3)+'</td></tr>'+
   '<tr><td>Δx·Δp, ħ</td><td colspan="2">'+fmt(o.dx*o.dp,3)+(o.dx*o.dp>=0.5-1e-6?' ≥ ½ — the uncertainty relation holds':'')+'</td></tr></tbody></table>';
  const P=F.P,nz=P.filter(x=>x>1e-6).length;
  $('st1').innerHTML=nz===1?'<b>A stationary state.</b> The factor e<sup>−iE<sub>n</sub>t/ħ</sup> is common to the whole function: Re Ψ oscillates, while |Ψ|² and all averages do not depend on time.':
    '<b>A superposition of '+nz+' states.</b> The terms gain phase at different rates, so |Ψ|² and ⟨x⟩ change with time. The beat frequencies are <span class=fr><span>E<sub>m</sub> − E<sub>n</sub></span><span>h</span></span>; after time T₁ all phases coincide and the picture repeats.';
  drawBars($('pSvg'),P,{});$('tV').textContent='t = '+fmt(t,3)+' T₁';$('tS').value=t%1}
// ---------- управление ----------
const PRE=[['ψ₁',[1,0,0,0],[0,0,0,0]],['ψ₂',[0,1,0,0],[0,0,0,0]],['ψ₁ + ψ₂',[1,1,0,0],[0,0,0,0]],['ψ₁ + iψ₂',[1,1,0,0],[0,90,0,0]],['ψ₁ + ψ₂ + ψ₃',[1,1,1,0],[0,0,0,0]],['ψ₁ + ψ₃',[1,0,1,0],[0,0,0,0]],['all four',[1,1,1,1],[0,0,0,0]]];
const preG=$('preG');PRE.forEach(([n,a,ph],i)=>{const b=document.createElement('button');b.type='button';b.className='chip';b.textContent=n;b.onclick=()=>{prep={a:a.slice(),ph:ph.map(x=>x*Math.PI/180)};syncAmp();reset()};preG.appendChild(b)});
const ab=$('ampBox');for(let k=0;k<4;k++){ab.insertAdjacentHTML('beforeend',`<span class="n">ψ<sub>${k+1}</sub></span><input type="range" min="0" max="1" step="0.01" id="a${k}" aria-label="Amplitude ψ${k+1}"><span class="hint">phase</span><input type="range" min="0" max="360" step="5" id="f${k}" aria-label="Phase ψ${k+1}"><span class="val" id="v${k}"></span>`)}
function syncAmp(){for(let k=0;k<4;k++){$('a'+k).value=prep.a[k];$('f'+k).value=Math.round(prep.ph[k]*180/Math.PI);$('v'+k).textContent=fmt(prep.a[k],2)+' · '+Math.round(prep.ph[k]*180/Math.PI)+'°'}
  preG.querySelectorAll('.chip').forEach((b,i)=>b.setAttribute('aria-pressed',PRE[i][1].every((x,k)=>Math.abs(x-prep.a[k])<1e-9)&&PRE[i][2].every((x,k)=>Math.abs(x*Math.PI/180-prep.ph[k])<1e-6)))}
for(let k=0;k<4;k++){$('a'+k).oninput=e=>{prep.a[k]=+e.target.value;if(prep.a.every(x=>x===0))prep.a[k]=0.01;syncAmp();reset()};$('f'+k).oninput=e=>{prep.ph[k]=+e.target.value*Math.PI/180;syncAmp();reset()}}
const getPrep=QC.live('post.prepare');
async function reset(){lastX=null;const tc=t;let c;try{c=await getPrep({a:prep.a,ph:prep.ph})}catch(e){return}C=c;t0=tc;S.mark=null;S.ymax=0;S.ymin=0;render()}
function stop(){playing=false;if(raf)cancelAnimationFrame(raf);raf=null;$('bPlay').textContent='▶ Time evolution'}
function play(){if(playing){stop();return}playing=true;$('bPlay').textContent='❚❚ Pause';let last=performance.now();
  const step=n=>{if(!playing)return;t+=(n-last)/1000*0.12;last=n;render();raf=requestAnimationFrame(step)};raf=requestAnimationFrame(step)}
$('bPlay').onclick=()=>{if(RM){t+=0.05;render();return}play()};$('bT0').onclick=()=>{stop();t=t0;render()};
$('tS').oninput=e=>{stop();t=Math.floor(t)+(+e.target.value);render()};
// ---------- измерения ----------
$('bME').onclick=async()=>{lastX=null;const r=Math.random(),tc=t;let M;try{M=await QC.api('post.measureE',{C,t:tc,t0,r})}catch(e){return}const P=M.P,k=M.k;C=M.C;t0=tc;S.mark=null;S.ymax=0;S.ymin=0;hist[k]++;histN++;drawHist();render();
  $('st2').innerHTML='Result: <b>E = '+((k+1)*(k+1))+'E₁</b> (n = '+(k+1)+'), the probability of this outcome was '+fmt(P[k],3)+'. The state has “collapsed” into ψ<sub>'+(k+1)+'</sub>: press the button again — the result will repeat.';
  $('st2').classList.remove('flash');void $('st2').offsetWidth;$('st2').classList.add('flash')};
$('bM100').onclick=async()=>{lastX=null;const rs=Array.from({length:200},()=>Math.random()),tc=t;let M;try{M=await QC.api('post.measureMany',{a:prep.a,ph:prep.ph,rs})}catch(e){return}C=M.C;t0=tc;const P=M.P;hist=new Array(NMAX).fill(0);M.ks.forEach(k=>hist[k]++);histN=200;drawHist(P);render();
  $('st2').innerHTML='200 systems in the same initial state gave different results. The fractions of outcomes (bars) are close to |c<sub>n</sub>|² (black ticks) — this is the probabilistic meaning of the coefficients. The state itself has not changed: each system was measured only once.'};
$('bBack').onclick=()=>{reset();hist=new Array(NMAX).fill(0);histN=0;drawHist();$('st2').textContent='The system is back in its initial state, as before the measurement. Histogram cleared.'};
function drawHist(P){drawBars($('hSvg'),hist.map(h=>histN?h/histN:0),{col:'--ok',ref:P||null})}
$('sig').oninput=e=>{$('sigV').textContent='σ = '+fmt(+e.target.value,3)+' L'};
$('bMX').onclick=async(e,rr)=>{const r=rr!=null?rr:Math.random(),sg=+$('sig').value,tc=t;if(rr==null)lastX={r,C:C.slice(),t0,t:tc};let M;try{M=await QC.api('post.measureX',{C,t:tc,t0,r,sigma:sg})}catch(e){return}const x0=M.x0;
  C=M.C;t0=tc;S.mark=x0;S.ymax=0;S.ymin=0;render();
  const P2=M.P;let nmax=0;P2.forEach((v,k)=>{if(v>0.01)nmax=k+1});
  $('st3').innerHTML='The particle was found at <b>x = '+fmt(x0,3)+' L</b>. Now (in the adopted idealization) Ψ is a Gaussian packet of width ≈ σ, with noticeable states up to n ≈ '+nmax+' (see the probabilities on the right). Start the time evolution: the packet spreads and fully reassembles after T₁.'};
// запуск
$('sig').value=0.04;$('sig').oninput({target:$('sig')});syncAmp();reset();drawHist();
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>{render();drawHist()});

// ---------- section 3 draws its own result; sections 4 (operators) and 5 (expectation value) ----------
let xBefore=null;
function drawX(before,after,x0){const sv=$('xSvg');sv.innerHTML='';const W=520,H=220,L=36,R=12,T=10,B=34,pw=W-L-R,ph=H-T-B;
  let hi=0;[before,after].forEach(a=>a&&a.forEach(v=>hi=Math.max(hi,v)));hi=Math.max(1,hi*1.08);
  const sx=x=>L+x*pw,sy=y=>T+ph-(y/hi)*ph;
  el('rect',{x:L,y:T,width:pw,height:ph,fill:'none',stroke:tok('--line')},sv);
  const area=(a,f,s)=>{let d='M'+sx(0)+','+sy(0);for(let i=0;i<NG;i++)d+=' L'+sx(XS[i]).toFixed(1)+','+sy(a[i]).toFixed(1);d+=' L'+sx(1)+','+sy(0)+'Z';el('path',{d,fill:f,stroke:s,'stroke-width':1.6},sv)};
  if(before)area(before,tok('--soft'),tok('--muted'));if(after)area(after,tok('--lp-bg'),tok('--lp'));
  if(x0!=null)el('line',{x1:sx(x0),y1:T,x2:sx(x0),y2:T+ph,stroke:tok('--warn'),'stroke-width':1.5,'stroke-dasharray':'3 3'},sv);
  [0,0.25,0.5,0.75,1].forEach(x=>el('text',{x:sx(x),y:H-17,'text-anchor':'middle','font-size':12,fill:tok('--muted')},sv,fmt(x,2)));
  el('text',{x:L+pw,y:H-2,'text-anchor':'end','font-size':12,fill:tok('--muted')},sv,'x / L')}
{const old=$('bMX').onclick;$('bMX').onclick=async(...a)=>{let F0;try{F0=await QC.api('post.frame',{C,t,t0})}catch(e){return}xBefore=F0.ps2;await old(...a);
  try{const F1=await QC.api('post.frame',{C,t,t0});drawX(xBefore,F1.ps2,S.mark);drawBars($('xpSvg'),F1.P,{})}catch(e){}}}
// section 4
const OPS=[['H','Ĥ — energy','E₁'],['p','p̂ — momentum','ħ/L'],['x','x̂ — position','L']],FUN=['ψ₁','ψ₂','ψ₃','the state of section 1'];let op='H',fs=0;
const opG=$('opG'),opF=$('opF');
OPS.forEach(([k,n])=>{const b=document.createElement('button');b.type='button';b.className='chip';b.textContent=n;b.onclick=()=>{op=k;opSync();opDraw()};opG.appendChild(b)});
FUN.forEach((n,i)=>{const b=document.createElement('button');b.type='button';b.className='chip';b.textContent=n;b.onclick=()=>{fs=i;opSync();opDraw()};opF.appendChild(b)});
function opSync(){opG.querySelectorAll('.chip').forEach((b,i)=>b.setAttribute('aria-pressed',OPS[i][0]===op));opF.querySelectorAll('.chip').forEach((b,i)=>b.setAttribute('aria-pressed',i===fs))}
const getOp=QC.live('post.operator'),getOne=QC.live('post.prepare');let opBusy=false;
async function opDraw(){let Cs=C,tt=t,tz=t0;if(fs<3){try{Cs=await getOne({a:[0,1,2,3].map(k=>k===fs?1:0),ph:[0,0,0,0]})}catch(e){return}tt=0;tz=0}
  if(!Cs.length)return;let o;try{o=await getOp({C:Cs,t:tt,t0:tz,op})}catch(e){return}
  const u=OPS.find(x=>x[0]===op)[2],sv=$('opSvg');sv.innerHTML='';const W=560,H=250,L=40,R=16,T=12,B=34,pw=W-L-R,ph=H-T-B;
  const cur=[o.are,o.aim,o.re.map(v=>v*o.mean),o.im.map(v=>v*o.mean)];let m=0;cur.forEach(a=>a.forEach(v=>m=Math.max(m,Math.abs(v))));m=Math.max(m*1.1,1e-9);
  const sx=x=>L+x*pw,sy=y=>T+ph/2-(y/m)*(ph/2);
  el('rect',{x:L,y:T,width:pw,height:ph,fill:'none',stroke:tok('--line')},sv);el('line',{x1:L,y1:sy(0),x2:L+pw,y2:sy(0),stroke:tok('--line')},sv);
  const line=(a,col,w,da)=>{let d='';for(let i=0;i<NG;i++)d+=(i?' L':'M')+sx(XS[i]).toFixed(1)+','+sy(a[i]).toFixed(1);const at={d,fill:'none',stroke:col,'stroke-width':w};if(da)at['stroke-dasharray']=da;el('path',at,sv)};
  line(cur[2],tok('--muted'),2.4,'6 4');line(cur[3],tok('--muted'),2.4,'2 4');line(cur[0],tok('--lp'),1.8);line(cur[1],tok('--ln'),1.8);
  [0,0.25,0.5,0.75,1].forEach(x=>el('text',{x:sx(x),y:H-17,'text-anchor':'middle','font-size':12,fill:tok('--muted')},sv,fmt(x,2)));
  el('text',{x:L+pw,y:H-2,'text-anchor':'end','font-size':12,fill:tok('--muted')},sv,'x / L');
  $('opTab').innerHTML='<table class="mtab"><thead><tr><th>quantity</th><th>value</th></tr></thead><tbody><tr><td>mean ⟨A⟩, '+u+'</td><td>'+fmt(o.mean,3)+'</td></tr><tr><td>spread ΔA = ‖ÂΨ − ⟨A⟩Ψ‖, '+u+'</td><td>'+fmt(o.spread,3)+'</td></tr><tr><td>fraction ‖ÂΨ − ⟨A⟩Ψ‖ / ‖ÂΨ‖</td><td>'+fmt(o.rel,3)+'</td></tr></tbody></table>';
  $('st4').innerHTML=o.rel<1e-6?'<b>An eigenfunction:</b> ÂΨ = '+fmt(o.mean,3)+'·Ψ. Measuring this quantity gives '+fmt(o.mean,3)+' '+u+' for certain, with no spread.':'<b>Not an eigenfunction:</b> ÂΨ is not proportional to Ψ. The result of a measurement is not known in advance: on average '+fmt(o.mean,3)+' '+u+', spread '+fmt(o.spread,3)+' '+u+'.'+(op==='p'&&fs<3?' The standing wave ψ<sub>n</sub> is a sum of waves with momenta near ±nπħ/L, so ⟨p⟩ = 0 and the spread is nπ.':'')}
// section 5
function drawContrib(P,E){const sv=$('cSvg');sv.innerHTML='';const W=520,H=220,L=40,R=10,T=12,B=30,pw=W-L-R,ph=H-T-B;let n=4;P.forEach((v,k)=>{if(v>0.003)n=Math.max(n,k+1)});n=Math.min(n,16);
  const w=P.slice(0,n).map((v,k)=>v*(k+1)*(k+1));let hi=Math.max(1,...w)*1.15;const bw=pw/n,sy=y=>T+ph-(y/hi)*ph;
  el('line',{x1:L,y1:T+ph,x2:L+pw,y2:T+ph,stroke:tok('--line')},sv);
  [0,hi/2,hi].forEach(v=>el('text',{x:L-6,y:sy(v)+4,'text-anchor':'end','font-size':11,fill:tok('--muted')},sv,fmt(v,1)));
  w.forEach((v,k)=>{el('rect',{x:L+k*bw+bw*0.15,y:sy(v),width:bw*0.7,height:Math.max(0,T+ph-sy(v)),fill:tok('--accent'),rx:2},sv);if(v>0.005)el('text',{x:L+k*bw+bw/2,y:sy(v)-4,'text-anchor':'middle','font-size':11,fill:tok('--ink')},sv,fmt(v,2));el('text',{x:L+k*bw+bw/2,y:H-12,'text-anchor':'middle','font-size':11,fill:tok('--muted')},sv,String(k+1))});
  el('text',{x:L+pw,y:H-1,'text-anchor':'end','font-size':11,fill:tok('--muted')},sv,'n');
  const cs=P.map((w,k)=>[k,w]).filter(x=>x[1]>1e-6);$('cTxt').innerHTML='⟨E⟩ = '+cs.map(([k,w])=>fmt(w,3)+'·'+((k+1)*(k+1))).join(' + ')+' = <b>'+fmt(E,3)+' E₁</b>. A measurement never gives this number itself if the superposition has more than one state.'}
function drawMean(M){const sv=$('mSvg');sv.innerHTML='';const W=520,H=220,L=44,R=12,T=12,B=36,pw=W-L-R,ph=H-T-B;
  const N=M?M.running.length:1000,E=M?M.mean:0,dE=M?M.dE:0;let lo=1,hi=16;if(M){const r=M.running;lo=Math.min(...r,E-dE);hi=Math.max(...r,E+dE)}const pad=(hi-lo)*0.08||1;lo-=pad;hi+=pad;
  const sx=n=>L+Math.log10(n)/Math.log10(N)*pw,sy=y=>T+ph*(hi-y)/(hi-lo);
  el('rect',{x:L,y:T,width:pw,height:ph,fill:'none',stroke:tok('--line')},sv);
  [1,10,100,1000].filter(n=>n<=N).forEach(n=>el('text',{x:sx(n),y:H-19,'text-anchor':'middle','font-size':11,fill:tok('--muted')},sv,String(n)));
  el('text',{x:L+pw,y:H-1,'text-anchor':'end','font-size':11,fill:tok('--muted')},sv,'N, measurements');
  [lo+pad,(lo+hi)/2,hi-pad].forEach(v=>el('text',{x:L-6,y:sy(v)+4,'text-anchor':'end','font-size':11,fill:tok('--muted')},sv,fmt(v,1)));
  if(!M)return;
  let up='',dn='';for(let j=0;j<=60;j++){const n=Math.pow(N,j/60),e=dE/Math.sqrt(n);up+=(j?' L':'M')+sx(n).toFixed(1)+','+sy(Math.min(hi,E+e)).toFixed(1);dn=' L'+sx(n).toFixed(1)+','+sy(Math.max(lo,E-e)).toFixed(1)+dn}
  el('path',{d:up+dn+'Z',fill:tok('--lp-bg'),stroke:'none'},sv);
  el('line',{x1:L,y1:sy(E),x2:L+pw,y2:sy(E),stroke:tok('--ok'),'stroke-width':2,'stroke-dasharray':'6 4'},sv);
  let d='';M.running.forEach((v,j)=>{d+=(j?' L':'M')+sx(j+1).toFixed(1)+','+sy(v).toFixed(1)});el('path',{d,fill:'none',stroke:tok('--accent'),'stroke-width':1.8},sv);
  const last=M.running[N-1];$('st5').innerHTML='Mean of 1000 measurements: <b>'+fmt(last,3)+' E₁</b>, expectation value ⟨E⟩ = '+fmt(M.mean,3)+' E₁. Deviation '+fmt(Math.abs(last-M.mean),3)+' with a standard error of '+fmt(M.dE/Math.sqrt(N),3)+'.'}
$('bS').onclick=async()=>{const rs=Array.from({length:1000},()=>Math.random());let M;try{M=await QC.api('post.meanSeries',{a:prep.a,ph:prep.ph,rs})}catch(e){return}drawMean(M)};
{let pend=0;const rf=renderF;renderF=function(F,tt){rf(F,tt);if(fs===3&&!playing){clearTimeout(pend);pend=setTimeout(opDraw,80)}}}
{const rs=reset;reset=async function(){await rs();drawMean(null);try{const F=await QC.api('post.frame',{C,t:t0,t0});drawContrib(F.P,F.obs.E)}catch(e){}$('st5').innerHTML='Press “Series”: 1000 systems in the state of section 1, the energy of each measured once.'}}
opSync();opDraw();reset();drawX(null,null,null);drawBars($('xpSvg'),new Array(NMAX).fill(0),{});drawMean(null);
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>{opDraw();drawMean(null)});
/* 2.16.0: a new precision σ repeats the last position measurement by itself — on the state it was made on, with the
   same random number (the same point x₀), so only the width of the packet changes */
$('sig').addEventListener('change',()=>{if(!lastX)return;stop();C=lastX.C.slice();t0=lastX.t0;t=lastX.t;$('bMX').onclick(null,lastX.r)});
/* in block 2 the button of the way of measuring chosen last is the lit one (it was always «Одно измерение») */
(()=>{const one=document.getElementById('bME'),many=document.getElementById('bM100'),back=document.getElementById('bBack');if(!one||!many)return;
  const pick=b=>{[one,many].forEach(x=>{x.classList.toggle('primary',x===b);x.setAttribute('aria-pressed',String(x===b))})};
  one.addEventListener('click',()=>pick(one));many.addEventListener('click',()=>pick(many));if(back)back.addEventListener('click',()=>pick(one));pick(one)})();
