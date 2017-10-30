CREATE TABLE users (
  user_id INTEGER,
  login_name TINYTEXT,
  PRIMARY KEY (user_id)
);

CREATE TABLE messages (
  message_id INTEGER,
  sender_id INTEGER,
  receiver_id INTEGER,
  file_id INTEGER DEFAULT NULL,
  timestamp TINYTEXT,
  message_body TEXT,
  PRIMARY KEY (message_id),
  CONSTRAINT FK_SENDER FOREIGN KEY (sender_id) REFERENCES users(user_id) ON DELETE CASCADE,
  CONSTRAINT FK_RECEIVER FOREIGN KEY (receiver_id) REFERENCES users(user_id) ON DELETE CASCADE,
  CONSTRAINT FK_FILE FOREIGN KEY (file_id) REFERENCES files(file_id) ON DELETE SET NULL
);

CREATE TABLE "files"
(
    file_id INTEGER PRIMARY KEY,
    file_name TINYTEXT,
    file_size INTEGER,
    encoding_type CHAR(3),
    compression_type CHAR(3)
);