/**
 * 排课管理（管理员）。对标参考项目的 `views/admin/ScheduleManage.vue`。
 *
 * 先选课程，再维护它的上课时间。一门课可以有多段（理论 + 实验），
 * 这些时段会一起进入学生课表，也一起参与时间冲突判定。
 *
 * 冲突规则（与后端一致）：**同学期、同星期、节次区间重叠**即冲突，
 * 与周次无关 —— 所以「同一门课的同一时段排两遍」也会被拒。
 */

import { api } from '../api.js'
import { h, mount } from '../dom.js'
import { pageCard } from '../layout.js'
import { WEEKDAYS, buildForm, validators } from './shared.js'
import {
  actionButtons, confirmDanger, dataTable, notifySuccess, openDialog, text,
} from '../ui.js'

/** 节次选项 1~12。 */
const SECTIONS = Array.from({ length: 12 }, (_, i) => i + 1)

export function render(container) {
  const courseSelect = h('select', { class: 'select', style: { minWidth: '280px' } },
    h('option', { value: '' }, '加载中…'))
  const body = h('div', {})
  const hint = h('div', { class: 'small muted mt-8' })

  const addButton = h('button', { class: 'btn btn--primary', disabled: true, onClick: () => openForm(null) }, '＋ 新增上课时间')

  mount(container, pageCard('排课管理', [addButton], h('div', {}, [
    h('div', { class: 'toolbar' }, [
      h('span', { class: 'muted' }, '选择课程：'),
      courseSelect,
    ]),
    body,
    hint,
  ])))

  let currentCourse = null

  async function loadCourses() {
    try {
      const page = await api.get('/api/courses', { page: 1, size: 200 })
      const list = page.list || []
      mount(courseSelect, list.map((course) => h('option', {
        value: course.id,
      }, `${course.courseCode} ${course.name}（${course.teacherName || '未安排'}）`)))
      if (list.length) {
        currentCourse = list[0]
        loadSchedules()
      }
    } catch {
      mount(courseSelect, h('option', { value: '' }, '课程加载失败'))
    }
  }

  courseSelect.addEventListener('change', () => {
    currentCourse = { id: Number(courseSelect.value) }
    loadSchedules()
  })

  async function loadSchedules() {
    if (!currentCourse) return
    const courseId = Number(currentCourse.id)
    addButton.disabled = false
    mount(body, h('div', { class: 'loading' }, [h('div', { class: 'spinner' }), '加载中…']))
    try {
      const list = await api.get('/api/schedules', { courseId })
      mount(body,
        dataTable({
          columns: [
            { key: 'weekdayName', title: '星期', render: (row) => row.weekdayName || WEEKDAYS[row.weekday - 1] },
            {
              key: 'section', title: '节次',
              render: (row) => `第 ${row.startSection} ~ ${row.endSection} 节`,
            },
            {
              key: 'week', title: '周次',
              render: (row) => `第 ${row.startWeek} ~ ${row.endWeek} 周`,
            },
            { key: 'classroom', title: '上课地点', render: (row) => text(row.classroom) },
            { key: 'actions', title: '操作', className: 'actions', render: (row) => actionButtons([
              { label: '编辑', onClick: () => openForm(row) },
              { label: '删除', danger: true, onClick: () => removeSchedule(row) },
            ]) },
          ],
          rows: list,
          emptyText: '这门课还没有排上课时间，学生看不到它出现在课表里',
        }))
      hint.textContent = `共 ${list.length} 段上课时间`
    } catch {
      mount(body, h('div', { class: 'empty' }, '加载失败'))
    }
  }

  async function removeSchedule(row) {
    const confirmed = await confirmDanger('删除上课时间',
      `确定删除「${row.weekdayName || WEEKDAYS[row.weekday - 1]} 第 ${row.startSection}~${row.endSection} 节」吗？`)
    if (!confirmed) return
    await api.del(`/api/schedules/${row.id}`)
    notifySuccess('上课时间已删除')
    loadSchedules()
  }

  function openForm(row) {
    const isEdit = Boolean(row)

    const numberInput = (value, min, max) => h('input', {
      class: 'input', type: 'number', min, max, value: String(value),
    })
    const sectionSelect = (value) => h('select', { class: 'select' },
      SECTIONS.map((n) => h('option', { value: n, selected: n === Number(value) }, `第 ${n} 节`)))

    // 节次 / 周次的「起止先后」是跨字段的，校验挂在后一个字段上，错误也就显示在后一个字段下面
    const startSectionNode = sectionSelect(row ? row.startSection : 1)
    const endSectionNode = sectionSelect(row ? row.endSection : 2)
    const startWeekNode = numberInput(row ? row.startWeek : 1, 1, 30)
    const endWeekNode = numberInput(row ? row.endWeek : 16, 1, 30)

    const notBefore = (label, startNode) => (value) => {
      const start = Number(startNode.value)
      const end = Number(value)
      if (!Number.isFinite(start) || !Number.isFinite(end)) return ''
      return end >= start ? '' : `开始${label}不能大于结束${label}`
    }

    const form = buildForm([
      {
        key: 'weekday', label: '星期',
        node: h('select', { class: 'select' }, WEEKDAYS.map((label, index) => h('option', {
          value: index + 1, selected: (row ? row.weekday : 1) === index + 1,
        }, label))),
      },
      { key: 'classroom', label: '上课地点', value: row ? (row.classroom || '') : '', placeholder: '如 教学楼 A301' },
      { key: 'startSection', label: '开始节次', node: startSectionNode },
      {
        key: 'endSection', label: '结束节次', node: endSectionNode,
        validate: notBefore('节次', startSectionNode),
      },
      {
        key: 'startWeek', label: '开始周', required: true,
        node: startWeekNode,
        validate: validators.all(validators.required('开始周'), validators.range('开始周', 1, 30)),
      },
      {
        key: 'endWeek', label: '结束周', required: true,
        node: endWeekNode,
        validate: validators.all(
          validators.required('结束周'),
          validators.range('结束周', 1, 30),
          notBefore('周', startWeekNode),
        ),
      },
    ])

    openDialog({
      title: isEdit ? '编辑上课时间' : '新增上课时间',
      body: form.node,
      confirmText: isEdit ? '保存' : '添加',
      onConfirm: async () => {
        if (!form.validate()) return false
        const values = form.values()
        const payload = {
          courseId: Number(currentCourse.id),
          weekday: Number(values.weekday),
          startSection: Number(values.startSection),
          endSection: Number(values.endSection),
          startWeek: Number(values.startWeek),
          endWeek: Number(values.endWeek),
          classroom: values.classroom.trim() || null,
        }
        try {
          if (isEdit) await api.put(`/api/schedules/${row.id}`, payload)
          else await api.post('/api/schedules', payload)
        } catch {
          return false     // 4003 教师时间冲突等错误已弹提示，保持弹窗
        }
        notifySuccess(isEdit ? '上课时间已更新' : '上课时间已添加')
        loadSchedules()
        return true
      },
    })
  }

  loadCourses()
}
