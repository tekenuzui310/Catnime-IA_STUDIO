# CATNIME AI STUDIO — Beta

Primeira versão funcional do CATNIME AI Studio com:

- Frontend dark/neon responsivo
- Upload e preview de PNG/JPG/WEBP
- 1080p, 2K e 4K
- Backend Django
- Real-ESRGAN via Replicate
- Face Enhance opcional
- Ajuste final exato com Pillow
- Download da imagem processada
- Endpoint `/api/health/`
- Endpoint `/api/upscale/`

## 1. Backend local

```bash
cd backend
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Instale:

```bash
pip install -r requirements.txt
```

Configure as variáveis de ambiente. Você pode copiar `.env.example`, mas note que Django não carrega `.env` sozinho. No Windows PowerShell:

```powershell
$env:REPLICATE_API_TOKEN="r8_SEU_TOKEN"
$env:REPLICATE_MODEL="nightmareai/real-esrgan"
```

Inicie:

```bash
python manage.py runserver
```

Teste:

`http://127.0.0.1:8000/api/health/`

## 2. Frontend local

Abra outro terminal:

```bash
cd frontend
python -m http.server 5500
```

Acesse:

`http://127.0.0.1:5500`

O `app.js` usa por padrão:

```js
http://127.0.0.1:8000/api
```

## 3. Produção

No frontend, antes de `app.js`, você pode definir:

```html
<script>
window.CATNIME_AI_API_BASE = "https://SEU-BACKEND/api";
</script>
<script src="./app.js"></script>
```

No backend, configure `REPLICATE_API_TOKEN`, `REPLICATE_MODEL`, `ALLOWED_HOSTS` e CORS no provedor.

## Importante

A chave do Replicate deve existir apenas no backend. Nunca coloque `REPLICATE_API_TOKEN` no JavaScript do navegador.

O modo atual preserva todo o conteúdo e não estica a imagem. Caso a proporção original não seja 16:9, a saída exata 1920×1080 / 2560×1440 / 3840×2160 terá espaço de preenchimento nas bordas.
