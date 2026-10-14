-- =============================================================================
--  高校选课管理系统 - 数据库结构脚本 (DDL)
--  数据库：SQLite 3.35+     引擎：WAL
--
--  说明：
--    1. 本脚本只删除并重建本系统自己的 6 张表与 2 个视图。
--    2. 表结构由本脚本决定，应用侧不做任何自动建表（对标参考项目的
--       spring.jpa.hibernate.ddl-auto=validate，实体只做校验）。
--    3. 执行顺序：01_schema.sql -> 02_seed_data.sql
--    4. 与 MySQL 版的差异（方言适配，语义不变）：
--         · AUTO_INCREMENT      -> INTEGER PRIMARY KEY AUTOINCREMENT
--         · DATETIME 默认值      -> TEXT + datetime('now','localtime')
--         · DECIMAL(3,1)        -> NUMERIC（SQLite 无定点类型，按列亲和性存 REAL）
--         · 表内 KEY/UNIQUE KEY -> 独立 CREATE INDEX / CREATE UNIQUE INDEX
--         · COMMENT             -> 行内 SQL 注释
-- =============================================================================

PRAGMA foreign_keys = ON;

-- 按外键依赖的反序删除（子表在前，父表在后）
DROP VIEW  IF EXISTS v_course_detail;
DROP VIEW  IF EXISTS v_student_credit;
DROP TABLE IF EXISTS enrollment;
DROP TABLE IF EXISTS course_schedule;
DROP TABLE IF EXISTS course;
DROP TABLE IF EXISTS student;
DROP TABLE IF EXISTS teacher;
DROP TABLE IF EXISTS sys_user;


-- =============================================================================
-- 1. sys_user  统一用户表
--    认证与业务解耦：学生/教师/管理员共用一张账号表，业务属性放在各自业务表
-- =============================================================================
CREATE TABLE sys_user (
  id            INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
  username      VARCHAR(50)  NOT NULL,              -- 登录账号（学号/工号）
  password_hash VARCHAR(100) NOT NULL,              -- BCrypt 加密后的密码
  role          VARCHAR(20)  NOT NULL,              -- STUDENT / TEACHER / ADMIN
  real_name     VARCHAR(50)  NOT NULL,              -- 真实姓名
  status        INTEGER      NOT NULL DEFAULT 1,    -- 1 启用 0 禁用
  created_at    TEXT         NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE UNIQUE INDEX uk_username ON sys_user (username);
CREATE INDEX        idx_role    ON sys_user (role);


-- =============================================================================
-- 2. student  学生表
-- =============================================================================
CREATE TABLE student (
  id         INTEGER     NOT NULL PRIMARY KEY AUTOINCREMENT,
  user_id    INTEGER     NOT NULL,
  student_no VARCHAR(20) NOT NULL,                  -- 学号
  name       VARCHAR(50) NOT NULL,
  gender     CHAR(1)     NOT NULL DEFAULT 'M',      -- M 男 / F 女
  major      VARCHAR(50) NOT NULL,                  -- 专业
  grade      VARCHAR(10) NOT NULL,                  -- 年级，如 2023
  phone      VARCHAR(20),
  CONSTRAINT fk_student_user FOREIGN KEY (user_id) REFERENCES sys_user (id)
);
CREATE UNIQUE INDEX uk_student_no   ON student (student_no);
CREATE UNIQUE INDEX uk_student_user ON student (user_id);
CREATE INDEX        idx_major_grade ON student (major, grade);


-- =============================================================================
-- 3. teacher  教师表
-- =============================================================================
CREATE TABLE teacher (
  id         INTEGER     NOT NULL PRIMARY KEY AUTOINCREMENT,
  user_id    INTEGER     NOT NULL,
  teacher_no VARCHAR(20) NOT NULL,                  -- 工号
  name       VARCHAR(50) NOT NULL,
  title      VARCHAR(20),                           -- 职称：教授/副教授/讲师
  dept       VARCHAR(50) NOT NULL,                  -- 所属院系
  CONSTRAINT fk_teacher_user FOREIGN KEY (user_id) REFERENCES sys_user (id)
);
CREATE UNIQUE INDEX uk_teacher_no   ON teacher (teacher_no);
CREATE UNIQUE INDEX uk_teacher_user ON teacher (user_id);


-- =============================================================================
-- 4. course  课程表
--    enrolled_count 是「有意为之的反范式」：避免每次查余量都要 COUNT 聚合，
--    其一致性由 chk_capacity 约束 + Service 层事务共同保证。
-- =============================================================================
CREATE TABLE course (
  id             INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
  course_code    VARCHAR(20)  NOT NULL,             -- 课程代码
  name           VARCHAR(100) NOT NULL,             -- 课程名称
  credit         NUMERIC      NOT NULL,             -- 学分（对标 DECIMAL(3,1)）
  hours          INTEGER      NOT NULL,             -- 学时
  course_type    VARCHAR(20)  NOT NULL,             -- 必修/选修/公选
  dept           VARCHAR(50)  NOT NULL,             -- 开课院系
  semester       VARCHAR(20)  NOT NULL,             -- 学期，如 2026-2027-1
  teacher_id     INTEGER      NOT NULL,             -- 授课教师
  capacity       INTEGER      NOT NULL,             -- 容量上限
  enrolled_count INTEGER      NOT NULL DEFAULT 0,   -- 已选人数（冗余字段）
  status         VARCHAR(20)  NOT NULL DEFAULT 'OPEN', -- OPEN 开放选课 / CLOSED 已关闭
  intro          VARCHAR(500),
  created_at     TEXT         NOT NULL DEFAULT (datetime('now','localtime')),
  CONSTRAINT fk_course_teacher FOREIGN KEY (teacher_id) REFERENCES teacher (id),
  CONSTRAINT chk_capacity CHECK (enrolled_count >= 0 AND enrolled_count <= capacity)
);
CREATE UNIQUE INDEX uk_code_semester    ON course (course_code, semester);
CREATE INDEX        idx_teacher         ON course (teacher_id);
CREATE INDEX        idx_semester_status ON course (semester, status);


-- =============================================================================
-- 5. course_schedule  上课时间表
--    独立成表的原因：一门课可能有多段上课时间（理论课+实验课），
--    且时间冲突检测需要按 (weekday, 节次区间) 做区间重叠比较。
-- =============================================================================
CREATE TABLE course_schedule (
  id            INTEGER     NOT NULL PRIMARY KEY AUTOINCREMENT,
  course_id     INTEGER     NOT NULL,
  weekday       INTEGER     NOT NULL,               -- 1=周一 ... 7=周日
  start_section INTEGER     NOT NULL,               -- 开始节次 1-12
  end_section   INTEGER     NOT NULL,               -- 结束节次 1-12
  start_week    INTEGER     NOT NULL,               -- 起始周
  end_week      INTEGER     NOT NULL,               -- 结束周
  classroom     VARCHAR(50),
  CONSTRAINT fk_cs_course FOREIGN KEY (course_id) REFERENCES course (id),
  CONSTRAINT chk_section CHECK (start_section > 0 AND end_section >= start_section),
  CONSTRAINT chk_week    CHECK (start_week > 0 AND end_week >= start_week)
);
CREATE INDEX idx_cs_course  ON course_schedule (course_id);
CREATE INDEX idx_cs_weekday ON course_schedule (weekday, start_section, end_section);


-- =============================================================================
-- 6. enrollment  选课记录表
--    student 与 course 的多对多关系由本表拆解。
--    uk_student_course 唯一索引是「防重复选课」的数据库级兜底。
-- =============================================================================
CREATE TABLE enrollment (
  id          INTEGER     NOT NULL PRIMARY KEY AUTOINCREMENT,
  student_id  INTEGER     NOT NULL,
  course_id   INTEGER     NOT NULL,
  status      VARCHAR(20) NOT NULL DEFAULT 'SELECTED', -- SELECTED 已选 / WITHDRAWN 已退
  score       NUMERIC,                                 -- 成绩，NULL 表示未录入
  selected_at TEXT        NOT NULL DEFAULT (datetime('now','localtime')),
  CONSTRAINT fk_enroll_student FOREIGN KEY (student_id) REFERENCES student (id),
  CONSTRAINT fk_enroll_course  FOREIGN KEY (course_id)  REFERENCES course (id),
  CONSTRAINT chk_score CHECK (score IS NULL OR (score >= 0 AND score <= 100))
);
CREATE UNIQUE INDEX uk_student_course        ON enrollment (student_id, course_id);
CREATE INDEX        idx_enroll_course_status ON enrollment (course_id, status);
CREATE INDEX        idx_enroll_student_status ON enrollment (student_id, status);


-- =============================================================================
-- 视图（课程要求加分项：用视图封装高频的多表连接）
-- =============================================================================

-- 课程详情 + 剩余容量（前端课程列表直接查这个视图）
CREATE VIEW v_course_detail AS
SELECT c.id,
       c.course_code,
       c.name,
       c.credit,
       c.hours,
       c.course_type,
       c.dept,
       c.semester,
       c.teacher_id,
       t.name  AS teacher_name,
       t.title AS teacher_title,
       c.capacity,
       c.enrolled_count,
       (c.capacity - c.enrolled_count) AS remaining,
       c.status,
       c.intro
FROM course c
JOIN teacher t ON t.id = c.teacher_id;

-- 学生学分统计
CREATE VIEW v_student_credit AS
SELECT s.id         AS student_id,
       s.student_no,
       s.name,
       s.major,
       c.semester,
       COUNT(e.id)  AS course_count,
       IFNULL(SUM(c.credit), 0) AS total_credit
FROM student s
LEFT JOIN enrollment e ON e.student_id = s.id AND e.status = 'SELECTED'
LEFT JOIN course c     ON c.id = e.course_id
GROUP BY s.id, s.student_no, s.name, s.major, c.semester;


-- =============================================================================
-- 结构校验：确认表已创建
-- =============================================================================
SELECT type, name FROM sqlite_master
WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%'
ORDER BY type, name;
