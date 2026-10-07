USE til_marcon_almoxarifado;

INSERT INTO usuarios (nome, login, senha_hash, perfil, setor_id) VALUES
('Admin Teste', 'admin.teste',
 '$2b$12$.ewv0sg6x7Ex.Rst7s.bu.11P92hovu1GkP.Kv92I2JHas3ve.xh2',
 'ADMIN', NULL),
('Solicitante Teste', 'solicitante.teste',
 '$2b$12$.ewv0sg6x7Ex.Rst7s.bu.11P92hovu1GkP.Kv92I2JHas3ve.xh2',
 'SOLICITANTE', (SELECT id FROM setores WHERE codigo = 'PROD'));

-- Conferir
SELECT id, nome, login, perfil, setor_id, ativo
FROM usuarios
WHERE login IN ('admin.teste', 'solicitante.teste');