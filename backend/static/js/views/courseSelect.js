/**
 * 选课中心（学生）。对标参考项目的 `views/student/CourseSelect.vue`。
 *
 * 页面由两块组成：
 *   * **可选课程** —— 后端 SQL 里已经排除了「已选」和「与我已选课程冲突」的课，
 *     所以这个列表里的每一门都能直接选；
 *   * **我的课程** —— 已选课程 + 成绩，可以在这里退课。
 *
 * 顶部那条黄色告警条来自 `/api/enrollments/conflicts`：它反查「有哪些课被我
 * 已选的时间挡住了」。没有这条提示，学生只会看到课程凭空消失，以为系统有毛病。
 *
 * 选课失败要按错误码分别给出可执行的下一步（超额 / 冲突 / 重复 / 关闭），
 * 一句「选课失败」等于什么都没说。
 */

import { api, ErrorCode } from '../api.js'
import { h, mount } from '../dom.js'
import { pageCard } from '../layout.js'
import { enrollmentStatusTag, scoreCell, semesterSelect } from './shared.js'
import {
  actionButtons, alertBar, confirmDialog, dataTable, notifySuccess, num, quotaBar, tag, text,
} from '../ui.js'

/** 选课失败的文案。key 是后端的错误码。 */
const FAILURE_HINTS = {
  [ErrorCode.COURSE_FULL]: '这门课名额已满。可以过几天再来看看 —— 有同学退课时名额会立刻归还。',
  [ErrorCode.TIME_CONFLICT]: '这门课与你已经选上的课程上课时间冲突。请先退掉冲突的课，或者换一门。',
  [ErrorCode.ALREADY_SELECTED]: '你已经选过这门课了，可以在「我的课程」里看到它。',
  [ErrorCode.COURSE_CLOSED]: '这门课当前未开放选课，请联系任课教师或教务处。',
}

export function render(container) {
  const state = { tab: 'available', semester: '' }

  const availableBody = h('div', {})
  const myBody = h('div', {})
  const conflictBar = h('div', {})
  const flashBar = h('div', {})
  const summary = h('div', { class: 'small muted mb-12' })

  const tabDefs = [
    { key: 'available', label: '可选课程', body: availableBody },
    { key: 'mine', label: '我的课程', body: myBody },
  ]
  const tabNodes = tabDefs.map((def) => h('button', {
    class: def.key === state.tab ? 'is-active' : '',
    onClick: () => activate(def.key),
  }, def.label))

  function activate(key) {
    state.tab = key
    tabDefs.forEach((def, index) => {
      tabNodes[index].classList.toggle('is-active', def.key === key)
      def.body.classList.toggle('hidden', def.key !== key)
    })
  }
  activate(state.tab)

  const semesterNode = semesterSelect({
    onChange: (value) => { state.semester = value; reloadAll() },
  })

  mount(container,
    h('div', { class: 'card' }, [
      h('div', { class: 'row-between' }, [
        h('div', { class: 'tabs__nav', style: { marginBottom: 0, borderBottom: 'none' } }, tabNodes),
        h('div', { class: 'row' }, [h('span', { class: 'muted' }, '学期：'), semesterNode]),
      ]),
      h('div', { class: 'mt-16' }, conflictBar),
      flashBar,
      summary,
      availableBody,
      myBody,
    ]))

  reloadAll()

  async function reloadAll() {
    await Promise.all([loadAvailable(), loadMine(), loadConflicts()])
  }

  /* ------------------------------------------------------------ 可选课程 */

  async function loadAvailable() {
    mount(availableBody, h('div', { class: 'loading' }, [h('div', { class: 'spinner' }), '加载中…']))
    let rows = []
    try {
      rows = await api.get('/api/enrollments/available', { semester: state.semester })
    } catch { /* 提示已弹 */ }

    const table = dataTable({
      columns: [
        { key: 'courseCode', title: '课程代码', render: (row) => h('span', { class: 'mono' }, text(row.courseCode)) },
        { key: 'name', title: '课程名称' },
        { key: 'credit', title: '学分', render: (row) => num(row.credit) },
        { key: 'courseType', title: '类型', render: (row) => text(row.courseType) },
        { key: 'dept', title: '开课院系', render: (row) => text(row.dept) },
        {
          key: 'teacherName', title: '授课教师',
          render: (row) => [text(row.teacherName),
            row.teacherTitle ? h('span', { class: 'small muted', style: { marginLeft: '4px' } }, row.teacherTitle) : null],
        },
        { key: 'quota', title: '余量', width: '150px', render: (row) => quotaBar(row.enrolledCount, row.capacity) },
        { key: 'actions', title: '操作', className: 'actions', render: (row) => actionButtons([
          {
            label: '选课',
            disabled: Number(row.remaining) <= 0,
            onClick: () => select(row),
          },
        ]) },
      ],
      rows,
      emptyText: '当前没有可选的课程（可能都已选过、与已选课程冲突，或尚未开放选课）',
    })

    mount(availableBody, [
      // 学生看到列表「少了课」时的第一反应是系统坏了，先说明筛选规则
      alertBar('列表已自动排除「已选过」和「与已选课程上课时间冲突」的课程 —— 过滤逻辑全部在 SQL 中完成。', 'success'),
      table,
    ])

    // 可选课程条数放在概览里，学生能一眼看出还有多少课能选
    summary.textContent = `可选课程 ${rows.length} 门`
  }

  async function select(row) {
    const confirmed = await confirmDialog({
      title: '确认选课',
      message: `确定选《${row.name}》吗？\n授课教师：${row.teacherName || '待定'}　学分：${num(row.credit)}　余量：${row.remaining ?? '—'}`,
      confirmText: '选课',
    })
    if (!confirmed) return

    try {
      await api.post('/api/enrollments', { courseId: row.id }, { silent: true })
      notifySuccess(`已选上《${row.name}》`)
      reloadAll()
    } catch (error) {
      showFailure(row, error)
    }
  }

  /** 选课失败：把错误码翻译成「接下来该做什么」，显示在课程列表上方。 */
  function showFailure(row, error) {
    const hint = FAILURE_HINTS[error.code] || error.message || '选课失败，请稍后再试'
    mount(flashBar, alertBar(`《${row.name}》：${hint}`, 'danger', clearFlash))
  }

  function clearFlash() {
    mount(flashBar)
  }

  /* ------------------------------------------------------------ 我的课程 */

  async function loadMine() {
    mount(myBody, h('div', { class: 'loading' }, [h('div', { class: 'spinner' }), '加载中…']))
    let rows = []
    try {
      rows = await api.get('/api/enrollments/my', { semester: state.semester })
    } catch { /* 提示已弹 */ }

    mount(myBody, dataTable({
      columns: [
        { key: 'courseCode', title: '课程代码', render: (row) => h('span', { class: 'mono' }, text(row.courseCode)) },
        { key: 'courseName', title: '课程名称' },
        { key: 'credit', title: '学分', render: (row) => num(row.credit) },
        { key: 'courseType', title: '类型', render: (row) => text(row.courseType) },
        { key: 'teacherName', title: '授课教师', render: (row) => text(row.teacherName) },
        { key: 'semester', title: '学期', render: (row) => text(row.semester) },
        { key: 'status', title: '状态', render: (row) => enrollmentStatusTag(row.status) },
        { key: 'score', title: '成绩', render: (row) => scoreCell(row.score) },
        { key: 'selectedAt', title: '选课时间', render: (row) => h('span', { class: 'small muted' }, text(row.selectedAt)) },
        { key: 'actions', title: '操作', className: 'actions', render: (row) => actionButtons([
          row.status === 'SELECTED'
            ? { label: '退课', danger: true, onClick: () => withdraw(row) }
            : null,
        ]) },
      ],
      rows,
      emptyText: '你还没有选任何课程，去「可选课程」里挑一门吧',
    }))
  }

  async function withdraw(row) {
    const confirmed = await confirmDialog({
      title: '退课确认',
      message: `确定退掉《${row.courseName}》吗？\n退课后名额会立刻归还，你可以重新选这门课。`,
      confirmText: '退课',
    })
    if (!confirmed) return
    try {
      await api.del(`/api/enrollments/${row.courseId}`, undefined, { silent: true })
      notifySuccess(`已退掉《${row.courseName}》`)
      reloadAll()
    } catch (error) {
      mount(flashBar, alertBar(`《${row.courseName}》：${error.message}`, 'danger', clearFlash))
    }
  }

  /* ------------------------------------------------------------ 冲突提示 */

  async function loadConflicts() {
    let rows = []
    try {
      rows = await api.get('/api/enrollments/conflicts', { semester: state.semester })
    } catch { /* 拿不到冲突列表不影响主流程 */ }

    if (!rows.length) {
      mount(conflictBar)
      return
    }

    // 措辞与参考项目一致：先说结论，再逐门课用标签点出「被哪一门挡住了」，
    // 否则学生只会看到课程从列表里凭空消失
    mount(conflictBar, alertBar(
      h('div', {}, [
        h('div', {}, '以下课程因时间冲突不可选：'),
        h('div', { class: 'row', style: { marginTop: '6px', flexWrap: 'wrap' } },
          rows.map((row) => tag(
            `${row.name}（与「${row.conflictWith || '已选课程'}」时间冲突）`, 'warning'))),
      ]),
      'warning',
      () => mount(conflictBar),
    ))
  }
}
