// Execute the real host script against IDs from the real HTML template.
const {test}=require('node:test');const assert=require('node:assert/strict');
const fs=require('node:fs');const vm=require('node:vm');
const html=fs.readFileSync('frontend/host.html','utf8');
const questions=JSON.parse(fs.readFileSync('frontend/static/questions.json','utf8'));
function boot(){
 function element(){return {children:[],append(...children){this.children.push(...children);}};}
 const ids=new Set([...html.matchAll(/\bid="([^"]+)"/g)].map(x=>x[1]));const nodes=new Map();
 function node(id){if(!ids.has(id))return null;if(!nodes.has(id))nodes.set(id,{id,value:'',hidden:false,disabled:false,textContent:'',listeners:{},addEventListener(n,f){this.listeners[n]=f;}});return nodes.get(id);}
 const screens=[...html.matchAll(/<section\b([^>]+)>/g)].filter(x=>x[1].includes('class="screen"')).map(x=>{const n=node(x[1].match(/id="([^"]+)"/)[1]);n.hidden=/\bhidden\b/.test(x[1]);return n;});
 const questionNodes=[{textContent:''},{textContent:''}];
 node('question-select').value=questions[0];node('round-count').value=html.match(/<select id="round-count"[\s\S]*?<option value="(\d+)" selected>/)[1];node('setup-error').hidden=true;
 const posts=[];
 const context={console,location:{pathname:'/',origin:'http://localhost'},history:{replaceState(){}},window:{scrollTo(){},matchMedia(){return{matches:false}}},
  document:{hidden:false,getElementById:node,createElement:element,addEventListener(){},querySelector(selector){assert.equal(selector,'#lobby [data-question]');return questionNodes[0];},querySelectorAll(selector){if(selector==='.screen')return screens;if(selector==='[data-question]')return questionNodes;return[];}},
  setTimeout:()=>1,clearTimeout(){},requestJSON:async(url,options)=>{posts.push({url,body:JSON.parse(options.body)});return {id:'11111111111141118111111111111111',question:JSON.parse(options.body).question,rounds:JSON.parse(options.body).rounds,status:'open',submission_count:0};}};
 vm.runInNewContext(fs.readFileSync('frontend/static/host.js','utf8').replace(/^import .*;\n/,''),context);
 return{node,posts,resultRow:context.resultRow};
}
for(const custom of [false,true])test(`host boots and creates a ${custom?'custom':'preset'} room without missing DOM elements`,async()=>{
 const {node,posts}=boot();
 if(custom){node('question-select').value='custom';node('custom-question').value='My custom question?';node('question-select').listeners.change();}
 await node('setup-form').listeners.submit({preventDefault(){}});
 assert.equal(posts[0].body.rounds,20);assert.equal(posts[0].url,'/api/rooms');assert.equal(posts[0].body.question,custom?'My custom question?':questions[0]);
 assert.equal(node('lobby').hidden,false);assert.equal(node('setup').hidden,true);assert.equal(node('setup-error').hidden,true);
 assert.match(node('room-link').value,/\/room\//);
});

test('result details preserve per-answer notes as text and replace old instruction boilerplate',()=>{
 const {resultRow}=boot();
 const note=row=>row.children[1].children[1].children[0].textContent;
 const first=resultRow({actual:'ai',style:'Chameleon',text:'A goat ate it.',explanation:'I used an unexpected goat as the punchline.',correct:true},0);
 const second=resultRow({actual:'ai',style:'Chameleon',text:'My laptop sailed away.',explanation:'I gave the laptop a surprise voyage.',correct:false},1);
 assert.notEqual(note(first),note(second));
 assert.equal(note(first),'I used an unexpected goat as the punchline.');
 const legacy=resultRow({actual:'ai',style:'Slang',text:'An older answer',explanation:'I was asked to use slang. I was not given human examples.'},2);
 assert.equal(note(legacy),'I used casual wording and internet slang.');
 const untrusted='<img src=x onerror=alert(1)>';
 assert.equal(note(resultRow({actual:'ai',style:'Basic',text:'text',explanation:untrusted},3)),untrusted);
});
