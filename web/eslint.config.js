import js from '@eslint/js';
import compat from './scripts/react-compat-rules.mjs';
import globals from 'globals';
import react from '@eslint-react/eslint-plugin';
import hooks from 'eslint-plugin-react-hooks';
import tseslint from 'typescript-eslint';

// Keep compiler-specific experimental constraints out of this existing JS app.
// Hooks correctness and dependency completeness remain blocking, not warnings.
export default [
  { ignores: ['dist/**', 'node_modules/**'] },
  {
    files: ['**/*.{js,jsx,mjs,ts,tsx}'],
    ...js.configs.recommended,
    languageOptions: {
      ecmaVersion: 'latest', sourceType: 'module',
      parserOptions: { ecmaFeatures: { jsx: true } },
      globals: globals.browser,
    },
  },
  {
    files: ['src/**/*.{js,jsx,ts,tsx}'],
    plugins: { '@eslint-react': react, 'react-hooks': hooks, 'react-compat': compat },
    settings: { react: { version: '19.2' } },
    rules: {
      'react-compat/no-duplicate-props': 'error',
      'react-compat/no-string-refs': 'error',
      'react-compat/no-unescaped-entities': 'error',
      '@eslint-react/no-class-component': 'error',
      '@eslint-react/no-missing-component-display-name': 'error',
      '@eslint-react/no-missing-key': 'error',
      '@eslint-react/no-direct-mutation-state': 'error',
      '@eslint-react/jsx-no-children-prop': 'error',
      '@eslint-react/jsx-no-comment-textnodes': 'error',
      '@eslint-react/dom-no-dangerously-set-innerhtml-with-children': 'error',
      '@eslint-react/dom-no-find-dom-node': 'error',
      '@eslint-react/dom-no-render-return-value': 'error',
      '@eslint-react/dom-no-unknown-property': 'error',
      '@eslint-react/dom-no-unsafe-target-blank': 'error',
      '@eslint-react/dom-no-void-elements-with-children': 'error',
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'error',
    },
  },
  {
    files: ['*.config.js', 'tests/**/*.mjs', 'scripts/**/*.mjs'],
    languageOptions: { globals: globals.node },
  },
  {
    files: ['src/**/*.{ts,tsx}'],
    languageOptions: { parser: tseslint.parser },
    plugins: { '@typescript-eslint': tseslint.plugin },
    rules: {
      'no-unused-vars': 'off',
      '@typescript-eslint/no-unused-vars': 'error',
    },
  },
];
