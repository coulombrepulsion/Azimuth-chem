/* Crystal-field page (Atlas v2).  The angular-overlap levels, ground-state
   filling, spin crossover, Jahn-Teller curve and quiz configurations come from
   quas_atlas.core.crystal_field (cf.state, cf.cx); this script draws. */
// ---------- страница «Кристаллическое поле и поле лигандов»: модель углового перекрывания ----------
const NS='http://www.w3.org/2000/svg',$=id=>document.getElementById(id);
function el(tag,a,p,t){const e=document.createElementNS(NS,tag);for(const k in a)e.setAttribute(k,a[k]);if(t!=null)e.textContent=t;if(p)p.appendChild(e);return e}
const tok=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const fmt=(x,d=1)=>{if(!isFinite(x))return '—';if(Math.abs(x)<0.5*Math.pow(10,-d))x=0;return x.toFixed(d).replace('-','−')};
const n0=x=>String(Math.round(x)).replace(/\B(?=(\d{3})+(?!\d))/g,' ').replace('-','−');
const SUP=s=>String(s).replace(/\d/g,c=>'⁰¹²³⁴⁵⁶⁷⁸⁹'[c]);
const DORB=[{id:'z2',h:'d<sub>z²</sub>'},{id:'x2y2',h:'d<sub>x²−y²</sub>'},
  {id:'xy',h:'d<sub>xy</sub>'},{id:'xz',h:'d<sub>xz</sub>'},{id:'yz',h:'d<sub>yz</sub>'}];
const GEO={
 oct:{nm:'octahedron',grp:'O<sub>h</sub>',lab:{z2:'e<sub>g</sub>',x2y2:'e<sub>g</sub>',xy:'t<sub>2g</sub>',xz:'t<sub>2g</sub>',yz:'t<sub>2g</sub>'},
   lab2:{z2:'a<sub>1g</sub>',x2y2:'b<sub>1g</sub>',xy:'b<sub>2g</sub>',xz:'e<sub>g</sub>',yz:'e<sub>g</sub>'},grp2:'D<sub>4h</sub>'},
 tet:{nm:'tetrahedron',grp:'T<sub>d</sub>',lab:{z2:'e',x2y2:'e',xy:'t<sub>2</sub>',xz:'t<sub>2</sub>',yz:'t<sub>2</sub>'}},
 sq:{nm:'square planar',grp:'D<sub>4h</sub>',lab:{z2:'a<sub>1g</sub>',x2y2:'b<sub>1g</sub>',xy:'b<sub>2g</sub>',xz:'e<sub>g</sub>',yz:'e<sub>g</sub>'}},
 spy:{nm:'square pyramid',grp:'C<sub>4v</sub>',lab:{z2:'a<sub>1</sub>',x2y2:'b<sub>1</sub>',xy:'b<sub>2</sub>',xz:'e',yz:'e'}},
 tbp:{nm:'trigonal bipyramid',grp:'D<sub>3h</sub>',lab:{z2:'a<sub>1</sub>′',x2y2:'e′',xy:'e′',xz:'e″',yz:'e″'}},
 lin:{nm:'linear',grp:'D<sub>∞h</sub>',lab:{z2:'σ<sub>g</sub><sup>+</sup>',x2y2:'δ<sub>g</sub>',xy:'δ<sub>g</sub>',xz:'π<sub>g</sub>',yz:'π<sub>g</sub>'}}};
const LIGN=['I⁻','Br⁻','Cl⁻','F⁻','H₂O','NH₃','en','CN⁻','CO'];
const IONS={1:'Ti³⁺',2:'V³⁺',3:'Cr³⁺',4:'Mn³⁺, Cr²⁺',5:'Fe³⁺, Mn²⁺',6:'Fe²⁺, Co³⁺',7:'Co²⁺',8:'Ni²⁺',9:'Cu²⁺',10:'Zn²⁺'};
let geo='oct',tAx=1,lig=4,nd=6,P=20000;
function label(g,orb,t){const G=GEO[g];if(g==='oct'&&Math.abs(t-1)>0.005)return G.lab2[DORB[orb].id];return G.lab[DORB[orb].id]}
const grpName=()=>geo==='oct'&&Math.abs(tAx-1)>0.005?(tAx===0?'D<sub>4h</sub>':'D<sub>4h</sub>'):GEO[geo].grp;
// ---------- рисование ----------
function drawGeo(){const sv=$('geo');sv.innerHTML='';const c=75,R=52,yaw=0.5,pit=0.35;const pr=v=>{const x=v[0]*Math.cos(yaw)-v[1]*Math.sin(yaw),y=v[0]*Math.sin(yaw)+v[1]*Math.cos(yaw);const z2=y*Math.sin(pit)+v[2]*Math.cos(pit),d=y*Math.cos(pit)-v[2]*Math.sin(pit);return [c+R*x,c-R*z2,d]};
  const Ls=cur.L.map(L=>{const f=L[3]==='ax'&&geo==='oct'?tAx:1;if(f===0)return null;const s=geo==='oct'&&L[3]==='ax'?Math.pow(f,-0.2):1;return [L[0]*s,L[1]*s,L[2]*s]}).filter(Boolean);
  const P0=pr([0,0,0]);const all=Ls.map(v=>pr(v)).sort((a,b)=>b[2]-a[2]);
  all.forEach(p=>{if(p[2]>0){el('line',{x1:P0[0],y1:P0[1],x2:p[0],y2:p[1],stroke:tok('--muted'),'stroke-width':3},sv);el('circle',{cx:p[0],cy:p[1],r:9,fill:tok('--ok'),stroke:tok('--ink'),'stroke-width':1},sv)}});
  el('circle',{cx:P0[0],cy:P0[1],r:13,fill:tok('--accent'),stroke:tok('--ink'),'stroke-width':1},sv);el('text',{x:P0[0],y:P0[1]+4,'text-anchor':'middle','font-size':11,fill:tok('--accent-ink')},sv,'M');
  all.forEach(p=>{if(p[2]<=0){el('line',{x1:P0[0],y1:P0[1],x2:p[0],y2:p[1],stroke:tok('--muted'),'stroke-width':3},sv);el('circle',{cx:p[0],cy:p[1],r:9,fill:tok('--ok'),stroke:tok('--ink'),'stroke-width':1},sv)}});
  $('geoT').innerHTML=GEO[geo].nm+', point group '+grpName()+(geo==='oct'&&tAx!==1?(tAx<1?' (axial ligands moved away: elongated octahedron'+(tAx===0?', limit — square planar':'')+')':' (axial ligands moved closer: compressed octahedron)'):'')+'. Ligand: '+LIGN[lig]+'.'}
function arrowsAt(sv,x,y,o){const up=cx=>el('path',{d:`M${cx},${y+9} L${cx},${y-9} M${cx-4},${y-4} L${cx},${y-10} L${cx+4},${y-4}`,stroke:tok('--ink'),'stroke-width':1.8,fill:'none'},sv),dn=cx=>el('path',{d:`M${cx},${y-9} L${cx},${y+9} M${cx-4},${y+4} L${cx},${y+10} L${cx+4},${y+4}`,stroke:tok('--ink'),'stroke-width':1.8,fill:'none'},sv);
  if(o>=1)up(x-(o===2?5:0));if(o===2)dn(x+5)}
let cur=null;
const liveS=QC.live('cf.state');
async function update(){let Z;try{Z=await liveS({geo,t:tAx,lig,nd,P})}catch(e){return}const lv=Z.lv,f=Z.f,Do=Z.Do;cur=Z;
  // диаграмма
  const sv=$('dia');sv.innerHTML='';const W=460,H=380,T=24,B=24;const emax=Math.max(...lv.map(l=>Math.abs(l.E)),3000)*1.15;const sy=e=>T+(H-T-B)*(emax-e)/(2*emax);
  el('line',{x1:30,y1:sy(0),x2:120,y2:sy(0),stroke:tok('--ink'),'stroke-width':2},sv);el('text',{x:75,y:sy(0)-10,'text-anchor':'middle','font-size':11.5,fill:tok('--muted')},sv,'free ion');el('text',{x:75,y:sy(0)+18,'text-anchor':'middle','font-size':11.5,fill:tok('--muted')},sv,'5 × d');
  // группы вырожденных уровней
  const groups=Z.groups;
  groups.forEach(g=>{const y=sy(lv[g[0]].E),w=34,gap=8,tw=g.length*w+(g.length-1)*gap,x0=250-tw/2;
    el('line',{x1:120,y1:sy(0),x2:x0-6,y2:y,stroke:tok('--muted'),'stroke-dasharray':'3 3'},sv);
    g.forEach((i,k)=>{const x=x0+k*(w+gap);el('line',{x1:x,y1:y,x2:x+w,y2:y,stroke:tok('--ink'),'stroke-width':2.2},sv);arrowsAt(sv,x+w/2,y,f.occ[i])});
    el('text',{x:x0+tw+10,y:y+4,'font-size':12.5,fill:tok('--ink')},sv).innerHTML=label(geo,lv[g[0]].orb,tAx).replace(/<sub>/g,'<tspan baseline-shift="sub" font-size="9">').replace(/<sup>/g,'<tspan baseline-shift="super" font-size="9">').replace(/<\/su[bp]>/g,'</tspan>');
    el('text',{x:x0+tw+52,y:y+4,'font-size':11,fill:tok('--muted')},sv,(lv[g[0]].E>=0?'+':'')+n0(lv[g[0]].E)+' cm⁻¹')});
  el('text',{x:W-6,y:H-6,'text-anchor':'end','font-size':11,fill:tok('--muted')},sv,'0 — barycenter of the d levels');
  // таблица уровней
  $('lvTab').innerHTML='<table class="mtab"><thead><tr><th class="l">level</th><th class="l">orbitals</th><th>E, cm⁻¹</th><th>e⁻</th></tr></thead><tbody>'+
    groups.slice().reverse().map(g=>'<tr><td class="l">'+label(geo,lv[g[0]].orb,tAx)+'</td><td class="l">'+g.map(i=>DORB[lv[i].orb].h).join(', ')+'</td><td>'+(lv[g[0]].E>=0?'+':'')+n0(lv[g[0]].E)+'</td><td>'+g.reduce((s,i)=>s+f.occ[i],0)+'</td></tr>').join('')+'</tbody></table>';
  const mu=Z.mu;const lfse=f.E;const isOh=geo==='oct'&&tAx===1;
  $('sumTab').innerHTML='<table class="mtab"><tbody>'+
    '<tr><td class="l">configuration</td><td>d'+SUP(nd)+' ('+IONS[nd]+')'+(isOh?': t<sub>2g</sub>'+SUP(Z.t2gN)+'e<sub>g</sub>'+SUP(Z.egN):'')+'</td></tr>'+
    '<tr><td class="l">Δ<sub>o</sub> for this ligand (octahedron)</td><td>'+n0(Do)+' cm⁻¹</td></tr>'+
    '<tr><td class="l">unpaired electrons</td><td>'+f.unp+' → '+(f.unp?'paramagnetic':'diamagnetic')+', μ<sub>s</sub> = √(n(n + 2)) = '+fmt(mu,2)+' μ<sub>B</sub></td></tr>'+
    '<tr><td class="l">CFSE (without pairing energy)</td><td>'+n0(lfse)+' cm⁻¹ = '+fmt(Z.lfseKJ,0)+' kJ/mol'+(isOh?' = '+fmt(Z.lfseDo,1)+' Δ<sub>o</sub>':'')+'</td></tr>'+
    '<tr><td class="l">electron pairs in the d levels</td><td>'+f.pairs+'</td></tr></tbody></table>';
  let s='';if(geo==='oct'&&tAx===1)s='Octahedron: the e<sub>g</sub> orbitals (d<sub>z²</sub>, d<sub>x²−y²</sub>) point straight at the ligands and rise by +0.6Δ<sub>o</sub>, while t<sub>2g</sub> drop by −0.4Δ<sub>o</sub>. Here Δ<sub>o</sub> = 3e<sub>σ</sub> − 4e<sub>π</sub>: π-donor ligands (halides) reduce Δ<sub>o</sub>, π-acceptor ligands (CN⁻, CO) increase it. This is the origin of the spectrochemical series.';
  else if(geo==='tet')s='Tetrahedron: the order of levels is reversed — t<sub>2</sub> above, e below, and the splitting is Δ<sub>t</sub> = '+n0(Z.Dt)+' cm⁻¹ ≈ '+fmt(Z.DtRatio,2)+'Δ<sub>o</sub> (theory gives '+'<span class=fr><span>4</span><span>9</span></span>'+'). Since Δ<sub>t</sub> is small, tetrahedral complexes are almost always high spin.';
  else if(geo==='sq'||(geo==='oct'&&tAx===0))s='Square planar: d<sub>x²−y²</sub> rises very high. For d⁸ (Ni²⁺, Pd²⁺, Pt²⁺) all eight electrons sit in the four lower orbitals and the complex is diamagnetic — which is why d⁸ with strong ligands prefers the square planar geometry.';
  else if(geo==='oct')s='A tetragonal distortion lowers the symmetry O<sub>h</sub> → D<sub>4h</sub>: e<sub>g</sub> splits into a<sub>1g</sub> (d<sub>z²</sub>) and b<sub>1g</sub> (d<sub>x²−y²</sub>), t<sub>2g</sub> into e<sub>g</sub> (d<sub>xz</sub>, d<sub>yz</sub>) and b<sub>2g</sub> (d<sub>xy</sub>). On elongation along z the orbitals with a z component end up lower.';
  else s='The level labels are the irreducible representations of the group '+GEO[geo].grp+', by which the d orbitals transform.';
  $('st1').innerHTML=s;drawGeo();hsPlot();jtPlot();
  $('ppV').textContent='P = '+n0(P)+' cm⁻¹';$('tetV').textContent=tAx===1?'none (O<sub>h</sub>)'.replace(/<[^>]+>/g,''):'axial × '+fmt(tAx,2);$('tet').value=tAx;$('pp').value=P;
  [...$('gG').children].forEach(b=>b.setAttribute('aria-pressed',b.dataset.g===geo));[...$('lG').children].forEach((b,k)=>b.setAttribute('aria-pressed',k===lig));[...$('dG').children].forEach((b,k)=>b.setAttribute('aria-pressed',k+1===nd));
  $('tRow').hidden=geo!=='oct'}
function hsPlot(){const sv=$('hsSvg');sv.innerHTML='';const W=520,H=300,L=64,R=14,T=16,B=34,pw=W-L-R,ph=H-T-B,Dmax=40000;const D=cur.Do;
  if(!cur.hs){$('st2').innerHTML='For d'+SUP(nd)+' there is only one configuration in an octahedron at any Δ<sub>o</sub>: high- and low-spin states differ only for d⁴–d⁷. Choose d⁴, d⁵, d⁶ or d⁷.';
    el('text',{x:W/2,y:H/2,'text-anchor':'middle','font-size':14,fill:tok('--muted')},sv,'only d⁴–d⁷ have a choice of spin');return}
  const [hs,ls]=cur.hs.cfg;const f=(c,Dv)=>cur.hs.E[c===hs?0:1][cur.hs.pts.indexOf(Dv)];const ys=[0,Dmax].flatMap(Dv=>[f(hs,Dv),f(ls,Dv)]);const lo=Math.min(...ys),hi=Math.max(...ys);
  const sx=Dv=>L+Dv/Dmax*pw,sy=E=>T+ph*(hi-E)/(hi-lo);el('rect',{x:L,y:T,width:pw,height:ph,fill:'none',stroke:tok('--line')},sv);
  for(let Dv=0;Dv<=Dmax;Dv+=10000)el('text',{x:sx(Dv),y:H-16,'text-anchor':'middle','font-size':11,fill:tok('--muted')},sv,n0(Dv));
  el('text',{x:L+pw,y:H-2,'text-anchor':'end','font-size':11.5,fill:tok('--muted')},sv,'Δo, cm⁻¹');el('text',{x:4,y:T-4,'font-size':11.5,fill:tok('--muted')},sv,'E(d), cm⁻¹');
  [[hs,'--warn','high spin'],[ls,'--accent','low spin']].forEach(([c,col,t],k)=>{el('line',{x1:sx(0),y1:sy(f(c,0)),x2:sx(Dmax),y2:sy(f(c,Dmax)),stroke:tok(col),'stroke-width':2.4},sv);
    el('text',{x:sx(1500),y:sy(f(c,1500))-8,'font-size':12,fill:tok(col)},sv,t+': t₂g'+SUP(c[0])+'eg'+SUP(c[1]))});
  el('line',{x1:sx(P),y1:T,x2:sx(P),y2:T+ph,stroke:tok('--muted'),'stroke-dasharray':'5 4'},sv);el('text',{x:sx(P)+4,y:T+14,'font-size':11.5,fill:tok('--muted')},sv,'Δo = P');
  if(D<=Dmax){el('line',{x1:sx(D),y1:T,x2:sx(D),y2:T+ph,stroke:tok('--ok'),'stroke-width':2.4},sv);el('text',{x:sx(D)+4,y:T+ph-6,'font-size':11.5,fill:tok('--ok')},sv,LIGN[lig])}
  const isLS=cur.hs.isLS;
  $('st2').innerHTML='d'+SUP(nd)+', ligand '+LIGN[lig]+': Δ<sub>o</sub> = '+n0(D)+' cm⁻¹ '+(D>P?'&gt;':'&lt;')+' P = '+n0(P)+' cm⁻¹ → <b>'+(isLS?'low-spin':'high-spin')+'</b> complex. The lines cross exactly at Δ<sub>o</sub> = P: going to low spin gains Δ<sub>o</sub> for every electron moved from e<sub>g</sub> to t<sub>2g</sub> and costs P for every new pair. Move P or change the ligand — this is how spin crossover is explained.'}
// Ян–Теллер: энергия электронов + упругая энергия как функция искажения
function jtPlot(){const sv=$('jtSvg');sv.innerHTML='';const W=520,H=300,L=64,R=14,T=16,B=34,pw=W-L-R,ph=H-T-B;const D=cur.Do,J=cur.jt;
  const dl=J.dl,E=J.E;
  const lo=Math.min(...E),hi=Math.max(...E.slice(0,1),...E.slice(-1));const sx=d=>L+(d+0.2)/0.4*pw,sy=e=>T+ph*(hi-e)/((hi-lo)||1);
  el('rect',{x:L,y:T,width:pw,height:ph,fill:'none',stroke:tok('--line')},sv);
  [-0.2,-0.1,0,0.1,0.2].forEach(d=>el('text',{x:sx(d),y:H-16,'text-anchor':'middle','font-size':11,fill:tok('--muted')},sv,'δ = '+fmt(d,1)));
  el('text',{x:L,y:H-2,'font-size':11,fill:tok('--muted')},sv,'← compression');el('text',{x:L+pw,y:H-2,'text-anchor':'end','font-size':11,fill:tok('--muted')},sv,'elongation →');el('text',{x:4,y:T-4,'font-size':11.5,fill:tok('--muted')},sv,'ΔE, cm⁻¹');
  el('line',{x1:sx(0),y1:T,x2:sx(0),y2:T+ph,stroke:tok('--line'),'stroke-dasharray':'3 3'},sv);
  el('path',{d:dl.map((d,i)=>(i?'L':'M')+sx(d).toFixed(1)+','+sy(E[i]).toFixed(1)).join(' '),fill:'none',stroke:tok('--accent'),'stroke-width':2.4},sv);
  const im=J.im;el('circle',{cx:sx(dl[im]),cy:sy(E[im]),r:5,fill:tok('--warn')},sv);
  const t2=J.t2,eg=J.eg,strong=J.strong,weak=J.weak;
  $('st3').innerHTML='d'+SUP(nd)+' in an octahedron: t<sub>2g</sub>'+SUP(t2)+'e<sub>g</sub>'+SUP(eg)+'. '+(strong?'<b>Strong Jahn–Teller effect</b>: e<sub>g</sub> holds an odd number of electrons, and the energy minimum is shifted away from the regular octahedron (dot). For example, in [Cu(H₂O)₆]²⁺ the four equatorial bonds are shorter than the two axial ones.':weak?'Weak effect: the degenerate t<sub>2g</sub> level is unevenly occupied, but the t<sub>2g</sub> orbitals do not point at the ligands, so the gain is small.':'The ground state is nondegenerate: distortion does not pay off, and the minimum is at the regular octahedron.')+
    ' Curve: the d-electron energy under tetragonal distortion (axial ligands weakened by 2δ, equatorial ones strengthened by δ, so the average field is unchanged) plus an elastic energy growing as δ². In this simple model elongation and compression are equivalent; experimentally elongation is almost always observed.'}
// ---------- корреляционная таблица ----------
function corr(){const keys=['oct','tet','sq','spy','tbp','lin'];
  $('corTab').innerHTML='<table class="mtab"><thead><tr><th class="l">orbital</th>'+keys.map(k=>'<th class="l">'+GEO[k].nm+', '+GEO[k].grp+'</th>').join('')+'<th class="l">elongated octahedron, D<sub>4h</sub></th></tr></thead><tbody>'+
    DORB.map(d=>'<tr><td class="l">'+d.h+'</td>'+keys.map(k=>'<td class="l">'+GEO[k].lab[d.id]+'</td>').join('')+'<td class="l">'+GEO.oct.lab2[d.id]+'</td></tr>').join('')+'</tbody></table>'}
// ---------- тренажёр ----------
let CX=[];
let qz=null;
function newQ(){let k;do{k=Math.floor(Math.random()*CX.length)}while(qz&&k===qz.k);const {name:nm,n,ls,c}=CX[k];qz={k,n,ls,c};
  $('qCx').innerHTML=nm+' <span class="hint" style="font-family:var(--f-body);font-size:14px">('+(n>=4&&n<=7?(ls?'low-spin':'high-spin'):'octahedron')+')</span>';for(let q=0;q<3;q++){$('q'+q).value='';$('q'+q).className=''}$('qRes').textContent='Enter your answers and press “Check”.'}
const num=s=>{s=String(s).trim().replace(',','.').replace('−','-');return s===''?NaN:+s};
$('qNew').onclick=newQ;
// «Проверьте себя» с выбором ответа (assets/js/try.*.js, initSelf): правильные ответы для вариантов
window.qcSelf=()=>[String(qz.n),String(qz.c.unp),fmt(qz.c.lfse,1)];
$('qChk').onclick=()=>{const ok=[num($('q0').value)===qz.n,num($('q1').value)===qz.c.unp,Math.abs(num($('q2').value)-qz.c.lfse)<0.05];ok.forEach((g,q)=>$('q'+q).className=$('q'+q).value.trim()===''?'':g?'ok':'bad');
  $('qRes').innerHTML=ok.every(Boolean)?'<b>Correct!</b>':'Not quite yet. Find the oxidation state of the metal and the number of d electrons, place them in t<sub>2g</sub> and e<sub>g</sub>; CFSE = (−0.4n<sub>t2g</sub> + 0.6n<sub>eg</sub>)Δ<sub>o</sub>.'};
$('qShow').onclick=()=>{const c=qz.c;$('q0').value=qz.n;$('q1').value=c.unp;$('q2').value=fmt(c.lfse,1);for(let q=0;q<3;q++)$('q'+q).className='ok';
  $('qRes').innerHTML=CX[qz.k].name+': d'+SUP(qz.n)+' → t<sub>2g</sub>'+SUP(c.t)+'e<sub>g</sub>'+SUP(c.e)+', unpaired '+c.unp+'; CFSE = −0.4 · '+c.t+' + 0,6 · '+c.e+' = '+fmt(c.lfse,1)+'Δ<sub>o</sub>.'};
// ---------- управление ----------
Object.entries(GEO).forEach(([k,g])=>{const b=document.createElement('button');b.type='button';b.className='chip';b.dataset.g=k;b.textContent=g.nm;b.onclick=()=>{geo=k;if(k!=='oct')tAx=1;update()};$('gG').appendChild(b)});
LIGN.forEach((n,i)=>{const b=document.createElement('button');b.type='button';b.className='chip';b.textContent=n;b.onclick=()=>{lig=i;update()};$('lG').appendChild(b)});
for(let k=1;k<=10;k++){const b=document.createElement('button');b.type='button';b.className='chip';b.innerHTML='d'+SUP(k);b.title=IONS[k];b.onclick=()=>{nd=k;update()};$('dG').appendChild(b)}
$('tet').oninput=e=>{tAx=+e.target.value;if(Math.abs(tAx-1)<0.015)tAx=1;update()};$('pp').oninput=e=>{P=+e.target.value;update()};
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',update);
corr();update();(async()=>{try{CX=await QC.api('cf.cx',{})}catch(e){return}newQ()})();
