# StreamDrop 🌊

StreamDrop is a massive, lightning-fast, unlimited file-sharing web application built with Django and vanilla JavaScript. It eliminates the cloud-storage middleman, allowing devices to pair via a 6-digit PIN to seamlessly stream and drop large files directly between devices across the globe.

### 🚀 Live Demo Network
The server is actively bridging globally via Cloudflare Zero Trust Edge:
👉 **[https://pushing-innocent-ratings-time.trycloudflare.com](https://pushing-innocent-ratings-time.trycloudflare.com)**

### ✨ Features
* **Infinite File Sizes:** Safely share massive 2GB, 10GB, or even 50GB unthrottled files because files temporarily stream directly through the physical host PC disk instead of limited cloud-memory containers.
* **Classic Radar UX:** Mimics the gorgeous scanning "ShareIt/Softonic" retro radar aesthetics using custom CSS. Senders shoot out waves, and receiving devices float on screen when connected.
* **Serverless Front-end Connectivity:** Just type the 6 digit code into a phone, tablet, or another network, and the devices will securely bridge instantly.
* **Native Chunk Stream Support:** Handles HTML5 HTTP Range mechanics organically so the receiver can instantly start watching a movie / playing audio immediately before it finishes downloading!

### 💻 How to Run Locally

If the Cloudflare tunnel is not running, you can easily host this application entirely from your local machine (across your local Wi-Fi).

1. **Install Requirements:** Make sure you have Python 3 installed. 
   *(Django and Django REST Framework must be installed).*
   ```bash
   pip install django djangorestframework
   ```

2. **Run Migrations:** 
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

3. **Start the Production Terminal:** Run the server explicitly on `0.0.0.0` so other devices on your Wi-Fi network can detect it!
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

4. **Connect Devices:** Open `http://localhost:8000` on your PC, hit SEND, then open your Phone's web browser, type your PC's IP address (e.g., `http://192.168.1.5:8000`), hit RECEIVE, and begin dropping files!
