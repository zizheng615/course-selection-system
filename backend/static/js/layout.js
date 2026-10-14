/**
 * 主布局。对标参考项目的 `layouts/MainLayout.vue`：
 * 左侧分组菜单 + 顶栏（页面标题 / 用户下拉）+ 内容区 + 悬浮 AI 入口。
 *
 * 菜单是**数据驱动的**（下面的 `MENU_GROUPS`），按当前角色过滤后渲染。
 * 这与 `router.js` 的路由表一起构成前端侧的扩展点：加一个页面改这两处数据即可，
 * 布局代码本身不动。
 */

import { h, mount } from './dom.js'
import { store } from './store.js'
import { confirmDialog } from './ui.js'
import { navigate } from './router.js'
import { toggleAssistant, mountAssistant } from './assistant.js'

/** 菜单分组。标题、图标、路径与参考项目 MainLayout.vue 逐项对齐。 */
export const MENU_GROUPS = [
  {
    title: '教学资源',
    roles: ['ADMIN'],
    items: [
      { path: '/admin/courses', title: '课程管理', icon: '▤' },
      { path: '/admin/schedules', title: '排课管理', icon: '◷' },
    ],
  },
  {
    title: '选课管理',
    roles: ['ADMIN'],
    items: [
      { path: '/admin/enrollments', title: '选课记录', icon: '❐' },
      { path: '/admin/stats', title: '统计报表', icon: '◈' },
    ],
  },
  {
    title: '人员管理',
    roles: ['ADMIN'],
    items: [
      { path: '/admin/students', title: '学生管理', icon: '☺' },
      { path: '/admin/teachers', title: '教师管理', icon: '✎' },
      { path: '/admin/users', title: '账号管理', icon: '⚿' },
    ],
  },
  {
    title: '选课',
    roles: ['STUDENT'],
    items: [
      { path: '/student/select', title: '选课中心', icon: '🛒' },
      { path: '/student/timetable', title: '我的课表', icon: '▦' },
    ],
  },
  {
    title: '教学',
    roles: ['TEACHER'],
    items: [{ path: '/teacher/courses', title: '我的课程', icon: '▤' }],
  },
]

let shell = null

/** 挂载布局骨架（只做一次）。 */
export function mountLayout(root) {
  const menuScroll = h('div', { class: 'aside__scroll' })
  const headerTitle = h('div', { class: 'header__title' })
  const content = h('div', { class: 'content' })

  const aside = h('aside', { class: 'aside' }, [
    h('div', { class: 'aside__logo' }, [
      h('span', { class: 'mark' }, '选'),
      h('span', {}, '选课管理系统'),
    ]),
    menuScroll,
  ])

  shell = h('div', { class: 'layout' }, [
    aside,
    h('main', { class: 'main' }, [
      h('header', { class: 'header' }, [headerTitle, buildUserArea()]),
      content,
    ]),
  ])

  mount(root, shell)
  mountAssistant()
  renderMenu(menuScroll)
  return { headerTitle, content }
}

/** 按角色过滤菜单并渲染。 */
function renderMenu(container) {
  const groups = MENU_GROUPS.filter((group) => group.roles.includes(store.role))
  mount(container, groups.map((group) => h('div', {}, [
    h('div', { class: 'menu-group__title' }, group.title),
    ...group.items.map((item) => h('div', {
      class: 'menu-item',
      dataset: { path: item.path },
      onClick: () => navigate(item.path),
    }, [
      h('span', { class: 'ico' }, item.icon),
      h('span', {}, item.title),
    ])),
  ])))
}

/** 高亮当前菜单项。 */
export function setActiveMenu(path) {
  document.querySelectorAll('.menu-item').forEach((item) => {
    item.classList.toggle('is-active', item.dataset.path === path)
  })
}

function buildUserArea() {
  const menu = h('div', { class: 'user__menu hidden' })
  const trigger = h('div', {
    class: 'user__trigger',
    onClick: (event) => { event.stopPropagation(); menu.classList.toggle('hidden') },
  }, [
    h('div', { class: 'avatar' }, store.displayName.slice(0, 1) || '?'),
    h('span', { class: 'user__name' }, store.displayName),
    h('span', { class: 'user__role' }, store.roleLabel),
    h('span', { class: 'muted' }, '▾'),
  ])

  mount(menu, [
    h('button', { onClick: () => { menu.classList.add('hidden'); showProfile() } }, '个人信息'),
    h('button', { onClick: () => { menu.classList.add('hidden'); logout() } }, '退出登录'),
  ])

  // 点击别处收起下拉
  document.addEventListener('click', () => menu.classList.add('hidden'))

  return h('div', { class: 'user' }, [trigger, menu])
}

function showProfile() {
  const user = store.user || {}
  import('./ui.js').then(({ openDialog }) => {
    const rows = [
      ['登录账号', user.username],
      ['姓名', user.realName],
      ['角色', store.roleLabel],
      ['关联编号', user.refId],
    ]
    openDialog({
      title: '个人信息',
      size: 'sm',
      hideFooter: true,
      body: h('div', {}, rows.map(([label, value]) => h('div', {
        class: 'row-between',
        style: { padding: '9px 0', borderBottom: '1px solid var(--b-lighter)' },
      }, [h('span', { class: 'muted' }, label), h('span', {}, String(value ?? '—'))]))),
    })
  })
}

async function logout() {
  const okToGo = await confirmDialog({ title: '退出登录', message: '确定要退出当前账号吗？', confirmText: '退出' })
  if (!okToGo) return
  store.clear()
  navigate('/login')
}

/** 顶栏右侧的 AI 入口按钮（除悬浮球外的第二个入口，键盘用户更容易点到）。 */
export function buildAssistantButton() {
  return h('button', { class: 'btn btn--sm', onClick: toggleAssistant, title: '打开智能助手' }, '🤖 智能助手')
}

/** 内容区整体替换。 */
export function setContent(headerTitle, content, title, node) {
  headerTitle.textContent = title
  content.replaceChildren()
  content.appendChild(node)
  content.scrollTop = 0
}

/** 页面级骨架：卡片 + 工具栏 + 主体。 */
export function pageCard(title, toolbar, body, subtitle = '') {
  return h('div', { class: 'card' }, [
    (title || toolbar)
      ? h('div', { class: 'card__head' }, [
          h('div', { class: 'card__title' }, [title, subtitle ? h('span', { class: 'sub' }, subtitle) : null]),
          toolbar ? h('div', { class: 'row' }, toolbar) : null,
        ])
      : null,
    body,
  ])
}

/** 供页面复用的容器工厂：返回一个可反复替换内容的 div。 */
export function slot() {
  return h('div', {})
}
