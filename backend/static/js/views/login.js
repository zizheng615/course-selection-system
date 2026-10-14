/**
 * 登录页。对标参考项目的 `views/Login.vue`：左侧品牌区 + 右侧表单。
 *
 * 登录成功后跳 `homePath(role)`；如果是被路由守卫从某个页面踢回来的，
 * 优先跳回原来那一页（`route.redirect`）。
 */

import { api } from '../api.js'
import { h, mount } from '../dom.js'
import { homePath, store } from '../store.js'
import { navigate } from '../router.js'
import { field, notifySuccess } from '../ui.js'

/** 演示账号：点一下自动填入，省得手打。密码都是 123456。 */
const DEMO_ACCOUNTS = [
  { username: 'admin', label: '管理员' },
  { username: 'tea001', label: '教师' },
  { username: 'stu001', label: '学生' },
]

export function render(container, route) {
  const usernameInput = h('input', { class: 'input', placeholder: '请输入登录账号', value: 'admin' })
  const passwordInput = h('input', { class: 'input', type: 'password', placeholder: '请输入密码', value: '123456' })
  const usernameField = field('登录账号', usernameInput, { required: true })
  const passwordField = field('密码', passwordInput, { required: true })

  let submitting = false
  const submitButton = h('button', { class: 'btn btn--primary btn--block login__submit', onClick: submit }, '登 录')

  async function submit() {
    if (submitting) return

    const username = usernameInput.value.trim()
    const password = passwordInput.value
    const okUser = usernameField.setError(username ? '' : '请输入登录账号')
    const okPass = passwordField.setError(password ? '' : '请输入密码')
    if (!okUser || !okPass) return

    submitting = true
    submitButton.classList.add('btn--loading')
    submitButton.textContent = '登录中…'
    try {
      const data = await api.post('/api/auth/login', { username, password }, { silent: true })
      store.setSession(data.token, data)
      notifySuccess(`欢迎回来，${data.realName || data.username}`)
      // 守卫记下的目标页优先；否则去本角色首页
      const target = route.redirect && route.redirect !== '/login' ? route.redirect : homePath(data.role)
      navigate(target)
    } catch (error) {
      // 账号不存在与密码错误共用一条提示（后端已做防枚举），这里原样展示即可
      passwordField.setError(error.message || '登录失败')
      passwordInput.focus()
      passwordInput.select()
    } finally {
      submitting = false
      submitButton.classList.remove('btn--loading')
      submitButton.textContent = '登 录'
    }
  }

  // 回车直接提交
  for (const input of [usernameInput, passwordInput]) {
    input.addEventListener('keydown', (event) => { if (event.key === 'Enter') submit() })
  }

  const page = h('div', { class: 'login' }, [
    h('div', { class: 'login__brand' }, [
      h('h1', {}, '高校选课管理系统'),
      h('p', {}, '面向学分制教学管理的选课平台 —— 课程与排课管理、学生选课与退课、成绩录入、统计报表，以及一个懂系统用法的智能助手。'),
      h('ul', { class: 'login__points' }, [
        h('li', {}, '有限课容量下的并发选课，不多录一个名额'),
        h('li', {}, '上课时间冲突自动识别，选课前就拦下'),
        h('li', {}, '软退课保留修读记录，容量精确归还'),
        h('li', {}, '管理员 / 教师 / 学生三种角色各司其职'),
      ]),
    ]),
    h('div', { class: 'login__panel' }, h('div', { class: 'login__form' }, [
      h('div', { class: 'login__title' }, '登录'),
      h('div', { class: 'login__sub' }, '请使用教务处下发的账号登录'),
      usernameField,
      passwordField,
      submitButton,
      h('div', { class: 'login__hint' }, [
        h('div', {}, ['演示账号密码均为 ', h('b', {}, '123456')]),
        h('div', { class: 'login__accounts' }, DEMO_ACCOUNTS.map((account) =>
          h('button', {
            type: 'button',
            onClick: () => {
              usernameInput.value = account.username
              passwordInput.value = '123456'
              submit()
            },
          }, `${account.label} ${account.username}`))),
      ]),
    ])),
  ])

  mount(container, page)
  usernameInput.focus()
}
