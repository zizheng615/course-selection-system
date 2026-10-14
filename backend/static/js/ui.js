/**
 * 组件层。对标参考项目里的 Element Plus 组件（DataTable / Dialog / Pagination /
 * Toast / Confirm / Tag / Progress / Tabs / Statistic）。
 *
 * 每个组件都是一个「接收配置、返回 DOM 节点」的普通函数 —— 没有虚拟 DOM、
 * 没有响应式系统。页面拿到新数据就重渲染对应的那一块，代价可忽略，
 * 换来的是整个前端零构建、零依赖。
 */

import { append, h, mount, num, text } from './dom.js'

/* ==========================================================================
   Toast
   ========================================================================== */

const TOAST_ICONS = { success: '✓', error: '✕', warning: '!', info: 'i' }

export function toast(message, type = 'info', duration = 2600) {
  const root = document.getElementById('toast-root')
  if (!root) return
  const node = h('div', { class: `toast toast--${type}` }, [
    h('span', {}, TOAST_ICONS[type] || ''),
    h('span', {}, message),
  ])
  root.appendChild(node)
  setTimeout(() => node.remove(), duration)
}

export const notifySuccess = (msg) => toast(msg, 'success')
export const notifyError = (msg) => toast(msg, 'error', 3600)
export const notifyWarning = (msg) => toast(msg, 'warning', 3200)

/* ==========================================================================
   Dialog / Confirm
   ========================================================================== */

/**
 * 打开一个对话框。
 *
 * @param {object} options
 * @param {string} options.title
 * @param {Node|Node[]} options.body
 * @param {Node[]} [options.footer]   默认渲染「取消 / 确定」
 * @param {string} [options.size]     'sm' | 'lg'
 * @param {Function} [options.onConfirm] 返回 false 时不关闭（校验失败）
 * @param {string} [options.confirmText]
 * @returns {{close: Function, root: HTMLElement}}
 */
export function openDialog(options) {
  const {
    title, body, footer, size, onConfirm, confirmText = '确定',
    cancelText = '取消', onCancel, hideFooter = false,
  } = options

  const close = () => {
    mask.remove()
    document.removeEventListener('keydown', onKey)
  }

  const onKey = (event) => {
    if (event.key === 'Escape') close()
  }

  const buttons = footer || []
  if (!hideFooter && !footer) {
    buttons.push(h('button', { class: 'btn', onClick: () => { if (onCancel) onCancel(); close() } }, cancelText))
    buttons.push(h('button', {
      class: 'btn btn--primary',
      onClick: async (event) => {
        const button = event.currentTarget
        // 请求回来之前先禁用，避免连点创建出两条重复数据
        if (button.disabled) return
        button.disabled = true
        try {
          // onConfirm 允许是异步的（要发请求）：返回 false 表示校验没过或请求失败，
          // 保持弹窗打开让用户改，而不是把刚填的内容丢掉
          if (onConfirm && (await onConfirm()) === false) return
        } catch (error) {
          // 调用方负责弹提示；这里只保证不静默关窗
          console.error('[dialog] onConfirm 抛出异常', error)
          return
        } finally {
          button.disabled = false
        }
        close()
      },
    }, confirmText))
  }

  const dialog = h('div', { class: ['dialog', size ? `dialog--${size}` : ''] }, [
    h('div', { class: 'dialog__head' }, [
      h('span', {}, title),
      h('button', { class: 'dialog__close', onClick: close, title: '关闭' }, '✕'),
    ]),
    h('div', { class: 'dialog__body' }, body),
    (!hideFooter && buttons.length) ? h('div', { class: 'dialog__foot' }, buttons) : null,
  ])

  const mask = h('div', {
    class: 'mask',
    // 只有点遮罩本身才关闭；点弹窗内部冒泡上来的不算
    onClick: (event) => { if (event.target === mask) { if (onCancel) onCancel(); close() } },
  }, dialog)

  document.getElementById('modal-root').appendChild(mask)
  document.addEventListener('keydown', onKey)
  return { close, root: dialog }
}

/** 二次确认。删除类操作一律先过这里 —— 不可逆的动作不能一点就走。 */
export function confirmDialog({ title = '确认操作', message, confirmText = '确定', danger = false }) {
  return new Promise((resolve) => {
    let settled = false
    const done = (value) => { if (!settled) { settled = true; resolve(value) } }
    openDialog({
      title,
      size: 'sm',
      body: h('div', { style: { lineHeight: '1.8' } }, message),
      confirmText,
      onConfirm: () => done(true),
      onCancel: () => done(false),
    })
    // 关掉弹窗的方式不止「确定/取消」两种（Esc、点遮罩），统一兜底为 false
    const root = document.getElementById('modal-root')
    const observer = new MutationObserver(() => {
      if (!root.querySelector('.mask')) { observer.disconnect(); done(false) }
    })
    observer.observe(root, { childList: true })
  })
}

/** 危险按钮的确认框：红色确认键。 */
export function confirmDanger(title, message, confirmText = '删除') {
  return confirmDialog({ title, message, confirmText, danger: true })
}

/* ==========================================================================
   表格
   ========================================================================== */

/**
 * 构造表格节点。
 *
 * @param {object} options
 * @param {Array}  options.columns  {key,title,width,align,className,render(row)->Node|string}
 * @param {Array}  options.rows
 * @param {boolean}[options.loading]
 * @param {string} [options.emptyText]
 */
export function dataTable({ columns, rows, loading = false, emptyText = '暂无数据' }) {
  if (loading) return h('div', { class: 'loading' }, [h('div', { class: 'spinner' }), '加载中…'])
  if (!rows || !rows.length) {
    return h('div', { class: 'empty' }, [
      h('div', { class: 'empty__icon' }, '☰'),
      h('div', { class: 'empty__text' }, emptyText),
    ])
  }

  const head = h('tr', {}, columns.map((col) => h('th', {
    style: col.width ? { width: col.width } : null,
    class: col.align === 'right' ? 'center' : null,
  }, col.title)))

  const body = rows.map((row, index) => h('tr', {}, columns.map((col) => {
    const cell = h('td', { class: col.className })
    const value = col.render ? col.render(row, index) : row[col.key]
    append(cell, value === null || value === undefined ? text(value) : value)
    return cell
  })))

  return h('div', { class: 'table-wrap' }, h('table', { class: 'table' }, [
    h('thead', {}, head),
    h('tbody', {}, body),
  ]))
}

/** 单元格渲染器：标签。 */
export function tag(value, type = 'info') {
  return h('span', { class: `tag tag--${type}` }, value)
}

/** 单元格渲染器：剩余名额进度条。 */
export function quotaBar(selected, capacity) {
  const total = Number(capacity) || 0
  const used = Number(selected) || 0
  const rate = total > 0 ? (used / total) * 100 : 0
  const cls = rate >= 100 ? 'is-full' : (rate >= 80 ? 'is-high' : '')
  return h('div', { class: 'row' }, [
    h('div', { class: 'progress', style: { flex: '1' } },
      h('div', { class: ['progress__bar', cls], style: { width: `${Math.min(rate, 100)}%` } })),
    h('span', { class: 'small muted nowrap' }, `${used}/${total}`),
  ])
}

/** 单元格渲染器：一行文字按钮。 */
export function actionButtons(items) {
  return h('div', { class: 'row' }, items.filter(Boolean).map((item) =>
    h('button', {
      class: ['btn', 'btn--text', 'btn--sm', item.danger ? 'is-danger' : ''],
      onClick: item.onClick,
      disabled: item.disabled,
    }, item.label)))
}

/* ==========================================================================
   分页
   ========================================================================== */

/**
 * @param {object} options
 * @param {number} options.page      当前页（从 1 开始）
 * @param {number} options.size      每页条数
 * @param {number} options.total     总条数
 * @param {Function} options.onChange(page, size)
 * @param {boolean} [options.sizeable] 是否显示每页条数选择
 */
export function pagination({ page, size, total, onChange, sizeable = true }) {
  const pages = Math.max(1, Math.ceil(total / size))
  const go = (p) => { if (p >= 1 && p <= pages && p !== page) onChange(p, size) }

  const numbers = pageNumbers(page, pages).map((p) => (p === '...'
    ? h('span', { class: 'muted', style: { padding: '0 4px' } }, '…')
    : h('button', { class: p === page ? 'is-active' : '', onClick: () => go(p) }, String(p))))

  return h('div', { class: 'pagination' }, [
    h('span', { class: 'pagination__total' }, `共 ${total} 条`),
    sizeable ? h('select', {
      class: 'select',
      style: { width: '104px', height: '30px' },
      onChange: (event) => onChange(1, Number(event.target.value)),
    }, [10, 20, 50, 100].map((s) => h('option', { value: s, selected: s === size }, `${s} 条/页`))) : null,
    h('button', { disabled: page <= 1, onClick: () => go(page - 1) }, '‹'),
    numbers,
    h('button', { disabled: page >= pages, onClick: () => go(page + 1) }, '›'),
  ])
}

/** 页码序列，超过 7 页时用省略号折叠（1 … 4 5 6 … 20）。 */
function pageNumbers(current, total) {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)
  if (current <= 4) return [1, 2, 3, 4, 5, '...', total]
  if (current >= total - 3) return [1, '...', total - 4, total - 3, total - 2, total - 1, total]
  return [1, '...', current - 1, current, current + 1, '...', total]
}

/* ==========================================================================
   其它小件
   ========================================================================== */

export function alertBar(message, type = 'info', onClose) {
  return h('div', { class: `alert alert--${type}` }, [
    h('span', { class: 'grow' }, message),
    onClose ? h('button', { class: 'alert__close', onClick: onClose }, '✕') : null,
  ])
}

export function statistic(label, value, unit = '', foot = '') {
  return h('div', { class: 'stat' }, [
    h('div', { class: 'stat__label' }, label),
    h('div', { class: 'stat__value' }, [String(value), unit ? h('span', { class: 'unit' }, unit) : null]),
    foot ? h('div', { class: 'stat__foot' }, foot) : null,
  ])
}

/** 带标签与错误位的表单项。返回 {wrap, input}，由调用方拿 input.value 取值。 */
export function field(label, input, { required = false, hint = '' } = {}) {
  const error = h('div', { class: 'field__error' })
  const wrap = h('div', { class: 'field' }, [
    h('label', { class: 'field__label' }, [required ? h('span', { class: 'req' }, '*') : null, label]),
    input,
    hint ? h('div', { class: 'small muted' }, hint) : null,
    error,
  ])
  wrap.setError = (message) => {
    error.textContent = message || ''
    input.classList.toggle('is-invalid', Boolean(message))
    return !message
  }
  return wrap
}

export function select(options, value, attrs = {}) {
  return h('select', { class: 'select', ...attrs },
    options.map((opt) => h('option', { value: opt.value, selected: String(opt.value) === String(value) }, opt.label)))
}

export function input(attrs = {}) {
  return h('input', { class: 'input', ...attrs })
}

/** 标签页容器。返回 {node, setActive}，切页时回调 onChange(key)。 */
export function tabs(items, activeKey, onChange) {
  const nav = h('div', { class: 'tabs__nav' })
  const panel = h('div', { class: 'tabs__panel' })
  const render = (key) => {
    mount(nav, items.map((item) => h('button', {
      class: item.key === key ? 'is-active' : '',
      onClick: () => render(item.key),
    }, item.label)))
    onChange(key, panel)
  }
  render(activeKey)
  return { node: h('div', {}, [nav, panel]), panel }
}

/** 数值格式化再导出，页面少引一个模块。 */
export { num, text }
