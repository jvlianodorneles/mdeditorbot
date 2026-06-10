import os
import re
import html
import json
import logging
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InlineQuery, InlineQueryResultArticle, InputTextMessageContent
import config

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Config validation
if not config.is_configured():
    logger.error("Configuration error: Please set API_ID, API_HASH, and BOT_TOKEN in your environment or .env file.")
    print("\n⚠️  ATENÇÃO: Configure as variáveis API_ID, API_HASH e BOT_TOKEN no arquivo .env antes de rodar o bot!\n")
    # We will initialize the client inside a try block, but we alert the user here

SETTINGS_FILE = "user_settings.json"

SUPERSCRIPTS = {
    '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
    '+': '⁺', '-': '⁻', '=': '⁼', '(': '⁽', ')': '⁾', 'n': 'ⁿ', 'i': 'ⁱ', 'x': 'ˣ', 'y': 'ʸ'
}
SUBSCRIPTS = {
    '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄', '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
    '+': '₊', '-': '₋', '=': '₌', '(': '₍', ')': '₎', 'a': 'ₐ', 'e': 'ₑ', 'h': 'ₕ', 'i': 'ᵢ', 'j': 'ⱼ',
    'k': 'ₖ', 'l': 'ₗ', 'm': 'ₘ', 'n': 'ₙ', 'o': 'ₒ', 'p': 'ₚ', 'r': 'ᵣ', 's': 'ₛ', 't': 'ₜ', 'u': 'ᵤ',
    'v': 'ᵥ', 'x': 'ₓ'
}
GREEK_AND_SYMBOLS = {
    r'\alpha': 'α', r'\beta': 'β', r'\gamma': 'γ', r'\delta': 'δ', r'\epsilon': 'ε',
    r'\zeta': 'ζ', r'\eta': 'η', r'\theta': 'θ', r'\iota': 'ι', r'\kappa': 'κ',
    r'\lambda': 'λ', r'\mu': 'μ', r'\nu': 'ν', r'\xi': 'ξ', r'\pi': 'π',
    r'\rho': 'ρ', r'\sigma': 'σ', r'\tau': 'τ', r'\upsilon': 'υ', r'\phi': 'φ',
    r'\chi': 'χ', r'\psi': 'ψ', r'\omega': 'ω',
    r'\Delta': 'Δ', r'\Gamma': 'Γ', r'\Theta': 'Θ', r'\Lambda': 'Λ', r'\Xi': 'Ξ',
    r'\Pi': 'Pi', r'\Sigma': 'Σ', r'\Phi': 'Φ', r'\Psi': 'Ψ', r'\Omega': 'Ω',
    r'\times': '×', r'\div': '÷', r'\pm': '±', r'\mp': '∓',
    r'\leq': '≤', r'\le': '≤', r'\geq': '≥', r'\ge': '≥', r'\neq': '≠', r'\approx': '≈',
    r'\infty': '∞', r'\partial': '∂', r'\nabla': '∇', r'\sum': '∑', r'\prod': '∏',
    r'\int': '∫', r'\sqrt': '√', r'\to': '→', r'\rightarrow': '→', r'\gets': '←',
    r'\leftarrow': '←', r'\leftrightarrow': '↔', r'\forall': '∀', r'\exists': '∃',
    r'\in': '∈', r'\notin': '∉', r'\ni': '∋', r'\subset': '⊂', r'\supset': '⊃',
    r'\subseteq': '⊆', r'\supseteq': '⊇', r'\cap': '∩', r'\cup': '∪', r'\emptyset': '∅',
    r'\hbar': 'ℏ', r'\ell': 'ℓ'
}

def parse_math(expr: str) -> str:
    # 1. Replace Greek letters and math symbols
    for latex, unicode_char in GREEK_AND_SYMBOLS.items():
        pattern = re.escape(latex)
        if latex[-1].isalpha():
            pattern += r"(?![a-zA-Z])"
        expr = re.sub(pattern, unicode_char, expr)
    
    # 2. Handle superscripts: ^1, ^{12}, ^x, ^{x+1}
    def replace_sup_brace(match):
        inner = match.group(1)
        return "".join(SUPERSCRIPTS.get(c, c) for c in inner)
    expr = re.sub(r'\^{([^}]+)}', replace_sup_brace, expr)
    
    def replace_sup_single(match):
        char = match.group(1)
        return SUPERSCRIPTS.get(char, f"^{char}")
    expr = re.sub(r'\^([0-9a-zA-Z+\-\(\)])', replace_sup_single, expr)

    # 3. Handle subscripts: _1, _{12}, _x, _{x+1}
    def replace_sub_brace(match):
        inner = match.group(1)
        return "".join(SUBSCRIPTS.get(c, c) for c in inner)
    expr = re.sub(r'_{([^}]+)}', replace_sub_brace, expr)
    
    def replace_sub_single(match):
        char = match.group(1)
        return SUBSCRIPTS.get(char, f"_{char}")
    expr = re.sub(r'_([0-9a-zA-Z+\-\(\)])', replace_sub_single, expr)
    
    # 4. Handle square roots: \sqrt{expression} -> √(expression)
    expr = re.sub(r'\\sqrt{([^}]+)}', r'√(\1)', expr)

    return expr

def gfm_to_html(text: str) -> str:
    # 1. Protect code blocks (```...```) and inline code (`...`) from being processed
    code_blocks = []
    def save_code_block(match):
        code_blocks.append(match.group(0))
        return f"__CODE_BLOCK_PLACEHOLDER_{len(code_blocks)-1}__"
    
    text = re.sub(r'```.*?```', save_code_block, text, flags=re.DOTALL)
    
    inline_codes = []
    def save_inline_code(match):
        inline_codes.append(match.group(0))
        return f"__INLINE_CODE_PLACEHOLDER_{len(inline_codes)-1}__"
    
    text = re.sub(r'`[^`\n]+`', save_inline_code, text)

    # 2. Convert GFM Math blocks: $$expr$$ -> <pre>parsed_math</pre>
    def replace_block_math(match):
        expr = match.group(1).strip()
        parsed = parse_math(expr)
        return f"<pre>{parsed}</pre>"
    text = re.sub(r'\$\$(.*?)\$\$', replace_block_math, text, flags=re.DOTALL)

    # 3. Convert GFM Inline Math: $expr$ -> <code>parsed_math</code>
    def replace_inline_math(match):
        expr = match.group(1).strip()
        parsed = parse_math(expr)
        return f"<code>{parsed}</code>"
    text = re.sub(r'\$([^$\n]+)\$', replace_inline_math, text)

    # 4. Standard Markdown to HTML conversion
    # Bold: **text**
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    # Italic: *text* or _text_
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    text = re.sub(r'_(.*?)_', r'<i>\1</i>', text)
    # Strikethrough: ~~text~~
    text = re.sub(r'~~(.*?)(?<!\\)~~', r'<s>\1</s>', text)
    # Spoiler: ||text||
    text = re.sub(r'\|\|(.*?)\|\|', r'<spoiler>\1</spoiler>', text)

    # Headers: # Header
    def replace_header(match):
        level = len(match.group(1))
        header_text = match.group(2).strip()
        return f"<b>{header_text}</b>"
    text = re.sub(r'^(#{1,6})\s+(.*?)$', replace_header, text, flags=re.MULTILINE)

    # Blockquotes: > Quote
    text = re.sub(r'^>\s+(.*?)$', r'<blockquote>\1</blockquote>', text, flags=re.MULTILINE)

    # Links: [text](url)
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', text)

    # 5. Restore code placeholders
    for i, code_block in enumerate(code_blocks):
        content = code_block.strip('`').strip()
        lines = content.split('\n', 1)
        lang = ""
        code_text = content
        if len(lines) > 1 and not ' ' in lines[0]:
            lang = lines[0].strip()
            code_text = lines[1]
        
        code_text = html.escape(code_text)
        if lang:
            html_code = f'<pre language="{lang}">{code_text}</pre>'
        else:
            html_code = f'<pre>{code_text}</pre>'
        text = text.replace(f"__CODE_BLOCK_PLACEHOLDER_{i}__", html_code)

    for i, inline_code in enumerate(inline_codes):
        content = html.escape(inline_code.strip('`'))
        html_code = f'<code>{content}</code>'
        text = text.replace(f"__INLINE_CODE_PLACEHOLDER_{i}__", html_code)

    return text

def load_user_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading user settings: {e}")
            return {}
    return {}

def save_user_setting(user_id: int, parse_mode: str):
    settings = load_user_settings()
    settings[str(user_id)] = parse_mode
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving settings: {e}")

# Initialize client if configured, otherwise create a placeholder
app = None
if config.is_configured():
    app = Client(
        "formatting_bot",
        api_id=config.API_ID,
        api_hash=config.API_HASH,
        bot_token=config.BOT_TOKEN
    )

async def upload_markdown_photos(client: Client, text: str, peer) -> list:
    import urllib.request
    import tempfile
    
    img_matches = re.findall(r'!\[(.*?)\]\((https?://[^)]+)\)', text)
    photos = []
    
    for alt, url in img_matches:
        tmp_path = None
        try:
            # Create a temporary file with .jpg extension to avoid PHOTO_EXT_INVALID
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp_path = tmp.name
                
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
            )
            with urllib.request.urlopen(req, timeout=10) as response, open(tmp_path, 'wb') as out_file:
                out_file.write(response.read())
                
            # Upload the file
            input_file = await client.save_file(tmp_path)
            
            # Convert to InputPhoto
            from pyrogram.raw.types import InputMediaUploadedPhoto, InputPhoto
            from pyrogram.raw.functions.messages import UploadMedia
            
            media = InputMediaUploadedPhoto(file=input_file)
            raw_media = await client.invoke(UploadMedia(peer=peer, media=media))
            photo = raw_media.photo
            
            input_photo = InputPhoto(
                id=photo.id,
                access_hash=photo.access_hash,
                file_reference=photo.file_reference
            )
            photos.append(input_photo)
            
        except Exception as e:
            logger.exception(f"Failed to download/upload image {url}: {e}")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
            
    return photos

async def format_and_send(client: Client, chat_id: int, text: str, mode: str, reply_to_message_id: int = None, edit_message_id: int = None, reply_markup = None):
    # If using Markdown/GFM or HTML modes, send via raw MTProto RichMessage support
    if mode in ["markdown", "markdown_v2", "math", "combined", "html"]:
        try:
            # Resolve the peer (chat)
            peer = await client.resolve_peer(chat_id)
            
            # Create a random_id
            import random
            random_id = random.randint(-9223372036854775808, 9223372036854775807)
            
            # Formulate the reply_to if reply_to_message_id is provided
            from pyrogram.raw.types import InputReplyToMessage, InputRichMessageHTML, InputRichMessageMarkdown
            from pyrogram.raw.functions.messages import SendMessage, EditMessage
            
            reply_to = InputReplyToMessage(reply_to_msg_id=reply_to_message_id) if reply_to_message_id else None
            
            # Prepare rich message (use HTML for html mode, and Markdown for all other modes)
            if mode == "html":
                rich_msg = InputRichMessageHTML(html=text)
            else:
                photos = await upload_markdown_photos(client, text, peer)
                rich_msg = InputRichMessageMarkdown(markdown=text, photos=photos if photos else None)
            
            raw_reply_markup = None
            if reply_markup:
                raw_reply_markup = await reply_markup.write(client)
            
            if edit_message_id:
                # Edit using raw invoke!
                await client.invoke(
                    EditMessage(
                        peer=peer,
                        id=edit_message_id,
                        message=text,  # Fallback text
                        rich_message=rich_msg,
                        reply_markup=raw_reply_markup
                    )
                )
            else:
                # Send using raw invoke!
                await client.invoke(
                    SendMessage(
                        peer=peer,
                        message=text,  # Fallback text
                        random_id=random_id,
                        reply_to=reply_to,
                        rich_message=rich_msg,
                        reply_markup=raw_reply_markup
                    )
                )
            return
        except Exception as e:
            logger.exception(f"Error sending rich message via raw MTProto: {e}")
            # Fallback to standard sending on error
            pass

    # Standard HTML mode or fallback
    parse_mode = enums.ParseMode.HTML if mode == "html" else enums.ParseMode.DEFAULT
        
    try:
        if edit_message_id:
            await client.edit_message_text(
                chat_id=chat_id,
                message_id=edit_message_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
        else:
            # Send formatted message
            await client.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                reply_to_message_id=reply_to_message_id,
                reply_markup=reply_markup
            )
    except Exception as e:
        error_msg = f"❌ **Erro de Formatação ({mode.upper()}):**\n\n```\n{str(e)}\n```\n\nVerifique se o seu código está correto e com as tags fechadas/escapadas devidamente."
        if edit_message_id:
            await client.edit_message_text(
                chat_id=chat_id,
                message_id=edit_message_id,
                text=error_msg,
                parse_mode=enums.ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        else:
            await client.send_message(
                chat_id=chat_id,
                text=error_msg,
                parse_mode=enums.ParseMode.MARKDOWN,
                reply_to_message_id=reply_to_message_id,
                reply_markup=reply_markup
            )
COMMANDS_SET = False

async def ensure_commands(client: Client):
    global COMMANDS_SET
    if COMMANDS_SET:
        return
    try:
        from pyrogram.types import BotCommand
        await client.set_bot_commands([
            BotCommand("start", "Iniciar o bot"),
            BotCommand("help", "Ajuda de formatação"),
            BotCommand("about", "Sobre o bot"),
            BotCommand("demo", "Mensagem de demonstração")
        ])
        
        # Set short description (shows in sharing / bot bio)
        await client.set_bot_info_short_description(
            "Formatador GFM Markdown e LaTeX para mensagens ricas no Telegram."
        )
        
        # Set full description (shows inside empty chat before starting)
        await client.set_bot_info_description(
            "Este bot converte mensagens de texto em formato GFM Markdown (GitHub Flavored Markdown) e LaTeX em mensagens ricas nativas do Telegram.\n\n"
            "Suporta negrito, itálico, spoilers, tabelas, blockquotes, listas, checklists, notas de rodapé e fórmulas matemáticas!"
        )
        
        COMMANDS_SET = True
        logger.info("Bot commands and descriptions set successfully!")
    except Exception as e:
        logger.error(f"Error setting bot commands/descriptions: {e}")

if app:
    @app.on_message(filters.private & filters.command("start"))
    async def start_command(client: Client, message: Message):
        await ensure_commands(client)
        welcome_text = (
            "👋 **Olá! Eu sou o bot de formatação de mensagens.**\n\n"
            "Eu fui criado para converter textos com marcações de código Markdown "
            "em mensagens ricas formatadas nativamente no Telegram. Eu dou suporte ao GFM (GitHub Flavored Markdown), "
            "o que inclui negrito, itálico, spoilers, blocos de código e fórmulas matemáticas LaTeX (usando `$` e `$$`).\n\n"
            "**Como usar:** Basta enviar qualquer mensagem formatada em Markdown diretamente no chat, e eu responderei com o texto formatado."
        )
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📖 Ajuda", callback_data="help"),
                InlineKeyboardButton("🚀 Demonstração", callback_data="demo")
            ],
            [
                InlineKeyboardButton("ℹ️ Sobre", callback_data="about")
            ]
        ])
        await message.reply_text(welcome_text, quote=True, reply_markup=buttons)

    @app.on_callback_query()
    async def handle_callbacks(client: Client, callback_query: CallbackQuery):
        await ensure_commands(client)
        data = callback_query.data
        try:
            await callback_query.answer()
        except Exception:
            pass
        
        chat_id = callback_query.message.chat.id
        msg_id = callback_query.message.id
        
        back_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Voltar", callback_data="back_start")]
        ])
        
        if data == "help":
            help_text = (
                "📖 **Formato markdown**\n\n"
                "Para aprender a formatar textos e códigos em Markdown, consulte o guia de referência rápida no link abaixo:\n"
                "🔗 [Guia de referência Markdown](https://github.com/adam-p/markdown-here/wiki/markdown-cheatsheet)\n\n"
                "Você pode adicionar este estilo de tradução IA no seu Telegram para expandir e converter textos comuns em código Markdown automaticamente antes de enviá-los no chat privado deste bot:\n"
                "🔗 [Adicionar estilo de IA no Telegram](https://t.me/addstyle/mBeDuJ1a1CHk0k5P)"
            )
            await client.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=help_text,
                reply_markup=back_markup,
                disable_web_page_preview=False
            )
        elif data == "demo":
            demo_markdown = (
                "🚀 **Demonstração completa de formatação markdown GFM**\n\n"
                "Aqui está uma amostra de tudo o que eu consigo formatar:\n\n"
                "### 1. Formatação de texto básica\n"
                "- **Negrito:** `**negrito**` -> **negrito**\n"
                "- *Itálico:* `*itálico*` -> *itálico*\n"
                "- ~~Riscado:~~ `~~riscado~~` -> ~~riscado~~\n"
                "- ||Spoiler:|| `||spoiler||` -> ||spoiler||\n"
                "- [Link](https://github.com) -> `[Link](https://github.com)`\n"
                "- **Texto marcado:** <mark>destacado</mark> -> `<mark>destacado</mark>`\n"
                "- **Estilo aninhado (nested):** **Texto em negrito contendo _itálico_ e ||um spoiler|| tudo junto**\n\n"
                "### 2. Listas e checklists (com aninhamento)\n"
                "Lista não ordenada com checklist aninhado:\n"
                "- Tarefas do projeto:\n"
                "  - [x] Atualizar biblioteca para Layer 227\n"
                "  - [ ] Implementar novos comandos\n"
                "    - [ ] Escrever testes unitários\n\n"
                "Lista ordenada:\n"
                "1. Passo um\n"
                "2. Passo dois\n\n"
                "### 3. Citações e códigos\n"
                "Citação em bloco aninhada (nested blockquote):\n"
                "> \"A imaginação é mais importante que o conhecimento...\"\n"
                ">> \"E o conhecimento é limitado perante ela.\"\n"
                "> — *Albert Einstein*\n\n"
                "Código inline: `` `print('Olá')` `` -> `print('Olá')`\n\n"
                "Bloco de código (Python):\n"
                "```python\n"
                "def soma(a, b):\n"
                "    return a + b\n"
                "```\n\n"
                "### 4. Fórmulas matemáticas LaTeX\n"
                "- **Fórmula inline:** Equivalência massa-energia: $E = mc^2$\n"
                "- **Fórmula em bloco (Bhaskara):**\n"
                "$$x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}$$\n"
                "- **Fórmula em bloco (Navier-Stokes):**\n"
                "$$\\frac{\\partial}{\\partial t} \\int_{\\Omega} \\rho \\mathbf{u} \\, d\\Omega + \\int_{\\partial\\Omega} \\rho \\mathbf{u} (\\mathbf{u} \\cdot \\mathbf{n}) \\, d\\Gamma = \\int_{\\partial\\Omega} -p \\mathbf{n} \\, d\\Gamma + \\int_{\\partial\\Omega} \\mu \\left( \\nabla \\mathbf{u} + (\\nabla \\mathbf{u})^T \\right) \\mathbf{n} \\, d\\Gamma + \\int_{\\Omega} \\mathbf{f}_b \\, d\\Omega$$\n\n"
                "### 5. Notas de rodapé\n"
                "Aqui está uma afirmação que precisa de referência[^1].\n\n"
                "[^1]: Esta é a nota de rodapé com a explicação detalhada da referência.\n\n"
                "### 6. Seção expansível\n"
                "<details>\n"
                "<summary>Clique aqui para expandir</summary>\n\n"
                "Este é o conteúdo oculto revelado ao expandir a seção!\n"
                "</details>\n\n"
                "### 7. Tabela\n"
                "| Recurso | Exemplo formatado | Sintaxe usada |\n"
                "| --- | --- | --- |\n"
                "| Negrito | **negrito** | `**negrito**` |\n"
                "| Math | $x^2$ | `$$x^2$$` |\n\n"
                "### 8. Seis níveis de títulos\n"
                "# Título nível 1\n"
                "## Título nível 2\n"
                "### Título nível 3\n"
                "#### Título nível 4\n"
                "##### Título nível 5\n"
                "###### Título nível 6\n\n"
                "### 9. Imagem de demonstração\n"
                "![Screenshot of a comment on a GitHub issue showing an image, added in the Markdown, of an Octocat smiling and raising a tentacle.](https://fujiframe.com/assets/images/_3000x2000_fit_center-center_85_none/1171/fuji-70-300-review-00014.webp)"
            )
            await format_and_send(client, chat_id, demo_markdown, "markdown", edit_message_id=msg_id, reply_markup=back_markup)
        elif data == "about":
            about_text = (
                "ℹ️ **Sobre o bot**\n\n"
                "• **Desenvolvedor:** Juliano Dorneles dos Santos\n"
                "• **Telegram:** @jvlianodorneles\n"
                "• **Tecnologia:** Python / PyroTGFork (MTProto API Layer 227)"
            )
            await client.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=about_text,
                reply_markup=back_markup
            )
        elif data == "back_start":
            welcome_text = (
                "👋 **Olá! Eu sou o bot de formatação de mensagens.**\n\n"
                "Eu fui criado para converter textos com marcações de código Markdown "
                "em mensagens ricas formatadas nativamente no Telegram. Eu dou suporte ao GFM (GitHub Flavored Markdown), "
                "o que inclui negrito, itálico, spoilers, blocos de código e fórmulas matemáticas LaTeX (usando `$` e `$$`).\n\n"
                "**Como usar:** Basta enviar qualquer mensagem formatada em Markdown diretamente no chat, e eu responderei com o texto formatado."
            )
            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📖 Ajuda", callback_data="help"),
                    InlineKeyboardButton("🚀 Demonstração", callback_data="demo")
                ],
                [
                    InlineKeyboardButton("ℹ️ Sobre", callback_data="about")
                ]
            ])
            await client.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=welcome_text,
                reply_markup=buttons
            )

    @app.on_message(filters.private & filters.command("help"))
    async def help_command(client: Client, message: Message):
        await ensure_commands(client)
        help_text = (
            "📖 **Ajuda de formatação markdown**\n\n"
            "Para aprender a formatar textos e códigos em Markdown, consulte o guia de referência rápida no link abaixo:\n"
            "🔗 [Guia de referência Markdown](https://github.com/adam-p/markdown-here/wiki/markdown-cheatsheet)\n\n"
            "**Dica (Tradução e Estilo IA):**\n"
            "Você pode adicionar este estilo de tradução IA no seu Telegram para expandir e converter textos comuns em código Markdown automaticamente antes de enviá-los no chat privado deste bot:\n"
            "🔗 [Adicionar estilo de IA no Telegram](https://t.me/addstyle/mBeDuJ1a1CHk0k5P)"
        )
        await message.reply_text(help_text, quote=True, disable_web_page_preview=False)

    @app.on_message(filters.private & filters.command("about"))
    async def about_command(client: Client, message: Message):
        await ensure_commands(client)
        about_text = (
            "ℹ️ **Sobre o bot**\n\n"
            "• **Desenvolvedor:** Juliano Dorneles dos Santos\n"
            "• **Telegram:** @jvlianodorneles\n"
            "• **Tecnologia:** Python / PyroTGFork (MTProto API Layer 227)"
        )
        await message.reply_text(about_text, quote=True)

    @app.on_message(filters.private & filters.command("demo"))
    async def demo_command(client: Client, message: Message):
        await ensure_commands(client)
        demo_markdown = (
            "🚀 **Demonstração completa de formatação markdown GFM**\n\n"
            "Aqui está uma amostra de tudo o que eu consigo formatar:\n\n"
            "### 1. Formatação de texto básica\n"
            "- **Negrito:** `**negrito**` -> **negrito**\n"
            "- *Itálico:* `*itálico*` -> *itálico*\n"
            "- ~~Riscado:~~ `~~riscado~~` -> ~~riscado~~\n"
            "- ||Spoiler:|| `||spoiler||` -> ||spoiler||\n"
            "- [Link](https://github.com) -> `[Link](https://github.com)`\n"
            "- **Texto marcado:** <mark>destacado</mark> -> `<mark>destacado</mark>`\n"
            "- **Estilo aninhado (nested):** **Texto em negrito contendo _itálico_ e ||um spoiler|| tudo junto**\n\n"
            "### 2. Listas e checklists (com aninhamento)\n"
            "Lista não ordenada com checklist aninhado:\n"
            "- Tarefas do projeto:\n"
            "  - [x] Atualizar biblioteca para Layer 227\n"
            "  - [ ] Implementar novos comandos\n"
            "    - [ ] Escrever testes unitários\n\n"
            "Lista ordenada:\n"
            "1. Passo um\n"
            "2. Passo dois\n\n"
            "### 3. Citações e códigos\n"
            "Citação em bloco aninhada (nested blockquote):\n"
            "> \"A imaginação é mais importante que o conhecimento...\"\n"
            ">> \"E o conhecimento é limitado perante ela.\"\n"
            "> — *Albert Einstein*\n\n"
            "Código inline: `` `print('Olá')` `` -> `print('Olá')`\n\n"
            "Bloco de código (Python):\n"
            "```python\n"
            "def soma(a, b):\n"
            "    return a + b\n"
            "```\n\n"
            "### 4. Fórmulas matemáticas LaTeX\n"
            "- **Fórmula inline:** Equivalência massa-energia: $E = mc^2$\n"
            "- **Fórmula em bloco (Bhaskara):**\n"
            "$$x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}$$\n"
            "- **Fórmula em bloco (Navier-Stokes):**\n"
            "$$\\frac{\\partial}{\\partial t} \\int_{\\Omega} \\rho \\mathbf{u} \\, d\\Omega + \\int_{\\partial\\Omega} \\rho \\mathbf{u} (\\mathbf{u} \\cdot \\mathbf{n}) \\, d\\Gamma = \\int_{\\partial\\Omega} -p \\mathbf{n} \\, d\\Gamma + \\int_{\\partial\\Omega} \\mu \\left( \\nabla \\mathbf{u} + (\\nabla \\mathbf{u})^T \\right) \\mathbf{n} \\, d\\Gamma + \\int_{\\Omega} \\mathbf{f}_b \\, d\\Omega$$\n\n"
            "### 5. Notas de rodapé\n"
            "Aqui está uma afirmação que precisa de referência[^1].\n\n"
            "[^1]: Esta é a nota de rodapé com a explicação detalhada da referência.\n\n"
            "### 6. Seção expansível\n"
            "<details>\n"
            "<summary>Clique aqui para expandir</summary>\n\n"
            "Este é o conteúdo oculto revelado ao expandir a seção!\n"
            "</details>\n\n"
            "### 7. Tabela\n"
            "| Recurso | Exemplo formatado | Sintaxe usada |\n"
            "| --- | --- | --- |\n"
            "| Negrito | **negrito** | `**negrito**` |\n"
            "| Math | $x^2$ | `$$x^2$$` |\n\n"
            "### 8. Seis níveis de títulos\n"
            "# Título nível 1\n"
            "## Título nível 2\n"
            "### Título nível 3\n"
            "#### Título nível 4\n"
            "##### Título nível 5\n"
            "###### Título nível 6\n\n"
            "### 9. Imagem de demonstração\n"
            "![Screenshot of a comment on a GitHub issue showing an image, added in the Markdown, of an Octocat smiling and raising a tentacle.](https://fujiframe.com/assets/images/_3000x2000_fit_center-center_85_none/1171/fuji-70-300-review-00014.webp)"
        )
        await format_and_send(client, message.chat.id, demo_markdown, "markdown", reply_to_message_id=message.id)

    @app.on_message(filters.private & filters.text)
    async def handle_message(client: Client, message: Message):
        await ensure_commands(client)
        # Ignore command messages
        if message.text.startswith("/"):
            return
            
        await format_and_send(client, message.chat.id, message.text, "markdown", reply_to_message_id=message.id)

    @app.on_inline_query()
    async def inline_handler(client: Client, inline_query: InlineQuery):
        await ensure_commands(client)
        query = inline_query.query
        if not query.strip():
            # Return a simple helper result article
            await inline_query.answer([
                InlineQueryResultArticle(
                    title="Escreva algo em Markdown",
                    description="Digite texto formatado em GFM Markdown para enviar formatado.",
                    input_message_content=InputTextMessageContent("Use o bot inline digitando: @nome_do_bot seu texto markdown")
                )
            ], cache_time=1)
            return
            
        try:
            from pyrogram.raw.types import InputBotInlineResult, InputBotInlineMessageRichMessage, InputRichMessageMarkdown
            from pyrogram.raw.functions.messages import SetInlineBotResults
            
            # For inline queries, we construct the rich message markdown directly
            # We don't download/upload photos here since it would be slow/require context
            rich_msg = InputRichMessageMarkdown(markdown=query)
            
            result = InputBotInlineResult(
                id="1",
                type="article",
                title="Enviar texto formatado (GFM)",
                description=query[:80] + "..." if len(query) > 80 else query,
                send_message=InputBotInlineMessageRichMessage(rich_message=rich_msg)
            )
            
            await client.invoke(
                SetInlineBotResults(
                    query_id=int(inline_query.id),
                    results=[result],
                    cache_time=1
                )
            )
        except Exception as e:
            logger.exception(f"Error handling inline query: {e}")


if __name__ == "__main__":
    if app:
        print("🤖 Bot iniciado com sucesso!")
        app.run()
    else:
        print("\n⚠️  Bot não pôde ser iniciado porque as credenciais não foram configuradas no arquivo .env.")
        print("Crie um arquivo .env a partir do .env.example e adicione suas credenciais.")
        print("Exemplo de execução posterior: python bot.py\n")
