/* Slater-Condon page (Atlas v2).  Alignment of the determinants, the
   permutation sign, the matrix element in spatial integrals and the spin
   notes come from quas_atlas.core.slater (slater.element); this script
   edits the determinants and writes the step-by-step solution. */
// Правила Слейтера–Кондона: спин-орбиталь = {o: номер пространственной орбитали, s: 'α'|'β'}
const so=(o,s)=>({o,s}),soKey=x=>x.o+x.s,eqSO=(a,b)=>a.o===b.o&&a.s===b.s;
/* spin notes of slater.element: template i, placeholders a[] in order */
const NOTE_T=[a=>`K between ${a[0]} and ${a[1]} = 0: different spins`,a=>`${a[0]} → ${a[1]}: spin changes, spin integration gives 0`,a=>`exchange term with ${a[0]} = 0: different spins`,a=>`⟨${a[0]}${a[1]}|${a[2]}${a[3]}⟩ = 0: spins do not match`,a=>`⟨${a[0]}${a[1]}|${a[2]}${a[3]}⟩ = 0: spins do not match`,a=>'three or more spin orbitals differ: the Hamiltonian contains at most two-electron operators'];
function fromSrv(r){if(r.bad)return r;r=JSON.parse(JSON.stringify(r));const O=([o,s])=>({o,s});r.al.B2=r.al.B2.map(O);r.al.diff=r.al.diff.map(([a,b])=>[O(a),O(b)]);r.notes=r.notes.map(n=>NOTE_T[n.i](n.a));return r}
const pairs=d=>d.map(x=>[x.o,x.s]);
// ---------- страница «Правила Слейтера–Кондона» ----------
const $=id=>document.getElementById(id);
const K=4;// число пространственных орбиталей
const lab=x=>x.o+x.s,detStr=D=>'|'+D.map(lab).join(' ')+'|';
let D=[[so(1,'α'),so(1,'β')],[so(2,'α'),so(2,'β')]],preKey='h2ci',hidden=false;
const PRE=[
 ['he','He: ⟨1s²|Ĥ|1s²⟩',[[1,'α'],[1,'β']],[[1,'α'],[1,'β']]],
 ['li','Li: 1s²2s',[[1,'α'],[1,'β'],[2,'α']],[[1,'α'],[1,'β'],[2,'α']]],
 ['trip','triplet φ₁αφ₂α',[[1,'α'],[2,'α']],[[1,'α'],[2,'α']]],
 ['h2ci','H₂: ⟨σ<sub>g</sub>²|Ĥ|σ<sub>u</sub>²⟩',[[1,'α'],[1,'β']],[[2,'α'],[2,'β']]],
 ['bril','single excitation',[[1,'α'],[1,'β']],[[1,'α'],[2,'β']]],
 ['spin','spin flip',[[1,'α'],[1,'β']],[[1,'α'],[2,'α']]],
 ['open','φ₁αφ₂β and φ₂αφ₁β',[[1,'α'],[2,'β']],[[2,'α'],[1,'β']]],
 ['perm','with permutation',[[1,'α'],[2,'α'],[3,'β']],[[3,'β'],[1,'α'],[4,'α']]],
 ['three','three differences',[[1,'α'],[1,'β'],[2,'α']],[[3,'α'],[3,'β'],[4,'α']]]];
const NOTE={he:'Ground-state energy of He in the single-determinant approximation: 2h₁₁ + J₁₁.',
 li:'The exchange term −K₁₂ appears only between electrons with the same spin (1sα and 2sα).',
 trip:'Compare with the singlet: the triplet energy contains −K₁₂ — electrons with parallel spins avoid each other (see the “Pauli principle” tab).',
 h2ci:'This is the off-diagonal CI matrix element for H₂ in a minimal basis (φ₁ = σ<sub>g</sub>, φ₂ = σ<sub>u</sub>): it equals K<sub>gu</sub> and mixes the configurations σ<sub>g</sub>² and σ<sub>u</sub>² — see the “H₂ dissociation” tab.',
 bril:'For a closed shell, h₁₂ + (11|12) is the element F₁₂ of the Fock operator. For Hartree–Fock orbitals it is zero (Brillouin’s theorem): single excitations do not mix directly with the ground determinant.',
 spin:'The Hamiltonian does not act on spin, so only determinants with the same projection M<sub>S</sub> can mix.',
 open:'These two determinants are used to build the singlet and the triplet with M<sub>S</sub> = 0: it is exactly the exchange integral K₁₂ that mixes them.',
 perm:'First, column 3β is moved to the third position — two transpositions, the sign does not change.',
 three:'Ĥ contains only one- and two-electron operators and cannot “reach” three replacements.'};
function setPre(k){const p=PRE.find(x=>x[0]===k);D=[p[2].map(([o,s])=>so(o,s)),p[3].map(([o,s])=>so(o,s))];preKey=k;hidden=false;quiz=null;$('quiz').innerHTML='';render()}
function chipsPre(){const g=$('preG');g.innerHTML='';PRE.forEach(([k,l])=>{const b=document.createElement('button');b.className='chip';b.type='button';b.innerHTML=l;b.setAttribute('aria-pressed',k===preKey);b.onclick=()=>setPre(k);g.appendChild(b)})}
function editor(i,res){const d=D[i],box=document.createElement('div');box.className='det';const name=i?'Ψ′':'Ψ';
  box.innerHTML=`<b>${name}</b>`;const orbs=document.createElement('div');orbs.className='orbs';
  for(let o=1;o<=K;o++){const c=document.createElement('div');c.className='orb';const sp=document.createElement('div');sp.className='sp';
    [['α','↑'],['β','↓']].forEach(([s,ch])=>{const b=document.createElement('button');b.type='button';b.className='sbtn';b.textContent=ch;const on=d.some(x=>x.o===o&&x.s===s);
      b.setAttribute('aria-pressed',on);b.setAttribute('aria-label',`φ${o}${s} in ${name}`);b.onclick=()=>{const k=d.findIndex(x=>x.o===o&&x.s===s);if(k>=0)d.splice(k,1);else d.push(so(o,s));preKey=null;hidden=false;render()};sp.appendChild(b)});
    c.appendChild(sp);const ln=document.createElement('div');ln.className='ln';c.appendChild(ln);const nm=document.createElement('div');nm.className='nm';nm.textContent='φ'+'₁₂₃₄'[o-1];c.appendChild(nm);orbs.appendChild(c)}
  box.appendChild(orbs);
  const cols=document.createElement('div');cols.className='cols';cols.innerHTML=`<span class="small" style="font-family:var(--f-body)">columns:</span><span class="bar">|</span>`;
  const dset=res&&res.al&&!hidden?new Set(res.al.diff.map(p=>lab(p[i]))):new Set();
  d.forEach((x,k)=>{const b=document.createElement('button');b.type='button';b.className='col'+(dset.has(lab(x))?' df':'');b.textContent=lab(x);b.title='move left';b.onclick=()=>{if(k>0){[d[k-1],d[k]]=[d[k],d[k-1]];preKey=null;hidden=false;render()}};cols.appendChild(b)});
  cols.insertAdjacentHTML('beforeend','<span class="bar">|</span>');box.appendChild(cols);return box}
function solution(r){const A=D[0],B=D[1];if(!A.length||!B.length)return '<p class="small">Add spin orbitals to both determinants.</p>';
  if(r.bad)return `<p class="small"><b>Different numbers of electrons</b> (${A.length} and ${B.length}): the Hamiltonian conserves the particle number, so such a matrix element is not considered.</p>`;
  const al=r.al,steps=[];
  steps.push(`<b class="h">Write out the determinants</b><span class="f">Ψ = ${detStr(A)}</span> &nbsp; <span class="f">Ψ′ = ${detStr(B)}</span>`);
  steps.push(`<b class="h">Bring Ψ′ into maximum coincidence</b>`+(al.inv===0?'Identical spin orbitals already occupy the same positions — nothing to permute, factor +1.':
    `Permute the columns so that identical spin orbitals stand in the same positions as in Ψ: <span class="f">${detStr(B)} → ${detStr(al.B2)}</span>. This takes ${al.inv} transposition(s)${al.inv===1?'':al.inv<5?'':''}, factor (−1)<sup>${al.inv}</sup> = <b>${al.sign>0?'+1':'−1'}</b>.`));
  const nd=r.nd;steps.push(`<b class="h">How many spin orbitals differ</b>`+(nd===0?'None: this is a diagonal element, the energy of the determinant.':
    `${nd}: `+al.diff.map(([m,p])=>`χ<sub>${lab(m)}</sub> → χ<sub>${lab(p)}</sub>`).join(', ')+'.'));
  const gen=nd===0?'⟨Ψ|Ĥ|Ψ⟩ = Σ<sub>i</sub> h<sub>ii</sub> + Σ<sub>i&lt;j</sub> (⟨ij|ij⟩ − ⟨ij|ji⟩)':nd===1?'⟨Ψ|Ĥ|Ψ′⟩ = h<sub>mp</sub> + Σ<sub>n≠m</sub> (⟨mn|pn⟩ − ⟨mn|np⟩)':nd===2?'⟨Ψ|Ĥ|Ψ′⟩ = ⟨mn|pq⟩ − ⟨mn|qp⟩':'⟨Ψ|Ĥ|Ψ′⟩ = 0';
  let sub='';
  if(nd===0){const t=[];A.forEach(x=>t.push(`h<sub>${lab(x)}</sub>`));for(let i=0;i<A.length;i++)for(let j=i+1;j<A.length;j++)t.push(`(⟨${lab(A[i])}${lab(A[j])}|${lab(A[i])}${lab(A[j])}⟩ − ⟨${lab(A[i])}${lab(A[j])}|${lab(A[j])}${lab(A[i])}⟩)`);sub=t.join(' + ')}
  else if(nd===1){const [m,p]=al.diff[0];sub=`h<sub>${lab(m)},${lab(p)}</sub>`+A.filter(n=>!(n.o===m.o&&n.s===m.s)).map(n=>` + ⟨${lab(m)}${lab(n)}|${lab(p)}${lab(n)}⟩ − ⟨${lab(m)}${lab(n)}|${lab(n)}${lab(p)}⟩`).join('')}
  else if(nd===2){const [[m,p],[n,q]]=al.diff;sub=`⟨${lab(m)}${lab(n)}|${lab(p)}${lab(q)}⟩ − ⟨${lab(m)}${lab(n)}|${lab(q)}${lab(p)}⟩`}
  steps.push(`<b class="h">General formula for this case</b><span class="f">${gen}</span>`+(sub?`<br>Substituting the spin orbitals: <span class="f" style="white-space:normal">${sub}</span>`:''));
  if(nd<=2)steps.push(`<b class="h">Integrate over spin</b>`+(r.notes.length?r.notes.map(t=>'• '+t).join('<br>'):'All terms survive: the spins match everywhere.')+'<br><span class="hint">The spin integral equals 1 if the electron has the same spin on the left and on the right, and 0 if the spins differ.</span>');
  else steps.push(`<b class="h">Why it is zero</b>${r.notes[0]}.`);
  const sg=al.sign<0&&!r.zero?'−(':'',sg2=al.sign<0&&!r.zero?')':'';
  steps.push(`<b class="h">Answer in terms of spatial integrals</b><span class="ans">⟨Ψ|Ĥ|Ψ′⟩ = ${r.expr}</span>`+(al.sign<0&&!r.zero?'<br><span class="hint">the minus sign comes from permuting the columns</span>':'')+
    (Object.keys(r.T).some(k=>k[0]==='c'&&!/^c:(\d),\1\|(\d),\2$/.test(k)&&!/^c:(\d),(\d)\|\1,\2$/.test(k))?'<br><span class="hint">(ab|cd) = ⟨ac|bd⟩ — chemists’ notation.</span>':''));
  let h='<ol class="steps">'+steps.map(s=>'<li>'+s+'</li>').join('')+'</ol>';if(preKey&&NOTE[preKey])h+=`<div class="status" style="margin-top:10px">${NOTE[preKey]}</div>`;return h}
const liveEl=QC.live('slater.element');
async function render(){let r={};if(D[0].length&&D[1].length){try{r=fromSrv(await liveEl({A:pairs(D[0]),B:pairs(D[1])}))}catch(e){return}}chipsPre();const box=$('dets');box.innerHTML='';box.appendChild(editor(0,r));box.appendChild(editor(1,r));
  $('sol').innerHTML=hidden?'<p class="small">The solution will appear once you answer the questions below.</p>':solution(r)}
// ---------- самопроверка ----------
let quiz=null,score=[0,0];
function rnd(n){return Math.floor(Math.random()*n)}
async function newQuiz(){const all=[];for(let o=1;o<=K;o++)['α','β'].forEach(s=>all.push(so(o,s)));
  const N=2+rnd(2);let A=[];const pool=all.slice();while(A.length<N){const k=rnd(pool.length);A.push(pool.splice(k,1)[0])}
  A.sort((x,y)=>x.o-y.o||(x.s==='α'?-1:1));
  const want=[0,1,1,2,2,3][rnd(6)];let B=A.slice();const free=all.filter(x=>!A.some(y=>y.o===x.o&&y.s===x.s));
  const idx=[...Array(N).keys()].sort(()=>Math.random()-0.5).slice(0,Math.min(want,N));
  idx.forEach(i=>{if(!free.length)return;const sameSpin=free.filter(x=>x.s===B[i].s);const src=Math.random()<0.75&&sameSpin.length?sameSpin:free;const pick=src[rnd(src.length)];free.splice(free.indexOf(pick),1);B[i]=pick});
  B=B.sort(()=>Math.random()-0.5);D=[A,B];preKey=null;hidden=true;let r;try{r=fromSrv(await QC.api('slater.element',{A:pairs(A),B:pairs(B)}))}catch(e){return}quiz={r,a1:null,a2:null};drawQuiz();render()}
function drawQuiz(){if(!quiz){$('quiz').innerHTML='';return}const q=quiz,r=q.r;
  const truth1=Math.min(r.nd,3),truth2=r.al.sign;
  const row=(label,opts,key,truth)=>{const v=q[key];return `<div class="qrow"><span class="small" style="min-width:300px">${label}</span>`+opts.map(([val,l])=>`<button class="chip" type="button" data-k="${key}" data-v="${val}" aria-pressed="${v===val}">${l}</button>`).join('')+(v!=null?`<span class="fb ${v===truth?'ok':'no'}">${v===truth?'correct':'incorrect'}</span>`:'')+'</div>'};
  let h=row('How many spin orbitals differ after bringing into maximum coincidence?',[[0,'0'],[1,'1'],[2,'2'],[3,'3 or more']],'a1',truth1)+row('What factor does the column permutation give?',[[1,'+1'],[-1,'−1']],'a2',truth2);
  if(q.a1!=null&&q.a2!=null)h+=`<div class="status">Answer: <b>${r.expr}</b>${r.al.sign<0&&!r.zero?' (including the permutation sign)':''}. The full solution is in the “Step-by-step solution” section.</div>`;
  $('quiz').innerHTML=h;$('quiz').querySelectorAll('[data-k]').forEach(b=>b.onclick=()=>{if(q[b.dataset.k]!=null)return;q[b.dataset.k]=+b.dataset.v;
    if(q.a1!=null&&q.a2!=null){score[1]++;if(q.a1===truth1&&q.a2===truth2)score[0]++;hidden=false;render();$('qScore').textContent=`solved correctly: ${score[0]} of ${score[1]}`}drawQuiz()})}
$('qNew').onclick=newQuiz;
render();
