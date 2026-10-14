/**
 * 统计报表（管理员）。对标参考项目的 `views/admin/StatsReport.vue`。
 *
 * 三张报表各自回答一个问题：
 *   * 热门课程 Top-N —— 哪些课快满了、满座率多少；
 *   * 各专业选课分布 —— 哪些专业选课活跃（**没有选课记录的专业也在表里**，
 *     否则会误以为那个专业不存在）；
 *   * 教师工作量 —— 每位教师带多少课、多少学生、多少学分（**没排课的教师同样在表里**）。
 *
 * 后端这两处用的是 LEFT JOIN，所以「零行」也会出现。前端不要自作主张过滤掉它们。
 */

import { api } from '../api.js'
import { h, mount } from '../dom.js'
import { pageCard } from '../layout.js'
import { semesterSelect } from './shared.js'
import { dataTable, num, quotaBar, statistic, text } from '../ui.js'

const LIMITS = [5, 10, 15, 20]

export function render(container) {
  const state = { semester: '', limit: 10 }

  const limitSelect = h('select', {
    class: 'select',
    onChange: (event) => { state.limit = Number(event.target.value); loadPopular() },
  }, LIMITS.map((n) => h('option', { value: n, selected: n === state.limit }, `Top ${n}`)))

  const semesterNode = semesterSelect({
    onChange: (value) => { state.semester = value; reloadAll() },
  })

  const summary = h('div', { class: 'stat-grid mb-16' })
  const popular = h('div', {})
  const majors = h('div', {})
  const workload = h('div', {})

  mount(container,
    h('div', { class: 'card' }, h('div', { class: 'toolbar', style: { marginBottom: 0 } }, [
      h('span', { class: 'muted' }, '统计学期：'), semesterNode,
    ])),
    summary,
    pageCard('热门课程', [limitSelect], popular, '按选课人数排序，满座率 = 已选 / 容量'),
    pageCard('各专业选课分布', [], majors, '含尚无选课记录的专业'),
    pageCard('教师工作量', [], workload, '含尚未排课的教师'))

  loadAll()

  function reloadAll() {
    loadPopular()
    loadMajors()
    loadWorkload()
  }

  async function loadAll() {
    await Promise.all([loadPopular(), loadMajors(), loadWorkload()])
    paintSummary()
  }

  let popularRows = []
  let majorRows = []
  let workloadRows = []

  async function loadPopular() {
    mount(popular, h('div', { class: 'loading' }, [h('div', { class: 'spinner' }), '加载中…']))
    try {
      popularRows = await api.get('/api/stats/popular-courses',
        { semester: state.semester, limit: state.limit })
    } catch {
      popularRows = []
    }
    mount(popular, dataTable({
      columns: [
        { key: 'courseCode', title: '课程代码', render: (row) => h('span', { class: 'mono' }, text(row.courseCode)) },
        { key: 'courseName', title: '课程名称' },
        { key: 'teacherName', title: '授课教师', render: (row) => text(row.teacherName) },
        { key: 'capacity', title: '容量', render: (row) => text(row.capacity) },
        { key: 'selectedCount', title: '已选人数', render: (row) => text(row.selectedCount) },
        { key: 'fillRate', title: '满座率', width: '150px', render: (row) => quotaBar(row.selectedCount, row.capacity) },
        {
          key: 'rate', title: '百分比',
          render: (row) => `${num(row.fillRate, 2)}%`,
        },
      ],
      rows: popularRows,
      emptyText: '该学期暂无选课数据',
    }))
    paintSummary()
  }

  async function loadMajors() {
    mount(majors, h('div', { class: 'loading' }, [h('div', { class: 'spinner' }), '加载中…']))
    try {
      majorRows = await api.get('/api/stats/major-distribution')
    } catch {
      majorRows = []
    }
    mount(majors, dataTable({
      columns: [
        { key: 'major', title: '专业', render: (row) => text(row.major) },
        { key: 'studentCount', title: '学生人数', render: (row) => text(row.studentCount) },
        { key: 'enrollmentCount', title: '选课人次', render: (row) => text(row.enrollmentCount) },
        {
          key: 'avgCoursesPerStudent', title: '人均选课',
          render: (row) => h('span', {}, [num(row.avgCoursesPerStudent, 2), h('span', { class: 'muted small' }, ' 门')]),
        },
      ],
      rows: majorRows,
      emptyText: '暂无专业数据',
    }))
    paintSummary()
  }

  async function loadWorkload() {
    mount(workload, h('div', { class: 'loading' }, [h('div', { class: 'spinner' }), '加载中…']))
    try {
      workloadRows = await api.get('/api/stats/teacher-workload', { semester: state.semester })
    } catch {
      workloadRows = []
    }
    mount(workload, dataTable({
      columns: [
        { key: 'teacherName', title: '教师', render: (row) => text(row.teacherName) },
        { key: 'title', title: '职称', render: (row) => text(row.title) },
        { key: 'dept', title: '所属院系', render: (row) => text(row.dept) },
        { key: 'courseCount', title: '课程门数', render: (row) => text(row.courseCount) },
        { key: 'totalStudents', title: '学生人次', render: (row) => text(row.totalStudents) },
        { key: 'totalCredit', title: '学分合计', render: (row) => num(row.totalCredit, 1) },
      ],
      rows: workloadRows,
      emptyText: '暂无教师数据',
    }))
    paintSummary()
  }

  /** 顶部概览。全部由三张报表的数据汇总而来，不额外发请求。 */
  function paintSummary() {
    if (!majorRows.length && !workloadRows.length) return
    const totalEnrollments = majorRows.reduce((sum, r) => sum + Number(r.enrollmentCount || 0), 0)
    const totalStudents = majorRows.reduce((sum, r) => sum + Number(r.studentCount || 0), 0)
    const teacherCount = workloadRows.length
    const avg = totalStudents ? (totalEnrollments / totalStudents) : 0
    const top = popularRows.length
      ? popularRows.reduce((best, r) => (Number(r.selectedCount) > Number(best.selectedCount) ? r : best), popularRows[0])
      : null

    mount(summary, [
      statistic('选课总人次', totalEnrollments, ' 次', '含全部学期的已选记录'),
      statistic('在册学生', totalStudents, ' 人', `${majorRows.length} 个专业`),
      statistic('任课教师', teacherCount, ' 人', `${state.semester || '全部学期'}口径`),
      statistic('人均选课', num(avg, 2), ' 门', '选课人次 / 学生人数'),
      top ? statistic('最热门课程', text(top.courseName), '', `已选 ${top.selectedCount} 人 / 容量 ${top.capacity}`) : null,
    ].filter(Boolean))
  }
}
