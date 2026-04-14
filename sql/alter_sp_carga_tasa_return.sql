USE [rep_post_dia];
GO

SET ANSI_NULLS ON;
GO
SET QUOTED_IDENTIFIER ON;
GO

/*
  ALTER PROCEDURE template: sp_carga_tasa
  - Devuelve RETURN 0 en caso de éxito.
  - En caso de error, captura ERROR_NUMBER() en el CATCH y lo retorna.
  - Es retrocompatible: si el SP se actualiza con RETURN 0/!=0, el cliente puede usar ese código.

  Nota: este script adapta tu SP original y envía un código de retorno. No realiza RAISERROR en el CATCH
  para permitir que el caller (por ejemplo, pyodbc) reciba el RETURN value mediante la técnica DECLARE @rc; EXEC @rc = ...; SELECT @rc.
*/

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
            -- Fecha inválida: devolver código de error (1)
            SET @return_code = 1;
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

        -- Opcional: registrar en tabla de logs si existe
        -- INSERT INTO dbo.log_sp_errors(sp_name, error_number, error_message, created_at) VALUES('sp_carga_tasa', @err_num, @err_msg, GETDATE());

        -- Devolver un código distinto de 0; puedes mapear a códigos específicos si lo deseas
        SET @return_code = CASE WHEN @err_num IS NULL THEN 50000 ELSE @err_num END;

        -- NOTA: No hacemos RAISERROR/THROW para permitir que el caller reciba el RETURN value.
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
    Debes obtener rc = 0 en camino feliz.

  Comentarios:
  - Si quieres que el SP siga lanzando errores (RAISERROR/THROW) además de devolver un código, podemos agregar RAISERROR en el CATCH, pero algunos callers recibirán excepción en lugar del RETURN value.
  - Puedes mapear códigos internos (por ejemplo, 1 = fecha inválida, 2 = violación de integridad, etc.)
*/
