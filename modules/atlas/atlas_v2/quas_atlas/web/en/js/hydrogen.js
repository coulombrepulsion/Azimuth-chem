/* Hydrogen atom page (Atlas v2).  Radial functions, the orbital slice, the
   point cloud, energy levels and spectral series come from
   quas_atlas.core.hydrogen (h.map, h.radial, h.cloud, h.levels, h.quiz);
   this script colours, projects and draws. */
// ---------- страница «Атом водорода и атомные орбитали» (ат. ед.) ----------
const NS='http://www.w3.org/2000/svg',$=id=>document.getElementById(id);
function el(tag,a,p,t){const e=document.createElementNS(NS,tag);for(const k in a)e.setAttribute(k,a[k]);if(t!=null)e.textContent=t;if(p)p.appendChild(e);return e}
const tok=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const FR=(a,b)=>'<span class=fr><span>'+a+'</span><span>'+b+'</span></span>';
const fmt=(x,d=2)=>{if(!isFinite(x))return '—';if(Math.abs(x)<0.5*Math.pow(10,-d))x=0;return x.toFixed(d).replace('-','−')};
// вещественные угловые функции (нормированные)
const ORB=[
 {id:'s',l:0,h:'s',node:'none'},
 {id:'pz',l:1,h:'p<sub>z</sub>',node:'the xy plane'},
 {id:'px',l:1,h:'p<sub>x</sub>',node:'the yz plane'},
 {id:'py',l:1,h:'p<sub>y</sub>',node:'the xz plane'},
 {id:'dz2',l:2,h:'d<sub>z²</sub>',node:'two cones at 54.7° to the z axis'},
 {id:'dxz',l:2,h:'d<sub>xz</sub>',node:'the xy and yz planes'},
 {id:'dyz',l:2,h:'d<sub>yz</sub>',node:'the xy and xz planes'},
 {id:'dxy',l:2,h:'d<sub>xy</sub>',node:'the xz and yz planes'},
 {id:'dx2y2',l:2,h:'d<sub>x²−y²</sub>',node:'the planes x = y and x = −y'},
 {id:'fz3',l:3,h:'f<sub>z³</sub>',node:'the xy plane and two cones'},
 {id:'fxz2',l:3,h:'f<sub>xz²</sub>',node:'the yz plane and two cones'},
 {id:'fyz2',l:3,h:'f<sub>yz²</sub>',node:'the xz plane and two cones'},
 {id:'fxyz',l:3,h:'f<sub>xyz</sub>',node:'the xy, xz and yz planes'},
 {id:'fzx2y2',l:3,h:'f<sub>z(x²−y²)</sub>',node:'the xy plane and the planes x = ±y'},
 {id:'fx3',l:3,h:'f<sub>x(x²−3y²)</sub>',node:'three planes through the z axis'},
 {id:'fy3',l:3,h:'f<sub>y(3x²−y²)</sub>',node:'three planes through the z axis'}];
const LN='spdf',ZS=[[1,'H'],[2,'He⁺'],[3,'Li²⁺']];
let n=2,oi=1,Z=1,plane='xz',view='psi',series=2,yaw=30,pitch=20,pts=[],CL=1;
const orb=()=>ORB[oi];
function rgb(c){const cv=document.createElement('canvas').getContext('2d');cv.fillStyle=c;const s=cv.fillStyle;if(s[0]==='#')return [parseInt(s.slice(1,3),16),parseInt(s.slice(3,5),16),parseInt(s.slice(5,7),16)];const m=s.match(/\d+/g);return m.slice(0,3).map(Number)}
// ---------- срез ----------
const liveM=QC.live('h.map'),liveR=QC.live('h.radial'),liveC=QC.live('h.cloud'),liveL=QC.live('h.levels');
/* the canvases are drawn at the displayed size times devicePixelRatio (they were stretched
   from 420 px and looked pixelated); the field keeps its 420×420 grid, is scaled smoothly, and the
   nodal lines are contours of ψ = 0 (marching squares with linear interpolation), drawn as vectors */
function hiDPI(cv,ar){const w=cv.getBoundingClientRect().width||cv.width,d=Math.min(3,window.devicePixelRatio||1);const W=Math.max(1,Math.round(w*d)),H=Math.max(1,Math.round(w*ar*d));if(cv.width!==W||cv.height!==H){cv.width=W;cv.height=H}return [W,H,d]}
const FW=420,FH=420;let lastM=null;
async function drawMap(){let M;try{M=await liveM({n,oi,Z,plane,W:FW,H:FH})}catch(e){return}lastM=M;paintMap()}
function paintMap(){const M=lastM;if(!M)return;const cv=$('map'),[W,H,dp]=hiDPI(cv,1),ctx=cv.getContext('2d'),L=M.L;
  const off=document.createElement('canvas');off.width=FW;off.height=FH;const oc=off.getContext('2d'),img=oc.createImageData(FW,FH);
  const P=rgb(tok('--lp')),Nn=rgb(tok('--ln')),B=rgb(tok('--soft'));const V=new Float32Array(Uint8Array.from(atob(M.f32),c=>c.charCodeAt(0)).buffer);let mx=M.mx;
  const zero=mx<1e-8;
  for(let j=0;j<FH;j++)for(let i=0;i<FW;i++){const v=V[j*FW+i]/(mx||1);let t=view==='psi'?Math.pow(Math.abs(v),0.55):v*v;const c=v>=0?P:Nn;const k=4*(j*FW+i);
    for(let q=0;q<3;q++)img.data[k+q]=B[q]*(1-t)+c[q]*t;img.data[k+3]=255}
  oc.putImageData(img,0,0);ctx.imageSmoothingEnabled=true;ctx.imageSmoothingQuality='high';ctx.drawImage(off,0,0,W,H);
  if(!zero){const tiny=mx*1e-6,sx=W/FW,sy=H/FH,X=i=>(i+0.5)*sx,Y=j=>(j+0.5)*sy;ctx.beginPath();
    const cut=(a,b)=>a*b<0&&Math.abs(a-b)>tiny;
    for(let j=0;j<FH-1;j++)for(let i=0;i<FW-1;i++){const a=V[j*FW+i],b=V[j*FW+i+1],c=V[(j+1)*FW+i+1],d=V[(j+1)*FW+i],q=[];
      if(cut(a,b))q.push([X(i+a/(a-b)),Y(j)]);if(cut(b,c))q.push([X(i+1),Y(j+b/(b-c))]);if(cut(c,d))q.push([X(i+1-c/(c-d)),Y(j+1)]);if(cut(d,a))q.push([X(i),Y(j+1-d/(d-a))]);
      for(let s=0;s+1<q.length;s+=2){ctx.moveTo(q[s][0],q[s][1]);ctx.lineTo(q[s+1][0],q[s+1][1])}}
    ctx.strokeStyle=tok('--ink');ctx.lineWidth=1.2*dp;ctx.globalAlpha=0.85;ctx.stroke();ctx.globalAlpha=1}
  ctx.fillStyle=tok('--muted');ctx.font=(13*dp)+'px sans-serif';const ax=plane==='xz'?['x','z']:plane==='xy'?['x','y']:['y','z'];
  ctx.strokeStyle=tok('--muted');ctx.lineWidth=dp;ctx.globalAlpha=0.45;ctx.beginPath();ctx.moveTo(W/2,0);ctx.lineTo(W/2,H);ctx.moveTo(0,H/2);ctx.lineTo(W,H/2);ctx.stroke();ctx.globalAlpha=1;
  ctx.fillText(ax[0],W-14*dp,H/2-6*dp);ctx.fillText(ax[1],W/2+6*dp,14*dp);ctx.fillText('±'+fmt(L,1).replace('.0','')+' a₀',8*dp,H-8*dp);
  $('mapT').innerHTML='Cross-section of '+n+orb().h+' in the plane '+plane+(view==='psi'?' (ψ)':' (|ψ|²)')+(zero?' — <b>the whole plane is nodal: ψ = 0</b>':'')}
// ---------- радиальные функции ----------
async function radial(){let Q;try{Q=await liveR({n,oi,Z})}catch(e){return}lastR=Q;drawHist();const sv=$('rad');sv.innerHTML='';const W=520,H=300,Lm=48,Rm=14,T=14,Bm=34,pw=W-Lm-Rm,ph=H-T-Bm,l=orb().l,L=Q.L;
  const N=600,rs=Q.rs,Rv=Q.Rv,Pv=Q.Pv;
  const mR=Q.mR,mP=Q.mP;const sx=r=>Lm+r/L*pw,y0=T+ph*0.55,syR=v=>y0-v/mR*ph*0.5,syP=v=>y0-v/mP*ph*0.5;
  el('line',{x1:Lm,y1:y0,x2:Lm+pw,y2:y0,stroke:tok('--line')},sv);el('line',{x1:Lm,y1:T,x2:Lm,y2:T+ph,stroke:tok('--line')},sv);
  const step=L>40?10:L>20?5:L>8?2:1;for(let r=0;r<=L;r+=step)el('text',{x:sx(r),y:H-16,'text-anchor':'middle','font-size':11,fill:tok('--muted')},sv,String(r));
  el('text',{x:Lm+pw,y:H-2,'text-anchor':'end','font-size':11.5,fill:tok('--muted')},sv,'r, a₀');
  const path=(f,arr)=>arr.map((v,i)=>(i?'L':'M')+sx(rs[i]).toFixed(1)+','+f(v).toFixed(1)).join(' ');
  el('path',{d:path(syP,Pv),fill:'none',stroke:tok('--warn'),'stroke-width':2.2},sv);el('path',{d:path(syR,Rv),fill:'none',stroke:tok('--accent'),'stroke-width':2.2},sv);
  const nodes=Q.nodes;
  nodes.forEach(r=>{el('circle',{cx:sx(r),cy:y0,r:4.5,fill:tok('--panel'),stroke:tok('--ink'),'stroke-width':1.6},sv)});
  const rm=Q.rm;el('line',{x1:sx(rm),y1:T,x2:sx(rm),y2:T+ph,stroke:tok('--muted'),'stroke-dasharray':'5 4'},sv);
  const ip=Q.ip,rmp=Q.rmp;el('circle',{cx:sx(rmp),cy:syP(Pv[ip]),r:4,fill:tok('--warn')},sv);
  const E=Q.E;
  $('infoTab').innerHTML='<table class="mtab"><tbody>'+
   '<tr><td>energy E<sub>n</sub> = −'+FR('Z²','2n²')+'</td><td>'+fmt(E,4)+' E<sub>h</sub> = '+fmt(Q.Eev,2)+' eV</td></tr>'+
   '<tr><td>degeneracy (without spin)</td><td>n² = '+n*n+'</td></tr>'+
   '<tr><td>radial nodes n − l − 1</td><td>'+(n-l-1)+(nodes.length?' (r = '+nodes.map(r=>fmt(r,2)).join('; ')+' a₀)':'')+'</td></tr>'+
   '<tr><td>angular nodes l</td><td>'+l+(l?' ('+orb().node+')':'')+'</td></tr>'+
   '<tr><td>mean radius ⟨r⟩</td><td>'+fmt(rm,2)+' a₀ = '+fmt(Q.rmA,2)+' Å</td></tr>'+
   '<tr><td>most probable r (maximum of r²R²)</td><td>'+fmt(rmp,2)+' a₀ = '+fmt(Q.rmpA,2)+' Å</td></tr></tbody></table>';
  $('st1').innerHTML='<b>'+n+orb().h+'</b>: total nodes n − 1 = '+(n-1)+' — radial '+(n-l-1)+' and angular '+l+'. '+
    (l===0?'Only s orbitals have a nonzero density at the nucleus (for 1s it is largest there). ':'For l &gt; 0 the function vanishes at the nucleus: R ∝ r<sup>l</sup>. ')+
    (n-l-1>0?'Radial nodes are spheres on which R(r) changes sign (circles on the plot). ':'')+
    (Z>1?'For an ion with charge Z = '+Z+' the orbital is '+Z+' times smaller, and the energy is '+Z*Z+' times deeper. ':'')}
// ---------- облако точек ----------
async function sample(){const seed=Math.floor(Math.random()*4294967296);let C;try{C=await liveC({n,oi,Z,seed})}catch(e){return}pts=C.pts;CL=C.L;
  $('cloudN').textContent=pts.length+' dots';drawCloud();drawHist()}
function drawCloud(){const cv=$('cloud'),[W,H,dp]=hiDPI(cv,400/460),ctx=cv.getContext('2d');ctx.fillStyle=tok('--soft');ctx.fillRect(0,0,W,H);
  const L=CL,S=Math.min(W,H)/2/L*0.92,r=Math.PI/180,cy=Math.cos(yaw*r),sy=Math.sin(yaw*r),cp=Math.cos(pitch*r),sp=Math.sin(pitch*r);
  const pr=([x,y,z])=>{const x1=x*cy-y*sy,y1=x*sy+y*cy;const y2=y1*cp-z*sp,z2=y1*sp+z*cp;return [W/2+S*x1,H/2-S*z2,y2]};
  ctx.strokeStyle=tok('--muted');ctx.lineWidth=dp;ctx.globalAlpha=0.6;ctx.font=(13*dp)+'px sans-serif';ctx.fillStyle=tok('--muted');
  [[[L,0,0],'x'],[[0,L,0],'y'],[[0,0,L],'z']].forEach(([v,t])=>{const a=pr([0,0,0]),b=pr(v);ctx.beginPath();ctx.moveTo(a[0],a[1]);ctx.lineTo(b[0],b[1]);ctx.stroke();ctx.fillText(t,b[0]+4*dp,b[1]-4*dp)});ctx.globalAlpha=1;
  const P=tok('--lp'),Nn=tok('--ln');const q=pts.map(p=>[...pr(p),p[3]]).sort((a,b)=>b[2]-a[2]);
  const rd=1.15*dp;q.forEach(p=>{ctx.fillStyle=p[3]>0?P:Nn;ctx.globalAlpha=0.7;ctx.beginPath();ctx.arc(p[0],p[1],rd,0,6.2832);ctx.fill()});ctx.globalAlpha=1;
  const l=orb().l;$('st2').innerHTML=(n-l-1>0?'Radial nodes show up as empty spherical gaps between layers of dots. ':'There are no radial nodes. ')+(l?'Angular nodes ('+orb().node+') separate regions of different color.':'The cloud of an s orbital is spherically symmetric.')}
// ---------- уровни и спектр ----------
// the dots by distance from the nucleus against r²R²(r) of section 1 (fills the column next to the cloud)
let lastR=null;
function drawHist(){const sv=$('cHist');if(!sv)return;sv.innerHTML='';const Q=lastR;if(!Q||!pts.length)return;const W=520,H=300,Lm=44,Rm=14,T=14,Bm=36,pw=W-Lm-Rm,ph=H-T-Bm,L=Q.L,NB=40,dr=L/NB,h=new Array(NB).fill(0);
  pts.forEach(p=>{const r=Math.hypot(p[0],p[1],p[2]);const k=Math.floor(r/dr);if(k>=0&&k<NB)h[k]++});const N=pts.length,den=h.map(c=>c/(N*dr));
  let I=0;for(let i=1;i<Q.rs.length;i++)I+=(Q.Pv[i]+Q.Pv[i-1])/2*(Q.rs[i]-Q.rs[i-1]);I=I||1;const pv=Q.Pv.map(v=>v/I);
  const top=Math.max(...den,...pv)*1.1||1,sx=r=>Lm+r/L*pw,sy=v=>T+ph-v/top*ph;
  el('line',{x1:Lm,y1:T+ph,x2:Lm+pw,y2:T+ph,stroke:tok('--line')},sv);el('line',{x1:Lm,y1:T,x2:Lm,y2:T+ph,stroke:tok('--line')},sv);
  den.forEach((v,k)=>el('rect',{x:sx(k*dr)+0.5,y:sy(v),width:Math.max(0,pw/NB-1),height:Math.max(0,T+ph-sy(v)),fill:tok('--lp'),opacity:0.35},sv));
  el('path',{d:pv.map((v,i)=>(i?'L':'M')+sx(Q.rs[i]).toFixed(1)+','+sy(v).toFixed(1)).join(' '),fill:'none',stroke:tok('--warn'),'stroke-width':2.2},sv);
  const step=L>40?10:L>20?5:L>8?2:1;for(let r=0;r<=L;r+=step)el('text',{x:sx(r),y:H-19,'text-anchor':'middle','font-size':11,fill:tok('--muted')},sv,String(r));
  el('text',{x:Lm+pw,y:H-2,'text-anchor':'end','font-size':11.5,fill:tok('--muted')},sv,'r, a₀')}
function wl2rgb(w){let r=0,g=0,b=0;if(w<440){r=-(w-440)/60;b=1}else if(w<490){g=(w-440)/50;b=1}else if(w<510){g=1;b=-(w-510)/20}else if(w<580){r=(w-510)/70;g=1}else if(w<645){r=1;g=-(w-645)/65}else r=1;return 'rgb('+[r,g,b].map(v=>Math.round(255*Math.max(0,Math.min(1,v)))).join(',')+')'}
async function levels(){let V;try{V=await liveL({Z,series})}catch(e){return}const sv=$('lev');sv.innerHTML='';const W=520,H=360,T=20,Bm=20,top=-0.3,bot=-14.2*Z*Z;const sy=e=>T+(H-T-Bm)*(top-e)/(top-bot);
  const x0=110,x1=380;
  for(let k=1;k<=7;k++){const e=V.lev[k-1];const g=el('g',{},sv);el('line',{x1:x0,y1:sy(e),x2:x1,y2:sy(e),stroke:tok(k===n?'--warn':'--ink'),'stroke-width':k===n?2.6:1.4},g);
    if(k<=4){el('text',{x:x0-8,y:sy(e)+4,'text-anchor':'end','font-size':12,fill:tok('--ink')},g,'n = '+k);el('text',{x:x1+8,y:sy(e)+4,'font-size':11.5,fill:tok('--muted')},g,fmt(e,2)+' eV  ·  g = '+k*k)}}
  el('line',{x1:x0,y1:sy(0),x2:x1,y2:sy(0),stroke:tok('--muted'),'stroke-dasharray':'5 4'},sv);el('text',{x:x0-8,y:sy(0)+4,'text-anchor':'end','font-size':12,fill:tok('--muted')},sv,'n = ∞');
  const rows=V.rows;
  rows.forEach(([n2,nu,lam],i)=>{const x=x0+40+i*42,e1=V.e1,e2=V.rowsE[i];if(n2>7)return;
    const col=lam>=380&&lam<=750?wl2rgb(lam):tok('--accent');el('line',{x1:x,y1:sy(e2),x2:x,y2:sy(e1)-7,stroke:col,'stroke-width':2.4},sv);el('path',{d:`M${x-5},${sy(e1)-9} L${x+5},${sy(e1)-9} L${x},${sy(e1)}Z`,fill:col},sv)});
  const reg=l=>l<380?'UV':l<=750?'visible':'IR';
  $('serTab').innerHTML='<table class="mtab"><thead><tr><th>transition</th><th>ν̃, cm⁻¹</th><th>λ, nm</th><th>region</th></tr></thead><tbody>'+rows.map(([n2,nu,lam])=>'<tr><td>'+n2+' → '+series+'</td><td>'+Math.round(nu)+'</td><td>'+fmt(lam,1)+'</td><td>'+reg(lam)+'</td></tr>').join('')+
    '<tr><td>∞ → '+series+' (series limit)</td><td>'+Math.round(V.edge[0])+'</td><td>'+fmt(V.edge[1],1)+'</td><td>'+reg(V.edge[1])+'</td></tr></tbody></table>';
  const w=$('specW');w.querySelectorAll('.ln,.lb').forEach(e=>e.remove());const vis=rows.filter(r=>r[2]>=380&&r[2]<=750);
  vis.forEach(([n2,nu,lam])=>{const p=(lam-380)/370*100;const d=document.createElement('i');d.className='ln';d.style.left='calc('+p.toFixed(2)+'% - 1px)';d.style.background=wl2rgb(lam);w.appendChild(d);
    const t=document.createElement('span');t.className='lb';t.style.left=p.toFixed(2)+'%';t.textContent=Math.round(lam);w.appendChild(t)});
  const nm={1:'Lyman',2:'Balmer',3:'Paschen'}[series];
  $('st3').innerHTML=''+nm+(Z>1?' for '+ZS[Z-1][1]:'')+': '+(vis.length?'in the visible range: '+vis.length+' line(s)'+(vis.length===1?'':vis.length<5?'':'')+' (the strip shows 380–750 nm). ':'all lines are outside the visible range (380–750 nm). ')+'The lines crowd toward the series limit ∞ → '+series+': levels with large n lie closer and closer together.'}
// ---------- тренажёр ----------
let qz=null;
function newQ(){let k,nn;do{nn=1+Math.floor(Math.random()*4);const ok=ORB.map((o,i)=>i).filter(i=>ORB[i].l<nn);k=ok[Math.floor(Math.random()*ok.length)]}while(qz&&qz.n===nn&&qz.k===k);
  qz={n:nn,k};$('qOrb').innerHTML=nn+ORB[k].h;for(let q=0;q<3;q++){$('q'+q).value='';$('q'+q).className=''}$('qRes').textContent='Enter your answers and press “Check”.'}
const num=s=>{s=String(s).trim().replace(',','.').replace('−','-');return s===''?NaN:+s};
$('qNew').onclick=newQ;
// «Проверьте себя» с выбором ответа (assets/js/try.*.js, initSelf): правильные ответы для вариантов
window.qcSelf=async()=>{const A=await QC.api('h.quiz',{n:qz.n,k:qz.k});return [String(qz.n-A.l-1),String(A.l),fmt(A.E,2)]};
$('qChk').onclick=async()=>{let A;try{A=await QC.api('h.quiz',{n:qz.n,k:qz.k})}catch(e){return}const l=A.l,E=A.E;const ok=[num($('q0').value)===qz.n-l-1,num($('q1').value)===l,Math.abs(num($('q2').value)-E)<0.06];
  ok.forEach((g,q)=>$('q'+q).className=$('q'+q).value.trim()===''?'':g?'ok':'bad');
  $('qRes').innerHTML=ok.every(Boolean)?'<b>Correct!</b>':'Not quite yet. There are n − l − 1 radial nodes and l angular ones, and the energy is E<sub>n</sub> = −'+FR('13.6 eV','n²')+'.'};
$('qShow').onclick=async()=>{let A;try{A=await QC.api('h.quiz',{n:qz.n,k:qz.k})}catch(e){return}const l=A.l,E=A.E;$('q0').value=qz.n-l-1;$('q1').value=l;$('q2').value=fmt(E,2);for(let q=0;q<3;q++)$('q'+q).className='ok';
  $('qRes').innerHTML=qz.n+ORB[qz.k].h+': l = '+l+', radial nodes '+qz.n+' − '+l+' − 1 = '+(qz.n-l-1)+', angular '+l+(l?' ('+ORB[qz.k].node+')':'')+'; E = −'+FR('13.6','n²')+' = −'+FR('13.6',qz.n*qz.n)+' = '+fmt(E,2)+' eV.'};
// ---------- управление ----------
function chips(box,items,cur,cb){box.innerHTML='';items.forEach(([v,h])=>{const b=document.createElement('button');b.type='button';b.className='chip';b.innerHTML=h;b.setAttribute('aria-pressed',v===cur);b.onclick=()=>cb(v);box.appendChild(b)})}
function ui(){chips($('nG'),[1,2,3,4].map(k=>[k,'n = '+k]),n,v=>{n=v;if(orb().l>=n)oi=0;upd()});
  chips($('oG'),ORB.map((o,i)=>[i,n+o.h]).filter(([i])=>ORB[i].l<n),oi,v=>{oi=v;upd()});
  chips($('zG'),ZS.map(([z,s])=>[z,s+' (Z = '+z+')']),Z,v=>{Z=v;upd();levels()});
  chips($('pG'),[['xz','xz'],['xy','xy'],['yz','yz']],plane,v=>{plane=v;ui();drawMap()});
  chips($('vG'),[['psi','ψ'],['dens','|ψ|²']],view,v=>{view=v;ui();drawMap()});
  chips($('sG'),[[1,'Lyman (n₁ = 1)'],[2,'Balmer (n₁ = 2)'],[3,'Paschen (n₁ = 3)']],series,v=>{series=v;ui();levels()})}
function upd(){ui();drawMap();radial();sample();levels()}
$('bNew').onclick=sample;
(()=>{const cv=$('cloud');let d=null;cv.addEventListener('pointerdown',e=>{d=[e.clientX,e.clientY,yaw,pitch];cv.setPointerCapture(e.pointerId)});
  cv.addEventListener('pointermove',e=>{if(!d)return;yaw=d[2]+(e.clientX-d[0])*0.5;pitch=Math.max(-89,Math.min(89,d[3]+(e.clientY-d[1])*0.5));drawCloud()});
  cv.addEventListener('pointerup',()=>d=null);cv.addEventListener('pointercancel',()=>d=null)})();
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>{drawMap();radial();drawCloud();levels()});
{let rz=0;addEventListener('resize',()=>{clearTimeout(rz);rz=setTimeout(()=>{paintMap();drawCloud()},120)})}
upd();newQ();
