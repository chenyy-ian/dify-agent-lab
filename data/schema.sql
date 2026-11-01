-- student_grades：NL2SQL 示例库（MySQL 8.0+）
-- 字段与 apps/nlp2sql-analytics-agent.yml 中注入给模型的表结构保持一致。

DROP TABLE IF EXISTS student_grades;

CREATE TABLE student_grades (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    student_id   VARCHAR(20)  NOT NULL COMMENT '学号',
    student_name VARCHAR(50)  NOT NULL COMMENT '学生姓名',
    class_name   VARCHAR(50)  NOT NULL COMMENT '班级',
    subject      VARCHAR(50)  NOT NULL COMMENT '科目',
    score        DECIMAL(5,2) NOT NULL COMMENT '分数',
    exam_date    DATE         NOT NULL COMMENT '考试日期',
    semester     VARCHAR(50)  NOT NULL COMMENT '学期',
    grade        VARCHAR(50)  NOT NULL COMMENT '年级',
    created_at   DATETIME     NOT NULL COMMENT '记录创建时间',
    updated_at   DATETIME     NOT NULL COMMENT '记录更新时间',
    KEY idx_subject    (subject),
    KEY idx_class_name (class_name),
    KEY idx_semester   (semester),
    KEY idx_grade      (grade),
    KEY idx_exam_date  (exam_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学生成绩信息表';
