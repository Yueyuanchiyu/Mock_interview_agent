CREATE DATABASE IF NOT EXISTS ai_mock_interview
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_general_ci;

USE ai_mock_interview;

CREATE TABLE IF NOT EXISTS user_info (
  user_id INT NOT NULL AUTO_INCREMENT,
  user_name VARCHAR(50) NOT NULL,
  email VARCHAR(100) NOT NULL,
  PRIMARY KEY (user_id),
  UNIQUE KEY uk_user_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS job_role (
  id BIGINT NOT NULL AUTO_INCREMENT,
  role_code VARCHAR(50) NOT NULL,
  role_name VARCHAR(100) NOT NULL,
  description TEXT,
  created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_role_code (role_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS question_bank (
  id BIGINT NOT NULL AUTO_INCREMENT,
  role_code VARCHAR(50) NOT NULL,
  question_type VARCHAR(50) NOT NULL,
  difficulty INT DEFAULT 1,
  title TEXT NOT NULL,
  reference_answer TEXT,
  scoring_points TEXT,
  followup_points TEXT,
  tags VARCHAR(255),
  enabled TINYINT DEFAULT 1,
  created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_question_role_enabled (role_code, enabled),
  CONSTRAINT fk_question_role FOREIGN KEY (role_code)
    REFERENCES job_role (role_code) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS knowledge_doc (
  id BIGINT NOT NULL AUTO_INCREMENT,
  role_code VARCHAR(50) NOT NULL,
  title VARCHAR(255) NOT NULL,
  content LONGTEXT NOT NULL,
  source_type VARCHAR(50),
  tags VARCHAR(255),
  created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_knowledge_doc_role (role_code),
  CONSTRAINT fk_knowledge_doc_role FOREIGN KEY (role_code)
    REFERENCES job_role (role_code) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS knowledge_chunk (
  id BIGINT NOT NULL AUTO_INCREMENT,
  doc_id BIGINT NOT NULL,
  role_code VARCHAR(50) NOT NULL,
  chunk_index INT NOT NULL,
  chunk_text TEXT NOT NULL,
  keywords VARCHAR(255),
  created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_knowledge_chunk_role (role_code),
  KEY idx_knowledge_chunk_doc (doc_id),
  CONSTRAINT fk_chunk_doc FOREIGN KEY (doc_id)
    REFERENCES knowledge_doc (id) ON DELETE CASCADE,
  CONSTRAINT fk_knowledge_chunk_role FOREIGN KEY (role_code)
    REFERENCES job_role (role_code) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS learning_resource (
  id BIGINT NOT NULL AUTO_INCREMENT,
  role_code VARCHAR(50) NOT NULL,
  resource_type VARCHAR(50),
  title VARCHAR(255) NOT NULL,
  content TEXT,
  link VARCHAR(255),
  tags VARCHAR(255),
  created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_resource_role (role_code),
  CONSTRAINT fk_resource_role FOREIGN KEY (role_code)
    REFERENCES job_role (role_code) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS interview_session (
  id BIGINT NOT NULL AUTO_INCREMENT,
  user_key VARCHAR(100) NOT NULL,
  role_code VARCHAR(50) NOT NULL,
  total_questions INT NOT NULL,
  current_question_no INT DEFAULT 0,
  status VARCHAR(30) DEFAULT 'in_progress',
  start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  end_time DATETIME,
  total_score DECIMAL(5,2),
  PRIMARY KEY (id),
  KEY idx_session_user (user_key, id),
  KEY idx_session_role (role_code),
  CONSTRAINT fk_session_role FOREIGN KEY (role_code)
    REFERENCES job_role (role_code) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS interview_round (
  id BIGINT NOT NULL AUTO_INCREMENT,
  session_id BIGINT NOT NULL,
  question_no INT NOT NULL,
  question_id BIGINT NOT NULL,
  question_text TEXT NOT NULL,
  answer_text LONGTEXT,
  followup_question TEXT,
  followup_answer LONGTEXT,
  technical_score DECIMAL(5,2),
  depth_score DECIMAL(5,2),
  logic_score DECIMAL(5,2),
  role_match_score DECIMAL(5,2),
  speech_rate_score DECIMAL(5,2),
  clarity_score DECIMAL(5,2),
  confidence_score DECIMAL(5,2),
  strengths TEXT,
  weaknesses TEXT,
  suggestions TEXT,
  created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_round_session_question (session_id, question_no),
  CONSTRAINT fk_round_session FOREIGN KEY (session_id)
    REFERENCES interview_session (id) ON DELETE CASCADE,
  CONSTRAINT fk_round_question FOREIGN KEY (question_id)
    REFERENCES question_bank (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS interview_followup_turn (
  id BIGINT NOT NULL AUTO_INCREMENT,
  session_id BIGINT NOT NULL,
  question_no INT NOT NULL,
  followup_no INT NOT NULL,
  question_text TEXT NOT NULL,
  answer_text LONGTEXT,
  created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_followup_turn (session_id, question_no, followup_no),
  CONSTRAINT fk_followup_session FOREIGN KEY (session_id)
    REFERENCES interview_session (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS interview_report (
  id BIGINT NOT NULL AUTO_INCREMENT,
  session_id BIGINT NOT NULL,
  summary LONGTEXT,
  report_json LONGTEXT,
  report_docx_url VARCHAR(255),
  created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_report_session (session_id),
  CONSTRAINT fk_report_session FOREIGN KEY (session_id)
    REFERENCES interview_session (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS recommendation_record (
  id BIGINT NOT NULL AUTO_INCREMENT,
  session_id BIGINT NOT NULL,
  resource_id BIGINT NOT NULL,
  reason TEXT,
  priority INT DEFAULT 99,
  created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_recommendation (session_id, resource_id),
  CONSTRAINT fk_recommendation_session FOREIGN KEY (session_id)
    REFERENCES interview_session (id) ON DELETE CASCADE,
  CONSTRAINT fk_recommendation_resource FOREIGN KEY (resource_id)
    REFERENCES learning_resource (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

