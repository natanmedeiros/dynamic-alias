"""
Cache Encryption Module

Rules:
    1.2.28: If cache contains "_crypt", data was encrypted with machine GUID/ID
    1.2.29: If "_crypt" does not exist and data exists, encrypt and replace

Uses machine-specific identifier for encryption:
    - Windows: HKLM\\SOFTWARE\\Microsoft\\Cryptography\\MachineGuid
    - Linux: /etc/machine-id
    - macOS: IOPlatformUUID
"""
import os
import platform
import subprocess
import base64
import json
from hashlib import pbkdf2_hmac
from typing import Dict, Any

# Use cryptography library for AES encryption
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


# Salt for key derivation (fixed for deterministic keys)
KEY_DERIVATION_SALT = b"dynamic-alias-cache-encryption-v1"
KEY_DERIVATION_ITERATIONS = 100000


def get_machine_id() -> str:
    """
    Get unique machine identifier (cross-platform).
    
    Returns:
        Machine-specific unique identifier string.
        Falls back to hostname + username if platform-specific ID unavailable.
    """
    system = platform.system()
    
    try:
        if system == "Windows":
            return _get_windows_machine_guid()
        elif system == "Linux":
            return _get_linux_machine_id()
        elif system == "Darwin":
            return _get_macos_machine_id()
        else:
            # Unknown platform, use fallback
            return _get_fallback_machine_id()
    except RuntimeError:
        # Platform-specific method failed, use fallback
        return _get_fallback_machine_id()


def _get_fallback_machine_id() -> str:
    """
    Fallback machine ID using hostname and username.
    Used in CI/container environments where platform-specific IDs aren't available.
    
    NOTE: This is less secure than platform-specific IDs but allows the 
    application to work in CI environments.
    """
    import socket
    import getpass
    
    try:
        hostname = socket.gethostname()
    except Exception:
        hostname = "unknown-host"
    
    try:
        username = getpass.getuser()
    except Exception:
        username = "unknown-user"
    
    # Combine hostname + username as a pseudo-unique identifier
    fallback_id = f"fallback:{hostname}:{username}"
    return fallback_id


def _get_windows_machine_guid() -> str:
    """Get Windows MachineGuid from registry."""
    import winreg
    try:
        reg_path = r"SOFTWARE\Microsoft\Cryptography"
        reg_key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, 
            reg_path,
            0,
            winreg.KEY_READ | winreg.KEY_WOW64_64KEY
        )
        machine_guid, _ = winreg.QueryValueEx(reg_key, "MachineGuid")
        winreg.CloseKey(reg_key)
        return machine_guid
    except Exception as e:
        raise RuntimeError(f"Failed to get Windows MachineGuid: {e}")


def _get_linux_machine_id() -> str:
    """Get Linux machine-id from /etc/machine-id or /var/lib/dbus/machine-id."""
    paths = ["/etc/machine-id", "/var/lib/dbus/machine-id"]
    
    for path in paths:
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    machine_id = f.read().strip()
                    if machine_id:
                        return machine_id
            except Exception:
                continue
    
    raise RuntimeError("Failed to get Linux machine-id: file not found or empty")


def _get_macos_machine_id() -> str:
    """Get macOS IOPlatformUUID via ioreg."""
    try:
        result = subprocess.run(
            ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        for line in result.stdout.split("\n"):
            if "IOPlatformUUID" in line:
                # Extract UUID from line like: "IOPlatformUUID" = "XXXXXXXX-XXXX-..."
                parts = line.split('"')
                if len(parts) >= 4:
                    return parts[-2]
        
        raise RuntimeError("IOPlatformUUID not found in ioreg output")
    except subprocess.TimeoutExpired:
        raise RuntimeError("Timeout getting macOS IOPlatformUUID")
    except Exception as e:
        raise RuntimeError(f"Failed to get macOS IOPlatformUUID: {e}")


def derive_key(machine_id: str) -> bytes:
    """
    Derive a 256-bit AES key from machine ID using PBKDF2.
    
    Args:
        machine_id: Machine-specific identifier string.
        
    Returns:
        32-byte key suitable for AES-256.
    """
    return pbkdf2_hmac(
        'sha256',
        machine_id.encode('utf-8'),
        KEY_DERIVATION_SALT,
        KEY_DERIVATION_ITERATIONS,
        dklen=32  # 256 bits for AES-256
    )


def _get_encryption_key() -> bytes:
    """Get encryption key derived from machine ID."""
    machine_id = get_machine_id()
    return derive_key(machine_id)


def encrypt_data(data: Dict[str, Any]) -> str:
    """
    Encrypt dictionary data using AES-256-GCM.
    
    Args:
        data: Dictionary to encrypt.
        
    Returns:
        Base64-encoded encrypted string (iv + tag + ciphertext).
    """
    key = _get_encryption_key()
    
    # Convert dict to JSON bytes
    plaintext = json.dumps(data, ensure_ascii=False).encode('utf-8')
    
    # Generate random IV (12 bytes for GCM)
    iv = os.urandom(12)
    
    # Encrypt using AES-256-GCM
    cipher = Cipher(
        algorithms.AES(key),
        modes.GCM(iv),
        backend=default_backend()
    )
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(plaintext) + encryptor.finalize()
    
    # Combine IV (12) + tag (16) + ciphertext
    encrypted = iv + encryptor.tag + ciphertext
    
    # Return as base64
    return base64.b64encode(encrypted).decode('ascii')


def decrypt_data(encrypted: str) -> Dict[str, Any]:
    """
    Decrypt base64-encoded encrypted string to dictionary.
    
    Args:
        encrypted: Base64-encoded encrypted string.
        
    Returns:
        Decrypted dictionary.
        
    Raises:
        ValueError: If decryption fails (wrong key, corrupted data).
    """
    key = _get_encryption_key()
    
    try:
        # Decode from base64
        encrypted_bytes = base64.b64decode(encrypted)
        
        # Extract IV (12 bytes), tag (16 bytes), and ciphertext
        iv = encrypted_bytes[:12]
        tag = encrypted_bytes[12:28]
        ciphertext = encrypted_bytes[28:]
        
        # Decrypt using AES-256-GCM
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(iv, tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        
        # Parse JSON
        return json.loads(plaintext.decode('utf-8'))
        
    except Exception as e:
        raise ValueError(f"Failed to decrypt cache data: {e}")
