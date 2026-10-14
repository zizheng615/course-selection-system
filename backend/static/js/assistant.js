/**
 * AI 助手：悬浮入口 + 右侧抽屉。对标参考项目的 `components/AiAssistant.vue`。
 *
 * 三处细节与后端约定一致，改前端时别丢：
 *   1. **推荐问题由后端按角色返回**（`GET /api/ai/suggestions`），前端不写死 ——
 *      学生看到的追问里不能出现管理端菜单。
 *   2. **来源标签原样展示**：`本地知识库` / `未匹配` / 配置的服务名。三种含义不同，
 *      合并成一个「AI」会让用户分不清得到的是确定答案还是模型的自由发挥。
 *   3. 抽屉打开时给 `<body>` 加 `ai-open`，把内容区推开（CSS 里做），
 *      否则会盖住表格最右侧的「操作」列。
 */

import { api } from './api.js'
import { h, mount, richText } from './dom.js'
import { store } from './store.js'
import { tag } from './ui.js'

let drawer = null
let fab = null
let messages = null
let askInput = null
let sending = false
let suggestionsLoaded = false

/**
 * 挂载悬浮球与抽屉（由 layout 在渲染主布局时调用）。
 *
 * 这两块是挂在 `<body>` 上的，而主布局重挂载时 `mount(root)` 只清空 `#app` ——
 * 所以这里必须先把上一份摘掉，否则**每换一次账号就会多叠一个悬浮球**，
 * 而且上一位用户的欢迎语和推荐问题会原样留给下一位（角色隔离就破了）。
 */
export function mountAssistant() {
  if (drawer) drawer.remove()
  if (fab) fab.remove()
  document.body.classList.remove('ai-open')
  suggestionsLoaded = false
  sending = false

  messages = h('div', {})
  askInput = h('input', {
    class: 'input',
    placeholder: '问我系统怎么用，例如「怎么选课」',
    onKeydown: (event) => { if (event.key === 'Enter') send() },
  })

  drawer = h('div', { class: 'drawer' }, [
    h('div', { class: 'drawer__head' }, [
      h('div', { class: 'drawer__title' }, ['🤖 智能助手']),
      h('button', { class: 'dialog__close', onClick: closeAssistant, title: '收起' }, '✕'),
    ]),
    h('div', { class: 'drawer__body' }, messages),
    h('div', { class: 'drawer__foot' }, h('div', { class: 'ask-form' }, [
      askInput,
      h('button', { class: 'btn btn--primary', id: 'ai-send', onClick: send }, '发送'),
    ])),
  ])

  fab = h('button', { class: 'fab', title: '智能助手', onClick: toggleAssistant }, '🤖')

  document.body.appendChild(drawer)
  document.body.appendChild(fab)
}

export function isAssistantOpen() {
  return drawer.classList.contains('is-open')
}

export function openAssistant() {
  drawer.classList.add('is-open')
  fab.classList.add('is-open')
  fab.textContent = '✕'
  document.body.classList.add('ai-open')
  if (!suggestionsLoaded) {
    suggestionsLoaded = true
    greet()
  }
  setTimeout(() => askInput.focus(), 250)
}

export function closeAssistant() {
  drawer.classList.remove('is-open')
  fab.classList.remove('is-open')
  fab.textContent = '🤖'
  document.body.classList.remove('ai-open')
}

export function toggleAssistant() {
  if (isAssistantOpen()) closeAssistant()
  else openAssistant()
}

async function greet() {
  const name = store.displayName || '同学'
  pushMessage('ai', `你好，${name} 👋 我是选课系统的智能助手，可以解答系统怎么用。`)
  try {
    const list = await api.get('/api/ai/suggestions')
    if (list && list.length) {
      messages.appendChild(h('div', { class: 'chips' },
        list.map((q) => h('button', { class: 'chip', onClick: () => ask(q) }, q))))
      messages.scrollTop = messages.scrollHeight
    }
  } catch {
    /* 推荐问题拿不到不影响对话，静默忽略 */
  }
}

function pushMessage(who, text, source = '') {
  // 回答里的 `**加粗**` 与换行要真的渲染出来，否则用户看到一串星号
  const bubble = h('div', { class: 'msg__bubble' }, richText(text))
  const node = h('div', { class: ['msg', who === 'me' ? 'msg--me' : ''] }, bubble)
  if (source) {
    node.appendChild(h('div', { class: 'msg__meta' }, sourceTag(source)))
    // 来源挂在气泡下方，所以把整块包成纵向布局
    const wrap = h('div', { style: { display: 'flex', flexDirection: 'column', alignItems: who === 'me' ? 'flex-end' : 'flex-start' } })
    wrap.appendChild(node)
    messages.appendChild(wrap)
    messages.scrollTop = messages.scrollHeight
    return wrap
  }
  messages.appendChild(node)
  messages.scrollTop = messages.scrollHeight
  return node
}

/** 三种来源三种颜色：知识库=绿（确定）、未匹配=灰、大模型=蓝（生成）。 */
function sourceTag(source) {
  if (source === '本地知识库') return tag(source, 'success')
  if (source === '未匹配') return tag(source, 'info')
  return tag(source, 'primary')
}

function ask(question) {
  askInput.value = question
  send()
}

async function send() {
  const question = askInput.value.trim()
  if (!question || sending) return

  askInput.value = ''
  pushMessage('me', question)

  const pending = h('div', { class: 'msg' }, h('div', { class: 'msg__bubble' },
    h('span', { class: 'typing' }, [h('i'), h('i'), h('i')])))
  messages.appendChild(pending)
  messages.scrollTop = messages.scrollHeight

  sending = true
  try {
    const data = await api.post('/api/ai/chat', { question }, { silent: true })
    pending.remove()
    pushMessage('ai', data.answer, data.source)
    if (data.suggestions && data.suggestions.length) {
      messages.appendChild(h('div', { class: 'chips' },
        data.suggestions.map((q) => h('button', { class: 'chip', onClick: () => ask(q) }, q))))
    }
  } catch (error) {
    pending.remove()
    pushMessage('ai', error.message || '助手暂时不可用，请稍后再试')
  } finally {
    sending = false
    messages.scrollTop = messages.scrollHeight
    askInput.focus()
  }
}
