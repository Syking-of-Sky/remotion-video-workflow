import React from 'react';
import {AbsoluteFill, Composition, useCurrentFrame} from 'remotion';
import {loss, stateAt, learningRate, trajectory} from './model';
import timeline from '../timeline.json';

const Example: React.FC = () => {
  const frame = useCurrentFrame(), state = stateAt(frame);
  const x = (theta:number) => 120 + theta * 104;
  const y = (value:number) => 595 - value * 23;
  const curve = Array.from({length:121},(_,i)=>`${x(i/20)},${y(loss(i/20))}`).join(' ');
  return <AbsoluteFill style={{background:'#f6f3ed',fontFamily:'Arial, sans-serif',color:'#242935'}}>
    <div style={{position:'absolute',left:76,top:56,fontSize:24,letterSpacing:5}}>ONE MODEL · TWO REPRESENTATIONS</div>
    <div style={{position:'absolute',left:76,top:108,fontSize:54,fontWeight:700}}>Gradient descent</div>
    <svg width={1280} height={720} style={{position:'absolute',inset:0}}>
      <path d="M120 195V595H768" fill="none" stroke="#9ba2a8" strokeWidth={2}/>
      <polyline points={curve} fill="none" stroke="#4b7c91" strokeWidth={6}/>
      {trajectory.map((s,i)=><circle key={i} cx={x(s.theta)} cy={y(s.loss)} r={5} fill="#4b7c91" opacity={.22}/>)}
      <path d={`M${x(state.theta)} ${y(state.loss)}V595`} stroke="#c36957" strokeWidth={2} strokeDasharray="5 8"/>
      <circle cx={x(state.theta)} cy={y(state.loss)} r={13} fill="#c36957" stroke="#f6f3ed" strokeWidth={4}/>
      <text x={115} y={634} fill="#65707a" fontSize={20}>0</text><text x={740} y={634} fill="#65707a" fontSize={20}>6</text>
    </svg>
    <div style={{position:'absolute',left:835,top:220,lineHeight:1.8,fontSize:27}}>
      <div style={{fontSize:36,fontWeight:700}}>L(θ) = (θ − 2)²</div>
      <div>∇L = 2(θ − 2)</div><div>θ′ = θ − {learningRate} ∇L</div>
      <div style={{marginTop:30,color:'#c36957'}}>θ = {state.theta.toFixed(3)}</div>
      <div>L = {state.loss.toFixed(3)}</div><div>step {state.iteration}</div>
    </div>
    <div style={{position:'absolute',left:76,bottom:30,fontSize:19,color:'#65707a'}}>The marker and numbers share stateAt(frame). Seek any frame to reproduce it.</div>
  </AbsoluteFill>;
};

export const Root:React.FC=()=> <Composition id="Example" component={Example}
  width={1280} height={720} fps={timeline.fps} durationInFrames={timeline.durationInFrames}/>;
