# GFM Telegram Formatting Bot

Este bot converte automaticamente mensagens formatadas em **GFM Markdown** (GitHub Flavored Markdown) e **LaTeX** em mensagens ricas nativas do Telegram utilizando a API de mensagens ricas da **Layer 227 (MTProto)**.

## Recursos

- **Formatação de Texto**: Negrito, itálico, tachado, spoilers, trechos em código mono e blocos com sintaxe colorida.
- **Estruturas GFM**: Listas não ordenadas, listas ordenadas, checklists (com caixas de seleção interativas `[ ]`/`[x]`), blockquotes aninhados, tabelas e notas de rodapé.
- **Fórmulas Matemáticas LaTeX**: Conversão automática de equações matemáticas inline (`$formula$`) ou em bloco (`$$formula$$`) em caracteres matemáticos Unicode nativos.
- **Imagens Integradas**: Suporta sintaxe markdown padrão de imagem `![alt](url)` baixando-as de forma automática no servidor e enviando como mídia MTProto integrada sem quebrar.
- **Menu e Botões Interativos**: Configuração dinâmica de comandos nativos do Telegram no menu principal do bot e suporte a botões inline na mensagem `/start` (Ajuda, Demonstração e Sobre) com navegação interna por edição de mensagem (sem poluir o chat).
- **Modo Inline**: Digite `@nome_do_bot seu markdown` em qualquer conversa para gerar e enviar mensagens ricas.

---

## Pré-requisitos

- **Python 3.8+**
- **Git**

---

## Instalação e Execução

### 1. Clonar o repositório

```bash
git clone https://github.com/seu-usuario/seu-repositorio.git
cd seu-repositorio
```

### 2. Instalar as dependências

Para compilar os schemas da Layer 227 do MTProto, é necessário instalar o fork especial `pyrotgfork` diretamente da branch `dev`:

```bash
pip install -r requirements.txt
```

> *Nota: O `requirements.txt` já aponta para a URL do repositório dev do `PyroTGFork`.*

### 3. Configurar as variáveis de ambiente

Copie o arquivo `.env.example` para `.env`:

```bash
cp .env.example .env
```

Abra o arquivo `.env` e preencha com suas credenciais obtidas no Telegram:

* **API_ID** e **API_HASH**: Obtenha em [my.telegram.org](https://my.telegram.org) (API Development Tools).
* **BOT_TOKEN**: Obtenha ao criar o bot no [BotFather](https://t.me/BotFather).

### 4. Executar o bot

Rode o script principal:

```bash
python bot.py
```

*(No Windows, se houver problemas com caracteres unicode no console, você pode forçar o encoding UTF-8 usando `$env:PYTHONUTF8=1; python bot.py`)*

---

## Configurações Adicionais no Telegram (BotFather)

Para aproveitar todas as funções do bot, envie os seguintes comandos ao [BotFather](https://t.me/BotFather):

1. **Modo Inline**: Envie `/setinline`, selecione o seu bot e insira a frase de placeholder (ex: *Escreva em Markdown...*).
2. **Configurações de Privacidade**: Envie `/setprivacy`, selecione o seu bot e defina como `Disabled` para permitir que o bot leia mensagens e as formate no privado (opcional).

---

## Estrutura do Projeto

* `bot.py`: Código principal com manipuladores de comandos, conversão GFM/LaTeX, upload de mídias e modo inline.
* `config.py`: Módulo auxiliar para carregamento e validação das configurações no `.env`.
* `requirements.txt`: Dependências necessárias para executar a aplicação.
* `.env.example`: Modelo das configurações necessárias do ambiente.
* `.gitignore`: Filtro de exclusão de arquivos para commit seguro.
