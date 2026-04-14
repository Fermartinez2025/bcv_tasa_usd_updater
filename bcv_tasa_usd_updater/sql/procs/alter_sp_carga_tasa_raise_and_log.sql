-- filepath: c:\Users\fmartinez\Documents\bcv_tasa_usd_updater\sql\procs\alter_sp_carga_tasa_raise_and_log.sql
USE [rep_post_dia];
GO

SET ANSI_NULLS ON;
GO
SET QUOTED_IDENTIFIER ON;
GO

/*
  ALTER PROCEDURE: sp_carga_tasa (with RAISERROR + logging)

  - Crea una tabla de logs (si no existe) llamada dbo.log_sp_errors.
  - Ejecuta la lógica original (upsert sobre dbo.tasas_dicom).
  - En caso de excepción, inserta un registro en dbo.log_sp_errors con detalles.
  - Emite RAISERROR con severidad 16 para que los callers reciban excepción (pyodbc/otros).
  - Devuelve RETURN 0 en caso de éxito; en caso de error devuelve ERROR_NUMBER() (o 50000 si no disponible).

  Nota: Al usar RAISERROR el cliente normalmente recibirá excepción; en tu código Python la ejecución será atrapada y tratada
  (reintentos/rollback) — esto es coherente con la opción que solicitaste: notificar error y registrar en BD.
*/

-- Crear tabla de logs si no existe (idempotente)
IF OBJECT_ID('dbo.log_sp_errors', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.log_sp_errors (
        id INT IDENTITY(1,1) PRIMARY KEY,
        sp_name NVARCHAR(128) NOT NULL,
        error_number INT NULL,
        error_message NVARCHAR(MAX) NULL,
        error_state INT NULL,
        error_severity INT NULL,
        payload NVARCHAR(1000) NULL, -- opcional: parámetros o contexto
        created_at DATETIME2 DEFAULT SYSUTCDATETIME()
    );
END
GO

ALTER PROCEDURE [dbo].[sp_carga_tasa]
    @periodo       NVARCHAR(10),    -- 'manana' u otros
    @fechaProceso  NVARCHAR(10),    -- formato: 'YYYY-MM-DD' recomendado
    @valor         FLOAT,           -- tasa compra / referencia
    @valorVenta    FLOAT            -- tasa venta (si aplica)
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @return_code INT = 0;

    BEGIN TRY

        DECLARE @fecha DATE = TRY_CONVERT(DATE, @fechaProceso, 23); -- 23: ISO (YYYY-MM-DD)
        IF @fecha IS NULL
        BEGIN
            -- Fecha inválida: devolver código de error (1) y lanzar error
            SET @return_code = 1;
            RAISERROR('Fecha inválida. Use formato YYYY-MM-DD', 16, 1);
            RETURN @return_code;
        END

        -- Lógica original: upsert según periodo
        IF @periodo = N'manana'
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM [dbo].[tasas_dicom] WHERE [fecha] = @fecha)
            BEGIN
                INSERT INTO [dbo].[tasas_dicom] ([fecha], [valor])
                VALUES (@fecha, @valor);
            END
            ELSE
            BEGIN
                UPDATE [dbo].[tasas_dicom]
                   SET [valor] = @valor
                 WHERE [fecha] = @fecha;
            END
        END
        ELSE
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM [dbo].[tasas_dicom] WHERE [fecha] = @fecha)
            BEGIN
                INSERT INTO [dbo].[tasas_dicom] ([fecha], [valor], [valorVenta])
                VALUES (@fecha, @valor, @valorVenta);
            END
            ELSE
            BEGIN
                UPDATE [dbo].[tasas_dicom]
                   SET [valor]      = @valor,
                       [valorVenta] = @valorVenta
                 WHERE [fecha] = @fecha;
            END
        END

        -- Si llegamos aquí, éxito
        SET @return_code = 0;
        RETURN @return_code;

    END TRY
    BEGIN CATCH
        -- Capturar detalles del error
        DECLARE @err_num INT = ERROR_NUMBER();
        DECLARE @err_msg NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @err_state INT = ERROR_STATE();
        DECLARE @err_severity INT = ERROR_SEVERITY();

        -- Insertar en la tabla de logs con el payload mínimo (parámetros)
        BEGIN TRY
            INSERT INTO dbo.log_sp_errors (sp_name, error_number, error_message, error_state, error_severity, payload)
            VALUES ('sp_carga_tasa', @err_num, LEFT(@err_msg, 4000), @err_state, @err_severity,
                    'periodo=' + ISNULL(@periodo,'') + '; fecha=' + ISNULL(@fechaProceso,'') + '; valor=' + COALESCE(CONVERT(NVARCHAR(50), @valor), 'NULL') + '; valorVenta=' + COALESCE(CONVERT(NVARCHAR(50), @valorVenta), 'NULL'));
        END TRY
        BEGIN CATCH
            -- Si el INSERT de logging falla, no queremos ocultar el error original: continuamos
        END CATCH

        -- Devolver un código distinto de 0; mapear al número de error de SQL
        SET @return_code = CASE WHEN @err_num IS NULL THEN 50000 ELSE @err_num END;

        -- Lanzar error para que el caller (pyodbc, etc.) reciba excepción y pueda actuar (reintentos/alertas)
        RAISERROR('sp_carga_tasa fallo: %s', 16, 1, @err_msg);

        RETURN @return_code;
    END CATCH
END
GO

/*
  Instrucciones para aplicar:
  1) Abrir SQL Server Management Studio (SSMS) o tu herramienta favorita.
  2) Conectarte al servidor y seleccionar la base de datos `rep_post_dia`.
  3) Ejecutar este script.

  Validación:
  - Ejecuta desde un cliente:
      DECLARE @rc INT;
      EXEC @rc = [rep_post_dia].[dbo].[sp_carga_tasa] 'manana', '2025-12-12', 100.5, NULL;
      SELECT @rc AS rc;
    Si todo va bien, deberías obtener rc = 0; en caso de error, el caller recibirá una excepción (por RAISERROR) y además se generará
    un registro en dbo.log_sp_errors con detalles del error.

  Notas:
  - RAISERROR con severidad 16 hace que el caller reciba una excepción; si deseas un comportamiento distinto (por ejemplo, solo logging sin excepción),
    modifica o elimina la línea RAISERROR en el CATCH.
  - Si prefieres mapear códigos de error personalizados (1 = fecha inválida, 2 = duplicado, etc.) puedo ajustar el CASE de return_code y los RAISERROR
    con mensajes más estructurados.
*/