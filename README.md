# 高校选课管理系统（Python + SQLite）

一套完整的选课管理系统：管理员排课与管课、教师查看名单与录入成绩、学生选课退课看课表，
外加一个按角色隔离的 AI 助手。功能点与参考项目（Vue 3 + Spring Boot 3 + MySQL 8 版本）
逐项对齐，技术栈换成 **Python + FastAPI + SQLite**。

没有 npm、没有 Node、没有 MySQL、不联网也能完整跑起来。

---

## 快速开始

```bash
pip install -r requirements.txt
python scripts/init_db.py        # 建库 + 灌演示数据（幂等，可反复执行）
python run.py                    # http://localhost:8000
```

打开 <http://localhost:8000> 即可。接口文档在 <http://localhost:8000/docs>。

### 演示账号

| 角色 | 账号 | 口令 | 说明 |
|---|---|---|---|
| 管理员 | `admin` | `123456` | 全部管理功能 |
| 教师 | `tea001` ~ `tea010` | `123456` | 我的课程、学生名单、录入成绩 |
| 学生 | `stu001` ~ `stu050` | `123456` | 选课、退课、课表、成绩 |

> 口令仅用于本地演示（`DEFAULT_PASSWORD` 可覆盖）。生产部署请务必改掉。

---

## 功能清单

### 管理员

| 模块 | 能力 |
|---|---|
| 课程管理 | 分页 + 关键词/学期/状态筛选、新增、修改、删除、开放/关闭选课；同代码同学期唯一；容量不得小于已选人数；有选课记录时拒绝删除 |
| 排课管理 | 按课程维护多段上课时间（星期 / 节次 / 周次 / 地点）；**教师时间冲突**校验（同学期、同星期、节次区间重叠即拒绝） |
| 学生管理 | 分页 + 专业筛选、增删改；新增学生时**自动创建登录账号**（账号=学号，口令 `123456`）；改姓名同步账号姓名；有选课记录时拒绝删除 |
| 教师管理 | 同上，账号=工号；有课程时拒绝删除 |
| 账号管理 | 分页（带出关联的学生/教师业务信息）、改登录账号、重置口令、启用/禁用、删除；不能禁用或删除自己 |
| 选课记录 | 按学生/课程/状态/学期筛选；**代学生加选课**；软退课（保留历史）；硬删记录（同步归还容量） |
| 统计报表 | 热门课程 Top-N（含满座率）、各专业选课分布、教师工作量 |

### 学生

选课中心（可选课程 / 我的课程两个标签页）、选课、退课、我的课表（周网格）、成绩查询、
**冲突课程反查**（列出有哪些课被已选课程挡住了）。

### 教师

我的课程、学生名单、逐行录入/修改成绩（0~100，已退课学生不出现在名单里）。

### AI 助手（三种角色）

内置知识库按**角色过滤**：学生问「怎么新增课程」拿不到管理端的答案，
教师问「怎么退课」会落到「未匹配」。推荐问题同样按角色区分。
可选接入 Anthropic 协议兼容的大模型作为兜底。

---

## 目录结构

```
├── backend/
│   ├── app/
│   │   ├── main.py              # 应用装配：CORS、异常处理、路由注册、静态托管
│   │   ├── config.py            # 配置（敏感项只读环境变量）
│   │   ├── db.py                # SQLite 连接：WAL + busy_timeout + 线程局部连接
│   │   ├── common/              # 统一响应体、错误码、异常处理
│   │   ├── security/            # JWT、bcrypt、require_role 依赖工厂
│   │   ├── schemas/             # pydantic v2 入参/出参模型
│   │   ├── routers/             # 控制器层（薄，只做参数绑定与鉴权）
│   │   ├── service/             # 业务层（事务边界在这一层）
│   │   ├── repository/          # 数据访问层（只写 SQL）
│   │   └── ai/                  # AI 助手：知识库 + 提供方注册表
│   └── static/                  # 手写前端（HTML + CSS + 原生 ES Module）
├── sql/
│   ├── 01_schema.sql            # 权威 DDL：6 表 2 视图
│   ├── 02_seed_data.sql         # 演示数据
│   └── 03_queries.sql           # 17 条演示查询 + 执行计划对比 + 一致性自检
├── scripts/
│   ├── init_db.py               # 建库脚本（幂等）
│   ├── run_queries.py           # 跑 03_queries.sql 并打印结果
│   ├── sanitize_check.py        # 打包前置脱敏门禁
│   └── package.py               # 打包（先过门禁再压缩）
└── docs/                        # 设计说明、测试报告、演示脚本、API 契约
```

> 本包只含**运行所需源码**。单元测试代码与集成测试截图未随包提交，
> 但测试过程与结果记录在 [`docs/测试报告.md`](docs/测试报告.md)。

---

## 架构：Controller → Service → Repository

**事务边界只在 Service 层**，Repository 只负责 SQL，Router 只做参数绑定与鉴权。

```
HTTP → routers/ (鉴权 + 校验)  →  service/ (业务规则 + BEGIN IMMEDIATE 事务)  →  repository/ (SQL)  →  SQLite
```

### 开闭原则的四个落地扩展点

「对扩展开放、对修改关闭」不是一句口号，项目里有四处是**真的可以只加不改**的：

**1. AI 回答提供方**（核心扩展点）

`ai/provider.py` 定义 `AiAnswerProvider` 协议（`name` / `order` / `is_available` / `try_answer`），
`ai/registry.py` 维护一个有序注册表，`AiService` **只做编排**：按 `order` 依次询问，
谁先给出答案就用谁。

```python
# 新增一个回答来源：写一个类 + 注册，AiService 一行都不用改
class MyProvider:
    name = "我的知识源"
    order = 5
    def is_available(self) -> bool: ...
    def try_answer(self, question: str, ctx: AiContext) -> AiAnswer | None: ...

registry.register(MyProvider())
```

判断这条线有没有守住，标准很实际：**加一个新的回答来源，需要改动几个已有文件？
答案是 0。**

**2. 路由注册表**：`routers/__init__.py` 暴露 `ALL_ROUTERS`，`main.py` 循环注册。
新增模块 = 往列表里加一个元素。

**3. 声明式角色权限**：`require_role(*roles)` 依赖工厂，权限写在路由签名上，
而不是散落在各个 Service 的 `if role == ...` 里。

```python
@router.post("", dependencies=[Depends(require_role(Role.ADMIN))])
def create_course(...): ...
```

**4. 前端视图注册表**：`static/js/router.js` 的路由表 + `views/index.js` 的视图表 +
`layout.js` 的菜单数据。新增页面 = 新增一个 view 模块 + 注册一条记录。

---

## 几个值得说明的实现点

### 防超卖：一条 UPDATE，看影响行数

不用「先查余量再更新」（两个请求之间会被插队），而是把判断塞进 UPDATE 的 WHERE：

```sql
UPDATE course SET enrolled_count = enrolled_count + 1
 WHERE id = ? AND status = 'OPEN' AND enrolled_count < capacity
```

影响行数为 0 就说明没抢到。配合 `BEGIN IMMEDIATE` + WAL + `busy_timeout=10000`，
即便多个请求同时冲进来也不会超卖。测试时用 N 个线程抢 K 个名额，
成功次数恰好等于 K，且 `enrolled_count` 与真实选课记录数完全一致（见测试报告）。

### 时间冲突：区间重叠，两个维度都要判

```sql
A.start_section <= B.end_section AND B.start_section <= A.end_section
AND A.start_week <= B.end_week AND B.start_week <= A.end_week
```

学生冲突判「节次 + 周次」，教师排课冲突只判「节次」（同一周次区间内的排课冲突才算冲突）。
这套判定在**三处**逻辑一致：可选课程列表、冲突反查、选课校验 —— 全部在 SQL 里完成。

### 退课是软退课

退课把 `enrollment.status` 置为 `WITHDRAWN`，保留历史。
由于 `uk_student_course` 唯一索引的存在，重新选同一门课必须**复用原记录**（改回 `SELECTED` 并清空旧成绩）。

### 前端不使用 innerHTML

全站没有任何一处 `innerHTML` 拼接用户数据 —— 课程名、姓名都是用户输入，
而 JWT 就存在 `localStorage` 里，一个 XSS 就能把令牌读走。
所有文本走 `textContent`，节点走 `createElement`。
AI 回答里的 `**加粗**` 也是逐段建 `<strong>` 节点渲染的，而不是拼字符串。

---

## 配置与安全

**仓库里没有任何真实凭据。** 敏感项一律只从环境变量读取，且都有可安全公开的默认值 ——
什么都不配也能把系统完整跑起来（AI 助手退化为纯本地知识库）。

```bash
cp .env.example .env    # .env 已被 .gitignore 忽略
```

| 变量 | 默认 | 说明 |
|---|---|---|
| `AI_API_KEY` | 空 | **留空则大模型提供方不可用**，系统只走内置知识库 |
| `AI_BASE_URL` | `https://api.anthropic.com` | Anthropic 协议兼容端点 |
| `AI_MODEL` | `claude-sonnet-5-5` | 模型名 |
| `JWT_SECRET` | 公开的演示占位符 | **生产部署必须替换**为随机长字符串 |
| `JWT_EXPIRE_HOURS` | `24` | 令牌有效期 |
| `DB_PATH` | `data/course_selection.db` | 数据库位置 |
| `DEFAULT_SEMESTER` | `2026-2027-1` | 默认学期 |
| `DEFAULT_PASSWORD` | `123456` | 新建账号的初始口令 |

`scripts/sanitize_check.py` 是打包前的机械门禁：它**扫描的文件集与 `package.py`
实际压缩的文件集完全一致**，命中四类问题中的任意一条就直接失败 ——
`sk-` 开头的 Key 字面量、被赋了非空值的 `api-key`、硬编码绝对路径、JWT 密钥字面量。
本地 `.env`、`*.db` 这类文件本来就被排除在压缩包之外，不会被误判成泄露。

---

## 自检与验证

```bash
python scripts/run_queries.py       # 跑演示 SQL：17 条查询 + 执行计划对比 + 一致性自检
python scripts/sanitize_check.py    # 打包前脱敏门禁
```

`run_queries.py` 里有三条**一致性自检查询**，在干净数据下必须返回空结果集：
课程的 `enrolled_count` 与真实选课数是否一致、有无孤儿选课记录、
有无同一学生同一课程的多条有效记录。建库脚本每次执行也会跑一遍容量一致性校验。

开发阶段执行过的测试（266 个单元/接口用例 + 三种角色的浏览器全流程集成测试）
**代码与截图未随包提交**，过程、结果与缺陷记录见
[`docs/测试报告.md`](docs/测试报告.md)，手工验证步骤见
[`docs/演示脚本.md`](docs/演示脚本.md)。

---

## 文档

| 文档 | 内容 |
|---|---|
| [`docs/设计说明.md`](docs/设计说明.md) | 需求、架构、数据库设计、关键算法、开闭原则落地 |
| [`docs/测试报告.md`](docs/测试报告.md) | 单元测试与浏览器集成测试的过程、结果、缺陷记录 |
| [`docs/演示脚本.md`](docs/演示脚本.md) | 答辩演示的分步操作脚本 |
| [`docs/api-contract.md`](docs/api-contract.md) | 全部 REST 端点与错误码 |

---

## 从参考项目迁移时的技术差异

| 参考项目（MySQL 8） | 本项目（SQLite） | 原因 |
|---|---|---|
| `FIELD(a, b, c)` | `CASE WHEN` | SQLite 无 `FIELD()` |
| `CONCAT(a, b)` | `a \|\| b` | SQLite 的 `\|\|` 即字符串拼接 |
| `DATE_SUB(NOW(), INTERVAL n DAY)` | `datetime('now', '-n days')` | 函数名不同 |
| `EXPLAIN` | `EXPLAIN QUERY PLAN` | 执行计划输出格式不同 |
| `DECIMAL(3,1)` | `NUMERIC` + 读出后转 `float` | SQLite 无定点类型 |
| 默认 `REPEATABLE READ` 事务 | `BEGIN IMMEDIATE` 显式写事务 | SQLite 只有库级写锁，需主动升级 |
| `spring.datasource` 连接池 | 线程局部连接 + WAL + `busy_timeout` | 标准库 `sqlite3` 无连接池 |
