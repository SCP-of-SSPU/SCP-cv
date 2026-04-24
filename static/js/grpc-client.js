/**
 * SCP-cv gRPC-Web 客户端封装模块。
 * 提供对 PlaybackControlService 所有 RPC 的 Promise 化调用接口，
 * 以及 WatchPlaybackState 服务端流的订阅能力。
 *
 * 用法示例：
 *   import { listSources, controlPlayback, watchPlaybackState } from './grpc-client.bundle.js';
 *   const sources = await listSources(1);
 *   controlPlayback('win-1', 'play');
 *
 * @module grpc-client
 * @project SCP-cv
 * @author Qintsg
 */

// ────────────────────────────────────────────────────
// 导入生成的 gRPC-Web 桩代码
// ────────────────────────────────────────────────────

const {
  PlaybackControlServiceClient,
} = require('./grpc-generated/scp_cv/v1/control_grpc_web_pb.js');

const {
  EmptyRequest,
  WindowRequest,
  OpenSourceRequest,
  CloseSourceRequest,
  ControlPlaybackRequest,
  NavigateContentRequest,
  SelectDisplayTargetRequest,
  ListSourcesRequest,
  AddLocalPathSourceRequest,
  AddWebUrlSourceRequest,
  DeleteSourceRequest,
  ToggleLoopRequest,
  SetSpliceModeRequest,
  ScenarioDetail,
  ScenarioWindowSlot,
  UpdateScenarioRequest,
  DeleteScenarioRequest,
  ActivateScenarioRequest,
  CaptureScenarioRequest,
} = require('./grpc-generated/scp_cv/v1/control_pb.js');

// ────────────────────────────────────────────────────
// gRPC-Web 代理地址（可通过全局变量覆盖）
// ────────────────────────────────────────────────────

/**
 * 浏览器访问的 gRPC-Web 代理端点。
 * 页面可在加载本模块前设置 window.GRPC_WEB_PROXY_URL 来覆盖默认值。
 * @type {string}
 */
const GRPC_WEB_PROXY_URL =
  (typeof window !== 'undefined' && window.GRPC_WEB_PROXY_URL) ||
  'http://localhost:8081';

// ────────────────────────────────────────────────────
// 单例客户端实例
// ────────────────────────────────────────────────────

/**
 * PlaybackControlService 的 gRPC-Web 客户端单例。
 * 使用回调风格的 Client（非 PromiseClient），
 * 以便同时支持一元 RPC 与服务端流式 RPC。
 * @type {PlaybackControlServiceClient}
 */
const grpcClient = new PlaybackControlServiceClient(GRPC_WEB_PROXY_URL);

// ────────────────────────────────────────────────────
// 枚举映射：字符串 → protobuf 枚举值
// ────────────────────────────────────────────────────

/**
 * 播放控制动作映射。
 * 键为小写动作名，值为 PlaybackAction 枚举数值。
 * @enum {number}
 */
const PLAYBACK_ACTIONS = {
  play:  1, // ACTION_PLAY
  pause: 2, // ACTION_PAUSE
  stop:  3, // ACTION_STOP
};

/**
 * 内容导航动作映射。
 * 键为小写动作名，值为 NavigateAction 枚举数值。
 * @enum {number}
 */
const NAVIGATE_ACTIONS = {
  next: 1, // NAV_NEXT
  prev: 2, // NAV_PREV
  goto: 3, // NAV_GOTO
  seek: 4, // NAV_SEEK
};

// ────────────────────────────────────────────────────
// 内部工具函数
// ────────────────────────────────────────────────────

/**
 * 将回调风格的 gRPC 一元调用包装为 Promise。
 * 成功时以 protobuf 响应对象 resolve，调用方按需执行 toObject()。
 * 失败时以包含 gRPC 错误码和消息的 Error reject。
 *
 * @param {string} rpcName - RPC 方法名（仅用于错误信息）
 * @param {Function} rpcMethod - 客户端上的原型方法引用
 * @param {Object} requestMessage - 已填充字段的 protobuf 请求消息
 * @returns {Promise<Object>} protobuf 响应对象
 */
function unaryCall(rpcName, rpcMethod, requestMessage) {
  return new Promise((resolve, reject) => {
    rpcMethod.call(grpcClient, requestMessage, {}, (grpcError, response) => {
      if (grpcError) {
        // 构造可读的错误信息，包含 gRPC 状态码
        const errorDetail = `gRPC ${rpcName} 失败: ` +
          `code=${grpcError.code}, message=${grpcError.message}`;
        reject(new Error(errorDetail));
        return;
      }
      resolve(response);
    });
  });
}

// ────────────────────────────────────────────────────
// 源管理 API
// ────────────────────────────────────────────────────

/**
 * 列出指定类型的媒体源。
 * @param {number} sourceType - SourceType 枚举值（0=未知, 1=PPT, 2=视频 ...）
 * @returns {Promise<Object>} ListSourcesReply 对象
 */
export function listSources(sourceType) {
  const request = new ListSourcesRequest();
  request.setSourceType(sourceType);
  return unaryCall(
    'ListSources',
    grpcClient.listSources,
    request,
  );
}

/**
 * 添加本地路径媒体源。
 * @param {string} path - 本地文件或目录路径
 * @param {string} name - 媒体源显示名称
 * @param {number} sourceType - SourceType 枚举值
 * @returns {Promise<Object>} SourceReply 对象
 */
export function addLocalPathSource(path, name, sourceType) {
  const request = new AddLocalPathSourceRequest();
  request.setPath(path);
  request.setName(name);
  request.setSourceType(sourceType);
  return unaryCall(
    'AddLocalPathSource',
    grpcClient.addLocalPathSource,
    request,
  );
}

/**
 * 添加 Web URL 媒体源。
 * @param {string} url - 网页 URL 地址
 * @param {string} name - 媒体源显示名称
 * @returns {Promise<Object>} SourceReply 对象
 */
export function addWebUrlSource(url, name) {
  const request = new AddWebUrlSourceRequest();
  request.setUrl(url);
  request.setName(name);
  return unaryCall(
    'AddWebUrlSource',
    grpcClient.addWebUrlSource,
    request,
  );
}

/**
 * 删除指定的媒体源。
 * @param {string} mediaSourceId - 媒体源唯一标识
 * @returns {Promise<Object>} OperationReply 对象
 */
export function deleteSource(mediaSourceId) {
  const request = new DeleteSourceRequest();
  request.setMediaSourceId(mediaSourceId);
  return unaryCall(
    'DeleteSource',
    grpcClient.deleteSource,
    request,
  );
}

// ────────────────────────────────────────────────────
// 播放控制 API
// ────────────────────────────────────────────────────

/**
 * 在指定窗口打开媒体源并开始播放。
 * @param {string} windowId - 窗口标识
 * @param {string} mediaSourceId - 媒体源唯一标识
 * @param {boolean} autoplay - 是否自动播放
 * @returns {Promise<Object>} OperationReply 对象
 */
export function openSource(windowId, mediaSourceId, autoplay) {
  const request = new OpenSourceRequest();
  request.setWindowId(windowId);
  request.setMediaSourceId(mediaSourceId);
  request.setAutoplay(autoplay);
  return unaryCall(
    'OpenSource',
    grpcClient.openSource,
    request,
  );
}

/**
 * 关闭指定窗口的媒体源。
 * @param {string} windowId - 窗口标识
 * @returns {Promise<Object>} OperationReply 对象
 */
export function closeSource(windowId) {
  const request = new CloseSourceRequest();
  request.setWindowId(windowId);
  return unaryCall(
    'CloseSource',
    grpcClient.closeSource,
    request,
  );
}

/**
 * 控制指定窗口的播放状态（播放/暂停/停止）。
 * @param {string} windowId - 窗口标识
 * @param {string} action - 动作字符串：'play' | 'pause' | 'stop'
 * @returns {Promise<Object>} OperationReply 对象
 */
export function controlPlayback(windowId, action) {
  const actionEnum = PLAYBACK_ACTIONS[action];
  if (actionEnum === undefined) {
    return Promise.reject(
      new Error(`无效的播放动作: "${action}"，可选值: play, pause, stop`),
    );
  }
  const request = new ControlPlaybackRequest();
  request.setWindowId(windowId);
  request.setAction(actionEnum);
  return unaryCall(
    'ControlPlayback',
    grpcClient.controlPlayback,
    request,
  );
}

/**
 * 在指定窗口中导航内容（上一个/下一个/跳转/拖动进度）。
 * @param {string} windowId - 窗口标识
 * @param {string} action - 导航动作：'next' | 'prev' | 'goto' | 'seek'
 * @param {number} [targetIndex=0] - 跳转目标索引（仅 goto 时有效）
 * @param {number} [positionMs=0] - 目标播放位置毫秒数（仅 seek 时有效）
 * @returns {Promise<Object>} OperationReply 对象
 */
export function navigateContent(windowId, action, targetIndex = 0, positionMs = 0) {
  const actionEnum = NAVIGATE_ACTIONS[action];
  if (actionEnum === undefined) {
    return Promise.reject(
      new Error(`无效的导航动作: "${action}"，可选值: next, prev, goto, seek`),
    );
  }
  const request = new NavigateContentRequest();
  request.setWindowId(windowId);
  request.setAction(actionEnum);
  request.setTargetIndex(targetIndex);
  request.setPositionMs(positionMs);
  return unaryCall(
    'NavigateContent',
    grpcClient.navigateContent,
    request,
  );
}

/**
 * 切换指定窗口的循环播放模式。
 * @param {string} windowId - 窗口标识
 * @param {boolean} enabled - 是否启用循环
 * @returns {Promise<Object>} OperationReply 对象
 */
export function toggleLoop(windowId, enabled) {
  const request = new ToggleLoopRequest();
  request.setWindowId(windowId);
  request.setEnabled(enabled);
  return unaryCall(
    'ToggleLoop',
    grpcClient.toggleLoop,
    request,
  );
}

/**
 * 设置全局拼接模式开关。
 * @param {boolean} enabled - 是否启用拼接模式
 * @returns {Promise<Object>} SpliceModeReply 对象
 */
export function setSpliceMode(enabled) {
  const request = new SetSpliceModeRequest();
  request.setEnabled(enabled);
  return unaryCall(
    'SetSpliceMode',
    grpcClient.setSpliceMode,
    request,
  );
}

/**
 * 获取当前所有活跃窗口 ID 列表。
 * @returns {Promise<Object>} OperationReply 对象（窗口 ID 信息）
 */
export function showWindowIds() {
  const request = new EmptyRequest();
  return unaryCall(
    'ShowWindowIds',
    grpcClient.showWindowIds,
    request,
  );
}

// ────────────────────────────────────────────────────
// 状态查询 API
// ────────────────────────────────────────────────────

/**
 * 获取指定窗口的运行时状态信息。
 * @param {string} windowId - 窗口标识
 * @returns {Promise<Object>} RuntimeStatusReply 对象
 */
export function getRuntimeStatus(windowId) {
  const request = new WindowRequest();
  request.setWindowId(windowId);
  return unaryCall(
    'GetRuntimeStatus',
    grpcClient.getRuntimeStatus,
    request,
  );
}

/**
 * 获取指定窗口的当前播放状态。
 * @param {string} windowId - 窗口标识
 * @returns {Promise<Object>} PlaybackStateReply 对象
 */
export function getPlaybackState(windowId) {
  const request = new WindowRequest();
  request.setWindowId(windowId);
  return unaryCall(
    'GetPlaybackState',
    grpcClient.getPlaybackState,
    request,
  );
}

/**
 * 获取所有播放会话的快照。
 * @returns {Promise<Object>} AllSessionSnapshotsReply 对象
 */
export function getAllSessionSnapshots() {
  const request = new EmptyRequest();
  return unaryCall(
    'GetAllSessionSnapshots',
    grpcClient.getAllSessionSnapshots,
    request,
  );
}

// ────────────────────────────────────────────────────
// 显示器 API
// ────────────────────────────────────────────────────

/**
 * 列出所有可用的显示目标（显示器/投影仪）。
 * @returns {Promise<Object>} DisplayTargetsReply 对象
 */
export function listDisplayTargets() {
  const request = new EmptyRequest();
  return unaryCall(
    'ListDisplayTargets',
    grpcClient.listDisplayTargets,
    request,
  );
}

/**
 * 为指定窗口选择显示目标。
 * @param {string} windowId - 窗口标识
 * @param {string} displayMode - 显示模式标识
 * @param {string} targetLabel - 目标显示器标签
 * @returns {Promise<Object>} OperationReply 对象
 */
export function selectDisplayTarget(windowId, displayMode, targetLabel) {
  const request = new SelectDisplayTargetRequest();
  request.setWindowId(windowId);
  request.setDisplayMode(displayMode);
  request.setTargetLabel(targetLabel);
  return unaryCall(
    'SelectDisplayTarget',
    grpcClient.selectDisplayTarget,
    request,
  );
}

// ────────────────────────────────────────────────────
// 兼容 API
// ────────────────────────────────────────────────────

/**
 * 停止当前正在播放的内容（全局兼容接口）。
 * @returns {Promise<Object>} OperationReply 对象
 */
export function stopCurrentContent() {
  const request = new EmptyRequest();
  return unaryCall(
    'StopCurrentContent',
    grpcClient.stopCurrentContent,
    request,
  );
}

// ────────────────────────────────────────────────────
// 预案管理 API
// ────────────────────────────────────────────────────

/**
 * 构建 ScenarioWindowSlot 消息对象。
 * @param {Object} windowConfig - 窗口槽位配置
 * @param {number} windowConfig.sourceId - 媒体源 ID
 * @param {boolean} windowConfig.autoplay - 是否自动播放
 * @param {boolean} windowConfig.resume - 是否断点续播
 * @returns {ScenarioWindowSlot} 填充后的 protobuf 消息
 */
function buildWindowSlot(windowConfig) {
  const slot = new ScenarioWindowSlot();
  slot.setSourceId(windowConfig.sourceId);
  slot.setAutoplay(windowConfig.autoplay);
  slot.setResume(windowConfig.resume);
  return slot;
}

/**
 * 构建 ScenarioDetail 消息对象。
 * @param {string} name - 预案名称
 * @param {string} description - 预案描述
 * @param {boolean} isSpliceMode - 是否为拼接模式
 * @param {Object} window1Config - 窗口 1 槽位配置 {sourceId, autoplay, resume}
 * @param {Object} window2Config - 窗口 2 槽位配置 {sourceId, autoplay, resume}
 * @returns {ScenarioDetail} 填充后的 protobuf 消息
 */
function buildScenarioDetail(name, description, isSpliceMode, window1Config, window2Config) {
  const detail = new ScenarioDetail();
  detail.setName(name);
  detail.setDescription(description);
  detail.setIsSpliceMode(isSpliceMode);
  detail.setWindow1(buildWindowSlot(window1Config));
  detail.setWindow2(buildWindowSlot(window2Config));
  return detail;
}

/**
 * 列出所有预案。
 * @returns {Promise<Object>} ListScenariosReply 对象
 */
export function listScenarios() {
  const request = new EmptyRequest();
  return unaryCall(
    'ListScenarios',
    grpcClient.listScenarios,
    request,
  );
}

/**
 * 创建新预案。
 * @param {string} name - 预案名称
 * @param {string} description - 预案描述
 * @param {boolean} isSpliceMode - 是否为拼接模式
 * @param {Object} window1Config - 窗口 1 槽位配置 {sourceId, autoplay, resume}
 * @param {Object} window2Config - 窗口 2 槽位配置 {sourceId, autoplay, resume}
 * @returns {Promise<Object>} ScenarioReply 对象
 */
export function createScenario(name, description, isSpliceMode, window1Config, window2Config) {
  const request = buildScenarioDetail(name, description, isSpliceMode, window1Config, window2Config);
  return unaryCall(
    'CreateScenario',
    grpcClient.createScenario,
    request,
  );
}

/**
 * 更新已有预案。
 * @param {number} scenarioId - 预案唯一标识
 * @param {string} name - 预案名称
 * @param {string} description - 预案描述
 * @param {boolean} isSpliceMode - 是否为拼接模式
 * @param {Object} window1Config - 窗口 1 槽位配置 {sourceId, autoplay, resume}
 * @param {Object} window2Config - 窗口 2 槽位配置 {sourceId, autoplay, resume}
 * @returns {Promise<Object>} ScenarioReply 对象
 */
export function updateScenario(scenarioId, name, description, isSpliceMode, window1Config, window2Config) {
  const request = new UpdateScenarioRequest();
  request.setScenarioId(scenarioId);
  request.setDetail(buildScenarioDetail(name, description, isSpliceMode, window1Config, window2Config));
  return unaryCall(
    'UpdateScenario',
    grpcClient.updateScenario,
    request,
  );
}

/**
 * 删除指定预案。
 * @param {number} scenarioId - 预案唯一标识
 * @returns {Promise<Object>} OperationReply 对象
 */
export function deleteScenario(scenarioId) {
  const request = new DeleteScenarioRequest();
  request.setScenarioId(scenarioId);
  return unaryCall(
    'DeleteScenario',
    grpcClient.deleteScenario,
    request,
  );
}

/**
 * 激活指定预案，启动对应播放会话。
 * @param {number} scenarioId - 预案唯一标识
 * @returns {Promise<Object>} ActivateScenarioReply 对象
 */
export function activateScenario(scenarioId) {
  const request = new ActivateScenarioRequest();
  request.setScenarioId(scenarioId);
  return unaryCall(
    'ActivateScenario',
    grpcClient.activateScenario,
    request,
  );
}

/**
 * 从当前窗口 1/2 播放状态捕获预案。
 * @param {string} name - 预案名称
 * @param {string} description - 预案描述
 * @param {number} [scenarioId=0] - 已有预案 ID；0 表示创建新预案
 * @returns {Promise<Object>} ScenarioReply 对象
 */
export function captureScenario(name, description, scenarioId = 0) {
  const request = new CaptureScenarioRequest();
  request.setName(name);
  request.setDescription(description);
  request.setScenarioId(scenarioId);
  return unaryCall(
    'CaptureScenario',
    grpcClient.captureScenario,
    request,
  );
}

// ────────────────────────────────────────────────────
// 实时推送：服务端流式 RPC
// ────────────────────────────────────────────────────

/**
 * 订阅播放状态实时事件流（服务端流式 RPC）。
 * 当服务端推送 PlaybackStateEvent 时，onEvent 回调将被调用。
 *
 * @param {Function} onEvent - 每次收到事件时的回调，参数为 PlaybackStateEvent protobuf 对象
 * @param {Function} [onError] - 流发生错误时的回调，参数为 gRPC Error
 * @param {Function} [onEnd] - 流正常结束时的回调
 * @returns {Function} 取消函数——调用后将关闭流并停止接收事件
 */
export function watchPlaybackState(onEvent, onError, onEnd) {
  const request = new EmptyRequest();

  // 发起服务端流式调用，返回 ClientReadableStream
  const stream = grpcClient.watchPlaybackState(request, {});

  // 监听数据事件：保留 protobuf 对象，由调用方决定如何序列化。
  stream.on('data', (response) => {
    onEvent(response);
  });

  // 监听错误事件
  stream.on('error', (streamError) => {
    if (onError) {
      onError(streamError);
    }
  });

  // 监听流结束事件
  stream.on('end', () => {
    if (onEnd) {
      onEnd();
    }
  });

  // 返回取消函数，调用方可随时中止流
  return () => {
    stream.cancel();
  };
}
