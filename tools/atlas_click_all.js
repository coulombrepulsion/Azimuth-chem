// Azimuth 0.87.11: the check of the Atlas before the beta — opens each page of a language, clicks every button, tab,
// chip, check box, summary and every option of each list, and writes what went wrong: JS errors, errors in the console,
// plots left empty after a click. Needs Node with Playwright and the Atlas server on port 8792:
//   python3 -c "from quas_atlas.cli import main; main(['serve','--port','8792','--no-browser'])"   (in modules/atlas/atlas_v2)
//   node tools/atlas_click_all.js ru postulates.html units.html ...      → /tmp/crawl/out-ru.txt, one JSON line per page
// Run one language at a time: three at once load the computer so much that slow plots are reported as empty.
const {chromium}=require('playwright');const fs=require('fs');
(async()=>{fs.mkdirSync('/tmp/crawl',{recursive:true});const [lang,...pages]=process.argv.slice(2);const b=await chromium.launch();
for(const f of pages){let n=-1;const p=await b.newPage({viewport:{width:1280,height:900}});const issues=[];let ctx='load';
 p.on('pageerror',e=>issues.push(['pageerror',ctx,e.message.slice(0,200)]));
 p.on('console',m=>{if(m.type()==='error'&&!/favicon|ERR_|404/.test(m.text()))issues.push(['console',ctx,m.text().slice(0,200)])});
 p.on('dialog',d=>d.dismiss());
 try{await p.goto(`http://127.0.0.1:8792/${lang}/${f}`,{timeout:20000});await p.waitForTimeout(1500);
  n=await p.evaluate(()=>{const sel='main button:not([data-goto]):not(.demoBtn):not(.showA), main input[type=checkbox], main details>summary, main select';
    window.__els=[...document.querySelectorAll(sel)];return window.__els.length});
  for(let i=0;i<n;i++){
   const info=await p.evaluate(async(i)=>{const e=window.__els[i];if(!e||!e.isConnected)return null;
     const label=(e.tagName+':'+(e.id||e.textContent||'').trim()).slice(0,50);
     if(e.tagName==='SELECT'){for(let k=0;k<e.options.length;k++){e.selectedIndex=k;e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));await new Promise(r=>setTimeout(r,60))}}
     else{if(e.closest('details:not([open])')&&e.tagName!=='SUMMARY'){const d=e.closest('details');d.open=true}e.click()}
     return label},i).catch(err=>'ERR '+err.message.slice(0,80));
   ctx=info||('#'+i);await p.waitForTimeout(info&&/SELECT/.test(info)?100:220);
   const empty=await p.evaluate(()=>[...document.querySelectorAll('main svg')].filter(s=>{const r=s.getBoundingClientRect();if(r.width<80||r.height<60)return false;if(s.closest('[hidden],details:not([open])'))return false;
     return !s.querySelector('path,line,circle,rect,polyline,polygon,text,image,use,ellipse')}).map(s=>(s.id||'(svg)')+'#'+s.childElementCount+'@'+s.innerHTML.slice(0,60))).catch(()=>[]);
   empty.forEach(id=>issues.push(['empty-plot',ctx,id]));
  }
 }catch(e){issues.push(['crash',ctx,e.message.slice(0,200)])}
 const uniq=[...new Map(issues.map(x=>[x.join('|'),x])).values()];
 fs.appendFileSync(`/tmp/crawl/out-${lang}.txt`,JSON.stringify({f,els:typeof n!=="undefined"?n:-1,n:uniq.length,issues:uniq.slice(0,30)})+'\n');await p.close()}
await b.close()})();
