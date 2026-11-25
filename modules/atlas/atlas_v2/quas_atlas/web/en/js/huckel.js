/* Hueckel page (Atlas v2).  The secular problem, occupations, charges, bond orders,
   free valence, delocalisation energy, reactivity sites and the characteristic
   polynomial come from quas_atlas.core.huckel (endpoint huckel.solve); this
   script keeps the presets and the drawing. */
// Метод Хюккеля: π-система из атомов с параметрами h (α_X = α + hβ) и k (β_CX = kβ)
const HT={
 C :{lab:'C',h:0,  k:1,  z:1,name:'C'},
 N1:{lab:'N',h:0.5,k:1,  z:1,name:'pyridine-type N (1 π electron)'},
 N2:{lab:'N',h:1.5,k:0.8,z:2,name:'pyrrole-type N (2 π electrons)'},
 O1:{lab:'O',h:1.0,k:1,  z:1,name:'carbonyl-type O (1 π electron)'},
 O2:{lab:'O',h:2.0,k:0.8,z:2,name:'furan-type O (2 π electrons)'}};
const TYPE_CYCLE=['C','N1','N2','O1','O2'];
// ---------- интерфейс страницы «Метод Хюккеля» ----------
const NS='http://www.w3.org/2000/svg',$=id=>document.getElementById(id);
function el(tag,attrs,parent,text){const e=document.createElementNS(NS,tag);for(const k in attrs)e.setAttribute(k,attrs[k]);if(text!=null)e.textContent=text;if(parent)parent.appendChild(e);return e}
const fmt=(x,d=3)=>{if(x==null||isNaN(x))return '—';if(Math.abs(x)<0.5*Math.pow(10,-d))x=0;return x.toFixed(d).replace('-','−')};
const sgn=(x,d=3)=>(x>0.5*Math.pow(10,-d)?'+':'')+fmt(x,d);
function eLab(x){if(Math.abs(x)<5e-4)return 'α';const a=Math.abs(x),ia=Math.round(a);return 'α '+(x>0?'+ ':'− ')+(Math.abs(a-1)<5e-4?'':Math.abs(a-ia)<5e-4?String(ia):fmt(a))+'β'}
const S3=Math.sqrt(3);
// ---------- геометрия (y вверх, длина связи 1) ----------
function zig(n){return [...Array(n)].map((_,i)=>[i*S3/2,(i%2)*0.5])}
function poly(n,a0){const R=1/(2*Math.sin(Math.PI/n));return [...Array(n)].map((_,i)=>{const a=a0-2*Math.PI*i/n;return [R*Math.cos(a),R*Math.sin(a)]})}
function mk(pos,types,bonds,labels){return {atoms:pos.map((p,i)=>({x:p[0],y:p[1],t:(types&&types[i])||'C',lab:labels?labels[i]:String(i+1)})),bonds}}
function chainMol(n,types,labels){return mk(zig(n),types,[...Array(n-1)].map((_,i)=>[i,i+1]),labels)}
function ringMol(n,types,a0=Math.PI/2,labels){const m=mk(poly(n,a0),types,[...Array(n-1)].map((_,i)=>[i,i+1]),labels);m.bonds.push([n-1,0]);return m}
function naphthalene(){const h=S3/2;return mk([[h,1],[2*h,0.5],[2*h,-0.5],[h,-1],[0,-0.5],[-h,-1],[-2*h,-0.5],[-2*h,0.5],[-h,1],[0,0.5]],null,
  [[0,1],[1,2],[2,3],[3,4],[4,5],[5,6],[6,7],[7,8],[8,9],[9,0],[4,9]],['1','2','3','4','4a','5','6','7','8','8a'])}
function azulene(){const a5=1/(2*Math.tan(Math.PI/5)),R5=1/(2*Math.sin(Math.PI/5)),a7=1/(2*Math.tan(Math.PI/7)),R7=1/(2*Math.sin(Math.PI/7)),d=Math.PI/180;
  const P5=[36,108,180,252,324].map(t=>[-a5+R5*Math.cos(t*d),R5*Math.sin(t*d)]);
  const t0=Math.atan2(-0.5,-a7),P7=[1,2,3,4,5].map(k=>{const t=t0+k*2*Math.PI/7;return [a7+R7*Math.cos(t),R7*Math.sin(t)]});
  return mk([P5[0],P5[1],P5[2],P5[3],P5[4],...P7],null,[[0,1],[1,2],[2,3],[3,4],[4,5],[5,6],[6,7],[7,8],[8,9],[9,0],[0,4]],['8a','1','2','3','3a','4','5','6','7','8'])}
function fulvene(){const R5=1/(2*Math.sin(Math.PI/5)),m=ringMol(5,null,0);m.atoms.push({x:R5+1,y:0,t:'C',lab:'6'});m.bonds.push([0,5]);return m}
function benzyl(){const m=ringMol(6,null,Math.PI/2);m.atoms.push({x:0,y:2,t:'C',lab:'7'});m.bonds.push([0,6]);return m}
function tmm(){return mk([[0,0],[0,1],[-S3/2,-0.5],[S3/2,-0.5]],null,[[0,1],[0,2],[0,3]])}
const PRESETS=[
 {k:'eth',g:'chain',name:'Ethylene',f:()=>chainMol(2),ch:0},
 {k:'allyl',g:'chain',name:'Allyl',f:()=>chainMol(3),ch:0},
 {k:'buta',g:'chain',name:'Butadiene',f:()=>chainMol(4),ch:0},
 {k:'hexa',g:'chain',name:'Hexatriene',f:()=>chainMol(6),ch:0},
 {k:'c3',g:'ring',name:'Cyclopropenyl',f:()=>ringMol(3),ch:1},
 {k:'c4',g:'ring',name:'Cyclobutadiene',f:()=>ringMol(4,null,Math.PI/4),ch:0},
 {k:'c5',g:'ring',name:'Cyclopentadienyl',f:()=>ringMol(5),ch:-1},
 {k:'bz',g:'ring',name:'Benzene',f:()=>ringMol(6),ch:0},
 {k:'c7',g:'ring',name:'Tropylium',f:()=>ringMol(7),ch:1},
 {k:'c8',g:'ring',name:'Cyclooctatetraene',f:()=>ringMol(8,null,Math.PI/2+Math.PI/8),ch:0},
 {k:'naph',g:'fused',name:'Naphthalene',f:naphthalene,ch:0},
 {k:'azu',g:'fused',name:'Azulene',f:azulene,ch:0},
 {k:'fulv',g:'fused',name:'Fulvene',f:fulvene,ch:0},
 {k:'benzyl',g:'fused',name:'Benzyl',f:benzyl,ch:0},
 {k:'tmm',g:'fused',name:'Trimethylenemethane',f:tmm,ch:0},
 {k:'h2co',g:'het',name:'Formaldehyde',f:()=>chainMol(2,['O1','C'],['O','1']),ch:0},
 {k:'acro',g:'het',name:'Acrolein',f:()=>chainMol(4,['O1','C','C','C'],['O','1','2','3']),ch:0},
 {k:'pyr',g:'het',name:'Pyridine',f:()=>ringMol(6,['N1']),ch:0},
 {k:'pyrl',g:'het',name:'Pyrrole',f:()=>ringMol(5,['N2'],-Math.PI/2),ch:0},
 {k:'fur',g:'het',name:'Furan',f:()=>ringMol(5,['O2'],-Math.PI/2),ch:0}];
// ---------- состояние ----------
let mol=null,R=null,cur=0,view='mo',crit='fo',tab='coef',custom={ring:false,n:6};
function load(p){mol=p.f();mol.charge=p.ch;mol.name=p.name;mol.key=p.k;cur=-1;update()}
function loadCustom(){mol=custom.ring?ringMol(custom.n,null,custom.n===4?Math.PI/4:Math.PI/2):chainMol(custom.n);mol.charge=0;mol.name=(custom.ring?'Ring C':'Chain C')+custom.n;mol.key='custom';cur=-1;update()}
const liveH=QC.live('huckel.solve');
async function update(){let Z;const asked=mol;try{Z=await liveH({types:mol.atoms.map(a=>a.t),bonds:mol.bonds,charge:mol.charge})}catch(e){return}if(mol!==asked)return;/* another molecule was chosen meanwhile */R=Z;if(cur<0||cur>=R.n)cur=R.homo>=0?R.shells[R.homo].mo[R.shells[R.homo].mo.length-1]:0;
  document.querySelectorAll('[data-k]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.k===mol.key));
  $('bChain').setAttribute('aria-pressed',mol.key==='custom'&&!custom.ring);$('bRing').setAttribute('aria-pressed',mol.key==='custom'&&custom.ring);
  drawCharge();drawMol();drawLevels();drawSum();drawTab()}
// ---------- заряд ----------
function drawCharge(){const g=$('chg');g.innerHTML='';const z=mol.atoms.reduce((s,a)=>s+HT[a.t].z,0);
  [-2,-1,0,1,2].forEach(c=>{const b=document.createElement('button');b.className='chip';b.type='button';b.textContent=c>0?'+'+c:c<0?'−'+(-c):'0';
    const ne=z-c;b.disabled=ne<0||ne>2*mol.atoms.length;b.setAttribute('aria-pressed',mol.charge===c);b.onclick=()=>{mol.charge=c;update()};g.appendChild(b)});
  const ne=z-mol.charge;$('neTxt').textContent=ne+' π electron'+(ne%10===1&&ne!==11?'':(ne%10>=2&&ne%10<=4&&(ne<10||ne>20))?'s':'s')+(mol.charge>0?' — cation':mol.charge<0?' — anion':'')+(R.unpaired===1?(mol.charge?', radical':' (radical)'):R.unpaired===2?(mol.charge?', a biradical in Hückel theory':' (a biradical in Hückel theory)'):R.unpaired>2?', unpaired: '+R.unpaired:'')}
// ---------- молекула ----------
function dl(r){const a=mol.atoms[r];return a.t==='C'?a.lab:HT[a.t].lab+(a.lab===HT[a.t].lab?'':a.lab)}
function layout(W,H,pad,padY){if(padY==null)padY=pad;const xs=mol.atoms.map(a=>a.x),ys=mol.atoms.map(a=>a.y);const x0=Math.min(...xs),x1=Math.max(...xs),y0=Math.min(...ys),y1=Math.max(...ys);
  const s=Math.min((W-2*pad)/Math.max(x1-x0,1e-6),(H-2*padY)/Math.max(y1-y0,1e-6),78);const cx=(x0+x1)/2,cy=(y0+y1)/2;
  return mol.atoms.map(a=>[W/2+(a.x-cx)*s,H/2-(a.y-cy)*s])}
function outward(P,r){const nb=mol.bonds.filter(b=>b.includes(r)).map(b=>b[0]===r?b[1]:b[0]);let dx=0,dy=0;
  nb.forEach(j=>{dx+=P[r][0]-P[j][0];dy+=P[r][1]-P[j][1]});let L=Math.hypot(dx,dy);
  if(L<1e-3){if(nb.length===1){const j=nb[0];dx=-(P[j][1]-P[r][1]);dy=P[j][0]-P[r][0];L=Math.hypot(dx,dy)}else{dx=0;dy=-1;L=1}}return [dx/L,dy/L]}
/* between the choice of a molecule and its result (the calculation takes seconds in a browser) there is nothing to
   draw yet — a click on «МО» in that time read R.mos[-1] and stopped the page; update() draws when it has R */
function drawMol(){if(!R||cur<0||cur>=R.n||R.n!==mol.atoms.length)return;const svg=$('mol');svg.innerHTML='';const W=480,H=340;const P=layout(W,H,view==='mo'?62:view==='diag'?112:80,view==='diag'?92:null);const m=R.mos[cur];
  const gB=el('g',{},svg),gL=el('g',{},svg),gA=el('g',{},svg),gT=el('g',{},svg);
  mol.bonds.forEach(([i,j],b)=>{el('line',{x1:P[i][0],y1:P[i][1],x2:P[j][0],y2:P[j][1],stroke:'var(--ink)','stroke-width':view==='diag'?1.5+2.5*Math.max(0,R.bo[b]):2.4,'stroke-linecap':'round',opacity:view==='diag'?0.75:1},gB);
    if(view==='mo'&&m.c[i]*m.c[j]<-1e-8){// узел между атомами
      const t=Math.abs(m.c[i])/(Math.abs(m.c[i])+Math.abs(m.c[j]));const mx=P[i][0]+(P[j][0]-P[i][0])*t,my=P[i][1]+(P[j][1]-P[i][1])*t;
      const L=Math.hypot(P[j][0]-P[i][0],P[j][1]-P[i][1]),nx=-(P[j][1]-P[i][1])/L,ny=(P[j][0]-P[i][0])/L;
      el('line',{x1:mx-nx*16,y1:my-ny*16,x2:mx+nx*16,y2:my+ny*16,stroke:'var(--muted)','stroke-width':1.6,'stroke-dasharray':'3 3'},gT)}
    if(view==='diag'){const mx=(P[i][0]+P[j][0])/2,my=(P[i][1]+P[j][1])/2,L=Math.hypot(P[j][0]-P[i][0],P[j][1]-P[i][1]);let nx=-(P[j][1]-P[i][1])/L,ny=(P[j][0]-P[i][0])/L;
      // подпись снаружи от центра молекулы
      const cx=P.reduce((s,p)=>s+p[0],0)/P.length,cy=P.reduce((s,p)=>s+p[1],0)/P.length;if((mx-cx)*nx+(my-cy)*ny<0){nx=-nx;ny=-ny}
      const tx=mx+nx*13,ty=my+ny*13+4;const t=el('text',{x:tx,y:ty,'text-anchor':'middle','font-size':12.5,fill:'var(--ink)','font-family':'var(--f-mono)'},gT,fmt(R.bo[b]));
      t.setAttribute('paint-order','stroke');t.setAttribute('stroke','var(--panel)');t.setAttribute('stroke-width','4')}});
  if(view==='mo'){mol.atoms.forEach((a,r)=>{const c=m.c[r];if(Math.abs(c)<1e-3)return;el('circle',{cx:P[r][0],cy:P[r][1],r:8+46*Math.abs(c),fill:c>0?'var(--lp-bg)':'var(--ln-bg)',stroke:c>0?'var(--lp)':'var(--ln)','stroke-width':1.6},gL)})}
  if(view==='react'){const X=R.react[crit];if(X){const val=crit==='q'?R.q:null;
      X.cand.forEach(r=>{});
      const marks=[['E',X.E,'var(--el)','E⁺'],['N',X.N,'var(--nu)','Nu⁻'],['R',X.R,'var(--ra)','R·']];
      const used={};marks.forEach(([key,set,col,txt])=>set.forEach(r=>{const k=used[r]||0;used[r]=k+1;const [dx,dy]=outward(P,r);
        const bx=P[r][0]+dx*(30+k*24),by=P[r][1]+dy*(30+k*24);
        el('rect',{x:bx-16,y:by-10,width:32,height:20,rx:10,fill:col},gT);el('text',{x:bx,y:by+4.5,'text-anchor':'middle',class:'badge',fill:'var(--panel)'},gT,txt)}));
      mol.atoms.forEach((a,r)=>{if(!X.cand.includes(r))el('circle',{cx:P[r][0],cy:P[r][1],r:15,fill:'none',stroke:'var(--muted)','stroke-dasharray':'2 3','stroke-width':1.2},gL)})}}
  mol.atoms.forEach((a,r)=>{const g=el('g',{class:'atom',tabindex:0,role:'button','aria-label':'Atom '+a.lab+': '+HT[a.t].name+'. Click to change the type'},gA);
    const het=a.t!=='C';el('circle',{class:'core',cx:P[r][0],cy:P[r][1],r:het?13:11,fill:'var(--atom)',stroke:het?'var(--el)':'var(--ink)','stroke-width':het?2:1.5},g);
    el('text',{x:P[r][0],y:P[r][1]+(het?5:4),'text-anchor':'middle','font-size':het?15:11.5,'font-weight':het?600:400,fill:het?'var(--el)':'var(--muted)'},g,het?HT[a.t].lab:a.lab);
    if(HT[a.t].z===2){const [dx,dy]=outward(P,r);const bx=P[r][0]+dx*19,by=P[r][1]+dy*19;el('circle',{cx:bx-dy*3.5,cy:by+dx*3.5,r:2,fill:'var(--el)'},g);el('circle',{cx:bx+dy*3.5,cy:by-dx*3.5,r:2,fill:'var(--el)'},g)}
    const act=async()=>{a.t=TYPE_CYCLE[(TYPE_CYCLE.indexOf(a.t)+1)%TYPE_CYCLE.length];if(!mol.edited){mol.name+=' (modified)';mol.edited=true}mol.key='edit';
      const z=mol.atoms.reduce((s,x)=>s+HT[x.t].z,0);if(z-mol.charge>2*mol.atoms.length||z-mol.charge<0)mol.charge=0;cur=-1;await update();const nx=$('mol').querySelectorAll('.atom')[r];if(nx&&document.activeElement!==nx&&ev.kb)nx.focus()};
    let ev={kb:false};g.addEventListener('click',()=>{ev.kb=false;act()});g.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();ev.kb=true;act()}})});
  if(view==='diag'){mol.atoms.forEach((a,r)=>{const [dx,dy]=outward(P,r);const q=R.q[r];
      const dq=24+16*Math.abs(dx);const t=el('text',{x:P[r][0]+dx*dq,y:P[r][1]+dy*dq+4.5,'text-anchor':'middle','font-size':13,'font-weight':600,'font-family':'var(--f-mono)',fill:q>5e-4?'var(--warn)':q<-5e-4?'var(--accent)':'var(--muted)'},gT,sgn(q));
      t.setAttribute('paint-order','stroke');t.setAttribute('stroke','var(--panel)');t.setAttribute('stroke-width','4');
      if(R.F[r]!=null&&R.F[r]>0.02&&R.deg[r]<3){const L0=dq+20+12*Math.abs(dx),L1=L0+40*R.F[r];const x0=P[r][0]+dx*L0,y0=P[r][1]+dy*L0,x1=P[r][0]+dx*L1,y1=P[r][1]+dy*L1;
        el('line',{x1:x0,y1:y0,x2:x1,y2:y1,stroke:'var(--ra)','stroke-width':2},gT);
        el('path',{d:`M${x1},${y1} l${-dx*7-dy*4},${-dy*7+dx*4} l${dy*8},${-dx*8} z`,fill:'var(--ra)'},gT);
        const hz=Math.abs(dx)>0.8;const lt=el('text',{x:hz?x1-dx*8:x1+dx*13,y:hz?y1-11:y1+dy*13+4,'text-anchor':'middle','font-size':11.5,fill:'var(--ra)','font-family':'var(--f-mono)'},gT,fmt(R.F[r]));lt.setAttribute('paint-order','stroke');lt.setAttribute('stroke','var(--panel)');lt.setAttribute('stroke-width','3')}})}
  // легенда и пояснение
  const leg=$('molLeg'),tx=$('molTxt');
  document.querySelectorAll('[data-v]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.v===view));
  if(view==='mo'){leg.innerHTML='<span><i class="box" style="background:var(--lp-bg);border:1.5px solid var(--lp)"></i>c &gt; 0</span><span><i class="box" style="background:var(--ln-bg);border:1.5px solid var(--ln)"></i>c &lt; 0</span><span>size ∝ |c|</span><span><i class="sw" style="border-color:var(--muted);border-top-style:dashed"></i>node between atoms</span><span>top view of the p orbitals</span>';
    const nodes=mol.bonds.filter(([i,j])=>m.c[i]*m.c[j]<-1e-8).length,zero=mol.atoms.map((_,r)=>r).filter(r=>Math.abs(m.c[r])<1e-3).map(dl);
    const sh=R.shells[m.shell],kind=m.x>1e-4?'bonding':m.x<-1e-4?'antibonding':'nonbonding';
    tx.innerHTML=`<b>MO ${cur+1}</b>: E = ${eLab(m.x)}, ${kind}${sh.mo.length>1?`, degenerate (${sh.mo.length}-fold)`:''}; electrons in it: ${fmt(m.occ,m.occ%1?2:0)}. Sign changes along bonds: ${nodes}`+(zero.length?`; on atom${zero.length>1?'s':''} ${zero.join(', ')} the coefficient is zero — the node passes through the atom`:'')+'.'+(sh.mo.length>1?' For a degenerate level any combination of the orbitals is also a solution; the charges and bond orders do not depend on this choice.':'')}
  else if(view==='diag'){leg.innerHTML='<span><b style="color:var(--warn)">+q</b> — deficit of π electrons</span><span><b style="color:var(--accent)">−q</b> — excess</span><span>on bonds — π bond order p</span><span><i class="sw" style="border-color:var(--ra)"></i>free valence index F (for nodal atoms — in the table)</span>';
    tx.innerHTML='Molecular diagram: π charge q<sub>r</sub> = z<sub>r</sub> − Σn<sub>i</sub>c<sub>ri</sub>², bond order p<sub>rs</sub> = Σn<sub>i</sub>c<sub>ri</sub>c<sub>si</sub>, free valence index F<sub>r</sub> = √3 − Σp<sub>rs</sub> (C only). Bond thickness is proportional to p.'+(R.allC&&R.q.every(x=>Math.abs(x)<5e-4)?' All charges are zero: this is a general property of neutral alternant hydrocarbons (the Coulson–Rushbrooke theorem).':'')}
  else{const X=R.react[crit];leg.innerHTML=`<span>Criterion for ionic attack:</span><button class="chip" type="button" data-c="fo" aria-pressed="${crit==='fo'}">frontier orbitals</button><button class="chip" type="button" data-c="q" aria-pressed="${crit==='q'}">π charges</button>`;
    leg.querySelectorAll('[data-c]').forEach(b=>b.onclick=()=>{crit=b.dataset.c;drawMol()});
    if(!X){tx.textContent='No carbon atoms bearing hydrogen — nothing to substitute.';return}
    const L=s=>s.map(dl).join(', ');const v=(arr,s)=>arr?fmt(arr[s[0]]):'—';
    let h=`<b style="color:var(--el)">Electrophile (E⁺)</b> → ${L(X.E)}: ${crit==='q'?'most negative charge, q = '+sgn(R.q[X.E[0]]):'largest HOMO density, c² = '+v(R.fH,X.E)}. `+
      `<b style="color:var(--nu)">Nucleophile (Nu⁻)</b> → ${L(X.N)}: ${crit==='q'?'most positive charge, q = '+sgn(R.q[X.N[0]]):'largest LUMO density, c² = '+v(R.fL,X.N)}. `+
      `<b style="color:var(--ra)">Radical (R·)</b> → ${L(X.R)}: largest free valence index, F = ${fmt(R.F[X.R[0]])}.`;
    if(crit==='q'&&!X.polar)h+=' <br>The charges on all C atoms are practically the same, so the charge criterion cannot distinguish the positions — the orbital criterion is needed.';
    if(X.cand.length<mol.atoms.length)h+=' <br>Dashed circles mark atoms that do not take part in substitution: heteroatoms and bridgehead C atoms without hydrogen.';
    tx.innerHTML=h}}
// ---------- уровни ----------
function drawLevels(){const svg=$('lev');svg.innerHTML='';const W=540,top=24;
  const xs=R.mos.map(m=>m.x),lo=Math.min(-2.2,Math.min(...xs)-0.3),hi=Math.max(2.2,Math.max(...xs)+0.3);  const frost=R.ring&&R.allC;let u=392/(hi-lo);if(frost)u=Math.min(u,66);const bot=frost?34:24,H=Math.round((hi-lo)*u+top+bot),Y=x=>top+(x-lo)*u;// x больше → ниже (β<0)
  const fcx=2*u+40,xc=frost?fcx+2*u+80:220;const Wv=W;
  svg.setAttribute('viewBox',`0 0 ${Wv} ${H}`);
  // ось α
  el('line',{x1:frost?40:60,y1:Y(0),x2:Wv-10,y2:Y(0),stroke:'var(--muted)','stroke-dasharray':'4 4','stroke-width':1},svg);
  el('text',{x:frost?36:56,y:Y(0)+4,'text-anchor':'end','font-size':13,fill:'var(--muted)'},svg,'α');
  // шкала слева
  const ax=frost?20:40;el('line',{x1:ax,y1:top,x2:ax,y2:H-bot,stroke:'var(--line)','stroke-width':1},svg);
  for(let k=Math.ceil(lo);k<=Math.floor(hi);k++){if(k===0)continue;el('line',{x1:ax-4,y1:Y(k),x2:ax+4,y2:Y(k),stroke:'var(--muted)','stroke-width':1},svg);
    if(!frost)el('text',{x:ax-7,y:Y(k)+4,'text-anchor':'end','font-size':11.5,fill:'var(--muted)'},svg,(k>0?'+':'−')+(Math.abs(k)===1?'':Math.abs(k))+'β')}
  el('text',{x:ax+6,y:top-8,'font-size':11.5,fill:'var(--muted)'},svg,'higher energy ↑');
  if(frost){const n=R.n,cx=fcx,Rp=2*u;el('circle',{cx,cy:Y(0),r:Rp,fill:'none',stroke:'var(--line)','stroke-width':1.5},svg);
    const pts=[...Array(n)].map((_,k)=>[cx+Rp*Math.sin(2*Math.PI*k/n),Y(0)+Rp*Math.cos(2*Math.PI*k/n)]);
    el('polygon',{points:pts.map(p=>p.join(',')).join(' '),fill:'none',stroke:'var(--accent)','stroke-width':1.8},svg);
    pts.forEach(p=>{el('circle',{cx:p[0],cy:p[1],r:3.5,fill:'var(--accent)'},svg);el('line',{x1:p[0]+5,y1:p[1],x2:xc-75,y2:p[1],stroke:'var(--line)','stroke-dasharray':'2 3','stroke-width':1},svg)});
    el('text',{x:cx,y:H-6,'text-anchor':'middle','font-size':11.5,fill:'var(--muted)'},svg,'Frost circle: radius 2|β|')}
  // уровни
  const lw=40,gap=10,labs=[];
  R.shells.forEach((sh,s)=>{const g=sh.mo.length,y=Y(sh.x),w=g*lw+(g-1)*gap;let left=sh.ne;
    // распределение по правилу Хунда для отображения
    const occ=sh.mo.map(()=>0);for(let p=0;p<2&&left>0;p++)for(let i=0;i<g&&left>0;i++){occ[i]++;left--}
    sh.mo.forEach((mi,i)=>{const x0=xc-w/2+i*(lw+gap);const sel=mi===cur;const gg=el('g',{class:'lvl',role:'button',tabindex:0,'aria-label':`MO ${mi+1}, E = ${eLab(sh.x)}`},svg);
      el('rect',{x:x0-3,y:y-14,width:lw+6,height:28,fill:sel?'var(--acc-bg)':'transparent',rx:4},gg);
      el('line',{class:'l',x1:x0,y1:y,x2:x0+lw,y2:y,stroke:sel?'var(--accent)':'var(--ink)','stroke-width':sel?3.5:2.2},gg);
      const arrow=(x,up)=>{const y0=up?y+9:y-9,y1=up?y-9:y+9;el('line',{x1:x,y1:y0,x2:x,y2:y1,stroke:'var(--ink)','stroke-width':1.6},gg);el('path',{d:`M${x-3.5},${y1+(up?5:-5)} L${x},${y1} L${x+3.5},${y1+(up?5:-5)}`,fill:'none',stroke:'var(--ink)','stroke-width':1.6},gg)};
      if(occ[i]>=1)arrow(x0+lw/2-(occ[i]===2?6:0),true);if(occ[i]===2)arrow(x0+lw/2+6,false);
      const pick=()=>{cur=mi;if(view!=='mo')view='mo';drawMol();drawLevels();drawTab()};gg.addEventListener('click',pick);gg.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();pick()}})});
    labs.push({y,t:eLab(sh.x),x:xc+w/2+12,s});
    const tag=s===R.homo&&s===R.lumo?'SOMO':s===R.homo?'HOMO':s===R.lumo?'LUMO':'';if(tag)el('text',{x:xc-w/2-10,y:y+4,'text-anchor':'end','font-size':11.5,fill:'var(--accent)','font-weight':600},svg,tag)});
  // подписи энергий без наложений
  labs.sort((a,b)=>a.y-b.y);for(let i=1;i<labs.length;i++)if(labs[i].y-labs[i-1].y<14)labs[i].ly=(labs[i-1].ly||labs[i-1].y)+14;
  labs.forEach(l=>{const ly=Math.max(l.ly||l.y,(l.ly||l.y));el('text',{x:Math.max(...labs.map(q=>q.x)),y:ly+4,'font-size':12.5,fill:'var(--ink)','font-family':'var(--f-mono)'},svg,l.t)});
  const m=R.mos[cur];$('moName').textContent='MO '+(cur+1)+' of '+R.n;$('moPrev').disabled=cur===0;$('moNext').disabled=cur===R.n-1;
  $('toH').disabled=R.homo<0;$('toL').disabled=R.lumo<0}
// ---------- сводка ----------
function drawSum(){const s=$('sum'),n=R.n,ne=R.ne;let h='';
  h+=`<span>π electrons</span><b>${ne}</b>`;
  h+=`<span>E<sub>π</sub> = Σn<sub>i</sub>E<sub>i</sub></span><b>${ne}α ${R.B>=0?'+':'−'} ${fmt(Math.abs(R.B))}β</b>`;
  if(R.allC)h+=`<span>Delocalization energy</span><b>${fmt(R.DE)}β <span class="note" style="font-family:var(--f-body)">relative to ${R.m} isolated C=C ${R.m===1?'bond':'bonds'}${ne-2*R.m>0?` and ${ne-2*R.m} e at level α`:''}</span></b>`;
  else h+=`<span>Delocalization energy</span><b class="note" style="font-family:var(--f-body)">not computed for heterosystems: there is no unique localized reference structure</b>`;
  if(R.homo>=0&&R.lumo>=0&&R.homo!==R.lumo)h+=`<span>HOMO–LUMO gap</span><b>${fmt(R.shells[R.homo].x-R.shells[R.lumo].x)}|β|</b>`;
  if(R.unpaired)h+=`<span>Unpaired electrons</span><b>${R.unpaired} <span class="note" style="font-family:var(--f-body)">${R.homo===R.lumo?'level only partly filled':''}</span></b>`;
  if(R.ring&&R.allC){const v=ne%2?'odd number of electrons — radical':ne%4===2?`${ne} = 4n + 2: closed shell, aromatic system`:`${ne} = 4n: degenerate pair half filled — antiaromatic system`+(n===8&&ne===8?' (real cyclooctatetraene escapes this by becoming nonplanar)':'');h+=`<span>Hückel rule</span><b style="font-family:var(--f-body);font-weight:500">${v}</b>`}
  s.innerHTML=h}
// ---------- таблицы ----------
function polyStr(c){const n=c.length-1,sup=k=>String(k).split('').map(d=>'⁰¹²³⁴⁵⁶⁷⁸⁹'[d]).join('');let s='';
  c.forEach((v,i)=>{const p=n-i;if(Math.abs(v)<5e-4)return;const a=Math.abs(v);const num=(Math.abs(a-1)<5e-4&&p>0)?'':(Math.abs(a-Math.round(a))<5e-4?String(Math.round(a)):fmt(a));
    s+=(s?(v>0?' + ':' − '):(v<0?'−':''))+num+(p>0?'x'+(p>1?sup(p):''):'')});return s+' = 0'}
function drawTab(){document.querySelectorAll('[data-t]').forEach(b=>b.setAttribute('aria-selected',b.dataset.t===tab));const p=$('tpane'),n=R.n,labs=mol.atoms.map((_,r)=>dl(r));
  if(tab==='coef'){let h='<div class="tablewrap"><table class="mtab"><thead><tr><th>MO</th><th>E</th><th>n</th>'+labs.map(l=>`<th>c<sub>${l}</sub></th>`).join('')+'</tr></thead><tbody>';
    R.mos.forEach((m,i)=>{h+=`<tr class="pick${i===cur?' cur':''}" data-mo="${i}"><td class="n">${i+1}</td><td>${eLab(m.x)}</td><td>${fmt(m.occ,m.occ%1?2:0)}</td>`+m.c.map(c=>`<td>${fmt(c)}</td>`).join('')+'</tr>'});
    h+='</tbody></table></div><p class="hint">Rows are normalized: Σc² = 1. Click a row to show the orbital on the molecule. The overall sign of an MO is arbitrary (ψ and −ψ are the same orbital).</p>';p.innerHTML=h;
    p.querySelectorAll('[data-mo]').forEach(r=>r.onclick=()=>{cur=+r.dataset.mo;view='mo';drawMol();drawLevels();drawTab()})}
  else if(tab==='det'){let h='<p class="small">Secular equation after dividing by β and substituting x = <span class=fr><span>α − E</span><span>β</span></span>, i.e., E = α − xβ. On the diagonal — x + h of the atom; off the diagonal — k for neighbors and 0 for nonbonded atoms.</p><div class="tablewrap"><table class="mtab det" style="width:auto"><thead><tr><th></th>'+labs.map(l=>`<th>${l}</th>`).join('')+'</tr></thead><tbody>';
    for(let i=0;i<n;i++){h+=`<tr><td class="n">${labs[i]}</td>`;for(let j=0;j<n;j++){const v=R.A[i][j];let t;if(i===j)t=Math.abs(v)<1e-9?'x':'x + '+fmt(v,1);else t=Math.abs(v)<1e-9?'<span style="color:var(--muted)">0</span>':(Math.abs(v-1)<1e-9?'1':fmt(v,1));h+=`<td>${t}</td>`}h+='</tr>'}
    h+='</tbody></table></div>';
    const roots=R.mos.map(m=>-m.x);h+=n<=10?`<p class="small">Expanded determinant: <span class="val">${polyStr(R.poly)}</span></p>`:'';
    h+=`<p class="small">Roots: ${roots.map(x=>'x = '+fmt(x)).join('; ')}. Each root corresponds to a level E = α − xβ, that is, ${R.mos.map(m=>eLab(m.x)).join(', ')}.</p>`;p.innerHTML=h}
  else{let h='<div class="tablewrap"><table class="mtab"><thead><tr><th>Atom</th><th>type</th><th>z</th><th>π density P<sub>rr</sub></th><th>charge q</th><th>F</th><th>c² HOMO</th><th>c² LUMO</th></tr></thead><tbody>';
    mol.atoms.forEach((a,r)=>{h+=`<tr><td class="n">${labs[r]}</td><td class="n">${a.t==='C'?'C':HT[a.t].name.replace(/ \(.*/,'')}</td><td>${HT[a.t].z}</td><td>${fmt(R.P[r][r])}</td><td>${sgn(R.q[r])}</td><td>${fmt(R.F[r])}</td><td>${R.fH?fmt(R.fH[r]):'—'}</td><td>${R.fL?fmt(R.fL[r]):'—'}</td></tr>`});
    h+='</tbody></table></div><div class="tablewrap"><table class="mtab"><thead><tr><th>Bond</th><th>π bond order p</th><th>total order 1 + p</th><th>C–C length ≈ 1.517 − 0.18p, Å</th></tr></thead><tbody>';
    mol.bonds.forEach(([i,j],b)=>{const cc=mol.atoms[i].t==='C'&&mol.atoms[j].t==='C';h+=`<tr><td class="n">${labs[i]}–${labs[j]}</td><td>${fmt(R.bo[b])}</td><td>${fmt(1+R.bo[b])}</td><td>${cc?fmt(1.517-0.18*R.bo[b]):'—'}</td></tr>`});
    h+='</tbody></table></div><p class="hint">z is the number of π electrons the atom contributes to the system; q = z − P<sub>rr</sub>. For degenerate HOMOs/LUMOs the density is averaged over all orbitals of the level. The bond length is Coulson’s empirical relation, calibrated on ethylene (1.337 Å) and benzene (1.397 Å).</p>';p.innerHTML=h}}
// ---------- инициализация ----------
['chain','ring','fused','het'].forEach(g=>{const box=document.querySelector(`[data-g="${g}"]`);PRESETS.filter(p=>p.g===g).forEach(p=>{const b=document.createElement('button');b.className='chip';b.type='button';b.dataset.k=p.k;b.textContent=p.name;b.onclick=()=>load(p);box.appendChild(b)})});
const nAt=$('nAt');nAt.value=custom.n;$('nAtV').textContent=custom.n+' atoms';
nAt.oninput=()=>{custom.n=+nAt.value;if(custom.ring&&custom.n<3){custom.n=3;nAt.value=3}$('nAtV').textContent=custom.n+' atoms'+(custom.n<5?'s':'s');loadCustom()};
$('bChain').onclick=()=>{custom.ring=false;nAt.min=2;loadCustom()};$('bRing').onclick=()=>{custom.ring=true;nAt.min=3;if(custom.n<3){custom.n=3;nAt.value=3}loadCustom()};
document.querySelectorAll('[data-v]').forEach(b=>b.onclick=()=>{view=b.dataset.v;drawMol()});
document.querySelectorAll('[data-t]').forEach(b=>b.onclick=()=>{tab=b.dataset.t;drawTab()});
$('moPrev').onclick=()=>{if(cur>0){cur--;view='mo';drawMol();drawLevels();drawTab()}};$('moNext').onclick=()=>{if(cur<R.n-1){cur++;view='mo';drawMol();drawLevels();drawTab()}};
$('toH').onclick=()=>{if(R.homo>=0){cur=R.shells[R.homo].mo[0];view='mo';drawMol();drawLevels();drawTab()}};
$('toL').onclick=()=>{if(R.lumo>=0){cur=R.shells[R.lumo].mo[0];view='mo';drawMol();drawLevels();drawTab()}};
$('parTab').innerHTML='<table class="mtab"><thead><tr><th>Atom</th><th>h</th><th>k</th><th>π electrons</th><th>example</th></tr></thead><tbody>'+
 [['C',0,1,1,'all hydrocarbons'],['N1',0.5,1,1,'pyridine, imines'],['N2',1.5,0.8,2,'pyrrole, aniline'],['O1',1,1,1,'carbonyl: formaldehyde, acrolein'],['O2',2,0.8,2,'furan, phenol']].map(r=>`<tr><td class="n">${HT[r[0]].name}</td><td>${fmt(r[1],1)}</td><td>${fmt(r[2],1)}</td><td>${r[3]}</td><td class="n">${r[4]}</td></tr>`).join('')+'</tbody></table>';
load(PRESETS.find(p=>p.k==='buta'));
