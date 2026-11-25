/* Atomic terms page (Atlas v2).  Configurations, microstates, the
   (M_L, M_S) table, term extraction, Hund's rules and the ground terms of
   H-Kr come from quas_atlas.core.terms (terms.analyze, terms.element);
   this script builds the tables and texts. */
// ---------- страница «Термы атомов» ----------
const $=id=>document.getElementById(id);
const LL='SPDFGHIKLMNOQ',LN='spdf';
const SUP=s=>String(s).replace(/\d/g,c=>'⁰¹²³⁴⁵⁶⁷⁸⁹'[c]);
const half=x2=>x2%2===0?String(x2/2):'<span class=fr><span>'+x2+'</span><span>2</span></span>';
const halfT=x2=>x2%2===0?String(x2/2):x2+'/2';
const termH=(L,S2,J2)=>'<sup>'+(S2+1)+'</sup>'+LL[L]+(J2!=null?'<sub>'+halfT(J2)+'</sub>':'');
// ---------- configuration analysis: terms.analyze ----------
const ERRT={bad_token:a=>'Could not parse “'+a[0]+'”. Write it like d3, p2, 2p1 3p1.',count:a=>'A '+a[0]+'-subshell holds from 1 to '+a[1]+' electrons.',empty:'Enter a configuration.',duplicate:'Write identical subshells together: e.g. p2, not p1 p1. For different shells give the principal quantum numbers: 2p1 3p1.',too_many:'Too many microstates — take at most 8 electrons.'};
function errText(r){const t=ERRT[r.err];return typeof t==='function'?t(r.a):(t||r.err)}
const cfgName=sh=>sh.map(x=>(x.n||'')+LN[x.l]+SUP(x.N)).join(' ');
// ---------- раздел 1 ----------
let SH=null,MS=null,TB=null,TERMS=[],shown=0,AN=null;
const PRE=['p1','p2','p3','p4','d1','d2','d3','d5','d8','s1 p1','2p1 3p1','s1 d1'];
async function setCfg(s){let r;try{r=await QC.api('terms.analyze',{cfg:s})}catch(e){return false}$('cfgErr').textContent=r.err?errText(r):'';if(r.err)return false;
  SH=r.sh;$('cfgIn').value=s;AN=r;MS={length:r.nmicro};TB={T:r.T,Lm:r.Lm,Sm:r.Sm};TERMS=r.terms;shown=0;
  [...$('cfgG').children].forEach(b=>b.setAttribute('aria-pressed',b.dataset.c===s));render1();return true}
function render1(){const hl=shown>0?new Set(TERMS[shown-1].cells):new Set();const rem=Object.assign({},TB.T);for(let i=0;i<shown-1;i++)TERMS[i].cells.forEach(c=>rem[c]--);
  const S=[];for(let s=TB.Sm;s>=-TB.Sm;s-=2)S.push(s);
  $('tabT').innerHTML='Number of microstates with given M<sub>L</sub> and M<sub>S</sub>'+(shown?' (after subtracting '+(shown-1)+' term(s)'+(shown-1===1?'s':'s')+'; highlighted: '+termH(TERMS[shown-1].L,TERMS[shown-1].S2)+')':'');
  $('mlmsTab').innerHTML='<table class="mtab mlms"><thead><tr><th class="rh">M<sub>L</sub> \\ M<sub>S</sub></th>'+S.map(s=>'<th>'+(s>0?'+':s<0?'−':'')+half(Math.abs(s))+'</th>').join('')+'</tr></thead><tbody>'+
    Array.from({length:2*TB.Lm+1},(_,i)=>TB.Lm-i).map(ml=>'<tr><th class="rh">'+(ml>0?'+':ml<0?'−':'')+Math.abs(ml)+'</th>'+S.map(s=>{const k=ml+'|'+s,v=rem[k]||0;return '<td class="'+(hl.has(k)?'hl':v?'':'z')+'">'+v+'</td>'}).join('')+'</tr>').join('')+'</tbody></table>';
  const parts=SH.map((x,i)=>'C('+2*(2*x.l+1)+', '+x.N+') = '+AN.binom[i]);
  $('nMicro').innerHTML='<span>Configuration <b>'+cfgName(SH)+'</b></span><span>microstates: <b>'+MS.length+'</b>'+(SH.length>1?' = '+AN.binom.join(' × '):'')+'</span><span class="hint">'+parts.join('; ')+'</span>';
  const gr=AN.ground,single=SH.length===1;
  const gi=AN.gi;
  $('termList').innerHTML=TERMS.slice(0,shown).map((t,i)=>{const J=t.J2;
    return '<span class="t'+(i===gi?' g':'')+'">'+termH(t.L,t.S2)+'<small>'+t.mult+' microstates; J = '+J.map(halfT).join(', ')+'</small></span>'}).join('');
  const sum=TERMS.slice(0,shown).reduce((a,t)=>a+t.mult,0);
  $('st1').innerHTML=shown===0?'Press “Mark the next term”: take the largest M<sub>L</sub> and, for it, the largest M<sub>S</sub> — these are L and S of the next term. The term takes one microstate from every cell with |M<sub>L</sub>| ≤ L and |M<sub>S</sub>| ≤ S.':
    shown<TERMS.length?'Term '+termH(TERMS[shown-1].L,TERMS[shown-1].S2)+': L = '+TERMS[shown-1].L+', S = '+half(TERMS[shown-1].S2)+', it takes (2L + 1)(2S + 1) = '+TERMS[shown-1].mult+' microstates. Accounted for: '+sum+' of '+MS.length+'.':
    '<b>All microstates are assigned: '+sum+' = '+MS.length+'.</b> '+(single?'By Hund’s rules the ground term is '+termH(gr.L,gr.S2,gr.J2)+' (highlighted in green). Hund’s rules do not reliably predict the order of the other terms.':'For nonequivalent electrons all combinations of L and S are allowed.');
  $('bStep').disabled=shown>=TERMS.length}
$('bStep').onclick=()=>{if(shown<TERMS.length){shown++;render1()}};
$('bAll').onclick=()=>{shown=TERMS.length;render1()};
$('bReset').onclick=()=>{shown=0;render1()};
$('cfgGo').onclick=()=>setCfg($('cfgIn').value);$('cfgIn').addEventListener('keydown',e=>{if(e.key==='Enter')setCfg($('cfgIn').value)});
PRE.forEach(c=>{const b=document.createElement('button');b.type='button';b.className='chip';b.dataset.c=c;b.innerHTML=c.split(' ').map(p=>{const m=p.match(/^(\d?)([spdf])(\d+)$/);return m[1]+m[2]+'<sup>'+m[3]+'</sup>'}).join(' ');b.onclick=()=>setCfg(c);$('cfgG').appendChild(b)});
// ---------- раздел 2: элементы H–Kr ----------
const EL='H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr'.split(' ');
function cfgStr(E){return (E.core?'['+E.core+']':'')+E.rest.map(x=>x.n+LN[x.l]+'<sup>'+x.N+'</sup>').join('')}
const liveE=QC.live('terms.element');
let Zsel=26;
async function render2(){const Z=Zsel;let E;try{E=await liveE({Z})}catch(e){return}const op=E.open,g=E.ground;
  [...$('ptab').querySelectorAll('button')].forEach(b=>b.setAttribute('aria-pressed',+b.dataset.z===Z));
  $('elCfg').innerHTML='<span><b>'+EL[Z-1]+'</b> (Z = '+Z+')</span><span>'+cfgStr(E)+'</span>'+(op.length?'<span class="hint">open subshells: '+op.map(x=>x.n+LN[x.l]+SUP(x.N)).join(', ')+'</span>':'');
  $('boxes').innerHTML=g.closed?'<span class="hint">All subshells are filled.</span>':g.boxes.map(b=>{const n=2*b.x.l+1;return '<div class="shell"><div class="row">'+b.occ.map((o,k)=>'<span class="bx">'+(o===2?'↑↓':o===1?'↑':'')+'</span>').join('')+'</div><div class="row">'+Array.from({length:n},(_,k)=>'<span class="ml">'+(b.x.l-k>0?'+':b.x.l-k<0?'−':'')+Math.abs(b.x.l-k)+'</span>').join('')+'</div><div class="hint">'+b.x.n+LN[b.x.l]+SUP(b.x.N)+' · m<sub>l</sub></div></div>'}).join('');
  if(g.closed){$('st2').innerHTML='Closed shells: S = 0, L = 0, J = 0 → <span class="big">'+termH(0,0,0)+'</span>';return}
  const Ssum=g.boxes.map(b=>'('+b.up+' − '+b.dn+')·½').join(' + ');const Ml=g.boxes.map(b=>b.ml).join(' + ');
  $('st2').innerHTML='S = '+Ssum+' = '+half(g.S2)+' → 2S + 1 = <b>'+(g.S2+1)+'</b><br>L = |Σm<sub>l</sub>| = |'+Ml.replace(/-/g,'−')+'| = <b>'+g.L+'</b> ('+LL[g.L]+')<br>J = '+(g.L===0||g.S2===0?'L + S':g.less?'|L − S|, the subshell is less than half full':g.more?'L + S, the subshell is more than half full':'S')+' = <b>'+half(g.J2)+'</b><br>Ground term: <span class="big">'+termH(g.L,g.S2,g.J2)+'</span>'}
(()=>{const pos=Z=>{if(Z===1)return [1,1];if(Z===2)return [1,18];const per=Z<=10?2:Z<=18?3:4;const st=per===2?3:per===3?11:19;const k=Z-st;
    if(per<4){if(k<2)return [per,k+1];return [per,k+11]}return [per,k+1]};
  const grid=$('ptab');const cells={};for(let Z=1;Z<=36;Z++){const [r,c]=pos(Z);cells[r+'|'+c]=Z}
  for(let r=1;r<=4;r++)for(let c=1;c<=18;c++){const Z=cells[r+'|'+c];if(Z){const b=document.createElement('button');b.type='button';b.textContent=EL[Z-1];b.dataset.z=Z;b.title='Z = '+Z;b.onclick=()=>{Zsel=Z;render2()};grid.appendChild(b)}else grid.appendChild(document.createElement('span'))}})();
$('bToCfg').onclick=async()=>{let E;try{E=await QC.api('terms.element',{Z:Zsel})}catch(e){return}const op=E.open;if(!op.length)return;const s=op.map(x=>(op.length>1?x.n:'')+LN[x.l]+x.N).join(' ');if(await setCfg(s)){$('bAll').click();$('h1s').scrollIntoView({behavior:'smooth'})}};
// ---------- тренажёр ----------
let qz=null;
async function newQ(){let Z,E;try{do{Z=1+Math.floor(Math.random()*36);E=await QC.api('terms.element',{Z})}while((qz&&Z===qz.Z)||!E.open.length)}catch(e){return}qz={Z,g:E.ground};
  $('qEl').innerHTML=EL[Z-1]+' <span class="hint" style="font-family:var(--f-body);font-size:14px">'+cfgStr(E)+'</span>';for(let k=0;k<3;k++){$('q'+k).value='';$('q'+k).className=''}$('qRes').textContent='Enter your answers and press “Check”.'}
const pj=s=>{s=String(s).trim().replace(',','.').replace(/\s/g,'');if(/^\d+\/2$/.test(s))return +s.split('/')[0];if(s==='')return NaN;return Math.round(+s*2)};
const pL=s=>{s=String(s).trim().toUpperCase();if(/^\d+$/.test(s))return +s;const i=LL.indexOf(s);return s.length===1&&i>=0?i:NaN};
$('qNew').onclick=newQ;
// «Проверьте себя» с выбором ответа (assets/js/try.*.js, initSelf): правильные ответы для вариантов
window.qcSelf=()=>{const g=qz.g;return [String(g.S2+1),LL[g.L],halfT(g.J2)]};
$('qChk').onclick=()=>{const g=qz.g;const r=[+$('q0').value===g.S2+1,pL($('q1').value)===g.L,pj($('q2').value)===g.J2];
  r.forEach((ok,k)=>$('q'+k).className=$('q'+k).value.trim()===''?'':ok?'ok':'bad');
  $('qRes').innerHTML=r.every(Boolean)?'<b>Correct!</b> '+termH(g.L,g.S2,g.J2):'Not quite yet. Place the electrons of the open subshell in the m<sub>l</sub> boxes (section 2) and find S, L and J.'};
$('qShow').onclick=()=>{const g=qz.g;$('q0').value=g.S2+1;$('q1').value=LL[g.L];$('q2').value=halfT(g.J2);for(let k=0;k<3;k++)$('q'+k).className='ok';
  $('qRes').innerHTML='Ground term of '+EL[qz.Z-1]+': <span class="big">'+termH(g.L,g.S2,g.J2)+'</span> — S = '+half(g.S2)+', L = '+g.L+', J = '+half(g.J2)+'.';Zsel=qz.Z;render2()};
setCfg('p2');render2();newQ();
