# The future is now!
import uuid
import pickle
import face_recognition
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.files.storage import default_storage
import os
from django.conf import settings
from .models import RegisteredFaces


class InvalidImageException(Exception):
    pass


def save_image(request):
    img = request.FILES['base_image']
    img_extension = os.path.splitext(img.name)[-1]
    # return path to saved image
    img_path = settings.MEDIA_URL + request.data.get('identification_number') + img_extension
    default_storage.save(settings.MEDIA_URL + request.data.get('identification_number') + img_extension, img)

    return img_path


def save_base_image(request, encoding):
    img_path = save_image(request)
    face = RegisteredFaces()
    face.identification_number = request.data.get('identification_number')
    face.image_encoding = pickle.dumps(encoding.tolist(), protocol=2)
    face.image_path = img_path
    face.save()


def get_image_details(identification_number):
    try:
        image = RegisteredFaces.objects.get(identification_number=identification_number)
    except RegisteredFaces.DoesNotExist:
        image = None

    return image


def compare_images(self, *args, **kwargs):
    request = kwargs.get("request")
    image = get_image_details(kwargs.get('request').data.get('identification_number'))

    if image is None:

        if 'base_image' not in request.FILES:
            return "MISSING BASE IMAGE"

        base_image_file = kwargs.get("request").FILES['base_image']
        base_face = face_recognition.load_image_file(base_image_file)
        base_face_loc = face_recognition.face_locations(base_face)

        if len(base_face_loc) != 1:
            return "MISSING FACE IN BASE IMAGE"

        base_face_encoding = face_recognition.face_encodings(base_face)[0]
        save_base_image(kwargs.get("request"), base_face_encoding)
    else:
        base_face_encoding = pickle.loads(image.image_encoding)

    current_image_file = kwargs.get("request").FILES['current_image']
    current_face = face_recognition.load_image_file(current_image_file)
    current_face_loc = face_recognition.face_locations(current_face)
    if len(current_face_loc) != 1:
        return "MISSING FACE IN CURRENT IMAGE"
    current_face_encoding = face_recognition.face_encodings(current_face)[0]

    results = face_recognition.compare_faces([base_face_encoding], current_face_encoding, 0.4)

    return results[0]


class Image(APIView):

    def post(self, request, *args, **kwargs):

        if 'identification_number' not in request.data:
            return Response({"status": "Failed", "message": "Identification Number Missing", "code": "01"},
                            status=status.HTTP_400_BAD_REQUEST)

        if 'current_image' not in request.FILES:
            return Response({"status": "Failed", "message": "Current Image Missing", "code": "02"},
                            status=status.HTTP_400_BAD_REQUEST)

        result = compare_images(self, request=request)
        if result == 'MISSING BASE IMAGE':
            return Response({"status": "Failed", "message": "Base Image Missing", "code": "03"},
                            status=status.HTTP_400_BAD_REQUEST)
        elif result == 'MISSING FACE IN BASE IMAGE':
            return Response({"status": "Failed", "message": "Missing Face In Base Image", "code": "04"},
                            status=status.HTTP_400_BAD_REQUEST)
        elif result == 'MISSING FACE IN CURRENT IMAGE':
            return Response({"status": "Failed", "message": "Missing Face In Current Image", "code": "05"},
                            status=status.HTTP_400_BAD_REQUEST)

        return Response({"success": result}, status=status.HTTP_202_ACCEPTED)
