/**
 * esbuild 构建配置：将 gRPC-Web 客户端模块打包为浏览器可用的 ESM bundle。
 * 执行方式：node static/js/esbuild.config.mjs
 *
 * @project SCP-cv
 * @author Qintsg
 */

import * as esbuild from 'esbuild';

await esbuild.build({
  entryPoints: ['static/js/grpc-client.js'],
  bundle: true,                 // 将所有依赖打包到一个文件
  format: 'esm',                // 输出 ES Module 格式
  outfile: 'static/js/grpc-client.bundle.js',
  sourcemap: true,              // 生成 source map 便于调试
  minify: false,                // 开发阶段不压缩
  target: ['es2020'],           // 目标浏览器兼容级别
  external: [],                 // 不排除任何依赖，全部内联
});

console.log('✔ gRPC-Web 客户端 bundle 构建完成: static/js/grpc-client.bundle.js');
