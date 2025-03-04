CREATE TABLE IF NOT EXISTS logins_info (
    user_id SERIAL NOT NULL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions_info (
    session_id SERIAL NOT NULL PRIMARY KEY,
    user_id INT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users_info (
    user_id INT NOT NULL PRIMARY KEY,
    first_name VARCHAR(30),
    second_name VARCHAR(30),
    birth_date DATE,
    address VARCHAR(50),
    age INT,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);