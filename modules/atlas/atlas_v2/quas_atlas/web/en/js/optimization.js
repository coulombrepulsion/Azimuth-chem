/* Geometry-optimisation page (Atlas v2).  The spline surface of H2O, the four
   optimisers, the minimum, contours and harmonic frequencies come from
   quas_atlas.core.optimization (opt.static, opt.runs); this script draws and
   animates. */
const NS='http://www.w3.org/2000/svg',$=id=>document.getElementById(id);
function el(tag,a,p,t){const e=document.createElementNS(NS,tag);for(const k in a)e.setAttribute(k,a[k]);if(t!=null)e.textContent=t;if(p)p.appendChild(e);return e}
const fmt=(x,d=2)=>{if(x==null||!isFinite(x))return '—';if(Math.abs(x)<0.5*Math.pow(10,-d))x=0;return x.toFixed(d).replace('-','−')};
function chips(id,items,cur,set){const g=$(id);g.innerHTML='';items.forEach(([v,l])=>{const b=document.createElement('button');b.className='chip';b.type='button';b.innerHTML=l;b.setAttribute('aria-pressed',v===cur);b.onclick=()=>set(v);g.appendChild(b)})}
const MET=[['sd','steepest descent'],['sdls','descent with line search'],['nr','Newton–Raphson'],['bfgs','BFGS']];
const MCOL={sd:'var(--warn)',sdls:'var(--rho-l)',nr:'var(--ok)',bfgs:'var(--accent)'};
const st={m:'sd',step:0.5,start:[1.10,130],k:0,runs:{}};
let MIN=null,SEG=null,STAT=null;
const LEV=[1,2,5,10,20,50,100,200];
// карта: геометрия
const W=540,H=440,L=58,R=14,T=14,B=42,pw=W-L-R,ph=H-T-B,r0=0.80,r1=1.20,t0=80,t1=140;
const sx=r=>L+(r-r0)/(r1-r0)*pw,sy=t=>T+ph*(t1-t)/(t1-t0),ix=x=>r0+(x-L)/pw*(r1-r0),iy=y=>t1-(y-T)/ph*(t1-t0);
const liveR=QC.live('opt.runs');
async function runs(){let Z;try{Z=await liveR({start:st.start,step:st.step})}catch(e){return false}Object.values(Z).forEach(q=>q.path.forEach(p=>{if(p.out){p.e=NaN;p.g=NaN;p.de=NaN}}));st.runs=Z;return true}
function drawMap(){const sv=$('map');sv.innerHTML='';
  el('rect',{x:L,y:T,width:pw,height:ph,fill:'var(--panel)',stroke:'var(--line)'},sv);
  SEG.forEach((segs,li)=>{let d='';segs.forEach(([a,b])=>{d+='M'+sx(a[0]).toFixed(1)+','+sy(a[1]).toFixed(1)+'L'+sx(b[0]).toFixed(1)+','+sy(b[1]).toFixed(1)});
    el('path',{d,fill:'none',stroke:'var(--muted)','stroke-width':li<3?1.4:1,opacity:0.35+0.08*(LEV.length-li)},sv)});
  [0.8,0.9,1.0,1.1,1.2].forEach(r=>el('text',{x:sx(r),y:H-B+16,'text-anchor':'middle','font-size':11,fill:'var(--muted)'},sv,fmt(r,1)));
  [80,90,100,110,120,130,140].forEach(t=>el('text',{x:L-6,y:sy(t)+4,'text-anchor':'end','font-size':11,fill:'var(--muted)'},sv,String(t)));
  el('text',{x:L+pw,y:H-6,'text-anchor':'end','font-size':11.5,fill:'var(--muted)'},sv,'r(O–H), Å');el('text',{x:4,y:T+10,'font-size':11.5,fill:'var(--muted)'},sv,'θ, °');
  // минимум
  el('path',{d:`M${sx(MIN.r)-6},${sy(MIN.t)}h12M${sx(MIN.r)},${sy(MIN.t)-6}v12`,stroke:'var(--ink)','stroke-width':2},sv);
  // путь
  const q=st.runs[st.m],pts=q.path.slice(0,st.k+1).filter(p=>p.rt&&!p.out);
  if(pts.length>1){let d='';pts.forEach((p,i)=>{d+=(i?'L':'M')+sx(p.rt[0]).toFixed(1)+','+sy(p.rt[1]).toFixed(1)});el('path',{d,fill:'none',stroke:MCOL[st.m],'stroke-width':2.2},sv)}
  pts.forEach((p,i)=>el('circle',{cx:sx(p.rt[0]),cy:sy(p.rt[1]),r:i?3:5.5,fill:i?MCOL[st.m]:'var(--panel)',stroke:MCOL[st.m],'stroke-width':2},sv));
  const hit=el('rect',{x:L,y:T,width:pw,height:ph,fill:'transparent'},sv);
  hit.addEventListener('click',ev=>{const b=sv.getBoundingClientRect(),x=(ev.clientX-b.left)/b.width*W,y=(ev.clientY-b.top)/b.height*H;st.start=[ix(x),iy(y)];st.k=0;runs().then(ok=>{if(ok)draw()})})}
function drawConv(){const sv=$('cv');sv.innerHTML='';const W2=520,H2=250,l=46,r=12,t=10,b=32,w=W2-l-r,h=H2-t-b;
  const nmax=Math.min(100,Math.max(...MET.map(([m])=>st.runs[m].path.length-1),5));const y0=-6,y1=0;
  const X=i=>l+i/nmax*w,Y=g=>t+h*(y1-Math.max(y0,Math.min(y1,Math.log10(g))))/(y1-y0);
  el('rect',{x:l,y:t,width:w,height:h,fill:'none',stroke:'var(--line)'},sv);
  [-6,-4,-2,0].forEach(e=>{el('line',{x1:l,y1:Y(Math.pow(10,e)),x2:l+w,y2:Y(Math.pow(10,e)),stroke:'var(--line)','stroke-dasharray':'2 4'},sv);el('text',{x:l-5,y:Y(Math.pow(10,e))+4,'text-anchor':'end','font-size':11,fill:'var(--muted)'},sv,{'-6':'10⁻⁶','-4':'10⁻⁴','-2':'10⁻²','0':'1'}[e])});
  el('line',{x1:l,y1:Y(1e-5),x2:l+w,y2:Y(1e-5),stroke:'var(--ink)','stroke-dasharray':'5 4',opacity:0.5},sv);
  [0,Math.round(nmax/2),nmax].forEach(i=>el('text',{x:X(i),y:H2-b+15,'text-anchor':'middle','font-size':11,fill:'var(--muted)'},sv,String(i)));
  el('text',{x:l+w,y:H2-4,'text-anchor':'end','font-size':11.5,fill:'var(--muted)'},sv,'step number');
  MET.forEach(([m])=>{const p=st.runs[m].path.filter(z=>isFinite(z.g)),cur=m===st.m,lim=cur?st.k:p.length-1;let d='';p.slice(0,lim+1).forEach((z,i)=>{if(i>nmax)return;d+=(i?'L':'M')+X(i).toFixed(1)+','+Y(z.g).toFixed(1)});
    el('path',{d,fill:'none',stroke:MCOL[m],'stroke-width':cur?2.6:1.2,opacity:cur?1:0.45},sv)})}
function drawCmp(){const nm=Object.fromEntries(MET);let h='<table class="mtab"><thead><tr><th class="l">algorithm</th><th>steps</th><th>energies</th><th>gradients</th><th>Hessians</th></tr></thead><tbody>';
  MET.forEach(([m])=>{const q=st.runs[m];h+=`<tr${m===st.m?' class="cur"':''}><td class="l"><span style="color:${MCOL[m]}">●</span> ${nm[m]}</td><td>${q.stop==='conv'?q.path.length-1:(q.stop==='out'?'left the map':'&gt; 200')}</td><td>${q.nE}</td><td>${q.nG}</td><td>${q.nH}</td></tr>`});
  $('cmp').innerHTML=h+'</tbody></table>'}
const TXT={sd:'<b>Steepest descent</b>: a step of fixed length α along −g. The valley is elongated: the curvature along r is about 6 times that along θ, so the gradient points not at the minimum but across the valley. A small step means slow creeping, a large one a zigzag across the valley, and for α &gt; 2/λ<sub>max</sub> ≈ 1.6 the oscillations grow.',
  sdls:'<b>Descent with line search</b>: at each step the energy minimum along −g is found. The next gradient is then perpendicular to the previous one, and the path goes as a “staircase”. Fewer steps, but each needs dozens of energy evaluations — compare the table columns.',
  nr:'<b>Newton–Raphson</b>: the surface is approximated by a paraboloid with the exact Hessian, and the step is −H⁻¹g. Near the minimum convergence is quadratic — 3–4 steps suffice. But the Hessian is expensive: in a real calculation it costs as much as dozens of gradients. And if the Hessian has a negative eigenvalue, the Newton step leads to a saddle point — the basis of transition state searches.',
  bfgs:'<b>BFGS</b> (a quasi-Newton method): it starts from the unit matrix instead of the Hessian and refines it from how the gradient changes from step to step. It is almost as fast as Newton, but without second derivatives. This is how geometry optimization works in most quantum chemistry programs.'};
function drawText(){const q=st.runs[st.m],p=q.path[Math.min(st.k,q.path.length-1)];
  $('kV').innerHTML=`step ${Math.min(st.k,q.path.length-1)} of ${q.path.length-1}`+(p.rt&&isFinite(p.e)?`: r = ${fmt(p.rt[0],4)} Å, θ = ${fmt(p.rt[1],2)}°, E − E<sub>min</sub> = ${fmt(p.de,3)} kJ/mol`:'');
  let t=TXT[st.m];if(q.stop==='out')t+=' <b>With this step length the optimization left the map.</b>';else if(q.stop!=='conv')t+=' <b>No convergence within 200 steps.</b>';
  $('st1').innerHTML=t}
function draw(){if(!st.runs.sd)return;chips('mG',MET,st.m,v=>{st.m=v;st.k=0;draw()});$('stepRow').hidden=st.m!=='sd';$('step').value=st.step;$('stepV').textContent='α = '+fmt(st.step,2);
  drawMap();drawConv();drawCmp();drawText()}
let anim=null;
$('bStep').onclick=()=>{const n=st.runs[st.m].path.length-1;if(st.k<n)st.k++;draw()};
$('bRun').onclick=()=>{if(anim)clearInterval(anim);const n=st.runs[st.m].path.length-1;if(st.k>=n)st.k=0;const red=matchMedia('(prefers-reduced-motion: reduce)').matches;
  if(red){st.k=n;draw();return}anim=setInterval(()=>{st.k++;draw();if(st.k>=n){clearInterval(anim);anim=null}},Math.max(25,Math.min(250,3000/n)))};
$('bReset').onclick=()=>{if(anim){clearInterval(anim);anim=null}st.k=0;draw()};
$('step').oninput=e=>{st.step=+e.target.value;st.k=0;runs().then(ok=>{if(ok)draw()})};
// ---------- 2. минимум и частоты ----------
function sect2(){const ev=STAT.ev,f=STAT.f;
  $('res').innerHTML='<table class="mtab"><thead><tr><th class="l"></th><th>HF/6-31G*</th><th>experiment</th></tr></thead><tbody>'+
   `<tr><td class="l">r(O–H), Å</td><td>${fmt(MIN.r,3)}</td><td>0.958</td></tr>`+
   `<tr><td class="l">θ(H–O–H), °</td><td>${fmt(MIN.t,1)}</td><td>104.5</td></tr>`+
   `<tr><td class="l">Hessian eigenvalues, E<sub>h</sub>/bohr² and E<sub>h</sub>/rad²</td><td>${fmt(ev[0],3)}; ${fmt(ev[1],3)}</td><td></td></tr>`+
   `<tr><td class="l">bending vibration ν₂, cm⁻¹</td><td>${fmt(f[0],0)}</td><td>1649 (harmonic), 1595 (observed)</td></tr>`+
   `<tr><td class="l">symmetric stretch ν₁, cm⁻¹</td><td>${fmt(f[1],0)}</td><td>3832 (harmonic), 3657 (observed)</td></tr></tbody></table>`;
  $('st2').innerHTML=`Both eigenvalues of the Hessian on this map are positive: a minimum on the map has been found, not a saddle point. It is a minimum only among symmetric structures with equal O–H bonds. The third vibration, the antisymmetric stretch (B₂), breaks the equality of the bonds and is not visible on the map; to confirm a full minimum it must be checked too. In general the Hessian is checked along all vibrational coordinates after removing translations and rotations: at a minimum all frequencies are real. The O–H bond in HF is a little shorter than the experimental one: without correlation bonds come out shorter and the surface near the minimum steeper, although the HF bond energy is at the same time too low. So HF harmonic frequencies are too high by about 10 %; in practice they are multiplied by a scaling factor ≈ 0.9.`}
(async()=>{try{STAT=await QC.api('opt.static',{})}catch(e){return}MIN=STAT.MIN;SEG=STAT.SEG;sect2();if(await runs())draw()})();
