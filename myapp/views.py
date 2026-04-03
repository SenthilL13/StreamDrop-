import os
import uuid
import mimetypes
import json
import logging
import qrcode
from io import BytesIO
from django.conf import settings
from django.core.cache import cache
from django.http import StreamingHttpResponse, HttpResponse, HttpResponseNotFound, JsonResponse
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from rest_framework import status
from wsgiref.util import FileWrapper
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

logger = logging.getLogger(__name__)

# Make sure media directory exists
if not os.path.exists(settings.MEDIA_ROOT):
    os.makedirs(settings.MEDIA_ROOT)

def index_view(request):
    return render(request, 'index.html')

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@method_decorator(csrf_exempt, name='dispatch')
class FileUploadView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request, *args, **kwargs):
        ip = get_client_ip(request)
        cache_key = f"upload_limit_{ip}"
        
        # Simple Rate Limiting: 100 uploads/hour
        upload_count = cache.get(cache_key, 0)
        if upload_count >= 100:
            return Response({"error": "Rate limit exceeded (100 uploads/hour)."}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        cache.set(cache_key, upload_count + 1, timeout=3600)
        
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response({"error": "No file parsed"}, status=status.HTTP_400_BAD_REQUEST)

        # Settings
        expiry_hours = int(request.data.get('expiry_hours', 24))
        if expiry_hours <= 0:
            expiry_hours = 24
            
        file_id = str(uuid.uuid4())
        file_path = os.path.join(settings.MEDIA_ROOT, file_id)
        
        # Save file directly to disk in chunks
        with open(file_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
                
        mime_type, _ = mimetypes.guess_type(uploaded_file.name)
        if not mime_type:
            mime_type = 'application/octet-stream'
            
        metadata = {
            'file_id': file_id,
            'filename': uploaded_file.name,
            'mime_type': mime_type,
            'size': os.path.getsize(file_path),
            'password': request.data.get('password', None),
            'file_path': file_path
        }
        
        # Save to Redis
        cache.set(f"file_meta_{file_id}", metadata, timeout=expiry_hours * 3600)
        
        # Build URLs
        stream_url = request.build_absolute_uri(f'/stream/{file_id}/')
        share_url = request.build_absolute_uri(f'/?f={file_id}')
        
        # Room Association
        room_pin = request.data.get('room_pin')
        if room_pin:
            room_data = cache.get(f"room_{room_pin}")
            if room_data:
                room_data['files'].append({
                    'file_id': file_id,
                    'filename': metadata['filename'],
                    'mime_type': metadata['mime_type'],
                    'size': metadata['size']
                })
                cache.set(f"room_{room_pin}", room_data, timeout=3600)
        
        return Response({
            'file_id': file_id,
            'stream_url': stream_url,
            'share_url': share_url,
            'metadata': {
                'filename': metadata['filename'],
                'size': metadata['size'],
                'mime_type': metadata['mime_type']
            }
        }, status=status.HTTP_201_CREATED)

class FileInfoView(APIView):
    def get(self, request, file_id):
        metadata = cache.get(f"file_meta_{file_id}")
        if not metadata:
            return Response({"error": "File not found or expired."}, status=status.HTTP_404_NOT_FOUND)
        
        # Omit internal path
        out_meta = {
            'filename': metadata['filename'],
            'size': metadata['size'],
            'mime_type': metadata['mime_type'],
        }
        return Response(out_meta)

def stream_video(request, path, content_type):
    range_header = request.META.get('HTTP_RANGE', '').strip()
    range_match = range_header.replace('bytes=', '').split('-')
    size = os.path.getsize(path)
    
    if range_match and range_match[0]:
        first_byte = int(range_match[0])
        try:
            last_byte = int(range_match[1]) if range_match[1] else size - 1
        except ValueError:
            last_byte = size - 1
            
        if last_byte >= size:
            last_byte = size - 1
            
        length = last_byte - first_byte + 1
        
        def file_iterator(file_path, offset=0, bytes_to_read=None, chunk_size=4096000): # 4MB chunks
            with open(file_path, 'rb') as f:
                f.seek(offset)
                remaining = bytes_to_read
                while remaining > 0:
                    read_size = min(chunk_size, remaining)
                    data = f.read(read_size)
                    if not data:
                        break
                    remaining -= len(data)
                    yield data
                    
        resp = StreamingHttpResponse(file_iterator(path, offset=first_byte, bytes_to_read=length), status=206, content_type=content_type)
        resp['Content-Length'] = str(length)
        resp['Content-Range'] = f'bytes {first_byte}-{last_byte}/{size}'
    else:
        # No range requested
        def file_iterator(file_path, chunk_size=4096000):
            with open(file_path, 'rb') as f:
                while True:
                    data = f.read(chunk_size)
                    if not data:
                        break
                    yield data

        resp = StreamingHttpResponse(file_iterator(path), content_type=content_type)
        resp['Content-Length'] = str(size)
        
    resp['Accept-Ranges'] = 'bytes'
    return resp

class FileStreamView(APIView):
    def get(self, request, file_id):
        metadata = cache.get(f"file_meta_{file_id}")
        if not metadata:
            return HttpResponseNotFound("File not found or has expired.")
            
        file_path = metadata['file_path']
        if not os.path.exists(file_path):
            return HttpResponseNotFound("File no longer exists on disk.")
            
        # Optional password protection check
        pw = request.query_params.get('password')
        if metadata.get('password') and pw != metadata['password']:
            return HttpResponse("Unauthorized. Password required.", status=401)
            
        response = stream_video(request, file_path, metadata['mime_type'])
        
        # Setting CDN-like caching headers
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Content-Disposition'] = f'inline; filename="{metadata["filename"]}"'
        
        return response

def qr_code_view(request, file_id):
    share_url = request.build_absolute_uri(f'/?f={file_id}')
    img = qrcode.make(share_url)
    
    buf = BytesIO()
    img.save(buf, format='PNG')
    image_stream = buf.getvalue()
    
    return HttpResponse(image_stream, content_type="image/png")

import random

@method_decorator(csrf_exempt, name='dispatch')
class CreateRoomView(APIView):
    def post(self, request):
        ip = get_client_ip(request)
        pin = str(random.randint(100000, 999999))
        room_data = {
            'pin': pin,
            'state': 'waiting',
            'files': []
        }
        cache.set(f"room_{pin}", room_data, timeout=3600)
        return Response({'pin': pin})

@method_decorator(csrf_exempt, name='dispatch')
class JoinRoomView(APIView):
    def post(self, request):
        pin = request.data.get('pin')
        room_data = cache.get(f"room_{pin}")
        if not room_data:
            return Response({'error': 'Invalid PIN'}, status=404)
        
        room_data['state'] = 'connected'
        cache.set(f"room_{pin}", room_data, timeout=3600)
        return Response({'status': 'connected'})

class RoomStatusView(APIView):
    def get(self, request, pin):
        room_data = cache.get(f"room_{pin}")
        if not room_data:
            return Response({'error': 'Room expired'}, status=404)
        return Response(room_data)