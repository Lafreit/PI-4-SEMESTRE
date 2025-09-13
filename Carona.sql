CREATE TABLE `usuarios` (
  `id` INTEGER PRIMARY KEY AUTO_INCREMENT,
  `nome` TEXT NOT NULL,
  `email` TEXT UNIQUE NOT NULL,
  `senha` TEXT NOT NULL,
  `telefone` TEXT,
  `foto_perfil` TEXT,
  `tipo_usuario` TEXT NOT NULL COMMENT 'Valores: motorista, passageiro'
);

CREATE TABLE `veiculos` (
  `id` INTEGER PRIMARY KEY AUTO_INCREMENT,
  `usuario_id` INTEGER NOT NULL,
  `modelo` TEXT,
  `placa` TEXT UNIQUE,
  `cor` TEXT,
  `capacidade` INTEGER
);

CREATE TABLE `caronas` (
  `id` INTEGER PRIMARY KEY AUTO_INCREMENT,
  `motorista_id` INTEGER NOT NULL,
  `origem` TEXT NOT NULL,
  `destino` TEXT NOT NULL,
  `horario_saida` DATETIME NOT NULL,
  `valor_total` REAL,
  `vagas_disponiveis` INTEGER,
  `observacoes` TEXT
);

CREATE TABLE `carona_passageiros` (
  `id` INTEGER PRIMARY KEY AUTO_INCREMENT,
  `carona_id` INTEGER NOT NULL,
  `passageiro_id` INTEGER NOT NULL,
  `status` TEXT DEFAULT 'pendente' COMMENT 'Valores: pendente, confirmado, cancelado'
);

CREATE TABLE `avaliacoes` (
  `id` INTEGER PRIMARY KEY AUTO_INCREMENT,
  `avaliador_id` INTEGER NOT NULL,
  `avaliado_id` INTEGER NOT NULL,
  `nota` INTEGER COMMENT 'Valor entre 1 e 5',
  `comentario` TEXT,
  `data_avaliacao` DATETIME DEFAULT 'current_timestamp'
);

ALTER TABLE `veiculos` ADD FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`);

ALTER TABLE `caronas` ADD FOREIGN KEY (`motorista_id`) REFERENCES `usuarios` (`id`);

ALTER TABLE `carona_passageiros` ADD FOREIGN KEY (`carona_id`) REFERENCES `caronas` (`id`);

ALTER TABLE `carona_passageiros` ADD FOREIGN KEY (`passageiro_id`) REFERENCES `usuarios` (`id`);

ALTER TABLE `avaliacoes` ADD FOREIGN KEY (`avaliador_id`) REFERENCES `usuarios` (`id`);

ALTER TABLE `avaliacoes` ADD FOREIGN KEY (`avaliado_id`) REFERENCES `usuarios` (`id`);
