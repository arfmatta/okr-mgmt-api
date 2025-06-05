# Documentação da API de Gerenciamento de OKRs no GitLab

## 1. Visão Geral e Requisitos Funcionais

Esta API FastAPI facilita a criação e o gerenciamento de Objetivos e Key Results (KRs) como issues no GitLab, seguindo templates pré-definidos. O objetivo é fornecer uma interface programática para interações mais amigáveis com o sistema de OKRs, que futuramente será consumida por um frontend Angular.

**Requisitos Chave:**

*   **Criação de Objetivos (Issues):**
    *   Título formatado: "OBJ{número}: {TÍTULO DO OBJETIVO EM MAIÚSCULAS}".
    *   Descrição formatada em Markdown com seções "### Descrição:" e "### Resultados Chave".
    *   Criação em um projeto GitLab parametrizado.
    *   Aplicação de labels de Objetivo parametrizadas.
*   **Criação de Key Results (Issues):**
    *   Título formatado: "{Prefixo do Objetivo Pai} - KR{número}: {Título do KR}".
    *   Descrição formatada em Markdown com seções para descrição do KR, metas (prevista/realizada), responsáveis e uma tabela para "Projetos/Ações/Atividades".
    *   Criação no mesmo projeto GitLab do Objetivo.
    *   Vinculação do KR ao Objetivo pai.
    *   Aplicação de labels de KR parametrizadas.
    *   Adição de uma referência ao KR na descrição do Objetivo pai.
*   **Criação de Lista de Atividades para um KR:**
    *   Serviço para adicionar atividades à tabela Markdown na descrição de um issue de KR existente.

**Parâmetros de Conexão ao GitLab (Configuráveis):**
*   URL da API do GitLab.
*   Token de Acesso Privado.
*   ID do Projeto GitLab alvo.
*   Nomes das Labels para Objetivos (lista).
*   Nomes das Labels para KRs (lista).
*   Nome da Label para referência de KR na descrição do Objetivo (e.g., "OKR::Resultado Chave").

## 2. Diagrama de Componentes (Simplificado)

```
+-----------------+      +-----------------+      +----------------------+
| Frontend        |----->| API OKR (FastAPI)|----->| GitLab API           |
| (Angular - Futuro)|      | (Backend)       |      | (Issues, Labels, etc)|
+-----------------+      +-----------------+      +----------------------+
```

*   **Frontend (Angular - Futuro):** Interface do usuário para interagir com o sistema de OKRs.
*   **API OKR (FastAPI):** Este backend, que lida com a lógica de negócios, formatação e comunicação com o GitLab.
*   **GitLab API:** A API do GitLab usada para criar e gerenciar issues e seus metadados.

## 3. Visão Geral dos Endpoints da API

A API expõe os seguintes endpoints principais. Para detalhes completos sobre os schemas de request/response, consulte a documentação OpenAPI gerada automaticamente pela FastAPI em `/docs` ou `/redoc` na raiz da aplicação.

### 3.0. Autenticação (`/auth`)

*   **`POST /auth/token`**
    *   **Descrição:** Obtém um token JWT para autenticação. Enviar `username` e `password` como form data (`application/x-www-form-urlencoded`). Para fins de teste, usar `username: testuser` e `password: testpass`.
    *   **Request Body (Form Data):** `username` (string), `password` (string).
    *   **Response Body:** `Token` (contém `access_token`: string, `token_type`: string).

### 3.1. Objetivos (`/objectives`)

*   **`POST /objectives/`**
    *   **Descrição:** Cria um novo Objetivo. **Requer autenticação JWT.**
    *   **Request Body:** `ObjectiveCreateRequest` (contém `obj_number`, `title`, `description`).
    *   **Response Body:** `ObjectiveResponse` (contém dados do issue criado, incluindo `id`, `title` formatado, `description` formatada, `web_url`).
*   **`GET /objectives/`**
    *   **Descrição:** Lista todos os Objetivos (issues com as labels de objetivo configuradas).
    *   **Response Body:** `List[ObjectiveResponse]`.
*   **`GET /objectives/{objective_iid}`**
    *   **Descrição:** Busca um Objetivo específico pelo seu IID (Internal ID do issue no GitLab).
    *   **Response Body:** `ObjectiveResponse`.

### 3.2. Key Results (`/krs`)

*   **`POST /krs/`**
    *   **Descrição:** Cria um novo Key Result. Requer o `objective_iid` do objetivo pai.
        *Observação: A funcionalidade completa para criação de KRs, incluindo formatação detalhada e atualização da descrição do objetivo pai, foi implementada no `KRService` (conforme Subtask 13). No entanto, a verificação completa através de testes de execução tem sido dificultada por limitações no ambiente de desenvolvimento (timeouts), então a confiança na plena operacionalidade em todos os cenários depende de testes futuros em um ambiente de execução estável.*
    *   **Request Body:** `KRCreateRequest` (contém `objective_iid`, `kr_number`, `title`, `description`, `meta_prevista`, `meta_realizada`, `responsaveis`).
    *   **Response Body:** `KRResponse`.
*   **`GET /krs/{kr_iid}`**
    *   **Descrição:** Busca um Key Result específico pelo seu IID.
    *   **Response Body:** `KRResponse`.
*   **`GET /krs/objective/{objective_iid}`**
    *   **Descrição:** Lista todos os Key Results associados a um Objetivo específico.
    *   **Response Body:** `List[KRResponse]`.
*   **`GET /krs/`**
    *   **Descrição:** Lista todos os Key Results (issues com as labels de KR configuradas).
    *   **Response Body:** `List[KRResponse]`.
*   **`PUT /krs/{kr_iid}`**
    *   **Descrição:** Atualiza um Key Result existente. Permite alterar a descrição textual, meta prevista, meta realizada e a lista de responsáveis. Campos não fornecidos na requisição não serão alterados (manterão seus valores atuais), exceto a descrição que se tornará "(Descrição não fornecida)" se uma string vazia for passada.
    *   **Request Body:** `KRUpdateRequest` (contém `description: Optional[str]`, `meta_prevista: Optional[float]`, `meta_realizada: Optional[float]`, `responsaveis: Optional[List[str]]`).
    *   **Response Body:** `KRResponse`.

### 3.3. Atividades (`/activities`)

*   **`POST /activities/kr/{kr_iid}`**
    *   **Descrição:** Adiciona uma ou mais atividades à descrição de um Key Result existente. As atividades são adicionadas como novas linhas em uma tabela Markdown na descrição do KR.
    *   **Request Body:** `ActivityCreateRequest` (contém uma lista de objetos `Activity`).
    *   **Response Body:** `DescriptionResponse` (contém a string completa da descrição do KR atualizada).
    *   *(Observação: O endpoint para buscar/listar atividades parseadas da descrição foi desativado temporariamente devido à complexidade de parsear tabelas Markdown de forma robusta no backend.)*

## 4. Modelos de Dados Principais (Pydantic)

Referência aos modelos definidos em `app/models.py`.

*   `ObjectiveCreateRequest`: Para criar Objetivos.
*   `ObjectiveResponse`: Representação de um Objetivo.
*   `KRCreateRequest`: Para criar Key Results.
*   `KRResponse`: Representação de um Key Result.
*   `Activity`: Representação de uma Atividade.
*   `ActivityCreateRequest`: Para adicionar uma lista de Atividades a um KR.
*   `DescriptionResponse`: Resposta simples contendo uma string de descrição.
*   `KRUpdateRequest`: Para atualizar campos de um Key Result (descrição, metas, responsáveis).
*   `Token`: Representação do token de acesso JWT.
*   `TokenData`: Representação dos dados (claims) contidos em um token JWT.
*   `User`: Representação de um usuário autenticado (e.g., `username` extraído do token).

Para a estrutura detalhada de cada modelo, consulte a documentação OpenAPI (`/docs`).

## 5. Configuração

As seguintes variáveis de ambiente (ou arquivo `.env`) são usadas para configurar a aplicação:

*   `GITLAB_API_URL`: URL da instância do GitLab (e.g., `https://gitlab.com`).
*   `GITLAB_ACCESS_TOKEN`: Token de acesso pessoal com escopo de API.
*   `GITLAB_PROJECT_ID`: ID do projeto no GitLab onde os issues serão criados.
*   `GITLAB_OBJECTIVE_LABELS`: Nomes das labels para Objetivos (e.g., "Objetivo Estratégico,OKR").
*   `GITLAB_KR_LABELS`: Nomes das labels para Key Results (e.g., "Resultado Chave,OKR").
*   *(Implicitamente, a label "OKR::Resultado Chave" é usada ao referenciar KRs na descrição do Objetivo).*
*   `SECRET_KEY`: Chave secreta para assinar os tokens JWT.
*   `ALGORITHM`: Algoritmo usado para assinar os tokens JWT (e.g., "HS256").
*   `ACCESS_TOKEN_EXPIRE_MINUTES`: Tempo de validade do token de acesso em minutos.

EOF
