/* Molecular Hamiltonian page (Atlas v2).  Formula parsing, the list of
   nuclei, the electron count and every term count come from
   quas_atlas.core.hamiltonian (ham.molecule); this script typesets. */
// ---------- страница «Молекулярный гамильтониан» ----------
const $=id=>document.getElementById(id);
const fr=(a,b)=>'<span class=fr><span>'+a+'</span><span>'+b+'</span></span>';
const sg=(lo,up)=>'<span class="sg"><span class="up">'+(up||'')+'</span><span class="s">Σ</span><span class="lo">'+(lo||'')+'</span></span>';
const n0=x=>String(x).replace(/\B(?=(\d{3})+(?!\d))/g,' ');
const sub=s=>s.replace(/(\d+)/g,'<sub>$1</sub>');
/* the numbers of the formula typed in the field become subscripts (H₂O); the server gets plain digits */
const SUBD='₀₁₂₃₄₅₆₇₈₉',toSub=s=>String(s).replace(/\d/g,d=>SUBD[d]),fromSub=s=>String(s).replace(/[₀-₉]/g,c=>String(SUBD.indexOf(c)));
const fmla=(f,q)=>sub(f)+(q?'<sup>'+(Math.abs(q)>1?Math.abs(q):'')+(q>0?'+':'−')+'</sup>':'');
let cur=null,elMode=false;
const getMol=QC.live('ham.molecule');
async function show(f,q){let p;try{p=await getMol({formula:f,q:q==null?null:q})}catch(e){return}if(!p.ok&&p.error==='parse'){$('sum').innerHTML='<span class="bad">Could not parse the formula “'+f.replace(/</g,'&lt;')+'”.</span> Write element symbols with a capital letter: H<sub>2</sub>O, CH<sub>3</sub>OH, Fe(C<sub>5</sub>H<sub>5</sub>)<sub>2</sub>.';return}
  if(!p.ok&&p.error==='noelectrons'){$('sum').innerHTML='<span class="bad">This particle has no electrons left.</span>';return}
  if(!p.ok&&p.error==='toomany'){$('sum').innerHTML='<span class="bad">Too many nuclei to write out.</span>';return}
  q=p.q;const nuc=p.nuc,M=p.M,N=p.N,Zs=p.Zs;
  cur={f,q,nuc,M,N,Zs,cnt:p.counts,zz:p.zz};$('fIn').value=toSub(f);$('qIn').value=String(q);
  document.querySelectorAll('#molG .chip').forEach(b=>b.setAttribute('aria-pressed',b.dataset.f===f&&+b.dataset.q===q));
  $('sum').innerHTML='<b>'+fmla(f.replace(/[+-]$/,''),q)+'</b>: nuclei M = <b>'+M+'</b>, sum of nuclear charges ΣZ<sub>A</sub> = '+Zs+(q?', particle charge '+(q>0?'+':'−')+Math.abs(q):'')+', electrons N = ΣZ<sub>A</sub> − q = <b>'+N+'</b>.';
  render()}
function render(){if(!cur)return;const {nuc,M,N}=cur;const few=M<=5;
  const uniq=[...new Set(nuc.map(a=>a.e))];
  // T_N
  let tN;if(M<=3)tN=nuc.map((a,k)=>(k?' − ':'−')+fr('1','2M<sub>'+a.lab+'</sub>')+'∇<sub>'+a.lab+'</sub>²').join('');
  else tN='−'+sg('A=1','M')+fr('1','2M<sub>A</sub>')+'∇<sub>A</sub>²';
  const tE='−'+fr('1','2')+sg('i=1',N)+'∇<sub>i</sub>²';
  let vEN;if(few)vEN='−'+sg('i=1',N)+'('+nuc.map(a=>fr(a.Z,'r<sub>'+a.lab+',i</sub>')).join(' + ')+')';
  else vEN='−'+sg('i=1',N)+sg('A=1',M)+fr('Z<sub>A</sub>','r<sub>Ai</sub>');
  const vEE=N>1?'+'+sg('i=1',N-1)+sg('j=i+1',N)+fr('1','r<sub>ij</sub>'):'';
  let vNN='';const pairs=cur.cnt.VNN;
  if(M>1){if(pairs<=6){const t=[];cur.zz.forEach(([a,b,zz])=>t.push(fr(zz,'R<sub>'+nuc[a].lab+nuc[b].lab+'</sub>')));vNN='+'+t.join(' + ')}
    else vNN='+'+sg('A=1',M-1)+sg('B=A+1',M)+fr('Z<sub>A</sub>Z<sub>B</sub>','R<sub>AB</sub>')}
  const term=(h,lab,cls)=>h?'<span class="term '+(cls||'')+'"><span class="tx">'+h+'</span><span class="lab">'+lab+'</span></span>':'';
  $('hamBox').innerHTML='<span class="eqs">'+(elMode?'Ĥ<sub>el</sub> =':'Ĥ =')+'</span>'+term(tN,'T<sub>N</sub> — nuclei',elMode?'off':'')+' '+term(tE,'T<sub>e</sub> — electrons')+' '+term(vEN,'V<sub>eN</sub> — attraction')+' '+term(vEE,'V<sub>ee</sub> — electron repulsion')+
    (elMode?'<span class="br"></span><span class="eqs">U(R) = E<sub>el</sub>(R) + V<sub>NN</sub>,&nbsp;&nbsp; V<sub>NN</sub> =</span>'+term(vNN.replace(/^\+/,''),'constant for given R','const'):' '+term(vNN,'V<sub>NN</sub> — nuclear repulsion'));
  const masses=uniq.map(e=>'M<sub>'+e+'</sub> = '+n0(Math.round(nuc.find(a=>a.e===e).m-nuc.find(a=>a.e===e).Z))).join(', ');
  $('hamTxt').innerHTML=elMode?'<b>The nuclei are fixed.</b> The nuclear kinetic energy is dropped: the nuclei are '+n0(Math.round(Math.min(...nuc.map(a=>a.m))))+' or more times heavier than an electron and move much more slowly. The electronic problem is solved at fixed nuclear coordinates R, and V<sub>NN</sub> is then just a number: it shifts all levels equally and is added to E<sub>el</sub> to give the potential energy surface U(R).':
    '<b>The full Hamiltonian</b> describes the simultaneous motion of '+M+' '+ruN(M,'nuclei','nuclei','nuclei')+' and '+N+' '+ruN(N,'electrons','electrons','electrons')+'. Nuclear masses in electron masses: '+masses+'. The electron–electron distances r<sub>ij</sub>, electron–nucleus distances r<sub>Ai</sub> and internuclear distances R<sub>AB</sub> couple all particles, so the variables do not separate.';
  const C=[['T<sub>N</sub>','kinetic energy of the nuclei',M,'M'],['T<sub>e</sub>','kinetic energy of the electrons',N,'N'],['V<sub>eN</sub>','electron–nucleus attraction',cur.cnt.VeN,'N·M'],['V<sub>ee</sub>','electron repulsion',cur.cnt.Vee,fr('N(N − 1)','2')],['V<sub>NN</sub>','nuclear repulsion',pairs,fr('M(M − 1)','2')]];
  const mx=Math.log10(Math.max(...C.map(c=>c[2]))+1);
  $('cnt').innerHTML=C.map(c=>'<span>'+c[0]+' — '+c[1]+' <span class="hint">('+c[3]+')</span></span><b>'+n0(c[2])+'</b><span class="bar"><i style="width:'+(100*Math.log10(c[2]+1)/mx).toFixed(1)+'%"></i></span>').join('')+
    '<span><b style="font-family:var(--f-body)">total in Ĥ<sub>el</sub> + V<sub>NN</sub></b></span><b>'+n0(cur.cnt.total)+'</b><span></span>'}
const ruN=(n,one,few,many)=>{const m10=n%10,m100=n%100;return m10===1&&m100!==11?one:(m10>=2&&m10<=4&&(m100<10||m100>=20)?few:many)};
const EX=[['H2+',1],['H2',0],['HeH+',1],['LiH',0],['H2O',0],['NH3',0],['CH4',0],['NH4',1],['CO2',0],['C2H4',0],['C6H6',0],['CaH2',0],['MgF2',0],['BeCl2',0]];
const mg=$('molG');EX.forEach(([f,q])=>{const b=document.createElement('button');b.type='button';b.className='chip';b.dataset.f=f.replace(/\+$/,'');b.dataset.q=q;
  b.innerHTML=fmla(f.replace(/\+$/,''),q);b.onclick=()=>show(f.replace(/\+$/,''),q);mg.appendChild(b)});
[-2,-1,0,1,2].forEach(q=>{const o=document.createElement('option');o.value=q;o.textContent=q>0?'+'+q:q<0?'−'+(-q):'0';$('qIn').appendChild(o)});$('qIn').value='0';
$('bGo').onclick=()=>show(fromSub($('fIn').value.trim()),+$('qIn').value);
$('fIn').addEventListener('input',e=>{const i=e.target,p=i.selectionStart,v=toSub(i.value);if(v!==i.value){i.value=v;i.setSelectionRange(p,p)}});$('fIn').addEventListener('keydown',e=>{if(e.key==='Enter')$('bGo').click()});
$('bFull').onclick=()=>{elMode=false;$('bFull').setAttribute('aria-pressed','true');$('bEl').setAttribute('aria-pressed','false');render()};
$('bEl').onclick=()=>{elMode=true;$('bFull').setAttribute('aria-pressed','false');$('bEl').setAttribute('aria-pressed','true');render()};
// ---------- тренажёр ----------
const POOL=['LiF','HCl','H2S','PH3','SiH4','HCN','N2','O2','NaCl','KCl','C2H2','C2H6','BF3','SO2','N2O','CH3OH','H2O2','HCOOH','C2H4','MgH2','CaH2','BeH2','CH2O','NF3','CCl4','CS2','LiH','B2H6','C3H8'];
let qz=null;
async function newQ(){let f;do f=POOL[Math.floor(Math.random()*POOL.length)];while(qz&&f===qz.f);let p;try{p=await QC.api('ham.molecule',{formula:f,q:0})}catch(e){return}const M=p.M,N=p.N;
  qz={f,N,M,ans:[N,p.counts.Te,p.counts.VeN,p.counts.Vee,p.counts.VNN]};$('qMol').innerHTML=sub(f);for(let k=0;k<5;k++){$('q'+k).value='';$('q'+k).className=''}$('qRes').textContent='Enter the numbers and click “Check”.'}
$('qNew').onclick=newQ;
// «Проверьте себя» с выбором ответа (assets/js/try.*.js, initSelf): правильные ответы для вариантов
window.qcSelf=()=>qz.ans.slice(0,5).map(String);
$('qChk').onclick=()=>{let ok=0;for(let k=0;k<5;k++){const v=+String($('q'+k).value).replace(/\s/g,'');const good=v===qz.ans[k];$('q'+k).className=$('q'+k).value===''?'':good?'ok':'bad';if(good)ok++}
  $('qRes').innerHTML=ok===5?'<b class="okc">All correct!</b> Click “New molecule” for the next task.':'Correct: '+ok+' of 5. Hint: V<sub>eN</sub> — every electron with every nucleus; V<sub>ee</sub> and V<sub>NN</sub> — every pair once.'};
$('qShow').onclick=()=>{const {N,M}=qz;for(let k=0;k<5;k++){$('q'+k).value=qz.ans[k];$('q'+k).className='ok'}
  $('qRes').innerHTML='Nuclei M = '+M+', electrons N = '+N+'. T<sub>e</sub>: N = '+N+'; V<sub>eN</sub>: N·M = '+qz.ans[2]+'; V<sub>ee</sub>: '+fr('N(N − 1)','2')+' = '+qz.ans[3]+'; V<sub>NN</sub>: '+fr('M(M − 1)','2')+' = '+qz.ans[4]+'.'};
show('H2O',0);newQ();
