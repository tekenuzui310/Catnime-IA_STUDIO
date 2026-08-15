import tempfile
import io
import os
import uuid
from urllib.request import urlopen

import replicate
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from PIL import Image, ImageOps

TARGETS = {
    "1080p": (1920, 1080),
    "2k": (2560, 1440),
    "4k": (3840, 2160),
}

MAX_UPLOAD = 15 * 1024 * 1024

def health(request):
    configured = bool(os.getenv("REPLICATE_API_TOKEN"))
    return JsonResponse({
        "status": "ok",
        "service": "CATNIME AI Studio",
        "replicate_configured": configured,
    })

def _bool(value):
    return str(value).lower() in {"1", "true", "yes", "on"}

def _read_replicate_output(output):
    # Replicate outputs may be FileOutput-like objects, URLs, or lists.
    if isinstance(output, (list, tuple)):
        if not output:
            raise RuntimeError("O modelo não retornou arquivo.")
        output = output[0]

    if hasattr(output, "read"):
        data = output.read()
        if isinstance(data, bytes):
            return data

    url = getattr(output, "url", None)
    if callable(url):
        url = url()
    if not url:
        url = str(output)

    if not url.startswith(("http://", "https://")):
        raise RuntimeError("Formato de saída inesperado do modelo.")

    with urlopen(url, timeout=120) as response:
        return response.read()

def _resize_exact_contain(image, target):
    """
    Mantém todo o conteúdo da imagem sem esticar.
    O espaço restante é preenchido com um fundo preto.
    """
    image = image.convert("RGB")
    contained = ImageOps.contain(image, target, method=Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", target, (5, 5, 5))
    x = (target[0] - contained.width) // 2
    y = (target[1] - contained.height) // 2
    canvas.paste(contained, (x, y))
    return canvas

@csrf_exempt
def upscale_image(request):
    if request.method != "POST":
        return JsonResponse({"error": "Use POST."}, status=405)

    uploaded = request.FILES.get("image")
    resolution = request.POST.get("resolution", "1080p").lower()
    face_enhance = _bool(request.POST.get("face_enhance", "false"))

    if not uploaded:
        return JsonResponse({"error": "Nenhuma imagem foi enviada."}, status=400)

    if uploaded.size > MAX_UPLOAD:
        return JsonResponse({"error": "A imagem excede o limite de 15 MB."}, status=413)

    if resolution not in TARGETS:
        return JsonResponse({"error": "Resolução inválida. Use 1080p, 2k ou 4k."}, status=400)

    if not os.getenv("REPLICATE_API_TOKEN"):
        return JsonResponse({
            "error": "REPLICATE_API_TOKEN não configurado no backend."
        }, status=503)

    try:
        # Validate image before sending it to a paid API.
        uploaded.seek(0)
        check = Image.open(uploaded)
        check.verify()
        uploaded.seek(0)

        target_w, target_h = TARGETS[resolution]

        # Real-ESRGAN supports adjustable scale. We use 4x as a strong default,
        # then Pillow makes the output dimensions exact without stretching it.
        model = os.getenv("REPLICATE_MODEL", "nightmareai/real-esrgan")

uploaded.seek(0)

suffix = os.path.splitext(uploaded.name)[1] or ".png"

with tempfile.NamedTemporaryFile(
    suffix=suffix,
    delete=True
) as temp_file:

    for chunk in uploaded.chunks():
        temp_file.write(chunk)

    temp_file.flush()

    with open(temp_file.name, "rb") as image_file:

        output = replicate.run(
            model,
            input={
                "image": image_file,
                "scale": 4,
                "face_enhance": face_enhance,
            },
        )

        ai_bytes = _read_replicate_output(output)
        ai_image = Image.open(io.BytesIO(ai_bytes))
        final = _resize_exact_contain(ai_image, (target_w, target_h))

        buf = io.BytesIO()
        final.save(buf, format="PNG", optimize=True)
        payload = buf.getvalue()

        filename = f"catnime-ai-{resolution}-{uuid.uuid4().hex[:8]}.png"
        response = HttpResponse(payload, content_type="image/png")
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        response["Access-Control-Expose-Headers"] = "Content-Disposition"
        response["X-Catnime-Filename"] = filename
        response["X-Catnime-Width"] = str(target_w)
        response["X-Catnime-Height"] = str(target_h)
        return response

    except Exception as exc:
        return JsonResponse({
            "error": f"Falha no processamento: {exc}"
        }, status=500)
