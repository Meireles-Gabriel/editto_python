# Éditto Magazine - Backend API

Backend da aplicação Éditto Magazine, responsável pela geração de revistas digitais personalizadas usando Inteligência Artificial.

## Tecnologias

- Python 3.11
- Flask
- Firebase (Auth, Firestore, Storage)
- Google Cloud Platform
  - Cloud Run
  - Pub/Sub
  - Gemini AI
  - Imagen AI
- crewAI
- Exa API

## Arquitetura

O backend é estruturado em módulos:

- `staff/`: Módulo principal contendo a lógica de geração de revistas
  - `src/staff/main.py`: API Flask com endpoints para criação de revistas
  - `src/staff/crew.py`: Configuração dos agentes AI usando crewAI
  - `src/staff/config/`: Configurações YAML para agentes e tarefas
  - `src/staff/utilities/`: Utilitários para processamento de conteúdo

## Fluxo de Criação de Revista

1. Inicialização do processo (`/init-magazine-process-endpoint`)
2. Busca de artigos (`/fetch-articles-endpoint`)
3. Reescrita de conteúdo (`/rewrite-articles-endpoint`)
4. Geração de texto da capa (`/generate-cover-text-endpoint`)
5. Geração de imagem da capa (`/generate-image-endpoint`)
6. Finalização do processo (`/finalize-magazine-raw-data-endpoint`)

## Configuração do Ambiente

### Pré-requisitos

- Python 3.11
- Pip ou UV (gerenciador de pacotes)
- Conta Google Cloud Platform
- Conta Firebase
- Chaves de API:
  - Gemini AI
  - Exa API
  - Firebase Admin

### Variáveis de Ambiente

Criar arquivo `.env` com:

```env
GOOGLE_CLOUD_PROJECT_ID=seu-projeto-id
GEMINI_API_KEY=sua-chave-gemini
EXA_API_KEY=sua-chave-exa
```

### Arquivos de Credenciais

Adicionar na pasta `staff/src/staff/utilities/`:
- `gac.json`: Credenciais do Google Application
- `fac.json`: Credenciais do Firebase Admin

### Instalação

1. Clone o repositório
2. Instale as dependências:
```bash
pip install -r requirements.txt
```

### Execução Local

```bash
python staff/src/staff/main.py
```

### Deploy com Docker

1. Construa a imagem:
```bash
docker build -t editto-backend .
```

2. Execute o container:
```bash
docker run -p 8080:8080 editto-backend
```

## Desenvolvimento

### Estrutura de Arquivos

```
editto_python/
├── staff/
│   └── src/
│       └── staff/
│           ├── config/
│           │   ├── agents.yaml
│           │   └── tasks.yaml
│           ├── utilities/
│           │   ├── process_rewritten_article.py
│           │   └── process_cover_content.py
│           ├── crew.py
│           ├── main.py
│           └── globals.py
├── Dockerfile
└── requirements.txt
```

### Testes

Em desenvolvimento. Futuras versões incluirão testes unitários e de integração.

### Contribuição

1. Fork o repositório
2. Crie uma branch para sua feature (`git checkout -b feature/nome-da-feature`)
3. Faça commit das mudanças (`git commit -am 'Adiciona feature'`)
4. Push para a branch (`git push origin feature/nome-da-feature`)
5. Crie um Pull Request

## Licença

Este projeto é um software proprietário. Todos os direitos reservados.
