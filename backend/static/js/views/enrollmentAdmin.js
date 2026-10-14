/**
 * 选课记录管理（管理员）。对标参考项目的 `views/admin/EnrollmentManage.vue`。
 *
 * 三种介入手段，语义完全不同，界面上要能分清：
 *   * **代选课**：替学生加一门课，走与学生选课同一套校验（容量、冲突、重复）；
 *   * **退课**（软退课）：记录保留、状态置为 WITHDRAWN、容量归还，学生可以重新选；
 *   * **删除记录**：真正抹掉这一行，同时归还容量 —— 用于录错数据的情况。
 */

import { api } from '../api.js'
import { h, mount } from '../dom.js'
import { pageCard } from '../layout.js'
import { createPager, enrollmentStatusTag, scoreCell } from './shared.js'
import {
  actionButtons, confirmDanger, confirmDialog, notifySuccess, notifyWarning, openDialog, text,
} from '../ui.js'

export function render(container) {
  const state = { keyword: '', status: '' }

  const keywordInput = h('input', {
    class: 'input', placeholder: '学号 / 姓名 / 课程',
    onKeydown: (event) => { if (event.key === 'Enter') applyFilters() },
  })
  const statusSelect = h('select', {
    class: 'select',
    onChange: (event) => { state.status = event.target.value },
  }, [
    h('option', { value: '' }, '全部状态'),
    h('option', { value: 'SELECTED' }, '已选'),
    h('option', { value: 'WITHDRAWN' }, '已退课'),
  ])

  const body = h('div', {})

  const pager = createPager({
    body,
    columns: [
      { key: 'studentNo', title: '学号', render: (row) => h('span', { class: 'mono' }, text(row.studentNo)) },
      { key: 'studentName', title: '姓名' },
      { key: 'major', title: '专业', render: (row) => text(row.major) },
      { key: 'courseCode', title: '课程代码', render: (row) => h('span', { class: 'mono' }, text(row.courseCode)) },
      { key: 'courseName', title: '课程名称' },
      { key: 'teacherName', title: '授课教师', render: (row) => text(row.teacherName) },
      { key: 'semester', title: '学期', render: (row) => text(row.semester) },
      { key: 'status', title: '状态', render: (row) => enrollmentStatusTag(row.status) },
      { key: 'score', title: '成绩', render: (row) => scoreCell(row.score) },
      { key: 'selectedAt', title: '选课时间', render: (row) => h('span', { class: 'small muted' }, text(row.selectedAt)) },
      { key: 'actions', title: '操作', className: 'actions', render: (row) => actionButtons([
        row.status === 'SELECTED'
          ? { label: '退课', onClick: () => withdraw(row) }
          : null,
        { label: '删除记录', danger: true, onClick: () => removeRecord(row) },
      ]) },
    ],
    load: (page, size) => api.get('/api/enrollments', {
      keyword: state.keyword, status: state.status, page, size,
    }),
    emptyText: '没有符合条件的选课记录',
  })

  const filters = h('div', { class: 'toolbar' }, [
    keywordInput, statusSelect,
    h('button', { class: 'btn btn--primary', onClick: applyFilters }, '查询'),
    h('button', { class: 'btn', onClick: resetFilters }, '重置'),
  ])

  mount(container, pageCard('选课记录',
    [h('button', { class: 'btn btn--primary', onClick: openAdminEnroll }, '＋ 代学生选课')],
    h('div', {}, [filters, body])))

  pager.reload(1)

  function applyFilters() {
    state.keyword = keywordInput.value.trim()
    pager.reset()
  }

  function resetFilters() {
    keywordInput.value = ''
    statusSelect.value = ''
    state.keyword = ''
    state.status = ''
    pager.reset()
  }

  async function withdraw(row) {
    const confirmed = await confirmDialog({
      title: '退课确认',
      message: `确定为「${row.studentName}」退掉《${row.courseName}》吗？\n退课后记录会保留（状态变为已退课），名额归还给其他学生。`,
      confirmText: '退课',
    })
    if (!confirmed) return
    await api.patch(`/api/enrollments/record/${row.id}/withdraw`)
    notifySuccess('已退课，名额已归还')
    pager.reload()
  }

  async function removeRecord(row) {
    const confirmed = await confirmDanger('删除选课记录',
      `确定彻底删除「${row.studentName}」的《${row.courseName}》记录吗？\n记录将被抹除且无法恢复，名额同时归还。`)
    if (!confirmed) return
    await api.del(`/api/enrollments/record/${row.id}`)
    notifySuccess('选课记录已删除')
    pager.reload()
  }

  /* ------------------------------------------------------------ 代学生选课 */

  function openAdminEnroll() {
    const studentKeyword = h('input', { class: 'input', placeholder: '输入学号或姓名后点搜索' })
    const studentSelect = h('select', { class: 'select' }, h('option', { value: '' }, '请先搜索学生'))

    const courseKeyword = h('input', { class: 'input', placeholder: '输入课程代码或名称后点搜索' })
    const courseSelect = h('select', { class: 'select' }, h('option', { value: '' }, '请先搜索课程'))

    const searchStudents = async () => {
      const page = await api.get('/api/students', { keyword: studentKeyword.value.trim(), page: 1, size: 50 })
      const list = page.list || []
      mount(studentSelect, list.length
        ? list.map((s) => h('option', { value: s.id }, `${s.studentNo} ${s.name}（${s.major || '—'}）`))
        : h('option', { value: '' }, '没有匹配的学生'))
    }

    const searchCourses = async () => {
      const page = await api.get('/api/courses', { keyword: courseKeyword.value.trim(), page: 1, size: 50 })
      const list = page.list || []
      mount(courseSelect, list.length
        ? list.map((c) => h('option', { value: c.id },
            `${c.courseCode} ${c.name}（${c.teacherName || '未安排'}，余 ${c.remaining ?? '?'}）`))
        : h('option', { value: '' }, '没有匹配的课程'))
    }

    const row = (label, keyword, button, select) => h('div', { class: 'field' }, [
      h('label', { class: 'field__label' }, label),
      h('div', { class: 'row' }, [keyword, h('button', { class: 'btn', onClick: button }, '搜索')]),
      h('div', { class: 'mt-8' }, select),
    ])

    openDialog({
      title: '代学生选课',
      body: h('div', {}, [
        row('学生', studentKeyword, searchStudents, studentSelect),
        row('课程', courseKeyword, searchCourses, courseSelect),
        h('div', { class: 'small muted' }, '容量已满、时间冲突、重复选课都会被拒绝，规则与学生自己选课完全一致。'),
      ]),
      confirmText: '选课',
      onConfirm: async () => {
        const studentId = Number(studentSelect.value)
        const courseId = Number(courseSelect.value)
        if (!studentId) { notifyWarning('请先搜索并选择学生'); return false }
        if (!courseId) { notifyWarning('请先搜索并选择课程'); return false }
        try {
          await api.post('/api/enrollments/admin', { studentId, courseId }, { silent: true })
        } catch (error) {
          openDialog({
            title: '选课失败', size: 'sm', confirmText: '知道了',
            body: h('div', { style: { lineHeight: '1.9' } }, error.message),
          })
          return false
        }
        notifySuccess('代选课成功')
        pager.reload()
        return true
      },
    })

    searchStudents()
    searchCourses()
  }
}
