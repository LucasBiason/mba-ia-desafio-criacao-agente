// Small, tested JSX checks not provided by the new plugin's selected rules.
const metadata = { type: 'problem', schema: [] };
export default {
  rules: {
    'no-duplicate-props': {
      meta: { ...metadata, messages: { duplicate: 'Duplicate JSX property: {{name}}.' } },
      create(context) {
        return { JSXOpeningElement(node) {
          const seen = new Set();
          for (const attr of node.attributes) {
            if (attr.type !== 'JSXAttribute') continue;
            const name = attr.name.type === 'JSXIdentifier' ? attr.name.name : `${attr.name.namespace.name}:${attr.name.name.name}`;
            if (seen.has(name)) context.report({ node: attr, messageId: 'duplicate', data: { name } });
            seen.add(name);
          }
        } };
      },
    },
    'no-string-refs': {
      meta: { ...metadata, messages: { legacy: 'Legacy string refs are not supported; use a ref object or callback.' } },
      create(context) {
        return { JSXAttribute(node) {
          if (node.name.name !== 'ref') return;
          const value = node.value?.type === 'JSXExpressionContainer' ? node.value.expression : node.value;
          if (typeof value?.value === 'string') context.report({ node, messageId: 'legacy' });
        } };
      },
    },
    'no-unescaped-entities': {
      meta: { ...metadata, messages: { escape: 'Escape quotes, apostrophes, > and } in JSX text with entities or an expression.' } },
      create(context) {
        return { JSXText(node) {
          // Raw source preserves &quot; / &apos; rather than their decoded values.
          if (/["'>}]/.test(context.sourceCode.getText(node))) context.report({ node, messageId: 'escape' });
        } };
      },
    },
  },
};
