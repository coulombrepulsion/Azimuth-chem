/* Electron density page (Atlas v2).  The map, the axis profile, the bond
   critical point and the values under the cursor come from the Python model
   quas_atlas.core.density (dens.view, dens.point); this script only colours,
   draws contour lines and labels. */
const MOLD={H2:{name:'H₂',atoms:[{Z:1,zeta:1.24,name:'H',zf:1.0},{Z:1,zeta:1.24,name:'H',zf:1.0}],R:1.4,pro:[1,1]},
            HeH:{name:'HeH⁺',atoms:[{Z:2,zeta:2.0925,name:'He',zf:1.6875},{Z:1,zeta:1.24,name:'H',zf:1.0}],R:1.4632,pro:[2,0]}};
// ---------- страница «Электронная плотность» ----------
const NS='http://www.w3.org/2000/svg',$=id=>document.getElementById(id);
function el(tag,a,p,t){const e=document.createElementNS(NS,tag);for(const k in a)e.setAttribute(k,a[k]);if(t!=null)e.textContent=t;if(p)p.appendChild(e);return e}
const fmt=(x,d=3)=>{if(x==null||!isFinite(x))return '—';if(Math.abs(x)<0.5*Math.pow(10,-d))x=0;return x.toFixed(d).replace('-','−')};
const fsig=(x,d=3)=>(x>0.5*Math.pow(10,-d)?'+':'')+fmt(x,d);
const fg=x=>{if(!isFinite(x))return '—';const a=Math.abs(x);if(a===0)return '0';const d=a>=10?1:a>=1?3:a>=0.01?4:5;return fmt(x,d)};
const tok=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
let st={mol:'H2',R:1.4,view:'rho',cont:true};
try{const s=JSON.parse(localStorage.getItem('qc-dens')||'null');if(s&&MOLD[s.mol])st=Object.assign(st,s)}catch(e){}
let M=null;const VIEWS={
 rho:{name:'密度 ρ',title:'ρ(r)，e/玻尔³；对数刻度'},
 drho:{name:'形变密度 Δρ',title:'Δρ = ρ(分子) − ρ(自由原子)，e/玻尔³'},
 lap:{name:'拉普拉斯量 ∇²ρ',title:'∇²ρ，e/玻尔⁵；暖色——∇²ρ < 0（密度集中）'},
 esp:{name:'静电势 φ',title:'φ(r)，原子单位；暖色——φ < 0'}};
// ---------- цвета ----------
const hex=h=>[parseInt(h.slice(1,3),16),parseInt(h.slice(3,5),16),parseInt(h.slice(5,7),16)];
function dark(){const b=hex((tok('--panel')||'#ffffff').padEnd(7,'f'));return b[0]+b[1]+b[2]<300}
function ramp(stops,t){t=Math.max(0,Math.min(1,t));const n=stops.length-1,i=Math.min(n-1,Math.floor(t*n)),f=t*n-i;const a=hex(stops[i]),b=hex(stops[i+1]);return [0,1,2].map(k=>Math.round(a[k]+(b[k]-a[k])*f))}
function pal(){const d=dark();return d?{seq:['#151a22','#1c2c47','#2d5a9c','#6ea2f0','#dde9ff'],zero:'#191f28',warm:['#191f28','#6b2a1c','#c9583a','#ffb08f'],cool:['#191f28','#1d3a66','#3f78cc','#a9c8ff'],line:'rgba(231,234,240,',atom:'#e7eaf0'}
  :{seq:['#ffffff','#d6e3f6','#7fa5dc','#2a62b8','#0f2a5c'],zero:'#ffffff',warm:['#ffffff','#f4c1b0','#d8664a','#8f2410'],cool:['#ffffff','#c3d5f1','#5f8fd3','#163f87'],line:'rgba(27,34,48,',atom:'#1b2230'}}
// u ∈ [−1, 1]: >0 — тёплая сторона (избыток электронов / концентрация / φ<0)
function color(view,v,P){if(view==='rho'){const t=(Math.log10(Math.max(v,1e-6))+3)/3.6;return ramp(P.seq,t)}
  let u;if(view==='drho')u=Math.asinh(v/0.004)/Math.asinh(0.25/0.004);else if(view==='lap')u=Math.asinh(-v/0.05)/Math.asinh(30/0.05);else u=Math.asinh(-v/0.01)/Math.asinh(3/0.01);
  return u>=0?ramp(P.warm,u):ramp(P.cool,-u)}
const LEV={rho:[-3,-2,-1,0].flatMap(k=>[1,2,4,8].map(m=>m*Math.pow(10,k))),
 drho:[0.002,0.005,0.01,0.02,0.05,0.1,0.2].flatMap(v=>[v,-v]),lap:[0.01,0.03,0.1,0.3,1,3,10].flatMap(v=>[v,-v]),esp:[0.002,0.005,0.01,0.02,0.05,0.1,0.2,0.5,1,2].flatMap(v=>[v,-v])};
// ---------- геометрия карты ----------
const CW=720,CH=440,WB=8.6;const SC=CW/WB,HB=CH/SC;
const toZ=px=>M.R/2-WB/2+px/SC,toX=py=>HB/2-py/SC,pxZ=z=>(z-(M.R/2-WB/2))*SC,pyX=x=>(HB/2-x)*SC;
let grid=null,B=null;
const getView=QC.live('dens.view'),getPt=QC.live('dens.point');let PROF=null,ATB=null;
async function compute(){const mol=st.mol,R=st.R,md=MOLD[mol];const d=await getView({mol,R,view:st.view});
  M={key:mol,R,at:md.atoms.map((a,i)=>({...a,z:i?R:0}))};B=d.bcp;grid=d.grid;PROF=d.prof;ATB=d.atB}
function drawMap(){if(!grid)return;const cv=$('map'),ctx=cv.getContext('2d'),P=pal(),{nx,ny,g}=grid;
  /* the canvas at the resolution of the screen — the labels and the scale «1 бор» were blurred */
  {const k=Math.max(1,((cv.getBoundingClientRect().width||CW)/CW)*(window.devicePixelRatio||1));if(cv.width!==Math.round(CW*k)){cv.style.width='100%';cv.style.height='auto';cv.style.aspectRatio=CW+' / '+CH;cv.width=Math.round(CW*k);cv.height=Math.round(CH*k)}ctx.setTransform(cv.width/CW,0,0,cv.height/CH,0,0)}
  const off=document.createElement('canvas');off.width=nx;off.height=ny;const oc=off.getContext('2d'),img=oc.createImageData(nx,ny);
  for(let k=0;k<nx*ny;k++){const c=color(st.view,g[k],P);img.data[4*k]=c[0];img.data[4*k+1]=c[1];img.data[4*k+2]=c[2];img.data[4*k+3]=255}
  oc.putImageData(img,0,0);ctx.imageSmoothingEnabled=true;ctx.clearRect(0,0,CW,CH);ctx.drawImage(off,0,0,CW,CH);
  // изолинии: марширующие квадраты
  if(st.cont){const sx=CW/nx,sy=CH/ny;LEV[st.view].concat(st.view==='rho'?[]:[0]).forEach(L=>{ctx.beginPath();
      for(let j=0;j<ny-1;j++)for(let i=0;i<nx-1;i++){const a=g[j*nx+i]-L,b=g[j*nx+i+1]-L,c=g[(j+1)*nx+i+1]-L,d=g[(j+1)*nx+i]-L;
        const idx=(a>0?8:0)|(b>0?4:0)|(c>0?2:0)|(d>0?1:0);if(idx===0||idx===15)continue;
        const X0=(i+0.5)*sx,Y0=(j+0.5)*sy;const pT=[X0+sx*a/(a-b),Y0],pR=[X0+sx,Y0+sy*b/(b-c)],pB=[X0+sx*d/(d-c),Y0+sy],pL=[X0,Y0+sy*a/(a-d)];
        const seg=(p,q)=>{ctx.moveTo(p[0],p[1]);ctx.lineTo(q[0],q[1])};
        switch(idx){case 1:case 14:seg(pL,pB);break;case 2:case 13:seg(pB,pR);break;case 3:case 12:seg(pL,pR);break;case 4:case 11:seg(pT,pR);break;
          case 5:seg(pL,pT);seg(pB,pR);break;case 10:seg(pT,pR);seg(pL,pB);break;case 6:case 9:seg(pT,pB);break;case 7:case 8:seg(pL,pT);break}}
      ctx.strokeStyle=P.line+(L===0?'0.85)':'0.38)');ctx.lineWidth=L===0?1.8:1;ctx.stroke()})}
  // ось, ядра, КТС
  ctx.strokeStyle=P.line+'0.25)';ctx.lineWidth=1;ctx.setLineDash([2,4]);ctx.beginPath();ctx.moveTo(0,pyX(0));ctx.lineTo(CW,pyX(0));ctx.stroke();ctx.setLineDash([]);
  M.at.forEach(a=>{const X=pxZ(a.z),Y=pyX(0);ctx.fillStyle=P.atom;ctx.beginPath();ctx.arc(X,Y,4.5,0,2*Math.PI);ctx.fill();ctx.font='600 15px "Golos Text",system-ui,sans-serif';ctx.textAlign='center';
    ctx.lineWidth=4;ctx.strokeStyle=dark()?'rgba(17,21,28,.85)':'rgba(255,255,255,.85)';ctx.strokeText(a.name,X,Y-12);ctx.fillText(a.name,X,Y-12)});
  if(B){const X=pxZ(B.z),Y=pyX(0);ctx.fillStyle=tok('--ok');ctx.beginPath();ctx.moveTo(X,Y-7);ctx.lineTo(X+7,Y);ctx.lineTo(X,Y+7);ctx.lineTo(X-7,Y);ctx.closePath();ctx.fill();ctx.strokeStyle=P.atom;ctx.lineWidth=1;ctx.stroke()}
  // масштаб 1 бор
  ctx.fillStyle=P.atom;ctx.fillRect(16,CH-22,SC,2.5);ctx.font='12px "Golos Text",system-ui,sans-serif';ctx.textAlign='left';ctx.fillText('1 玻尔 = 0.529 Å',16,CH-30);
  if(pin){ctx.strokeStyle=P.atom;ctx.lineWidth=1.5;ctx.beginPath();ctx.arc(pxZ(pin.z),pyX(pin.x),6,0,2*Math.PI);ctx.stroke()}
  // шкала цвета
  const n=24,cs=[];for(let k=0;k<=n;k++){const t=k/n;let c;if(st.view==='rho')c=color('rho',Math.pow(10,-3+3.6*t),P);else{const u=2*t-1;c=u>=0?ramp(P.warm,u):ramp(P.cool,-u)}cs.push(`rgb(${c})`)}
  $('cbar').style.background='linear-gradient(90deg,'+cs.join(',')+')';
  const lab={rho:['0.001','0.01','0.1','1','4'],drho:['−0.25（流出）','0','+0.25（流入）'],lap:['+30（稀疏）','0','−30（集中）'],esp:['+3','0','−3']}[st.view];
  $('cbl').innerHTML=lab.map(t=>`<span>${t}</span>`).join('');$('mapTitle').textContent=VIEWS[st.view].title}
// ---------- точка под курсором ----------
let pin=null;
async function showPoint(x,z){if(!M)return;let q;try{q=await getPt({mol:M.key,R:M.R,x,z})}catch(e){return}const r=q.rho,d=q.drho,l=q.lap,p=q.esp;
  $('pt').innerHTML=`<span>坐标 (z, x)</span><b>${fmt(z,2)}; ${fmt(x,2)} 玻尔</b><span>ρ</span><b>${fg(r)}</b><span>Δρ</span><b>${fsig(d,4)}</b><span>∇²ρ</span><b>${fsig(l,3)}</b><span>φ</span><b>${fsig(p,4)}</b>`}
function evXY(e){const r=$('map').getBoundingClientRect();const px=(e.clientX-r.left)/r.width*CW,py=(e.clientY-r.top)/r.height*CH;return {z:toZ(px),x:toX(py)}}
$('map').addEventListener('pointermove',e=>{const q=evXY(e);showPoint(q.x,q.z)});
$('map').addEventListener('pointerdown',e=>{pin=evXY(e);showPoint(pin.x,pin.z);drawMap()});
$('map').addEventListener('pointerleave',()=>{if(pin)showPoint(pin.x,pin.z)});
// ---------- КТС и пояснения ----------
function drawInfo(){const b=$('bcp'),H2=st.mol==='H2';
  if(B)b.innerHTML=`<span>位置</span><b>z = ${fmt(B.z,3)} 玻尔${H2?'（键中点）':`（从 He 到 H 的 ${fmt(B.z/M.R*100,0)} % 处）`}</b><span>ρ<sub>BCP</sub></span><b>${fmt(B.rho,4)}</b><span>曲率 λ₁ = λ₂, λ₃</span><b>${fmt(B.l1,3)}, ${fmt(B.l3,3)}</b><span>∇²ρ = λ₁ + λ₂ + λ₃</span><b>${fsig(B.lap,3)}</b><span>BCP 处的 Δρ</span><b>${fsig(B.drho,4)}</b>`;
  else b.innerHTML='<span>未找到</span><b>ρ 沿键轴在两核之间没有极小值</b>';
  let t='';const v=st.view;
  if(v==='rho')t='密度极大值位于核上。在两核之间 ρ 经过一个鞍点——<b>键临界点</b>（菱形）：该处 ∇ρ = 0，沿键方向 ρ 极小（λ₃ > 0），垂直方向极大（λ₁, λ₂ < 0）。按巴德的观点，存在这样的点以及连接两核的最大密度线是化学键的标志。';
  else if(v==='drho')t='Δρ 显示形成分子时电子相对于自由原子向何处移动（'+(H2?'两个 H 原子，ζ = 1':'ζ = 1.6875 的 He 和裸质子：HeH⁺ → He + H⁺')+'）。暖色区域——电子流入，冷色——流出。Δρ 在全空间的积分为零：电子只是重新分布。'+(H2?' 在 H₂ 中，密度在键上积累并向核收缩：分子函数的 ζ = 1.24 > 1。':' 在 HeH⁺ 中，He 的电子对部分转移到质子上：H 一侧的密度增加。');
  else if(v==='lap')t='∇²ρ < 0——密度局部集中（高于邻域平均值），∇²ρ > 0——稀疏。按巴德的观点，键临界点处 ∇²ρ < 0 是共价（“共享”）键的特征，∇²ρ > 0 则对应闭壳层相互作用：离子键、氢键、范德华相互作用。'+(B?(B.lap<0?' 此处 ∇²ρ<sub>BCP</sub> < 0：共价型。':' 此处 ∇²ρ<sub>BCP</sub> > 0：闭壳层相互作用——在大 R 下原子几乎不成键。'):'');
  else t='φ 由带正电的核和带负电的电子云共同产生。程序中彩色的“ESP 图”显示的正是这个量：它决定带电试剂从哪里接近。'+(H2?' 对中性的 H₂，分子附近的静电势为正（核未被完全屏蔽），而在赤道面远处略为负：这体现了分子的四极矩。':' HeH⁺ 是阳离子，因此处处 φ > 0，在核附近最强。');
  if(!B)t+=st.mol==='H2'?' <br><b>没有临界点：</b>在如此压缩下，两核处的密度极大值合并为一个，ρ 沿键轴没有极小值。':' <br><b>没有临界点：</b>HeH⁺ 中 H 上的电子很少，而高斯函数在核处没有尖点，因此 H 上不会出现自己的密度极大值。这是最小高斯基组的缺陷：精确密度在每个核上都有尖点。增大 R——约从 1.74 玻尔起该点就会出现。';
  $('txt').innerHTML=t;
  $('mapLeg').innerHTML='<span>● 核</span><span style="color:var(--ok)">◆ 键临界点</span>'+(st.view!=='rho'?'<span>粗等值线——零值</span>':'<span>等值线 0.001·{1, 2, 4, 8}·10ᵏ</span>')}
// ---------- профиль ----------
function drawProf(){const svg=$('prof');svg.innerHTML='';const W=900,H=260,L=70,Rr=16,T=14,Bt=36;const z0=M.R/2-WB/2,z1=M.R/2+WB/2,v=st.view;
  const tr={rho:[x=>Math.log10(Math.max(x,1e-7)),[1e-3,1e-2,0.1,1,10]],drho:[x=>Math.asinh(x/0.004),[-0.2,-0.05,-0.01,0,0.01,0.05,0.2]],lap:[x=>Math.asinh(x/0.05),[-10,-1,-0.1,0,0.1,1,10]],esp:[x=>Math.asinh(x/0.01),[-0.01,0,0.01,0.1,1,10]]}[v];
  const N=700,zs=[...Array(N+1)].map((_,i)=>z0+(z1-z0)*i/N),ys=zs.map((z,i)=>tr[0](PROF[i]));const tk=tr[1].map(tr[0]);
  const lo=Math.min(...tk,...ys.filter(isFinite)),hi=Math.max(...tk.filter(t=>t<=Math.max(...ys)+0.5),...ys.filter(isFinite));
  const X=z=>L+(z-z0)/(z1-z0)*(W-L-Rr),Y=y=>H-Bt-(y-lo)/(hi-lo||1)*(H-T-Bt);
  tr[1].forEach((t,i)=>{const y=tk[i];if(y<lo-1e-9||y>hi+1e-9)return;el('line',{x1:L,x2:W-Rr,y1:Y(y),y2:Y(y),stroke:t===0?'var(--muted)':'var(--line)','stroke-width':1},svg);el('text',{x:L-6,y:Y(y)+4,'text-anchor':'end','font-size':12,fill:'var(--muted)'},svg,fmt(t,t===0?0:Math.abs(t)<0.01?3:Math.abs(t)<1?2:0))});
  for(let z=Math.ceil(z0);z<=z1;z++){el('text',{x:X(z),y:H-Bt+17,'text-anchor':'middle','font-size':12,fill:'var(--muted)'},svg,String(z).replace('-','−'))}
  el('text',{x:(L+W-Rr)/2,y:H-4,'text-anchor':'middle','font-size':12,fill:'var(--muted)'},svg,'沿键轴的 z，玻尔');
  M.at.forEach(a=>{el('line',{x1:X(a.z),x2:X(a.z),y1:T,y2:H-Bt,stroke:'var(--muted)','stroke-dasharray':'3 3','stroke-width':1},svg);el('text',{x:X(a.z),y:T+10,'text-anchor':'middle','font-size':12.5,fill:'var(--ink)','font-weight':600},svg,a.name)});
  if(B)el('path',{d:`M${X(B.z)},${Y(tr[0](ATB))-8} l6,8 l-6,8 l-6,-8 z`,fill:'var(--ok)'},svg);
  el('path',{d:zs.map((z,i)=>(i?'L':'M')+X(z).toFixed(1)+','+Y(Math.max(lo,Math.min(hi,ys[i]))).toFixed(1)).join(''),fill:'none',stroke:'var(--accent)','stroke-width':2.4},svg);
  $('profLeg').innerHTML=`<span><i class="sw" style="border-color:var(--accent)"></i>x = 0 处的${VIEWS[v].name}</span><span>${v==='rho'?'对数刻度':'刻度向两端压缩（asinh），以便同时看清小值和大值'}</span>`}
// ---------- управление ----------
function chips(id,items,cur,set){const g=$(id);g.innerHTML='';items.forEach(([v,l])=>{const b=document.createElement('button');b.className='chip';b.type='button';b.innerHTML=l;b.setAttribute('aria-pressed',v===cur);b.onclick=()=>set(v);g.appendChild(b)})}
async function all(){try{localStorage.setItem('qc-dens',JSON.stringify(st))}catch(e){}
  chips('molG',Object.entries(MOLD).map(([k,m])=>[k,m.name]),st.mol,v=>{st.mol=v;st.R=MOLD[v].R;pin=null;all()});
  chips('viewG',Object.entries(VIEWS).map(([k,o])=>[k,o.name]),st.view,v=>{st.view=v;all()});
  $('R').value=st.R;$('Rv').textContent=fmt(st.R,2)+' 玻尔 = '+fmt(st.R*0.529177,3)+' Å';$('cont').checked=st.cont;
  try{await compute()}catch(e){return}drawMap();drawInfo();drawProf();if(pin)showPoint(pin.x,pin.z);else if(B)showPoint(0,B.z);else showPoint(0,M.R/2)}
let rT=null;$('R').oninput=e=>{st.R=+e.target.value;$('Rv').textContent=fmt(st.R,2)+' 玻尔 = '+fmt(st.R*0.529177,3)+' Å';pumpR()};
/* while R is dragged the map follows it (one calculation at a time, the latest R wins) and each new map fades in
   over the old one */
let rBusy=0,rWant=0,FADE=0;async function pumpR(){rWant=1;if(rBusy)return;rBusy=1;while(rWant){rWant=0;FADE=1;await all();FADE=0}rBusy=0}
{const draw0=drawMap;drawMap=function(){const cv=$('map');if(!FADE||!grid||!cv.width||matchMedia('(prefers-reduced-motion: reduce)').matches){drawMap.id=(drawMap.id||0)+1;return draw0()}
  const old=document.createElement('canvas');old.width=cv.width;old.height=cv.height;old.getContext('2d').drawImage(cv,0,0);draw0();
  const nw=document.createElement('canvas');nw.width=cv.width;nw.height=cv.height;nw.getContext('2d').drawImage(cv,0,0);
  const ctx=cv.getContext('2d'),t0=performance.now(),id=(drawMap.id=(drawMap.id||0)+1);
  (function step(){if(id!==drawMap.id||old.width!==cv.width)return;const t=Math.min(1,(performance.now()-t0)/220);ctx.save();ctx.setTransform(1,0,0,1,0,0);ctx.clearRect(0,0,cv.width,cv.height);
    ctx.globalAlpha=1;ctx.drawImage(nw,0,0);ctx.globalAlpha=1-t;ctx.drawImage(old,0,0);ctx.restore();if(t<1)requestAnimationFrame(step)})()}}
$('Req').onclick=()=>{st.R=MOLD[st.mol].R;all()};$('cont').onchange=e=>{st.cont=e.target.checked;drawMap()};
new MutationObserver(()=>drawMap()).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>drawMap());
all();
