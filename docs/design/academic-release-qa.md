# QA operacional acadêmica reproduzível

Executado em 19/11/2026 no Linux: **passou** o recorte operacional dos passos 1–14
mais a parte automatizada do passo 15. Não equivale a aprovação completa do desafio.

```bash
uv run python tools/academic_release_qa.py
```

O roteiro sobe um processo Uvicorn próprio em porta loopback alocada pelo sistema,
usa bancos temporários exclusivos e injeta um modelo determinístico no ADK real.
As frases do roteiro oficial são mapeadas explicitamente para chamadas de ferramentas:
não é teste de compreensão de linguagem, resistência do Gemini a prompts ou variações.
A pergunta do passo 3 é mapeada à consulta de reservas; a proteção de visitantes
é coberta adicionalmente pelos testes de domínio/API, não por interpretação da frase.

O processo filho tem conexões de saída bloqueadas e não carrega credenciais.
O script não acessa as instâncias 8000/8793. Encerra somente seu processo, fecha sua
porta e descarta seus diretórios temporários ao terminar.
Requer Linux/POSIX para passar o descritor do socket ao processo filho.

## Evidências verificadas

- Pré-condições: RSV-1377 no 101 e Marina Duarte no 302.
- Sessão fixa, cancelamento próprio e recusa de alteração/dados de outra unidade.
- Reserva gratuita sem pendência; reserva paga e visitante sem efeito antes da decisão.
- Negação sem efeito, aprovação com efeito, replay/ID inválido 409 e sessão ausente 404.
- Resposta de piscina com 20h; eventos sem capítulos de outros assuntos.
- Dois reinícios reais de processo: primeiro com confirmação do especialista pendente;
  segundo com histórico e efeitos já gravados. Retomada e continuidade aprovadas.
- Duas aprovações HTTP concorrentes em sessões distintas: ambas 200, uma única reserva.
- ADK instalado 2.9.1 e declaração exata no projeto; SHA256 das cinco fixtures
  antes/depois idênticos. Isso prova preservação local, não comparação com upstream.

## Fora desta prova

Instalação de clone limpo, execução integral com Gemini, revisão manual completa do
passo 15, variações adversariais de linguagem e publicação do fork. O passo 1 é
exercitado aqui apenas quanto à inicialização isolada e pré-condições de dados.
O resultado JSON final explicita essas limitações e registra hashes e porta usada.
