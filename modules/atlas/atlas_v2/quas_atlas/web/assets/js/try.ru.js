(function(){
  /* ---------- «Проверьте свои знания»: проверка ответов ---------- */
  function num(s){const m=String(s).replace(/[−–]/g,'-').replace(/\s/g,'').replace(/,/g,'.').match(/-?\d*\.?\d+(e-?\d+)?/i);return m?parseFloat(m[0]):NaN}
  function initTry(){const box=document.querySelector('.try');if(!box||box.dataset.ready)return;box.dataset.ready='1';
    const qs=[...box.querySelectorAll('.tq')],sc=box.querySelector('.tscore');let first=0,done=0;
    function score(){sc.textContent=done?`Верно с первой попытки: ${first} из ${qs.length}`:''}
    qs.forEach(q=>{const fb=q.querySelector('.fb'),ans=q.querySelector('.ans'),sh=q.querySelector('.showA');let tried=false,fin=false;
      function reveal(){ans.hidden=false;sh.hidden=true}
      function finish(ok){if(fin)return;fin=true;if(ok&&!tried){first++}done++;score()}
      sh.onclick=()=>{reveal();finish(false)};
      q.querySelectorAll('.opt').forEach(b=>b.onclick=()=>{const ok=b.dataset.ok==='1';
        q.querySelectorAll('.opt').forEach(o=>{o.disabled=true;if(o.dataset.ok==='1')o.classList.add('ok')});
        if(!ok)b.classList.add('bad');fb.className='fb '+(ok?'ok':'bad');fb.textContent=ok?'Верно!':'Неверно.';finish(ok);reveal()});
      const inp=q.querySelector('.ninp'),chk=q.querySelector('.chk');
      if(inp){const go=()=>{const x=num(inp.value);if(isNaN(x)){fb.className='fb bad';fb.textContent='Введите число.';return}
          const v=+inp.dataset.v,t=+inp.dataset.tol,ok=Math.abs(x-v)<=t+1e-12;
          inp.classList.toggle('ok',ok);inp.classList.toggle('bad',!ok);fb.className='fb '+(ok?'ok':'bad');
          if(ok){fb.textContent='Верно!';finish(true);reveal()}else{fb.textContent='Пока неверно — проверьте ещё раз или откройте ответ.';tried=true}};
        chk.onclick=go;inp.addEventListener('keydown',e=>{if(e.key==='Enter')go()})}
    });score();
    /* задания по одному: «Предыдущее» / «Следующее» */
    let cur=0;const nav=document.createElement('div');nav.className='tnav';
    nav.innerHTML='<button type="button" class="tbtn tprev">← Предыдущее</button><span class="tdots"></span><button type="button" class="tbtn tnext">Следующее →</button>';
    sc.after(nav);const dots=nav.querySelector('.tdots');
    qs.forEach((q,i)=>{const d=document.createElement('button');d.type='button';d.className='tdot';d.setAttribute('aria-label',`Задание ${i+1} из ${qs.length}`);d.onclick=()=>go(i);dots.appendChild(d)});
    function go(i){cur=Math.max(0,Math.min(qs.length-1,i));qs.forEach((q,j)=>q.hidden=j!==cur);[...dots.children].forEach((d,j)=>d.classList.toggle('on',j===cur));
      nav.querySelector('.tprev').disabled=cur===0;nav.querySelector('.tnext').disabled=cur===qs.length-1;react(qs[cur].dataset.st||'n')}
    nav.querySelector('.tprev').onclick=()=>go(cur-1);nav.querySelector('.tnext').onclick=()=>go(cur+1);
    /* Квил рядом с заданиями и его реакции */
    Object.values(TRYQ).flat().forEach(u=>{const i=new Image();i.src=u});/* loaded in advance, no pause at the first answer */
    const tin=box.querySelector('.tryIn'),q=document.createElement('img');q.className='tryQ away';q.alt='';q.setAttribute('aria-hidden','true');tin.prepend(q);
    function react(k){if(!TRYQ[k])return;if(q.dataset.k===k)return;q.dataset.k=k;{const L=[].concat(TRYQ[k]);q.src=L[Math.random()*L.length|0];/* one figure height for every pose */const m=/quill-try-([a-z]+)/.exec(q.src);q.style.setProperty('--k',(TQK[m&&m[1]]||1))}q.classList.remove('pop');void q.offsetWidth;q.classList.add('pop')}
    qs.forEach((qq,i)=>{const mark=st=>{qq.dataset.st=st;dots.children[i].classList.remove('ok','bad','show');dots.children[i].classList.add(st);if(i===cur)react(st)};
      qq.addEventListener('click',e=>{const t=e.target;setTimeout(()=>{const fb=qq.querySelector('.fb');
        if(t.closest('.showA'))mark(qq.dataset.st==='ok'?'ok':'show');
        else if(fb.classList.contains('ok'))mark('ok');else if(fb.classList.contains('bad')&&fb.textContent)mark('bad')},0)});
      const inp=qq.querySelector('.ninp');if(inp)inp.addEventListener('keydown',e=>{if(e.key==='Enter')setTimeout(()=>{const fb=qq.querySelector('.fb');mark(fb.classList.contains('ok')?'ok':'bad')},0)})});
    go(0);
    /* без перелёта Квил из шапки — панель заданий открывается и закрывается на месте */
    const det=box.querySelector('details');
    let busy=0;
    det.addEventListener('toggle',async()=>{const id=++busy;
      if(det.open){/* Quill appears at once, while the page scrolls (she waited 0.45 s for the scroll and seemed to hang) */
        if(!RM)box.scrollIntoView({behavior:'smooth',block:'start'});if(id!==busy)return;
        q.classList.remove('away');react(qs[cur].dataset.st||'n')}
      else q.classList.add('away')});
    /* прокрутили выше заданий — панель сворачивается */
    if('IntersectionObserver' in window)new IntersectionObserver(es=>{for(const e of es)if(!e.isIntersecting&&e.boundingClientRect.top>innerHeight&&det.open)det.open=false},{threshold:0}).observe(box)}
  /* ---------- Демонстрация ---------- */
  const RM=matchMedia('(prefers-reduced-motion: reduce)').matches;
  let lastQ=null,bar=null,btn=null,k=0,run=0,hl=null,spot=null,tgt=null,raf=0,pz=-1,skip=false,left=true;
  const sleep=ms=>new Promise(r=>setTimeout(r,ms));
  function pick(sel,i){const a=document.querySelectorAll(sel);return a[i||0]||null}
  function pressed(e){const v=e.getAttribute('aria-pressed')||e.getAttribute('aria-checked');return v==='true'||e.checked===true}
  /* прокрутка один раз за шаг и минимальная: только если нужная область не видна */
  function reveal(e){if(!e)return;const top=60,bot=innerHeight-170,r=e.getBoundingClientRect();if(r.top>=top&&r.bottom<=bot)return;
    let dy;if(r.height>bot-top||r.top<top)dy=r.top-top;else dy=r.bottom-bot;scrollBy({top:dy,behavior:RM?'auto':'smooth'})}
  function focusArea(e){if(!e)return;const sec=e.closest('section,.panel')||e,h=innerHeight-230;reveal(sec.getBoundingClientRect().height<=h?sec:e)}
  async function setv(e,v){const fire=()=>{e.dispatchEvent(new Event('input',{bubbles:true}))};
    if(e.type==='range'&&!RM){const a=+e.value,n=18;for(let j=1;j<=n;j++){e.value=a+(v-a)*j/n;fire();await sleep(28)}}
    e.value=v;fire();e.dispatchEvent(new Event('change',{bubbles:true}))}
  async function act(st,id){let last=null,scl=null,ls=null;
    for(const x of st.a||[]){if(id!==run)return;const [c,sel]=x;
      if(c==='wait'){await sleep(sel);continue}
      /* what a step needs may still be on its way — the result of the click before it is calculated for seconds in a
         browser; wait for it up to 8 s */
      let e=pick(sel,c==='set'?0:x[2]);for(let w=0;!e&&w<40&&id===run;w++){await sleep(200);e=pick(sel,c==='set'?0:x[2])}
      if(id!==run)return;if(!e){console.warn('demo: missing',sel);continue}
      if(c==='scroll'){const dd=e.closest('details');if(dd&&!dd.open)dd.open=true}
      if(c==='scroll'){leave();e.scrollIntoView({behavior:RM?'auto':'smooth',block:'start'});await sleep(RM?0:450);last=/^H[1-4]$/.test(e.tagName)?e:(e.closest('section')||e);scl=last;continue}
      {const dd=e.closest('details');if(dd&&!dd.open)dd.open=true}
      if(!RM)await sleep(250);
      if(c==='click')e.click();
      else if(c==='on'){if(pressed(e)!==x[3])e.click()}
      else if(c==='set')await setv(e,x[2]);
      last=(c==='set'?e.closest('.crow,.row,label,div')||e:e);ls=[sel,c==='set'?0:x[2],c];await sleep(RM?0:180)}
    if(id!==run)return;
    /* кнопки-переключатели перерисовываются после щелчка: берём элемент заново */
    if(last&&!last.isConnected&&ls){const e=pick(ls[0],ls[1]);last=e?(ls[2]==='set'?e.closest('.crow,.row,label,div')||e:e):null}
    let tg=st.hl?document.querySelector(st.hl):(scl&&last&&!scl.contains(last)&&!(scl.parentElement&&scl.parentElement.contains(last))?scl:last);
    if(tg&&window.qcReveal)tg=window.qcReveal(tg)||tg;
    const L=tg&&tg.tagName==='SECTION'?headBlock(tg.querySelector('h2,h3')||tg):tg&&/^H[1-4]$/.test(tg.tagName)?headBlock(tg):block(tg);
    const same=!left&&tgt&&L.length===tgt.length&&L.every((e,i)=>e===tgt[i]);
    if(!same){leave();const r=urect(L);if(r){const top=70,bot=innerHeight-24;if(r.top<top||r.bottom>bot){const dy=(r.height>bot-top||r.top<top)?r.top-top:r.bottom-bot;scrollBy({top:dy,behavior:RM?'auto':'smooth'})}}
      await settle(L,id);if(id!==run)return;
      aim(L);await sleep(RM?0:80);if(id!==run)return;
      bar.classList.toggle('qr',innerWidth>=640&&k%2===1);await sleep(RM?0:40);
      label();bar.classList.remove('off');left=false;await sleep(RM?0:260);if(id!==run)return}
    mark(tg&&L[0]!==tg?tg:null);
    skip=false;await typeIn(bar.querySelector('b'),st.t,id);await typeIn(bar.querySelector('.dd'),st.d,id)}
  /* Квил улетает с текущего места: облачко и подсветка гаснут */
  function leave(){if(left)return;left=true;
    /* no flight between blocks */
    aim(null);spot&&spot.classList.remove('on');bar.classList.add('off')}
  /* ждём, пока прокрутка закончится и блок перестанет двигаться */
  async function settle(L,id){let pv=null,same=0;for(let i=0;i<50&&id===run;i++){await sleep(RM?0:50);const r=urect(L||[]),y=r?Math.round(r.top):0;if(y===pv){if(++same>=3)break}else same=0;pv=y}}
  /* текст «говорится» посимвольно; разметка (индексы, курсив) сохраняется */
  async function typeIn(el,html,id){el.innerHTML=html;if(RM||skip)return;const T=[],w=document.createTreeWalker(el,NodeFilter.SHOW_TEXT);
    while(w.nextNode())T.push([w.currentNode,w.currentNode.data]);T.forEach(x=>x[0].data='');
    for(const [n,t] of T){for(let i=1;i<=t.length;i++){if(id!==run)return;if(skip){T.forEach(x=>x[0].data=x[1]);return}n.data=t.slice(0,i);await sleep(/[.,:;!?—。，；：！？]/.test(t[i-1])?45:8)/* twice as fast */}}}
  /* блок для подсветки: самый крупный предок, который ещё помещается в 60 % высоты окна */
  function block(e){if(!e)return [];let b=e;const lim=innerHeight*.86;
    for(let p=e.parentElement;p&&p!==document.body;p=p.parentElement){if(p.tagName==='SECTION'||p.tagName==='MAIN')break;const r=p.getBoundingClientRect();if(r.height>lim||r.width>innerWidth-8)break;b=p}
    /* добавляем следующие за блоком график или таблицу, если всё вместе помещается */
    const L=[b],t=b.getBoundingClientRect().top,l2=innerHeight*.86;
    for(let n=b.nextElementSibling;n;n=n.nextElementSibling){const r=n.getBoundingClientRect();if(!r.height)continue;if(r.bottom-t>l2)break;L.push(n);if(/^(svg|canvas|figure|table|div)$/i.test(n.tagName)&&r.height>120)break}
    return withViz(L)}
  /* если подсвечены одни настройки, добавляем график или схему, которыми они управляют */
  const VIZ='svg,canvas,img:not(.qPose):not(.tryQ),table,.mtab';
  function withViz(L){if(!L.length||L.some(e=>e.matches(VIZ)||e.querySelector(VIZ)))return L;
    const lim=innerHeight*.9,u=urect(L);if(!u)return L;let V=null;
    /* only inside the same section — the next section, «Следующий вопрос» and «Проверьте свои знания» were lit too */
    for(let a=L[L.length-1],lv=0;a&&a!==document.body&&lv<4&&!V&&!a.matches('section,.panel,main,aside');a=a.parentElement,lv++){
      for(let n=a.nextElementSibling,c=0;n&&c<3;n=n.nextElementSibling,c++){if(n.matches('section,.panel,aside,.try,.nextQ'))break;if(n.matches(VIZ)||n.querySelector(VIZ)){V=n;break}}}
    if(!V)return L;const r=V.getBoundingClientRect();
    if(Math.max(u.bottom,r.bottom)-Math.min(u.top,r.top)<=lim)return [...L,V];
    if(r.height<=lim)return [V];
    const g=V.querySelector('svg,canvas');return g&&g.getBoundingClientRect().height<=lim?[g]:L}
  /* заголовок раздела вместе со следующими блоками, пока они помещаются */
  function headBlock(h){const L=[h],lim=innerHeight*.72;let t=h.getBoundingClientRect().top;
    for(let n=h.nextElementSibling;n;n=n.nextElementSibling){const r=n.getBoundingClientRect();if(r.bottom-t>lim)break;L.push(n)}return L}
  function urect(L){let a=1e9,b=1e9,c=-1e9,d=-1e9;for(const e of L){const r=e.getBoundingClientRect();if(!r.width&&!r.height)continue;a=Math.min(a,r.left);b=Math.min(b,r.top);c=Math.max(c,r.right);d=Math.max(d,r.bottom)}return c<a?null:{left:a,top:b,right:c,bottom:d,width:c-a,height:d-b}}
  function pose(i){if(i===pz)return;pz=i;const q=bar.querySelector('.dq'),L=PRQ[i];if(!q||!L)return;const c=L.filter(u=>u!==q.getAttribute('src')),C=c.length?c:L;q.src=C[Math.random()*C.length|0]}
  function dock(){bar.style.top='auto';bar.style.bottom='12px';bar.style.left=Math.max(8,(innerWidth-bar.offsetWidth)/2)+'px';pose(bar.classList.contains('qr')?4:1)}
  function place(){raf=requestAnimationFrame(place);if(!bar||!spot)return;if(bar.classList.contains('off')&&!tgt)return;/* 2.16.0: she fades where she was */const r=tgt&&urect(tgt);
    if(!r){spot.classList.remove('on');dock();return}
    const p=8,m=12,vw=innerWidth,vh=innerHeight;spot.classList.add('on');
    spot.style.top=(r.top-p)+'px';spot.style.left=(r.left-p)+'px';spot.style.width=(r.width+2*p)+'px';spot.style.height=(r.height+2*p)+'px';
    if(vw<640){dock();return}
    const bh=bar.offsetHeight,bw=bar.offsetWidth,R=bar.classList.contains('qr');let top;
    if(r.bottom+p+m+bh<=vh-m)top=r.bottom+p+m;else if(r.top-p-m-bh>=m)top=r.top-p-m-bh;else top=vh-bh-m;
    top=Math.min(Math.max(m,top),vh-bh-m);const left=R?Math.min(Math.max(m,r.right+p-bw),vw-bw-m):Math.min(Math.max(m,r.left-p),vw-bw-m);
    bar.style.bottom='auto';bar.style.top=top+'px';bar.style.left=left+'px';
    /* указка смотрит на центр блока: вверх, вниз или вбок */
    const cy=Math.max(r.top,0)/2+Math.min(r.bottom,vh)/2,qy=top+bh*.55,d=cy-qy;pose((R?3:0)+(d<-70?1:d>70?2:0))}
  function aim(L){tgt=L&&L.length?L:null}
  function mark(e){if(hl)hl.classList.remove('demo-hl');hl=null;if(e&&e.tagName!=='SECTION'){hl=e;e.classList.add('demo-hl')}}
  /* 2.16.0: the step number and the buttons change when Quill appears at the next place, not before she leaves */
  function label(){const D=window.DEMO,st=D[k];
    bar.querySelector('.dn').textContent=`Демонстрация · шаг ${k+1} из ${D.length}`;
    /* the bubble takes the size of the whole text before typing — Quill no longer moves while she speaks */
    {const x=bar.querySelector('.dtx'),bb=bar.querySelector('b'),dd=bar.querySelector('.dd');x.style.minHeight=x.style.width='';bb.innerHTML=st.t;dd.innerHTML=st.d;const r=x.getBoundingClientRect();x.style.width=Math.ceil(r.width)+'px';x.style.minHeight=Math.ceil(r.height)+'px'}
    bar.querySelector('b').innerHTML='';bar.querySelector('.dd').innerHTML='';{const t=document.createElement('div');t.innerHTML=st.t+'. '+st.d;bar.querySelector('.sr').textContent=t.textContent}
    bar.querySelector('.pv').disabled=k===0;const nx=bar.querySelector('.nx');nx.textContent=k===D.length-1?'✓':'▶';nx.title=k===D.length-1?'Завершить':'Далее';}
  function show(){const D=window.DEMO,st=D[k];run++;pz=-1;leave();
    act(st,run)}
  function key(e){if(!bar)return;const t=e.target.tagName;if(/INPUT|TEXTAREA|SELECT/.test(t)&&e.key!=='Escape')return;
    if(e.key==='ArrowRight'||e.key==='PageDown'){e.preventDefault();next()}else if(e.key==='ArrowLeft'||e.key==='PageUp'){e.preventDefault();prev()}else if(e.key==='Escape')stop()}
  function next(){if(k<window.DEMO.length-1){k++;show()}else stop()}
  function prev(){if(k>0){k--;show()}}
  function stop(){run++;mark(null);cancelAnimationFrame(raf);tgt=null;
    if(spot){spot.remove();spot=null}if(bar){bar.remove();bar=null}lastQ=null;document.body.classList.remove('demoOn');btn.classList.remove('on');btn.textContent=btn.textContent.replace('■','▶');btn.setAttribute('aria-pressed','false');tellHub(false);btn.focus()}
  /* the button of the demonstration glows while it runs and stops it; the hub's button too */
  /* the window or the section of the hub is left (the page is hidden): the demonstration stops for real, and the
     buttons go out */
  document.addEventListener('visibilitychange',()=>{if(document.hidden&&bar)stop()});
  function tellHub(on){try{if(parent!==window)parent.postMessage({qcDemoOn:on},'*')}catch(e){}}
  const TQK={"board":1.1,"clap":1.107,"oops":1.111,"pencil":1.124,"puzzled":1.04,"reading":1.107},PRQ=[["../assets/img/quill-demo-present-r-20261026-g.webp"], ["../assets/img/quill-demo-up-r-20261026-g.webp"], ["../assets/img/quill-demo-down-r-20261026-g.webp"], ["../assets/img/quill-demo-present-l-20261026-g.webp"], ["../assets/img/quill-demo-up-l-20261026-g.webp"], ["../assets/img/quill-demo-down-l-20261026-g.webp"]],TRYQ={"n": ["../assets/img/quill-try-think-20261026-g.webp", "../assets/img/quill-try-present-20261026-g.webp"], "ok": ["../assets/img/quill-try-success-20261026-g.webp", "../assets/img/quill-try-thumb-20261027-g.webp", "../assets/img/quill-try-clap-20261031-g.webp"], "bad": ["../assets/img/quill-try-puzzled-20261031-g.webp", "../assets/img/quill-try-pencil-20261031-g.webp", "../assets/img/quill-try-oops-20261031-g.webp", "../assets/img/quill-try-hint-20261027-g.webp"], "show": ["../assets/img/quill-try-reading-20261031-g.webp", "../assets/img/quill-try-board-20261027-g.webp"]};
  function start(){k=0;bar=document.createElement('div');bar.className='demoBar';bar.setAttribute('role','dialog');bar.setAttribute('aria-label','Демонстрация');
    bar.innerHTML='<img class="dq" alt="" aria-hidden="true" src=""><div class="bub"><div class="dtx"><span class="sr" aria-live="polite"></span><span class="dn"></span><b></b><span class="dd"></span></div><div class="dctl"><button type="button" class="pv">◀</button><button type="button" class="nx">▶</button><button type="button" class="cl">✕</button></div></div>';
    bar.querySelector('.pv').title='Назад';bar.querySelector('.cl').title='Закрыть';
    bar.querySelector('.dtx').onclick=()=>{skip=true};bar.querySelector('.pv').onclick=prev;bar.querySelector('.nx').onclick=next;bar.querySelector('.cl').onclick=stop;
    bar.classList.add('off');left=true;spot=document.createElement('div');spot.className='demoSpot';spot.setAttribute('aria-hidden','true');document.body.appendChild(spot);document.body.appendChild(bar);document.body.classList.add('demoOn');pz=-1;cancelAnimationFrame(raf);place();btn.classList.add('on');btn.textContent=btn.textContent.replace('▶','■');btn.setAttribute('aria-pressed','true');tellHub(true);show();bar.querySelector('.nx').focus()}
  function initDemo(){if(!window.DEMO||btn)return;btn=document.createElement('button');btn.type='button';btn.className='demoBtn';btn.textContent='▶ Демонстрация';
    btn.title='Пошаговый показ возможностей страницы (стрелки ← → , Esc — выход)';btn.onclick=()=>bar?stop():start();document.body.appendChild(btn);document.addEventListener('keydown',key)}
  /* переход из поиска хаба к разделу страницы */
  addEventListener('message',e=>{const g=e.data&&e.data.qcGo;if(!g)return;let el=g.id?document.getElementById(g.id):null;
    if(g.text){const n=t=>t.replace(/\s+/g,' ').trim();const tx=n(g.text);const c=[...document.querySelectorAll('h2,h3,h4,li,.qt,p,dd,dt,.t,.l,button')].find(x=>n(x.textContent).slice(0,400)===tx);if(c)el=c}
    if(!el)return;el=window.qcReveal(el)||el;const d=el.closest('details');if(d&&!d.open)d.open=true;
    const tq=el.closest('.tq');if(tq&&tq.hidden){const qs=[...document.querySelectorAll('.try .tq')],dt=document.querySelectorAll('.tdot')[qs.indexOf(tq)];dt&&dt.click()}
    setTimeout(()=>{el.scrollIntoView({behavior:RM?'auto':'smooth',block:'center'});el.classList.remove('qcFound');void el.offsetWidth;el.classList.add('qcFound')},d?500:0)});
  /* ---------- корень: знак радикала с чертой над всем подкоренным выражением ---------- */
  const RSVG='<svg viewBox="0 0 60 100" preserveAspectRatio="none" aria-hidden="true"><path d="M2 58 L14 51 L30 96 L58 1 L62 1" fill="none" stroke="currentColor" stroke-width="7" stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke" style="stroke-width:.07em"/></svg>';
  const RSKIP='script,style,svg,textarea,option,select,title,code,pre,.rt,input';
  const RTOK=/^[0-9A-Za-zͰ-Ͽ₀-ₜ²³¹⁰-ⁿ]+(?:[.,][0-9]+)?/;
  function mkRoot(open,close){const rt=document.createElement('span');rt.className='rt';rt.innerHTML='<span class="rq">√'+open+'</span>'+RSVG+'<span class="ri"></span>'+(close?'<span class="rq">'+close+'</span>':'');return rt}
  function rootOne(t){const i=t.data.indexOf('√');if(i<0)return false;const rest=t.data.slice(i+1),R=document.createRange();
    if(rest[0]==='('){/* ищем закрывающую скобку: в этом же тексте или в следующих узлах того же уровня */
      let dep=0,node=t,off=i+1,endN=null,endO=-1;
      while(node&&!endN){if(node.nodeType===3){const d=node.data;for(let j=(node===t?off:0);j<d.length;j++){const c=d[j];if(c==='(')dep++;else if(c===')'){dep--;if(dep===0){endN=node;endO=j;break}}}}
        if(!endN)node=node.nextSibling}
      if(!endN)return 'skip';
      R.setStart(t,i+2);R.setEnd(endN,endO);const frag=R.extractContents();const rt=mkRoot('(',')');rt.querySelector('.ri').append(frag);
      /* t теперь кончается на «√(», endN (если это другой узел) начинается с «)» */
      const after=endN===t?t.splitText(i+2):endN;after.data=after.data.replace(/^\)/,'');t.data=t.data.slice(0,i);t.after(rt);return true}
    const m=rest.match(RTOK);
    if(m){const tail=t.splitText(i);tail.data=tail.data.slice(1);const rest2=tail.splitText(m[0].length);const rt=mkRoot('','');rt.querySelector('.ri').append(tail);rest2.before(rt);return true}
    if(rest===''&&t.nextSibling&&t.nextSibling.nodeType===1&&!t.nextSibling.matches(RSKIP)){const el=t.nextSibling;t.data=t.data.slice(0,i);const rt=mkRoot('','');el.before(rt);rt.querySelector('.ri').append(el);return true}
    return 'skip'}
  function initRoots(){const root=document.querySelector('main')||document.body;if(!root)return;let busy=false;
    const pass=()=>{busy=true;try{for(let guard=0;guard<400;guard++){const w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,{acceptNode:n=>n.data.indexOf('√')>=0&&!(n.parentElement&&n.parentElement.closest(RSKIP))&&!n._rs?NodeFilter.FILTER_ACCEPT:NodeFilter.FILTER_REJECT});
        const n=w.nextNode();if(!n)break;const r=rootOne(n);if(r==='skip')n._rs=1}}catch(e){console.warn(e)}busy=false};
    pass();let pend=false;new MutationObserver(()=>{if(busy||pend)return;pend=true;requestAnimationFrame(()=>{pend=false;pass()})}).observe(root,{childList:true,subtree:true,characterData:true})}
  /* ---------- длинный текст: карточки-вкладки и сворачиваемые пояснения ---------- */
  const FOLDT={ru:['\u041f\u043e\u0434\u0440\u043e\u0431\u043d\u0435\u0435 \u25be','\u0421\u0432\u0435\u0440\u043d\u0443\u0442\u044c \u25b4'],en:['More \u25be','Less \u25b4'],zh:['\u5c55\u5f00 \u25be','\u6536\u8d77 \u25b4']};
  function initFold(){const lg=(document.documentElement.lang||'ru').slice(0,2),T=FOLDT[lg]||FOLDT.ru;
    document.querySelectorAll('main .eq').forEach((g,gi)=>{const B=[...g.children].filter(x=>x.classList.contains('eqb'));
      if(B.length<3||!B.every(b=>b.querySelector(':scope>.t')))return;g.classList.add('eqTabs');
      const nav=document.createElement('div');nav.className='eqNav';nav.setAttribute('role','tablist');
      const sel=(i,f)=>{B.forEach((b,j)=>b.classList.toggle('on',j===i));[...nav.children].forEach((x,j)=>{x.setAttribute('aria-selected',j===i?'true':'false');x.tabIndex=j===i?0:-1});if(f)nav.children[i].focus()};
      B.forEach((b,i)=>{const bt=document.createElement('button');bt.type='button';bt.className='eqTab';bt.setAttribute('role','tab');bt.id='eqT'+gi+'_'+i;bt.textContent=b.querySelector(':scope>.t').textContent;
        if(!b.id)b.id='eqP'+gi+'_'+i;b.setAttribute('role','tabpanel');b.setAttribute('aria-labelledby',bt.id);bt.setAttribute('aria-controls',b.id);bt.onclick=()=>sel(i);nav.appendChild(bt)});
      nav.addEventListener('keydown',e=>{const i=[...nav.children].indexOf(document.activeElement);if(i<0)return;let j=-1;
        if(e.key==='ArrowRight')j=(i+1)%B.length;else if(e.key==='ArrowLeft')j=(i-1+B.length)%B.length;else if(e.key==='Home')j=0;else if(e.key==='End')j=B.length-1;
        if(j>=0){e.preventDefault();e.stopPropagation();sel(j,true)}});
      g.prepend(nav);g._sel=sel;sel(0)});
    const ro=window.ResizeObserver?new ResizeObserver(es=>es.forEach(x=>x.target._chk&&x.target._chk())):null;
    document.querySelectorAll('main p.small, main p.hint, main div.small').forEach(p=>{if(p.closest('.try,.nextQ,.limits,.eqb,.demoBar,figure figcaption'))return;
      const b=document.createElement('button');b.type='button';b.className='foldB';b.hidden=true;b.textContent=T[0];b.setAttribute('aria-expanded','false');
      p.classList.add('fold');p.after(b);
      const tog=o=>{p.classList.toggle('open',o);b.textContent=o?T[1]:T[0];b.setAttribute('aria-expanded',o?'true':'false')};
      b.onclick=()=>tog(!p.classList.contains('open'));p._tog=tog;
      p._chk=()=>{if(p.classList.contains('open')){b.hidden=p.textContent.length<300&&!p.querySelector('table,svg,canvas');return}
        if(p.querySelector('table,svg,canvas,img')){p.classList.remove('fold');b.hidden=true;return}
        /* one or two more lines are not worth folding — then the text is shown whole */
        p.classList.remove('nofold');const lh=parseFloat(getComputedStyle(p).lineHeight)||20,extra=p.scrollHeight-p.clientHeight;
        if(extra>4&&extra<=lh*2.2){p.classList.add('nofold');b.hidden=true;return}
        b.hidden=!(extra>4)};
      p._chk();ro&&ro.observe(p);new MutationObserver(()=>{p.classList.add('fold');requestAnimationFrame(p._chk)}).observe(p,{childList:true,subtree:true,characterData:true})})}
  window.qcReveal=function(el){if(!el)return el;if(el.matches('.eqTab')){el.click();return document.getElementById(el.getAttribute('aria-controls'))||el}const d=el.closest('details');if(d&&!d.open)d.open=true;
    const pn=el.closest('.eqTabs>.eqb');if(pn){const g=pn.parentElement;if(!pn.classList.contains('on')&&g._sel)g._sel([...g.children].filter(x=>x.classList.contains('eqb')).indexOf(pn));if(el.matches('.t'))el=pn}
    const f=el.closest('.fold');if(f&&f._tog&&!f.classList.contains('open'))f._tog(true);return el};
  /* ---------- глоссарий: термины пунктиром, по щелчку — определение ---------- */
  let glPop=null;
  function glClose(){if(glPop){glPop.remove();glPop=null}}
  function glOpen(sp){const D=window.QC_GL,it=D.items[+sp.dataset.g];glClose();glPop=document.createElement('div');glPop.className='glPop';glPop.setAttribute('role','dialog');
    const esc=t=>t.replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
    glPop.innerHTML='<div class="glH">'+esc(it[1])+'</div><div class="glD">'+esc(it[3])+'</div>'+(it[4]!==window.QC_GL_SELF&&it[6]?'<a class="glA" href="'+it[5]+'" data-goto="'+it[4]+'">'+esc(D.ui[0])+': '+esc(it[6])+' →</a>':'');
    document.body.appendChild(glPop);const r=sp.getBoundingClientRect(),w=glPop.offsetWidth,h=glPop.offsetHeight;
    let x=r.left+scrollX,y=r.bottom+scrollY+8;x=Math.min(Math.max(8+scrollX,x),scrollX+innerWidth-w-8);if(r.bottom+h+12>innerHeight&&r.top>h+12)y=r.top+scrollY-h-8;
    glPop.style.left=x+'px';glPop.style.top=y+'px'}
  function initGloss(){const D=window.QC_GL,root=document.querySelector('main');if(!D||!root||root.dataset.gl)return;root.dataset.gl='1';
    const skip='h1,h2,h3,h4,a,button,label,input,textarea,select,svg,code,pre,script,style,summary,nav,.grp,.demoBar,.gl,.glPop,.chip,.nqA,.limits dt,[data-nogl]';
    D.items.forEach((it,i)=>{let re;try{re=new RegExp(it[2],'iu')}catch(e){return}
      const w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,{acceptNode:n=>n.parentElement&&!n.parentElement.closest(skip)&&n.data.trim()?1:2});
      for(let n=w.nextNode();n;n=w.nextNode()){const m=re.exec(n.data);if(!m||!m[0])continue;
        const a=n.splitText(m.index);a.splitText(m[0].length);const sp=document.createElement('span');sp.className='gl';sp.dataset.g=i;sp.tabIndex=0;sp.setAttribute('role','button');sp.setAttribute('aria-haspopup','dialog');sp.title=it[1];
        a.parentNode.replaceChild(sp,a);sp.appendChild(a);break}});
    document.addEventListener('click',e=>{const sp=e.target.closest&&e.target.closest('.gl');if(sp){e.preventDefault();glPop&&glPop.dataset.for===sp.dataset.g?glClose():(glOpen(sp),glPop.dataset.for=sp.dataset.g);return}if(glPop&&!glPop.contains(e.target))glClose()});
    document.addEventListener('keydown',e=>{if(e.key==='Escape')glClose();else if((e.key==='Enter'||e.key===' ')&&e.target.classList&&e.target.classList.contains('gl')){e.preventDefault();glOpen(e.target);glPop.dataset.for=e.target.dataset.g}})}
  addEventListener('message',e=>{const d=e.data&&e.data.qcDemo;if(!d||!btn)return;if(d==='toggle')bar?stop():start();else if(d===-1){if(bar)stop()}else if(!bar)start()});
  /* ---------- «Проверьте себя» (тренажёр со случайными заданиями): ответы выбираются, а не вводятся ----------
     The page keeps its own check: a choice is written into the (now hidden) field, «Проверить» checks the fields as
     before, and the colour of a field is copied onto the chosen option. The correct answers come from the page
     (window.qcSelf(): one string per field, as «Показать решение» writes them); three distractors per field are typical
     slips: a neighbouring integer, a factor of two, a neighbouring letter of L, J one step off. */
  function initSelf(){const box=document.querySelector('.selfBox'),quiz=box&&box.querySelector('.quiz');
    if(!quiz||typeof window.qcSelf!=='function'||quiz.dataset.mcq)return;quiz.dataset.mcq='1';quiz.classList.add('mcq');
    const fields=[...quiz.querySelectorAll('input')],res=box.querySelector('#qRes'),q=box.querySelector('.row b[id]');
    const rows=fields.map(inp=>{const o=document.createElement('div');o.className='opts';o.setAttribute('role','group');inp.after(o);return o});
    const st=box.querySelector('.qmsg')||document.createElement('span');
    function norm(s){return String(s).replace(/[−–]/g,'-').replace(/\s/g,'').replace(',','.')}
    function distract(s){s=String(s).trim();const minus=/−/.test(s)?'−':'-',sep=/,/.test(s)?',':'.';
      if(/^[A-Z]$/.test(s)){const L='SPDFGHIK',i=Math.max(0,L.indexOf(s)),c=[];for(const d of[1,-1,2,-2,3])if(L[i+d])c.push(L[i+d]);return c}
      const half=/\//.test(s),x=half?(()=>{const m=norm(s).match(/(-?\d+)\/(\d+)/);return m?m[1]/m[2]:NaN})():parseFloat(norm(s));if(!isFinite(x))return[];
      const dec=(norm(s).split('.')[1]||'').length;
      const out=v=>{if(half||(Math.abs(v*2-Math.round(v*2))<1e-9&&/\//.test(s))){const k=Math.round(v*2);return k%2?(k<0?minus:'')+Math.abs(k)+'/2':String(k/2)}
        const t=Math.abs(v).toFixed(dec).replace('.',sep);return (v<-1e-12&&+t.replace(',','.')!==0?minus:'')+t};
      let c;
      if(half)c=[x-1,x+1,x+2,x-0.5,x+0.5];
      else if(!dec){c=x<=4?[x+1,x-1,x+2,x-2,x+3]:[x-1,x+1,2*x,Math.round(x/2),x+2];if(x>=0)c=c.filter(v=>v>=0)}
      else if(dec===1&&Math.abs(x*2-Math.round(x*2))<1e-9)c=[x-0.5,x+0.5,x+1,x-1];
      else if(dec===1)c=[x-0.4,x+0.4,x-0.8,x+0.6];
      else c=[x*2,x/2,x*4,x/4];
      if(half||(!dec&&x>=0)||x>0)c=c.filter(v=>v>=0);
      const seen=new Set([out(x)]),r=[];for(const v of c){const t=out(v);if(!seen.has(t)){seen.add(t);r.push(t)}}return r}
    function shuffle(a){for(let i=a.length-1;i>0;i--){const j=Math.random()*(i+1)|0;[a[i],a[j]]=[a[j],a[i]]}return a}
    let gen=0;
    async function build(){const my=++gen;let ans;try{ans=await window.qcSelf()}catch(e){return}if(my!==gen||!ans)return;
      fields.forEach((inp,i)=>{const right=String(ans[i]),ds=distract(right);
        const pool=ds.slice(0,2).concat(shuffle(ds.slice(2)).slice(0,1));
        const opts=shuffle([right].concat(pool)),row=rows[i];row.innerHTML='';inp.value='';inp.className='';
        opts.forEach(t=>{const b=document.createElement('button');b.type='button';b.className='opt';b.textContent=t;
          b.onclick=()=>{row.querySelectorAll('.opt').forEach(o=>o.classList.remove('sel','ok','bad'));b.classList.add('sel');inp.value=t;inp.className=''};row.appendChild(b)})})}
    /* the page colours the fields; the chosen option takes the colour, «Показать решение» marks the right ones */
    const sync=inp=>{const row=rows[fields.indexOf(inp)],v=norm(inp.value);row.querySelectorAll('.opt').forEach(o=>{
        const mine=v!==''&&norm(o.textContent)===v;if(inp.classList.contains('ok')&&mine){o.classList.add('ok','sel')}
        else if(inp.classList.contains('bad')&&mine)o.classList.add('bad');
        else if(!mine)o.classList.remove('sel','ok','bad')})};
    const mo=new MutationObserver(ms=>ms.forEach(m=>sync(m.target)));fields.forEach(f=>mo.observe(f,{attributes:true,attributeFilter:['class']}));
    if(res){const p=res.textContent;if(/Введите|Enter|输入/.test(p))res.textContent='Выберите ответы и нажмите «Проверить».'}
    if(q)new MutationObserver(()=>setTimeout(()=>{build();if(res&&/Введите|Enter|输入/.test(res.textContent))res.textContent='Выберите ответы и нажмите «Проверить».'},0)).observe(q,{childList:true,characterData:true,subtree:true});
    if(q&&q.textContent.trim())build()}
  function init(){initTry();try{initSelf()}catch(e){console.warn(e)}initDemo();try{initFold()}catch(e){console.warn(e)}try{initRoots()}catch(e){console.warn(e)}setTimeout(initGloss,400)}
  /* v2: start once the first calculations are drawn (as v1 did on its synchronously drawn page) */
  const go=()=>{if(window.QC&&QC.idle)QC.idle().then(init);else init()};
  if(document.readyState==='loading')addEventListener('DOMContentLoaded',go);else go();
})();
