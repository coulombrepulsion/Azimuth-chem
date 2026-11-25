/* Atomic units page (Atlas v2).  CODATA factors, the converter, the energy
   estimate (T + V versus r) and the energy scale come from quas_atlas.core.units
   (au.constants, au.convert, au.estimate, au.scale); this script formats
   and draws (axis scaling uses the factors received from the server). */
// ---------- страница «Атомные единицы» (CODATA 2018) ----------
const NS='http://www.w3.org/2000/svg',$=id=>document.getElementById(id);
function el(tag,a,p,t){const e=document.createElementNS(NS,tag);for(const k in a)e.setAttribute(k,a[k]);if(t!=null)e.textContent=t;if(p)p.appendChild(e);return e}
const fmt=(x,d=3)=>{if(x==null||!isFinite(x))return '—';if(Math.abs(x)<0.5*Math.pow(10,-d))x=0;return x.toFixed(d).replace('-','−')};
const SUP=s=>String(s).split('').map(c=>c==='-'?'⁻':'⁰¹²³⁴⁵⁶⁷⁸⁹'[+c]).join('');
function num(x,p=7){if(x===0)return '0';const a=Math.abs(x);if(a>=1e-3&&a<1e7){let t=x.toPrecision(p);if(t.includes('e'))t=(+t).toString();if(t.includes('.'))t=t.replace(/0+$/,'').replace(/\.$/,'');return t.replace('-','−')}
  const e=Math.floor(Math.log10(a)),m=x/Math.pow(10,e);let t=m.toPrecision(p);if(t.includes('.'))t=t.replace(/0+$/,'').replace(/\.$/,'');return t.replace('-','−')+'·10'+SUP(e)}
let EH=null,A0=null;  /* from au.constants */
// ---------- таблица базовых величин ----------
$('baseTab').innerHTML='<table class="mtab bt"><thead><tr><th class="n">quantity</th><th class="n">atomic unit</th><th class="n">in SI</th><th class="n">in familiar units</th></tr></thead><tbody>'+[
 ['mass','m<sub>e</sub> = 1','9.1093837·10⁻³¹ kg','1 u (dalton) = 1822.888 m<sub>e</sub>'],
 ['charge','e = 1','1.602176634·10⁻¹⁹ C','—'],
 ['action','ħ = 1','1.054571817·10⁻³⁴ J·s','—'],
 ['length','bohr a₀ = <span class=fr><span>4πε₀ħ²</span><span>m<sub>e</sub>e²</span></span>','5.29177211·10⁻¹¹ m','0.529177 Å'],
 ['energy','hartree E<sub>h</sub> = <span class=fr><span>e²</span><span>4πε₀a₀</span></span>','4.35974472·10⁻¹⁸ J','27.2114 eV = 2625.50 kJ/mol = 627.509 kcal/mol = 219474.6 cm⁻¹'],
 ['time','<span class=fr><span>ħ</span><span>E<sub>h</sub></span></span>','2.41888433·10⁻¹⁷ s','24.19 as'],
 ['velocity','<span class=fr><span>a₀E<sub>h</sub></span><span>ħ</span></span>','2.18769126·10⁶ m/s','speed of light c = 137.036 a.u.'],
 ['dipole moment','e·a₀','8.47835363·10⁻³⁰ C·m','2.541746 D'],
 ['electric field','<span class=fr><span>E<sub>h</sub></span><span>e·a₀</span></span>','5.14220675·10¹¹ V/m','—']].map(r=>'<tr>'+r.map(c=>`<td class="n">${c}</td>`).join('')+'</tr>').join('')+'</tbody></table>';
// ---------- конвертер ----------
const CAT={energy:{name:'energy',u:[['Eh','hartree'],['eV','eV'],['kJ','kJ/mol'],['kcal','kcal/mol'],['cm','cm⁻¹'],['K','K (E/k<sub>B</sub>)'],['Hz','Hz'],['J','J']]},
 length:{name:'length',u:[['a0','bohr'],['A','Å'],['pm','pm'],['nm','nm'],['m','m']]},
 dipole:{name:'dipole moment',u:[['au','a.u. (e·a₀)'],['D','debye'],['Cm','C·m']]},
 mass:{name:'mass',u:[['me','m<sub>e</sub>'],['u','u (dalton, Da)'],['kg','kg']]},
 time:{name:'time',u:[['au','a.u.'],['as','as'],['fs','fs'],['s','s']]}};
let cat='energy',unit='eV';
/* quantities that cannot be negative say so; the mass unit is explained */
/* every category explains its less familiar units under the table (only the dalton was explained) */
const NOTES={"energy": "hartree (E<sub>h</sub>) — the atomic unit of energy; eV — electronvolt, the energy an electron gains crossing a potential difference of 1 V; kJ/mol and kcal/mol — energy per mole of particles (used in thermochemistry); cm⁻¹ — the wavenumber <span class=fr><span>1</span><span>λ</span></span> of a light quantum of the same energy (spectroscopy); K — the temperature at which kT equals this energy; Hz — the frequency of the quantum, E = hν.", "length": "bohr (a₀) — the atomic unit of length, the radius of the first Bohr orbit; Å — ångström, 10⁻¹⁰ m; pm — picometre, 10⁻¹² m; nm — nanometre, 10⁻⁹ m.", "dipole": "a.u. — e·a₀: the electron charge at a distance of one bohr; D — debye, ≈ 3.336·10⁻³⁰ C·m (molecular dipole moments are usually given in debye: water has 1.85 D); C·m — the SI unit.", "time": "a.u. — the time in which an electron on the first Bohr orbit travels one bohr (≈ 24 as); as — attosecond, 10⁻¹⁸ s; fs — femtosecond, 10⁻¹⁵ s (the typical time of molecular vibrations).", "mass": "m<sub>e</sub> — the electron mass, the atomic unit of mass in quantum chemistry; u — the atomic mass unit, also called the dalton (Da): 1/12 of the mass of a carbon-12 atom."};
const NONNEG={mass:'A mass cannot be negative — enter a positive number.',length:'A length (distance) cannot be negative — enter a positive number.'},MASSNOTE='u is the atomic mass unit, also called the dalton (Da): 1/12 of the mass of a carbon-12 atom.';
const getConv=QC.live('au.convert');
async function conv(){const g=$('catG');g.innerHTML='';Object.entries(CAT).forEach(([k,c])=>{const b=document.createElement('button');b.className='chip';b.type='button';b.textContent=c.name;b.setAttribute('aria-pressed',k===cat);b.onclick=()=>{cat=k;unit=CAT[k].u[1][0];$('cv').value='1';conv()};g.appendChild(b)});
  const s=$('cu');s.innerHTML=CAT[cat].u.map(([k,l])=>`<option value="${k}"${k===unit?' selected':''}>${l.replace(/<[^>]+>/g,'')}</option>`).join('');
  const v=parseFloat($('cv').value.replace(',','.').replace('−','-'));
  if(isFinite(v)&&v<0&&NONNEG[cat]){$('convTab').innerHTML='<p class="small bad">'+NONNEG[cat]+'</p>';return}
  if(!isFinite(v)){$('convTab').innerHTML='<p class="small">Enter a number.</p>';return}let RC;try{RC=await getConv({cat,unit,value:v})}catch(e){return}
  $('convTab').innerHTML='<table class="mtab bt"><tbody>'+CAT[cat].u.map(([k,l],i)=>`<tr${k===unit?' class="sel"':''}><td class="n">${l}</td><td>${num(RC.rows[i][1])}</td></tr>`).join('')+'</tbody></table>'+(NOTES[cat]?'<p class="small unitNote">'+NOTES[cat]+'</p>':'')}
$('cv').addEventListener('input',conv);$('cu').addEventListener('change',e=>{unit=e.target.value;conv()});
// ---------- оценка радиуса ----------
let Z=1,r=0.5,uu='au';
function axes(svg,o){const X=x=>o.L+(x-o.x0)/(o.x1-o.x0)*(o.W-o.L-o.R),Y=y=>o.H-o.B-(y-o.y0)/(o.y1-o.y0)*(o.H-o.T-o.B);
  o.yt.forEach(v=>{el('line',{x1:o.L,x2:o.W-o.R,y1:Y(v),y2:Y(v),stroke:Math.abs(v)<1e-12?'var(--muted)':'var(--line)','stroke-width':1},svg);el('text',{x:o.L-6,y:Y(v)+4,'text-anchor':'end','font-size':11.5,fill:'var(--muted)'},svg,fmt(v,o.yd))});
  o.xt.forEach(v=>{el('line',{x1:X(v),x2:X(v),y1:o.H-o.B,y2:o.H-o.B+4,stroke:'var(--muted)','stroke-width':1},svg);el('text',{x:X(v),y:o.H-o.B+17,'text-anchor':'middle','font-size':11.5,fill:'var(--muted)'},svg,fmt(v,o.xd))});
  el('text',{x:(o.L+o.W-o.R)/2,y:o.H-2,'text-anchor':'middle','font-size':12,fill:'var(--muted)'},svg,o.xl);el('text',{x:o.L+4,y:o.T-2,'font-size':12,fill:'var(--muted)'},svg,o.yl);return {X,Y}}
const getEst=QC.live('au.estimate');
async function sec3(){$('Z').value=Z;$('Zv').textContent='Z = '+Z+(Z===1?' (H)':Z===2?' (He⁺)':Z===3?' (Li²⁺)':'');$('r').value=r;
  const ef=uu==='au'?1:EH.eV,lf=uu==='au'?1:A0,eu=uu==='au'?'Eₕ':'eV',lu=uu==='au'?'bohr':'Å';
  $('rv').textContent=`${fmt(r,3)} bohr = ${fmt(r*A0,3)} Å`;
  let D;try{D=await getEst({Z,r})}catch(e){return}const rmin=D.rmin,Emin=D.Emin;
  const svg=$('eChart');svg.innerHTML='';const ymin=Emin*1.6*ef,ymax=Z*Z*1.2*ef,step=Math.pow(10,Math.floor(Math.log10((ymax-ymin)/4))),st=[1,2,5].map(k=>k*step).find(s=>(ymax-ymin)/s<=6)||10*step;
  const yt=[];for(let v=Math.ceil(ymin/st)*st;v<=ymax+1e-9;v+=st)yt.push(+v.toFixed(6));
  const o={W:540,H:300,L:58,R:14,T:20,B:38,x0:0,x1:2*lf,y0:ymin,y1:ymax,xt:[0,0.5,1,1.5,2].map(v=>v*lf),xd:uu==='au'?1:2,yt,yd:Math.abs(st)<1?1:0,xl:'r, '+lu,yl:'energy, '+eu};const {X,Y}=axes(svg,o);
  const rs=[...Array(400)].map((_,i)=>0.02+1.98*i/399);const P=a=>{let s='',pen=false;rs.forEach((x,i)=>{const y=a[i]*ef;if(y<ymin||y>ymax){pen=false;return}s+=(pen?'L':'M')+X(x*lf).toFixed(1)+','+Y(y).toFixed(1);pen=true});return s};
  el('path',{d:P(D.Tc),fill:'none',stroke:'var(--warn)','stroke-width':1.6,'stroke-dasharray':'6 4'},svg);el('path',{d:P(D.Vc),fill:'none',stroke:'var(--ok)','stroke-width':1.6,'stroke-dasharray':'6 4'},svg);
  el('path',{d:P(D.Ec),fill:'none',stroke:'var(--accent)','stroke-width':2.6},svg);
  el('circle',{cx:X(rmin*lf),cy:Y(Emin*ef),r:5,fill:'none',stroke:'var(--ok)','stroke-width':2},svg);
  if(D.E*ef>=ymin&&D.E*ef<=ymax)el('circle',{cx:X(r*lf),cy:Y(D.E*ef),r:5.5,fill:'var(--accent)'},svg);
  [['kinetic ħ²/(2mr²)','var(--warn)',30],['attraction −Ze²/(4πε₀r)','var(--ok)',48],['sum','var(--accent)',66]].forEach(([t,c,y])=>el('text',{x:o.W-o.R-4,y:y,'text-anchor':'end','font-size':12,fill:c},svg,t));
  $('eKv').innerHTML=`<span>r</span><b>${fmt(r,3)} bohr = ${fmt(r*A0,3)} Å</b><span>kinetic</span><b>${fmt(D.T,4)} E<sub>h</sub> = ${fmt(D.T*EH.eV,2)} eV</b><span>potential</span><b>${fmt(D.V,4)} E<sub>h</sub> = ${fmt(D.V*EH.eV,2)} eV</b><span>sum</span><b>${fmt(D.E,4)} E<sub>h</sub> = ${fmt(D.E*EH.eV,2)} eV</b>`;
  const at=Math.abs(r-rmin)<0.006;
  $('t3').innerHTML=at?`<b>Minimum:</b> r = <span class=fr><span>1</span><span>Z</span></span> = ${fmt(rmin,3)} bohr, E = −<span class=fr><span>Z²</span><span>2</span></span> = ${fmt(Emin,3)} E<sub>h</sub> (${fmt(Emin*EH.eV,2)} eV)${Z===1?' — exactly the ground-state energy of the hydrogen atom. Such a crude estimate gives the exact answer because the bohr itself is defined by precisely this balance.':'. The energy grows as Z² and the size shrinks as <span class=fr><span>1</span><span>Z</span></span> — in atomic units this is obvious at once, with no constants.'} At the minimum the kinetic energy equals half the magnitude of the potential energy: T = −<span class=fr><span>V</span><span>2</span></span> (virial theorem).`:
   (r<rmin?'The electron is squeezed beyond the optimum: the kinetic energy ~<span class=fr><span>1</span><span>r²</span></span> grows faster than the gain in attraction ~<span class=fr><span>1</span><span>r</span></span>.':'The electron is too spread out: the kinetic energy is small, but so is the attraction to the nucleus.');
  const g=$('uG');g.innerHTML='';[['au','bohr and hartree'],['si','Å and eV']].forEach(([k,l])=>{const b=document.createElement('button');b.className='chip';b.type='button';b.textContent=l;b.setAttribute('aria-pressed',k===uu);b.onclick=()=>{uu=k;sec3()};g.appendChild(b)})}
$('Z').oninput=e=>{Z=+e.target.value;sec3()};$('r').oninput=e=>{r=+e.target.value;sec3()};$('rMin').onclick=()=>{r=1/Z;sec3()};
// ---------- шкала энергий ----------
const SCL=[['total energy of benzene (HF)'],['total energy of H₂O (HF)'],['carbon 1s electron binding energy (≈ 290 eV)'],['ionization energy of the H atom'],['C–C bond energy'],['correlation energy of H₂O'],['correlation energy of He'],['O–H vibrational quantum (3700 cm⁻¹)'],['hydrogen bond in the water dimer'],['“chemical accuracy”: 1 kcal/mol',1],['kT at 298 K',1],['H₂O rotational quantum (≈ 27 cm⁻¹)']];  /* labels; energies from au.scale (same order) */
let su='Eh';
const getScale=QC.live('au.scale');
async function sec4(){const g=$('sG');g.innerHTML='';[['Eh','hartree'],['eV','eV'],['kJ','kJ/mol'],['cm','cm⁻¹']].forEach(([k,l])=>{const b=document.createElement('button');b.className='chip';b.type='button';b.textContent=l;b.setAttribute('aria-pressed',k===su);b.onclick=()=>{su=k;sec4()};g.appendChild(b)});
  let d;try{d=await getScale({unit:su})}catch(e){return}
  const order=SCL.map((_,i)=>i).sort((a,b)=>d.eh[b]-d.eh[a]),SC=order.map(i=>[SCL[i][0],d.eh[i],SCL[i][1]]);
  const svg=$('scale');svg.innerHTML='';const L=290,W=900,R=110,T=10,rowH=(420-T-30)/SC.length;const vals=order.map(i=>d.v[i]);
  const lo=Math.floor(Math.log10(Math.min(...vals))),hi=Math.ceil(Math.log10(Math.max(...vals)));const X=v=>L+(Math.log10(v)-lo)/(hi-lo)*(W-L-R);
  for(let k=lo;k<=hi;k++){el('line',{x1:X(Math.pow(10,k)),x2:X(Math.pow(10,k)),y1:T,y2:420-24,stroke:'var(--line)','stroke-width':1},svg);el('text',{x:X(Math.pow(10,k)),y:416,'text-anchor':'middle','font-size':11.5,fill:'var(--muted)'},svg,'10'+SUP(k))}
  SC.forEach((s,i)=>{const y=T+i*rowH,v=vals[i];el('text',{x:L-10,y:y+rowH/2+4,'text-anchor':'end','font-size':12.5,fill:'var(--ink)'},svg,s[0]);
    el('rect',{x:L,y:y+4,width:Math.max(2,X(v)-L),height:rowH-8,rx:3,fill:s[2]?'var(--rho-l)':'var(--acc-bg)',stroke:'var(--accent)','stroke-width':1},svg);
    el('text',{x:X(v)+6,y:y+rowH/2+4,'font-size':12,fill:'var(--ink)','font-family':'var(--f-mono)'},svg,num(v,3))})}
QC.api('au.constants',{}).then(c=>{EH=c.EH;A0=c.A0;conv();sec3();sec4()}).catch(()=>{});
