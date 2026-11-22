import test from 'node:test';
import assert from 'node:assert/strict';
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {InMemoryTransport} from '@modelcontextprotocol/sdk/inMemory.js';
import {createServer} from '../mcp.mjs';

test('MCP publishes exactly three read tools; no payment or consent tool',async()=>{
 const calls=[];
 const server=createServer({call:async(name,args)=>{calls.push([name,args]);return {source:'synthetic-test',live:false};}});
 const client=new Client({name:'synthetic-audit',version:'1'});
 const [a,b]=InMemoryTransport.createLinkedPair();
 try {
  await Promise.all([server.connect(a),client.connect(b)]);
  const list=await client.listTools();
  assert.deepEqual(list.tools.map(t=>t.name).sort(),['get_balance','get_transactions','list_accounts']);
  const result=await client.callTool({name:'get_balance',arguments:{account:'synthetic-eur'}});
  assert.equal(result.isError,undefined);assert.equal(calls.length,1);
  assert.match(result.content[0].text,/synthetic-test/);
  const denied=await client.callTool({name:'pay',arguments:{}});
  assert.equal(denied.isError,true);assert.equal(calls.length,1);
 } finally {await client.close();await server.close();}
});
test('MCP generic errors never disclose private provider text',async()=>{
 const server=createServer({call:async()=>{throw Error('private-secret');}});
 const client=new Client({name:'synthetic-audit',version:'1'});
 const [a,b]=InMemoryTransport.createLinkedPair();
 try{await Promise.all([server.connect(a),client.connect(b)]);const r=await client.callTool({name:'list_accounts',arguments:{}});assert.equal(r.isError,true);assert.equal(r.content[0].text,'STOPPED');}
 finally{await client.close();await server.close();}
});
