# Projeto Carona

## Objetivos do Projeto
O projeto **Carona Solidária** tem como objetivo intermediar, por meio de um aplicativo web pago, o compartilhamento de assentos em veículos entre pessoas físicas. A proposta é conectar proprietários de veículos que desejam compartilhar os custos de seus deslocamentos diários com usuários que realizam trajetos semelhantes e estão dispostos a pagar uma quota proporcional à distância percorrida, cobrindo os custos de uso e manutenção do veículo.

O aplicativo visa obter lucro por meio de uma **taxa fixa** cobrada tanto do dono do veículo quanto dos usuários que dividem as despesas da carona.

## Clientes e Usuários
- Proprietários de veículos com rotinas de deslocamento diário.
- Pessoas com trajetos semelhantes ou coincidentes, como colegas de trabalho, escola, faculdade.
- Usuários eventuais que precisam se deslocar para destinos compatíveis com os motoristas cadastrados.

## Funcionalidades Desejadas
- Cadastro de motoristas  
- Cadastro de veículos  
- Cadastro de usuários colaboradores  
- Identificação de itinerários  
- Exibição de vagas disponíveis por itinerário  
- Confirmação da parceria entre motorista e carona  
- Disponibilização da locação do veículo durante o trajeto  
- Seleção e processamento de formas de pagamento  
- Contabilidade e repasse de valores ao motorista após as viagens  

## Tecnologias Utilizadas
- Front-end: Django  
- Back-end: Python + Django  
- Banco de dados: SQLite  
- Controle de versão: Git + GitHub

## Integrantes
- [Rayanne Nunes](https://github.com/rayannenunes)  
- [Sara Beatriz](https://github.com/SaraBeatris)  
- [Luiz Freitas](https://github.com/Lafreit)
---

## Produto Backlog

### Épico 1: Gestão de Usuários e Veículos
Este épico abrange tudo o que um usuário precisa para começar a usar a plataforma, desde a criação da conta até a gestão de suas informações e veículos.

#### Funcionalidade 1.1: Cadastro e Autenticação de Usuário
**Histórias de Usuário:**
- Como um novo usuário, quero me cadastrar na plataforma para que eu possa utilizar os serviços de carona.
- Como um usuário, quero ter um login seguro para que minhas informações estejam protegidas.

**Tarefas:**
- Desenvolver tela de cadastro com validação de dados.
- Implementar autenticação por e-mail e senha.
- Implementar criptografia para senhas.
- Desenvolver fluxo de "esqueci a senha".

#### Funcionalidade 1.2: Gerenciamento de Perfil do Usuário
**Histórias de Usuário:**
- Como um usuário colaborador, quero cadastrar meus dados pessoais (nome, contato) para que eu possa buscar e participar de caronas.
- Como um usuário colaborador, quero editar as informações do meu perfil para que eu possa mantê-las atualizadas.

**Tarefas:**
- Criar tela de perfil para preenchimento de dados pessoais.
- Implementar funcionalidade de edição do perfil (nome, foto, contato).
- Adicionar validação para dados de contato.

#### Funcionalidade 1.3: Gerenciamento de Veículos do Motorista
**Histórias de Usuário:**
- Como um motorista, quero cadastrar meu veículo (modelo, placa, capacidade) para que eu possa oferecer caronas.
- Como um motorista, quero editar as informações do meu perfil para que eu possa mantê-las atualizadas.

**Tarefas:**
- Criar formulário para cadastro de veículos (modelo, ano, placa, capacidade).
- Implementar funcionalidade de edição e remoção de veículos.
- Validar dados do veículo (formato da placa, capacidade).

---

### Épico 2: Criação e Gerenciamento de Rotas
Este épico foca na funcionalidade central da plataforma para motoristas (oferecer rotas) e para colaboradores (buscar por rotas).

#### Funcionalidade 2.1: Criação e Edição de Itinerários
**Histórias de Usuário:**
- Como um motorista, quero definir meu itinerário diário (origem, destino, horários) para que eu possa oferecer caronas.
- Como um motorista, quero editar meu itinerário para que eu possa ajustá-lo a mudanças na minha rotina.

**Tarefas:**
- Desenvolver interface para cadastro de itinerários (origem, destino, horários).
- Integrar API de mapas para seleção de origem/destino.
- Criar funcionalidade de edição, ativação e desativação de itinerários.

#### Funcionalidade 2.2: Busca e Salvamento de Itinerários
**Histórias de Usuário:**
- Como um usuário colaborador, quero buscar por itinerários que coincidam com meus deslocamentos diários para que eu possa encontrar caronas disponíveis.
- Como um usuário colaborador, quero salvar meus itinerários frequentes para que eu possa acessá-los rapidamente.

**Tarefas:**
- Desenvolver tela de busca por itinerários (origem, destino, data, horário).
- Implementar algoritmo de busca que filtre resultados compatíveis.
- Criar funcionalidade para salvar buscas frequentes do usuário.

---

### Épico 3: Reserva e Gestão de Vagas
Este épico cobre todo o fluxo de solicitação, aceitação, confirmação e cancelamento de caronas.

#### Funcionalidade 3.1: Visualização e Solicitação de Vagas
**Histórias de Usuário:**
- Como um usuário colaborador, quero visualizar as vagas disponíveis em veículos que se adequam ao meu itinerário para que eu possa escolher uma carona.
- Como um usuário colaborador, quero ver os detalhes da carona (motorista, veículo, horário, ponto de encontro) para que eu possa tomar uma decisão informada.
- Como um usuário colaborador, quero solicitar uma vaga em uma carona para que eu possa me juntar a ela.

**Tarefas:**
- Criar tela de resultados da busca com informações essenciais (motorista, veículo, horário, vagas).
- Criar página de detalhes da carona com informações completas e foto do motorista/veículo.
- Implementar botão de "Solicitar Vaga".

#### Funcionalidade 3.2: Gestão de Solicitações do Motorista
**Histórias de Usuário:**
- Como um motorista, quero visualizar as solicitações de carona para o meu itinerário para que eu possa aceitar ou recusar.
- Como um motorista, quero aceitar uma solicitação de carona para que o passageiro seja confirmado na minha carona.
- Como um motorista, quero recusar uma solicitação de carona para que o passageiro saiba que não há mais vagas.

**Tarefas:**
- Desenvolver painel para o motorista visualizar as solicitações recebidas.
- Implementar botões de "Aceitar" e "Recusar" para cada solicitação.
- Criar notificações para o usuário colaborador sobre a decisão do motorista.

#### Funcionalidade 3.3: Confirmação e Cancelamento
**Histórias de Usuário:**
- Como um usuário colaborador, quero receber a confirmação da minha vaga para que eu saiba que a carona está garantida.
- Como um usuário colaborador, quero cancelar minha participação em uma carona antes do trajeto para que o motorista possa realocar a vaga.
- Como um motorista, quero visualizar os passageiros confirmados para a minha carona para que eu saiba quem esperar.

**Tarefas:**
- Desenvolver sistema de notificações (e-mail ou push) para confirmação de vagas.
- Implementar funcionalidade de cancelamento para o usuário colaborador.
- Criar interface para o motorista visualizar a lista de passageiros confirmados.

---

### Épico 4: Pagamentos e Monetização
Este épico trata do fluxo financeiro do aplicativo, garantindo que os pagamentos sejam processados de forma segura e que o motorista receba sua parte.

#### Funcionalidade 4.1: Fluxo de Pagamento do Usuário
**Histórias de Usuário:**
- Como um usuário colaborador, quero visualizar o custo da carona (quota a pagar) para que eu saiba quanto devo.
- Como um usuário colaborador, quero selecionar uma forma de pagamento (cartão de crédito, débito, etc.) para que eu possa pagar pela carona.
- Como o sistema, quero processar o pagamento do usuário colaborador para que a transação seja concluída.

**Tarefas:**
- Desenvolver tela de checkout com valor da carona.
- Integrar com um gateway de pagamento (ex: Stripe, PagSeguro).
- Implementar seleção de métodos de pagamento (cartão, etc.).

#### Funcionalidade 4.2: Gestão de Ganhos do Motorista e Taxas do App
**Histórias de Usuário:**
- Como o sistema, quero calcular a taxa fixa cobrada do motorista e do usuário colaborador para que a monetização do app ocorra.
- Como o sistema, quero realizar a contabilidade e o repasse dos valores devidos ao motorista ao final das viagens para que ele receba seu dinheiro.
- Como um motorista, quero visualizar meu extrato de ganhos para que eu acompanhe os valores a serem recebidos.

**Tarefas:**
- Implementar a lógica de cálculo das taxas.
- Desenvolver o sistema de repasse de valores para os motoristas.
- Criar um painel de "Extrato Financeiro" para o motorista, mostrando ganhos e repasses.