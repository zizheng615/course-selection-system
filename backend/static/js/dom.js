/**
 * 极简 DOM 构建层。
 *
 * 全站不使用 innerHTML 拼接用户数据 —— 课程名、学生姓名都是用户输入，
 * 字符串拼接就是一个 XSS 口子。所有文本都走 textContent，节点走 createElement。
 * 需要「一段富文本」的地方（比如 AI 回答里的换行）用 white-space: pre-wrap 解决，
 * 而不是 innerHTML。
 */

/**
 * 创建元素。
 *
 * @param {string} tag                 标签名
 * @param {object} [attrs]             class / style / dataset / on* / 其余属性
 * @param {Array|Node|string} [kids]   子节点
 */
export function h(tag, attrs = {}, kids = []) {
  const node = document.createElement(tag)

  for (const [key, value] of Object.entries(attrs || {})) {
    if (value === null || value === undefined || value === false) continue

    if (key === 'class' || key === 'className') {
      node.className = Array.isArray(value) ? value.filter(Boolean).join(' ') : String(value)
    } else if (key === 'style' && typeof value === 'object') {
      Object.assign(node.style, value)
    } else if (key === 'dataset') {
      Object.assign(node.dataset, value)
    } else if (key.startsWith('on') && typeof value === 'function') {
      node.addEventListener(key.slice(2).toLowerCase(), value)
    } else if (key === 'value') {
      node.value = value
    } else if (key === 'checked' || key === 'disabled' || key === 'selected') {
      node[key] = Boolean(value)
    } else {
      node.setAttribute(key, String(value))
    }
  }

  append(node, kids)
  return node
}

/** 把任意子节点追加到父节点。数组递归，null/undefined/false 跳过。 */
export function append(parent, kids) {
  if (kids === null || kids === undefined || kids === false || kids === true) return parent
  if (Array.isArray(kids)) {
    kids.forEach((kid) => append(parent, kid))
    return parent
  }
  parent.appendChild(kids instanceof Node ? kids : document.createTextNode(String(kids)))
  return parent
}

/**
 * 极简富文本：把 `**加粗**` 与换行渲染成真实节点，返回 DocumentFragment。
 *
 * 对标参考项目 `AiAssistant.vue` 里的 `render()`（它的知识库回答里确实带 `**`），
 * 但这里**不走 innerHTML** —— 逐段建节点、正文一律 textContent，
 * 所以回答里带了 HTML 也只会被当成字面量显示，少一个注入口子。
 */
export function richText(text) {
  const fragment = document.createDocumentFragment()
  const source = text === null || text === undefined ? '' : String(text)

  source.split('\n').forEach((line, lineIndex) => {
    if (lineIndex) fragment.appendChild(h('br'))
    // 带捕获组切分：奇数下标即被 ** 包住的那一段
    line.split(/\*\*(.+?)\*\*/g).forEach((part, index) => {
      if (!part) return
      fragment.appendChild(index % 2 ? h('strong', {}, part) : document.createTextNode(part))
    })
  })
  return fragment
}

/** 用新内容整体替换容器内容。 */
export function mount(container, ...kids) {
  container.replaceChildren()
  append(container, kids)
  return container
}

export function qs(selector, root = document) {
  return root.querySelector(selector)
}

export function qsa(selector, root = document) {
  return Array.from(root.querySelectorAll(selector))
}

/** 显示用文本：null / 空串统一显示为「—」，避免表格里出现空白格。 */
export function text(value) {
  if (value === null || value === undefined || value === '') return '—'
  return String(value)
}

/** 数字展示：保留必要的小数，去掉尾随 0（学分 2.0 -> 2，2.5 -> 2.5）。 */
export function num(value, digits = 2) {
  if (value === null || value === undefined || value === '') return '—'
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  return String(Number(n.toFixed(digits)))
}

/** 防抖：搜索框输入时用。 */
export function debounce(fn, wait = 300) {
  let timer = null
  return (...args) => {
    clearTimeout(timer)
    timer = setTimeout(() => fn(...args), wait)
  }
}

/** 聚焦到某个输入框（弹窗打开后调用，省一次点击）。 */
export function focusFirst(container) {
  const el = container.querySelector('input:not([type=hidden]), textarea, select')
  if (el) setTimeout(() => el.focus(), 30)
}
