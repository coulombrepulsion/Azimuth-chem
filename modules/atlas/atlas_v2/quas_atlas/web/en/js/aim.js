/* Atoms in molecules page (Atlas v2).  RHF, critical points, gradient paths,
   Bader charges, the map, the volume grids, the ESP surface, molecular orbitals
   and bond profiles come from quas_atlas.core.aim / core.qtaim / core.gto
   (endpoints aim.meta, aim.stage, aim.mo, aim.prof; large arrays arrive as
   base64 float32).  This script draws: contour map, WebGL scene and the
   isosurfaces of the grids (marching tetrahedra below, the v1.0 code). */
// isosurface F = level: marching tetrahedra (display only)
const ISO=(()=>{
const TET=[[0,5,1,6],[0,1,2,6],[0,2,3,6],[0,3,7,6],[0,7,4,6],[0,4,5,6]];
const CORN=[[0,0,0],[1,0,0],[1,1,0],[0,1,0],[0,0,1],[1,0,1],[1,1,1],[0,1,1]];
function iso(F,G,level,sign){const [nx,ny,nz]=G.n,s=sign||1;const pos=[],nrm=[],idx=[],map=new Map();
  const val=(i,j,k)=>F[(Math.min(nz-1,Math.max(0,k))*ny+Math.min(ny-1,Math.max(0,j)))*nx+Math.min(nx-1,Math.max(0,i))];
  const grad=(i,j,k)=>[-(val(i+1,j,k)-val(i-1,j,k))*s,-(val(i,j+1,k)-val(i,j-1,k))*s,-(val(i,j,k+1)-val(i,j,k-1))*s];
  const at=(i,j,k)=>s*(F[(k*ny+j)*nx+i]-level);
  const vert=(a,b)=>{const key=a<b?a*16777259+b:b*16777259+a;let v=map.get(key);if(v!==undefined)return v;
    const ia=a%nx,ja=Math.floor(a/nx)%ny,ka=Math.floor(a/(nx*ny)),ib=b%nx,jb=Math.floor(b/nx)%ny,kb=Math.floor(b/(nx*ny));
    const fa=at(ia,ja,ka),fb=at(ib,jb,kb),t=fa/(fa-fb);v=pos.length/3;
    pos.push(G.o[0]+(ia+t*(ib-ia))*G.h,G.o[1]+(ja+t*(jb-ja))*G.h,G.o[2]+(ka+t*(kb-ka))*G.h);
    const ga=grad(ia,ja,ka),gb=grad(ib,jb,kb);nrm.push(ga[0]+t*(gb[0]-ga[0]),ga[1]+t*(gb[1]-ga[1]),ga[2]+t*(gb[2]-ga[2]));map.set(key,v);return v};
  const gi=(i,j,k)=>(k*ny+j)*nx+i;const c=new Array(8),f=new Array(8);
  for(let k=0;k<nz-1;k++)for(let j=0;j<ny-1;j++)for(let i=0;i<nx-1;i++){let anyP=false,anyN=false;
    for(let q=0;q<8;q++){const d=CORN[q];c[q]=gi(i+d[0],j+d[1],k+d[2]);f[q]=at(i+d[0],j+d[1],k+d[2]);if(f[q]>0)anyP=true;else anyN=true}
    if(!anyP||!anyN)continue;
    for(const t of TET){const v=t.map(q=>c[q]),fv=t.map(q=>f[q]);const ins=[0,1,2,3].filter(q=>fv[q]>0);
      if(ins.length===0||ins.length===4)continue;const out=[0,1,2,3].filter(q=>fv[q]<=0);
      if(ins.length===1){const a=ins[0];idx.push(vert(v[a],v[out[0]]),vert(v[a],v[out[1]]),vert(v[a],v[out[2]]))}
      else if(ins.length===3){const a=out[0];idx.push(vert(v[a],v[ins[0]]),vert(v[a],v[ins[2]]),vert(v[a],v[ins[1]]))}
      else{const [a,b]=ins,[p,q]=out;const v1=vert(v[a],v[p]),v2=vert(v[a],v[q]),v3=vert(v[b],v[q]),v4=vert(v[b],v[p]);idx.push(v1,v2,v3,v1,v3,v4)}}}
  // нормали -- по градиенту поля (наружу, туда, где поле меньше уровня)
  const P=new Float32Array(pos),I=new Uint32Array(idx),N=new Float32Array(nrm);
  for(let o=0;o<N.length;o+=3){const l=Math.hypot(N[o],N[o+1],N[o+2])||1;N[o]/=l;N[o+1]/=l;N[o+2]/=l}
  return {pos:P,nrm:N,idx:I}}
return {iso}})();
const BONDS=[{"m":"H2","bond":"H–H","rho":0.2437,"lap":-1.0538,"H":-0.2634,"G":0,"eps":0},{"m":"LiH","bond":"H–Li","rho":0.0366,"lap":0.1577,"H":0.0008,"G":0.0387,"eps":0},{"m":"LiF","bond":"F–Li","rho":0.0737,"lap":0.7858,"H":0.0238,"G":0.1727,"eps":0},{"m":"HF","bond":"H–F","rho":0.3524,"lap":-2.7159,"H":-0.7514,"G":0.0725,"eps":0},{"m":"N2","bond":"N–N","rho":0.68,"lap":-2.4669,"H":-1.1834,"G":0.5667,"eps":0},{"m":"CO","bond":"O–C","rho":0.4845,"lap":1.5274,"H":-0.7935,"G":1.1754,"eps":0},{"m":"F2","bond":"F–F","rho":0.2874,"lap":0.2486,"H":-0.1974,"G":0.2596,"eps":0},{"m":"H2O","bond":"H–O","rho":0.3568,"lap":-1.9719,"H":-0.5563,"G":0.0634,"eps":0.024},{"m":"NH3","bond":"H–N","rho":0.3348,"lap":-1.6749,"H":-0.469,"G":0.0502,"eps":0.04},{"m":"CH4","bond":"H–C","rho":0.2753,"lap":-0.9658,"H":-0.2798,"G":0.0384,"eps":0},{"m":"C2H4","bond":"C–C","rho":0.3482,"lap":-1.0882,"H":-0.4007,"G":0.1287,"eps":0.444},{"m":"C2H4","bond":"H–C","rho":0.2797,"lap":-1.02,"H":-0.287,"G":0.032,"eps":0.012},{"m":"C3H6","bond":"H–C","rho":0.2771,"lap":-0.9803,"H":-0.2803,"G":0.0353,"eps":0.027},{"m":"C3H6","bond":"C–C","rho":0.2437,"lap":-0.5127,"H":-0.2085,"G":0.0803,"eps":0.475}];
// ---------- страница «Атомы в молекулах: теория Бейдера» ----------
const NS='http://www.w3.org/2000/svg',$=id=>document.getElementById(id);
function el(tag,a,p,t){const e=document.createElementNS(NS,tag);for(const k in a)e.setAttribute(k,a[k]);if(t!=null)e.textContent=t;if(p)p.appendChild(e);return e}
const tok=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const fmt=(x,d=3)=>{if(x==null||!isFinite(x))return '—';if(Math.abs(x)<0.5*Math.pow(10,-d))x=0;return x.toFixed(d).replace('-','−')};
const fsg=(x,d=2)=>(x>0.5*Math.pow(10,-d)?'+':'')+fmt(x,d);
const SUBN=s=>s.replace(/(\d)/g,'<sub>$1</sub>');
let META=null;
const MOLS=[['H2','H₂'],['LiH','LiH'],['LiF','LiF'],['HF','HF'],['N2','N₂'],['CO','CO'],['F2','F₂'],['H2O','H₂O'],['NH3','NH₃'],['CH4','CH₄'],['C2H4','C₂H₄'],['C3H6','C₃H₆'],['C6H6','C₆H₆'],['CO2','CO₂'],['F2CO','F₂CO'],['BF3','BF₃'],['C6F6','C₆F₆']];
const BASES=['STO-3G','6-31G','6-31G*','6-31G**'];
const NBF={'STO-3G':{H:1,h:5},'6-31G':{H:2,h:9},'6-31G*':{H:2,h:15},'6-31G**':{H:5,h:15}};
const nbfOf=(k,b)=>META.M[k].a.reduce((s,a)=>s+(a[0]==='H'?NBF[b].H:NBF[b].h),0);
const allowed=(k,b)=>nbfOf(k,b)<=60&&META.M[k].a.every(a=>META.has[b].includes(a[0]));
const S={k:'H2O',b:'6-31G**',f:'rho',lay:{gp:true,ias:true,gr:true}};
const cache={};const key=(k,b)=>k+'|'+b;
// ---------- calculations: the Python server, stage by stage ----------
let busy=null,queue=[];
const B64=s=>{const b=atob(s),u=new Uint8Array(b.length);for(let i=0;i<b.length;i++)u[i]=b.charCodeAt(i);return u.buffer};
function dec(x){if(Array.isArray(x))return x.map(dec);if(x&&typeof x==='object'){if(typeof x.f32==='string')return new Float32Array(B64(x.f32));if(typeof x.u32==='string')return new Uint32Array(B64(x.u32));const o={};for(const k in x)o[k]=dec(x[k]);return o}return x}
function onMsg(m){const c=cache[key(m.k,m.b)]||(cache[key(m.k,m.b)]={});c[m.stage]=m;
  if(m.stage==='bader'||m.stage==='err'){busy=null;next()}
  if(m.k===S.k&&m.b===S.b)render();renderQ();updAll()}
function next(){if(busy||!queue.length)return;const j=queue.shift();const c=cache[key(j.k,j.b)];if(c&&c.bader){next();return}busy=j;
  (async()=>{for(const st of ['scf','map','vol','esp','bader']){if(busy!==j)return;const c2=cache[key(j.k,j.b)];if(c2&&c2[st])continue;let m;
    try{m=await QC.api('aim.stage',{k:j.k,b:j.b,stage:st})}catch(err){m={stage:'err',msg:String(err&&err.message||err)}}
    if(busy!==j)return;m.k=j.k;m.b=j.b;onMsg(dec(m));if(m.stage==='err')return}})()}
function request(k,b,front){const c=cache[key(k,b)];if(c&&c.bader)return;if(busy&&busy.k===k&&busy.b===b)return;if(queue.some(j=>j.k===k&&j.b===b))return;
  if(front){// текущий выбор важнее: прерываем фоновую работу воркера
    if(busy&&!(busy.k===k&&busy.b===b)){const c2=cache[key(busy.k,busy.b)];if(c2&&!c2.bader)delete cache[key(busy.k,busy.b)];queue.unshift(busy);busy=null}
    queue.unshift({k,b})}else queue.push({k,b});next()}
// ---------- элементы управления ----------
function chips(box,items,cur,cb,dis){box.innerHTML='';items.forEach(([v,h])=>{const b=document.createElement('button');b.type='button';b.className='chip';b.innerHTML=h;b.setAttribute('aria-pressed',v===cur);if(dis&&dis(v)){b.disabled=true;b.title=META.M[S.k].a.every(a=>META.has[v].includes(a[0]))?'Too many basis functions for a calculation in the browser':'Only the STO-3G basis is available for boron'}b.onclick=()=>cb(v);box.appendChild(b)})}
function ui(){chips($('mG'),MOLS,S.k,v=>{S.k=v;if(!allowed(v,S.b))S.b=BASES.slice().reverse().find(b=>allowed(v,b));go()});
  chips($('bG'),BASES.map(b=>[b,b]),S.b,v=>{S.b=v;go()},b=>!allowed(S.k,b));
  chips($('fG'),[['rho','ρ'],['lap','∇²ρ']],S.f,v=>{S.f=v;ui();drawMap()});
  const lb=$('lG');lb.innerHTML='';[['gp','∇ρ paths'],['ias','atomic boundaries'],['gr','bond paths']].forEach(([v,h])=>{const b=document.createElement('button');b.type='button';b.className='chip';b.textContent=h;b.setAttribute('aria-pressed',S.lay[v]);b.onclick=()=>{S.lay[v]=!S.lay[v];ui();drawMap()};lb.appendChild(b)})}
function go(){ui();request(S.k,S.b,true);render()}
// ---------- карта ----------
const cv=$('map'),ctx=cv.getContext('2d');let geom=null;
function mapXY(m,s,t){return [(s-m.P.s0)/(m.P.s1-m.P.s0)*cv.width,(m.P.t1-t)/(m.P.t1-m.P.t0)*cv.height]}
function contours(F,nx,ny,lev){// маршрутизация квадратов: отрезки в координатах сетки
  const segs=[];for(let j=0;j<ny-1;j++)for(let i=0;i<nx-1;i++){const a=F[j*nx+i]-lev,b=F[j*nx+i+1]-lev,c=F[(j+1)*nx+i+1]-lev,d=F[(j+1)*nx+i]-lev;
    const idx=(a>0?1:0)|(b>0?2:0)|(c>0?4:0)|(d>0?8:0);if(idx===0||idx===15)continue;
    const e=[[i+a/(a-b),j],[i+1,j+b/(b-c)],[i+d/(d-c),j+1],[i,j+a/(a-d)]];// верх, право, низ, лево
    const T={1:[[3,0]],2:[[0,1]],3:[[3,1]],4:[[1,2]],5:[[3,0],[1,2]],6:[[0,2]],7:[[3,2]],8:[[2,3]],9:[[0,2]],10:[[0,1],[2,3]],11:[[1,2]],12:[[1,3]],13:[[0,1]],14:[[0,3]]}[idx];
    T.forEach(([p,q])=>segs.push([e[p],e[q]]))}return segs}
function drawMap(){const c=cache[key(S.k,S.b)];const m=c&&c.map;const sc=c&&c.scf;
  $('mapT').innerHTML=(S.f==='rho'?'Electron density ρ':'Laplacian of the density ∇²ρ')+' in the molecular plane '+MOLS.find(x=>x[0]===S.k)[1]+', '+S.b;
  if(!m){cv.width=640;cv.height=480;ctx.fillStyle=tok('--soft');ctx.fillRect(0,0,cv.width,cv.height);ctx.fillStyle=tok('--muted');ctx.font='15px '+tok('--f-body');ctx.textAlign='center';ctx.fillText(sc?'Drawing the map…':'Computing the wave function…',cv.width/2,cv.height/2);legend();return}
  const W0=640,H0=Math.round(W0*(m.P.t1-m.P.t0)/(m.P.s1-m.P.s0));if(cv.width!==W0||cv.height!==H0){cv.width=W0;cv.height=H0}
  const kx=cv.width/(m.nx-1),ky=cv.height/(m.ny-1);ctx.fillStyle=tok('--panel');ctx.fillRect(0,0,cv.width,cv.height);
  const line=(segs,col,w,dash)=>{ctx.strokeStyle=col;ctx.lineWidth=w;ctx.setLineDash(dash||[]);ctx.beginPath();segs.forEach(([p,q])=>{ctx.moveTo(p[0]*kx,p[1]*ky);ctx.lineTo(q[0]*kx,q[1]*ky)});ctx.stroke();ctx.setLineDash([])};
  if(S.f==='rho'){const levs=[];for(let e=-3;e<=2;e++)for(const f of [1,2,4,8])levs.push(f*Math.pow(10,e));
    ctx.globalAlpha=0.75;levs.forEach(L=>line(contours(m.R,m.nx,m.ny,L),tok('--ci')||tok('--accent'),1));ctx.globalAlpha=1}
  else{// заливка знака и изолинии
    const img=ctx.createImageData(m.nx,m.ny);const cp=hex(tok('--lp')),cn=hex(tok('--ln'));
    for(let i=0;i<m.nx*m.ny;i++){const v=m.L[i];const col=v<0?cp:cn;const a=Math.min(1,Math.log10(1+Math.abs(v)*50)/3)*70;img.data[4*i]=col[0];img.data[4*i+1]=col[1];img.data[4*i+2]=col[2];img.data[4*i+3]=a}
    const oc=document.createElement('canvas');oc.width=m.nx;oc.height=m.ny;oc.getContext('2d').putImageData(img,0,0);ctx.imageSmoothingEnabled=true;ctx.drawImage(oc,0,0,cv.width,cv.height);
    const levs=[];for(let e=-3;e<=1;e++)for(const f of [1,2,4,8])levs.push(f*Math.pow(10,e));
    levs.forEach(L=>{line(contours(m.L,m.nx,m.ny,-L),tok('--lp'),1);line(contours(m.L,m.nx,m.ny,L),tok('--ln'),1,[4,3])})}
  const poly=(pts,col,w)=>{if(pts.length<2)return;ctx.strokeStyle=col;ctx.lineWidth=w;ctx.beginPath();pts.forEach(([s,t],i)=>{const [x,y]=mapXY(m,s,t);i?ctx.lineTo(x,y):ctx.moveTo(x,y)});ctx.stroke()};
  if(S.lay.gp){ctx.globalAlpha=0.4;m.gp.forEach(p=>poly(p,tok('--muted'),0.8));ctx.globalAlpha=1}
  if(S.lay.ias)m.ias.forEach(p=>poly(p,tok('--ink'),2.2));
  if(S.lay.gr)m.bpaths.forEach(h=>h.forEach(p=>poly(p,tok('--accent'),3)));
  // атомы
  sc.atoms.forEach((a,i)=>{const [x,y]=mapXY(m,m.P.pr[i][0],m.P.pr[i][1]);const inp=m.P.inpl[i];ctx.globalAlpha=inp?1:0.35;
    ctx.fillStyle=tok('--panel');ctx.strokeStyle=tok('--ink');ctx.lineWidth=1.5;ctx.beginPath();ctx.arc(x,y,a.el==='H'?9:12,0,2*Math.PI);ctx.fill();ctx.stroke();
    ctx.fillStyle=tok('--ink');ctx.font='600 12px '+tok('--f-body');ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(a.el,x,y+0.5);ctx.globalAlpha=1});
  // критические точки
  m.cp2.forEach(c=>{if(c.type==='n'||c.off>0.05)return;const [x,y]=mapXY(m,c.xy[0],c.xy[1]);
    if(c.type==='b'){ctx.fillStyle=tok('--warn');ctx.strokeStyle=tok('--panel');ctx.lineWidth=1.5;ctx.beginPath();ctx.arc(x,y,4.5,0,2*Math.PI);ctx.fill();ctx.stroke()}
    else{ctx.fillStyle=tok('--ok');ctx.beginPath();ctx.moveTo(x,y-6);ctx.lineTo(x+5.5,y+4);ctx.lineTo(x-5.5,y+4);ctx.closePath();ctx.fill()}});
  geom=m;legend()}
function legend(){const L=$('mapL');const parts=[];
  if(S.f==='rho')parts.push('<span><i class="ln" style="border-color:var(--ci)"></i>ρ contours: 0.001; 0.002; 0.004; 0.008; 0.01 … a.u.</span>');
  else parts.push('<span><i class="ln" style="border-color:var(--lp)"></i>∇²ρ &lt; 0: concentration</span><span><i class="ln" style="border-color:var(--ln);border-top-style:dashed"></i>∇²ρ &gt; 0: depletion</span>');
  if(S.lay.ias)parts.push('<span><i class="ln" style="border-color:var(--ink)"></i>interatomic surface</span>');
  if(S.lay.gr)parts.push('<span><i class="ln" style="border-color:var(--accent);border-top-width:3px"></i>bond path</span>');
  parts.push('<span><i class="dt" style="background:var(--warn)"></i>bond CP</span><span><i class="tr" style="border-bottom-color:var(--ok)"></i>ring CP</span>');
  L.innerHTML=parts.join('')}
function hex(c){c=c.trim();if(c.startsWith('#')){if(c.length===4)c='#'+c[1]+c[1]+c[2]+c[2]+c[3]+c[3];return [1,3,5].map(i=>parseInt(c.slice(i,i+2),16))}
  const m=c.match(/\d+(\.\d+)?/g);return m?m.slice(0,3).map(Number):[0,0,0]}
cv.addEventListener('click',e=>{const m=geom;if(!m)return;const r=cv.getBoundingClientRect();const fx=(e.clientX-r.left)/r.width,fy=(e.clientY-r.top)/r.height;
  const i=Math.round(fx*(m.nx-1)),j=Math.round(fy*(m.ny-1));if(i<0||j<0||i>=m.nx||j>=m.ny)return;const v=m.R[j*m.nx+i],l=m.L[j*m.nx+i];
  $('pt').innerHTML='At the point: ρ = '+fmt(v,4)+' a.u., ∇²ρ = '+fmt(l,3)+' a.u. — '+(l<0?'density is concentrated (∇²ρ &lt; 0)':'density is depleted (∇²ρ &gt; 0)')+'.'});
// ---------- подписи атомов и групп эквивалентных атомов ----------
function groups(sc){const g=[];sc.atoms.forEach((a,i)=>{const q=sc.mul[i];const f=g.find(x=>x.el===a.el&&Math.abs(x.q-q)<2e-3);if(f)f.idx.push(i);else g.push({el:a.el,q,idx:[i]})});return g}
const glab=(g,all)=>{const same=all.filter(x=>x.el===g.el);let s=g.el;if(same.length>1)s+=['','′','″','‴'][same.indexOf(g)]||'';return s+(g.idx.length>1?' (×'+g.idx.length+')':'')};
const ORD={H:9,Li:1,C:2,N:3,O:4,F:5};const bondName=(sc,ats)=>{const e=ats.map(i=>i<0?'?':sc.atoms[i].el);
  e.sort((a,b)=>(ORD[a]||0)-(ORD[b]||0));if(e[0]==='H'&&e[1]==='F')return 'H–F';if(e.includes('Li')&&e.includes('H'))return 'Li–H';return e.join('–')};
// ---------- вывод ----------
function render(){const c=cache[key(S.k,S.b)]||{};const sc=c.scf;drawMap();
  if(!sc){$('infoTab').innerHTML='';$('st1').innerHTML='<span class="busy">Computing RHF/'+S.b+'…</span>';$('cpTab').innerHTML='';$('st2').innerHTML='';return}
  const g=groups(sc);
  $('infoTab').innerHTML='<table class="mtab"><tbody>'+
    '<tr><td class="l">Method</td><td>RHF/'+S.b+'</td></tr><tr><td class="l">Basis functions</td><td>'+sc.nbf+'</td></tr>'+
    '<tr><td class="l">Total energy</td><td>'+fmt(sc.E,5)+' a.u.</td></tr><tr><td class="l">SCF iterations</td><td>'+sc.it+(sc.conv===false?' — <b style="color:var(--warn)">SCF has not converged, the results are unreliable</b>':'')+'</td></tr>'+
    '<tr><td class="l">ε<sub>HOMO</sub></td><td>'+fmt(sc.eps[sc.nocc-1],3)+' a.u.</td></tr></tbody></table>';
  $('st1').innerHTML=(c.map?'':'<span class="busy">Drawing the map and paths…</span> ')+(c.bader?'':'<span class="busy">Integrating atomic basins…</span> ')+
    (c.err?'Calculation error: '+c.err.msg:'')+(c.map&&c.bader?'The calculation took '+fmt(c.bader.ms/1000,1)+' s. Atoms outside the map plane are shown faded. '+(S.k==='CH4'?'Only two of the four H atoms lie in the plane.':S.k==='C3H6'||S.k==='NH3'?'Some H atoms lie outside the map plane.':''):'');
  // таблица КТ
  const cps=sc.cps;const cnt={n:0,b:0,r:0,c:0};cps.forEach(x=>cnt[x.type]++);
  const seen=[];const rows=cps.filter(x=>x.type!=='n').filter(x=>{const k2=x.type+(x.atoms?bondName(sc,x.atoms):'')+x.rho.toFixed(4);if(seen.includes(k2)){seen.push(k2);return false}seen.push(k2);return true});
  const mult=x=>seen.filter(s=>s===x.type+(x.atoms?bondName(sc,x.atoms):'')+x.rho.toFixed(4)).length;
  const TN={b:'bond (3, −1)',r:'ring (3, +1)',c:'cage (3, +3)'};
  $('cpTab').innerHTML='<table class="mtab"><thead><tr><th class="l">Point</th><th class="l">Atoms</th><th>ρ</th><th>∇²ρ</th><th>λ₁, λ₂, λ₃</th><th>ε</th><th>H = G + V</th><th>|V|/G</th></tr></thead><tbody>'+
    rows.map(x=>'<tr><td class="l">'+TN[x.type]+(mult(x)>1?' ×'+mult(x):'')+'</td><td class="l">'+(x.atoms?bondName(sc,x.atoms):'—')+'</td><td>'+fmt(x.rho,3)+'</td><td>'+fmt(x.lap,3)+'</td><td>'+x.l.map(v=>fmt(v,2)).join('; ')+'</td><td>'+(x.eps==null?'—':fmt(x.eps,2))+'</td><td>'+fmt(x.H,3)+'</td><td>'+(x.G>1e-4?fmt(Math.abs(x.V)/x.G,2):'—')+'</td></tr>').join('')+'</tbody></table>';
  const ph=cnt.n-cnt.b+cnt.r-cnt.c;const na=sc.atoms.filter((a,i)=>sc.noatt[i]).map(a=>a.el);
  let t='Found: maxima (3, −3): '+cnt.n+', bond points — '+cnt.b+', rings — '+cnt.r+', cages — '+cnt.c+'. Poincaré–Hopf check: '+cnt.n+' − '+cnt.b+' + '+cnt.r+' − '+cnt.c+' = '+ph+(ph===1?' ✓':' — some point was not found')+'. ';
  const bs=rows.filter(x=>x.type==='b');
  t+=bs.map(x=>'<b>'+bondName(sc,x.atoms)+'</b>: '+(x.lap<0?'∇²ρ<sub>b</sub> &lt; 0 — density is concentrated between the nuclei, a shared (covalent) interaction':x.H<0?'∇²ρ<sub>b</sub> &gt; 0 but H<sub>b</sub> &lt; 0 — a strongly polar bond with a significant covalent contribution':'∇²ρ<sub>b</sub> &gt; 0 and H<sub>b</sub> &gt; 0 — a closed-shell interaction, an ionic bond')+
    (x.eps>0.2?'; ellipticity '+fmt(x.eps,2)+' — the density is stretched in the plane of the π system':'')+'.').join(' ');
  if(na.length)t+=' <b>Atom '+na.join(', ')+' has no density maximum</b>: in the minimal basis the density increases monotonically from H toward the neighbouring atom, and H forms no basin of its own. This is an artifact of a basis without a cusp at the nucleus — look at the same molecule in 6-31G.';
  if(S.k==='C3H6')t+=' The C–C bond paths bend outward from the ring (“banana” bonds), and the large ellipticity reflects ring strain.';
  if(S.k==='C6H6')t+=' At the ring center there is a ring point (3, +1): the density there is minimal in the ring plane and maximal along the axis.';
  $('st2').innerHTML=t;renderQ()}
// таблица зарядов: строки — базисы, посчитанные для текущей молекулы
function renderQ(){const c0=Object.keys(cache).filter(k2=>k2.startsWith(S.k+'|')).map(k2=>cache[k2]).filter(c=>c.scf);
  if(!c0.length){$('qTab').innerHTML='';$('st3').innerHTML='';return}
  const g=groups(c0[0].scf);const rows=BASES.map(b=>cache[key(S.k,b)]).filter(c=>c&&c.scf);
  const head='<tr><th class="l">Basis</th>'+g.map(x=>'<th colspan="3">'+glab(x,g)+'</th>').join('')+'</tr><tr><th></th>'+g.map(()=>'<th>Mull.</th><th>Löwd.</th><th>Bader</th>').join('')+'</tr>';
  const body=rows.map(c=>{const sc=c.scf;const gg=groups(sc);return '<tr'+(sc.b===S.b?' style="font-weight:600"':'')+'><td class="l">'+sc.b+'</td>'+g.map(x=>{const i=x.idx[0];
    return '<td>'+fsg(sc.mul[i])+'</td><td>'+fsg(sc.low[i])+'</td><td>'+(c.bader?fsg(c.bader.q[i]):'<span class="busy">…</span>')+'</td>'}).join('')+'</tr>'}).join('');
  $('qTab').innerHTML='<table class="mtab"><thead>'+head+'</thead><tbody>'+body+'</tbody></table>';
  // вывод
  const done=rows.filter(c=>c.bader);let t='';
  if(done.length>=2){const i=g.find(x=>x.el!=='H'&&x.el!=='Li')?g.find(x=>x.el!=='H'&&x.el!=='Li').idx[0]:g[0].idx[0];const el2=c0[0].scf.atoms[i].el;
    const sp=a=>Math.max(...a)-Math.min(...a);const m=done.map(c=>c.scf.mul[i]),l=done.map(c=>c.scf.low[i]),bq=done.map(c=>c.bader.q[i]);
    t='Spread of the charge of '+el2+' between bases: Mulliken '+fmt(sp(m),2)+', Löwdin '+fmt(sp(l),2)+', Bader '+fmt(sp(bq),2)+'. ';}
  const cb=cache[key(S.k,S.b)];
  if(cb&&cb.bader)t+='Sum of electrons over all basins: '+fmt(cb.bader.tot,3)+' — the integration is correct. ';
  t+='The Bader charge is a property of the density itself: as the basis grows it converges to a limit. Mulliken charges have no such limit — in large bases with diffuse functions they change unpredictably. In the small bases of this page all three schemes change, especially when moving away from STO-3G. ';
  if(cb&&cb.scf&&cb.scf.noatt.some(x=>x))t+='<b>Note:</b> '+cb.scf.atoms.filter((a,i)=>cb.scf.noatt[i]).map(a=>a.el).join(', ')+' has no density maximum of its own in this basis, so it has no basin and its whole electron goes to the neighbour — charge +1. This is an artifact of a basis without a cusp at the nucleus; in 6-31G and larger the maximum appears. ';
  if(['H2O','HF','NH3','LiF','LiH','CO'].includes(S.k))t+='Bader charges are noticeably larger in magnitude than Mulliken charges: the atomic boundary lies where the density is minimal, and the more electronegative atom gets almost all of the bond density.';
  if(['CH4','C2H4','C3H6','C6H6'].includes(S.k))t+='H charges in hydrocarbons are small, and their sign depends on the basis: polarization functions on H (6-31G**) shift the C–H bond point, and the atomic boundary moves with it.';
  $('st3').innerHTML=t}
// все базисы
function updAll(){const todo=BASES.filter(b=>allowed(S.k,b)&&!(cache[key(S.k,b)]&&cache[key(S.k,b)].bader));const run=busy||queue.length;
  $('allB').disabled=!todo.length;$('allSt').textContent=run?'Calculating… in queue: '+(queue.length+(busy?1:0)):'';}
$('allB').onclick=()=>{BASES.filter(b=>allowed(S.k,b)).forEach(b=>request(S.k,b,false));updAll()};
// ---------- диаграмма типов связей ----------
function drawSc(){const sv=$('sc');sv.innerHTML='';const W=560,H=380,L=60,R=16,T=16,B=48;const pw=W-L-R,ph=H-T-B;
  const x0=0,x1=0.75,y0=-3,y1=1.8;const X=x=>L+(x-x0)/(x1-x0)*pw,Y=y=>T+(y1-y)/(y1-y0)*ph;
  el('rect',{x:L,y:Y(y1),width:pw,height:Y(0)-Y(y1),fill:tok('--ln'),opacity:0.06},sv);el('rect',{x:L,y:Y(0),width:pw,height:Y(y0)-Y(0),fill:tok('--lp'),opacity:0.06},sv);
  el('line',{x1:L,y1:Y(0),x2:L+pw,y2:Y(0),stroke:tok('--muted'),'stroke-dasharray':'4 3'},sv);
  el('line',{x1:L,y1:T,x2:L,y2:T+ph,stroke:tok('--line')},sv);el('line',{x1:L,y1:T+ph,x2:L+pw,y2:T+ph,stroke:tok('--line')},sv);
  for(let x=0;x<=0.75;x+=0.25)el('text',{x:X(x),y:T+ph+16,'text-anchor':'middle','font-size':11,fill:tok('--muted')},sv,fmt(x,2));
  for(let y=-3;y<=1;y+=1)el('text',{x:L-6,y:Y(y)+4,'text-anchor':'end','font-size':11,fill:tok('--muted')},sv,fmt(y,0));
  el('text',{x:L+pw/2,y:H-8,'text-anchor':'middle','font-size':12,fill:tok('--ink')},sv,'');{const t=sv.lastChild;t.innerHTML='ρ<tspan dy="3.5" font-size="0.75em">b</tspan><tspan dy="-3.5">, a.u.</tspan>'}
  const ty=el('text',{x:16,y:T+ph/2,'text-anchor':'middle','font-size':12,fill:tok('--ink'),transform:'rotate(-90 16 '+(T+ph/2)+')'},sv,'');ty.innerHTML='∇²ρ<tspan dy="3.5" font-size="0.75em">b</tspan><tspan dy="-3.5">, a.u.</tspan>';
  el('text',{x:L+pw-6,y:Y(y1)+14,'text-anchor':'end','font-size':11.5,fill:tok('--muted')},sv,'depletion: closed shells, strongly polar');
  el('text',{x:L+pw-6,y:Y(y0)-6,'text-anchor':'end','font-size':11.5,fill:tok('--muted')},sv,'concentration: covalent bonds');
  const tip=el('text',{x:0,y:0,'font-size':12,fill:tok('--ink'),'font-weight':600},sv,'');
  BONDS.forEach(d=>{const lab=MOLS.find(x=>x[0]===d.m)[1]+': '+fixB(d.bond);
    const c=el('circle',{cx:X(d.rho),cy:Y(d.lap),r:6,fill:d.H<0?tok('--accent'):tok('--warn'),stroke:tok('--panel'),'stroke-width':1.5,tabindex:0,'aria-label':lab},sv);
    el('title',{},c,lab+' — ρb = '+fmt(d.rho,3)+', ∇²ρb = '+fmt(d.lap,2)+', Hb = '+fmt(d.H,3));
    const show=()=>{tip.textContent=lab;tip.setAttribute('x',Math.min(X(d.rho)+9,W-150));tip.setAttribute('y',Y(d.lap)-9)};c.addEventListener('mouseenter',show);c.addEventListener('focus',show)});
  $('st4').innerHTML='The C–H, N–H, O–H, H–F, C–C and N≡N bonds lie below zero: these are classic covalent bonds. LiF and LiH lie above zero with H<sub>b</sub> &gt; 0: ionic. CO and F₂ are also above zero but with H<sub>b</sub> &lt; 0: in CO the density at the bond point is large, but the point is shifted toward C and falls into its depletion region; in F₂ it is a long bond between two atoms with nearly filled shells. So the sign of ∇²ρ<sub>b</sub> is not a “covalency test” but one of several criteria read together.'}
const fixB=b=>({'H–Li':'Li–H','F–Li':'Li–F','O–C':'C–O','H–O':'O–H','H–N':'N–H','H–C':'C–H','H–F':'H–F'})[b]||b;
drawSc();QC.api('aim.meta',{}).then(m=>{META=m;ui();go();updAll()}).catch(()=>{});
addEventListener('message',e=>{if(e.data&&'proj' in e.data)setTimeout(()=>{drawMap();drawSc()},50)});
if(window.matchMedia)try{matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>{drawMap();drawSc()})}catch(e){}
// ---------- 2. трёхмерный вид: WebGL без внешних библиотек ----------
const PLDESC={H2:'a plane containing the molecular axis',LiH:'a plane containing the molecular axis',LiF:'a plane containing the molecular axis',HF:'a plane containing the molecular axis',
  N2:'a plane containing the molecular axis',CO:'a plane containing the molecular axis',F2:'a plane containing the molecular axis',CO2:'a plane containing the molecular axis',H2O:'the molecular plane',
  NH3:'a plane through the C₃ axis, the N atom and one H atom',CH4:'an H–C–H plane through two H atoms',C2H4:'the molecular plane',C3H6:'the plane of the ring of C atoms',C6H6:'the ring plane',
  F2CO:'the molecular plane',BF3:'the molecular plane',C6F6:'the ring plane'};
const ACOL={H:[0.9,0.91,0.93],Li:[0.6,0.36,0.83],B:[0.96,0.65,0.55],C:[0.3,0.32,0.35],N:[0.23,0.36,0.85],O:[0.85,0.23,0.17],F:[0.31,0.68,0.23]};
const ARAD={H:0.36,Li:0.62,B:0.55,C:0.52,N:0.5,O:0.49,F:0.46};
const mul3=(A,B)=>A.map(r=>[0,1,2].map(j=>r[0]*B[0][j]+r[1]*B[1][j]+r[2]*B[2][j]));
const rotX=a=>[[1,0,0],[0,Math.cos(a),-Math.sin(a)],[0,Math.sin(a),Math.cos(a)]],rotY=a=>[[Math.cos(a),0,Math.sin(a)],[0,1,0],[-Math.sin(a),0,Math.cos(a)]];
const V3={fn:'esp',val:{rho:0.05,lap:2,mo:0},sh:{atoms:true,graph:true,plane:false,labels:true},rng:null,R:null,zoom:1,key:null,gl:undefined,glFail:false,scene:null};
function v3Base(){const [u,w]=META.PL[S.k];const n=[u[1]*w[2]-u[2]*w[1],u[2]*w[0]-u[0]*w[2],u[0]*w[1]-u[1]*w[0]];return [u,w,n]}
function v3View(kind){const B=v3Base();V3.R=kind==='face'?B:mul3(mul3(rotX(-0.95),rotY(0.55)),B);V3.zoom=1;draw3()}
// ---- WebGL ----
function mkGL(cv){const gl=cv.getContext('webgl',{antialias:true,premultipliedAlpha:false,alpha:true});if(!gl)return null;gl.getExtension('OES_element_index_uint');
  const sh=(t,src)=>{const s=gl.createShader(t);gl.shaderSource(s,src);gl.compileShader(s);return s};
  const prog=(vs,fs)=>{const p=gl.createProgram();gl.attachShader(p,sh(gl.VERTEX_SHADER,vs));gl.attachShader(p,sh(gl.FRAGMENT_SHADER,fs));gl.linkProgram(p);return p};
  const lit=prog(`attribute vec3 aP;attribute vec3 aN;attribute vec4 aC;uniform mat4 uM;uniform mat4 uPr;uniform mat3 uR;varying vec3 vN;varying vec4 vC;varying vec3 vV;
    void main(){vec4 p=uM*vec4(aP,1.0);vV=p.xyz;vN=uR*aN;vC=aC;gl_Position=uPr*p;}`,
   `precision mediump float;varying vec3 vN;varying vec4 vC;varying vec3 vV;uniform float uA;
    void main(){vec3 n=normalize(vN);vec3 l=normalize(vec3(0.35,0.55,1.0));float d=abs(dot(n,l));vec3 v=normalize(-vV);vec3 h=normalize(l+v);
    float s=pow(abs(dot(n,h)),48.0)*0.3;gl_FragColor=vec4(vC.rgb*(0.38+0.62*d)+s,vC.a*uA);}`);
  const tex=prog(`attribute vec3 aP;attribute vec2 aT;uniform mat4 uM;uniform mat4 uPr;varying vec2 vT;void main(){vT=aT;gl_Position=uPr*uM*vec4(aP,1.0);}`,
   `precision mediump float;varying vec2 vT;uniform sampler2D uS;uniform float uA;void main(){vec4 c=texture2D(uS,vT);gl_FragColor=vec4(c.rgb,uA);}`);
  return {gl,lit,tex,texObj:gl.createTexture()}}
function buf(gl,data,el){const b=gl.createBuffer();const t=el?gl.ELEMENT_ARRAY_BUFFER:gl.ARRAY_BUFFER;gl.bindBuffer(t,b);gl.bufferData(t,data,gl.STATIC_DRAW);return b}
function meshGL(G,m){const gl=G.gl;return {p:buf(gl,m.pos),n:buf(gl,m.nrm),c:buf(gl,m.col),i:buf(gl,m.idx,true),cnt:m.idx.length,alpha:m.alpha==null?1:m.alpha,two:m.two}}
function freeGL(G,o){if(!o)return;const gl=G.gl;['p','n','c','i'].forEach(k=>o[k]&&gl.deleteBuffer(o[k]))}
// геометрия: сферы и трубки
const ICO=(()=>{const t=(1+Math.sqrt(5))/2;let v=[[-1,t,0],[1,t,0],[-1,-t,0],[1,-t,0],[0,-1,t],[0,1,t],[0,-1,-t],[0,1,-t],[t,0,-1],[t,0,1],[-t,0,-1],[-t,0,1]].map(p=>{const l=Math.hypot(...p);return p.map(x=>x/l)});
  let f=[[0,11,5],[0,5,1],[0,1,7],[0,7,10],[0,10,11],[1,5,9],[5,11,4],[11,10,2],[10,7,6],[7,1,8],[3,9,4],[3,4,2],[3,2,6],[3,6,8],[3,8,9],[4,9,5],[2,4,11],[6,2,10],[8,6,7],[9,8,1]];
  for(let it=0;it<2;it++){const mid={};const g=[];const m=(a,b)=>{const k=a<b?a+'_'+b:b+'_'+a;if(mid[k]!=null)return mid[k];const p=v[a].map((x,i)=>(x+v[b][i])/2);const l=Math.hypot(...p);v.push(p.map(x=>x/l));return mid[k]=v.length-1};
    f.forEach(([a,b,c])=>{const ab=m(a,b),bc=m(b,c),ca=m(c,a);g.push([a,ab,ca],[b,bc,ab],[c,ca,bc],[ab,bc,ca])});f=g}
  return {v,f}})();
function geomBuilder(){const P=[],N=[],C=[],I=[];return {P,N,C,I,
  sphere(c,r,col){const o=P.length/3;ICO.v.forEach(p=>{P.push(c[0]+r*p[0],c[1]+r*p[1],c[2]+r*p[2]);N.push(...p);C.push(...col)});ICO.f.forEach(t=>I.push(o+t[0],o+t[1],o+t[2]))},
  tube(a,b,r,col){const d=[b[0]-a[0],b[1]-a[1],b[2]-a[2]];const L=Math.hypot(...d);if(L<1e-6)return;const z=d.map(x=>x/L);const t0=Math.abs(z[0])<0.9?[1,0,0]:[0,1,0];
    let x=[z[1]*t0[2]-z[2]*t0[1],z[2]*t0[0]-z[0]*t0[2],z[0]*t0[1]-z[1]*t0[0]];const lx=Math.hypot(...x);x=x.map(q=>q/lx);const y=[z[1]*x[2]-z[2]*x[1],z[2]*x[0]-z[0]*x[2],z[0]*x[1]-z[1]*x[0]];
    const o=P.length/3,K=10;for(let k=0;k<K;k++){const ph=2*Math.PI*k/K,cs=Math.cos(ph),sn=Math.sin(ph);const nn=[cs*x[0]+sn*y[0],cs*x[1]+sn*y[1],cs*x[2]+sn*y[2]];
      for(const e of [a,b]){P.push(e[0]+r*nn[0],e[1]+r*nn[1],e[2]+r*nn[2]);N.push(...nn);C.push(...col)}}
    for(let k=0;k<K;k++){const k2=(k+1)%K;I.push(o+2*k,o+2*k+1,o+2*k2+1,o+2*k,o+2*k2+1,o+2*k2)}},
  done(alpha){return {pos:new Float32Array(P),nrm:new Float32Array(N),col:new Float32Array(C),idx:new Uint32Array(I),alpha}}}}
function colored(m,rgba){const n=m.pos.length/3,c=new Float32Array(4*n);for(let i=0;i<n;i++)c.set(rgba,4*i);return {pos:m.pos,nrm:m.nrm,idx:m.idx,col:c}}
function espColor(v,rng){const t=Math.max(-1,Math.min(1,v/rng));const st=[[0.78,0.12,0.10],[0.97,0.70,0.18],[0.66,0.90,0.38],[0.22,0.72,0.86],[0.14,0.28,0.80]];const x=(t+1)*2,i=Math.min(3,Math.floor(x)),f=x-i,a=st[i],b=st[i+1];return [a[0]+(b[0]-a[0])*f,a[1]+(b[1]-a[1])*f,a[2]+(b[2]-a[2])*f,1]}
// ---- сцена ----
const KJ=2625.5;
function c3(){return cache[key(S.k,S.b)]||{}}
function triL(F,G,x,y,z){const [nx,ny,nz]=G.n;const fx=(x-G.o[0])/G.h,fy=(y-G.o[1])/G.h,fz=(z-G.o[2])/G.h;const i=Math.min(nx-2,Math.max(0,Math.floor(fx))),j=Math.min(ny-2,Math.max(0,Math.floor(fy))),k=Math.min(nz-2,Math.max(0,Math.floor(fz)));const u=fx-i,v=fy-j,w=fz-k;let s=0;
  for(let a=0;a<2;a++)for(let b=0;b<2;b++)for(let c=0;c<2;c++)s+=(a?u:1-u)*(b?v:1-v)*(c?w:1-w)*F[((k+c)*ny+j+b)*nx+i+a];return s}
function isoFor(c){const sc=c.scf,vol=c.vol;if(!sc||!vol)return null;c._iso=c._iso||{};
  if(V3.fn==='rho'){const k='rho|'+V3.val.rho;if(!c._iso[k])c._iso[k]=[{m:ISO.iso(vol.R,vol.G,V3.val.rho),col:[0.42,0.62,0.86,1],a:0.38}];return c._iso[k]}
  if(V3.fn==='lap'){const a=V3.val.lap,k='lap|'+a;
    if(!c._iso[k])c._iso[k]=[{m:ISO.iso(vol.L,vol.GL,-a,-1),col:[0.86,0.25,0.18,1],a:0.6},{m:ISO.iso(vol.L,vol.GL,a,1),col:[0.22,0.42,0.86,1],a:0.6}];return c._iso[k]}
  if(V3.fn==='mo'){const kmo=sc.nocc-1+V3.val.mo;if(kmo<0||kmo>=sc.nmo)return [];const k='mo|'+kmo;
    if(!c._iso[k]){c._iso[k]=[];const kk=S.k,bb=S.b;QC.api('aim.mo',{k:kk,b:bb,kmo}).then(Z=>{const F=dec(Z);
      c._iso[k]=[{m:ISO.iso(F,vol.G,0.05,1),col:[0.22,0.45,0.85,1],a:0.55},{m:ISO.iso(F,vol.G,-0.05,-1),col:[0.86,0.33,0.2,1],a:0.55}];if(S.k===kk&&S.b===bb){if(V3.scene)V3.scene.key='';draw3()}}).catch(()=>{delete c._iso[k]})}return c._iso[k]}
  return null}
function buildScene(){const G=V3.gl;if(!G)return;const c=c3(),sc=c.scf;const sceneKey=[S.k,S.b,V3.fn,V3.val[V3.fn],V3.rng,JSON.stringify(V3.sh),!!c.map,!!c.vol,!!c.esp].join('|');
  if(V3.scene&&V3.scene.key===sceneKey)return;if(V3.scene)V3.scene.objs.forEach(o=>freeGL(G,o.gl));
  const objs=[];V3.scene={key:sceneKey,objs};if(!sc)return;
  const g=geomBuilder();if(V3.sh.atoms)sc.atoms.forEach(a=>g.sphere([a.x,a.y,a.z],(ARAD[a.el]||0.5)*(V3.fn==='lap'?0.3:1),[...(ACOL[a.el]||[0.6,0.6,0.6]),1]));
  if(V3.sh.graph){const ac=tokRGB('--accent'),wc=tokRGB('--warn'),oc=tokRGB('--ok');
    sc.cps.forEach(cp=>{if(cp.type==='b'&&cp.path)cp.path.forEach(h=>{for(let i=0;i+1<h.length;i++)g.tube(h[i],h[i+1],0.07,[...ac,1])});
      if(cp.type==='b')g.sphere(cp.p,0.13,[...wc,1]);else if(cp.type!=='n')g.sphere(cp.p,0.15,[...oc,1])})}
  const solid=g.done(1);if(solid.idx.length)objs.push({gl:meshGL(G,solid),kind:'opaque'});
  if(V3.fn==='esp'&&c.esp){const e=c.esp,n=e.V.length,col=new Float32Array(4*n);const rng=V3.rng/KJ;for(let i=0;i<n;i++)col.set(espColor(e.V[i],rng),4*i);
    objs.push({gl:meshGL(G,{pos:e.mesh.pos,nrm:e.mesh.nrm,idx:e.mesh.idx,col}),kind:'trans',alpha:0.92,pre:true})}
  else{const L=isoFor(c);if(L)L.forEach(x=>{if(x.m.idx.length)objs.push({gl:meshGL(G,x.m.col?x.m:colored(x.m,x.col)),kind:'trans',alpha:x.a,pre:!!x.pre})})}
  if(V3.sh.plane&&c.map){const [u,w]=v3Base(),P=c.map.P;const to3=(s,t)=>[s*u[0]+t*w[0],s*u[1]+t*w[1],s*u[2]+t*w[2]];
    const q=[to3(P.s0,P.t1),to3(P.s1,P.t1),to3(P.s1,P.t0),to3(P.s0,P.t0)];const gl=G.gl;
    objs.push({kind:'plane',gl:{p:buf(gl,new Float32Array(q.flat())),t:buf(gl,new Float32Array([0,0,1,0,1,1,0,1])),i:buf(gl,new Uint32Array([0,1,2,0,2,3]),true),cnt:6}});
    gl.bindTexture(gl.TEXTURE_2D,G.texObj);gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,false);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,cv);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE)}}
function tokRGB(n){const v=hex(tok(n));return v.map(x=>x/255)}
// матрицы
function mat4(R,ctr,dist){const m=new Float32Array(16);for(let i=0;i<3;i++)for(let j=0;j<3;j++)m[j*4+i]=R[i][j];
  for(let i=0;i<3;i++)m[12+i]=-(R[i][0]*ctr[0]+R[i][1]*ctr[1]+R[i][2]*ctr[2]);m[14]-=dist;m[15]=1;return m}
function persp(f,asp,n,fa){const t=1/Math.tan(f/2);return new Float32Array([t/asp,0,0,0,0,t,0,0,0,0,(fa+n)/(n-fa),-1,0,0,2*fa*n/(n-fa),0])}
function draw3(){const box=$('gl');if(!box||!META)return;if(V3.glFail){ui3();return}if(!V3.gl){V3.gl=mkGL(box);if(!V3.gl){V3.glFail=true;ui3();$('st5').textContent='The browser does not support WebGL, so the 3D view is unavailable.';return}}
  if(V3.key!==S.k){V3.key=S.k;const B=v3Base();V3.R=mul3(mul3(rotX(-0.95),rotY(0.55)),B);V3.zoom=1;V3.rng=null;V3.rngUser=false}
  const c=c3(),sc=c.scf;const rk=S.k+'|'+S.b;if(c.esp&&V3.rngK!==rk&&!V3.rngUser){V3.rngK=rk;const mx=Math.max(...Array.from(c.esp.V).map(Math.abs))*KJ;V3.rng=Math.max(20,Math.min(300,Math.round(mx*0.6/5)*5))}
  if(V3.rng==null)V3.rng=100;
  const G=V3.gl,gl=G.gl;const dpr=Math.min(2,window.devicePixelRatio||1);const W=Math.round(box.clientWidth*dpr),H=Math.round(box.clientHeight*dpr);
  if(box.width!==W||box.height!==H){box.width=W;box.height=H}const ov=$('glo');if(ov.width!==W||ov.height!==H){ov.width=W;ov.height=H}
  buildScene();gl.viewport(0,0,W,H);gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
  const oc=ov.getContext('2d');oc.clearRect(0,0,W,H);ui3();if(!sc){oc.fillStyle=tok('--muted');oc.font=(15*dpr)+'px '+tok('--f-body');oc.textAlign='center';oc.fillText('Computing the wave function…',W/2,H/2);return}
  // центр и масштаб
  const at=sc.atoms;const ctr=[0,1,2].map(k=>at.reduce((s,a)=>s+[a.x,a.y,a.z][k],0)/at.length);const rad=Math.max(2.5,...at.map(a=>Math.hypot(a.x-ctr[0],a.y-ctr[1],a.z-ctr[2])))+(V3.fn==='lap'?1.3:3.2);
  const fov=0.55,dist=rad/Math.sin(fov/2)/V3.zoom;const M=mat4(V3.R,ctr,dist),Pr=persp(fov,W/H,Math.max(0.1,dist-rad*3),dist+rad*3);
  const R9=new Float32Array([V3.R[0][0],V3.R[1][0],V3.R[2][0],V3.R[0][1],V3.R[1][1],V3.R[2][1],V3.R[0][2],V3.R[1][2],V3.R[2][2]]);
  gl.enable(gl.DEPTH_TEST);gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.disable(gl.CULL_FACE);
  const useLit=()=>{gl.useProgram(G.lit);gl.uniformMatrix4fv(gl.getUniformLocation(G.lit,'uM'),false,M);gl.uniformMatrix4fv(gl.getUniformLocation(G.lit,'uPr'),false,Pr);gl.uniformMatrix3fv(gl.getUniformLocation(G.lit,'uR'),false,R9)};
  const drawLit=(o,a)=>{const p=G.lit;gl.uniform1f(gl.getUniformLocation(p,'uA'),a);
    [['aP',o.p,3],['aN',o.n,3],['aC',o.c,4]].forEach(([nm,b,sz])=>{const l=gl.getAttribLocation(p,nm);gl.bindBuffer(gl.ARRAY_BUFFER,b);gl.enableVertexAttribArray(l);gl.vertexAttribPointer(l,sz,gl.FLOAT,false,0,0)});
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,o.i);gl.drawElements(gl.TRIANGLES,o.cnt,gl.UNSIGNED_INT,0)};
  const objs=V3.scene?V3.scene.objs:[];useLit();gl.depthMask(true);gl.colorMask(true,true,true,true);
  objs.filter(o=>o.kind==='opaque').forEach(o=>drawLit(o.gl,1));
  // ЭСП: только ближний слой поверхности (предварительный проход глубины); остальные поверхности -- полупрозрачные, видно и задние лепестки
  objs.filter(o=>o.kind==='trans'&&o.pre).forEach(o=>{gl.colorMask(false,false,false,false);gl.depthMask(true);drawLit(o.gl,1);
    gl.colorMask(true,true,true,true);gl.depthMask(false);gl.depthFunc(gl.LEQUAL);drawLit(o.gl,o.alpha);gl.depthFunc(gl.LESS);gl.depthMask(true)});
  gl.depthMask(false);objs.filter(o=>o.kind==='trans'&&!o.pre).forEach(o=>drawLit(o.gl,o.alpha));gl.depthMask(true);
  objs.filter(o=>o.kind==='plane').forEach(o=>{const p=G.tex;gl.useProgram(p);gl.uniformMatrix4fv(gl.getUniformLocation(p,'uM'),false,M);gl.uniformMatrix4fv(gl.getUniformLocation(p,'uPr'),false,Pr);
    gl.uniform1f(gl.getUniformLocation(p,'uA'),0.82);gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,G.texObj);gl.uniform1i(gl.getUniformLocation(p,'uS'),0);gl.depthMask(false);
    [['aP',o.gl.p,3],['aT',o.gl.t,2]].forEach(([nm,b,sz])=>{const l=gl.getAttribLocation(p,nm);gl.bindBuffer(gl.ARRAY_BUFFER,b);gl.enableVertexAttribArray(l);gl.vertexAttribPointer(l,sz,gl.FLOAT,false,0,0)});
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,o.gl.i);gl.drawElements(gl.TRIANGLES,6,gl.UNSIGNED_INT,0);gl.depthMask(true);
    const l=gl.getAttribLocation(p,'aT');gl.disableVertexAttribArray(l)});
  // подписи: проекция точки
  const proj=q=>{const x=q[0]-ctr[0],y=q[1]-ctr[1],z=q[2]-ctr[2];const v=[0,1,2].map(i=>V3.R[i][0]*x+V3.R[i][1]*y+V3.R[i][2]*z);v[2]-=dist;
    const t=1/Math.tan(fov/2);return [W/2+W/2*(t/(W/H))*v[0]/(-v[2]),H/2-H/2*t*v[1]/(-v[2]),v[2]]};
  oc.textAlign='center';oc.textBaseline='middle';
  if(V3.sh.labels&&V3.sh.atoms&&V3.fn!=='esp'&&V3.fn!=='rho'){oc.font='600 '+(12*dpr)+'px '+tok('--f-body');at.forEach(a=>{const p=proj([a.x,a.y,a.z]);oc.fillStyle=a.el==='H'?'#333':'#fff';oc.fillText(a.el,p[0],p[1])})}
  if(V3.fn==='esp'&&c.esp&&V3.sh.labels){oc.font='600 '+(12.5*dpr)+'px '+tok('--f-body');
    c.esp.ext.filter(e=>Math.abs(e.v*KJ)>=8&&(e.type==='max')===(e.v>0)&&(!e.n||(V3.R[2][0]*e.n[0]+V3.R[2][1]*e.n[1]+V3.R[2][2]*e.n[2])>0.05)).forEach(e=>{const p=proj(e.p);const txt=(e.v>0?'+':'−')+Math.abs(e.v*KJ).toFixed(0);
      oc.fillStyle=e.type==='max'?'#1d3f8a':'#8a1f14';oc.strokeStyle='rgba(255,255,255,0.9)';oc.lineWidth=3*dpr;oc.strokeText(txt,p[0],p[1]-11*dpr);oc.fillText(txt,p[0],p[1]-11*dpr);
      oc.beginPath();oc.arc(p[0],p[1],3*dpr,0,2*Math.PI);oc.fill()})}
  text3()}
function ui3(){const fn=[['none','molecule only'],['rho','ρ'],['lap','∇²ρ'],['mo','MO'],['esp','ESP on ρ = 0.001']];
  chips($('fnG'),fn,V3.fn,v=>{V3.fn=v;draw3()});
  const vr=$('valRow');vr.hidden=!['rho','lap','mo'].includes(V3.fn);$('espRow').hidden=V3.fn!=='esp';
  if(V3.fn==='rho'){$('valL').textContent='ρ, a.u.';chips($('valG'),[0.001,0.01,0.05,0.1,0.3].map(x=>[x,fmt(x,x<0.01?3:x<0.1?2:1)]),V3.val.rho,v=>{V3.val.rho=v;draw3()})}
  if(V3.fn==='lap'){$('valL').textContent='∇²ρ, a.u.';chips($('valG'),[1,2,3,5].map(x=>[x,'±'+fmt(x,0)]),V3.val.lap,v=>{V3.val.lap=v;draw3()})}
  if(V3.fn==='mo'){$('valL').textContent='Orbital (|ψ| = 0.05)';chips($('valG'),[[-2,'HOMO−2'],[-1,'HOMO−1'],[0,'HOMO'],[1,'LUMO'],[2,'LUMO+1']],V3.val.mo,v=>{V3.val.mo=v;draw3()})}
  const r=$('espR');r.value=V3.rng||100;$('espV').textContent='±'+(V3.rng||100)+' kJ/mol';
  const sb=$('shG');sb.innerHTML='';[['atoms','atoms'],['graph','molecular graph'],['plane','map plane'],['labels','labels']].forEach(([k2,h])=>{const b=document.createElement('button');b.type='button';b.className='chip';b.textContent=h;b.setAttribute('aria-pressed',V3.sh[k2]);b.onclick=()=>{V3.sh[k2]=!V3.sh[k2];draw3()};sb.appendChild(b)});
  const vb=$('vwG');vb.innerHTML='';[['tilt','tilted view'],['face','onto the map plane'],['zi','+'],['zo','−']].forEach(([k2,h])=>{const b=document.createElement('button');b.type='button';b.className='chip';b.textContent=h;
    if(k2==='zi'||k2==='zo')b.setAttribute('aria-label',k2==='zi'?'Zoom in':'Zoom out');b.onclick=()=>{if(k2==='tilt'||k2==='face')v3View(k2);else{V3.zoom*=k2==='zi'?1.2:1/1.2;draw3()}};vb.appendChild(b)})}
function nearAtom(sc,p){let best=null,bd=1e9;sc.atoms.forEach((a,i)=>{const d=Math.hypot(a.x-p[0],a.y-p[1],a.z-p[2]);if(d<bd){bd=d;best=i}});return best}
function text3(){const c=c3(),sc=c.scf;const L=$('glL'),T=$('st5');if(!sc){L.innerHTML='';T.innerHTML='';return}
  const busy=s=>'<span class="busy">'+s+'</span>';
  if(V3.fn==='esp'){L.innerHTML='<span>V &lt; 0<i class="cbar"></i>V &gt; 0</span><span>scale ±'+V3.rng+' kJ/mol (±'+fmt(V3.rng/4.184,0)+' kcal/mol)</span><span>numbers on the surface are local extrema of V, kJ/mol</span>';
    if(!c.esp){T.innerHTML=busy('Computing the electrostatic potential on the ρ = 0.001 surface…');return}
    const ex=c.esp.ext,mx=ex.filter(e=>e.type==='max').sort((a,b)=>b.v-a.v),mn=ex.filter(e=>e.type==='min').sort((a,b)=>a.v-b.v);
    const desc=e=>fmt(e.v*KJ,0)+' kJ/mol at atom '+sc.atoms[nearAtom(sc,e.p)].el;
    let t='Largest value on the surface V<sub>S,max</sub> = '+(mx.length?desc(mx[0]):'—')+', smallest V<sub>S,min</sub> = '+(mn.length?desc(mn[0]):'—')+'. ';
    t+=(ESPTXT[S.k]||'');if(S.b==='STO-3G'&&!['BF3','C6F6','C6H6'].includes(S.k))t+=' A minimal basis gives only a rough potential: compare with 6-31G*.';
    T.innerHTML=t;return}
  L.innerHTML=V3.fn==='lap'?'<span><i class="dt" style="background:#db4030"></i>∇²ρ &lt; 0: concentration</span><span><i class="dt" style="background:#386bdb"></i>∇²ρ &gt; 0: depletion</span>':V3.fn==='mo'?'<span><i class="dt" style="background:#3873d9"></i>ψ &gt; 0</span><span><i class="dt" style="background:#db5433"></i>ψ &lt; 0</span>':
    (V3.sh.graph?'<span><i class="ln" style="border-color:var(--accent);border-top-width:3px"></i>bond paths</span><span><i class="dt" style="background:var(--warn)"></i>bond CP</span>':'');
  if(V3.fn==='none'){T.innerHTML='The molecule and its molecular graph. Switch on the map plane to see where the section from Section 1 lies: '+PLDESC[S.k]+'.';return}
  if(!c.vol){T.innerHTML=busy('Computing the density on a 3D grid…');return}
  if(V3.fn==='rho')T.innerHTML='Isosurface ρ = '+fmt(V3.val.rho,V3.val.rho<0.01?3:2)+' a.u. At large values the surface breaks up into droplets around the nuclei, at small values it wraps the whole molecule; the 0.001 a.u. surface is the accepted “outer boundary” of the molecule.';
  if(V3.fn==='lap')T.innerHTML='Two isosurfaces: ∇²ρ = −'+fmt(V3.val.lap,0)+' a.u. (red, the density is concentrated inside it) and ∇²ρ = +'+fmt(V3.val.lap,0)+' a.u. (blue, the density is depleted inside it). An isosurface carries a single value of the function, and so a single colour; the sign of ∇²ρ is shown by the two surfaces. The red shells around F and O are lone pairs and bonds: these are nucleophilic centres (Lewis bases). Where a blue surface shows on the outside, not covered by red, the valence density is depleted, and a nucleophile attacks there: the C atom in F₂CO, the B atom in BF₃. The blue spheres inside the red shells are the depletion between the inner and the valence shells. In this mode the atoms are drawn smaller so as not to hide the shells.';
  if(V3.fn==='mo'){const kmo=sc.nocc-1+V3.val.mo;T.innerHTML=(kmo>=0&&kmo<sc.nmo)?'Orbital No. '+(kmo+1)+', ε = '+fmt(sc.eps[kmo]!=null?sc.eps[kmo]:NaN,3)+' a.u.'+(V3.val.mo>0?' (virtual)':' (occupied)')+'. Blue and red lobes are the two signs of ψ; the surface is |ψ| = 0.05 a.u.':'There is no such orbital in this basis.'}}
const ESPTXT={F2:'This is a σ-hole: on the extension of the F–F bond the potential is positive, while the belt around each fluorine atom is negative. The electron density of fluorine is concentrated in the belt (lone pairs) and depleted along the bond. For Cl, Br and I the σ-holes are stronger: halogen bonding rests on them.',
  CO2:'π-hole: the belt around the carbon atom is positive, the ends of the molecule (the O atoms) are negative. So CO₂ interacts with bases through carbon: this is how the addition of amines and of hydroxide to CO₂ begins.',
  BF3:'A π-hole above and below the boron atom: boron has an empty p orbital perpendicular to the plane. The lone pair of a Lewis base (ammonia, ethers) adds here.',
  F2CO:'A π-hole above and below the carbonyl carbon: the two fluorines and the oxygen withdraw density, and the carbon is open to nucleophilic attack perpendicular to the plane of the molecule.',
  C6F6:'Above the C₆F₆ ring the potential is positive (a π-hole), above C₆H₆ it is negative (compare). The fluorine atoms withdraw π density, the quadrupole moment changes sign, and C₆F₆ attracts anions while benzene attracts cations.',
  C6H6:'Above the benzene ring the potential is negative: the π cloud attracts cations (cation–π interaction). Compare with C₆F₆, where the sign is reversed.',
  H2O:'The negative regions are on the side of the oxygen lone pairs, the positive ones at the hydrogen atoms: so water acts both as a donor and as an acceptor of hydrogen bonds.',
  NH3:'The potential minimum is on the C₃ axis on the side of the nitrogen lone pair: a proton or a Lewis acid approaches here.',
  HF:'The hydrogen atom is strongly positive (a hydrogen-bond donor), the belt around fluorine is negative.',
  CO:'A negative region at carbon (the carbon lone pair): CO coordinates to metals through it.',
  N2:'Negative regions at the ends (lone pairs) and a positive belt around the middle of the bond: this is the quadrupole moment showing up.',
  LiF:'An almost ionic molecule: on the lithium side the potential is strongly positive, on the fluorine side strongly negative.',
  LiH:'An almost ionic molecule Li⁺H⁻: the potential is positive on the lithium side and negative on the side of the hydride ion.'};
$('espR').addEventListener('input',e=>{V3.rng=+e.target.value;V3.rngUser=true;draw3()});
(function(){let d=null;const w=document.querySelector('.glwrap');if(!w)return;
  w.addEventListener('pointerdown',e=>{d={x:e.clientX,y:e.clientY};w.setPointerCapture(e.pointerId);w.classList.add('drag')});
  w.addEventListener('pointermove',e=>{if(!d||!V3.R)return;const dx=e.clientX-d.x,dy=e.clientY-d.y;d={x:e.clientX,y:e.clientY};V3.R=mul3(mul3(rotY(dx*0.01),rotX(dy*0.01)),V3.R);draw3()});
  const up=()=>{d=null;w.classList.remove('drag')};w.addEventListener('pointerup',up);w.addEventListener('pointercancel',up);
  w.addEventListener('wheel',e=>{if(!e.ctrlKey&&!e.altKey)return;e.preventDefault();V3.zoom*=e.deltaY<0?1.1:1/1.1;draw3()},{passive:false});
  if(window.ResizeObserver)new ResizeObserver(()=>draw3()).observe(w)})();
const _dm=drawMap;drawMap=function(){_dm();$('mapT').innerHTML=(S.f==='rho'?'Electron density ρ':'Laplacian of the density ∇²ρ')+', '+MOLS.find(x=>x[0]===S.k)[1]+', '+S.b+'. Map plane: '+PLDESC[S.k];if(V3.scene)V3.scene.key='';draw3()};
drawMap();

// ---------- одномерные профили вдоль линии связи ----------
const PF={key:'',i:0};const liveProf=QC.live('aim.prof');
async function prof(){const c=c3(),sc=c.scf,st=$('pSt'),R1=$('pRho'),R2=$('pLap');if(!R1)return;
  if(!sc){R1.innerHTML='';R2.innerHTML='';$('pbG').innerHTML='';st.textContent='The profiles will appear when the calculation finishes.';/* the message in the empty plots too */R1.innerHTML=R2.innerHTML='<text x=\"480\" y=\"130\" text-anchor=\"middle\" font-size=\"14\" fill=\"var(--muted)\">'+st.textContent+'</text>';return}
  const k=key(S.k,S.b);const bonds=[];const seen=new Set();(sc.cps||[]).forEach(cp=>{if(cp.type!=='b'||!cp.atoms||cp.atoms.some(i=>i<0))return;const id=cp.atoms.slice().sort((a,b)=>a-b).join('-');if(seen.has(id))return;seen.add(id);bonds.push(cp)});
  if(PF.key!==k){PF.key=k;PF.i=0}
  if(!bonds.length){R1.innerHTML='';R2.innerHTML='';$('pbG').innerHTML='';st.textContent='No bond critical points were found.';/* the message in the empty plots too */R1.innerHTML=R2.innerHTML='<text x=\"480\" y=\"130\" text-anchor=\"middle\" font-size=\"14\" fill=\"var(--muted)\">'+st.textContent+'</text>';return}
  if(PF.i>=bonds.length)PF.i=0;
  const lab=b=>{let [i,j]=b.atoms;if(sc.atoms[i].Z<sc.atoms[j].Z)[i,j]=[j,i];const ni=sc.atoms.filter((a,q)=>a.el===sc.atoms[i].el).length>1,nj=sc.atoms.filter((a,q)=>a.el===sc.atoms[j].el).length>1;return bondName(sc,b.atoms)+(ni||nj?' ('+(i+1)+'–'+(j+1)+')':'')};
  chips($('pbG'),bonds.map((b,i)=>[i,lab(b)]),PF.i,v=>{PF.i=v;prof()});
  const cp=bonds[PF.i];let [ia,ib]=cp.atoms;if(sc.atoms[ia].Z<sc.atoms[ib].Z)[ia,ib]=[ib,ia];const A=sc.atoms[ia],B=sc.atoms[ib];const d=[B.x-A.x,B.y-A.y,B.z-A.z],L=Math.hypot(...d),u=d.map(x=>x/L);
  let Z;try{Z=await liveProf({k:S.k,b:S.b,ia,ib})}catch(e){return}
  const s0=-1.2,s1=L+1.2,N=420,S2=[],RHO=Z.RHO,LAP=Z.LAP;
  for(let q=0;q<=N;q++){const t=s0+(s1-s0)*q/N;S2.push(t)}
  const sb=(cp.p[0]-A.x)*u[0]+(cp.p[1]-A.y)*u[1]+(cp.p[2]-A.z)*u[2];
  const W=960,H=250,l=70,rr=20,T=14,Bm=36,X=t=>l+(t-s0)/(s1-s0)*(W-l-rr);
  const axisX=(svg)=>{for(let t=Math.ceil(s0);t<=s1;t+=1)el('text',{x:X(t),y:H-16,'text-anchor':'middle','font-size':12,fill:tok('--muted')},svg,fmt(t,0));el('text',{x:(l+W-rr)/2,y:H-1,'text-anchor':'middle','font-size':12,fill:tok('--muted')},svg,'distance from the '+A.el+' nucleus along the bond line, bohr')};
  const nuc=(svg)=>{[[0,A.el],[L,B.el]].forEach(([t,e])=>{el('line',{x1:X(t),x2:X(t),y1:T,y2:H-Bm,stroke:tok('--muted'),'stroke-dasharray':'2 3'},svg);el('text',{x:X(t)+4,y:T+12,'font-size':13,'font-weight':700,fill:tok('--ink')},svg,e)});
    el('line',{x1:X(sb),x2:X(sb),y1:T,y2:H-Bm,stroke:tok('--ok'),'stroke-dasharray':'5 4'},svg)};
  // ρ: логарифмическая шкала
  R1.innerHTML='';const lo=-3,hi=Math.ceil(Math.log10(Math.max(...RHO)));const Y=v=>T+(hi-Math.log10(Math.max(v,1e-3)))/(hi-lo)*(H-T-Bm);
  for(let k2=lo;k2<=hi;k2++){el('line',{x1:l,x2:W-rr,y1:Y(Math.pow(10,k2)),y2:Y(Math.pow(10,k2)),stroke:tok('--line')},R1);el('text',{x:l-6,y:Y(Math.pow(10,k2))+4,'text-anchor':'end','font-size':12,fill:tok('--muted')},R1,k2<0?fmt(Math.pow(10,k2),-k2):fmt(Math.pow(10,k2),0))}
  el('text',{x:16,y:T+(H-T-Bm)/2,'text-anchor':'middle','font-size':12,fill:tok('--muted'),transform:`rotate(-90 16 ${T+(H-T-Bm)/2})`},R1,'ρ, a.u.');
  nuc(R1);axisX(R1);let dP='';S2.forEach((t,q)=>dP+=(q?'L':'M')+X(t).toFixed(1)+' '+Y(RHO[q]).toFixed(1));el('path',{d:dP,fill:'none',stroke:tok('--el'),'stroke-width':2.2},R1);
  el('circle',{cx:X(sb),cy:Y(cp.rho),r:5,fill:tok('--ok')},R1);{const t=el('text',{x:X(sb)+8,y:Y(cp.rho)-8,'font-size':12.5,fill:tok('--ok')},R1,'');t.innerHTML='ρ<tspan dy="3.5" font-size="0.75em">b</tspan><tspan dy="-3.5"> = '+fmt(cp.rho,3)+'</tspan>';t.setAttribute('paint-order','stroke');t.setAttribute('stroke',tok('--panel'));t.setAttribute('stroke-width','4')}
  // ∇²ρ: шкала arsinh, чтобы видеть и ядро, и связь
  R2.innerHTML='';const f=v=>Math.asinh(v/0.1);const fm=Math.max(...LAP.map(v=>Math.abs(f(v))));const hiL=Math.min(fm,f(1e4));const Y2=v=>T+(hiL-Math.max(-hiL,Math.min(hiL,f(v))))/(2*hiL)*(H-T-Bm);
  [0,1,10,100,1000,1e4].forEach(v=>[v,-v].forEach((w,z)=>{if(z&&!v)return;if(Math.abs(f(w))>hiL)return;el('line',{x1:l,x2:W-rr,y1:Y2(w),y2:Y2(w),stroke:v===0?tok('--ink'):tok('--line')},R2);el('text',{x:l-6,y:Y2(w)+4,'text-anchor':'end','font-size':12,fill:tok('--muted')},R2,(w>0?'+':'')+fmt(w,w&&Math.abs(w)<1?1:0))}));
  el('text',{x:16,y:T+(H-T-Bm)/2,'text-anchor':'middle','font-size':12,fill:tok('--muted'),transform:`rotate(-90 16 ${T+(H-T-Bm)/2})`},R2,'∇²ρ, a.u.');
  // заливка областей концентрации
  let segs=[],cur=null;S2.forEach((t,q)=>{if(LAP[q]<0){if(!cur){cur=[];segs.push(cur)}cur.push(q)}else cur=null});
  segs.forEach(g=>{let d2='M'+X(S2[g[0]]).toFixed(1)+' '+Y2(0).toFixed(1);g.forEach(q=>d2+='L'+X(S2[q]).toFixed(1)+' '+Y2(LAP[q]).toFixed(1));d2+='L'+X(S2[g[g.length-1]]).toFixed(1)+' '+Y2(0).toFixed(1)+'Z';el('path',{d:d2,fill:tok('--nu'),opacity:.18},R2)});
  nuc(R2);axisX(R2);let dL='';S2.forEach((t,q)=>dL+=(q?'L':'M')+X(t).toFixed(1)+' '+Y2(LAP[q]).toFixed(1));el('path',{d:dL,fill:'none',stroke:tok('--nu'),'stroke-width':2.2},R2);
  el('circle',{cx:X(sb),cy:Y2(cp.lap),r:5,fill:tok('--ok')},R2);{const t=el('text',{x:X(sb)+8,y:Y2(cp.lap)-8,'font-size':12.5,fill:tok('--ok')},R2,'');t.innerHTML='∇²ρ<tspan dy="3.5" font-size="0.75em">b</tspan><tspan dy="-3.5"> = '+(cp.lap>0?'+':'')+fmt(cp.lap,3)+'</tspan>';t.setAttribute('paint-order','stroke');t.setAttribute('stroke',tok('--panel'));t.setAttribute('stroke-width','4')}
  const off=Math.hypot(cp.p[0]-(A.x+u[0]*sb),cp.p[1]-(A.y+u[1]*sb),cp.p[2]-(A.z+u[2]*sb));
  st.textContent='Bond length '+fmt(L,3)+' bohr; the critical point is '+fmt(sb,3)+' bohr from '+A.el+'. Shaded: ∇²ρ < 0, electrons are concentrated. The ∇²ρ scale is compressed (arsinh) to show hundreds of atomic units near the nucleus and tenths near the bond at the same time.'+(off>0.02?' The bond path is curved: the critical point lies '+fmt(off,2)+' bohr off the straight line.':'')}
const _render1=render;render=function(){_render1();prof().catch(e=>console.error(e))};
if(window.matchMedia)try{matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>{try{prof()}catch(e){}})}catch(e){}
