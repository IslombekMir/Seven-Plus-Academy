-- =========================
-- Database
-- =========================
CREATE DATABASE IF NOT EXISTS seven_plus
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE seven_plus;

-- USERS
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    public_id VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(20) UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX idx_users_name ON users(last_name, first_name);

-- USER SETTINGS
CREATE TABLE user_settings (
    user_id INT PRIMARY KEY,
    theme VARCHAR(50),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT
);

-- STUDENTS
CREATE TABLE students (
    user_id INT PRIMARY KEY,
    enrollment_date DATE NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT
);

-- TEACHERS
CREATE TABLE teachers (
    user_id INT PRIMARY KEY,
    default_salary_percentage DECIMAL(5,2),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT
);

-- ADMINS
CREATE TABLE admins (
    user_id INT PRIMARY KEY,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT
);

-- ANNOUNCEMENTS
CREATE TABLE announcements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message TEXT NOT NULL,
    updated_at DATETIME NOT NULL,
    updated_by INT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    visible_to ENUM('staff', 'all') NOT NULL DEFAULT 'staff',
    FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE RESTRICT
);

CREATE INDEX idx_announcements_updated_by ON announcements(updated_by);

-- ACHIEVEMENTS (fixed: added id PK)
CREATE TABLE achievements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    certificate_type VARCHAR(100),
    score DECIMAL(6,2),
    image_url VARCHAR(255),
    other_details TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT
);

CREATE INDEX idx_achievements_user ON achievements(user_id);

-- SUBJECTS
CREATE TABLE subjects (
	id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL
);

-- CLASSES
CREATE TABLE classes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    subject_id INT NOT NULL,
    homework_description TEXT,
    homework_updated_at DATETIME,
    default_payment_amount DECIMAL(10,2),
    week_days VARCHAR(50),
    start_time TIME,
    end_time TIME,
    start_date DATE NOT NULL,
    end_date DATE,
    FOREIGN KEY (subject) REFERENCES subjects(id) ON DELETE RESTRICT
);

CREATE INDEX idx_classes_subject ON classes(subject);

-- CLASS_STUDENT
CREATE TABLE class_student (
    id INT AUTO_INCREMENT PRIMARY KEY,
    class_id INT NOT NULL,
    student_id INT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    UNIQUE (class_id, student_id),
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE RESTRICT,
    FOREIGN KEY (student_id) REFERENCES students(user_id) ON DELETE RESTRICT
);

CREATE INDEX idx_class_student_class ON class_student(class_id);
CREATE INDEX idx_class_student_student ON class_student(student_id);

-- CLASS_TEACHER
CREATE TABLE class_teacher (
    id INT AUTO_INCREMENT PRIMARY KEY,
    class_id INT NOT NULL,
    teacher_id INT NOT NULL,
    UNIQUE (class_id, teacher_id),
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE RESTRICT,
    FOREIGN KEY (teacher_id) REFERENCES teachers(user_id) ON DELETE RESTRICT
);

CREATE INDEX idx_class_teacher_class ON class_teacher(class_id);
CREATE INDEX idx_class_teacher_teacher ON class_teacher(teacher_id);

-- CLASS_STUDENT_PRICING (fixed: make composite PK)
CREATE TABLE class_student_pricing (
    class_student_id INT NOT NULL,
    month DATE NOT NULL,
    agreed_payment_amount DECIMAL(10,2),
    PRIMARY KEY (class_student_id, month),
    FOREIGN KEY (class_student_id) REFERENCES class_student(id) ON DELETE RESTRICT
);

CREATE INDEX idx_class_student_pricing_month ON class_student_pricing(month);

-- CLASS_TEACHER_PRICING (fixed: make composite PK)
CREATE TABLE class_teacher_pricing (
    class_teacher_id INT NOT NULL,
    month DATE NOT NULL,
    agreed_salary_percentage DECIMAL(5,2),
    PRIMARY KEY (class_teacher_id, month),
    FOREIGN KEY (class_teacher_id) REFERENCES class_teacher(id) ON DELETE RESTRICT
);

CREATE INDEX idx_class_teacher_pricing_month ON class_teacher_pricing(month);

-- ATTENDANCES
CREATE TABLE attendances (
    class_student_id INT NOT NULL,
    date DATE NOT NULL,
    attended BOOLEAN NOT NULL,
    PRIMARY KEY (class_student_id, date),
    FOREIGN KEY (class_student_id) REFERENCES class_student(id) ON DELETE RESTRICT
);

CREATE INDEX idx_attendances_date ON attendances(date);

-- EXAM_MARKS (fixed: add id PK, keep UNIQUE)
CREATE TABLE exam_marks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    class_student_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    date DATE NOT NULL,
    max_mark INT NOT NULL,
    real_mark INT NOT NULL,
    UNIQUE (class_student_id, name),
    FOREIGN KEY (class_student_id) REFERENCES class_student(id) ON DELETE RESTRICT
);

CREATE INDEX idx_exam_marks_date ON exam_marks(date);

-- PAYMENTS
CREATE TABLE payments (
    class_student_id INT NOT NULL,
    month DATE NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    updated_at DATETIME NOT NULL,
    updated_by INT NOT NULL,
    PRIMARY KEY (class_student_id, month),
    FOREIGN KEY (class_student_id) REFERENCES class_student(id) ON DELETE RESTRICT,
    FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE RESTRICT
);

CREATE INDEX idx_payments_updated_by ON payments(updated_by);
CREATE INDEX idx_payments_month ON payments(month);

-- ROLES
CREATE TABLE roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT
);

-- PERMISSIONS
CREATE TABLE permissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT
);

-- ROLE_PERMISSIONS
CREATE TABLE role_permissions (
    role_id INT NOT NULL,
    permission_id INT NOT NULL,
    PRIMARY KEY (role_id, permission_id),
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
);

-- USER_ROLES
CREATE TABLE user_roles (
    user_id INT NOT NULL,
    role_id INT NOT NULL,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
);

-- ORGANIZATION
CREATE TABLE organization (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    phone_number VARCHAR(20),
    email VARCHAR(100),
    website VARCHAR(255),
    description TEXT
);

-- BRANCHES
CREATE TABLE branches (
    id INT AUTO_INCREMENT PRIMARY KEY,
    organization_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    address VARCHAR(255),
    phone_number VARCHAR(20),
    FOREIGN KEY (organization_id) REFERENCES organization(id) ON DELETE CASCADE
);
