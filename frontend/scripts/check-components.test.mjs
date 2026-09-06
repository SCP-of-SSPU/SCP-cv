// 使用与 Vite 相同的 Vue 编译器捕获模板中遗漏导入的组件。
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import { compileScript, compileTemplate, parse } from 'vue/compiler-sfc';

const sourceRoot = fileURLToPath(new URL('../src/', import.meta.url));

function vueFiles(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    return entry.isDirectory() ? vueFiles(path) : path.endsWith('.vue') ? [path] : [];
  });
}

test('所有 Naive UI 模板组件必须显式注册', () => {
  const unresolved = [];
  for (const filename of vueFiles(sourceRoot)) {
    const { descriptor, errors } = parse(readFileSync(filename, 'utf8'), { filename });
    assert.deepEqual(errors, [], filename);
    if (!descriptor.template || !descriptor.scriptSetup) continue;
    const script = compileScript(descriptor, { id: filename });
    const result = compileTemplate({
      source: descriptor.template.content,
      filename,
      id: filename,
      compilerOptions: { bindingMetadata: script.bindings },
    });
    assert.deepEqual(result.errors, [], filename);
    for (const match of result.code.matchAll(/_resolveComponent\("(n-[^"]+|N[A-Z][^"]*)"\)/g)) {
      unresolved.push(`${relative(sourceRoot, filename)}: ${match[1]}`);
    }
  }
  assert.deepEqual(unresolved, [], `未注册组件：\n${unresolved.join('\n')}`);
});

test('移动底栏在路由动作之前阻止原生导航，更多只打开抽屉', () => {
  const filename = join(sourceRoot, 'layouts/AppNavigation.vue');
  const { descriptor } = parse(readFileSync(filename, 'utf8'), { filename });
  const bottom = descriptor.template.content.match(/<nav v-if="compact"[\s\S]*?<\/nav>/)?.[0];
  assert.ok(bottom, '必须存在移动底栏');
  assert.doesNotMatch(bottom, /<RouterLink\b/, '自动导航的 RouterLink 会先访问不存在的 /more');
  assert.match(bottom, /@click\.prevent=/, '导航必须由底栏 handler 显式负责');
});

test('侧边抽屉宽度不能大于手机视口', () => {
  for (const name of ['sources/AddSourceDrawer', 'sources/EditSourceDrawer', 'scenarios/ScenarioEditDrawer', 'scenarios/ScenarioPreviewDrawer']) {
    const source = readFileSync(join(sourceRoot, `features/${name}.vue`), 'utf8');
    const drawer = source.match(/<n-drawer\s[\s\S]*?>/)?.[0];
    assert.match(drawer, /width="min\(\d+px, 100vw\)"/, name);
  }
});

test('空闲窗口只展示一次操作提示', () => {
  const filename = join(sourceRoot, 'features/display/PlaybackControl.vue');
  const { descriptor } = parse(readFileSync(filename, 'utf8'), { filename });
  assert.equal([...descriptor.template.content.matchAll(/t\('playback\.noSource'\)/g)].length, 1);
});

test('媒体列表溢出时可横向滚动，导航不会被表格挤窄', () => {
  const sources = readFileSync(join(sourceRoot, 'features/sources/SourcesView.vue'), 'utf8');
  assert.match(sources, /content-style="padding:0; overflow-x:auto"/);
  const shell = readFileSync(join(sourceRoot, 'layouts/AppShell.css'), 'utf8');
  const navigation = shell.match(/\.app-shell__nav\s*\{([^}]+)\}/)?.[1];
  assert.match(navigation, /flex-shrink:\s*0/);
});
