/**
 * 会话状态。对标参考项目的 `stores/user.js`（Pinia）。
 *
 * Token 放 localStorage：刷新页面不掉登录态。这是作业演示的取舍 ——
 * 生产环境应改用 HttpOnly Cookie，localStorage 里的 Token 会被 XSS 读走。
 * 本项目的前端全程不使用 innerHTML，从源头上堵住了这个风险。
 */

const TOKEN_KEY = 'cs.token'
const USER_KEY = 'cs.user'

/** 角色展示名，与后端 `security/context.py` 的 ROLE_LABELS 一致。 */
export const ROLE_LABELS = { ADMIN: '管理员', TEACHER: '教师', STUDENT: '学生' }

/** 各角色的默认首页。对标参考项目 router 里的 `homePath()`。 */
export function homePath(role) {
  switch (role) {
    case 'ADMIN': return '/admin/courses'
    case 'TEACHER': return '/teacher/courses'
    case 'STUDENT': return '/student/select'
    default: return '/login'
  }
}

function readJSON(key) {
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export const store = {
  token: localStorage.getItem(TOKEN_KEY) || '',
  user: readJSON(USER_KEY),

  get isLogin() {
    return Boolean(this.token && this.user)
  },

  get role() {
    return this.user ? this.user.role : ''
  },

  get roleLabel() {
    return ROLE_LABELS[this.role] || '未知'
  },

  get displayName() {
    return (this.user && (this.user.realName || this.user.username)) || ''
  },

  setSession(token, user) {
    this.token = token
    this.user = user
    localStorage.setItem(TOKEN_KEY, token)
    localStorage.setItem(USER_KEY, JSON.stringify(user))
  },

  setUser(user) {
    this.user = user
    localStorage.setItem(USER_KEY, JSON.stringify(user))
  },

  clear() {
    this.token = ''
    this.user = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  },
}
