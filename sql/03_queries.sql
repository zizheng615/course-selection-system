-- =============================================================================
--  高校选课管理系统（Python + SQLite） —— 演示查询脚本
--
--  用途：逐条演示本项目的 SQL 设计，体现「多表连接 / 聚合统计 / 区间重叠 /
--        执行计划优化 / 冗余计数一致性校验」。
--
--  依赖：先执行 01_schema.sql 与 02_seed_data.sql
--  运行：python scripts/run_queries.py       （或 sqlite3 data/course_selection.db < 本文件）
--
--  ── 与 MySQL 参考版的方言差异（逐条列出，便于对照）────────────────────
--    · `FIELD(x, ...)`        -> `CASE WHEN x = ... THEN n END`
--    · `CONCAT(a, b)`         -> `a || b`
--    · `DATE_SUB(NOW(), INTERVAL n DAY)` -> `datetime('now','localtime','-n days')`
--    · `EXPLAIN`              -> `EXPLAIN QUERY PLAN`
--    · `EXPLAIN ... FORCE INDEX` -> `... NOT INDEXED`（SQLite 只支持反向提示）
--    · **整数除法**           -> `COUNT(*) / capacity` 在 SQLite 里恒为 0，
--                                必须写成 `COUNT(*) * 100.0 / capacity`
--    · 变量                   -> SQLite 无会话变量，演示参数直接写成字面量
-- =============================================================================


-- =============================================================================
--  演示参数（按需替换）
--    student_no  演示学生学号   默认 2023050（吴悦心）
--    course_id   演示课程 id    默认 1（数据结构 CS101，两段上课时间：周三 1-2 与 周三 9-10）
--    semester    演示学期       默认 2026-2027-1
--
--  为什么挑 2023050 而不是 stu001：这位同学选了《数据结构》（周三 1-2 节），
--  而《线性代数》（MA102）恰好也排在周三 1-2 节 —— 这是种子数据里**刻意埋下的
--  一对冲突课程**。于是查询 3（可选课程）会把它排除掉，查询 3b（冲突反查）
--  会把它指出来，一正一反都能看到实际效果；用别的学生这两个查询都会是空集，
--  演示不出「区间重叠」这件事。
-- =============================================================================


-- =============================================================================
-- 查询 1：课程列表 + 剩余容量（多表连接 / 视图）
-- 说明：课程 JOIN 教师，并用视图里算好的 remaining 供选课页展示。
-- =============================================================================
SELECT id,
       course_code,
       name,
       credit,
       course_type,
       dept,
       teacher_name,
       teacher_title,
       capacity,
       enrolled_count,
       remaining,
       status
FROM v_course_detail
WHERE semester = '2026-2027-1'
ORDER BY course_code;


-- =============================================================================
-- 查询 2：学生个人课表（多表连接 + 排序）
-- 说明：从选课记录出发，连接课程、教师、上课时间三张表，按星期与节次排序。
--      只取 SELECTED —— 退课的记录不占课表。
-- =============================================================================
SELECT c.course_code,
       c.name          AS course_name,
       t.name          AS teacher_name,
       cs.weekday,
       CASE cs.weekday
            WHEN 1 THEN '周一' WHEN 2 THEN '周二' WHEN 3 THEN '周三' WHEN 4 THEN '周四'
            WHEN 5 THEN '周五' WHEN 6 THEN '周六' WHEN 7 THEN '周日'
       END             AS weekday_name,
       cs.start_section,
       cs.end_section,
       cs.start_week,
       cs.end_week,
       cs.classroom
FROM enrollment e
JOIN student        s  ON s.id = e.student_id
JOIN course         c  ON c.id = e.course_id
JOIN teacher        t  ON t.id = c.teacher_id
JOIN course_schedule cs ON cs.course_id = c.id
WHERE s.student_no = '2023050'
  AND e.status = 'SELECTED'
ORDER BY cs.weekday, cs.start_section;


-- =============================================================================
-- 查询 3：时间冲突检测 ★（区间重叠判定）
-- 说明：找出该学生「未选过、课程开放、有余量、且不与已选课程时间冲突」的课程。
--
--      区间重叠公式：A.start <= B.end AND B.start <= A.end
--      两门课在**同一天**且**节次区间相交**即为冲突。
--
--      全部在 SQL 内完成，不需要把课表捞进应用内存里两两比较 ——
--      这是本项目三处冲突判断（可选课程 / 冲突反查 / 选课校验）共用的同一套逻辑。
-- =============================================================================
SELECT c.id,
       c.course_code,
       c.name,
       c.credit,
       c.capacity,
       c.enrolled_count,
       (c.capacity - c.enrolled_count) AS remaining
FROM course c
WHERE c.semester = '2026-2027-1'
  AND c.status = 'OPEN'
  AND c.enrolled_count < c.capacity
  AND NOT EXISTS (
        SELECT 1 FROM enrollment e
         WHERE e.course_id = c.id AND e.student_id = (
               SELECT id FROM student WHERE student_no = '2023050')
      )
  AND NOT EXISTS (
        SELECT 1
          FROM course_schedule cs_new
          JOIN course_schedule cs_old ON cs_old.weekday = cs_new.weekday
          JOIN enrollment      e      ON e.course_id = cs_old.course_id
          JOIN student         s      ON s.id = e.student_id
         WHERE cs_new.course_id = c.id
           AND s.student_no = '2023050'
           AND e.status = 'SELECTED'
           -- 区间重叠：两段节次区间相交
           AND cs_new.start_section <= cs_old.end_section
           AND cs_old.start_section <= cs_new.end_section
      )
ORDER BY c.course_code;


-- =============================================================================
-- 查询 3b：反查 —— 列出与该学生已选课程「确实冲突」的课程
-- 说明：与查询 3 互为反面。前端顶部的黄色告警条就是靠它给出
--       「《某课》被你已选的《另一门课》挡住了」，否则学生只会看到课程凭空消失。
-- =============================================================================
SELECT DISTINCT
       c.id,
       c.course_code,
       c.name
FROM course c
JOIN course_schedule cs_new ON cs_new.course_id = c.id
JOIN course_schedule cs_old ON cs_old.weekday = cs_new.weekday
JOIN enrollment      e      ON e.course_id = cs_old.course_id
JOIN student         s      ON s.id = e.student_id
JOIN course          blocked ON blocked.id = cs_old.course_id
WHERE s.student_no = '2023050'
  AND e.status = 'SELECTED'
  AND c.id <> cs_old.course_id
  AND cs_new.start_section <= cs_old.end_section
  AND cs_old.start_section <= cs_new.end_section
ORDER BY c.course_code;


-- =============================================================================
-- 查询 4：热门课程 Top 10（聚合 + 排行 + 占比）
-- 说明：按选课人数降序，并计算「满座率」。
--
--  ⚠ SQLite 陷阱：`COUNT(...) / capacity` 是**整数除法**，结果恒为 0。
--    必须乘 100.0 提升为浮点，这里就是 Python 版踩过并修掉的那个坑。
-- =============================================================================
SELECT c.course_code,
       c.name           AS course_name,
       t.name           AS teacher_name,
       c.capacity,
       COUNT(e.id)      AS selected_count,
       COUNT(e.id) * 100.0 / c.capacity AS fill_rate
FROM course c
JOIN teacher t        ON t.id = c.teacher_id
LEFT JOIN enrollment e ON e.course_id = c.id AND e.status = 'SELECTED'
WHERE c.semester = '2026-2027-1'
GROUP BY c.id, c.course_code, c.name, t.name, c.capacity
ORDER BY selected_count DESC, c.course_code
LIMIT 10;


-- =============================================================================
-- 查询 5：各专业选课分布（多维聚合）
-- 说明：LEFT JOIN 保证**没有选课记录的专业也会出现**，
--       否则报表里会凭空少掉几个专业，看起来像数据丢了。
-- =============================================================================
SELECT s.major,
       COUNT(DISTINCT s.id) AS student_count,
       COUNT(e.id)          AS enrollment_count,
       COUNT(e.id) * 1.0 / COUNT(DISTINCT s.id) AS avg_courses_per_student
FROM student s
LEFT JOIN enrollment e ON e.student_id = s.id AND e.status = 'SELECTED'
GROUP BY s.major
ORDER BY enrollment_count DESC, s.major;


-- =============================================================================
-- 查询 6：学生学分统计（视图 + 聚合）
-- 说明：直接查 v_student_credit 视图；只统计 SELECTED，退课不计学分。
-- =============================================================================
SELECT student_no, name, major, semester, course_count, total_credit
FROM v_student_credit
WHERE semester = '2026-2027-1'
ORDER BY total_credit DESC, student_no
LIMIT 20;


-- =============================================================================
-- 查询 7：某门课程的学生名单与成绩（教师端 / 管理员端）
-- 说明：只取 SELECTED —— 退课的学生不出现在名单里，
--       因此「给已退课学生录成绩」在界面上根本不会发生。
-- =============================================================================
SELECT s.student_no,
       s.name   AS student_name,
       s.major,
       s.grade,
       e.status,
       e.score
FROM enrollment e
JOIN student s ON s.id = e.student_id
WHERE e.course_id = 1
  AND e.status = 'SELECTED'
ORDER BY s.student_no;


-- =============================================================================
-- 查询 8：教师工作量统计（按选课人数汇总）
-- 说明：学期条件写在 LEFT JOIN 的 ON 里（与参考项目一致），
--       这样查一个没有课的学期时，教师仍会以 0 出现，报表不会「缺人」。
--
--       人数直接累加 course.enrolled_count，而不是再 JOIN 一次 enrollment：
--       后者要对每门课的行做去重计数，容易在「一门课多个学生」时写错。
--       这里依赖的正是那条不变量 —— enrolled_count 与真实 SELECTED 记录数一致
--       （由脚本末尾的一致性自检守住）。
-- =============================================================================
SELECT t.name                          AS teacher_name,
       t.title,
       t.dept,
       COUNT(DISTINCT c.id)            AS course_count,
       IFNULL(SUM(c.enrolled_count), 0) AS total_students,
       IFNULL(SUM(c.credit), 0)        AS total_credit
FROM teacher t
LEFT JOIN course c ON c.teacher_id = t.id AND c.semester = '2026-2027-1'
GROUP BY t.id, t.name, t.title, t.dept
ORDER BY total_students DESC, t.name;


-- =============================================================================
-- 执行计划对比（数据库工程实践加分项）
-- 演示 idx_semester_status 索引对课程列表查询的优化效果。
-- MySQL 的 `type=ref` / `type=ALL` 在 SQLite 里对应 `SEARCH ... USING INDEX`
-- 与 `SCAN`。
-- =============================================================================

-- 8.1 走索引：SEARCH course USING INDEX idx_semester_status
EXPLAIN QUERY PLAN
SELECT c.id, c.name, c.capacity, c.enrolled_count
FROM course c
WHERE c.semester = '2026-2027-1' AND c.status = 'OPEN';

-- 8.2 反向对比：NOT INDEXED 强制全表扫描，计划变成 SCAN course
EXPLAIN QUERY PLAN
SELECT c.id, c.name, c.capacity, c.enrolled_count
FROM course c NOT INDEXED
WHERE c.semester = '2026-2027-1' AND c.status = 'OPEN';

-- 8.3 冲突检测的执行计划：确认命中 idx_cs_weekday
EXPLAIN QUERY PLAN
SELECT cs_new.course_id
FROM course_schedule cs_new
JOIN course_schedule cs_old ON cs_old.weekday = cs_new.weekday
WHERE cs_new.course_id = 2
  AND cs_new.start_section <= cs_old.end_section
  AND cs_old.start_section <= cs_new.end_section;

-- 8.4 选课记录按「课程 + 状态」过滤：命中 idx_enroll_course_status
EXPLAIN QUERY PLAN
SELECT COUNT(*) FROM enrollment e
WHERE e.course_id = 1 AND e.status = 'SELECTED';


-- =============================================================================
-- 并发安全性自检：确认冗余计数 `course.enrolled_count` 与真实选课记录数一致
--
-- 这两者一旦不一致，说明「选课」或「退课」事务里有一条路径漏改了计数 ——
-- 表现在界面上就是「名额还剩 1 但选不上」或者「已经超卖了」。
-- 「选课」与「退课」两条事务路径都必须维护住这条不变量，任何一条漏改都会被它抓出来。
--
-- **正常情况下应返回空结果集。**
-- =============================================================================

-- 9.1 逐门课核对
SELECT c.id,
       c.course_code,
       c.name,
       c.capacity,
       c.enrolled_count                     AS 冗余计数,
       COUNT(e.id)                          AS 真实选课数,
       COUNT(e.id) - c.enrolled_count       AS 差额
FROM course c
LEFT JOIN enrollment e ON e.course_id = c.id AND e.status = 'SELECTED'
GROUP BY c.id, c.course_code, c.name, c.capacity, c.enrolled_count
HAVING COUNT(e.id) <> c.enrolled_count;

-- 9.2 一句话总账：两边都为 0 才算干净
SELECT (SELECT IFNULL(SUM(enrolled_count), 0) FROM course)            AS 计数合计,
       (SELECT COUNT(*) FROM enrollment WHERE status = 'SELECTED')    AS 记录合计;

-- 9.3 从未出现过超卖：任何一门课的已选人数都不应超过容量
SELECT id, course_code, name, capacity, enrolled_count
FROM course
WHERE enrolled_count > capacity;

-- 9.4 唯一约束没被绕过：一个学生同一门课最多一条记录（含已退课）
SELECT student_id, course_id, COUNT(*) AS 记录数
FROM enrollment
GROUP BY student_id, course_id
HAVING COUNT(*) > 1;
