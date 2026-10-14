/**
 * 页面注册表 —— 前端侧的「开闭原则」扩展点。
 *
 * 约定：每个页面模块导出 `render(container, route)`，在容器里自行加载数据并渲染。
 * `router.js` 的路由表通过 `view: "键名"` 指向这里的一项。
 *
 * 新增一个页面：
 *   1. 新建 `views/xxx.js`，导出 `render`；
 *   2. 在下面注册 `xxx: renderXxx`；
 *   3. 在 `router.js` 的 routes 里加一条 `{ path, view: 'xxx', title, roles }`，
 *      需要出现在菜单里的话再去 `layout.js` 的 MENU_GROUPS 加一项。
 *
 * 三张表（routes / VIEWS / MENU_GROUPS）必须同时更新：只改其中两张的话，
 * 症状是「点菜单白屏」或「页面在但菜单里找不到」，都很难人工发现。
 */

import { render as renderLogin } from './login.js'
import { render as renderCourseAdmin } from './courseAdmin.js'
import { render as renderScheduleAdmin } from './scheduleAdmin.js'
import { render as renderStudentAdmin } from './studentAdmin.js'
import { render as renderTeacherAdmin } from './teacherAdmin.js'
import { render as renderUserAdmin } from './userAdmin.js'
import { render as renderEnrollmentAdmin } from './enrollmentAdmin.js'
import { render as renderStatsAdmin } from './statsAdmin.js'
import { render as renderCourseSelect } from './courseSelect.js'
import { render as renderMyTimetable } from './myTimetable.js'
import { render as renderMyCourse } from './myCourse.js'

export const VIEWS = {
  login: renderLogin,
  courseAdmin: renderCourseAdmin,
  scheduleAdmin: renderScheduleAdmin,
  studentAdmin: renderStudentAdmin,
  teacherAdmin: renderTeacherAdmin,
  userAdmin: renderUserAdmin,
  enrollmentAdmin: renderEnrollmentAdmin,
  statsAdmin: renderStatsAdmin,
  courseSelect: renderCourseSelect,
  myTimetable: renderMyTimetable,
  myCourse: renderMyCourse,
}
