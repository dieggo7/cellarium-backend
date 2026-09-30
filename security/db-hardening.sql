-- Hardening do banco para o deploy do backend Til Marcon.
-- As credenciais abaixo são placeholders e devem ser substituídas por valores do gerenciador de segredos do ambiente.
-- Execute este script como usuário administrativo do MySQL/MariaDB.

CREATE DATABASE IF NOT EXISTS til_marcon_almoxarifado;

CREATE USER IF NOT EXISTS 'tilmaroon_app'@'localhost' IDENTIFIED BY 'CHANGE_ME_STRONG_PASSWORD';
CREATE USER IF NOT EXISTS 'tilmaroon_app'@'%' IDENTIFIED BY 'CHANGE_ME_STRONG_PASSWORD';

-- Revoga privilégios de superusuário e reduz as permissões ao mínimo necessário.
REVOKE ALL PRIVILEGES, GRANT OPTION FROM 'tilmaroon_app'@'localhost';
REVOKE ALL PRIVILEGES, GRANT OPTION FROM 'tilmaroon_app'@'%';

GRANT SELECT, INSERT, UPDATE, DELETE ON til_marcon_almoxarifado.* TO 'tilmaroon_app'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON til_marcon_almoxarifado.* TO 'tilmaroon_app'@'%';
GRANT EXECUTE ON PROCEDURE til_marcon_almoxarifado.sp_registrar_saida_estoque TO 'tilmaroon_app'@'localhost';
GRANT EXECUTE ON PROCEDURE til_marcon_almoxarifado.sp_registrar_saida_estoque TO 'tilmaroon_app'@'%';

-- Restringe alterações estruturais a um usuário de administração separado.
REVOKE CREATE, ALTER, DROP, INDEX, CREATE ROUTINE, ALTER ROUTINE, EVENT, TRIGGER ON *.* FROM 'tilmaroon_app'@'localhost';
REVOKE CREATE, ALTER, DROP, INDEX, CREATE ROUTINE, ALTER ROUTINE, EVENT, TRIGGER ON *.* FROM 'tilmaroon_app'@'%';

-- Garante logs e auditoria para alterações em estoque e autenticação.
CREATE TABLE IF NOT EXISTS til_marcon_almoxarifado.audit_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    evento VARCHAR(128) NOT NULL,
    usuario_id BIGINT NULL,
    detalhe JSON NULL,
    ip_origem VARCHAR(64) NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

DELIMITER $$
CREATE TRIGGER IF NOT EXISTS trg_movimentacoes_estoque_block_update
BEFORE UPDATE ON til_marcon_almoxarifado.movimentacoes_estoque
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000'
    SET MESSAGE_TEXT = 'Atualização de movimentacao_estoque não permitida; use inserção e auditoria controlada.';
END$$

CREATE TRIGGER IF NOT EXISTS trg_movimentacoes_estoque_block_delete
BEFORE DELETE ON til_marcon_almoxarifado.movimentacoes_estoque
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000'
    SET MESSAGE_TEXT = 'Exclusão de movimentacao_estoque não permitida; registre um evento de correção em audit_log.';
END$$
DELIMITER ;

FLUSH PRIVILEGES;
