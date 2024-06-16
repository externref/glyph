CREATE TABLE IF NOT EXISTS pastes (
    paste_id VARCHAR(6) PRIMARY KEY,
    paste_data VARCHAR,
    paste_language VARCHAR,
    created_by VARCHAR(20), 
    created_on TIMESTAMP,
    delete_password VARCHAR(10)
);

CREATE TABLE IF NOT EXISTS cdn (
    image_id VARCHAR(6) PRIMARY KEY,
    image_data BLOB,
    created_by VARCHAR(20),
    created_on TIMESTAMP,
    delete_password VARCHAR(10)
);