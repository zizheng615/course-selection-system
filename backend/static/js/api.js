/**
 * 接口层。对标参考项目的 `utils/request.js`（axios 实例 + 拦截器）。
 *
 * 后端契约：**HTTP 状态码恒为 200**，成败只看响应体里的 `code`：
 *   `{ code: 0, message: "ok", data: … }`
 * 所以这里不能用 `response.ok` 判成败 —— 业务错误也是 200。
 *
 * 统一在这一层处理三件事，页面里就不用重复写了：
 *   1. 附带 `Authorization` 头；
 *   2. 1001/1002（未登录/Token 失效）→ 清会话并广播，由 app.js 跳登录页；
 *   3. 其余业务错误 → 抛 ApiError，调用方 `catch` 或让它自动弹 Toast。
 */

import { store } from './store.js'
import { notifyError } from './ui.js'

/** 业务错误码，与后端 `common/errors.py` 的 ErrorCode 一一对应。 */
export const ErrorCode = {
  SUCCESS: 0,
  LOGIN_FAILED: 1001,
  TOKEN_INVALID: 1002,
  NO_PERMISSION: 1003,
  PARAM_ERROR: 2000,
  NOT_FOUND: 3001,
  COURSE_CLOSED: 4001,
  ALREADY_SELECTED: 4002,
  TIME_CONFLICT: 4003,
  COURSE_FULL: 4004,
  NOT_SELECTED: 4005,
  COURSE_DELETE_FORBIDDEN: 4006,
  DUPLICATE_KEY: 4007,
  SYSTEM_ERROR: 5000,
}

/** 选课失败的错误码 —— 页面据此决定是弹提示还是亮冲突告警条。 */
export const SELECT_FAILURES = [
  ErrorCode.COURSE_CLOSED, ErrorCode.ALREADY_SELECTED,
  ErrorCode.TIME_CONFLICT, ErrorCode.COURSE_FULL,
]

export class ApiError extends Error {
  constructor(code, message) {
    super(message)
    this.name = 'ApiError'
    this.code = code
  }
}

async function request(method, path, { body, params, silent = false } = {}) {
  const url = new URL(path, window.location.origin)
  Object.entries(params || {}).forEach(([key, value]) => {
    // 空值不参与查询：后端把空串当成「不筛选」，但显式传空串可读性差，这里直接省略
    if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, value)
  })

  const headers = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (store.token) headers.Authorization = `Bearer ${store.token}`

  let payload
  try {
    const response = await fetch(url, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    })
    payload = await response.json()
  } catch (exc) {
    // 网络断了 / 服务没起来 / 返回的不是 JSON —— 都要给出人能看懂的一句话
    const error = new ApiError(ErrorCode.SYSTEM_ERROR, '网络异常，请确认服务已启动')
    if (!silent) notifyError(error.message)
    throw error
  }

  if (payload.code === ErrorCode.SUCCESS) return payload.data

  // 未登录或 Token 失效：清掉本地会话，广播给 app.js 去跳登录页
  if (payload.code === ErrorCode.LOGIN_FAILED || payload.code === ErrorCode.TOKEN_INVALID) {
    store.clear()
    window.dispatchEvent(new CustomEvent('app:unauthorized'))
  } else if (!silent) {
    notifyError(payload.message || '操作失败')
  }

  throw new ApiError(payload.code, payload.message || '操作失败')
}

export const api = {
  get: (path, params, options) => request('GET', path, { params, ...options }),
  post: (path, body, options) => request('POST', path, { body, ...options }),
  put: (path, body, options) => request('PUT', path, { body, ...options }),
  patch: (path, body, options) => request('PATCH', path, { body, ...options }),
  del: (path, params, options) => request('DELETE', path, { params, ...options }),

  /** 分页查询统一走这里：后端分页体固定为 {list,total,page,size}。 */
  page: (path, params, options) => request('GET', path, { params, ...options }),
}

/** 分页参数规范化。后端对非法值有兜底，前端这里只是保持请求体干净。 */
export function pageParams({ page = 1, size = 10, ...rest }) {
  return { page, size, ...rest }
}
