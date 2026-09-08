import assert from 'node:assert/strict';
import test from 'node:test';

import {
  getClientHistoryKind,
  resolveInitialRoute,
  resolveBackAction,
} from '../src/platform/index.ts';
import {
  pickUploadFile,
  saveResponseFile,
} from '../src/platform/files.ts';

test('网页使用 history，本地 Electron/Android 资源包使用 hash', () => {
  assert.equal(getClientHistoryKind('web'), 'history');
  assert.equal(getClientHistoryKind('app'), 'hash');
});

test('打包客户端首次启动进入主机连接页，网页仍进入控制台', () => {
  assert.equal(resolveInitialRoute('app', false), '/connect');
  assert.equal(resolveInitialRoute('app', true), '/dashboard');
  assert.equal(resolveInitialRoute('web', false), '/dashboard');
});

test('返回键先关闭浮层，再回退路由，根页面才请求退出客户端', () => {
  assert.equal(resolveBackAction({ hasDismissibleLayer: true, canGoBack: true }), 'dismiss-layer');
  assert.equal(resolveBackAction({ hasDismissibleLayer: false, canGoBack: true }), 'router-back');
  assert.equal(resolveBackAction({ hasDismissibleLayer: false, canGoBack: false }), 'exit-client');
});

test('上传只消费平台选择器返回的 Blob，不把客户端路径注册成主机路径', async () => {
  const bytes = new Blob(['media-bytes'], { type: 'video/mp4' });
  const calls = [];
  const adapter = {
    pickFile: async (accept) => {
      calls.push(accept);
      return { name: 'clip.mp4', mimeType: 'video/mp4', size: bytes.size, data: bytes };
    },
  };

  const selected = await pickUploadFile(adapter, ['video/*']);

  assert.deepEqual(calls, [['video/*']]);
  assert.equal(selected.name, 'clip.mp4');
  assert.equal(selected.data, bytes);
  assert.equal('path' in selected, false);
});

test('受保护下载在当前会话取得 Blob 后交给受限平台保存接口', async () => {
  const bytes = new Blob(['download'], { type: 'application/pdf' });
  let saved;
  const adapter = {
    saveFile: async (request) => {
      saved = request;
      return true;
    },
  };
  const response = {
    ok: true,
    headers: new Headers({ 'Content-Type': 'application/pdf' }),
    blob: async () => bytes,
  };

  assert.equal(await saveResponseFile(adapter, response, 'slides.pdf'), true);
  assert.equal(saved.suggestedName, 'slides.pdf');
  assert.equal(saved.mimeType, 'application/pdf');
  assert.equal(saved.data, bytes);
});

test('文件选择取消与下载失败均不得误报成功', async () => {
  assert.equal(await pickUploadFile({ pickFile: async () => null }, ['*/*']), null);
  await assert.rejects(
    saveResponseFile(
      { saveFile: async () => true },
      { ok: false, status: 401, headers: new Headers(), blob: async () => new Blob() },
      'denied.bin',
    ),
    /HTTP 401/,
  );
});
