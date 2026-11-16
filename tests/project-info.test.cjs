const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

function boot(){
 const timers=new Map();let nextTimer=1;
 const html=fs.readFileSync('frontend/host.html','utf8');
 const ids=new Set([...html.matchAll(/\bid="([^"]+)"/g)].map(match=>match[1]));
 const info={events:{},addEventListener(name,fn){this.events[name]=fn;}};
 const link={};
 const panel={hidden:true,contains(node){return node===link;}};
 const document={activeElement:null,events:{},addEventListener(name,fn){this.events[name]=fn;},
  getElementById(id){assert(ids.has(id),`missing real element ${id}`);return nodes[id];}};
 const trigger={attributes:{},events:{},setAttribute(name,value){this.attributes[name]=value;},addEventListener(name,fn){this.events[name]=fn;},focus(){document.activeElement=this;info.events.focusin();}};
 info.contains=node=>[info,trigger,panel,link].includes(node);
 const nodes={'project-info':info,'project-info-trigger':trigger,'project-info-panel':panel};
 vm.runInNewContext(fs.readFileSync('frontend/static/project-info.js','utf8'),{document,
  setTimeout(fn){const id=nextTimer++;timers.set(id,fn);return id;},clearTimeout(id){timers.delete(id);}});
 function flushTimers(){const callbacks=[...timers.values()];timers.clear();callbacks.forEach(fn=>fn());}
 return {info,trigger,panel,link,document,flushTimers};
}

test('hover opens the panel, interacting inside keeps it open, and leaving closes it',()=>{
 const {info,trigger,panel,link,document,flushTimers}=boot();
 info.events.pointerenter();
 assert.equal(panel.hidden,false);assert.equal(trigger.attributes['aria-expanded'],'true');
 document.events.pointerdown({target:link});
 assert.equal(panel.hidden,false);
 info.events.pointerleave();assert.equal(panel.hidden,false);
 flushTimers();assert.equal(panel.hidden,true);
});

test('returning into the popover cancels its pending dismissal',()=>{
 const {info,panel,flushTimers}=boot();
 info.events.pointerenter();info.events.pointerleave();info.events.pointerenter();
 flushTimers();assert.equal(panel.hidden,false);
});

test('keyboard focus within the panel survives pointer exit and closes on focus exit',()=>{
 const {info,panel,link,document}=boot();
 info.events.focusin();document.activeElement=link;
 info.events.pointerleave();assert.equal(panel.hidden,false);
 info.events.focusout({relatedTarget:link});assert.equal(panel.hidden,false);
 info.events.focusout({relatedTarget:{}});assert.equal(panel.hidden,true);
});

test('tap opens, Escape restores focus and closes, and outside interaction dismisses',()=>{
 const {trigger,panel,link,document}=boot();
 trigger.events.click();assert.equal(panel.hidden,false);
 document.activeElement=link;document.events.keydown({key:'Escape'});
 assert.equal(panel.hidden,true);assert.equal(document.activeElement,trigger);
 assert.equal(trigger.attributes['aria-expanded'],'false');
 trigger.events.click();document.events.pointerdown({target:{}});
 assert.equal(panel.hidden,true);
});
