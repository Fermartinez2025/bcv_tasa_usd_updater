-- Integration tests for the stored procedure sp_carga_tasa

-- Test case 1: Successful insert for 'manana' period
DECLARE @rc INT;
EXEC @rc = [rep_post_dia].[dbo].[sp_carga_tasa] 'manana', '2025-12-12', 100.5, NULL;
SELECT @rc AS rc; -- Expected: 0

-- Test case 2: Successful update for existing date
EXEC @rc = [rep_post_dia].[dbo].[sp_carga_tasa] 'manana', '2025-12-12', 105.0, NULL;
SELECT @rc AS rc; -- Expected: 0

-- Test case 3: Invalid date format
EXEC @rc = [rep_post_dia].[dbo].[sp_carga_tasa] 'manana', 'invalid-date', 100.5, NULL;
SELECT @rc AS rc; -- Expected: 1 (error for invalid date)

-- Test case 4: Successful insert with venta value
EXEC @rc = [rep_post_dia].[dbo].[sp_carga_tasa] 'otro', '2025-12-13', 100.5, 110.5;
SELECT @rc AS rc; -- Expected: 0

-- Test case 5: Update with venta value
EXEC @rc = [rep_post_dia].[dbo].[sp_carga_tasa] 'otro', '2025-12-13', 105.0, 115.0;
SELECT @rc AS rc; -- Expected: 0

-- Test case 6: Check log entry for error handling
EXEC @rc = [rep_post_dia].[dbo].[sp_carga_tasa] 'manana', '2025-12-12', NULL, NULL;
SELECT @rc AS rc; -- Expected: 1 (error for NULL valor)

-- Validate log entry in dbo.log_sp_errors
SELECT * FROM dbo.log_sp_errors WHERE sp_name = 'sp_carga_tasa' ORDER BY created_at DESC;