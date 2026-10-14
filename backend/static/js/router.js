/**
 * 路由表 —— **开闭原则的第四个扩展点**。
 *
 * 新增一个页面 = 在 `VIEWS`（views/index.js）里注册一个渲染函数，
 * 再往下面的 `routes` 追加一条记录。`app.js` 的调度逻辑不需要任何改动。
 * 注意三张表要一起改（routes / VIEWS / layout.js 的 MENU_GROUPS），
 * 漏掉其中一张的症状是「点菜单白屏」，很难在人工点测里一眼看出来。
 *
 * 用 hash 路由（`#/admin/courses`）而不是 History API：前端由 FastAPI 的
 * StaticFiles 直接托管，没有 SPA fallback 重写规则，History 模式下刷新
 * `/admin/courses` 会 404。hash 模式刷新永远命中 index.html。
 */

import { store, homePath } from './store.js'

export const routes = [
  { path: '/login', view: 'login', title: '登录', public: true },

  // ---------- 管理员 ----------
  { path: '/admin/courses', view: 'courseAdmin', title: '课程管理', roles: ['ADMIN'] },
  { path: '/admin/schedules', view: 'scheduleAdmin', title: '排课管理', roles: ['ADMIN'] },
  { path: '/admin/students', view: 'studentAdmin', title: '学生管理', roles: ['ADMIN'] },
  { path: '/admin/teachers', view: 'teacherAdmin', title: '教师管理', roles: ['ADMIN'] },
  { path: '/admin/users', view: 'userAdmin', title: '账号管理', roles: ['ADMIN'] },
  { path: '/admin/enrollments', view: 'enrollmentAdmin', title: '选课记录', roles: ['ADMIN'] },
  { path: '/admin/stats', view: 'statsAdmin', title: '统计报表', roles: ['ADMIN'] },

  // ---------- 学生 ----------
  { path: '/student/select', view: 'courseSelect', title: '选课中心', roles: ['STUDENT'] },
  { path: '/student/timetable', view: 'myTimetable', title: '我的课表', roles: ['STUDENT'] },

  // ---------- 教师 ----------
  { path: '/teacher/courses', view: 'myCourse', title: '我的课程', roles: ['TEACHER'] },
]

/** 当前路径（不含 `#`）。空 hash 视为首页。 */
export function currentPath() {
  const raw = window.location.hash.replace(/^#/, '')
  return raw || '/'
}

export function navigate(path) {
  if (currentPath() === path) return
  window.location.hash = path
}

/** 按路径找路由记录。 */
export function match(path) {
  return routes.find((route) => route.path === path) || null
}

/**
 * 路由守卫。对标参考项目 `router.beforeEach`：
 * 未登录去登录页（记住来源）、已登录访问登录页送回首页、角色不符回自己的首页。
 *
 * @returns {object} 最终应当渲染的路由记录
 */
export function resolve(path) {
  const target = match(path)

  if (!target) return match(store.isLogin ? homePath(store.role) : '/login')
  if (target.public) return store.isLogin ? match(homePath(store.role)) : target
  if (!store.isLogin) return { ...match('/login'), redirect: path }
  if (target.roles && !target.roles.includes(store.role)) return match(homePath(store.role))

  return target
}

/** 已登录时把 `#/` 换成本角色的首页，避免空白页。 */
export function ensureHome() {
  if (currentPath() === '/' || currentPath() === '') navigate(store.isLogin ? homePath(store.role) : '/login')
}

export { homePath }
