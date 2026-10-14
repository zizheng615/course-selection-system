/**
 * 教师管理（管理员）。对标参考项目的 `views/admin/TeacherManage.vue`。
 *
 * 与「学生管理」同构：新增时自动开登录账号（账号默认等于工号，密码 123456）；
 * 已有课程的教师不允许删除。院系筛选在参考项目里也是**自由输入**而不是下拉，
 * 这里保持一致。
 */

import { api } from '../api.js'
import { h, mount } from '../dom.js'
import { pageCard } from '../layout.js'
import { buildForm, createPager, validators } from './shared.js'
import {
  actionButtons, confirmDanger, notifySuccess, openDialog, tag, text,
} from '../ui.js'

const TITLES = ['教授', '副教授', '讲师', '助教']

export function render(container) {
  const state = { keyword: '', dept: '' }

  const keywordInput = h('input', {
    class: 'input', placeholder: '工号 / 姓名',
    onKeydown: (event) => { if (event.key === 'Enter') applyFilters() },
  })
  const deptInput = h('input', {
    class: 'input', placeholder: '所属院系（全部）',
    onKeydown: (event) => { if (event.key === 'Enter') applyFilters() },
  })

  const body = h('div', {})

  const pager = createPager({
    body,
    columns: [
      { key: 'teacherNo', title: '工号', render: (row) => h('span', { class: 'mono' }, row.teacherNo) },
      { key: 'name', title: '姓名' },
      { key: 'title', title: '职称', render: (row) => text(row.title) },
      { key: 'dept', title: '所属院系' },
      {
        key: 'account', title: '登录账号',
        render: (row) => (row.userId ? tag('已开通', 'success') : tag('未开通', 'info')),
      },
      { key: 'actions', title: '操作', className: 'actions', render: (row) => actionButtons([
        { label: '编辑', onClick: () => openForm(row) },
        { label: '删除', danger: true, onClick: () => removeTeacher(row) },
      ]) },
    ],
    load: (page, size) => api.get('/api/teachers', {
      keyword: state.keyword, dept: state.dept, page, size,
    }),
    emptyText: '没有符合条件的教师',
  })

  const filters = h('div', { class: 'toolbar' }, [
    keywordInput, deptInput,
    h('button', { class: 'btn btn--primary', onClick: applyFilters }, '查询'),
    h('button', { class: 'btn', onClick: resetFilters }, '重置'),
  ])

  mount(container, pageCard('教师管理',
    [h('button', { class: 'btn btn--primary', onClick: () => openForm(null) }, '＋ 新增教师')],
    h('div', {}, [filters, body])),
    h('div', { class: 'small muted' }, '新增教师会自动创建登录账号：账号默认等于工号，初始密码 123456。'))

  pager.reload(1)

  function applyFilters() {
    state.keyword = keywordInput.value.trim()
    state.dept = deptInput.value.trim()
    pager.reset()
  }

  function resetFilters() {
    keywordInput.value = ''
    deptInput.value = ''
    state.keyword = ''
    state.dept = ''
    pager.reset()
  }

  async function removeTeacher(row) {
    const confirmed = await confirmDanger('删除教师',
      `确定删除教师「${row.name}（${row.teacherNo}）」及其登录账号？名下有课程的教师不允许删除。`)
    if (!confirmed) return
    try {
      await api.del(`/api/teachers/${row.id}`, undefined, { silent: true })
      notifySuccess('教师已删除')
      pager.reload()
    } catch (error) {
      openDialog({
        title: '无法删除', size: 'sm', confirmText: '知道了',
        body: h('div', { style: { lineHeight: '1.9' } }, error.message),
      })
    }
  }

  function openForm(row) {
    const isEdit = Boolean(row)
    const specs = [
      {
        key: 'teacherNo', label: '工号', value: row ? row.teacherNo : '',
        required: true, placeholder: '如 T2023011',
        validate: validators.required('工号'),
      },
      {
        key: 'name', label: '姓名', value: row ? row.name : '',
        required: true, validate: validators.required('姓名'),
      },
      {
        key: 'title', label: '职称',
        node: h('select', { class: 'select' }, TITLES.map((t) => h('option', {
          value: t, selected: (row ? row.title : '讲师') === t,
        }, t))),
      },
      {
        key: 'dept', label: '所属院系', value: row ? row.dept : '',
        required: true, validate: validators.required('所属院系'),
      },
    ]

    if (!isEdit) {
      specs.push(
        {
          key: 'username', label: '登录账号', value: '', hint: '选填，留空则默认使用工号',
          validate: (value) => (!value || value.trim().length >= 3 ? '' : '账号至少 3 位'),
        },
        {
          key: 'password', label: '初始密码', value: '', hint: '选填，留空则使用默认密码 123456',
          validate: (value) => (!value || value.length >= 6 ? '' : '密码至少 6 位'),
        },
      )
    }

    const form = buildForm(specs)

    openDialog({
      title: isEdit ? `编辑教师 · ${row.name}` : '新增教师',
      size: 'lg',
      body: form.node,
      confirmText: isEdit ? '保存' : '创建',
      onConfirm: async () => {
        if (!form.validate()) return false
        const values = form.values()
        const payload = {
          teacherNo: values.teacherNo.trim(),
          name: values.name.trim(),
          title: values.title,
          dept: values.dept.trim(),
        }
        if (!isEdit) {
          if (values.username.trim()) payload.username = values.username.trim()
          if (values.password) payload.password = values.password
        }
        try {
          if (isEdit) await api.put(`/api/teachers/${row.id}`, payload)
          else await api.post('/api/teachers', payload)
        } catch {
          return false
        }
        notifySuccess(isEdit ? '教师信息已更新' : '教师已创建，登录账号已自动开通')
        pager.reload()
        return true
      },
    })
  }
}
