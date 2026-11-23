// Pure protocol helpers; operation arguments never leave the confirmation card.
export function chatResponse(response) {
  const pending = response?.confirmacoes_pendentes;
  if (pending !== undefined && (!Array.isArray(pending) || pending.some(item =>
    !item || typeof item.id !== 'string' || !item.id || typeof item.acao !== 'string' ||
    !item.detalhes || typeof item.detalhes !== 'object' || Array.isArray(item.detalhes)))) {
    throw new Error('O serviço retornou confirmações inválidas. Consulte a conversa antes de continuar.');
  }
  const message = typeof response?.message === 'string' ? response.message.trim() : '';
  if (!message && !pending?.length) throw new Error('O assistente não retornou uma resposta válida.');
  return { message, pending };
}

export function createDecisionGuard() {
  const attempted = new Set();
  const activeSessions = new Set();
  return {
    claim(sessionId, id) {
      const key = JSON.stringify([sessionId, id]);
      if (attempted.has(key) || activeSessions.has(sessionId)) return false;
      attempted.add(key); activeSessions.add(sessionId); return true;
    },
    release(sessionId) { activeSessions.delete(sessionId); },
  };
}

export async function submitConfirmation(api, guard, sessionId, id, confirmado) {
  if (!sessionId || !id || typeof confirmado !== 'boolean') throw new Error('Decisão inválida.');
  if (!guard.claim(sessionId, id)) return null;
  try {
    const response = await api('/api/resident/chat/sessions/' + encodeURIComponent(sessionId) + '/confirmations', {
      method: 'POST', body: { id, confirmado },
    });
    return chatResponse(response);
  } finally {
    // Keep the attempted ID even on network failure: no blind replay.
    guard.release(sessionId);
  }
}

export function restoredChatHistory(data) {
  if (!data || !Array.isArray(data.messages) || !Array.isArray(data.confirmacoes_pendentes)) {
    throw new Error('Não foi possível restaurar o histórico completo.');
  }
  chatResponse({ message: 'history', confirmacoes_pendentes: data.confirmacoes_pendentes });
  const messages = data.messages.filter(item => item && ['user','assistant'].includes(item.role) && typeof item.content === 'string');
  return { messages, pending: data.confirmacoes_pendentes, cursor: data.next_cursor ?? null, archived: Boolean(data.archived) };
}
