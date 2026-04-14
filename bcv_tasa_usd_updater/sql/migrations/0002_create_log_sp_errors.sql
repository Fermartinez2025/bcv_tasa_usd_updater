CREATE TABLE dbo.log_sp_errors (
    id INT IDENTITY(1,1) PRIMARY KEY,
    sp_name NVARCHAR(128) NOT NULL,
    error_number INT NULL,
    error_message NVARCHAR(MAX) NULL,
    error_state INT NULL,
    error_severity INT NULL,
    payload NVARCHAR(1000) NULL,
    created_at DATETIME2 DEFAULT SYSUTCDATETIME()
);