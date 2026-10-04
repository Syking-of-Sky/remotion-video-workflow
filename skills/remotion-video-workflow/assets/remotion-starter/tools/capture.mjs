import {bundle} from '@remotion/bundler';
import {openBrowser, selectComposition, renderStill} from '@remotion/renderer';
import {parseArgs} from 'node:util';
import path from 'node:path';
import fs from 'node:fs/promises';
const {values}=parseArgs({options:{frames:{type:'string'},composition:{type:'string',default:'Example'},entry:{type:'string',default:'src/index.ts'},output:{type:'string',default:'renders/stills'},browser:{type:'string'}}});
if(!values.frames)throw new Error('Supply --frames 0,89,179');
const frames=values.frames.split(',').map(Number);
if(frames.some(f=>!Number.isInteger(f)||f<0))throw new Error('Frames must be nonnegative integers');
const serveUrl=await bundle({entryPoint:path.resolve(values.entry)});
const browser=await openBrowser('chrome',{browserExecutable:values.browser||process.env.REMOTION_BROWSER_EXECUTABLE});
try{
 const composition=await selectComposition({serveUrl,id:values.composition,puppeteerInstance:browser});
 if(frames.some(f=>f>=composition.durationInFrames))throw new Error('Frame exceeds composition');
 await fs.mkdir(values.output,{recursive:true});
 for(const frame of frames){await renderStill({serveUrl,composition,frame,puppeteerInstance:browser,output:path.resolve(values.output,`frame-${String(frame).padStart(6,'0')}.png`)});console.log(`Captured ${frame}`)}
}finally{await browser.close({silent:true})}
