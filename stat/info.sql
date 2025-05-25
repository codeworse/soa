DROP TABLE IF EXISTS actions;

CREATE TABLE default.actions (
    post_id INT NOT NULL,
    user_id INT NOT NULL,
    type STRING NOT NULL,
    date DATETIME NOT NULL
)
ENGINE=MergeTree()
PRIORITY KEY date;
