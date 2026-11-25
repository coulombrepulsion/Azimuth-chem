/* Slater-Condon page (Atlas v2).  Alignment of the determinants, the
   permutation sign, the matrix element in spatial integrals and the spin
   notes come from quas_atlas.core.slater (slater.element); this script
   edits the determinants and writes the step-by-step solution. */
// Правила Слейтера–Кондона: спин-орбиталь = {o: номер пространственной орбитали, s: 'α'|'β'}
const so=(o,s)=>({o,s}),soKey=x=>x.o+x.s,eqSO=(a,b)=>a.o===b.o&&a.s===b.s;
/* spin notes of slater.element: template i, placeholders a[] in order */
const NOTE_T=[a=>`K между ${a[0]} и ${a[1]} = 0: спины разные`,a=>`${a[0]} → ${a[1]}: спин меняется, интегрирование по спину даёт 0`,a=>`обменный член с ${a[0]} = 0: спины разные`,a=>`⟨${a[0]}${a[1]}|${a[2]}${a[3]}⟩ = 0: спины не совпадают`,a=>`⟨${a[0]}${a[1]}|${a[2]}${a[3]}⟩ = 0: спины не совпадают`,a=>'отличаются три и более спин-орбитали: гамильтониан содержит не более чем двухэлектронные операторы'];
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
 ['trip','триплет φ₁αφ₂α',[[1,'α'],[2,'α']],[[1,'α'],[2,'α']]],
 ['h2ci','H₂: ⟨σ<sub>g</sub>²|Ĥ|σ<sub>u</sub>²⟩',[[1,'α'],[1,'β']],[[2,'α'],[2,'β']]],
 ['bril','однократное возбуждение',[[1,'α'],[1,'β']],[[1,'α'],[2,'β']]],
 ['spin','смена спина',[[1,'α'],[1,'β']],[[1,'α'],[2,'α']]],
 ['open','φ₁αφ₂β и φ₂αφ₁β',[[1,'α'],[2,'β']],[[2,'α'],[1,'β']]],
 ['perm','с перестановкой',[[1,'α'],[2,'α'],[3,'β']],[[3,'β'],[1,'α'],[4,'α']]],
 ['three','три отличия',[[1,'α'],[1,'β'],[2,'α']],[[3,'α'],[3,'β'],[4,'α']]]];
const NOTE={he:'Энергия основного состояния He в приближении одного определителя: 2h₁₁ + J₁₁.',
 li:'Обменный член −K₁₂ есть только между электронами с одинаковыми спинами (1sα и 2sα).',
 trip:'Сравните с синглетом: у триплета в энергию входит −K₁₂ — электроны с параллельными спинами избегают друг друга (см. вкладку «Принцип Паули»).',
 h2ci:'Это недиагональный элемент матрицы КВ для H₂ в минимальном базисе (φ₁ = σ<sub>g</sub>, φ₂ = σ<sub>u</sub>): он равен K<sub>gu</sub> и смешивает конфигурации σ<sub>g</sub>² и σ<sub>u</sub>² — см. вкладку «Диссоциация H₂».',
 bril:'Для замкнутой оболочки h₁₂ + (11|12) — это элемент F₁₂ оператора Фока. Для хартри–фоковских орбиталей он равен нулю (теорема Бриллюэна): однократные возбуждения напрямую с основным определителем не смешиваются.',
 spin:'Гамильтониан не действует на спин, поэтому смешиваться могут только определители с одинаковой проекцией M<sub>S</sub>.',
 open:'Из этих двух определителей строят синглет и триплет с M<sub>S</sub> = 0: их смешивает именно обменный интеграл K₁₂.',
 perm:'Сначала столбец 3β переносим на третье место — две транспозиции, знак не меняется.',
 three:'Ĥ содержит только одно- и двухэлектронные операторы и не может «дотянуться» до трёх замен.'};
function setPre(k){const p=PRE.find(x=>x[0]===k);D=[p[2].map(([o,s])=>so(o,s)),p[3].map(([o,s])=>so(o,s))];preKey=k;hidden=false;quiz=null;$('quiz').innerHTML='';render()}
function chipsPre(){const g=$('preG');g.innerHTML='';PRE.forEach(([k,l])=>{const b=document.createElement('button');b.className='chip';b.type='button';b.innerHTML=l;b.setAttribute('aria-pressed',k===preKey);b.onclick=()=>setPre(k);g.appendChild(b)})}
function editor(i,res){const d=D[i],box=document.createElement('div');box.className='det';const name=i?'Ψ′':'Ψ';
  box.innerHTML=`<b>${name}</b>`;const orbs=document.createElement('div');orbs.className='orbs';
  for(let o=1;o<=K;o++){const c=document.createElement('div');c.className='orb';const sp=document.createElement('div');sp.className='sp';
    [['α','↑'],['β','↓']].forEach(([s,ch])=>{const b=document.createElement('button');b.type='button';b.className='sbtn';b.textContent=ch;const on=d.some(x=>x.o===o&&x.s===s);
      b.setAttribute('aria-pressed',on);b.setAttribute('aria-label',`φ${o}${s} в ${name}`);b.onclick=()=>{const k=d.findIndex(x=>x.o===o&&x.s===s);if(k>=0)d.splice(k,1);else d.push(so(o,s));preKey=null;hidden=false;render()};sp.appendChild(b)});
    c.appendChild(sp);const ln=document.createElement('div');ln.className='ln';c.appendChild(ln);const nm=document.createElement('div');nm.className='nm';nm.textContent='φ'+'₁₂₃₄'[o-1];c.appendChild(nm);orbs.appendChild(c)}
  box.appendChild(orbs);
  const cols=document.createElement('div');cols.className='cols';cols.innerHTML=`<span class="small" style="font-family:var(--f-body)">столбцы:</span><span class="bar">|</span>`;
  const dset=res&&res.al&&!hidden?new Set(res.al.diff.map(p=>lab(p[i]))):new Set();
  d.forEach((x,k)=>{const b=document.createElement('button');b.type='button';b.className='col'+(dset.has(lab(x))?' df':'');b.textContent=lab(x);b.title='сдвинуть влево';b.onclick=()=>{if(k>0){[d[k-1],d[k]]=[d[k],d[k-1]];preKey=null;hidden=false;render()}};cols.appendChild(b)});
  cols.insertAdjacentHTML('beforeend','<span class="bar">|</span>');box.appendChild(cols);return box}
function solution(r){const A=D[0],B=D[1];if(!A.length||!B.length)return '<p class="small">Добавьте спин-орбитали в оба определителя.</p>';
  if(r.bad)return `<p class="small"><b>Разное число электронов</b> (${A.length} и ${B.length}): гамильтониан сохраняет число частиц, такой матричный элемент не рассматривают.</p>`;
  const al=r.al,steps=[];
  steps.push(`<b class="h">Записываем определители</b><span class="f">Ψ = ${detStr(A)}</span> &nbsp; <span class="f">Ψ′ = ${detStr(B)}</span>`);
  steps.push(`<b class="h">Приводим Ψ′ к максимальному совпадению</b>`+(al.inv===0?'Одинаковые спин-орбитали уже стоят на одних и тех же местах — переставлять нечего, множитель +1.':
    `Переставляем столбцы так, чтобы одинаковые спин-орбитали стояли на тех же местах, что в Ψ: <span class="f">${detStr(B)} → ${detStr(al.B2)}</span>. Это ${al.inv} транспозици${al.inv===1?'я':al.inv<5?'и':'й'}, множитель (−1)<sup>${al.inv}</sup> = <b>${al.sign>0?'+1':'−1'}</b>.`));
  const nd=r.nd;steps.push(`<b class="h">Сколько спин-орбиталей отличается</b>`+(nd===0?'Ни одной: это диагональный элемент, энергия определителя.':
    `${nd}: `+al.diff.map(([m,p])=>`χ<sub>${lab(m)}</sub> → χ<sub>${lab(p)}</sub>`).join(', ')+'.'));
  const gen=nd===0?'⟨Ψ|Ĥ|Ψ⟩ = Σ<sub>i</sub> h<sub>ii</sub> + Σ<sub>i&lt;j</sub> (⟨ij|ij⟩ − ⟨ij|ji⟩)':nd===1?'⟨Ψ|Ĥ|Ψ′⟩ = h<sub>mp</sub> + Σ<sub>n≠m</sub> (⟨mn|pn⟩ − ⟨mn|np⟩)':nd===2?'⟨Ψ|Ĥ|Ψ′⟩ = ⟨mn|pq⟩ − ⟨mn|qp⟩':'⟨Ψ|Ĥ|Ψ′⟩ = 0';
  let sub='';
  if(nd===0){const t=[];A.forEach(x=>t.push(`h<sub>${lab(x)}</sub>`));for(let i=0;i<A.length;i++)for(let j=i+1;j<A.length;j++)t.push(`(⟨${lab(A[i])}${lab(A[j])}|${lab(A[i])}${lab(A[j])}⟩ − ⟨${lab(A[i])}${lab(A[j])}|${lab(A[j])}${lab(A[i])}⟩)`);sub=t.join(' + ')}
  else if(nd===1){const [m,p]=al.diff[0];sub=`h<sub>${lab(m)},${lab(p)}</sub>`+A.filter(n=>!(n.o===m.o&&n.s===m.s)).map(n=>` + ⟨${lab(m)}${lab(n)}|${lab(p)}${lab(n)}⟩ − ⟨${lab(m)}${lab(n)}|${lab(n)}${lab(p)}⟩`).join('')}
  else if(nd===2){const [[m,p],[n,q]]=al.diff;sub=`⟨${lab(m)}${lab(n)}|${lab(p)}${lab(q)}⟩ − ⟨${lab(m)}${lab(n)}|${lab(q)}${lab(p)}⟩`}
  steps.push(`<b class="h">Общая формула для этого случая</b><span class="f">${gen}</span>`+(sub?`<br>Подставляем спин-орбитали: <span class="f" style="white-space:normal">${sub}</span>`:''));
  if(nd<=2)steps.push(`<b class="h">Интегрируем по спину</b>`+(r.notes.length?r.notes.map(t=>'• '+t).join('<br>'):'Все члены сохраняются: спины везде совпадают.')+'<br><span class="hint">Интеграл по спину равен 1, если у электрона одинаковый спин слева и справа, и 0, если разный.</span>');
  else steps.push(`<b class="h">Почему ноль</b>${r.notes[0]}.`);
  const sg=al.sign<0&&!r.zero?'−(':'',sg2=al.sign<0&&!r.zero?')':'';
  steps.push(`<b class="h">Ответ в пространственных интегралах</b><span class="ans">⟨Ψ|Ĥ|Ψ′⟩ = ${r.expr}</span>`+(al.sign<0&&!r.zero?'<br><span class="hint">знак минус — от перестановки столбцов</span>':'')+
    (Object.keys(r.T).some(k=>k[0]==='c'&&!/^c:(\d),\1\|(\d),\2$/.test(k)&&!/^c:(\d),(\d)\|\1,\2$/.test(k))?'<br><span class="hint">(ab|cd) = ⟨ac|bd⟩ — химическая нотация.</span>':''));
  let h='<ol class="steps">'+steps.map(s=>'<li>'+s+'</li>').join('')+'</ol>';if(preKey&&NOTE[preKey])h+=`<div class="status" style="margin-top:10px">${NOTE[preKey]}</div>`;return h}
const liveEl=QC.live('slater.element');
async function render(){let r={};if(D[0].length&&D[1].length){try{r=fromSrv(await liveEl({A:pairs(D[0]),B:pairs(D[1])}))}catch(e){return}}chipsPre();const box=$('dets');box.innerHTML='';box.appendChild(editor(0,r));box.appendChild(editor(1,r));
  $('sol').innerHTML=hidden?'<p class="small">Решение откроется, когда вы ответите на вопросы ниже.</p>':solution(r)}
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
  const row=(label,opts,key,truth)=>{const v=q[key];return `<div class="qrow"><span class="small" style="min-width:300px">${label}</span>`+opts.map(([val,l])=>`<button class="chip" type="button" data-k="${key}" data-v="${val}" aria-pressed="${v===val}">${l}</button>`).join('')+(v!=null?`<span class="fb ${v===truth?'ok':'no'}">${v===truth?'верно':'неверно'}</span>`:'')+'</div>'};
  let h=row('Сколько спин-орбиталей отличается после приведения?',[[0,'0'],[1,'1'],[2,'2'],[3,'3 и больше']],'a1',truth1)+row('Какой множитель даёт перестановка столбцов?',[[1,'+1'],[-1,'−1']],'a2',truth2);
  if(q.a1!=null&&q.a2!=null)h+=`<div class="status">Ответ: <b>${r.expr}</b>${r.al.sign<0&&!r.zero?' (с учётом знака перестановки)':''}. Полное решение — в разделе «Решение по шагам».</div>`;
  $('quiz').innerHTML=h;$('quiz').querySelectorAll('[data-k]').forEach(b=>b.onclick=()=>{if(q[b.dataset.k]!=null)return;q[b.dataset.k]=+b.dataset.v;
    if(q.a1!=null&&q.a2!=null){score[1]++;if(q.a1===truth1&&q.a2===truth2)score[0]++;hidden=false;render();$('qScore').textContent=`решено верно: ${score[0]} из ${score[1]}`}drawQuiz()})}
$('qNew').onclick=newQuiz;
render();
