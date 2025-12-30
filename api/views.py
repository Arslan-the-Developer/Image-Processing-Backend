# views.py
import uuid
import base64
from io import BytesIO
import numpy as np
import math

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




class ResizeImage(APIView):

    def post(self, request):

        print('Request Received.....')

        image_id = request.data.get("image_id",None)
        resize_scale = request.data.get("resize_scale",None)

        if not image_id:
            return Response(
                {"error": "image_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not resize_scale:
            return Response(
                {"error": "Resize Scale is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Load original image from cache
        original_img = cache.get(f"original:{image_id}")

        if original_img is None:
            return Response(
                {"error": "Image expired or not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Always start from ORIGINAL
        processed_img = original_img.copy()
        processed_img_array = np.array(processed_img)

        new_h = math.ceil(processed_img_array.shape[0] * float(resize_scale))
        new_w = math.ceil(processed_img_array.shape[1] * float(resize_scale))

        print('Now Resizing The Image.....')

        resized_image_array = bl_resize(processed_img_array, new_w=new_w, new_h=new_h)

        return Response(
            {
                "image_w": processed_img_array.shape[1],
                "image_h": processed_img_array.shape[0],
                "resize_scale": resize_scale,
                "new_image_w": math.ceil(processed_img_array.shape[1]*resize_scale),
                "new_image_h": math.ceil(processed_img_array.shape[0]*resize_scale),
                "image": image_to_base64(Image.fromarray(resized_image_array)),
            },
            status=status.HTTP_200_OK
        )




class ModifyGeometry(APIView):

    def post(self, request):

        print('Request Received.....')

        image_id = request.data.get("image_id",None)
        change_to_be_made = request.data.get("change_to_be_made",None)

        if not image_id:
            return Response(
                {"error": "image_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not change_to_be_made:
            return Response(
                {"error": "Resize Scale is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        print(change_to_be_made,type(change_to_be_made))


        # Load original image from cache
        original_img = cache.get(f"original:{image_id}")

        if original_img is None:
            return Response(
                {"error": "Image expired or not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Always start from ORIGINAL
        to_be_processed_img = original_img.copy()
        to_be_processed_img_array = np.array(to_be_processed_img)

        for op in change_to_be_made:
            
            to_be_processed_img_array = change_geometry(to_be_processed_img_array, op)

        if to_be_processed_img_array is None:
            
            return Response(
                {"error": "Invalid geometry operation"},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {
                "image": image_to_base64(Image.fromarray(to_be_processed_img_array)),
            },
            status=status.HTTP_200_OK
        )



class EdgeDetectionView(APIView):

    def post(self, request):

        image_id = request.data.get("image_id",None)

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

        # Always start from ORIGINAL
        to_be_processed_img = original_img.copy().convert('L')
        to_be_processed_img_array = np.array(to_be_processed_img)

        modified_image = sobel_edge_detection(to_be_processed_img_array)


        return Response(
            {
                "image": image_to_base64(modified_image),
            },
            status=status.HTTP_200_OK
        )




class ChannelAnalysisView(APIView):

    def post(self, request):

        image_id = request.data.get("image_id",None)

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

        # Always start from ORIGINAL
        to_be_processed_img = original_img.copy().convert('L')
        to_be_processed_img_array = np.array(to_be_processed_img)

        modified_image = sobel_edge_detection(to_be_processed_img_array)


        return Response(
            {
                "image": image_to_base64(modified_image),
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





def bl_resize(original_img, new_h, new_w):
    """
    Resize an image using Bilinear Interpolation.

    Parameters:
        original_img (numpy.ndarray): (H, W, C) image
        new_h (int): desired height
        new_w (int): desired width

    Returns:
        numpy.ndarray: resized image (new_h, new_w, C)
    """

    old_h, old_w, c = original_img.shape

    if new_h <= 0 or new_w <= 0:
        raise ValueError("new_h and new_w must be positive integers")

    # Create output image
    resized = np.zeros((new_h, new_w, c), dtype=np.float32)

    # Scaling factors
    h_scale = old_h / new_h
    w_scale = old_w / new_w

    for i in range(new_h):
        for j in range(new_w):

            # Map pixel centers
            x = (i + 0.5) * h_scale - 0.5
            y = (j + 0.5) * w_scale - 0.5

            # Neighbor pixel indices
            x0 = int(math.floor(x))
            y0 = int(math.floor(y))
            x1 = x0 + 1
            y1 = y0 + 1

            # Clamp indices
            x0 = max(0, min(x0, old_h - 1))
            x1 = max(0, min(x1, old_h - 1))
            y0 = max(0, min(y0, old_w - 1))
            y1 = max(0, min(y1, old_w - 1))

            # Distances
            dx = x - x0
            dy = y - y0

            # Four neighboring pixels
            p00 = original_img[x0, y0]
            p01 = original_img[x0, y1]
            p10 = original_img[x1, y0]
            p11 = original_img[x1, y1]

            # Bilinear interpolation
            top = p00 * (1 - dy) + p01 * dy
            bottom = p10 * (1 - dy) + p11 * dy
            pixel = top * (1 - dx) + bottom * dx

            resized[i, j] = pixel

    # Clip and convert to uint8
    resized = np.clip(resized, 0, 255)
    return resized.astype(np.uint8)




def change_geometry(original_array: np.ndarray, change: str) -> np.ndarray | None:

    operations = {
        'r': lambda x: np.rot90(x, k=1),
        '-r': lambda x: np.rot90(x, k=3),
        'vf': np.flipud,
        'hf': np.fliplr,
    }

    operation = operations.get(change)
    if not operation:
        return None

    return operation(original_array)




def sobel_edge_detection(grayscale_image_array):

    img_array = grayscale_image_array.astype(np.float32)

    # Define Sobel kernels
    sobel_x = np.array([[-1, 0, 1],
                        [-2, 0, 2],
                        [-1, 0, 1]], dtype=np.float32)

    sobel_y = np.array([[-1, -2, -1],
                        [0, 0, 0],
                        [1, 2, 1]], dtype=np.float32)

    # Apply convolution
    # Create padded image to handle borders during convolution
    padded_img = np.pad(img_array, 1, mode='edge')
    
    gradient_x = np.zeros_like(img_array)
    gradient_y = np.zeros_like(img_array)

    for i in range(img_array.shape[0]):
        for j in range(img_array.shape[1]):
            # Extract 3x3 window
            window = padded_img[i:i+3, j:j+3]
            gradient_x[i, j] = np.sum(window * sobel_x)
            gradient_y[i, j] = np.sum(window * sobel_y)

    # Calculate magnitude of the gradient
    magnitude = np.sqrt(gradient_x**2 + gradient_y**2)

    # Normalize to 0-255 and convert to uint8 for saving
    magnitude = (magnitude / magnitude.max()) * 255
    edge_image = Image.fromarray(magnitude.astype(np.uint8))

    return edge_image
