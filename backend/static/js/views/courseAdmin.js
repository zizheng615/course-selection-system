/**
 * 课程管理（管理员）。对标参考项目的 `views/admin/CourseManage.vue`。
 *
 * 覆盖：分页列表（关键词 / 学期 / 状态筛选）、新增、修改、开放关闭选课、删除。
 * 「剩余名额」用进度条呈现，比一列数字更容易看出哪门课快满了。
 */

import { api } from '../api.js'
import { h, mount } from '../dom.js'
import { pageCard } from '../layout.js'
import {
  buildForm, courseStatusTag, createPager, semesterSelect, teacherSelect, validators,
} from './shared.js'
import {
  actionButtons, confirmDanger, confirmDialog, notifySuccess, num, openDialog, quotaBar, text,
} from '../ui.js'

const COURSE_TYPES = ['必修', '选修', '限选', '公共']

export function render(container) {
  const state = { keyword: '', semester: '', status: '' }

  const keywordInput = h('input', {
    class: 'input', placeholder: '课程代码 / 名称',
    onKeydown: (event) => { if (event.key === 'Enter') applyFilters() },
  })

  const semesterNode = semesterSelect({ onChange: (value) => { state.semester = value } })
  const statusNode = h('select', {
    class: 'select',
    onChange: (event) => { state.status = event.target.value },
  }, [
    h('option', { value: '' }, '全部状态'),
    h('option', { value: 'OPEN' }, '开放选课'),
    h('option', { value: 'CLOSED' }, '已关闭'),
  ])

  const body = h('div', {})

  const pager = createPager({
    body,
    columns: [
      { key: 'courseCode', title: '课程代码', render: (row) => h('span', { class: 'mono' }, row.courseCode) },
      { key: 'name', title: '课程名称' },
      { key: 'credit', title: '学分', render: (row) => num(row.credit) },
      { key: 'hours', title: '学时', render: (row) => text(row.hours) },
      { key: 'courseType', title: '类型' },
      { key: 'dept', title: '开课院系' },
      { key: 'teacherName', title: '授课教师' },
      { key: 'quota', title: '选课情况', width: '150px', render: (row) => quotaBar(row.enrolledCount, row.capacity) },
      { key: 'semester', title: '学期' },
      { key: 'status', title: '状态', render: (row) => courseStatusTag(row.status) },
      { key: 'actions', title: '操作', className: 'actions', render: (row) => actionButtons([
        { label: '编辑', onClick: () => openForm(row) },
        {
          label: row.status === 'OPEN' ? '关闭选课' : '开放选课',
          onClick: () => toggleStatus(row),
        },
        { label: '删除', danger: true, onClick: () => removeCourse(row) },
      ]) },
    ],
    load: (page, size) => api.get('/api/courses', {
      keyword: state.keyword, semester: state.semester, status: state.status, page, size,
    }),
    emptyText: '没有符合条件的课程',
  })

  function applyFilters() {
    state.keyword = keywordInput.value.trim()
    pager.reset()
  }

  function resetFilters() {
    keywordInput.value = ''
    state.keyword = ''
    state.status = ''
    statusNode.value = ''
    pager.reset()
  }

  const toolbar = [
    h('button', { class: 'btn btn--primary', onClick: () => openForm(null) }, '＋ 新增课程'),
  ]

  const filters = h('div', { class: 'toolbar' }, [
    keywordInput, semesterNode, statusNode,
    h('button', { class: 'btn btn--primary', onClick: applyFilters }, '查询'),
    h('button', { class: 'btn', onClick: resetFilters }, '重置'),
  ])

  mount(container, pageCard('课程管理', toolbar, h('div', {}, [filters, body])),
    h('div', { class: 'small muted' }, '提示：容量不能小于已选人数；已有选课记录的课程不允许删除。'))

  pager.reload(1)

  /* ---------------------------------------------------------------- 动作 */

  async function toggleStatus(row) {
    const next = row.status === 'OPEN' ? 'CLOSED' : 'OPEN'
    const label = next === 'OPEN' ? '开放' : '关闭'
    const confirmed = await confirmDialog({
      title: `${label}选课`,
      message: `确定要${label}《${row.name}》的选课吗？${next === 'CLOSED' ? '关闭后学生将无法再选这门课。' : ''}`,
      confirmText: label,
    })
    if (!confirmed) return
    await api.patch(`/api/courses/${row.id}/status`, undefined, { params: { status: next } })
    notifySuccess(`已${label}《${row.name}》的选课`)
    pager.reload()
  }

  async function removeCourse(row) {
    const confirmed = await confirmDanger('删除课程',
      `确定删除《${row.name}》？若已存在选课记录，系统会拒绝删除以保留修读记录。`)
    if (!confirmed) return
    try {
      await api.del(`/api/courses/${row.id}`, undefined, { silent: true })
      notifySuccess('课程已删除')
      pager.reload()
    } catch (error) {
      // 4006 的提示语由后端给出（含记录条数），直接展示比 Toast 更容易读清
      showBlocked(error.message)
    }
  }

  function showBlocked(message) {
    openDialog({
      title: '无法删除',
      size: 'sm',
      hideFooter: false,
      confirmText: '知道了',
      body: h('div', { style: { lineHeight: '1.9' } }, message),
    })
  }

  /** 新增（row 为 null）或编辑课程。 */
  async function openForm(row) {
    const isEdit = Boolean(row)
    const teachers = await teacherSelect(row ? row.teacherId : '')
    if (!teachers.list.length) {
      openDialog({
        title: '请先创建教师', size: 'sm', hideFooter: true,
        body: '新增课程必须指定授课教师，请先到「教师管理」里添加一位教师。',
      })
      return
    }

    const form = buildForm([
      {
        key: 'courseCode', label: '课程代码', value: row ? row.courseCode : '',
        required: true, placeholder: '如 CS101',
        validate: validators.required('课程代码'),
      },
      {
        key: 'name', label: '课程名称', value: row ? row.name : '',
        required: true, validate: validators.required('课程名称'),
      },
      {
        key: 'credit', label: '学分', value: row ? row.credit : '',
        required: true, placeholder: '0.5 ~ 20',
        validate: validators.all(validators.required('学分'), validators.range('学分', 0.5, 20)),
      },
      {
        key: 'hours', label: '学时', value: row ? row.hours : '',
        required: true, validate: validators.all(validators.required('学时'), validators.positive('学时')),
      },
      {
        key: 'courseType', label: '课程类型',
        node: h('select', { class: 'select' }, COURSE_TYPES.map((t) => h('option', {
          value: t, selected: row ? row.courseType === t : t === '选修',
        }, t))),
      },
      {
        key: 'dept', label: '开课院系', value: row ? row.dept : '',
        required: true, validate: validators.required('开课院系'),
      },
      {
        key: 'semester', label: '学期',
        node: semesterSelect({ value: row ? row.semester : '', allLabel: null }),
      },
      { key: 'teacherId', label: '授课教师', node: teachers.node },
      {
        key: 'capacity', label: '课容量', value: row ? row.capacity : 50,
        required: true, hint: row ? `当前已选 ${row.enrolledCount} 人，不能小于该值` : '',
        validate: validators.all(validators.required('课容量'), validators.positive('课容量')),
      },
      {
        key: 'status', label: '状态',
        node: h('select', { class: 'select' }, [
          h('option', { value: 'OPEN', selected: !row || row.status === 'OPEN' }, '开放选课'),
          h('option', { value: 'CLOSED', selected: Boolean(row) && row.status === 'CLOSED' }, '已关闭'),
        ]),
      },
      {
        key: 'intro', label: '课程简介', value: row ? (row.intro || '') : '', full: true,
        node: h('textarea', { class: 'textarea', rows: 3 }, row ? (row.intro || '') : ''),
      },
    ])

    openDialog({
      title: isEdit ? `编辑课程 · ${row.name}` : '新增课程',
      size: 'lg',
      body: form.node,
      confirmText: isEdit ? '保存' : '创建',
      onConfirm: async () => {
        if (!form.validate()) return false
        const values = form.values()
        const payload = {
          courseCode: values.courseCode.trim(),
          name: values.name.trim(),
          credit: Number(values.credit),
          hours: Number(values.hours),
          courseType: values.courseType,
          dept: values.dept.trim(),
          semester: values.semester,
          teacherId: Number(values.teacherId),
          capacity: Number(values.capacity),
          status: values.status,
          intro: values.intro.trim() || null,
        }
        try {
          if (isEdit) await api.put(`/api/courses/${row.id}`, payload)
          else await api.post('/api/courses', payload)
        } catch {
          return false       // 错误提示已弹出，保持弹窗让用户改
        }
        notifySuccess(isEdit ? '课程已更新' : '课程已创建')
        pager.reload()
        return true
      },
    })
  }
}
