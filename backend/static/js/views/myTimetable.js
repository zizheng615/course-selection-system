/**
 * 我的课表（学生）。对标参考项目的 `views/student/MyTimetable.vue`。
 *
 * 网格按「节次 × 星期」铺开：一门课如果占 1~2 节，两格都要填上，
 * 否则学生看不出这门课到底占多久。一门课有多段上课时间（理论 + 实验）时，
 * 每段各自落到自己的格子里 —— 这正是 `course_schedule` 一对多的意义。
 */

import { api } from '../api.js'
import { h, mount } from '../dom.js'
import { pageCard } from '../layout.js'
import { WEEKDAYS, semesterSelect } from './shared.js'
import { dataTable, num, text } from '../ui.js'

const SECTIONS = Array.from({ length: 12 }, (_, i) => i + 1)

/** 节次所在的时间段，显示在行首，方便学生对着作息表看。 */
const SECTION_TIME = [
  '08:00', '08:55', '10:00', '10:55', '14:00', '14:55',
  '16:00', '16:55', '19:00', '19:55', '20:50', '21:45',
]

export function render(container) {
  const state = { semester: '' }

  const grid = h('div', {})
  const detail = h('div', {})
  const summary = h('div', { class: 'small muted mb-12' })

  const semesterNode = semesterSelect({
    onChange: (value) => { state.semester = value; load() },
  })

  mount(container,
    h('div', { class: 'card' }, [
      h('div', { class: 'row-between' }, [
        h('div', { class: 'row' }, [h('span', { class: 'muted' }, '学期：'), semesterNode]),
        summary,
      ]),
      h('div', { class: 'mt-16' }, grid),
    ]),
    pageCard('已选课程明细', [], detail))

  async function load() {
    mount(grid, h('div', { class: 'loading' }, [h('div', { class: 'spinner' }), '加载中…']))
    let rows = []
    try {
      rows = await api.get('/api/enrollments/my/timetable', { semester: state.semester })
    } catch { /* 提示已弹 */ }

    renderGrid(rows)
    renderDetail(rows)
  }

  function renderGrid(rows) {
    // (weekday, section) -> 该格的课程段
    const cells = new Map()
    for (const item of rows) {
      const from = Number(item.startSection)
      const to = Number(item.endSection)
      for (let section = from; section <= to; section += 1) {
        const key = `${item.weekday}-${section}`
        if (!cells.has(key)) cells.set(key, [])
        cells.get(key).push(item)
      }
    }

    // 整门课（按 courseId 去重）统计，用于概览
    const courseIds = new Set(rows.map((r) => r.courseId))
    const credits = rows.reduce((sum, r) => sum + Number(r.credit || 0), 0)
    summary.textContent = `共 ${courseIds.size} 门课 · ${credits.toFixed(1)} 学分 · ${rows.length} 段上课时间`

    const head = h('tr', {}, [h('th', { class: 'slot' }, '节次'), ...WEEKDAYS.map((d) => h('th', {}, d))])
    const body = SECTIONS.map((section) => h('tr', {}, [
      h('td', { class: 'slot' }, [
        h('div', {}, `第${section}节`),
        h('div', { class: 'small muted' }, SECTION_TIME[section - 1] || ''),
      ]),
      ...WEEKDAYS.map((_, index) => {
        const items = cells.get(`${index + 1}-${section}`) || []
        const cell = h('td', { class: items.length ? '' : 'is-free' })
        items.forEach((item) => cell.appendChild(h('div', { class: 'course-chip' }, [
          h('b', {}, item.courseName || ''),
          h('span', {}, `${item.teacherName || '待定'}${item.classroom ? ` · ${item.classroom}` : ''}`),
          h('span', {}, `第${item.startWeek}~${item.endWeek}周`),
        ])))
        return cell
      }),
    ]))

    mount(grid, h('div', { class: 'table-wrap' },
      h('table', { class: 'timetable' }, [h('thead', {}, head), h('tbody', {}, body)])))
  }

  function renderDetail(rows) {
    mount(detail, dataTable({
      columns: [
        { key: 'courseCode', title: '课程代码', render: (row) => h('span', { class: 'mono' }, text(row.courseCode)) },
        { key: 'courseName', title: '课程名称' },
        { key: 'credit', title: '学分', render: (row) => num(row.credit) },
        { key: 'courseType', title: '类型', render: (row) => text(row.courseType) },
        { key: 'teacherName', title: '授课教师', render: (row) => text(row.teacherName) },
        { key: 'weekdayName', title: '星期', render: (row) => row.weekdayName || WEEKDAYS[row.weekday - 1] || '—' },
        { key: 'sections', title: '节次', render: (row) => `第 ${row.startSection} ~ ${row.endSection} 节` },
        { key: 'weeks', title: '周次', render: (row) => `第 ${row.startWeek} ~ ${row.endWeek} 周` },
        { key: 'classroom', title: '上课地点', render: (row) => text(row.classroom) },
      ],
      rows,
      emptyText: '本学期还没有选课，先去「选课中心」选几门吧',
    }))
  }

  load()
}
