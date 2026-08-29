-- Placement Week Scheduler — Database Schema
-- Mirai Labs Assignment A
-- MySQL 8+
--
-- This file defines the complete application schema.
-- Seed/sample data is intentionally NOT included here.
-- Baseline snapshot tables are included because the application uses them
-- for Restore Baseline functionality.

CREATE DATABASE IF NOT EXISTS placement_scheduler
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE placement_scheduler;

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS replan_log;
DROP TABLE IF EXISTS disruptions;
DROP TABLE IF EXISTS interviews_baseline;
DROP TABLE IF EXISTS rooms_baseline;
DROP TABLE IF EXISTS panels_baseline;
DROP TABLE IF EXISTS students_baseline;
DROP TABLE IF EXISTS interviews;
DROP TABLE IF EXISTS shortlists;
DROP TABLE IF EXISTS panels;
DROP TABLE IF EXISTS rooms;
DROP TABLE IF EXISTS students;
DROP TABLE IF EXISTS companies;

SET FOREIGN_KEY_CHECKS = 1;

-- 1. Companies
CREATE TABLE companies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    placement_day INT NOT NULL,
    arrival_time TIME NULL,
    cgpa_cutoff DECIMAL(4,2) NOT NULL,
    panels INT NOT NULL,
    interview_duration_min INT NOT NULL,
    priority_tier INT NOT NULL,
    CONSTRAINT chk_companies_day CHECK (placement_day BETWEEN 1 AND 4),
    CONSTRAINT chk_companies_cutoff CHECK (cgpa_cutoff BETWEEN 0 AND 10),
    CONSTRAINT chk_companies_panels CHECK (panels > 0),
    CONSTRAINT chk_companies_duration CHECK (interview_duration_min > 0),
    CONSTRAINT chk_companies_tier CHECK (priority_tier IN (1,2,3))
) ENGINE=InnoDB;

-- 2. Students
CREATE TABLE students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    cgpa DECIMAL(4,2) NOT NULL,
    branch VARCHAR(50) NOT NULL,
    status ENUM('active','withdrawn') NOT NULL DEFAULT 'active',
    CONSTRAINT chk_students_cgpa CHECK (cgpa BETWEEN 0 AND 10)
) ENGINE=InnoDB;

-- 3. Rooms
CREATE TABLE rooms (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    capacity INT NOT NULL DEFAULT 1,
    status ENUM('available','offline') NOT NULL DEFAULT 'available',
    CONSTRAINT chk_rooms_capacity CHECK (capacity > 0)
) ENGINE=InnoDB;

-- 4. Panels
CREATE TABLE panels (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    panel_number INT NOT NULL,
    status ENUM('available','unavailable') NOT NULL DEFAULT 'available',
    CONSTRAINT fk_panels_company
        FOREIGN KEY (company_id) REFERENCES companies(id),
    CONSTRAINT uq_panels_company_number UNIQUE (company_id, panel_number),
    -- Needed for the composite FK from interviews.
    CONSTRAINT uq_panels_id_company UNIQUE (id, company_id),
    CONSTRAINT chk_panels_number CHECK (panel_number > 0)
) ENGINE=InnoDB;

-- 5. Shortlists
CREATE TABLE shortlists (
    student_id INT NOT NULL,
    company_id INT NOT NULL,
    PRIMARY KEY (student_id, company_id),
    CONSTRAINT fk_shortlists_student
        FOREIGN KEY (student_id) REFERENCES students(id),
    CONSTRAINT fk_shortlists_company
        FOREIGN KEY (company_id) REFERENCES companies(id)
) ENGINE=InnoDB;

-- 6. Interviews
CREATE TABLE interviews (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    company_id INT NOT NULL,
    room_id INT NULL,
    panel_id INT NULL,
    start_time DATETIME NULL,
    end_time DATETIME NULL,
    status ENUM('scheduled','unscheduled','cancelled','replanned') NOT NULL DEFAULT 'unscheduled',
    reason VARCHAR(255) NULL,
    CONSTRAINT fk_interviews_student
        FOREIGN KEY (student_id) REFERENCES students(id),
    CONSTRAINT fk_interviews_company
        FOREIGN KEY (company_id) REFERENCES companies(id),
    CONSTRAINT fk_interviews_room
        FOREIGN KEY (room_id) REFERENCES rooms(id),
    CONSTRAINT fk_interviews_panel
        FOREIGN KEY (panel_id) REFERENCES panels(id),
    -- Ensures an assigned panel belongs to the same company as the interview.
    CONSTRAINT fk_interview_panel_company
        FOREIGN KEY (panel_id, company_id) REFERENCES panels(id, company_id),
    CONSTRAINT chk_interviews_time_order CHECK (
        start_time IS NULL OR end_time IS NULL OR end_time > start_time
    )
) ENGINE=InnoDB;

-- 7. Disruptions
CREATE TABLE disruptions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    type ENUM(
        'company_delay',
        'panel_unavailable',
        'student_withdrawal',
        'room_unavailable'
    ) NOT NULL,
    company_id INT NULL,
    panel_id INT NULL,
    student_id INT NULL,
    room_id INT NULL,
    start_time DATETIME NULL,
    end_time DATETIME NULL,
    delay_minutes INT NULL,
    reason VARCHAR(255) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_disruptions_company
        FOREIGN KEY (company_id) REFERENCES companies(id),
    CONSTRAINT fk_disruptions_panel
        FOREIGN KEY (panel_id) REFERENCES panels(id),
    CONSTRAINT fk_disruptions_student
        FOREIGN KEY (student_id) REFERENCES students(id),
    CONSTRAINT fk_disruptions_room
        FOREIGN KEY (room_id) REFERENCES rooms(id),
    CONSTRAINT chk_disruptions_delay CHECK (delay_minutes IS NULL OR delay_minutes >= 0),
    CONSTRAINT chk_disruptions_time_order CHECK (
        start_time IS NULL OR end_time IS NULL OR end_time >= start_time
    )
) ENGINE=InnoDB;

-- 8. Replan log
CREATE TABLE replan_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    interview_id INT NOT NULL,
    old_room_id INT NULL,
    old_panel_id INT NULL,
    old_start_time DATETIME NULL,
    old_end_time DATETIME NULL,
    new_room_id INT NULL,
    new_panel_id INT NULL,
    new_start_time DATETIME NULL,
    new_end_time DATETIME NULL,
    reason VARCHAR(255) NULL,
    logged_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_replan_log_interview
        FOREIGN KEY (interview_id) REFERENCES interviews(id),
    CONSTRAINT fk_replan_log_old_room
        FOREIGN KEY (old_room_id) REFERENCES rooms(id),
    CONSTRAINT fk_replan_log_old_panel
        FOREIGN KEY (old_panel_id) REFERENCES panels(id),
    CONSTRAINT fk_replan_log_new_room
        FOREIGN KEY (new_room_id) REFERENCES rooms(id),
    CONSTRAINT fk_replan_log_new_panel
        FOREIGN KEY (new_panel_id) REFERENCES panels(id)
) ENGINE=InnoDB;

-- 9–12. Baseline snapshot tables used by Restore Baseline.
-- These are deliberately independent snapshots rather than foreign-keyed
-- copies, so they remain restorable even when the live schedule changes.
-- Keep these definitions aligned with backend/replan_metrics.py.
CREATE TABLE interviews_baseline (
    id INT PRIMARY KEY,
    student_id INT NOT NULL,
    company_id INT NOT NULL,
    room_id INT NULL,
    panel_id INT NULL,
    start_time DATETIME NULL,
    end_time DATETIME NULL,
    status VARCHAR(20) NOT NULL,
    reason VARCHAR(255) NULL,
    saved_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE rooms_baseline (
    id INT PRIMARY KEY,
    status VARCHAR(20) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE panels_baseline (
    id INT PRIMARY KEY,
    status VARCHAR(20) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE students_baseline (
    id INT PRIMARY KEY,
    status VARCHAR(20) NOT NULL
) ENGINE=InnoDB;

-- Performance indexes used by conflict checks and dashboard queries.
CREATE INDEX idx_interviews_student_time
    ON interviews (student_id, start_time, end_time);

CREATE INDEX idx_interviews_room_time
    ON interviews (room_id, start_time, end_time);

CREATE INDEX idx_interviews_panel_time
    ON interviews (panel_id, start_time, end_time);

CREATE INDEX idx_shortlists_company
    ON shortlists (company_id);

CREATE INDEX idx_disruptions_type
    ON disruptions (type);

CREATE INDEX idx_replan_log_interview
    ON replan_log (interview_id);

CREATE INDEX idx_replan_log_logged_at
    ON replan_log (logged_at);

-- Optional baseline population:
-- Run only after the schedule/resources/students have been seeded and the
-- generated baseline is the state you want Restore Baseline to return to.
--
-- INSERT INTO interviews_baseline SELECT * FROM interviews;
-- INSERT INTO rooms_baseline SELECT * FROM rooms;
-- INSERT INTO panels_baseline SELECT * FROM panels;
-- INSERT INTO students_baseline SELECT * FROM students;
