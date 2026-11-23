# Gates do frontend

Da pasta `web/`, com Node `^22.13.0 || >=24` e npm:

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm run check
```

O lockfile e todas as dependências diretas de lint estão fixados. `check` para
na primeira falha e executa:

1. `npm run lint`: ESLint flat config, JavaScript recomendado, regras React equivalentes selecionadas,
   Rules of Hooks e dependências de efeitos como erros. Cobre também hooks em
   `.js`, os dois componentes `.tsx`, configurações, scripts e testes Node.
   Zero warnings permitidos. Não é formatter nem typechecker.
2. `npm run test:all`: testes Node (`tests/*.test.mjs`), inclusive regressão que
   prova que a configuração encontra hooks condicionais, dependências ausentes
   e componentes JSX inexistentes.
3. `npm run build`: bundle de produção Vite.
4. `npm run check:assets`: entry HTML, referências JS/CSS, logo empacotado e
   identidade dos arquivos de `public/` no `dist/`.

## Decisões de compatibilidade

- A aplicação existente é majoritariamente JavaScript. `react/prop-types` está
  desligada; não exigimos migração global nem PropTypes em componentes tipados.
- Não ativamos regras experimentais do React Compiler como um atalho para declarar
  o código existente inválido. Ordem de hooks e dependências continuam bloqueantes.
- ESLint **10.15.0**, `@eslint/js` **10.0.1**, plugin React
  `@eslint-react/eslint-plugin` **5.30.5**, plugin oficial de hooks **7.1.1** e
  `typescript-eslint` **8.73.0**, todos fixados, substituem ESLint 9 EOL.
  O mínimo de desenvolvimento/build do frontend sobe deliberadamente para
  Node **22.13.0** (ou >=24); não altera o contrato do backend ou do navegador.
  Docker verifica esse piso antes de instalar. Imagem local `node:22-alpine`
  verificada com Node **22.23.3**.
- A família nova não fornece todas as regras antigas com os mesmos nomes:
  ESLint 10 cobre referências JSX com `no-undef`/`no-unused-vars`;
  o plugin cobre keys, propriedades DOM, children, HTML perigoso, target blank,
  display names e mutação de estado. Classes React são recusadas (a aplicação
  é funcional), cobrindo caminhos legados de lifecycle/render/string refs.
  Três checks locais pequenos e testados preservam props duplicadas, string refs
  em JSX e entidades não escapadas. Hooks continuam nas regras oficiais.
  Não há `--force`, `--legacy-peer-deps` nem waiver de erros para passar o gate.

## Limites do aceite

Build não equivale a typecheck. Ainda não há um gate TypeScript/`checkJs` completo
para o aplicativo; o parser TS do lint só verifica sintaxe e regras configuradas.
Os testes Node não substituem testes DOM/Playwright, acessibilidade ou contratos
HTTP. `tests/test_chat_async_sessions.py` e `tests/test_mobile_navigation.py`
continuam testes separados: exigem o harness/instância local apropriados, e não
são silenciosamente contados como aprovados por `test:all`.

Não chamar `check` de DoD 10/10: ele cobre os gates frontend acima; typecheck e
aceite funcional completo exigem evidências próprias. Não há deploy ou commit
implícito em nenhum comando.
