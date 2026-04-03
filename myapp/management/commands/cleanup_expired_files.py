from django.core.management.base import BaseCommand
import os
import time
from django.conf import settings
from django.core.cache import cache

class Command(BaseCommand):
    help = 'Cleans up expired files from the upload directory'

    def handle(self, *args, **kwargs):
        media_dir = settings.MEDIA_ROOT
        
        if not os.path.exists(media_dir):
            self.stdout.write("Media directory does not exist. Nothing to do.")
            return

        current_time = time.time()
        deleted_count = 0

        for filename in os.listdir(media_dir):
            file_path = os.path.join(media_dir, filename)
            
            # Skip directories
            if not os.path.isfile(file_path):
                continue

            # Check if this file has a cache entry
            # Our cache keys are file_meta_{file_id}
            # The filename is the file_id
            cache_key = f"file_meta_{filename}"
            metadata = cache.get(cache_key)

            if not metadata:
                # Cache entry doesn't exist (expired or deleted).
                # To prevent race conditions (file created but cache not set yet),
                # we only delete if the file is older than 1 hour.
                # However, if we want strict deletion, maybe the TTL passed.
                # Let's say if file is older than 2 hours.
                file_age = current_time - os.path.getmtime(file_path)
                if file_age > 7200: # 2 hours
                    os.remove(file_path)
                    deleted_count += 1
                    self.stdout.write(self.style.SUCCESS(f'Deleted expired file: {filename}'))

        self.stdout.write(self.style.SUCCESS(f'Successfully deleted {deleted_count} expired files.'))
