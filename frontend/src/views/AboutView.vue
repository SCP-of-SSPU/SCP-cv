<template>
  <section class="panel about-hero">
    <span class="eyebrow">About SCP-cv</span>
    <h2>单机大屏播控系统</h2>
    <p>SCP-cv 通过 Vue 控制台、Django REST API、SSE 状态推送和 PySide6 本地播放器完成 PPT、视频、图片、网页与 SRT 直播源的四窗口播放控制。</p>
  </section>

  <section class="grid three">
    <article class="panel">
      <h2>使用流程</h2>
      <ol class="guide-list">
        <li>运行 <code>uv run python manage.py runall</code></li>
        <li>在启动器中选择播放窗口屏幕</li>
        <li>进入 Web 控制台上传或注册媒体源</li>
        <li>在显示控制页或播放控制页打开源</li>
        <li>保存预案并一键激活现场状态</li>
      </ol>
    </article>
    <article class="panel">
      <h2>关键入口</h2>
      <p><code>/dashboard</code> 总览态势</p>
      <p><code>/display/big-left</code> 大屏左控制</p>
      <p><code>/display/tv-left</code> TV 左控制</p>
      <p><code>/ppt-focus/1</code> PPT 专注页</p>
    </article>
    <article class="panel">
      <h2>运行约束</h2>
      <p>大屏模式只使用 <code>single</code> 与 <code>double</code>。</p>
      <p>窗口 3/4 始终静音；Single 模式下窗口 2 静音。</p>
      <p>设备电源当前记录控制意图，未接入物理协议。</p>
    </article>
  </section>

  <section class="panel">
    <h2>验证命令</h2>
    <pre><code>uv run pytest tests/ -q
uv run ruff check .
npm --prefix frontend run typecheck
npm --prefix frontend run build</code></pre>
  </section>
</template>
