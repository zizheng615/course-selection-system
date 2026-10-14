/**
 * 前端入口。
 *
 * 职责只有三件：监听 hash 变化 → 交给路由守卫决定渲染哪条路由 → 从页面注册表
 * 里取出渲染函数调用。**这里不出现任何一个具体页面的名字**，所以新增页面
 * 不用改这个文件（开闭原则）。
 */

import { h, mount } from './dom.js'
import { currentPath, navigate, resolve } from './router.js'
import { mountLayout, setActiveMenu, setContent } from './layout.js'
import { store } from './store.js'
import { VIEWS } from './views/index.js'

const root = document.getElementById('app')

/** 当前渲染模式：'login'（整屏）或 'layout'（带侧边栏）。 */
let mode = ''
/** 主布局里的两个可替换节点。 */
let shell = null

function renderStandalone(route) {
  mode = 'login'
  shell = null
  const view = VIEWS[route.view]
  mount(root)
  view(root, route)
}

function renderLayout(route) {
  if (mode !== 'layout') {
    mount(root)
    shell = mountLayout(root)
    mode = 'layout'
  }
  setActiveMenu(route.path)

  const container = h('div', {})
  setContent(shell.headerTitle, shell.content, route.title, container)

  const view = VIEWS[route.view]
  if (!view) {
    mount(container, h('div', { class: 'empty' }, `页面未注册：${route.view}`))
    return
  }
  view(container, route)
}

function render() {
  const path = currentPath()
  const route = resolve(path)

  // 守卫要求换一条路径（未登录 / 角色不符）：改写 hash，由 hashchange 再进来一次
  if (route.path !== path) {
    navigate(route.path)
    return
  }

  if (route.public) renderStandalone(route)
  else renderLayout(route)
}

// 会话失效（Token 过期或被删号）时由 api.js 广播，这里统一跳登录页
window.addEventListener('app:unauthorized', () => {
  mode = ''
  if (currentPath() !== '/login') navigate('/login')
  else render()
})

window.addEventListener('hashchange', render)

// 首屏。地址栏没有 hash 时 `resolve('/')` 匹配不到任何路由，
// 会自动重定向到当前角色的首页（未登录则去登录页），这里不必特判。
render()
