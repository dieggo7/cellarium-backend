USE til_marcon_almoxarifado;

SET @has_os_encerrada_at = (
    SELECT COUNT(*) FROM information_schema.columns
    WHERE table_schema = DATABASE() AND table_name = 'requisicoes'
      AND column_name = 'os_encerrada_at'
);
SET @ddl = IF(@has_os_encerrada_at > 0, 'SELECT 1',
    'ALTER TABLE requisicoes ADD COLUMN os_encerrada_at DATETIME NULL AFTER data_conclusao');
PREPARE migration_stmt FROM @ddl;
EXECUTE migration_stmt;
DEALLOCATE PREPARE migration_stmt;

SET @has_quantidade_sobrante = (
    SELECT COUNT(*) FROM information_schema.columns
    WHERE table_schema = DATABASE() AND table_name = 'requisicao_itens'
      AND column_name = 'quantidade_sobrante'
);
SET @ddl = IF(@has_quantidade_sobrante > 0, 'SELECT 1',
    'ALTER TABLE requisicao_itens ADD COLUMN quantidade_sobrante DECIMAL(12,3) NULL AFTER quantidade_atendida');
PREPARE migration_stmt FROM @ddl;
EXECUTE migration_stmt;
DEALLOCATE PREPARE migration_stmt;
