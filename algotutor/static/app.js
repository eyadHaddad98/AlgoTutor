'use strict';
const $ = id => document.getElementById(id);
const state = {catalog: [], busy: false};
const routes = {rag: 'חיפוש בהרצאות · RAG', tools: 'כלי חישוב · Tools', direct: 'שיחה · LLM'};
const eventNames = {visit:'ביקור בצומת', settle:'קביעת מרחק סופי', relax_pass:'סבב הרפיה', intermediate:'צומת ביניים', accept:'בחירת קשת', reject_cycle:'דחייה: נוצר מעגל', discover:'גילוי צומת', finish:'סיום צומת', augment:'הגדלת זרימה', union:'איחוד קבוצות', find:'מציאת נציג', scan:'סריקת שכנים'};

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
async function api(path, body) {
  const response = await fetch(path, body === undefined ? {credentials:'same-origin'} : {
    method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)
  });
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || value.output?.error || 'הבקשה לא הושלמה.');
  return value;
}
function toast(message) {
  $('toast').textContent = message; $('toast').hidden = false;
  clearTimeout(state.toastTimer); state.toastTimer = setTimeout(() => {$('toast').hidden = true;}, 6000);
}
function showLabError(message) {$('lab-error').textContent = message; $('lab-error').hidden = !message;}
function jsonDetails(data, caption='נתונים מלאים · JSON') {
  const details = el('details'); details.append(el('summary','',caption));
  const pre = el('pre','',JSON.stringify(data, null, 2)); pre.dir='ltr'; details.append(pre); return details;
}
function updateVertexOptions() {
  const names = $('vertices').value.split(',').map(x=>x.trim()).filter(Boolean);
  for (const id of ['source','sink']) {
    const value = $(id).value; $(id).replaceChildren();
    names.forEach(name => {const o=el('option','',name);o.value=name;$(id).append(o);});
    if (names.includes(value)) $(id).value=value;
  }
}
function formArguments() {
  const vertices = $('vertices').value.split(',').map(x=>x.trim()).filter(Boolean);
  const edges = $('edges').value.split('\n').filter(x=>x.trim()).map((line,i)=>{
    const parts=line.trim().split(/[\s,]+/);
    if (parts.length<2 || parts.length>3) throw new Error(`שורה ${i+1}: הזינו מקור, יעד ומשקל.`);
    const weight=parts.length===3?Number(parts[2]):1;
    if (!Number.isFinite(weight)) throw new Error(`שורה ${i+1}: המשקל אינו מספר תקין.`);
    return {from:parts[0],to:parts[1],weight};
  });
  const args={graph:{vertices,edges,directed:$('directed').checked}};
  const name=$('algorithm').value;
  if (['bfs','dijkstra','bellman_ford','prim','dfs','ford_fulkerson','edmonds_karp'].includes(name)) args.source=$('source').value;
  if (['ford_fulkerson','edmonds_karp'].includes(name)) args.sink=$('sink').value;
  return args;
}
function currentArguments() {
  if ($('json-details').open || $('algorithm').value==='union_find') {
    try {const args=JSON.parse($('json-input').value);if (!args || Array.isArray(args) || typeof args!=='object') throw new Error();return args;}
    catch {throw new Error('קלט ה־JSON אינו תקין. בדקו פסיקים, מירכאות וסוגריים.');}
  }
  return formArguments();
}
function syncPreview() {
  if ($('algorithm').value==='union_find') return;
  try {
    const args=formArguments();
    if (!$('json-details').open) $('json-input').value=JSON.stringify(args,null,2);
    drawGraph($('graph-preview'),args.graph);
    $('graph-kind').textContent=args.graph.directed?'גרף מכוון':'גרף לא מכוון';
  } catch { /* Keep the previous preview while a line is being edited. */ }
}
function loadExample() {
  const algorithm=state.catalog.find(x=>x.name===$('algorithm').value);
  if (!algorithm) return;
  const args=algorithm.example, uf=algorithm.name==='union_find';
  $('graph-editor').hidden=uf; $('json-details').open=uf;
  $('json-input').value=JSON.stringify(args,null,2);
  $('algorithm-hint').textContent=`הרצאה ${algorithm.lecture} · `+({graph_scan:'צמתים, קשתות ורשימות שכנות',bfs:'מרחקים לפי מספר קשתות, ללא שימוש במשקלים',dijkstra:'מרחקים ומסלולים · משקלים אי־שליליים',bellman_ford:'גם עם משקל שלילי · כולל בדיקת מעגלים שליליים',floyd_warshall:'מרחקים בין כל זוג צמתים',prim:'עץ פורש מינימלי · גרף לא מכוון וקשיר',kruskal:'עץ פורש מינימלי · גרף לא מכוון וקשיר',union_find:'איחוד קבוצות ומציאת נציג',dfs:'יער חיפוש וזמני גילוי וסיום',biconnected:'גרף לא מכוון · צמתי הפרדה ורכיבים דו־קשירים',ford_fulkerson:'זרימה וחתך מינימלי · קיבולות שלמות 0–50',edmonds_karp:'מסלולי הגדלה באמצעות BFS · קיבולות שלמות 0–50'}[algorithm.name]);
  if (!uf) {
    $('vertices').value=args.graph.vertices.join(', ');
    $('edges').value=args.graph.edges.map(e=>`${e.from} ${e.to} ${e.weight}`).join('\n');
    $('directed').checked=args.graph.directed; updateVertexOptions();
    $('source').value=args.source||args.graph.vertices[0]; $('sink').value=args.sink||args.graph.vertices.at(-1);
    $('source').parentElement.hidden=!['bfs','dijkstra','bellman_ford','prim','dfs','ford_fulkerson','edmonds_karp'].includes(algorithm.name);
    $('sink-field').hidden=!['ford_fulkerson','edmonds_karp'].includes(algorithm.name); syncPreview();
  }
  showLabError(''); $('lab-result').replaceChildren();
}
function svgNode(tag,attrs) {
  const node=document.createElementNS('http://www.w3.org/2000/svg',tag);
  for(const [k,v] of Object.entries(attrs||{})) node.setAttribute(k,String(v));
  return node;
}
let graphSerial=0;
function drawGraph(container,graph,step={}) {
  container.replaceChildren();
  if (!graph || !Array.isArray(graph.vertices) || !Array.isArray(graph.edges) || graph.vertices.length>16) return;
  const svg=svgNode('svg',{viewBox:'0 0 420 210',role:'img','aria-label':'תצוגת הגרף ושלב האלגוריתם'});
  const positions=new Map(), n=graph.vertices.length;
  graph.vertices.forEach((v,i)=>{const a=-Math.PI/2+i*2*Math.PI/n;positions.set(v,{x:210+Math.cos(a)*138,y:106+Math.sin(a)*76});});
  const markerId=`arrow-${++graphSerial}`;
  const defs=svgNode('defs'), marker=svgNode('marker',{id:markerId,viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:5,markerHeight:5,orient:'auto-start-reverse'});
  marker.append(svgNode('path',{d:'M0 0L10 5L0 10z',fill:'#7f9e8d'}));defs.append(marker);svg.append(defs);
  const activeEdges=new Set(step.selected_edge_ids||step.relaxed_edge_ids||[]);
  if(step.edge) activeEdges.add(step.edge.id);
  if(step.arcs) step.arcs.forEach(a=>activeEdges.add(a.edge_id));
  graph.edges.forEach((edge,i)=>{
    const from=positions.get(edge.from), to=positions.get(edge.to);if(!from||!to)return;
    const dx=to.x-from.x,dy=to.y-from.y,d=Math.hypot(dx,dy)||1;
    const parallel=graph.directed && graph.edges.some(e=>e.from===edge.to&&e.to===edge.from&&e!==edge);
    const x1=from.x+dx/d*17,y1=from.y+dy/d*17,x2=to.x-dx/d*20,y2=to.y-dy/d*20;
    const offset=parallel?18:0,mx=(from.x+to.x)/2-dy/d*offset,my=(from.y+to.y)/2+dx/d*offset;
    const path=svgNode('path',{d:edge.from===edge.to?`M${from.x-12} ${from.y-11}c-32 -45 56 -45 24 0`:`M${x1} ${y1}Q${mx} ${my} ${x2} ${y2}`,class:'graph-edge'+(activeEdges.has(i)?' active':'')});
    if(graph.directed)path.setAttribute('marker-end',`url(#${markerId})`);svg.append(path);
    const text=svgNode('text',{x:edge.from===edge.to?from.x:mx,y:edge.from===edge.to?from.y-34:my-5,class:'edge-label'});text.textContent=String(edge.weight??1);svg.append(text);
  });
  graph.vertices.forEach(v=>{
    const p=positions.get(v),active=v===step.vertex||(step.path||[]).includes(v);
    svg.append(svgNode('circle',{cx:p.x,cy:p.y,r:16,class:'graph-node'+(active?' active':'')}));
    const text=svgNode('text',{x:p.x,y:p.y+1,class:'node-label'+(active?' active':'')});text.textContent=String(v).length>7?String(v).slice(0,6)+'…':v;
    const title=svgNode('title');title.textContent=v;text.append(title);svg.append(text);
  });
  container.append(svg);
}
function table(headers,rows) {
  const wrap=el('div','table-wrap'),t=el('table'),thead=el('thead'),tr=el('tr');
  headers.forEach(x=>tr.append(el('th','',x)));thead.append(tr);t.append(thead);
  const tbody=el('tbody');rows.forEach(row=>{const r=el('tr');row.forEach(v=>r.append(el('td','',v===null?'∞':v==='-infinity'?'−∞':String(v))));tbody.append(r);});t.append(tbody);wrap.append(t);return wrap;
}
function downloadJSON(data,name) {
  const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));
  const link=el('a');link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function resultCard(item) {
  const result=item.output, card=el('div','result-card');
  const head=el('div','result-head');head.append(el('strong','',state.catalog.find(x=>x.name===item.name)?.label||item.name));
  const download=el('button','text-button','הורדת תוצאה ↓');download.type='button';download.onclick=()=>downloadJSON(item,`${item.name}-result.json`);head.append(download);card.append(head);
  if(result.error){card.append(el('p','inline-error',result.error));return card;}
  if(result.total_weight!==undefined||result.max_flow!==undefined){const metric=el('div','result-metric',String(result.total_weight??result.max_flow));metric.append(el('small','',result.max_flow!==undefined?'זרימה מקסימלית':'משקל העץ'));card.append(metric);}
  if(result.negative_cycle)card.append(el('p','inline-error','זוהה מעגל שלילי. −∞ מציין מרחק שאינו חסום מלמטה.'));
  if(result.distances){const d=result.distances,keys=Object.keys(d);if(keys.length&&typeof d[keys[0]]==='object'&&d[keys[0]]!==null)card.append(table(['מ / אל',...keys],keys.map(k=>[k,...keys.map(v=>d[k][v])])));else card.append(table(['צומת','מרחק','מסלול'],keys.map(k=>[k,d[k],result.paths?.[k]?.join(' → ')||'—'])));}
  if(result.tree_edges)card.append(table(['מקור','יעד','משקל'],result.tree_edges.map(e=>[e.from,e.to,e.weight])));
  if(result.discovery)card.append(table(['צומת','גילוי',result.low?'low':'סיום'],Object.keys(result.discovery).map(v=>[v,result.discovery[v],(result.low||result.finish)[v]])));
  if(result.articulation_points)card.append(el('p','',`צמתי הפרדה: ${result.articulation_points.join(', ')||'אין'}. רכיבים: ${result.components.length}.`));
  if(result.edge_flows){card.append(table(['מקור','יעד','זרימה / קיבולת'],result.edge_flows.map(e=>[e.from,e.to,`${e.flow} / ${e.capacity}`])));card.append(el('p','',`קיבולת חתך מינימלי: ${result.min_cut.capacity}`));}
  if(result.groups)card.append(el('p','',result.groups.map(g=>`{ ${g.join(', ')} }`).join('  |  ')));
  if(result.adjacency)card.append(table(['צומת','שכנים'],Object.entries(result.adjacency).map(([v,neighbors])=>[v,neighbors.map(e=>`${e.vertex} (${e.weight})`).join(', ')||'—'])));
  if(result.note)card.append(el('p','hint',result.note));
  const steps=result.steps||[];
  if(steps.length){
    const preview=el('div','graph-preview');if(item.input.graph)card.append(preview);
    const controls=el('div','step-controls');const prev=el('button','','←'),next=el('button','','→'),slider=el('input');prev.setAttribute('aria-label','השלב הקודם');next.setAttribute('aria-label','השלב הבא');slider.type='range';slider.min='0';slider.max=String(steps.length-1);slider.value='0';slider.setAttribute('aria-label','שלב בחישוב');slider.dir='ltr';
    const counter=el('span','step-counter');controls.append(prev,slider,next,counter);card.append(controls);
    const caption=el('div','step-caption'),stepDetails=el('details');stepDetails.append(el('summary','','פרטי השלב'));const pre=el('pre');stepDetails.append(pre);card.append(caption,stepDetails);
    const display=()=>{const i=Number(slider.value),step=steps[i];counter.textContent=`שלב ${i+1} / ${steps.length}`;caption.textContent=(eventNames[step.event]||step.event)+(step.vertex?' '+step.vertex:'')+(step.bottleneck!==undefined?` · תוספת ${step.bottleneck}, סה״כ ${step.total_flow}`:'');pre.textContent=JSON.stringify(step,null,2);if(item.input.graph)drawGraph(preview,item.input.graph,step);prev.disabled=i===0;next.disabled=i===steps.length-1;};
    slider.oninput=display;prev.onclick=()=>{slider.value=Number(slider.value)-1;display();};next.onclick=()=>{slider.value=Number(slider.value)+1;display();};display();
    if(result.trace_truncated)card.append(el('p','hint',`מוצגים 250 צעדים ראשונים מתוך ${result.augmentations}; התוצאה הסופית מלאה.`));
  }
  card.append(jsonDetails(result));return card;
}
function renderMessage(role,text,payload={}) {
  $('welcome')?.remove();const bubble=el('article',`bubble ${role}`);
  if(role==='user')bubble.textContent=text;
  else {
    const label=el('div','bubble-label');label.append(el('b','','AlgoTutor'));if(payload.route)label.append(el('span','route-chip',routes[payload.route]));if(payload.generation==='fallback')label.append(el('span','route-chip','תשובת גיבוי'));bubble.append(label,el('div','bubble-text',text));
    (payload.tool_results||[]).forEach(item=>bubble.append(resultCard(item)));
    if(payload.sources?.length){const details=el('details','sources');details.append(el('summary','',`${payload.sources.length} מקורות שנמצאו בהרצאות`));payload.sources.forEach((s,i)=>{const source=el('div','source'),link=el('a','',`[${i+1}] הרצאה ${s.lecture} · שקופית ${s.slide||'—'} · עמוד ${s.page}`);link.href=s.url;link.target='_blank';link.rel='noopener';source.append(link,el('p','',s.text),el('small','',`${s.score_type==='cosine'?'דמיון קוסינוס':'התאמה מילולית בהדגמה'}: ${s.score} · זהו ציון חיפוש, לא מדד לוודאות התשובה`));details.append(source);});bubble.append(details);}
    if(payload.notices?.length)bubble.append(el('div','notice',payload.notices.join('\n')));
    if(payload.routing){const details=el('details','route-details');details.append(el('summary','','איך השאלה נותבה?'),el('p','',`${payload.routing.reason} (${payload.routing.method})`));bubble.append(details);}
  }
  $('messages').append(bubble);$('messages').scrollTop=$('messages').scrollHeight;return bubble;
}
async function sendMessage(message,attached=null) {
  if(state.busy||!message.trim())return;
  state.busy=true;$('send').disabled=true;$('new-chat').disabled=true;$('explain-tool').disabled=true;
  renderMessage('user',message);$('message').value='';const loading=el('div','loading','בודק את השאלה, המקורות וכלי החישוב…');$('messages').append(loading);$('messages').scrollTop=$('messages').scrollHeight;
  try {const response=await api('/chat',{message,tool_request:attached});renderMessage('assistant',response.answer,response);}
  catch(error){renderMessage('assistant',`הבקשה לא הושלמה: ${error.message}`);$('message').value=message;}
  finally{loading.remove();state.busy=false;$('send').disabled=false;$('new-chat').disabled=false;$('explain-tool').disabled=false;}
}
$('chat-form').addEventListener('submit',e=>{e.preventDefault();sendMessage($('message').value);});
$('message').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();sendMessage($('message').value);}});
document.querySelectorAll('[data-prompt]').forEach(b=>b.onclick=()=>sendMessage(b.dataset.prompt));
$('new-chat').onclick=async()=>{try{await api('/sessions/new',{});$('messages').replaceChildren();renderMessage('assistant','התחלנו שיחה חדשה. מה תרצו ללמוד?');}catch(e){toast(e.message);}};
$('algorithm').onchange=loadExample;$('load-example').onclick=loadExample;$('json-example').onclick=()=>{const open=$('json-details').open;loadExample();$('json-details').open=open;};
['vertices','edges','directed','source','sink'].forEach(id=>$(id).addEventListener('input',()=>{if(id==='vertices')updateVertexOptions();syncPreview();}));
$('json-details').addEventListener('toggle',()=>{if(!$('json-details').open)syncPreview();});
$('json-input').addEventListener('input',()=>{
  if(!$('json-details').open)return;
  try{const args=JSON.parse($('json-input').value);if(args.graph){drawGraph($('graph-preview'),args.graph);$('graph-kind').textContent='תצוגה מקלט JSON';}}catch{/* Incomplete JSON is validated on submit. */}
});
$('run-tool').onclick=async()=>{showLabError('');try{const arguments_=currentArguments();$('run-tool').disabled=true;const result=await api('/tools/run',{algorithm:$('algorithm').value,arguments:arguments_});$('lab-result').replaceChildren(resultCard(result));$('lab-result').scrollIntoView({behavior:'smooth',block:'nearest'});}catch(e){showLabError(e.message);}finally{$('run-tool').disabled=false;}};
$('explain-tool').onclick=()=>{try{const algorithm=$('algorithm').value;sendMessage(`הרץ את ${state.catalog.find(x=>x.name===algorithm).label} על הקלט שצירפתי והסבר את התוצאה ואת השלבים.`,{algorithm,arguments:currentArguments()});$('chat-heading').scrollIntoView({behavior:'smooth',block:'nearest'});}catch(e){showLabError(e.message);}};
async function init(){
  try{const catalog=await api('/catalog');state.catalog=catalog.algorithms;catalog.algorithms.forEach(a=>{const option=el('option','',`${a.label} · הרצאה ${a.lecture}`);option.value=a.name;$('algorithm').append(option);});$('algorithm').value='dijkstra';loadExample();catalog.lectures.forEach(l=>{const link=el('a');link.href=`/lectures/${l.lecture}`;link.target='_blank';link.rel='noopener';link.append(el('b','',String(l.lecture).padStart(2,'0')),el('span','',l.topic));$('lectures').append(link);});
    const history=await api('/history');history.messages.forEach(m=>renderMessage(m.role,m.content,m.payload));
  }catch(e){toast(e.message);}
  try{const health=await api('/health');$('status').replaceChildren(el('i'),document.createTextNode(health.demo?'מצב הדגמה':health.status==='ready'?'המערכת מוכנה':'חלק מהשירותים דורשים הגדרה'));$('status').classList.toggle('ready',health.status==='ready');if(health.demo||health.status!=='ready'){$('mode-note').hidden=false;$('mode-note').textContent=health.demo?'מצב הדגמה מקומי: כלי החישוב פעילים. החיפוש מילולי, ללא Claude וללא מאגר וקטורי. להפעלה המלאה פעלו לפי README.':'כלי החישוב זמינים. להפעלת הצ׳אט המלא נדרשים מפתח Anthropic ומאגר הרצאות מאונדקס. ראו הוראות ב־README.';}}
  catch(e){$('status').textContent='השרת אינו זמין';toast(e.message);}
}
window.algotutorReady = init();
