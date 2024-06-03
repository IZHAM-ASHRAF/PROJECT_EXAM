CREATE TABLE Admins (
    id INT PRIMARY KEY IDENTITY(1,1),
    username NVARCHAR(50) NOT NULL UNIQUE,
    password NVARCHAR(255) NOT NULL
);

CREATE TABLE Scores (
    id INT PRIMARY KEY IDENTITY(1,1),
    score INT NOT NULL,
    created_at DATETIME DEFAULT GETDATE()
);
