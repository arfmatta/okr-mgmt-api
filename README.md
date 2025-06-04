# GitLab OKR Management API

Este projeto implementa uma API FastAPI para gerenciar Objetivos e Key Results (KRs) como issues no GitLab, seguindo templates pré-definidos.

## 1. Visão Geral

A API permite a criação programática de Objetivos e KRs, a vinculação entre eles, e a adição de atividades a KRs. Ela é projetada para ser consumida por uma interface de usuário (frontend) ou outros sistemas que necessitem interagir com a gestão de OKRs no GitLab de forma estruturada.

Principais Funcionalidades:
- Criação de Objetivos com formatação de título e descrição específicas.
- Criação de Key Results com formatação, vinculação a Objetivos e atualização da descrição do Objetivo pai.
- Adição de Atividades (como linhas de tabela Markdown) à descrição de Key Results.

## 2. Pré-requisitos

- Python 3.8+
- pip (gerenciador de pacotes Python)
- Acesso a uma instância GitLab e um token de acesso com permissões de API.

## 3. Setup do Ambiente

1.  **Clone o repositório:**
    ```bash
    git clone <URL_DO_REPOSITORIO>
    cd <NOME_DO_DIRETORIO>
    ```

2.  **Crie e ative um ambiente virtual:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # No Windows: venv\Scripts\activate
    ```

3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

## 4. Configuração

A aplicação requer variáveis de ambiente para se conectar e interagir com o GitLab. Crie um arquivo `.env` na raiz do projeto com o seguinte conteúdo, substituindo pelos seus valores:

```env
# Exemplo de arquivo .env
GITLAB_API_URL="https://gitlab.com"
GITLAB_ACCESS_TOKEN="SEU_TOKEN_DE_ACESSO_PESSOAL_AQUI"
GITLAB_PROJECT_ID="ID_DO_SEU_PROJETO_GITLAB_ALVO"
GITLAB_OBJECTIVE_LABELS="Objetivo,Meta Principal"
# (Nomes das labels, separados por vírgula se múltiplos, para identificar Objetivos)
GITLAB_KR_LABELS="Resultado Chave,KR"
# (Nomes das labels, separados por vírgula se múltiplos, para identificar KRs)

# PYTHONPATH=. # Descomente se necessário para a descoberta de módulos em alguns ambientes
```

**Variáveis de Ambiente Detalhadas:**
- `GITLAB_API_URL`: A URL base da sua instância GitLab (e.g., `https://gitlab.com`).
- `GITLAB_ACCESS_TOKEN`: Seu token de acesso pessoal do GitLab com escopo `api`.
- `GITLAB_PROJECT_ID`: O ID numérico do projeto no GitLab onde os issues de OKR serão criados.
- `GITLAB_OBJECTIVE_LABELS`: Uma lista de nomes de labels (separados por vírgula, sem espaços ao redor da vírgula) que serão aplicadas aos issues de Objetivo. Ex: `LabelObj1,LabelObj2`
- `GITLAB_KR_LABELS`: Uma lista de nomes de labels (separados por vírgula) que serão aplicadas aos issues de KR. Ex: `LabelKR1,LabelKR2`

*(Nota: A label "OKR::Resultado Chave" é usada internamente pelo serviço ao adicionar referências de KR na descrição do Objetivo pai. Certifique-se que esta label exista no seu projeto GitLab se desejar usar essa funcionalidade visualmente no GitLab).*

## 5. Executando a Aplicação

Com o ambiente virtual ativado e o arquivo `.env` configurado:

```bash
uvicorn app.main:app --reload
```

A API estará disponível em `http://localhost:8000`.

Você pode acessar a documentação interativa (Swagger UI) em `http://localhost:8000/docs` e a documentação alternativa (ReDoc) em `http://localhost:8000/redoc`.

## 6. Executando os Testes

### 6.1. Testes Unitários

Os testes unitários mockam dependências externas (como o `GitlabService`) e testam a lógica interna dos serviços.

```bash
python -m unittest discover tests/unit
```

### 6.2. Testes de Integração

Os testes de integração fazem chamadas HTTP reais para a API rodando localmente, que por sua vez interage com uma instância **real** do GitLab.

**Importante:**
- **Configuração:** Certifique-se que seu arquivo `.env` está configurado com credenciais válidas para um **projeto de teste** no GitLab. Os testes criarão issues reais.
- **Projeto de Teste:** É altamente recomendável usar um projeto GitLab dedicado para testes para evitar poluir projetos de produção.

```bash
python -m unittest discover tests/integration
```
*(Nota: A execução bem-sucedida dos testes de integração no ambiente de desenvolvimento automatizado pode ser instável devido a timeouts ou falta de configuração do `.env` nesse ambiente específico).*

## 7. Documentação da API (Detalhada)

- Consulte o arquivo [docs/api_requirements_diagram.md](docs/api_requirements_diagram.md) para uma visão geral dos requisitos, diagrama de componentes e um resumo dos endpoints.
- Para a documentação completa e interativa dos endpoints, schemas de dados e modelos, acesse `/docs` ou `/redoc` quando a aplicação estiver rodando.

## 8. Coleção do Postman

Uma coleção do Postman para facilitar testes funcionais manuais está disponível em [docs/postman_collection.json](docs/postman_collection.json). Você pode importá-la no seu cliente Postman. A coleção inclui variáveis como `{{base_url}}` que você pode configurar no seu ambiente Postman.

---

*Observação sobre o `KRService` (Serviço de Key Results): A implementação da lógica completa para criação de KRs (incluindo formatação detalhada de títulos e descrições, vinculação e atualização da descrição do objetivo pai) está presente no código. No entanto, a verificação completa desta funcionalidade através da execução de testes foi dificultada por limitações no ambiente de desenvolvimento automatizado (timeouts). Recomenda-se testes manuais ou execução dos testes de integração em um ambiente local estável para validar completamente este serviço.*
