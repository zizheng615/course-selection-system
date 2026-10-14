/**
 * 学生管理（管理员）。对标参考项目的 `views/admin/StudentManage.vue`。
 *
 * 两个要点：
 *   * 新增学生时**自动创建登录账号**。登录账号默认等于学号、密码默认 123456，
 *     所以表单里这两项是可选的 —— 留空即用默认值，不要把它们做成必填。
 *   * 删除受保护：只要该学生有任何选课记录（**含已退课的**）就拒绝删除，
 *     否则修读历史会凭空消失。
 */

import { api } from '../api.js'
import { h, mount } from '../dom.js'
import { pageCard } from '../layout.js'
import { buildForm, createPager, validators } from './shared.js'
import {
  actionButtons, confirmDanger, notifySuccess, openDialog, tag, text,
} from '../ui.js'

const GENDERS = [{ value: 'M', label: '男' }, { value: 'F', label: '女' }]

function genderLabel(value) {
  return value === 'F' ? '女' : '男'
}

export function render(container) {
  const state = { keyword: '', major: '' }

  const keywordInput = h('input', {
    class: 'input', placeholder: '学号 / 姓名',
    onKeydown: (event) => { if (event.key === 'Enter') applyFilters() },
  })
  const majorSelect = h('select', {
    class: 'select',
    onChange: (event) => { state.major = event.target.value },
  }, h('option', { value: '' }, '全部专业'))

  const body = h('div', {})

  const pager = createPager({
    body,
    columns: [
      { key: 'studentNo', title: '学号', render: (row) => h('span', { class: 'mono' }, row.studentNo) },
      { key: 'name', title: '姓名' },
      { key: 'gender', title: '性别', render: (row) => genderLabel(row.gender) },
      { key: 'major', title: '专业' },
      { key: 'grade', title: '年级', render: (row) => text(row.grade) },
      { key: 'phone', title: '手机号', render: (row) => text(row.phone) },
      {
        // StudentVO 里没有登录账号字段（账号属于 sys_user），这里只表达「有没有开号」，
        // 具体账号名要到「账号管理」里看 —— 不猜、不拼一个可能不对的字符串出来
        key: 'account', title: '登录账号',
        render: (row) => (row.userId ? tag('已开通', 'success') : tag('未开通', 'info')),
      },
      { key: 'actions', title: '操作', className: 'actions', render: (row) => actionButtons([
        { label: '编辑', onClick: () => openForm(row) },
        { label: '删除', danger: true, onClick: () => removeStudent(row) },
      ]) },
    ],
    load: (page, size) => api.get('/api/students', {
      keyword: state.keyword, major: state.major, page, size,
    }),
    emptyText: '没有符合条件的学生',
  })

  const filters = h('div', { class: 'toolbar' }, [
    keywordInput, majorSelect,
    h('button', { class: 'btn btn--primary', onClick: applyFilters }, '查询'),
    h('button', { class: 'btn', onClick: resetFilters }, '重置'),
  ])

  mount(container, pageCard('学生管理',
    [h('button', { class: 'btn btn--primary', onClick: () => openForm(null) }, '＋ 新增学生')],
    h('div', {}, [filters, body])),
    h('div', { class: 'small muted' }, '新增学生会自动创建登录账号：账号默认等于学号，初始密码 123456。'))

  loadMajors()
  pager.reload(1)

  function applyFilters() {
    state.keyword = keywordInput.value.trim()
    pager.reset()
  }

  function resetFilters() {
    keywordInput.value = ''
    majorSelect.value = ''
    state.keyword = ''
    state.major = ''
    pager.reset()
  }

  async function loadMajors() {
    try {
      const list = await api.get('/api/students/majors')
      mount(majorSelect, [h('option', { value: '' }, '全部专业')]
        .concat(list.map((m) => h('option', { value: m }, m))))
    } catch { /* 专业选项拿不到不影响列表 */ }
  }

  async function removeStudent(row) {
    const confirmed = await confirmDanger('删除学生',
      `确定删除学生「${row.name}（${row.studentNo}）」及其登录账号？已有选课记录的学生不允许删除。`)
    if (!confirmed) return
    try {
      await api.del(`/api/students/${row.id}`, undefined, { silent: true })
      notifySuccess('学生已删除')
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
        key: 'studentNo', label: '学号', value: row ? row.studentNo : '',
        required: true, placeholder: '如 2023051',
        validate: validators.required('学号'),
      },
      {
        key: 'name', label: '姓名', value: row ? row.name : '',
        required: true, validate: validators.required('姓名'),
      },
      {
        key: 'gender', label: '性别',
        node: h('select', { class: 'select' }, GENDERS.map((g) => h('option', {
          value: g.value, selected: (row ? row.gender : 'M') === g.value,
        }, g.label))),
      },
      {
        key: 'major', label: '专业', value: row ? row.major : '',
        required: true, validate: validators.required('专业'),
      },
      {
        key: 'grade', label: '年级', value: row ? row.grade : '2026',
        required: true, placeholder: '如 2026', validate: validators.required('年级'),
      },
      { key: 'phone', label: '手机号', value: row ? (row.phone || '') : '', placeholder: '选填' },
    ]

    // 登录账号只在新增时可填：账号一旦建好，改账号属于「账号管理」的职责
    if (!isEdit) {
      specs.push(
        {
          key: 'username', label: '登录账号', value: '', hint: '选填，留空则默认使用学号',
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
      title: isEdit ? `编辑学生 · ${row.name}` : '新增学生',
      size: 'lg',
      body: form.node,
      confirmText: isEdit ? '保存' : '创建',
      onConfirm: async () => {
        if (!form.validate()) return false
        const values = form.values()
        const payload = {
          studentNo: values.studentNo.trim(),
          name: values.name.trim(),
          gender: values.gender,
          major: values.major.trim(),
          grade: values.grade.trim(),
          phone: values.phone.trim() || null,
        }
        // 编辑时不传账号密码 —— 那是「账号管理」页面的职责
        if (!isEdit) {
          if (values.username.trim()) payload.username = values.username.trim()
          if (values.password) payload.password = values.password
        }
        try {
          if (isEdit) await api.put(`/api/students/${row.id}`, payload)
          else await api.post('/api/students', payload)
        } catch {
          return false
        }
        notifySuccess(isEdit ? '学生信息已更新' : '学生已创建，登录账号已自动开通')
        pager.reload()
        return true
      },
    })
  }
}
