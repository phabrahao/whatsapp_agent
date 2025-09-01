from Crypto.Cipher import AES
import hashlib
import hmac
import base64
import requests
from PIL import Image
from io import BytesIO

def decrypt_image(url, media_key):
    # Download encrypted data
    data = requests.get(url).content
    
    # Decode media key and expand with proper HKDF
    key = base64.b64decode(media_key)
    key = hmac.new(b"\0"*32, key, hashlib.sha256).digest()
    
    # HKDF expansion for 112 bytes
    keyStream = b""
    keyBlock = b""
    blockIndex = 1
    while len(keyStream) < 112:
        keyBlock = hmac.new(key, keyBlock + b"WhatsApp Image Keys" + chr(blockIndex).encode(), hashlib.sha256).digest()
        blockIndex += 1
        keyStream += keyBlock
    
    # Extract IV and cipher key
    iv = keyStream[:16]
    cipher_key = keyStream[16:48]
    
    # Decrypt (remove MAC)
    cipher = AES.new(cipher_key, AES.MODE_CBC, iv)
    decrypted = cipher.decrypt(data[:-10])
    
    # Remove padding
    decrypted = decrypted[:-decrypted[-1]]
    
    return decrypted
