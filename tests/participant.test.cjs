// DOM/HTTP test doubles exercise the actual participant script; no real browser or LLM.
const {test}=require('node:test');const assert=require('node:assert/strict');
const vm=require('node:vm');const fs=require('node:fs');const {randomUUID}=require('node:crypto');
const tick=()=>new Promise(resolve=>setImmediate(resolve));
test('failed submission retains text and retry ID; completion follows server acknowledgement',async()=>{
 const elements={};const storage=new Map();let fail=true;const posts=[];
 const element=id=>elements[id]??=( {hidden:true,value:'',disabled:false,textContent:'',handlers:{},addEventListener(name,fn){this.handlers[name]=fn;}} );
 const context={console,crypto:{randomUUID},location:{pathname:'/room/11111111111141118111111111111111'},
  localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)},
  document:{getElementById:element},requestJSON:async(url,options)=>{
   if(!options)return {question:'Question?',status:'open',submitted:false};
   posts.push(JSON.parse(options.body));if(fail)throw new Error('test network failure');return {accepted:true};
  }};
 const script=fs.readFileSync('frontend/static/participant.js','utf8').replace(/^import .*;\n/,'');
 vm.runInNewContext(script,context);await tick();
 element('submission').value='My actual typed answer';
 await element('answer-form').handlers.submit({preventDefault(){}});
 assert.equal(element('submission').value,'My actual typed answer');
 assert.equal(JSON.parse([...storage.values()][0]).completed,false);
 assert.equal(element('submission-confirmation').hidden,true);
 assert.equal(element('submit-answer').disabled,false);
 fail=false;await element('answer-form').handlers.submit({preventDefault(){}});
 assert.equal(posts[0].submission_id,posts[1].submission_id);
 assert.equal(JSON.parse([...storage.values()][0]).completed,true);
 assert.equal(element('submission-confirmation').hidden,false);
});
