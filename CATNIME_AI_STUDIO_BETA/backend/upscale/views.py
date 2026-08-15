import io
import os
import uuid
import tempfile
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

    configured = bool(
        os.getenv("REPLICATE_API_TOKEN")
    )

    return JsonResponse({
        "status": "ok",
        "service": "CATNIME AI Studio",
        "replicate_configured": configured,
    })


def _bool(value):

    return str(value).lower() in {
        "1",
        "true",
        "yes",
        "on"
    }


def _read_replicate_output(output):

    # Alguns modelos podem retornar uma lista
    if isinstance(output, (list, tuple)):

        if not output:
            raise RuntimeError(
                "O modelo não retornou nenhuma imagem."
            )

        output = output[0]

    # FileOutput do Replicate
    if hasattr(output, "read"):

        data = output.read()

        if isinstance(data, bytes):
            return data

    # Alguns outputs possuem .url()
    url = getattr(output, "url", None)

    if callable(url):
        url = url()

    if not url:
        url = str(output)

    if not url.startswith(
        ("http://", "https://")
    ):

        raise RuntimeError(
            "Formato de saída inesperado do Replicate."
        )

    with urlopen(
        url,
        timeout=180
    ) as response:

        return response.read()


def _resize_exact_contain(
    image,
    target
):

    """
    Mantém toda a imagem sem esticar.

    Se a proporção não for 16:9,
    adiciona pequenas bordas para
    atingir exatamente:

    1920x1080
    2560x1440
    3840x2160
    """

    image = image.convert("RGB")

    contained = ImageOps.contain(
        image,
        target,
        method=Image.Resampling.LANCZOS
    )

    canvas = Image.new(
        "RGB",
        target,
        (5, 5, 5)
    )

    x = (
        target[0] -
        contained.width
    ) // 2

    y = (
        target[1] -
        contained.height
    ) // 2

    canvas.paste(
        contained,
        (x, y)
    )

    return canvas


@csrf_exempt
def upscale_image(request):

    if request.method != "POST":

        return JsonResponse(
            {
                "error": "Use POST."
            },
            status=405
        )


    uploaded = request.FILES.get(
        "image"
    )

    resolution = request.POST.get(
        "resolution",
        "1080p"
    ).lower()

    face_enhance = _bool(
        request.POST.get(
            "face_enhance",
            "false"
        )
    )


    if not uploaded:

        return JsonResponse(
            {
                "error":
                "Nenhuma imagem foi enviada."
            },
            status=400
        )


    if uploaded.size > MAX_UPLOAD:

        return JsonResponse(
            {
                "error":
                "A imagem excede o limite de 15 MB."
            },
            status=413
        )


    if resolution not in TARGETS:

        return JsonResponse(
            {
                "error":
                "Resolução inválida."
            },
            status=400
        )


    if not os.getenv(
        "REPLICATE_API_TOKEN"
    ):

        return JsonResponse(
            {
                "error":
                "REPLICATE_API_TOKEN não configurado."
            },
            status=503
        )


    try:

        # =========================
        # VALIDAR IMAGEM
        # =========================

        uploaded.seek(0)

        check = Image.open(uploaded)

        check.verify()

        uploaded.seek(0)


        # =========================
        # RESOLUÇÃO FINAL
        # =========================

        target_w, target_h = (
            TARGETS[resolution]
        )


        # =========================
        # MODELO
        # =========================

        model = os.getenv(
            "REPLICATE_MODEL",
            "nightmareai/real-esrgan"
        )


        # =========================
        # ARQUIVO TEMPORÁRIO
        # =========================

        suffix = os.path.splitext(
            uploaded.name
        )[1]

        if not suffix:

            suffix = ".png"


        with tempfile.NamedTemporaryFile(
            suffix=suffix
        ) as temp_file:

            uploaded.seek(0)

            for chunk in uploaded.chunks():

                temp_file.write(chunk)

            temp_file.flush()


            # =========================
            # ENVIAR PARA REPLICATE
            # =========================

            with open(
                temp_file.name,
                "rb"
            ) as image_file:

                output = replicate.run(
                    model,
                    input={
                        "image": image_file,
                        "scale": 4,
                        "face_enhance":
                            face_enhance,
                    },
                )


        # =========================
        # PEGAR RESULTADO DA IA
        # =========================

        ai_bytes = (
            _read_replicate_output(
                output
            )
        )


        ai_image = Image.open(
            io.BytesIO(
                ai_bytes
            )
        )


        # =========================
        # RESOLUÇÃO EXATA
        # =========================

        final = _resize_exact_contain(
            ai_image,
            (
                target_w,
                target_h
            )
        )


        # =========================
        # CONVERTER PARA PNG
        # =========================

        buffer = io.BytesIO()

        final.save(
            buffer,
            format="PNG",
            optimize=True
        )

        payload = buffer.getvalue()


        filename = (
            f"catnime-ai-"
            f"{resolution}-"
            f"{uuid.uuid4().hex[:8]}"
            f".png"
        )


        # =========================
        # RESPOSTA
        # =========================

        response = HttpResponse(
            payload,
            content_type="image/png"
        )


        response[
            "Content-Disposition"
        ] = (
            f'inline; '
            f'filename="{filename}"'
        )


        response[
            "Access-Control-Expose-Headers"
        ] = (
            "Content-Disposition, "
            "X-Catnime-Filename, "
            "X-Catnime-Width, "
            "X-Catnime-Height"
        )


        response[
            "X-Catnime-Filename"
        ] = filename


        response[
            "X-Catnime-Width"
        ] = str(target_w)


        response[
            "X-Catnime-Height"
        ] = str(target_h)


        return response


    except Exception as exc:

        print(
            "CATNIME UPSCALE ERROR:",
            repr(exc)
        )

        return JsonResponse(
            {
                "error":
                f"Falha no processamento: {exc}"
            },
            status=500
        )
