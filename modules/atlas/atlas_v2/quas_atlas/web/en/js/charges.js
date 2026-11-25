/* Atomic charges page (Atlas v2).  The RHF data, atom labels, point-charge and
   density dipoles and the experimental values come from quas_atlas.core.charges
   (charges.meta, charges.view, charges.series); this script draws. */
// ---------- страница «Атомные заряды: сравнение схем» (данные RHF посчитаны заранее той же программой, что на странице Бейдера) ----------
const NS='http://www.w3.org/2000/svg',$=id=>document.getElementById(id);
function el(tag,a,p,t){const e=document.createElementNS(NS,tag);for(const k in a)e.setAttribute(k,a[k]);if(t!=null)e.textContent=t;if(p)p.appendChild(e);return e}
const fmt=(x,d=2)=>{if(x==null||!isFinite(x))return '—';if(Math.abs(x)<0.5*Math.pow(10,-d))x=0;return x.toFixed(d).replace('-','−')};
const sg=(x,d=2)=>(x>0.5*Math.pow(10,-d)?'+':'')+fmt(x,d);
const tok=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
let B=null,M=null;
const SCH=[['mul','Mulliken','--nu'],['low','Löwdin','--ok'],['bad','Bader','--el']];
const Q={m:0,b:3,a:0};
const sub=s=>s.replace(/\d/g,c=>'₀₁₂₃₄₅₆₇₈₉'[c]);
function chips(box,labels,cur,on){box.innerHTML='';labels.forEach((t,i)=>{const b=document.createElement('button');b.type='button';b.className='chip';b.innerHTML=t;b.setAttribute('aria-pressed',i===cur);b.onclick=()=>on(i);box.appendChild(b)})}
function mark(box,i){[...box.children].forEach((b,j)=>b.setAttribute('aria-pressed',j===i))}
const liveV=QC.live('charges.view'),liveS=QC.live('charges.series');
async function init(){try{M=await QC.api('charges.meta',{})}catch(e){return}B=M.B;
  chips($('molG'),M.mols.map(m=>m.n),Q.m,i=>{Q.m=i;Q.a=0;mark($('molG'),i);draw()});
  chips($('basG'),B,Q.b,i=>{Q.b=i;mark($('basG'),i);draw()});
  draw()}
async function draw(){const m=M.mols[Q.m],b=B[Q.b];let r;try{r=await liveV({m:Q.m,b})}catch(e){return}const L=m.L;
  $('info').innerHTML=m.n+', RHF/'+b+': basis functions '+r.nbf+', E = '+fmt(r.E,6)+' E<sub>h</sub>.';
  $('tab').innerHTML='<table class="mtab"><thead><tr><th>atom</th>'+SCH.map(s=>'<th>'+s[1]+'</th>').join('')+'</tr></thead><tbody>'+L.map((l,i)=>'<tr><td>'+l+'</td>'+SCH.map(([k])=>'<td>'+(r.q[k]?sg(r.q[k][i]):'—')+'</td>').join('')+'</tr>').join('')+'</tbody></table>';
  bars(m,r.q,L);
  const notes=[];if(!r.q.bad)notes.push('Bader charges for HF in STO-3G are not shown: in this basis the program found no basin of its own for hydrogen.');
  if(m.id==='LiH'&&b==='STO-3G')notes.push('In STO-3G the Mulliken scheme gives lithium a negative charge — contrary to common sense: lithium gives an electron to hydrogen. This is a classic example of an artifact of the scheme.');
  if(m.id==='CH4')notes.push('Even the sign of the carbon charge in methane depends on the scheme: negative by Mulliken and Löwdin, positive by Bader.');
  if(B[Q.b]==='6-31G**'&&!m.hasH)notes.push('There is no hydrogen in the molecule, so 6-31G** is the same as 6-31G*: the “second star” adds p functions only on H.');
  $('note').textContent=notes.join(' ');
  chips($('atG'),m.uniq.map(i=>L[i]),Q.a,i=>{Q.a=i;mark($('atG'),i);chart()});chart();dip(r,m)}
function bars(m,r,L){const svg=$('bars');svg.innerHTML='';const W=960,H=260,lft=60,rt=16,top=14,bot=34;let mx=0;SCH.forEach(([k])=>r[k]&&r[k].forEach(v=>mx=Math.max(mx,Math.abs(v))));mx=Math.max(0.5,Math.ceil(mx*4)/4);
  const Y=v=>top+(mx-v)/(2*mx)*(H-top-bot),n=L.length,gw=(W-lft-rt)/n,bw=Math.min(36,gw/4);
  for(let v=-mx;v<=mx+1e-9;v+=mx/2){el('line',{x1:lft,x2:W-rt,y1:Y(v),y2:Y(v),stroke:Math.abs(v)<1e-9?tok('--muted'):tok('--line')},svg);el('text',{x:lft-6,y:Y(v)+4,'text-anchor':'end','font-size':12,fill:tok('--muted')},svg,sg(v,2))}
  L.forEach((l,i)=>{const x0=lft+gw*i+gw/2;SCH.forEach(([k,,c],j)=>{if(!r[k])return;const v=r[k][i],x=x0+(j-1)*(bw+4)-bw/2;el('rect',{x,y:Math.min(Y(v),Y(0)),width:bw,height:Math.abs(Y(v)-Y(0)),fill:tok(c),rx:2},svg)});
    el('text',{x:x0,y:H-10,'text-anchor':'middle','font-size':13,fill:tok('--ink')},svg,l)});
  $('leg').innerHTML=SCH.map(([,n,c])=>'<span><span class="box" style="background:'+tok(c)+'"></span>'+n+'</span>').join('')}
async function chart(){const m=M.mols[Q.m],i=m.uniq[Q.a];let vals;try{vals=await liveS({m:Q.m,i})}catch(e){return}const svg=$('chart');svg.innerHTML='';const W=960,H=300,lft=60,rt=120,top=16,bot=36;
  let lo=0,hi=0;vals.flat().forEach(v=>{if(v!=null){lo=Math.min(lo,v);hi=Math.max(hi,v)}});const pad=Math.max(0.1,(hi-lo)*0.1);lo-=pad;hi+=pad;
  const X=j=>lft+j*(W-lft-rt)/3,Y=v=>top+(hi-v)/(hi-lo)*(H-top-bot);const step=(hi-lo)>2?0.5:(hi-lo)>0.8?0.25:0.1;
  for(let v=Math.ceil(lo/step)*step;v<=hi;v+=step){el('line',{x1:lft,x2:W-rt,y1:Y(v),y2:Y(v),stroke:Math.abs(v)<1e-9?tok('--muted'):tok('--line')},svg);el('text',{x:lft-6,y:Y(v)+4,'text-anchor':'end','font-size':12,fill:tok('--muted')},svg,sg(v,2))}
  B.forEach((b,j)=>el('text',{x:X(j),y:H-12,'text-anchor':'middle','font-size':13,fill:tok('--ink')},svg,b));
  SCH.forEach(([k,n,c],s)=>{const pts=vals[s].map((v,j)=>v==null?null:[X(j),Y(v)]);let d='';pts.forEach((p,j)=>{if(!p)return;d+=(d&&pts[j-1]?'L':'M')+p[0].toFixed(1)+' '+p[1].toFixed(1)});el('path',{d,fill:'none',stroke:tok(c),'stroke-width':2.4},svg);
    pts.forEach((p,j)=>{if(p)el('circle',{cx:p[0],cy:p[1],r:j===Q.b?6:4,fill:tok(c)},svg)});const last=pts.filter(Boolean).pop();if(last)el('text',{x:W-rt+10,y:last[1]+4,'font-size':13,fill:tok(c)},svg,n)})}
function dip(r,m){const mu=r.mu;
  const rows=SCH.map(([k,n])=>{const v=r.dip[k];if(!v)return '<tr><td>'+n+'</td><td>—</td><td>—</td></tr>';const mq=v.mq;return '<tr><td>'+n+'</td><td>'+fmt(mq,2)+'</td><td>'+(v.dir?(v.dir>0?'same':'opposite'):'—')+'</td></tr>'}).join('');
  $('dip').innerHTML='<table class="mtab"><thead><tr><th>source</th><th>|μ|, D</th><th>direction</th></tr></thead><tbody><tr><td><b>calculation from the full density</b></td><td><b>'+fmt(mu,2)+'</b></td><td>—</td></tr>'+rows+'<tr><td>experiment</td><td>'+fmt(r.exp,2)+'</td><td>—</td></tr></tbody></table>';
  $('dipNote').textContent=m.id==='CO'?'CO is a hard case: in experiment the negative end of the dipole is on carbon, while Hartree–Fock in extended basis sets gives the opposite direction; the correct sign is obtained only with correlation. Bader charges (C⁺, O⁻) represent the density distribution but not the dipole moment, which also includes the polarization of the atomic basins.':(m.id==='CH4'||m.id==='CO2')?'The dipole moment is zero by symmetry for any charges; the electrostatics of such molecules is described by the quadrupole moment.':'Bader point charges usually overestimate the dipole moment: the atomic basins are also polarized, and this contribution opposes the charge transfer. Charges fitted to the electrostatic potential reproduce it best — that is what they were designed for.'}
init();matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>{if(M)draw()});
