/**
 * 页面共用小工具。纯函数与轻量封装，不含任何页面专属逻辑。
 *
 * 存在的主要理由：六个管理端页面都是「筛选条 + 表格 + 分页」的同一套骨架，
 * 把这段骨架抽出来，每个页面就只剩「列定义」和「加载函数」两件事。
 */

import { api } from '../api.js'
import { h, mount } from '../dom.js'
import { dataTable, field, pagination, tag } from '../ui.js'

export const WEEKDAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

export function weekdayName(value) {
  return WEEKDAYS[Number(value) - 1] || '—'
}

/** 课程状态标签。 */
export function courseStatusTag(status) {
  return status === 'OPEN' ? tag('开放选课', 'success') : tag('已关闭', 'info')
}

/** 选课记录状态标签。软退课的记录保留在库里，用灰色区分。 */
export function enrollmentStatusTag(status) {
  return status === 'SELECTED' ? tag('已选', 'primary') : tag('已退课', 'info')
}

/** 账号状态开关的文字。 */
export function userStatusTag(status) {
  return Number(status) === 1 ? tag('正常', 'success') : tag('已禁用', 'danger')
}

/** 成绩单元格：未录入显示灰色「未录入」，而不是 0（0 分是有效成绩）。 */
export function scoreCell(score) {
  if (score === null || score === undefined) return h('span', { class: 'muted' }, '未录入')
  const value = Number(score)
  const type = value >= 60 ? 'success' : 'danger'
  return tag(String(value), type)
}

/**
 * 分页列表控制器：管理「页码 / 每页条数 / 数据 / 加载态」并把表格与分页渲染进 `body`。
 *
 * @param {object} options
 * @param {HTMLElement} options.body    渲染目标容器
 * @param {Array}  options.columns      列定义，见 ui.dataTable
 * @param {Function} options.load       (page, size) => Promise<{list,total,page,size}>
 * @param {string} [options.emptyText]
 */
export function createPager({ body, columns, load, emptyText = '暂无数据' }) {
  const state = { page: 1, size: 10, total: 0, rows: [], loading: true }

  function paint() {
    mount(body,
      dataTable({ columns, rows: state.rows, loading: state.loading, emptyText }),
      state.loading || state.total === 0 ? null : pagination({
        page: state.page,
        size: state.size,
        total: state.total,
        onChange: (page, size) => { state.size = size; reload(page) },
      }))
  }

  async function reload(page = state.page) {
    state.loading = true
    paint()
    try {
      const data = await load(page, state.size)
      state.rows = data.list || []
      state.total = data.total || 0
      state.page = data.page || page
      state.size = data.size || state.size
    } catch {
      // 具体错误已由 api.js 弹过 Toast，这里只需要让表格回到空态
      state.rows = []
      state.total = 0
    }
    state.loading = false
    paint()
  }

  return {
    state,
    reload,
    /** 筛选条件变化后回到第一页。 */
    reset: () => reload(1),
  }
}

/**
 * 学期下拉框。选项来自后端**已存在的**学期（`/api/courses/semesters` 返回字符串数组，
 * 按学期倒序），避免手写一个不存在的学期导致列表永远为空。
 *
 * @param {object} options
 * @param {string} [options.value]     初始选中项；留空则取最新的学期
 * @param {string} [options.allLabel]  传 null 表示不加「全部学期」这一项（表单里用）
 */
export function semesterSelect({ value = '', onChange, allLabel = '全部学期' } = {}) {
  const node = h('select', { class: 'select', onChange: (event) => onChange && onChange(event.target.value) })
  node.dataset.value = value

  api.get('/api/courses/semesters').then((list) => {
    const semesters = Array.isArray(list) ? list : []
    const selected = value || semesters[0] || ''
    const items = (allLabel ? [{ value: '', label: allLabel }] : [])
      .concat(semesters.map((s) => ({ value: s, label: s })))
    mount(node, items.map((item) => h('option', {
      value: item.value,
      selected: String(item.value) === String(selected),
    }, item.label)))
    node.dataset.value = selected
    // 首次拿到选项后通知一次，页面可以据此立刻加载数据
    if (!value && selected && onChange) onChange(selected)
  }).catch(() => { /* 拿不到学期就不给选项，页面会显示空列表 */ })

  return node
}

/** 教师下拉框（新增/编辑课程时选授课教师）。 */
export async function teacherSelect(value) {
  let list = []
  try {
    list = await api.get('/api/teachers/all')
  } catch { /* 忽略 */ }
  return {
    list,
    node: h('select', { class: 'select' }, list.map((t) => h('option', {
      value: t.id,
      selected: String(t.id) === String(value),
    }, `${t.name}（${t.title || '—'} · ${t.dept || '—'}）`))),
  }
}

/** 一个简单的「必填」校验器集合，配合 ui.field 的 setError 使用。 */
export const validators = {
  required: (label) => (value) => (String(value ?? '').trim() ? '' : `请填写${label}`),
  positive: (label) => (value) => (Number(value) > 0 ? '' : `${label}必须大于 0`),
  range: (label, min, max) => (value) => {
    const n = Number(value)
    return n >= min && n <= max ? '' : `${label}需在 ${min} ~ ${max} 之间`
  },
  /** 一次跑多个校验，返回第一条错误。 */
  all: (...checks) => (value) => {
    for (const check of checks) {
      const message = check(value)
      if (message) return message
    }
    return ''
  },
}

/**
 * 表单构造器。把「字段定义 → 输入控件 → 取值 → 校验」串起来，
 * 弹窗里的新增/编辑表单都用它，省掉每个页面重写一遍取值与报错。
 *
 * @param {Array} specs 每项 {key,label,node?,value?,placeholder?,hint?,full?,validate?}
 * @returns {{node:HTMLElement, input:Function, values:Function, validate:Function}}
 */
export function buildForm(specs) {
  const items = specs.map((spec) => {
    const input = spec.node || h('input', {
      class: 'input',
      value: spec.value === null || spec.value === undefined ? '' : String(spec.value),
      placeholder: spec.placeholder || '',
      type: spec.type || 'text',
    })
    const wrapper = field(spec.label, input, { required: spec.required, hint: spec.hint })
    if (spec.full) wrapper.classList.add('field--full')
    return { spec, input, wrapper }
  })

  return {
    node: h('div', { class: 'form-grid' }, items.map((it) => it.wrapper)),
    input: (key) => {
      const item = items.find((it) => it.spec.key === key)
      return item ? item.input : null
    },
    validate() {
      let passed = true
      items.forEach((item) => {
        const message = item.spec.validate ? item.spec.validate(item.input.value, item.input) : ''
        item.wrapper.setError(message)
        if (message) passed = false
      })
      return passed
    },
    values() {
      const out = {}
      items.forEach((item) => { out[item.spec.key] = item.input.value })
      return out
    },
  }
}
