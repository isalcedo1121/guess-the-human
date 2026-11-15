const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

function boot({blocked=false,pending=false}={}){
 const clips=[],plays=[],resolvers=[];
 class Audio {
  constructor(src){this.src=src;this.currentTime=10;this.muted=false;this.pauses=0;clips.push(this);}
  pause(){this.pauses++;}
  play(){
   plays.push({src:this.src,muted:this.muted});
   if(blocked)return Promise.reject(new Error('Playback blocked'));
   if(pending&&this.muted)return new Promise(resolve=>resolvers.push(resolve));
   return Promise.resolve();
  }
 }
 const context={Audio};
 const code=fs.readFileSync('frontend/static/sounds.js','utf8').replace(/^export /gm,'');
 vm.runInNewContext(code,context);
 return{context,clips,plays,resolvers};
}

test('sounds prime silently, stop previous clips, and rotate the original three wrong sounds',async()=>{
 const {context,clips,plays}=boot();
 await context.unlockSounds();
 assert.equal(clips.length,6);
 assert(plays.every(play=>play.muted));
 assert(clips.every(clip=>!clip.muted&&clip.currentTime===0));
 await context.playSound('correct');
 for(let i=0;i<4;i++)await context.playWrong();
 await context.playSound('win');await context.playSound('lose');
 assert.deepEqual(plays.filter(play=>!play.muted).map(play=>play.src),[
  '/static/sounds/correct.mp3','/static/sounds/wrong1.mp3','/static/sounds/wrong2.mp3',
  '/static/sounds/wrong3.mp3','/static/sounds/wrong1.mp3','/static/sounds/win.mp3','/static/sounds/lose.mp3'
 ]);
 assert(clips.every(clip=>clip.pauses===8));
});

test('blocked playback resolves harmlessly',async()=>{
 const {context}=boot({blocked:true});
 await context.unlockSounds();
 await context.playSound('correct');
 await context.playWrong();
 await context.playSound('unknown');
});

test('a game sound waits for silent priming to finish',async()=>{
 const {context,plays,resolvers}=boot({pending:true});
 const priming=context.unlockSounds();
 const correct=context.playSound('correct');
 assert(plays.every(play=>play.muted));
 resolvers.forEach(resolve=>resolve());
 await priming;await correct;
 assert.deepEqual(plays.filter(play=>!play.muted),[{src:'/static/sounds/correct.mp3',muted:false}]);
});
