# Consulta seletiva do regulamento vigente

## Caminho real
```text
principal → transfer_to_agent(convivencia)
  → consultar_regulamento(pergunta específica)
  → revalidar identidade/sessão/vínculo
  → RegulationRepository.current() (versão vigente)
  → selecionar capítulo por assunto
  → selecionar um artigo por termos da dúvida
  → {version, chapter, excerpt} OU pedido de esclarecimento
  → eventos persistidos contêm apenas o artigo retornado
```

O texto completo existe somente no servidor durante seleção. Não é colocado no
prompt, state ou resultado da tool. Reaproveitamos o repository do domínio
parameters e a regra existente de versão mais alta, sem copiar fixture como
fonte permanente nem criar outra base. Nenhum dado original foi modificado.

## Trechos para estudar
`tools/regulation_read.py`:
```python
self._validate_access()
with self.repository_factory() as repository:
    current = repository.current()
    result = select_excerpt(current.content, pergunta)
    return {"version": current.version, **result}
```
A autorização ocorre antes da leitura. A versão acompanha a citação e uma
publicação nova passa a valer sem reinstalar a tool. Autor/metadata administrativa
não são enviados ao modelo.

`parameters/queries/regulation_excerpt.py` é seleção determinística, não LLM:
primeiro exige assunto no título do capítulo, depois pontua artigos pelos termos
da dúvida. Horários têm expansão pequena de vocabulário. Empate, assunto ausente,
artigo sem correspondência ou acima de4000 caracteres pede precisão. Nunca usa
texto integral como fallback. Perguntas têm limite500 caracteres.

`runtime/multi_agent_read.py` só conecta a tool quando recebida explicitamente e
confere igualdade de SessionIdentity. Convivência usa fonte retornada e informa
limitações; visitas continuam indisponíveis. Demo8793 e wiring Gemini anteriores
não foram alterados por esta etapa.

## Evidência
63 testes passaram (seis novos). Fixture original em SQLite descartável:
- “horário da piscina aos domingos” retorna somente Art.22, com20h;
- publicação sintética versão1 com19h retorna versão1/19h, não versão0/20h;
- dump integral/perguntas vagas ou ambíguas não retornam excerpt;
- revogação bloqueia antes de abrir repository;
- Runner real+fake transfere à convivência e registra chamada/resultado;
- fechar/reabrir banco mantém só Art.22, sem Art.27 ou capítulos III/XI;
- instruções do principal não contêm o regulamento.

## Limites explícitos
A seleção é lexical e conservadora, não interpretação jurídica nem busca
semântica completa. Pode pedir esclarecimento para perguntas válidas, sinônimos
não previstos ou estrutura Markdown diferente. Isso é preferível a enviar
capítulos alheios. Ainda precisa cobertura de todos os assuntos do avaliador,
perguntas adversariais e dados administrativos alterados. Um modelo real pode
escolher pergunta inadequada: testes fake comprovam o caminho e limites do código,
não qualidade semântica universal. A topologia de confirmação/escrita e F10
completo seguem pendentes. Nenhuma chamada Gemini foi feita.

## Correção após revisão: capítulos com vários assuntos
Academia, brinquedoteca e playground compartilham título de capítulo, mas não
compartilham todas as regras. A seleção agora mantém o assunto pedido e examina
o começo de cada artigo; artigos sem assunto explícito herdam o contexto anterior.
Isso mantém personal trainer no contexto academia, sem atribuí-lo ao playground.
Horários também reconhecem expressões explícitas como6h/23h; idade expande para
anos/faixa etária. Empate ou ausência de evidência continua sem excerpt.

Regressões adicionadas: idade playground→Art34 (não29), personal trainer
playground→sem trecho, horário academia→Art29/6h–23h, inclusive com espaços
extras. Suite total65 testes passou. Continua seleção lexical conservadora, não
prova de compreensão universal de qualquer reescrita administrativa.
