/* Potential energy surface page (Atlas v2).  The LEPS surface, its grids,
   the transition state, the reaction path with zero-point energies, point
   analysis, gradient descent, Newton's method, trajectories, the isotope
   table and the Landau-Zener section come from quas_atlas.core.pes
   (pes.static, pes.point, pes.descend, pes.newton, pes.traj, pes.series,
   pes.kie, pes.lz).  This script colours the map, traces contour lines and
   draws. */

const tok=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const NS='http://www.w3.org/2000/svg';
function el(p,t,a){const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);p.appendChild(e);return e}
const fc=(x,d)=>x.toFixed(d).replace('-','−');
let ISO='H';
/* frequencies arrive signed (negative = imaginary) */
const wn=f=>(f<0?'i':'')+Math.round(Math.abs(f));
/* transition state, reaction path, zero-point energies, map grids: from pes.static */
let STATIC=null,TS=null,IRC=null,PATH=null,ZR=null,iTS=0,BAR=null,NUI=null;
let TK=300;
/* ===== состояние ===== */
let S={tab:'pt',p:[1.6,0.8],trail:[],trailKind:'',msg:'',Ecol:0.5,vib:true,phase:0,anim:null,traj:null,frame:0,series:null};
try{const s=JSON.parse(localStorage.getItem('pes-state')||'null');if(s){['tab','Ecol','vib','phase'].forEach(k=>{if(s[k]!=null)S[k]=s[k]});if(s.p)S.p=s.p}}catch(e){}
const save=()=>{try{localStorage.setItem('pes-state',JSON.stringify({tab:S.tab,Ecol:S.Ecol,vib:S.vib,phase:S.phase,p:S.p}))}catch(e){}};
/* ===== карта ===== */
const ML=50,MT=10,MW=410,MH2=410,R0=0.5,R1=3.0;
const sx=r=>ML+(r-R0)/(R1-R0)*MW,sy=r=>MT+MH2-(r-R0)/(R1-R0)*MH2,ix=X=>R0+(X-ML)/MW*(R1-R0),iy=Y=>R0+(MT+MH2-Y)/MH2*(R1-R0);
function hexrgb(c){c=c.trim();if(c.startsWith('#'))return [1,3,5].map(i=>parseInt(c.slice(i,i+2),16));return c.match(/\d+/g).slice(0,3).map(Number)}
let mapImg=null,contourPath='',mapTheme='';
function buildMap(){if(!STATIC)return;const th=['--h0','--h1','--h2','--h3'].map(t=>tok(t)).join();if(mapImg&&th===mapTheme)return;mapTheme=th;
  const N=180,cv=document.createElement('canvas');cv.width=N;cv.height=N;const cx=cv.getContext('2d'),img=cx.createImageData(N,N);const st=['--h0','--h1','--h2','--h3'].map(t=>hexrgb(tok(t)));
  for(let j=0;j<N;j++)for(let i=0;i<N;i++){let t=Math.max(0,Math.min(1,STATIC.map.E[j*N+i]/3))*3;const k=Math.min(2,Math.floor(t)),f=t-k;const c=st[k].map((x,q)=>Math.round(x+(st[k+1][q]-x)*f));img.data.set([c[0],c[1],c[2],255],4*(j*N+i))}
  cx.putImageData(img,0,0);mapImg=cv.toDataURL();
  /* изолинии: марширующие квадраты */const M=140,gr=[];for(let j=0;j<=M;j++){gr.push([]);for(let i=0;i<=M;i++)gr[j].push(STATIC.cont.E[j*(M+1)+i])}
  const levels=[0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0,1.5,2.0,2.5,3.0];let d='';
  const P=(i,j)=>[sx(R0+i/M*(R1-R0)),sy(R0+j/M*(R1-R0))];
  levels.forEach(lv=>{for(let j=0;j<M;j++)for(let i=0;i<M;i++){const v=[gr[j][i],gr[j][i+1],gr[j+1][i+1],gr[j+1][i]];const c=[[i,j],[i+1,j],[i+1,j+1],[i,j+1]];const pts=[];
    for(let e=0;e<4;e++){const a=v[e],b=v[(e+1)%4];if((a<lv)!==(b<lv)){const t=(lv-a)/(b-a);const A=c[e],B=c[(e+1)%4];pts.push(P(A[0]+(B[0]-A[0])*t,A[1]+(B[1]-A[1])*t))}}
    if(pts.length>=2)d+='M'+pts[0][0].toFixed(1)+','+pts[0][1].toFixed(1)+'L'+pts[1][0].toFixed(1)+','+pts[1][1].toFixed(1);if(pts.length===4)d+='M'+pts[2][0].toFixed(1)+','+pts[2][1].toFixed(1)+'L'+pts[3][0].toFixed(1)+','+pts[3][1].toFixed(1)}});
  contourPath=d}
function stext(par,x,y,txt,attrs){const t=el(par,'text',Object.assign({x,y},attrs));txt.split(/(_[A-Za-zа-я]+)/).forEach(part=>{if(!part)return;if(part[0]==='_'){const ts=el(t,'tspan',{'baseline-shift':'sub','font-size':'75%'});ts.textContent=part.slice(1)}else{const ts=el(t,'tspan',{});ts.textContent=part}});return t}
function drawMap(A){if(!STATIC)return;buildMap();const sv=document.getElementById('map');sv.innerHTML='';const ink=tok('--ink'),mut=tok('--muted');
  const cp=el(sv,'clipPath',{id:'cm'});el(cp,'rect',{x:ML,y:MT,width:MW,height:MH2});
  el(sv,'image',{href:mapImg,x:ML,y:MT,width:MW,height:MH2,preserveAspectRatio:'none'});
  const g=el(sv,'g',{'clip-path':'url(#cm)'});
  el(g,'path',{d:contourPath,fill:'none',stroke:'#000','stroke-opacity':.28,'stroke-width':.8});
  el(g,'line',{x1:sx(R0),y1:sy(R0),x2:sx(R1),y2:sy(R1),stroke:'#000','stroke-opacity':.25,'stroke-dasharray':'4 4'});
  IRC.forEach(arr=>{const pts=arr.map(q=>sx(q.r1).toFixed(1)+','+sy(q.r2).toFixed(1)).join(' ');el(g,'polyline',{points:pts,fill:'none',stroke:'#000','stroke-opacity':.5,'stroke-width':4.5});el(g,'polyline',{points:pts,fill:'none',stroke:tok('--path'),'stroke-width':2.4})});
  el(sv,'circle',{cx:sx(TS.r),cy:sy(TS.r),r:7,fill:'none',stroke:'#fff','stroke-width':2.5});el(sv,'circle',{cx:sx(TS.r),cy:sy(TS.r),r:7,fill:'none',stroke:'#000','stroke-width':1,'stroke-opacity':.6});
  const tr=S.tab==='dyn'&&S.traj?S.traj.slice(0,S.frame+1).map(f=>[f.r1,f.r2]):S.trail;
  if(tr&&tr.length>1){el(g,'polyline',{points:tr.map(q=>sx(q[0]).toFixed(1)+','+sy(q[1]).toFixed(1)).join(' '),fill:'none',stroke:'#fff','stroke-width':4,'stroke-opacity':.7});
    el(g,'polyline',{points:tr.map(q=>sx(q[0]).toFixed(1)+','+sy(q[1]).toFixed(1)).join(' '),fill:'none',stroke:tok('--traj'),'stroke-width':2.2});
    if(S.trailKind==='newton'&&S.tab==='pt')tr.forEach(q=>el(g,'circle',{cx:sx(q[0]),cy:sy(q[1]),r:3.2,fill:tok('--traj'),stroke:'#fff','stroke-width':1}))}
  if(S.tab==='pt'){const [r1,r2]=S.p,X=sx(r1),Y=sy(r2);const gg=A.g,gn=A.gn;
    const ev=A.ev;ev.forEach(e=>{const c=tok(e.l<0?'--neg':'--pos'),L=28;el(g,'line',{x1:X-e.v[0]*L,y1:Y+e.v[1]*L,x2:X+e.v[0]*L,y2:Y-e.v[1]*L,stroke:'#fff','stroke-width':5,'stroke-opacity':.75});el(g,'line',{x1:X-e.v[0]*L,y1:Y+e.v[1]*L,x2:X+e.v[0]*L,y2:Y-e.v[1]*L,stroke:c,'stroke-width':2.6})});
    if(gn>0.02){const L=Math.min(55,14+gn*9),ux=-gg[0]/gn,uy=-gg[1]/gn;const tx=X+ux*L,ty=Y-uy*L;el(g,'line',{x1:X,y1:Y,x2:tx,y2:ty,stroke:'#fff','stroke-width':4.5,'stroke-opacity':.8});el(g,'line',{x1:X,y1:Y,x2:tx,y2:ty,stroke:ink,'stroke-width':2});
      el(g,'polygon',{points:[[tx+ux*8,ty-uy*8],[tx-uy*4.5,ty-ux*4.5],[tx+uy*4.5,ty+ux*4.5]].map(q=>q.join(',')).join(' '),fill:ink})}
    el(sv,'circle',{cx:X,cy:Y,r:6,fill:tok('--accent'),stroke:'#fff','stroke-width':2})}
  else if(S.traj){const f=S.traj[Math.min(S.frame,S.traj.length-1)];el(sv,'circle',{cx:sx(f.r1),cy:sy(f.r2),r:6,fill:tok('--traj'),stroke:'#fff','stroke-width':2,'clip-path':'url(#cm)'})}/* the atoms fly apart beyond the map — the point leaves it instead of hanging over the scale */
  el(sv,'rect',{x:ML,y:MT,width:MW,height:MH2,fill:'none',stroke:tok('--line')});
  [0.5,1,1.5,2,2.5,3].forEach(v=>{el(sv,'text',{x:sx(v),y:MT+MH2+16,'text-anchor':'middle','font-size':11.5,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=fc(v,1);el(sv,'text',{x:ML-6,y:sy(v)+4,'text-anchor':'end','font-size':11.5,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=fc(v,1)});
  stext(sv,ML+MW,MT+MH2+34,'r₁ = r(H_A–H_B), Å',{'text-anchor':'end','font-size':13.5,'font-style':'italic','font-family':'PT Serif, serif',fill:ink});
  stext(sv,14,MT+MH2/2,'r₂ = r(H_B–H_C), Å',{'font-size':13.5,'font-style':'italic','font-family':'PT Serif, serif',fill:ink,transform:`rotate(-90 14 ${MT+MH2/2})`,'text-anchor':'middle'});
  const lab=(x,y,t,a)=>stext(sv,x,y,t,{'font-size':12.5,'font-weight':600,fill:'#1b2230','font-family':'Golos Text, sans-serif','text-anchor':a||'start',stroke:'#fff','stroke-width':3,'paint-order':'stroke'});
  lab(sx(2.95),sy(0.86),'H_A + H_B–H_C','end');lab(sx(0.82),sy(2.85),'H_A–H_B + H_C');lab(sx(TS.r)+10,sy(TS.r)-10,'TS');lab(sx(2.95),sy(2.9),'three separate atoms (+4.7 eV)','end')}
/* ===== атомы ===== */
function drawAtoms(r1,r2){const sv=document.getElementById('atoms');sv.innerHTML='';const ink=tok('--ink'),mut=tok('--muted');const sc=70,xc=260;const xA=-r1,xB=0,xC=r2;const cm=(xA+xB+xC)/3;const X=x=>xc+(x-cm)*sc;
  el(sv,'line',{x1:10,x2:510,y1:34,y2:34,stroke:tok('--line')});
  [[xA,'H_A'],[xB,'H_B'],[xC,'H_C']].forEach(([x,n])=>{const cx=Math.max(14,Math.min(506,X(x)));el(sv,'circle',{cx,cy:34,r:13,fill:'#e8eaee',stroke:'#7a818c','stroke-width':1.4});stext(sv,cx,38,n,{'text-anchor':'middle','font-size':11.5,'font-weight':600,fill:'#1b2230','font-family':'Golos Text, sans-serif'})});
  const dl=(a,b,t)=>{const x1=Math.max(14,Math.min(506,X(a))),x2=Math.max(14,Math.min(506,X(b)));el(sv,'text',{x:(x1+x2)/2,y:64,'text-anchor':'middle','font-size':12,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=t};
  dl(xA,xB,'r₁ = '+fc(r1,2));dl(xB,xC,'r₂ = '+fc(r2,2))}
/* ===== анализ точки ===== */
/* text for the kind of point determined by the model (pes.point) */
function kindOf(A){const K={valley:['Valley floor: an H₂ molecule and a distant H atom, a minimum “at infinity”','min'],min:['Minimum','min'],ts:['First-order saddle point: transition state','ts'],saddle2:['Second-order saddle point: no chemical meaning',''],slope:['Not a stationary point: a slope, ∇E ≠ 0','']}[A.kind];return Object.assign({},A,{kind:K[0],cls:K[1]})}
function panePt(pane,A){const a=kindOf(A);
  pane.innerHTML='<div class="verdict '+a.cls+'">'+a.kind+'</div><div class="kvt"><span>E</span><b>'+fc(a.e,3)+' eV</b><span>∇E = (<span class=fr><span>∂E</span><span>∂r₁</span></span>, <span class=fr><span>∂E</span><span>∂r₂</span></span>)</span><b>('+fc(a.g[0],2)+'; '+fc(a.g[1],2)+') eV/Å, |∇E| = '+fc(a.gn,2)+'</b>'+
   '<span>curvatures (Hessian eigenvalues)</span><b>'+a.ev.map(x=>'<span style="color:var('+(x.l<0?'--neg':'--pos')+')">'+fc(x.l,1)+'</span>').join('; ')+' eV/Å²</b><span>frequencies (mass-weighted)</span><b>'+a.wn.map(wn).join('; ')+' cm⁻¹</b></div>'+
   '<p class="hint" style="font-size:13.5px">On the map: the black arrow is the descent direction (−∇E); the green and red segments are the principal curvature directions (green: a “valley”, E increases both ways; red: a “pass”, E decreases both ways). '+(a.gn>=0.03&&a.nneg?'There is a negative curvature here, but ∇E ≠ 0, so this is not yet a transition state: a saddle requires both conditions at once.':'')+'</p>'+
   '<div class="row"><button class="btn primary" id="bDesc" type="button">Gradient descent</button><button class="btn" id="bNewt" type="button">Newton method</button><button class="btn" id="bTS" type="button">To transition state</button><button class="btn" id="bClr" type="button">Clear trace</button></div><div class="status" id="ptMsg">'+(S.msg||'Click on the map or press a button. The first two buttons are the same algorithms that programs use to optimize geometry and locate transition states.')+'</div>';
  pane.querySelector('#bDesc').onclick=descend;pane.querySelector('#bNewt').onclick=newton;pane.querySelector('#bTS').onclick=async()=>{let T;try{T=await QC.api('pes.point',{r1:TS.r,r2:TS.r,iso:ISO})}catch(e){return}S.p=[TS.r,TS.r];S.trail=[];S.msg='Transition state: r₁ = r₂ = '+fc(TS.r,3)+' Å, E‡ = '+fc(TS.E,3)+' eV above the reactants. One imaginary frequency '+wn(T.wn[1])+' cm⁻¹: a vibration along the reaction path, in which one H atom passes from one partner to the other. The second frequency is the symmetric vibration, in which the end atoms move toward and away from each other.';render()};
  pane.querySelector('#bClr').onclick=()=>{S.trail=[];S.msg='';render()}}
async function descend(){let D;try{D=await QC.api('pes.descend',{r1:S.p[0],r2:S.p[1],iso:ISO})}catch(e){return}const r=D.r,tr=D.trail;
  S.trail=tr;S.trailKind='desc';S.p=D.p;
  const a=kindOf(D.a);
  if(a.nneg>0&&a.gn<0.03){S.msg='<b>Gradient descent stopped at the transition state!</b> You started on the line r₁ = r₂: there the gradient points along this line, and the descent follows it straight into the saddle point, where ∇E = 0. The algorithm is “satisfied”: the gradient is zero. A saddle can be told from a minimum only by the Hessian: here there is one negative curvature and one imaginary frequency. That is why frequencies must always be computed after any geometry optimization.';render();return}
  const side=r[0]<r[1]?'H<sub>A</sub>–H<sub>B</sub> + H<sub>C</sub> (products)':'H<sub>A</sub> + H<sub>B</sub>–H<sub>C</sub> (reactants)';
  S.msg='<b>Gradient descent</b> (each step always against ∇E) rolled down into the valley '+side+'. '+(r[0]>=R1||r[1]>=R1?'Within the map the valley has no floor: the free atom can be moved arbitrarily far away, and the energy tends to that of H + H₂. ':'')+'The H–H bond length in the valley is '+fc(Math.min(...S.p),3)+' Å, the equilibrium one. This is how geometry optimizers work: they always reach the <b>nearest</b> minimum, not the deepest one. Computational programs (for example ASE) do the same, only instead of simple descent they use faster methods such as BFGS.';render()}
async function newton(){let N;try{N=await QC.api('pes.newton',{r1:S.p[0],r2:S.p[1],iso:ISO})}catch(e){return}const r=N.r,tr=N.trail;
  S.trail=tr;S.trailKind='newton';
  if(N.ok){S.p=r;const a=kindOf(N.a);S.msg='<b>Newton method</b> (step −H⁻¹∇E, where H is the Hessian) reached a stationary point in '+(tr.length-1)+' steps: <b>'+a.kind.toLowerCase()+'</b>. Newton’s method does not care whether it is a minimum or a saddle: it looks for any point where ∇E = 0. That is why a transition-state search is started close to it, and frequencies are always computed afterwards: exactly one imaginary frequency confirms a TS.'}
  else{S.msg='<b>Newton method</b> found no stationary point on the map from this point: the steps go '+(r[0]>R1||r[1]>R1?'off to infinity along the valley':'sideways')+'. Start closer to the transition state (white circle): there it converges in a few steps.'}
  render()}
/* ===== dynamics: trajectories from pes.traj / pes.series ===== */
function paneDyn(pane){const Ezpe=STATIC.EZPE[ISO];
  pane.innerHTML='<div class="crow"><span class="l" style="min-width:150px">Collision energy</span><input type="range" id="ec" min="0.05" max="1.5" step="0.01" style="width:200px"><span class="val" id="ecv"></span></div>'+
   '<label class="hint" style="display:flex;gap:6px;align-items:center"><input type="checkbox" id="vb"'+(S.vib?' checked':'')+'> the '+(ISO==='H'?'H₂':'D₂')+' molecule vibrates with its zero-point energy ('+fc(Ezpe,2)+' eV)</label>'+
   '<div class="crow"><span class="l" style="min-width:150px">Vibration phase</span><input type="range" id="ph" min="0" max="345" step="15" style="width:200px"'+(S.vib?'':' disabled')+'><span class="val" id="phv"></span></div>'+
   '<div class="row"><button class="btn primary" id="go" type="button">Run</button><button class="btn" id="ser" type="button">Series: 24 phases</button></div><div class="status" id="dynMsg">'+(S.msg2||'Atom H<sub>A</sub> approaches the molecule H<sub>B</sub>H<sub>C</sub>. The nuclear motion is classical (Newton’s equations) on a surface computed for fixed nuclei. The barrier is '+fc(TS.E,2)+' eV.')+'</div>';
  const ec=pane.querySelector('#ec'),ph=pane.querySelector('#ph');ec.value=S.Ecol;ph.value=S.phase;pane.querySelector('#ecv').textContent=fc(S.Ecol,2)+' eV';pane.querySelector('#phv').textContent=S.phase+'°';
  ec.oninput=e=>{S.Ecol=+e.target.value;pane.querySelector('#ecv').textContent=fc(S.Ecol,2)+' eV';save()};ph.oninput=e=>{S.phase=+e.target.value;pane.querySelector('#phv').textContent=S.phase+'°';save()};
  pane.querySelector('#vb').onchange=e=>{S.vib=e.target.checked;ph.disabled=!S.vib;pane.querySelector('#ser').disabled=!S.vib;save()};if(!S.vib)pane.querySelector('#ser').disabled=true;
  pane.querySelector('#go').onclick=async()=>{let T;try{T=await QC.api('pes.traj',{Ecol:S.Ecol,vib:S.vib,phase:S.phase,iso:ISO})}catch(e){return}S.traj=T.frames;S.frame=0;
    const tot=S.Ecol+(S.vib?T.Ezpe:0);S.msg2=(T.react?'<b>Reaction!</b> H<sub>A</sub> captured atom H<sub>B</sub>, and H<sub>C</sub> flew away. ':'<b>Reflection:</b> H<sub>A</sub> bounced back, and the molecule stayed the same. ')+'Collision energy '+fc(S.Ecol,2)+' eV'+(S.vib?' + vibrational '+fc(T.Ezpe,2)+' eV':'')+' with a barrier of '+fc(TS.E,2)+' eV. '+(T.react&&S.Ecol<TS.E?'The translational energy was not enough: the vibration of the molecule helped. ':'')+(!T.react&&tot>TS.E?'The total energy was enough, but the trajectory missed the “throat” of the pass: what matters is not only the energy but also how it is distributed. ':'')+'Look at the trace: the trajectory runs along the valley floor, turns at the pass and exits into the other valley.';animate()};
  pane.querySelector('#ser').onclick=async()=>{let SR;try{SR=await QC.api('pes.series',{Ecol:S.Ecol,iso:ISO})}catch(e){return}let n=0;const res=SR.react;res.forEach(x=>{if(x)n++});
    S.msg2='<b>A series of 24 phases</b> of the H₂ vibration at collision energy '+fc(S.Ecol,2)+' eV: reaction in '+n+' of 24 cases (probability ≈ '+Math.round(100*n/24)+' %). Try different energies: below the threshold there is no reaction at all, above it the probability grows quickly, and at high energies it drops again: the atom flies over the pass, bounces off the “wall” and comes back. The threshold here is below the barrier: part of the H₂ vibrational energy also goes into crossing the barrier. Such a dependence is the classical “excitation function”; quantum effects (tunneling, quantized vibrations) shift it.';S.traj=null;render()}}
function animate(){if(S.anim)cancelAnimationFrame(S.anim);const fr=S.traj;if(matchMedia('(prefers-reduced-motion: reduce)').matches){S.frame=fr.length-1;render();return}
  const t0=performance.now();const step=n=>{S.frame=Math.max(0,Math.min(fr.length-1,Math.floor((n-t0)/1000*60)));drawMap();const f=fr[S.frame];drawAtoms(f.r1,f.r2);if(S.frame<fr.length-1)S.anim=requestAnimationFrame(step);else render()};S.anim=requestAnimationFrame(step)}
/* ===== профиль ===== */
function drawProf(){if(!STATIC)return;const sv=document.getElementById('prof');sv.innerHTML='';const mut=tok('--muted'),ink=tok('--ink');const pts=[...IRC[1].slice().reverse(),...IRC[0].slice(1)];
  const smin=Math.min(...pts.map(p=>p.s)),smax=Math.max(...pts.map(p=>p.s));const L=56,T=16,W=820,H=174;const sx=s=>L+(s-smin)/(smax-smin)*W,sy=e=>T+H-e/0.5*H;
  [0,0.1,0.2,0.3,0.4,0.5].forEach(e=>{el(sv,'line',{x1:L,x2:L+W,y1:sy(e),y2:sy(e),stroke:tok('--line'),'stroke-width':.7});el(sv,'text',{x:L-6,y:sy(e)+4,'text-anchor':'end','font-size':11.5,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=fc(e,1)});
  el(sv,'polyline',{points:pts.map(p=>sx(p.s).toFixed(1)+','+sy(p.E).toFixed(1)).join(' '),fill:'none',stroke:tok('--accent'),'stroke-width':2.6});
  [['H','--rho-l'],['D','--virt']].forEach(([k,c])=>{el(sv,'polyline',{points:PATH.map(p=>sx(p.s).toFixed(1)+','+sy(p.E+p['z'+k]-ZR[k]).toFixed(1)).join(' '),fill:'none',stroke:tok(c),'stroke-width':k===ISO?2.4:1.6,'stroke-dasharray':'7 4',opacity:k===ISO?1:.7})});
  el(sv,'circle',{cx:sx(0),cy:sy(TS.E),r:5,fill:tok('--accent')});
  el(sv,'text',{x:sx(0),y:sy(TS.E)-10,'text-anchor':'middle','font-size':12.5,fill:ink,'font-family':'Golos Text, sans-serif'}).textContent='transition state, E‡ = '+fc(TS.E,2)+' eV';
  stext(sv,L+6,sy(0)-8,'H_A + H_B–H_C',{'font-size':12.5,fill:ink,'font-family':'Golos Text, sans-serif'});
  stext(sv,L+W-6,sy(0)-8,'H_A–H_B + H_C',{'text-anchor':'end','font-size':12.5,fill:ink,'font-family':'Golos Text, sans-serif'});
  for(let s=Math.ceil(smin);s<=smax;s++)el(sv,'text',{x:sx(s),y:T+H+16,'text-anchor':'middle','font-size':11.5,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=fc(s,0);
  el(sv,'text',{x:L+W,y:T+H+34,'text-anchor':'end','font-size':13,'font-style':'italic','font-family':'PT Serif, serif',fill:mut}).textContent='s, Å';
  el(sv,'text',{x:L+6,y:T+12,'font-size':12,fill:mut,'font-family':'Golos Text, sans-serif'}).textContent='E, eV';drawZPE()}
const getKie=QC.live('pes.kie');
async function drawZPE(){if(!STATIC)return;let K;try{K=await getKie({T:TK})}catch(e){return}const k={H:K.kH,D:K.kD};
  const row=i=>'<tr><td>'+(i==='H'?'H + H₂':'D + D₂')+'</td><td>'+fc(TS.E,3)+'</td><td>'+fc(PATH[iTS]['z'+i],3)+' − '+fc(ZR[i],3)+'</td><td><b>'+fc(BAR[i],3)+'</b></td><td>'+NUI[i]+'i</td><td>'+fc(k[i],2)+'</td></tr>';
  const ratio=K.ratio;
  document.getElementById('zpeTab').innerHTML='<table><thead><tr><th>system</th><th>PES barrier, eV</th><th>ZPE at TS − ZPE of reactants, eV</th><th>effective barrier, eV</th><th>imaginary frequency, cm⁻¹</th><th>Wigner κ</th></tr></thead><tbody>'+row('H')+row('D')+'</tbody></table>';
  document.getElementById('zpeTxt').innerHTML='<b>Zero-point vibrations (ZPE).</b> Even at the lowest point the molecule vibrates: for the reactants this is the H–H vibration ('+fc(ZR.H,2)+' eV for H₂, '+fc(ZR.D,2)+' eV for D₂), while at the transition state it is the vibration across the path (symmetric stretch H···H···H). It is “softer”, so the effective barrier is lower than the PES barrier (dashed line on the profile). For D all frequencies are √2 times smaller, and so are the zero-point energies, so the gain is smaller: the effective barrier for D is higher by '+fc(BAR.D-BAR.H,3)+' eV. At '+TK+' K this contribution alone gives a factor exp(<span class=fr><span>ΔE</span><span>kT</span></span>) ≈ '+fc(ratio,1)+' in favor of H — this is the main cause of the <b>kinetic isotope effect</b>. '+
   '<b>Tunneling</b> (Wigner): κ = 1 + <span class=fr><span>1</span><span>24</span></span>(<span class=fr><span>hν‡</span><span>kT</span></span>)², where ν‡ is the magnitude of the imaginary frequency. The light H tunnels more easily (κ is larger). When κ is noticeably greater than 1, the Wigner estimate is already crude — it is good only as a first correction. The model is one-dimensional: rotational and translational partition functions are not included here.'}
/* ===== избегаемое пересечение ===== */
let LZ={lv:-1.7,v:1000};try{const s=JSON.parse(localStorage.getItem('pes-lz')||'null');if(s)LZ=s}catch(e){}
const getLZ=QC.live('pes.lz');
async function drawLZ(){let Z;try{Z=await getLZ({lv:LZ.lv,v:LZ.v})}catch(e){return}const V=Z.V,v=LZ.v,RC=Z.RC;document.getElementById('Vv').textContent=fc(V,3)+' eV';document.getElementById('velv').textContent=v+' m/s';
  const plot=(id,Ra,Rb,Ea,Eb,zoom)=>{const sv=document.getElementById(id);sv.innerHTML='';const mut=tok('--muted'),ink=tok('--ink');const L=52,T=10,W=470,H=220;const sx=R=>L+(R-Ra)/(Rb-Ra)*W,sy=e=>T+H-(e-Ea)/(Eb-Ea)*H;
    const cp=el(sv,'clipPath',{id:'c'+id});el(cp,'rect',{x:L,y:T,width:W,height:H});const g=el(sv,'g',{'clip-path':'url(#c'+id+')'});
    const n=5;for(let i=0;i<=n;i++){const e=Ea+(Eb-Ea)*i/n;el(sv,'line',{x1:L,x2:L+W,y1:sy(e),y2:sy(e),stroke:tok('--line'),'stroke-width':.7});el(sv,'text',{x:L-6,y:sy(e)+4,'text-anchor':'end','font-size':11.5,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=fc(e,zoom?2:0)}
    const Rs=Array.from({length:400},(_,i)=>Ra+(Rb-Ra)*i/399),CV=zoom?Z.zoom:Z.full;const line=(a,c,w,d)=>el(g,'polyline',{points:Rs.map((R,i)=>sx(R).toFixed(1)+','+sy(a[i]).toFixed(1)).join(' '),fill:'none',stroke:c,'stroke-width':w,'stroke-dasharray':d||'none'});
    line(CV.cov,mut,1.6,'6 4');line(CV.ion,mut,1.6,'6 4');line(CV.lo,tok('--accent'),2.5);line(CV.hi,tok('--accent'),2.5);
    const nt=zoom?[Math.ceil(Ra),Math.floor(Rb)]:[2,4,6,8,10,12,14];for(let R=nt[0];R<=nt[nt.length-1];R+=zoom?0.5:2)el(sv,'text',{x:sx(R),y:T+H+16,'text-anchor':'middle','font-size':11.5,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=fc(R,zoom?1:0);
    el(sv,'text',{x:L+W,y:T+H+34,'text-anchor':'end','font-size':13,'font-style':'italic','font-family':'PT Serif, serif',fill:mut}).textContent='R(Na–Cl), Å';
    if(!zoom){el(sv,'rect',{x:sx(RC-1.2),y:sy(0.35),width:sx(RC+1.2)-sx(RC-1.2),height:sy(-0.35)-sy(0.35),fill:'none',stroke:ink,'stroke-dasharray':'3 3'});
      const t=(x,y,s)=>el(sv,'text',{x,y,'font-size':12,fill:ink,'font-family':'Golos Text, sans-serif'}).textContent=s;t(sx(10.3),sy(0.25)-4,'Na + Cl');t(sx(3.0),sy(-3.2),'Na⁺ + Cl⁻')}
    else{el(sv,'line',{x1:sx(RC),x2:sx(RC),y1:sy(-V),y2:sy(V),stroke:tok('--rho-l'),'stroke-width':2});el(sv,'text',{x:sx(RC)+6,y:sy(0)+4,'font-size':12.5,fill:tok('--rho-l'),'font-family':'Golos Text, sans-serif'}).textContent='gap 2V'}};
  plot('lz',1.5,14,-5,2,false);plot('lzz',RC-1.2,RC+1.2,-0.35,0.35,true);
  const dF=Z.dF,P=Z.P;
  document.getElementById('lzText').innerHTML='<b>Landau–Zener formula:</b> the probability to “jump through” the crossing while staying on the diabatic curve is P = exp(−<span class=fr><span>2πV²</span><span>ħv|ΔF|</span></span>), where |ΔF| = '+fc(dF,3)+' eV/Å is the difference of the curve slopes. Now <b>P = '+(P<1e-3?P.toExponential(1).replace('e-','·10⁻'):fc(P,3))+'</b>: '+
   (P<0.05?'the nuclei move slowly compared with the rearrangement of the electrons, and the system stays on the adiabatic curve — <b>the Born–Oppenheimer approximation holds</b>.':P>0.95?'the electrons “do not have time” to rearrange: the system hops between adiabatic curves, staying on the diabatic one. <b>One surface is not enough</b> — the Born–Oppenheimer approximation breaks down.':'the system hops to the other adiabatic curve with appreciable probability — <b>an intermediate case</b>; a calculation with several surfaces is needed.')+
   ' In one collision the crossing is passed twice (on approach and on separation), so the probability of forming the ion pair Na⁺Cl⁻ (the “harpoon”) is 2P(1 − P) = '+fc(Z.P2,3)+'. Decrease V and increase v — nonadiabatic transitions become unavoidable: this is how photochemistry and radiationless transitions work. The model parameters are simplified: V and the slopes were chosen for clarity.'}
/* ===== сборка ===== */
function renderPane(A){const pane=document.getElementById('pane');document.querySelectorAll('.tab').forEach(b=>b.setAttribute('aria-selected',b.dataset.tab===S.tab));if(S.tab==='pt')panePt(pane,A);else paneDyn(pane)}
const getPt=QC.live('pes.point');
async function render(){if(!STATIC)return;let A=null;if(S.tab==='pt'){try{A=await getPt({r1:S.p[0],r2:S.p[1],iso:ISO})}catch(e){return}}drawMap(A);renderPane(A);if(S.tab==='pt')drawAtoms(...S.p);else if(S.traj){const f=S.traj[Math.min(S.frame,S.traj.length-1)];drawAtoms(f.r1,f.r2)}else drawAtoms(3.0,0.742);save()}
document.querySelectorAll('.tab').forEach(b=>b.onclick=()=>{S.tab=b.dataset.tab;if(S.anim)cancelAnimationFrame(S.anim);render()});
(()=>{const sv=document.getElementById('map');let down=false;const set=e=>{if(S.tab!=='pt'){S.tab='pt'}const r=sv.getBoundingClientRect();const X=(e.clientX-r.left)/r.width*470,Y=(e.clientY-r.top)/r.height*470;const r1=ix(X),r2=iy(Y);if(r1<R0||r2<R0||r1>R1||r2>R1)return;S.p=[r1,r2];S.msg='';if(S.trailKind)S.trail=[],S.trailKind='';render()};
  sv.addEventListener('pointerdown',e=>{down=true;sv.setPointerCapture(e.pointerId);set(e)});sv.addEventListener('pointermove',e=>{if(down)set(e)});sv.addEventListener('pointerup',()=>down=false)})();
const Vin=document.getElementById('V'),vin=document.getElementById('vel');Vin.value=LZ.lv;vin.value=LZ.v;
Vin.oninput=e=>{LZ.lv=+e.target.value;drawLZ();try{localStorage.setItem('pes-lz',JSON.stringify(LZ))}catch(x){}};vin.oninput=e=>{LZ.v=+e.target.value;drawLZ();try{localStorage.setItem('pes-lz',JSON.stringify(LZ))}catch(x){}};
QC.api('pes.static',{}).then(d=>{STATIC=d;TS=d.TS;IRC=d.IRC;PATH=d.PATH;ZR=d.ZR;iTS=d.iTS;BAR=d.BAR;NUI=d.NUI;render();drawProf();drawZPE()}).catch(()=>{});drawLZ();
const redraw=()=>{mapImg=null;render();drawProf();drawLZ()};
function renderIso(){const box=document.getElementById('iso');box.innerHTML='';[['H','H + H₂'],['D','D + D₂']].forEach(([k,l])=>{const b=document.createElement('button');b.type='button';b.className='chip';b.textContent=l;b.setAttribute('aria-pressed',k===ISO);b.onclick=()=>{ISO=k;S.traj=null;S.msg2='';renderIso();render();drawProf()};box.appendChild(b)})}
renderIso();const Tin=document.getElementById('Tk');Tin.value=TK;document.getElementById('Tkv').textContent=TK+' K';Tin.oninput=e=>{TK=+e.target.value;document.getElementById('Tkv').textContent=TK+' K';drawZPE()};drawZPE();
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',redraw);
new MutationObserver(redraw).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
