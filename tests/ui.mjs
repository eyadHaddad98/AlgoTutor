// Real Flask HTTP + browser-like DOM checks. This is not a browser rendering test.
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdtemp, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join, resolve, dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
const require = createRequire(import.meta.url);
const {JSDOM, CookieJar, VirtualConsole} = require(process.env.ALGO_JSDOM || 'jsdom');
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const temp=await mkdtemp(join(tmpdir(),'algotutor-ui-'));
const origin='http://127.0.0.1:5099';
const server=spawn(process.env.ALGO_PYTHON || 'python', ['-c',
  'import os; from algotutor.web import create_app; from algotutor.config import Settings; create_app(Settings(demo=True,api_key="",secret_key="test-only-secret-"*3,database_url="sqlite:///"+os.environ["ALGO_UI_TEST_DB"])).run(host="127.0.0.1",port=5099)'],
  {cwd:root,env:{...process.env,ALGO_UI_TEST_DB:join(temp,'test.sqlite3')},stdio:['ignore','ignore','pipe']});
let errors='',dom;
server.stderr.on('data',d=>{errors+=String(d);});
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function until(predicate,message) {for(let n=0;n<200;n++){if(await predicate())return;await sleep(25);}throw new Error('Timeout: '+message);}
const jar=new CookieJar(),browserErrors=[];
async function load(){
  const virtualConsole=new VirtualConsole();virtualConsole.on('jsdomError',e=>browserErrors.push(e.message));
  const document=await JSDOM.fromURL(origin,{runScripts:'dangerously',resources:'usable',pretendToBeVisual:true,cookieJar:jar,virtualConsole,
    beforeParse(window){
      window.HTMLElement.prototype.scrollIntoView=function(){};
      window.fetch=async(url,options={})=>{const target=new URL(url,origin);const headers={...options.headers,Cookie:jar.getCookieStringSync(target.href)};
        const response=await fetch(target,{...options,headers});for(const cookie of response.headers.getSetCookie())jar.setCookieSync(cookie,target.href);return response;};
    }});
  await until(()=>document.window.document.querySelectorAll('#algorithm option').length===12,'catalog');
  await until(()=>document.window.document.getElementById('mode-note').hidden===false,'health');
  return document;
}
try {
  await until(async()=>{try{return (await fetch(origin+'/health')).ok;}catch{return false;}},'Flask startup');
  dom=await load();const $=id=>dom.window.document.getElementById(id);
  assert.equal(dom.window.document.documentElement.dir,'rtl');
  assert.equal($('graph-preview').querySelectorAll('circle').length,5);
  assert.equal($('lectures').querySelectorAll('a').length,11);
  for(const option of [...$('algorithm').options]){
    $('algorithm').value=option.value;$('algorithm').dispatchEvent(new dom.window.Event('change'));
    $('run-tool').click();await until(()=>!$('run-tool').disabled,'calculator '+option.value);
    assert.equal($('lab-error').hidden,true,option.value+': '+$('lab-error').textContent);
    assert.equal($('lab-result').querySelectorAll('.result-card').length,1,option.value);
    const slider=$('lab-result').querySelector('input[type=range]');
    if(slider){slider.value=slider.max;slider.dispatchEvent(new dom.window.Event('input'));assert.ok($('lab-result').querySelector('.step-caption').textContent);}
  }
  async function chat(message){$('message').value=message;$('chat-form').dispatchEvent(new dom.window.Event('submit',{cancelable:true}));await until(()=>!$('send').disabled,'chat');}
  await chat('שלום');assert.match($('messages').textContent,/שיחה · LLM/);
  await chat('מהו עץ פורש מינימלי?');assert.match($('messages').textContent,/חיפוש בהרצאות/);assert.ok($('messages').querySelectorAll('.source').length);
  $('algorithm').value='dijkstra';$('algorithm').dispatchEvent(new dom.window.Event('change'));
  $('explain-tool').click();await until(()=>!$('send').disabled,'attached tool chat');assert.ok($('messages').querySelector('.result-card'));
  assert.equal($('messages').querySelectorAll('.bubble').length,6);
  dom.window.close();dom=await load();await until(()=>$('messages').querySelectorAll('.bubble').length===6,'restored history');
  $('edges').value='A B -1';$('edges').dispatchEvent(new dom.window.Event('input'));$('run-tool').click();await until(()=>!$('run-tool').disabled,'invalid input');assert.match($('lab-error').textContent,/שליליים/);
  $('json-details').open=true;$('json-input').value='{bad';$('run-tool').click();assert.match($('lab-error').textContent,/JSON/);
  $('new-chat').click();await until(()=>$('messages').querySelectorAll('.bubble').length===1,'new chat');
  const unexpected=browserErrors.filter(e=>!e.includes('Could not parse CSS stylesheet'));
  assert.deepEqual(unexpected,[]);
  console.log(JSON.stringify({passed:true,calculator_examples:12,chat_routes:3,history_reload:true,new_session:true,input_errors:true,rtl_dom:true,visual_browser_test:false},null,2));
} catch(e){console.error(e);console.error(errors.slice(-3000));process.exitCode=1;}
finally{dom?.window.close();server.kill();await rm(temp,{recursive:true,force:true});}
