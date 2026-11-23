import test from 'node:test';
import assert from 'node:assert/strict';
import { chatResponse, createDecisionGuard, submitConfirmation } from '../src/chat-confirmations.js';

test('read-only message is unchanged, absent pending stays absent', () => {
  assert.deepEqual(chatResponse({message:'Consulta válida'}), {message:'Consulta válida',pending:undefined});
});
test('empty message accepted only with valid pending action', () => {
  assert.equal(chatResponse({message:'',confirmacoes_pendentes:[{id:'p1',acao:'reservar_area',detalhes:{taxa:50}}]}).pending.length,1);
  assert.throws(() => chatResponse({message:'',confirmacoes_pendentes:[]}));
  assert.throws(() => chatResponse({message:'OK',confirmacoes_pendentes:[{id:'p1'}]}));
});
test('only id and boolean transmitted; URL session escaped', async () => {
  let captured;
  const api = async (...args) => {captured=args;return {message:'Negação recebida',confirmacoes_pendentes:[]};};
  await submitConfirmation(api,createDecisionGuard(),'session/a','p1',false);
  assert.equal(captured[0],'/api/resident/chat/sessions/session%2Fa/confirmations');
  assert.deepEqual(captured[1],{method:'POST',body:{id:'p1',confirmado:false}});
});
test('doubleclick and another card in same session cannot send concurrent decisions', async () => {
  let release; let calls=0;
  const api=async () => {calls++;await new Promise(resolve=>release=resolve);return {message:'Processada',confirmacoes_pendentes:[]};};
  const guard=createDecisionGuard();
  const first=submitConfirmation(api,guard,'A','p1',true);
  assert.equal(await submitConfirmation(api,guard,'A','p1',true),null);
  assert.equal(await submitConfirmation(api,guard,'A','p2',false),null);
  release();await first;
  assert.equal(calls,1);
});
test('ambiguous failure does not auto retry, separate session remains independent', async () => {
  let calls=0;const guard=createDecisionGuard();
  const api=async () => {calls++;throw new Error('lost response');};
  await assert.rejects(submitConfirmation(api,guard,'A','p1',true));
  assert.equal(await submitConfirmation(api,guard,'A','p1',true),null);
  await assert.rejects(submitConfirmation(api,guard,'B','p1',true));
  assert.equal(calls,2);
});
test('non-boolean decisions are rejected before network', async () => {
  await assert.rejects(submitConfirmation(()=>assert.fail('network'),createDecisionGuard(),'A','p1','true'));
});

const { restoredChatHistory } = await import('../src/chat-confirmations.js');
test('restore keeps chronological server order and reversible archive flag', () => {
  const value=restoredChatHistory({messages:[{id:'1',role:'user',content:'Oi'},{id:'2',role:'assistant',content:'Olá'}],confirmacoes_pendentes:[],next_cursor:'older',archived:true});
  assert.deepEqual(value.messages.map(m=>m.id),['1','2']);assert.equal(value.cursor,'older');assert.equal(value.archived,true);
});
test('restore rejects unknown pending state instead of silently treating it as empty', () => {
  assert.throws(()=>restoredChatHistory({messages:[]}));
  assert.throws(()=>restoredChatHistory({messages:[],confirmacoes_pendentes:[{id:'broken'}]}));
});
test('restore excludes tool/internal entries from the visible conversation', () => {
  assert.deepEqual(restoredChatHistory({messages:[null,{role:'tool',content:'internal'}],confirmacoes_pendentes:[]}).messages,[]);
});
