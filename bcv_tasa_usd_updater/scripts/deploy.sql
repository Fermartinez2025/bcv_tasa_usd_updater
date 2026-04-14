USE [rep_post_dia];
GO

-- Deploy the database schema and initial data setup

-- Create the tasas_dicom table
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'dbo.tasas_dicom') AND type in (N'U'))
BEGIN
    CREATE TABLE dbo.tasas_dicom (
        fecha DATE PRIMARY KEY,
        valor FLOAT NOT NULL,
        valorVenta FLOAT NULL
    );
END
GO

-- Create the log_sp_errors table
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'dbo.log_sp_errors') AND type in (N'U'))
BEGIN
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
END
GO

-- Additional initial data setup can be added here if necessary
-- Example: INSERT INTO dbo.tasas_dicom (fecha, valor) VALUES ('2025-12-12', 100.5);