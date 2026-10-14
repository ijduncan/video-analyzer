"use strict";
const test = require('node:test'), assert = require('node:assert/strict');
const { createHost } = require('../host');
function fixture(options={}) {
  let projectId='p', timelineImports=0, writes=0;
  const assets=[0,1].map(index=>({ media_path:`C:\\Footage\\${index}\\same.mov`, source_fps:24, duration_seconds:10,
    metadata:{ schema_version:'1.0', fields:[{resolve:'Description',value:'Description '+index},{resolve:'DOP',value:'DP '+index}],
      record:{schema:'video-analyzer.library',asset:{id:'a'+index},shots:[{shot_number:1,visual_description:'Scene '+index,start_seconds:0,end_seconds:10}],transcript:[{start_seconds:1,end_seconds:2,text:'Dialogue '+index}]} } }));
  const metadata=assets.map(()=>({})), third=assets.map(()=>({}));
  const items=assets.map((asset,index)=>({GetUniqueId:async()=>String(index),
    GetClipProperty:async()=>({'File Path':asset.media_path,FPS:options.badRate&&index===1?25:24,Frames:240,Start:0}),
    GetMetadata:async()=>({...metadata[index]}),SetMetadata:async value=>{writes++;if(options.writeFailure)return false;metadata[index]={...metadata[index],...value};return true;},
    GetThirdPartyMetadata:async()=>({...third[index]}),SetThirdPartyMetadata:async value=>{third[index]={...third[index],...value};return true;}}));
  const root={GetClipList:async()=>items,GetSubFolderList:async()=>[]};
  const pool={GetRootFolder:async()=>root,ImportMedia:async paths=>{assert.deepEqual(paths,assets.map(asset=>asset.media_path)); if(options.switchProject)projectId='other';return items;},
    ImportTimelineFromFile:async(file,settings)=>{timelineImports++; if(options.switchProject)projectId='other'; assert.equal(file,'C:\\Temp\\timeline.xml'); assert.equal(settings.importSourceClips,true);return options.timelineFailure?null:{GetItemListInTrack:async()=>items.map(item=>({GetMediaPoolItem:async()=>item}))};}};
  const project={GetUniqueId:async()=>projectId,GetMediaPool:async()=>pool,SetCurrentTimeline:async()=>true};
  return {host:createHost({GetProjectManager:async()=>({GetCurrentProject:async()=>project})}),
    pack:{schema:'video-analyzer.resolve-handoff',version:1,title:'Booth',layout:'timeline',timeline_path:'C:\\Temp\\timeline.xml',assets},metadata,third,imports:()=>timelineImports,writes:()=>writes};
}
test('package import applies complete metadata to the actual imported timeline originals',async()=>{
  const f=fixture();const result=await f.host.importPackage('p',f.pack);
  assert.equal(result.media,2);assert.equal(result.timeline,true);assert.equal(f.imports(),1);
  for(let i=0;i<2;i++){assert.equal(f.metadata[i].Description,'Description '+i);assert.equal(f.metadata[i].DOP,'DP '+i);assert.match(f.metadata[i]['Dialog Notes'],new RegExp('Dialogue '+i));assert.deepEqual(JSON.parse(f.third[i]['Video Analyzer Complete analysis JSON']),f.pack.assets[i].metadata.record);}
});
test('unverified timing and switched projects cannot receive metadata writes',async()=>{
  for(const options of [{badRate:true},{switchProject:true}]){const f=fixture(options);await assert.rejects(f.host.importPackage('p',f.pack));assert.equal(f.writes(),0);assert.equal(f.imports(),1);}
});
test('failed metadata or timeline import is reported without automatic replay',async()=>{
  const f=fixture({writeFailure:true});await assert.rejects(f.host.importPackage('p',f.pack),{code:'METADATA_WRITE_FAILED'});assert.equal(f.imports(),1);
  const other=fixture({timelineFailure:true});await assert.rejects(other.host.importPackage('p',other.pack),{code:'TIMELINE_IMPORT_FAILED'});assert.equal(other.writes(),0);assert.equal(other.imports(),1);
});
test('media-library only import applies metadata without creating a timeline',async()=>{
  const f=fixture();f.pack.layout='bin';assert.equal((await f.host.importPackage('p',f.pack)).timeline,false);assert.equal(f.imports(),0);assert.ok(f.writes()>0);
});
