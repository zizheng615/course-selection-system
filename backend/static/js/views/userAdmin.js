/**
 * 账号管理（管理员）。对标参考项目的 `views/admin/UserManage.vue`。
 *
 * 这一页管的是 `sys_user` 本身：登录账号、密码、启用状态。
 * 「关联信息」列把账号与它的学生/教师业务记录对上号（关联类型 + 学号/工号 + 专业/院系），
 * 否则一屏 tea003 / stu042 根本认不出是谁。
 *
 * 两条保护：不能禁用自己、不能删除自己 —— 否则管理员会把自己锁在系统外。
 */

import { api } from '../api.js'
import { h, mount } from '../dom.js'
import { pageCard } from '../layout.js'
import { buildForm, createPager, userStatusTag, validators } from './shared.js'
import {
  actionButtons, confirmDanger, confirmDialog, notifySuccess, openDialog, tag, text,
} from '../ui.js'
import { store } from '../store.js'

const ROLES = [
  { value: '', label: '全部角色' },
  { value: 'ADMIN', label: '管理员' },
  { value: 'TEACHER', label: '教师' },
  { value: 'STUDENT', label: '学生' },
]

const ROLE_TAG = { ADMIN: 'danger', TEACHER: 'warning', STUDENT: 'primary' }

export function render(container) {
  const state = { keyword: '', role: '' }

  const keywordInput = h('input', {
    class: 'input', placeholder: '账号 / 姓名',
    onKeydown: (event) => { if (event.key === 'Enter') applyFilters() },
  })
  const roleSelect = h('select', {
    class: 'select',
    onChange: (event) => { state.role = event.target.value },
  }, ROLES.map((r) => h('option', { value: r.value }, r.label)))

  const body = h('div', {})

  const pager = createPager({
    body,
    columns: [
      { key: 'username', title: '登录账号', render: (row) => h('span', { class: 'mono' }, row.username) },
      { key: 'realName', title: '姓名' },
      { key: 'role', title: '角色', render: (row) => tag(row.roleName, ROLE_TAG[row.role] || 'info') },
      {
        key: 'link', title: '关联信息',
        render: (row) => [
          h('span', {}, row.linkType),
          row.linkNo ? h('span', { class: 'mono small muted', style: { marginLeft: '6px' } }, row.linkNo) : null,
          row.linkExtra ? h('span', { class: 'small muted', style: { marginLeft: '6px' } }, `· ${row.linkExtra}`) : null,
        ],
      },
      { key: 'status', title: '状态', render: (row) => userStatusTag(row.status) },
      { key: 'createdAt', title: '创建时间', render: (row) => h('span', { class: 'small muted' }, text(row.createdAt)) },
      { key: 'actions', title: '操作', className: 'actions', render: (row) => actionButtons([
        { label: '改账号 / 密码', onClick: () => openCredentials(row) },
        {
          label: Number(row.status) === 1 ? '禁用' : '启用',
          disabled: row.id === (store.user && store.user.userId),
          onClick: () => toggleStatus(row),
        },
        {
          label: '删除', danger: true,
          disabled: row.id === (store.user && store.user.userId),
          onClick: () => removeUser(row),
        },
      ]) },
    ],
    load: (page, size) => api.get('/api/users', {
      keyword: state.keyword, role: state.role, page, size,
    }),
    emptyText: '没有符合条件的账号',
  })

  const filters = h('div', { class: 'toolbar' }, [
    keywordInput, roleSelect,
    h('button', { class: 'btn btn--primary', onClick: applyFilters }, '查询'),
    h('button', { class: 'btn', onClick: resetFilters }, '重置'),
  ])

  mount(container, pageCard('账号管理', [], h('div', {}, [filters, body])),
    h('div', { class: 'small muted' },
      '学生与教师的账号在其「学生管理 / 教师管理」中开通，这里负责改账号、重置密码与启停。'))

  pager.reload(1)

  function applyFilters() {
    state.keyword = keywordInput.value.trim()
    pager.reset()
  }

  function resetFilters() {
    keywordInput.value = ''
    roleSelect.value = ''
    state.keyword = ''
    state.role = ''
    pager.reset()
  }

  function openCredentials(row) {
    const form = buildForm([
      {
        key: 'username', label: '登录账号', value: row.username, required: true,
        validate: validators.all(
          validators.required('登录账号'),
          (value) => (value.trim().length >= 3 ? '' : '账号至少 3 位'),
        ),
      },
      {
        key: 'password', label: '新密码', value: '',
        hint: '留空则只改账号，不修改密码',
        validate: (value) => (!value || value.length >= 6 ? '' : '密码至少 6 位'),
      },
    ])

    openDialog({
      title: `修改账号 · ${row.realName}`,
      body: form.node,
      confirmText: '保存',
      onConfirm: async () => {
        if (!form.validate()) return false
        const values = form.values()
        const payload = { username: values.username.trim() }
        if (values.password) payload.password = values.password
        try {
          await api.put(`/api/users/${row.id}/credentials`, payload)
        } catch {
          return false
        }
        notifySuccess(values.password ? '账号与密码已更新' : '登录账号已更新')
        pager.reload()
        return true
      },
    })
  }

  async function toggleStatus(row) {
    const next = Number(row.status) === 1 ? 0 : 1
    const label = next === 1 ? '启用' : '禁用'
    const confirmed = await confirmDialog({
      title: `${label}账号`,
      message: `确定要${label}账号「${row.username}」吗？${next === 0 ? '禁用后该用户将无法登录系统。' : ''}`,
      confirmText: label,
    })
    if (!confirmed) return
    await api.patch(`/api/users/${row.id}/status`, undefined, { params: { status: next } })
    notifySuccess(`账号已${label}`)
    pager.reload()
  }

  async function removeUser(row) {
    const confirmed = await confirmDanger('删除账号',
      `确定删除账号「${row.username}」？已绑定学生或教师记录的账号不允许删除。`)
    if (!confirmed) return
    try {
      await api.del(`/api/users/${row.id}`, undefined, { silent: true })
      notifySuccess('账号已删除')
      pager.reload()
    } catch (error) {
      openDialog({
        title: '无法删除', size: 'sm', confirmText: '知道了',
        body: h('div', { style: { lineHeight: '1.9' } }, error.message),
      })
    }
  }
}
