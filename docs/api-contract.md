# 选课管理系统 API 契约

本文件是 Python 重实现所依据的**接口事实来源**，逐字段抄录自参考项目
`backend/src/main/java/com/example/cs/`（controller / dto / vo / common）。
共 **45 个端点**。

## 0. 全局约定

* 所有端点挂在 `/api` 下。
* 统一响应体 `Result<T>`：`{ code, message, data }`；成功时 `message` 恒为字面量 `"ok"`，
  `Result<Void>` 的 `data` 为 `null`。
* **HTTP 状态码恒为 200**，业务成败只由 `code` 表达。
* 分页响应 `data` 段为 `PageResult<T>`：`{ list, total, page, size }`，`page` 从 1 开始。
* 认证头 `Authorization: Bearer <JWT>`。放行路径：`POST /api/auth/login`、`/api/public/**`。
* 角色：`ADMIN` / `TEACHER` / `STUDENT`。**方法级注解读优于类级**；无注解 = 任意已登录用户可访问。
* 时间字段 JSON 格式 `yyyy-MM-dd HH:mm:ss`。
* 字段名一律 camelCase（与 Java 字段名一致）。

---

## 1. 认证 — 前缀 `/api/auth`（类级无角色限制）

| # | 方法 | 路径 | 角色 | 入参 | 出参 |
|---|---|---|---|---|---|
| E01 | POST | `/api/auth/login` | 公开 | body `LoginDTO{username*, password*}` | `Result<LoginVO>` |
| E02 | GET | `/api/auth/me` | 已登录 | — | `Result<LoginVO>` |

`LoginVO`：`token`, `userId`, `username`, `role`, `realName`, `refId`（学生=student.id / 教师=teacher.id，管理员为 null）, `expireHours`。
> E02 返回的 `token` 与 `expireHours` 均为 `null`，只回填用户信息。

E01 错误：`1001` 账号或密码错误 / 该账号已被禁用，请联系管理员。

---

## 2. 学生 — 前缀 `/api/students`（类级 `ADMIN`）

| # | 方法 | 路径 | 入参 | 出参 |
|---|---|---|---|---|
| E03 | GET | `/api/students` | `keyword?`, `major?`, `page=1`, `size=10` | `Result<PageResult<StudentVO>>` |
| E04 | GET | `/api/students/majors` | — | `Result<List<String>>` |
| E05 | POST | `/api/students` | body `StudentDTO` | `Result<StudentVO>` |
| E06 | PUT | `/api/students/{id}` | body `StudentDTO` | `Result<StudentVO>` |
| E07 | DELETE | `/api/students/{id}` | — | `Result<Void>` |

`StudentVO`：`id, userId, studentNo, name, gender, major, grade, phone`

`StudentDTO`：`studentNo*`(≤20) `name*`(≤50) `gender`(`^[MF]$`，默认 `M`) `major*` `grade*` `phone`(≤20) `username` `password`
> `username` 缺省时取 `studentNo`；新建学生必然同时建登录账号（初始密码 `123456`）。
> 错误：`4007` 学号已存在 / 登录账号已存在；`3001` 学生不存在；`4006` 存在选课历史（含已退课）不允许删除。

---

## 3. 教师 — 前缀 `/api/teachers`（类级 `ADMIN`）

| # | 方法 | 路径 | 入参 | 出参 |
|---|---|---|---|---|
| E08 | GET | `/api/teachers` | `keyword?`, `dept?`, `page=1`, `size=10` | `Result<PageResult<TeacherVO>>` |
| E09 | GET | `/api/teachers/all` | — | `Result<List<TeacherVO>>` |
| E10 | POST | `/api/teachers` | body `TeacherDTO` | `Result<TeacherVO>` |
| E11 | PUT | `/api/teachers/{id}` | body `TeacherDTO` | `Result<TeacherVO>` |
| E12 | DELETE | `/api/teachers/{id}` | — | `Result<Void>` |

`TeacherVO`：`id, userId, teacherNo, name, title, dept`
`TeacherDTO`：`teacherNo*`(≤20) `name*`(≤50) `title` `dept*` `username` `password`
> 错误：`4007` 工号已存在；`3001` 教师不存在；`4006` 该教师还有 N 门课程。

---

## 4. 课程 — 前缀 `/api/courses`（逐方法标注）

| # | 方法 | 路径 | 角色 | 入参 | 出参 |
|---|---|---|---|---|---|
| E13 | GET | `/api/courses` | 已登录 | `keyword?`, `semester?`, `status?`, `page=1`, `size=10` | `Result<PageResult<CourseVO>>` |
| E14 | GET | `/api/courses/semesters` | 已登录 | — | `Result<List<String>>` |
| E15 | GET | `/api/courses/my` | TEACHER | `semester?` | `Result<List<CourseVO>>` |
| E16 | GET | `/api/courses/{id}` | 已登录 | — | `Result<CourseVO>` |
| E17 | POST | `/api/courses` | ADMIN | body `CourseDTO` | `Result<CourseVO>` |
| E18 | PUT | `/api/courses/{id}` | ADMIN | body `CourseDTO` | `Result<CourseVO>` |
| E19 | PATCH | `/api/courses/{id}/status` | ADMIN | query `status*`（`OPEN`/`CLOSED`） | `Result<Void>` |
| E20 | DELETE | `/api/courses/{id}` | ADMIN | — | `Result<Void>` |

`CourseVO`（17 字段，声明顺序）：
`id, courseCode, name, credit, hours, courseType, dept, semester, teacherId, teacherName, teacherTitle, capacity, enrolledCount, remaining, status, intro, conflictWith`
> `conflictWith` **仅**由 E37 `/enrollments/conflicts` 填充，其余场景为 `null`。
> E36 `/enrollments/available` 返回的行只有 `id, courseCode, name, credit, courseType, dept, teacherName, teacherTitle, capacity, enrolledCount, remaining` 有值，
> `status` 强制为 `"OPEN"`，`hours/semester/teacherId/intro/conflictWith` 均为 `null`。

`CourseDTO`：`courseCode*`(≤20) `name*`(≤100) `credit*`(0.5–20) `hours*`(≥1) `courseType*` `dept*` `semester*` `teacherId*` `capacity*`(≥1) `status`(`OPEN`/`CLOSED`，缺省 `OPEN`) `intro`(≤500)
> 错误：`4007` 课程代码已存在；`3001` 课程不存在 / 授课教师不存在；`2000` 容量不能小于当前已选人数 N；`4006` 该课程已有 N 条选课记录。

---

## 5. 排课 — 前缀 `/api/schedules`

| # | 方法 | 路径 | 角色 | 入参 | 出参 |
|---|---|---|---|---|---|
| E21 | GET | `/api/schedules` | 已登录 | `courseId*` | `Result<List<ScheduleVO>>` |
| E22 | POST | `/api/schedules` | ADMIN | body `ScheduleDTO` | `Result<ScheduleVO>` |
| E23 | PUT | `/api/schedules/{id}` | ADMIN | body `ScheduleDTO` | `Result<ScheduleVO>` |
| E24 | DELETE | `/api/schedules/{id}` | ADMIN | — | `Result<Void>` |

`ScheduleVO`：`id, courseId, courseName, weekday, weekdayName, startSection, endSection, startWeek, endWeek, classroom`
`ScheduleDTO`：`courseId*` `weekday*`(1–7) `startSection*`(1–12) `endSection*`(1–12) `startWeek*`(1–30) `endWeek*`(1–30) `classroom`(≤50)
> 错误：`3001` 课程不存在 / 上课时间记录不存在；`2000` 开始节次不能大于结束节次 / 起始周不能大于结束周；
> `4003` 该教师在周X S-E 节已有其他课程安排，排课冲突。

---

## 6. 统计 — 前缀 `/api/stats`（类级 `ADMIN`）

| # | 方法 | 路径 | 入参 | 出参 |
|---|---|---|---|---|
| E25 | GET | `/api/stats/popular-courses` | `semester?`, `limit=10` | `Result<List<PopularCourseVO>>` |
| E26 | GET | `/api/stats/major-distribution` | — | `Result<List<MajorStatVO>>` |
| E27 | GET | `/api/stats/teacher-workload` | `semester?` | `Result<List<TeacherWorkloadVO>>` |

* `PopularCourseVO`：`courseCode, courseName, teacherName, capacity, selectedCount, fillRate`（百分比，如 `83.3`）
* `MajorStatVO`：`major, studentCount, enrollmentCount, avgCoursesPerStudent`
* `TeacherWorkloadVO`：`teacherName, title, dept, courseCount, totalStudents, totalCredit`

---

## 7. 账号 — 前缀 `/api/users`（类级 `ADMIN`）

| # | 方法 | 路径 | 入参 | 出参 |
|---|---|---|---|---|
| E28 | GET | `/api/users` | `keyword?`, `role?`, `page=1`, `size=10` | `Result<PageResult<UserVO>>` |
| E29 | PUT | `/api/users/{id}/credentials` | body `UserCredentialDTO` | `Result<Void>` |
| E30 | PATCH | `/api/users/{id}/status` | query `status*`(1/0) | `Result<Void>` |
| E31 | DELETE | `/api/users/{id}` | — | `Result<Void>` |

`UserVO`：`id, username, role, roleName(管理员/教师/学生), realName, status, createdAt, linkType(学生/教师/—), linkNo, linkExtra`
`UserCredentialDTO`：`username*`(3–50, `^[A-Za-z0-9_.-]+$`) `password`(6–32，**留空 = 不改密码**)
> 错误：`3001` 账号不存在；`4007` 登录账号已被占用：X；
> `2000` 状态只能为 1（启用）或 0（禁用）/ 不能禁用当前登录的账号 / 不能删除当前登录的账号；
> `4006` 该账号已绑定学生信息… / 该账号已绑定教师信息…。

---

## 8. 选课 — `EnrollmentController` 前缀为 `/api`（逐方法标注）

| # | 方法 | 路径 | 角色 | 入参 | 出参 |
|---|---|---|---|---|---|
| E32 | POST | `/api/enrollments` | STUDENT | body `SelectCourseDTO{courseId*}` | `Result<Void>` |
| E33 | DELETE | `/api/enrollments/{courseId}` | STUDENT | — | `Result<Void>`（软退课） |
| E34 | GET | `/api/enrollments/my` | STUDENT | `semester?` | `Result<List<MyCourseVO>>` |
| E35 | GET | `/api/enrollments/my/timetable` | STUDENT | `semester?` | `Result<List<TimetableVO>>` |
| E36 | GET | `/api/enrollments/available` | STUDENT | `semester?` | `Result<List<CourseVO>>` |
| E37 | GET | `/api/enrollments/conflicts` | STUDENT | `semester?` | `Result<List<CourseVO>>` |
| E38 | GET | `/api/courses/{courseId}/students` | TEACHER, ADMIN | — | `Result<List<CourseStudentVO>>` |
| E39 | PATCH | `/api/enrollments/score` | TEACHER, ADMIN | body `ScoreDTO{enrollmentId*, score*}` | `Result<Void>` |
| E40 | GET | `/api/enrollments` | ADMIN | `keyword?`, `courseId?`, `status?`, `page=1`, `size=10` | `Result<PageResult<EnrollmentRecordVO>>` |
| E41 | POST | `/api/enrollments/admin` | ADMIN | body `AdminEnrollDTO{studentId*, courseId*}` | `Result<Void>` |
| E42 | PATCH | `/api/enrollments/record/{id}/withdraw` | ADMIN | — | `Result<Void>`（软退课） |
| E43 | DELETE | `/api/enrollments/record/{id}` | ADMIN | — | `Result<Void>`（硬删，归还容量） |

* `MyCourseVO`：`enrollmentId, courseId, courseCode, courseName, credit, courseType, semester, teacherName, status, score, selectedAt`
* `TimetableVO`：`courseId, courseCode, courseName, credit, courseType, teacherName, weekday, weekdayName, startSection, endSection, startWeek, endWeek, classroom`
* `CourseStudentVO`：`enrollmentId, studentId, studentNo, studentName, major, grade, score`
* `EnrollmentRecordVO`：`id, studentId, studentNo, studentName, major, courseId, courseCode, courseName, teacherName, semester, status, score, selectedAt`

> 学生身份一律取自 JWT，绝不从 body 读。
> `4005` 未选该课程或已退课 / 该学生已退课，无法录入成绩 / 该记录已是退课状态。
> `5000` 课程容量计数异常，退课已回滚 / 课程容量计数异常，删除已回滚。

**路径约定**：学生自助与管理员操作都挂在 `/api/enrollments` 下，两者都有删除语义，
因此管理员操作统一加 `record` 段，避免同路径同方法冲突。

---

## 9. AI 助手 — 前缀 `/api/ai`（类级无角色限制）

| # | 方法 | 路径 | 入参 | 出参 |
|---|---|---|---|---|
| E44 | POST | `/api/ai/chat` | body `AiChatDTO{question*}`(≤500) | `Result<AiChatVO>` |
| E45 | GET | `/api/ai/suggestions` | — | `Result<List<String>>` |

`AiChatVO`：`answer, source, suggestions`
> 角色取自 JWT，不读 body。`source` 三值互不合并：`本地知识库` / `未匹配` / 配置的服务名。

---

## 10. 错误码

| 常量 | 值 | 代表消息 |
|---|---|---|
| SUCCESS | 0 | `ok` |
| LOGIN_FAILED | 1001 | 账号或密码错误 / 该账号已被禁用，请联系管理员 / 未登录，请先登录 |
| TOKEN_INVALID | 1002 | 登录已过期，请重新登录 |
| NO_PERMISSION | 1003 | 无权访问该资源，需要角色：X / 该操作仅学生可用 / 该操作仅教师可用 |
| PARAM_ERROR | 2000 | 参数校验失败 / 开始节次不能大于结束节次 / 容量不能小于当前已选人数 N 等 |
| NOT_FOUND | 3001 | 课程不存在 / 学生不存在 / 教师不存在 / 账号不存在 / 选课记录不存在 等 |
| COURSE_CLOSED | 4001 | 该课程未开放选课 |
| ALREADY_SELECTED | 4002 | 已选过该课程，请勿重复选课 |
| TIME_CONFLICT | 4003 | 该课程与已选课程上课时间冲突，无法选课 / 该教师在周X S-E 节已有其他课程安排，排课冲突 |
| COURSE_FULL | 4004 | 课程容量已满或已关闭，选课失败 |
| NOT_SELECTED | 4005 | 未选该课程或已退课 / 该学生已退课，无法录入成绩 |
| COURSE_DELETE_FORBIDDEN | 4006 | 该课程已有 N 条选课记录，无法删除… / 该学生存在 N 条选课历史记录… |
| DUPLICATE_KEY | 4007 | 学号已存在：X / 登录账号已存在：X / 登录账号已被占用：X |
| SYSTEM_ERROR | 5000 | 服务器内部错误 / 课程容量计数异常，退课已回滚 |

**数据库约束翻译**：`uk_student_course` → `4002`；`chk_capacity` → `4004`；其它完整性冲突 → `4007`。

---

## 11. 端点计数

| 控制器 | 前缀 | 端点数 |
|---|---|---|
| Auth | `/api/auth` | 2 |
| Student | `/api/students` | 5 |
| Teacher | `/api/teachers` | 5 |
| Course | `/api/courses` | 8 |
| Schedule | `/api/schedules` | 4 |
| Stats | `/api/stats` | 3 |
| User | `/api/users` | 4 |
| Enrollment | `/api` | 12 |
| AI | `/api/ai` | 2 |
| **合计** | | **45** |
