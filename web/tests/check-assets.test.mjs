import assert from 'node:assert/strict';
import test from 'node:test';
import { mkdtemp, mkdir, writeFile, copyFile, rm, symlink } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { promisify } from 'node:util';
import { execFile } from 'node:child_process';

const execute = promisify(execFile);
async function fixture(t) {
  const root = await mkdtemp(join(tmpdir(), 'aurora-assets-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  await mkdir(join(root, 'scripts'));
  await mkdir(join(root, 'dist/assets'), { recursive: true });
  await copyFile(new URL('../scripts/check-assets.mjs', import.meta.url), join(root, 'scripts/check-assets.mjs'));
  await writeFile(join(root, 'dist/index.html'), '<script src="/assets/app.js"></script><link href="/assets/app.css">');
  for (const name of ['app.js', 'app.css', 'aurora-logo-test.svg']) await writeFile(join(root, 'dist/assets', name), 'asset');
  return { root, run: () => execute(process.execPath, [join(root, 'scripts/check-assets.mjs')]) };
}

test('clean tree without optional public directory passes', async t => {
  const { run } = await fixture(t);
  assert.match((await run()).stdout, /assets verified/);
});

test('existing empty public directory also passes', async t => {
  const { root, run } = await fixture(t);
  await mkdir(join(root, 'public'));
  await run();
});

test('nested public files must be copied identically', async t => {
  const { root, run } = await fixture(t);
  await mkdir(join(root, 'public/icons'), { recursive: true });
  await mkdir(join(root, 'dist/icons'));
  await writeFile(join(root, 'public/icons/a.svg'), 'original');
  await writeFile(join(root, 'dist/icons/a.svg'), 'original');
  await run();
  await writeFile(join(root, 'dist/icons/a.svg'), 'different');
  await assert.rejects(run(), /Public asset changed or missing/);
  await rm(join(root, 'dist/icons/a.svg'));
  await assert.rejects(run(), /ENOENT/);
});

test('missing required bundle still fails when public is absent', async t => {
  const { root, run } = await fixture(t);
  await rm(join(root, 'dist/assets/app.js'));
  await assert.rejects(run(), /ENOENT/);
});

test('invalid public root is not treated as an optional missing directory', async t => {
  const { root, run } = await fixture(t);
  await writeFile(join(root, 'public'), 'not a directory');
  await assert.rejects(run(), /ENOTDIR/);
});

test('missing nested public target is not swallowed', async t => {
  const { root, run } = await fixture(t);
  await mkdir(join(root, 'public'));
  await symlink(join(root, 'missing-nested-target'), join(root, 'public/nested'));
  await assert.rejects(run(), /ENOENT/);
});


test('public permission failure is not swallowed as optional absence', async t => {
  const { root } = await fixture(t);
  // Deterministic fault injection also works in CI containers running as root,
  // where chmod(000) would not actually deny reads.
  const preload = `import fs from 'node:fs/promises';
    import { syncBuiltinESMExports } from 'node:module';
    const original = fs.readdir;
    fs.readdir = async function(path, ...args) {
      if (path === ${JSON.stringify(join(root, 'public'))}) {
        throw Object.assign(new Error('EACCES public root'), { code: 'EACCES', path });
      }
      return original.call(this, path, ...args);
    };
    syncBuiltinESMExports();`;
  await assert.rejects(execute(process.execPath, [
    '--import', `data:text/javascript,${encodeURIComponent(preload)}`,
    join(root, 'scripts/check-assets.mjs'),
  ]), /EACCES/);
});
