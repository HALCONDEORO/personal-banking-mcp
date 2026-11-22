// Offline fault injection, including the independent reviewer's fsync-after-rename case.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import https from 'node:https';
import {syncBuiltinESMExports} from 'node:module';
import {EventEmitter} from 'node:events';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {randomBytes} from 'node:crypto';
import {EncryptedStore} from '../store.mjs';
import {ReadClient,aisGet} from '../ais.mjs';
const NOW=1800000000000;
const initial=()=>({version:1,sessionId:'synthetic',validUntil:NOW+3*86400000,lastClock:NOW,revoked:false,stopped:false,accounts:[{uid:'synthetic',currency:'EUR'}],quota:{}});

test('actual AES store: final directory fsync failure persists stop, including reopen',async()=>{
 const dir=fs.mkdtempSync(join(tmpdir(),'bankmcp-review-'));fs.chmodSync(dir,0o700);
 const key=randomBytes(32),original=fs.fsyncSync;let store,count=0,calls=0;
 try {
  store=new EncryptedStore(dir,key);store.write(initial());
  fs.fsyncSync=fd=>{count++;if(count===4)throw Error('synthetic directory fsync failure');return original(fd);};syncBuiltinESMExports();
  const client=new ReadClient({store,clock:()=>NOW,signer:()=> 'synthetic',transport:async()=>{calls++;return {balances:[]};}});
  await assert.rejects(client.call('get_balance',{account:'synthetic'}));
  assert.equal(store.read().stopped,true);
  await assert.rejects(client.call('get_balance',{account:'synthetic'}));
  fs.fsyncSync=original;syncBuiltinESMExports();store.close();store=new EncryptedStore(dir,key);
  const reopened=new ReadClient({store,clock:()=>NOW,signer:()=> 'synthetic',transport:async()=>{calls++;return {balances:[]};}});
  await assert.rejects(reopened.call('get_balance',{account:'synthetic'}));assert.equal(calls,1);
  assert.equal(store.read().quota['synthetic/balances'].length,1);
 } finally {fs.fsyncSync=original;syncBuiltinESMExports();store?.close();fs.rmSync(dir,{recursive:true,force:true});}
});

test('actual encrypted quota: four reads, close/reopen retains stop+budget, reviewed synthetic recovery does not clear quota',async()=>{
 const dir=fs.mkdtempSync(join(tmpdir(),'bankmcp-quota-'));fs.chmodSync(dir,0o700);
 const key=randomBytes(32);let store,calls=0,now=NOW;
 const make=()=>new ReadClient({store,clock:()=>now,signer:()=> 'synthetic',transport:async()=>{calls++;return {balances:[]};}});
 try {
  store=new EncryptedStore(dir,key);store.write(initial());let client=make();
  for(let i=0;i<4;i++)await client.call('get_balance',{account:'synthetic'});
  await assert.rejects(client.call('get_balance',{account:'synthetic'}),/QUOTA/);
  store.close();store=new EncryptedStore(dir,key);client=make();
  assert.equal(store.read().quota['synthetic/balances'].length,4);
  await assert.rejects(client.call('get_balance',{account:'synthetic'}),/CONSENT_OR_STATE/);
  // Test-only owner recovery. No application command or MCP tool exposes this.
  const recovered=store.read();recovered.stopped=false;store.write(recovered);client=make();
  await assert.rejects(client.call('get_balance',{account:'synthetic'}),/QUOTA/);
  now=NOW+86400000;await client.call('get_balance',{account:'synthetic'});assert.equal(calls,5);
  store.close();store=new EncryptedStore(dir,key);assert.equal(store.read().quota['synthetic/balances'].length,1);assert.equal(store.read().stopped,true);
 } finally {store?.close();fs.rmSync(dir,{recursive:true,force:true});}
});

test('production transport offline: success, status/redirect, cap, JSON, abort and total timeout',async()=>{
 const original=https.request,originalTimer=globalThis.setTimeout;
 let mode='ok',requests=0,seen,destroyed=false;
 try {
  https.request=(url,opts,callback)=>{
   requests++;seen={url:url.href,opts};const req=new EventEmitter();req.destroy=()=>{destroyed=true;};
   req.end=()=>queueMicrotask(()=>{
    if(mode==='timeout')return;
    const res=new EventEmitter();res.statusCode=mode==='redirect'?302:mode==='status'?429:200;res.destroy=()=>{};callback(res);
    if(res.statusCode!==200)return;
    if(mode==='abort'){res.emit('aborted');return;}
    res.emit('data',Buffer.from(mode==='cap'?'x'.repeat(1048577):mode==='json'?'private-bad-json':'{"balances":[]}'));
    res.emit('end');
   });return req;
  };syncBuiltinESMExports();
  assert.deepEqual(await aisGet('/accounts/synthetic/balances',{},'synthetic'),{balances:[]});
  assert.equal(seen.url,'https://api.enablebanking.com/accounts/synthetic/balances');assert.equal(seen.opts.method,'GET');assert.equal(seen.opts.agent,false);
  for(const m of ['redirect','status','cap','json','abort']){mode=m;const before=requests;await assert.rejects(aisGet('/accounts/synthetic/balances',{},'synthetic'));assert.equal(requests,before+1);}
  mode='timeout';destroyed=false;
  globalThis.setTimeout=(fn,delay)=>{assert.equal(delay,10000);queueMicrotask(fn);return 0;};
  await assert.rejects(aisGet('/accounts/synthetic/balances',{},'synthetic'),/TIMEOUT/);assert.equal(destroyed,true);
 } finally {globalThis.setTimeout=originalTimer;https.request=original;syncBuiltinESMExports();}
});

test('actual AES store: transient read corruption consumes same-process resume',async()=>{
 const dir=fs.mkdtempSync(join(tmpdir(),'bankmcp-read-'));fs.chmodSync(dir,0o700);let store,calls=0;
 try {
  store=new EncryptedStore(dir,randomBytes(32));store.write(initial());
  const client=new ReadClient({store,clock:()=>NOW,signer:()=> 'synthetic',transport:async()=>{calls++;return {balances:[]};}});
  await client.call('get_balance',{account:'synthetic'});
  const path=join(dir,'state.aesgcm'),raw=fs.readFileSync(path);fs.writeFileSync(path,Buffer.from('corrupt synthetic'));
  await assert.rejects(client.call('get_balance',{account:'synthetic'}));
  fs.writeFileSync(path,raw);
  await assert.rejects(client.call('get_balance',{account:'synthetic'}));assert.equal(calls,1);assert.equal(store.read().stopped,true);
 }finally{store?.close();fs.rmSync(dir,{recursive:true,force:true});}
});
