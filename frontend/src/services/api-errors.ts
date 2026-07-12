import { t } from '@/locales';

import type { ControlCommandState } from './control-command';

export interface ApiDetailPayload {
  detail?: string;
  code?: string;
  commands?: ControlCommandState[];
}

function buildNonJsonError(statusCode: number, responseText: string): Error {
  const normalizedText = responseText.trim().replace(/\s+/g, ' ');
  const previewText = normalizedText.slice(0, 120) || t('api.emptyResponse');
  return new Error(t('api.nonJson', { code: statusCode, preview: previewText }));
}

export function parseJsonText<T>(responseText: string, statusCode: number, contentType = ''): T & ApiDetailPayload {
  const trimmedText = responseText.trim();
  if (!trimmedText) return {} as T & ApiDetailPayload;
  if (contentType && !contentType.includes('application/json')) {
    throw buildNonJsonError(statusCode, trimmedText);
  }
  try {
    return JSON.parse(trimmedText) as T & ApiDetailPayload;
  } catch {
    throw buildNonJsonError(statusCode, trimmedText);
  }
}

/** 401 专用错误：路由守卫 / Pinia store 据此触发清状态 + 跳登录。 */
export class UnauthorizedError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'UnauthorizedError';
  }
}

export class ApiRequestError extends Error {
  readonly status: number;
  readonly code: string;
  readonly commands: ControlCommandState[];

  constructor(
    message: string,
    status: number,
    code = '',
    commands: ControlCommandState[] = [],
  ) {
    super(message);
    this.name = 'ApiRequestError';
    this.status = status;
    this.code = code;
    this.commands = commands;
  }
}
