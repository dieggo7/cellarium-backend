USE til_marcon_almoxarifado;

-- =====================================================================
-- 13. DADOS INICIAIS — CATEGORIAS
-- =====================================================================
INSERT INTO categorias (nome, codigo_prefixo, descricao) VALUES
('Matérias-primas, metais e perfis',                     'MP', 'Chapas, barras, perfis e vigas metálicas'),
('Consumíveis de solda e corte térmico',                  'CS', 'Arames, eletrodos, bicos e insumos de soldagem'),
('Abrasivos, corte e usinagem',                           'AB', 'Discos, brocas, fresas e ferramentas de corte'),
('Elementos de fixação',                                  'FX', 'Parafusos, porcas, arruelas e rebites'),
('Químicos, lubrificantes e MRO',                         'QM', 'Óleos, graxas, desengraxantes e produtos químicos'),
('Equipamentos de Proteção Individual',                   'EP', 'EPIs para uso operacional'),
('Utensílios de almoxarifado, manutenção e operação',     'UT', 'Materiais de apoio à manutenção e operação');

-- =====================================================================
-- 14. DADOS INICIAIS — UNIDADES DE MEDIDA
-- =====================================================================
INSERT INTO unidades_medida (nome) VALUES
('Unidade'), ('Chapa'), ('Barra'), ('Pedaço'), ('Rolo'), ('Caixa'),
('Kg'), ('M³'), ('Galão'), ('Frasco'), ('Lata'), ('Tubo'),
('Bombona'), ('Par'), ('Jogo'), ('Pacote'), ('Bisnaga');

-- =====================================================================
-- 15. DADOS DE EXEMPLO — SETORES
-- Preparado para cadastro futuro; NÃO representa necessariamente os
-- setores oficiais da Til Marcon (conforme instruído no prompt).
-- =====================================================================
INSERT INTO setores (nome, codigo) VALUES
('Produção',   'PROD'),
('Manutenção', 'MANUT'),
('Solda',      'SOLDA'),
('Usinagem',   'USIN'),
('Montagem',   'MONT');

-- =====================================================================
-- 16. DADOS DE EXEMPLO — LOCALIZAÇÕES
-- =====================================================================
INSERT INTO localizacoes (codigo, descricao, corredor, estante, prateleira, posicao) VALUES
('A1-E1-P1', 'Corredor A, estante 1, prateleira 1', 'A1', 'E1', 'P1', '01'),
('A1-E2-P1', 'Corredor A, estante 2, prateleira 1', 'A1', 'E2', 'P1', '01'),
('B2-E1-P3', 'Corredor B, estante 1, prateleira 3', 'B2', 'E1', 'P3', '01');

-- =====================================================================
-- 17. DADOS DE EXEMPLO — USUÁRIOS
-- Os valores de senha_hash dos demais usuários são PLACEHOLDERS ilustrativos.
-- Em produção, a aplicação deve gerar hashes reais (bcrypt/argon2).
-- =====================================================================
INSERT INTO usuarios (nome, login, senha_hash, perfil, setor_id) VALUES
('Administrador do Sistema', 'admin',        '$argon2id$v=19$m=65536,t=3,p=4$QJfugOAOIZcVWvbjJzYAiQ$K/EM1fsxsqabW1eZAxXgzJlMJV6kUsYjalCZ7nKSjfI', 'ADMIN',       NULL);
-- =====================================================================
-- 18. DADOS DOS MATERIAIS
-- Código, descrição e prefixo de categoria preservados exatamente como
-- fornecidos no arquivo de origem. Unidade e especificação inferidas
-- tecnicamente (ver observação no topo do script).
-- =====================================================================

-- ---- MP — Matérias-primas, metais e perfis ----
INSERT INTO materiais (codigo, descricao, categoria_id, unidade_medida_id, especificacao, qr_code) VALUES
('MP-001', 'Chapa de Aço Carbono SAE 1020 - 1/8" (3.17mm)',
    (SELECT id FROM categorias WHERE codigo_prefixo='MP'), (SELECT id FROM unidades_medida WHERE nome='Chapa'),
    'Espessura 1/8" (3,17mm) — uso em estruturas e componentes metálicos gerais', UUID()),
('MP-002', 'Chapa de Aço Carbono SAE 1020 - 1/4" (6.35mm)',
    (SELECT id FROM categorias WHERE codigo_prefixo='MP'), (SELECT id FROM unidades_medida WHERE nome='Chapa'),
    'Espessura 1/4" (6,35mm) — uso em estruturas e componentes metálicos gerais', UUID()),
('MP-003', 'Chapa de Aço Inox AISI 304 - Escovada 1.5mm',
    (SELECT id FROM categorias WHERE codigo_prefixo='MP'), (SELECT id FROM unidades_medida WHERE nome='Chapa'),
    'Inox AISI 304, acabamento escovado, espessura 1,5mm', UUID()),
('MP-004', 'Chapa de Alumínio Naval 5052 H32 - 2.0mm',
    (SELECT id FROM categorias WHERE codigo_prefixo='MP'), (SELECT id FROM unidades_medida WHERE nome='Chapa'),
    'Liga 5052 H32, espessura 2,0mm, aplicação naval/estrutural', UUID()),
('MP-005', 'Viga U de Aço Carbono - 3"',
    (SELECT id FROM categorias WHERE codigo_prefixo='MP'), (SELECT id FROM unidades_medida WHERE nome='Barra'),
    'Perfil U 3", aço carbono', UUID()),
('MP-007', 'Perfil Tubular Quadrado Aço Carbono 40x40x2.0mm',
    (SELECT id FROM categorias WHERE codigo_prefixo='MP'), (SELECT id FROM unidades_medida WHERE nome='Barra'),
    'Seção 40x40mm, parede 2,0mm', UUID()),
('MP-012', 'Barra Redonda de Aço SAE 1045 - Diâmetro 1"',
    (SELECT id FROM categorias WHERE codigo_prefixo='MP'), (SELECT id FROM unidades_medida WHERE nome='Barra'),
    'Diâmetro 1", aço SAE 1045', UUID()),
('MP-013', 'Barra Redonda de Aço SAE 4140 - Diâmetro 2"',
    (SELECT id FROM categorias WHERE codigo_prefixo='MP'), (SELECT id FROM unidades_medida WHERE nome='Barra'),
    'Diâmetro 2", aço SAE 4140', UUID());

-- ---- CS — Consumíveis de solda e corte térmico ----
INSERT INTO materiais (codigo, descricao, categoria_id, unidade_medida_id, especificacao, qr_code) VALUES
('CS-001', 'Arame de Solda MIG/MAG Solid ER70S-6 - 1.2mm',
    (SELECT id FROM categorias WHERE codigo_prefixo='CS'), (SELECT id FROM unidades_medida WHERE nome='Rolo'),
    'Bitola 1,2mm, processo MIG/MAG', UUID()),
('CS-004', 'Eletrodo Revestido AWS E6013 - 2.50mm',
    (SELECT id FROM categorias WHERE codigo_prefixo='CS'), (SELECT id FROM unidades_medida WHERE nome='Caixa'),
    'Bitola 2,50mm, uso geral', UUID()),
('CS-005', 'Eletrodo Revestido AWS E7018 - 3.25mm',
    (SELECT id FROM categorias WHERE codigo_prefixo='CS'), (SELECT id FROM unidades_medida WHERE nome='Caixa'),
    'Bitola 3,25mm, alta resistência mecânica', UUID()),
('CS-012', 'Bico de Contato MIG M6 x 28 x 1.2mm',
    (SELECT id FROM categorias WHERE codigo_prefixo='CS'), (SELECT id FROM unidades_medida WHERE nome='Unidade'),
    'Rosca M6, comprimento 28mm, para arame 1,2mm', UUID()),
('CS-017', 'Antirrespingo de Solda em Spray',
    (SELECT id FROM categorias WHERE codigo_prefixo='CS'), (SELECT id FROM unidades_medida WHERE nome='Lata'),
    'Uso em processos de solda MIG/MAG', UUID());

-- ---- AB — Abrasivos, corte e usinagem ----
INSERT INTO materiais (codigo, descricao, categoria_id, unidade_medida_id, especificacao, qr_code) VALUES
('AB-001', 'Disco de Corte para Aço Carbono 4.1/2" x 1.0mm',
    (SELECT id FROM categorias WHERE codigo_prefixo='AB'), (SELECT id FROM unidades_medida WHERE nome='Unidade'),
    'Diâmetro 4.1/2", espessura 1,0mm', UUID()),
('AB-004', 'Disco Flap Grão 40 - Zircônio 4.1/2"',
    (SELECT id FROM categorias WHERE codigo_prefixo='AB'), (SELECT id FROM unidades_medida WHERE nome='Unidade'),
    'Grão 40, zircônio, diâmetro 4.1/2"', UUID()),
('AB-010', 'Broca helicoidal HSS DIN 338 - 3.0mm',
    (SELECT id FROM categorias WHERE codigo_prefixo='AB'), (SELECT id FROM unidades_medida WHERE nome='Unidade'),
    'Diâmetro 3,0mm, aço rápido HSS', UUID()),
('AB-014', 'Inserto de Metal Duro WNMG 080408',
    (SELECT id FROM categorias WHERE codigo_prefixo='AB'), (SELECT id FROM unidades_medida WHERE nome='Unidade'),
    'Geometria WNMG 080408, uso em torneamento', UUID()),
('AB-019', 'Fresa Metal Duro Topo Reto 4 Facas - Ø 10mm',
    (SELECT id FROM categorias WHERE codigo_prefixo='AB'), (SELECT id FROM unidades_medida WHERE nome='Unidade'),
    '4 facas, diâmetro 10mm', UUID());

-- ---- FX — Elementos de fixação ----
INSERT INTO materiais (codigo, descricao, categoria_id, unidade_medida_id, especificacao, qr_code) VALUES
('FX-001', 'Parafuso Sextavado RI Grau 5 - 1/4" x 1" UNC',
    (SELECT id FROM categorias WHERE codigo_prefixo='FX'), (SELECT id FROM unidades_medida WHERE nome='Caixa'),
    'Rosca inteira, grau 5, 1/4" x 1" UNC', UUID()),
('FX-002', 'Parafuso Sextavado RP Classe 8.8 - M10 x 50mm',
    (SELECT id FROM categorias WHERE codigo_prefixo='FX'), (SELECT id FROM unidades_medida WHERE nome='Caixa'),
    'Rosca parcial, classe 8.8, M10 x 50mm', UUID()),
('FX-004', 'Parafuso Allen Cabeça Cilíndrica M6 x 20mm',
    (SELECT id FROM categorias WHERE codigo_prefixo='FX'), (SELECT id FROM unidades_medida WHERE nome='Caixa'),
    'Sextavado interno, M6 x 20mm', UUID()),
('FX-008', 'Porca Sextavada Leve Zincada 1/4" UNC',
    (SELECT id FROM categorias WHERE codigo_prefixo='FX'), (SELECT id FROM unidades_medida WHERE nome='Caixa'),
    'Zincada, rosca 1/4" UNC', UUID()),
('FX-012', 'Arruela Lisa Zincada DIN 125 - M8',
    (SELECT id FROM categorias WHERE codigo_prefixo='FX'), (SELECT id FROM unidades_medida WHERE nome='Caixa'),
    'DIN 125, M8, zincada', UUID()),
('FX-017', 'Rebite de Repuxo Alumínio/Aço 4.0 x 12mm',
    (SELECT id FROM categorias WHERE codigo_prefixo='FX'), (SELECT id FROM unidades_medida WHERE nome='Caixa'),
    'Diâmetro 4,0mm, comprimento 12mm', UUID());

-- ---- QM — Químicos, lubrificantes e MRO ----
INSERT INTO materiais (codigo, descricao, categoria_id, unidade_medida_id, especificacao, qr_code) VALUES
('QM-001', 'Óleo Solúvel Semi-Sintético para Usinagem',
    (SELECT id FROM categorias WHERE codigo_prefixo='QM'), (SELECT id FROM unidades_medida WHERE nome='Galão'),
    'Uso em processos de usinagem', UUID()),
('QM-003', 'Graxa de Lítio NLGI 2',
    (SELECT id FROM categorias WHERE codigo_prefixo='QM'), (SELECT id FROM unidades_medida WHERE nome='Bisnaga'),
    'Consistência NLGI 2, lubrificação geral', UUID()),
('QM-004', 'Óleo Lubrificante Industrial ISO VG 68',
    (SELECT id FROM categorias WHERE codigo_prefixo='QM'), (SELECT id FROM unidades_medida WHERE nome='Galão'),
    'Viscosidade ISO VG 68', UUID()),
('QM-007', 'Desengraxante Industrial Alcalino',
    (SELECT id FROM categorias WHERE codigo_prefixo='QM'), (SELECT id FROM unidades_medida WHERE nome='Bombona'),
    'Limpeza de peças e superfícies metálicas', UUID()),
('QM-013', 'Trava Química de Alta Torque',
    (SELECT id FROM categorias WHERE codigo_prefixo='QM'), (SELECT id FROM unidades_medida WHERE nome='Frasco'),
    'Fixação roscada de alta resistência', UUID()),
('QM-017', 'Desengripante e Lubrificante em Spray',
    (SELECT id FROM categorias WHERE codigo_prefixo='QM'), (SELECT id FROM unidades_medida WHERE nome='Lata'),
    'Uso geral em manutenção', UUID());

-- ---- EP — Equipamentos de Proteção Individual ----
INSERT INTO materiais (codigo, descricao, categoria_id, unidade_medida_id, especificacao, qr_code) VALUES
('EP-001', 'Máscara de Solda Eletrônica de Escurecimento Automático',
    (SELECT id FROM categorias WHERE codigo_prefixo='EP'), (SELECT id FROM unidades_medida WHERE nome='Unidade'),
    'Escurecimento automático, uso em soldagem', UUID()),
('EP-004', 'Avental de Raspa de Couro',
    (SELECT id FROM categorias WHERE codigo_prefixo='EP'), (SELECT id FROM unidades_medida WHERE nome='Unidade'),
    'Proteção térmica para soldagem', UUID()),
('EP-008', 'Luva de Raspa Cano Longo',
    (SELECT id FROM categorias WHERE codigo_prefixo='EP'), (SELECT id FROM unidades_medida WHERE nome='Par'),
    'Proteção térmica e mecânica', UUID()),
('EP-012', 'Óculos de Proteção Incolor',
    (SELECT id FROM categorias WHERE codigo_prefixo='EP'), (SELECT id FROM unidades_medida WHERE nome='Unidade'),
    'Lente incolor, proteção ocular', UUID()),
('EP-016', 'Respirador Semifacial PFF2',
    (SELECT id FROM categorias WHERE codigo_prefixo='EP'), (SELECT id FROM unidades_medida WHERE nome='Unidade'),
    'Filtro PFF2, proteção respiratória', UUID()),
('EP-018', 'Botina de Segurança',
    (SELECT id FROM categorias WHERE codigo_prefixo='EP'), (SELECT id FROM unidades_medida WHERE nome='Par'),
    'Uso industrial, com biqueira de proteção', UUID());

-- ---- UT — Utensílios de almoxarifado, manutenção e operação ----
INSERT INTO materiais (codigo, descricao, categoria_id, unidade_medida_id, especificacao, qr_code) VALUES
('UT-001', 'Estopa Branca para Limpeza Mecânica',
    (SELECT id FROM categorias WHERE codigo_prefixo='UT'), (SELECT id FROM unidades_medida WHERE nome='Kg'),
    'Limpeza geral de máquinas e equipamentos', UUID()),
('UT-005', 'Fita Veda Rosca PTFE',
    (SELECT id FROM categorias WHERE codigo_prefixo='UT'), (SELECT id FROM unidades_medida WHERE nome='Rolo'),
    'Vedação de roscas hidráulicas/pneumáticas', UUID()),
('UT-009', 'Abraçadeira de Nylon',
    (SELECT id FROM categorias WHERE codigo_prefixo='UT'), (SELECT id FROM unidades_medida WHERE nome='Pacote'),
    'Fixação de cabos e mangueiras', UUID()),
('UT-011', 'Engate Rápido Pneumático Macho',
    (SELECT id FROM categorias WHERE codigo_prefixo='UT'), (SELECT id FROM unidades_medida WHERE nome='Unidade'),
    'Conexão pneumática rápida', UUID()),
('UT-018', 'Trena Métrica Manual com Trava - 5 Metros',
    (SELECT id FROM categorias WHERE codigo_prefixo='UT'), (SELECT id FROM unidades_medida WHERE nome='Unidade'),
    'Medição manual, trava automática, 5 metros', UUID());

-- =====================================================================
-- 19. ESTOQUE — um registro por material (níveis ilustrativos de
-- exemplo; devem ser substituídos pela contagem real do almoxarifado)
-- =====================================================================
INSERT INTO estoque (material_id, quantidade_atual, estoque_minimo, estoque_maximo, localizacao_id)
SELECT m.id,
       CASE WHEN m.codigo = 'AB-014' THEN 3      -- exemplo de item com estoque baixo
            WHEN m.codigo = 'CS-012' THEN 0       -- exemplo de item sem estoque
            ELSE 50 END,
       10, 200,
       (SELECT id FROM localizacoes ORDER BY id LIMIT 1)
FROM materiais m;

-- =====================================================================
-- 20. DADOS DE EXEMPLO — REQUISIÇÃO DEMONSTRATIVA
-- (dados fictícios apenas para validar views, procedure e consultas)
-- =====================================================================
INSERT INTO requisicoes (numero, setor_id, usuario_solicitante_id, status) VALUES
('REQ-2026-000001', (SELECT id FROM setores WHERE codigo='SOLDA'),
    (SELECT id FROM usuarios WHERE login='solic.solda'), 'PENDENTE');

INSERT INTO requisicao_itens (requisicao_id, material_id, quantidade_solicitada) VALUES
((SELECT id FROM requisicoes WHERE numero='REQ-2026-000001'),
    (SELECT id FROM materiais WHERE codigo='CS-001'), 5),
((SELECT id FROM requisicoes WHERE numero='REQ-2026-000001'),
    (SELECT id FROM materiais WHERE codigo='EP-008'), 2);

-- =====================================================================
-- 21. MATERIAIS IDENTIFICADOS NAS ETIQUETAS DE RODAS E RODÍZIOS
-- Códigos impressos preservados em codigo e qr_code. Estoque começa em
-- zero até que a quantidade física seja conferida no almoxarifado.
-- Este bloco pode ser executado novamente sem duplicar os cadastros.
-- =====================================================================
INSERT INTO categorias (nome, codigo_prefixo, descricao)
VALUES ('Rodas, rodízios e componentes de movimentação', 'RD', 'Rodas, pneus, rodízios, garfos e guias de equipamentos')
ON DUPLICATE KEY UPDATE ativo = VALUES(ativo);

INSERT INTO materiais (codigo, descricao, categoria_id, unidade_medida_id, especificacao, qr_code)
SELECT item.codigo, item.descricao, categoria.id, unidade.id, item.especificacao, item.codigo
FROM (
    SELECT '6687' AS codigo, 'Roda de borracha 10200 BIN 3/4 (10")' AS descricao, '10200 BIN; 3/4; 10 polegadas' AS especificacao
    UNION ALL SELECT '4226', 'Roda em chapa 16 - 1210R1, roda RM 6', 'Chapa 16; referência 1210R1; roda RM 6'
    UNION ALL SELECT '7078', 'Roda de borracha 200 x 65 x 19 mm (8")', '200 x 65 x 19 mm; 8 polegadas'
    UNION ALL SELECT '9058', 'Roda de poliuretano amarelo Nº 01', 'Poliuretano amarelo; referência Nº 01'
    UNION ALL SELECT '129', 'Rodízio GLE 414 NPN-MM (4" giratório)', 'GLE 414 NPN-MM; 4 polegadas; giratório'
    UNION ALL SELECT '120', 'Rodízio FLE 312 NPP (3" fixa) - MM', 'FLE 312 NPP; 3 polegadas; fixo; MM'
    UNION ALL SELECT '127', 'Rodízio GLE 312 NPP (3" giratório) - MM Marcon', 'GLE 312 NPP; 3 polegadas; giratório; MM Marcon'
    UNION ALL SELECT '173', 'Garfo GMS 350B R - giratório', 'GMS 350B R; garfo giratório'
    UNION ALL SELECT '7988', 'Garfo GGMX 62 para plataforma elevador', 'GGMX 62; plataforma elevador'
    UNION ALL SELECT '17940', 'Guia de ferro fundido Nº 06', 'Ferro fundido; referência Nº 06'
    UNION ALL SELECT '1794', 'Pneu maciço 8 polegadas', 'Pneu maciço; 8 polegadas'
    UNION ALL SELECT '1796', 'Pneu maciço 10 polegadas', 'Pneu maciço; 10 polegadas'
    UNION ALL SELECT '1795', 'Pneu maciço 9 polegadas', 'Pneu maciço; 9 polegadas'
    UNION ALL SELECT '5746', 'Roda de borracha 9200 BIN 3/4 (9")', '9200 BIN; 3/4; 9 polegadas'
) AS item
JOIN categorias AS categoria ON categoria.codigo_prefixo = 'RD'
JOIN unidades_medida AS unidade ON unidade.nome = 'Unidade'
WHERE NOT EXISTS (
    SELECT 1 FROM materiais AS existente
    WHERE existente.codigo = item.codigo OR existente.qr_code = item.codigo
)
ON DUPLICATE KEY UPDATE codigo = VALUES(codigo);

INSERT IGNORE INTO estoque (material_id, quantidade_atual, estoque_minimo, estoque_maximo)
SELECT material.id, 0, 0, NULL
FROM materiais AS material
WHERE material.codigo IN ('6687', '4226', '7078', '9058', '129', '120', '127', '173', '7988', '17940', '1794', '1796', '1795', '5746');

-- =====================================================================
