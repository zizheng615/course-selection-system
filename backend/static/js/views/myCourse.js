/**
 * 我的课程（教师）。对标参考项目的 `views/teacher/MyCourse.vue`。
 *
 * 教师能看到自己任教的课程、每门课的选课人数，以及**学生名单**；
 * 成绩在名单里逐行录入（0~100 分）。
 *
 * 注意：已退课的学生不在名单里（名单只取 SELECTED 记录），
 * 所以「给已退课的学生录成绩」这件事在界面上根本不会发生 ——
 * 后端仍然会拦（4005），但那属于防御，不是正常路径。
 */

import { api } from '../api.js'
import { h, mount } from '../dom.js'
import { pageCard } from '../layout.js'
import { scoreCell, semesterSelect } from './shared.js'
import {
  actionButtons, dataTable, notifySuccess, num, openDialog, quotaBar, text,
} from '../ui.js'

export function render(container) {
  const state = { semester: '' }

  const body = h('div', {})
  const summary = h('div', { class: 'small muted mb-12' })

  const semesterNode = semesterSelect({
    onChange: (value) => { state.semester = value; load() },
  })

  mount(container, pageCard('我的课程', [
    h('span', { class: 'muted' }, '学期：'), semesterNode,
  ], h('div', {}, [summary, body])))

  async function load() {
    mount(body, h('div', { class: 'loading' }, [h('div', { class: 'spinner' }), '加载中…']))
    let rows = []
    try {
      rows = await api.get('/api/courses/my', { semester: state.semester })
    } catch { /* 提示已弹 */ }

    const totalStudents = rows.reduce((sum, r) => sum + Number(r.enrolledCount || 0), 0)
    summary.textContent = `共任教 ${rows.length} 门课程 · 累计 ${totalStudents} 人选课`

    mount(body, dataTable({
      columns: [
        { key: 'courseCode', title: '课程代码', render: (row) => h('span', { class: 'mono' }, text(row.courseCode)) },
        { key: 'name', title: '课程名称' },
        { key: 'credit', title: '学分', render: (row) => num(row.credit) },
        { key: 'hours', title: '学时', render: (row) => text(row.hours) },
        { key: 'courseType', title: '类型', render: (row) => text(row.courseType) },
        { key: 'semester', title: '学期', render: (row) => text(row.semester) },
        { key: 'quota', title: '选课情况', width: '150px', render: (row) => quotaBar(row.enrolledCount, row.capacity) },
        { key: 'actions', title: '操作', className: 'actions', render: (row) => actionButtons([
          { label: `学生名单（${row.enrolledCount ?? 0}）`, onClick: () => openRoster(row) },
        ]) },
      ],
      rows,
      emptyText: '本学期你还没有任教课程',
    }))
  }

  /** 学生名单弹窗：列出选课学生并可逐行录成绩。 */
  async function openRoster(course) {
    const rosterBody = h('div', {},
      h('div', { class: 'loading' }, [h('div', { class: 'spinner' }), '加载中…']))

    const dialog = openDialog({
      title: `学生名单 · ${course.name}`,
      size: 'lg',
      hideFooter: true,
      body: h('div', {}, [
        h('div', { class: 'small muted mb-12' }, '成绩范围 0 ~ 100 分，留空表示尚未录入；已退课的学生不在名单中。'),
        rosterBody,
      ]),
    })

    await refresh()

    async function refresh() {
      let rows = []
      try {
        rows = await api.get(`/api/courses/${course.id}/students`)
      } catch { /* 提示已弹 */ }

      mount(rosterBody, dataTable({
        columns: [
          { key: 'studentNo', title: '学号', render: (row) => h('span', { class: 'mono' }, text(row.studentNo)) },
          { key: 'studentName', title: '姓名' },
          { key: 'major', title: '专业', render: (row) => text(row.major) },
          { key: 'grade', title: '年级', render: (row) => text(row.grade) },
          { key: 'score', title: '成绩', render: (row) => scoreCell(row.score) },
          { key: 'actions', title: '操作', className: 'actions', render: (row) => actionButtons([
            { label: row.score === null || row.score === undefined ? '录入成绩' : '修改成绩', onClick: () => openScore(row) },
          ]) },
        ],
        rows,
        emptyText: '还没有学生选这门课',
      }))
    }

    function openScore(student) {
      const input = h('input', {
        class: 'input', type: 'number', min: 0, max: 100, step: 1,
        value: student.score === null || student.score === undefined ? '' : String(student.score),
        placeholder: '0 ~ 100',
      })
      const error = h('div', { class: 'field__error' })

      openDialog({
        title: `录入成绩 · ${student.studentName}`,
        size: 'sm',
        confirmText: '保存',
        body: h('div', {}, [
          h('div', { class: 'muted small mb-12' }, `${student.studentNo} · ${student.major || '—'} · ${course.name}`),
          h('label', { class: 'field__label' }, '成绩'),
          input,
          error,
        ]),
        onConfirm: async () => {
          const raw = input.value.trim()
          const value = Number(raw)
          if (raw === '' || Number.isNaN(value)) {
            error.textContent = '请输入成绩'
            input.classList.add('is-invalid')
            return false
          }
          if (value < 0 || value > 100) {
            error.textContent = '成绩必须在 0 ~ 100 之间'
            input.classList.add('is-invalid')
            return false
          }
          try {
            await api.patch('/api/enrollments/score', { enrollmentId: student.enrollmentId, score: value })
          } catch {
            return false
          }
          notifySuccess(`已录入 ${student.studentName} 的成绩：${value}`)
          await refresh()
          return true
        },
      })
    }
  }

  load()
}
