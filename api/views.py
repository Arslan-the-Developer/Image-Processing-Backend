# views.py
import uuid
import base64
from io import BytesIO
import numpy as np

from PIL import Image
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import matplotlib.colors as mcolors


CACHE_TIMEOUT = 60 * 10  # 10 minutes


class UploadOriginalImage(APIView):

    def post(self, request):

        image_base64 = request.data.get("image_base64")

        if not image_base64:
            return Response(
                {"error": "image_base64 is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            img = base64_to_image(image_base64)
            img = img.convert("RGB")
        except ValueError:
            return Response(
                {"error": "Invalid base64 image"},
                status=status.HTTP_400_BAD_REQUEST
            )

        image_id = str(uuid.uuid4())

        # Cache original image
        cache.set(f"original:{image_id}", img, timeout=CACHE_TIMEOUT)

        return Response(
            {"image_id": image_id},
            status=status.HTTP_201_CREATED
        )




class ApplyImageAdjustments(APIView):

    def post(self, request):

        image_id = request.data.get("image_id")

        if not image_id:
            return Response(
                {"error": "image_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Load original image from cache
        original_img = cache.get(f"original:{image_id}")

        if original_img is None:
            return Response(
                {"error": "Image expired or not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Read adjustment values
        brightness = float(request.data.get("brightness", 0))
        contrast = float(request.data.get("contrast", 0))
        saturation = float(request.data.get("saturation", 0))
        gamma = float(request.data.get("gamma", 1.0))

        # Always start from ORIGINAL
        processed_img = original_img.copy()
        processed_img = apply_adjustments(
            processed_img,
            brightness=brightness,
            contrast=contrast,
            saturation=saturation,
            gamma=gamma
        )

        return Response(
            {
                "image": image_to_base64(processed_img)
            },
            status=status.HTTP_200_OK
        )




def base64_to_image(base64_string):
    """
    Convert a base64 string (with data:image/...) into a PIL Image.
    Raises ValueError if invalid.
    """
    if "," in base64_string:
        _, base64_data = base64_string.split(",", 1)
    else:
        base64_data = base64_string

    try:

        decoded = base64.b64decode(base64_data)

    except Exception:

        raise ValueError("Invalid base64 data")

    try:

        img = Image.open(BytesIO(decoded))
        img.verify()   # verify first
        img = Image.open(BytesIO(decoded))  # re-open after verify()
        return img
    
    except Exception:

        raise ValueError("Invalid image file")



def image_to_base64(pil_image, fmt="PNG"):
    """
    Convert a PIL Image to a Base64 data URL.
    """
    buffer = BytesIO()
    pil_image.save(buffer, format=fmt)
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return f"data:image/{fmt.lower()};base64,{encoded}"



def apply_adjustments(img, brightness=0, saturation=1, gamma=1.0, contrast=1):

    arr = np.array(img).astype(np.float32)

    # Brightness

    if brightness != 0:
        arr = np.clip(arr + float(brightness), 0, 255)

    
    if contrast != 1:
        
        arr = np.clip((arr - 128.0) * contrast + 128.0, 0, 255)

    # Gamma correction
    if gamma != 1.0:
        arr = np.clip(255 * ((arr / 255) ** (1 / gamma)), 0, 255)

    # Saturatoin
    if saturation != 0:
        
        hsv_array = mcolors.rgb_to_hsv(arr.astype(np.float32) / 255.0)
        hsv_array[:,:,1] = np.clip(hsv_array[:,:,1] * saturation, 0, 1)
        arr = mcolors.hsv_to_rgb(hsv_array)*255

    return Image.fromarray(arr.astype(np.uint8))
