import json
import os

import paramiko
from platformdirs import user_data_dir


class SSHKeyManager:
    def __init__(self, app_name="SSHKeyManager"):
        # Get the user data directory path for saving keys
        self.key_dir = user_data_dir(app_name, "meowmeowahr")
        os.makedirs(self.key_dir, exist_ok=True)

    def generate_key(self, key_name):
        """Generates an SSH key and saves it with the given key_name."""
        private_key = paramiko.RSAKey.generate(2048)
        public_key = private_key.get_base64()

        # Save private key in a file
        private_key_path = os.path.join(self.key_dir, f"{key_name}_private.key")
        private_key.write_private_key_file(private_key_path)

        # Save the public key in a separate file (optional)
        public_key_path = os.path.join(self.key_dir, f"{key_name}_public.key")
        with open(public_key_path, "w") as public_key_file:
            public_key_file.write(f"ssh-rsa {public_key}")

        # Save key information for future use or removal
        self._save_key_info(key_name, private_key_path, public_key_path)

        return private_key_path, public_key_path

    def remove_key(self, key_name):
        """Removes the key pair associated with the given key_name.

        Args:
            key_name (_type_): Name of the SSH key

        Returns:
            bool: Was the key successfully removed
        """
        key_info = self._load_key_info()
        if key_name in key_info:
            private_key_path, public_key_path = key_info[key_name]
            if os.path.exists(private_key_path):
                os.remove(private_key_path)
            if os.path.exists(public_key_path):
                os.remove(public_key_path)
            key_info.pop(key_name)
            self._save_key_info(key_name=None, data=key_info)
            return True
        return False

    def _save_key_info(self, key_name, private_key_path=None, public_key_path=None, data=None):
        """Saves or updates key pair info to a local file."""
        key_info_file = os.path.join(self.key_dir, "key_info.json")
        if os.path.exists(key_info_file):
            with open(key_info_file, "rb") as f:
                key_info = json.load(f)
        else:
            key_info = {}

        if key_name:
            key_info[key_name] = (private_key_path, public_key_path)
        elif data is not None:
            key_info = data

        with open(key_info_file, "w") as f:
            json.dump(key_info, f)

    def _load_key_info(self):
        """Loads key pair info from a local file."""
        key_info_file = os.path.join(self.key_dir, "key_info.json")
        if os.path.exists(key_info_file):
            with open(key_info_file, "rb") as f:
                return json.load(f)
        return {}

    def list_keys(self):
        """Lists all key names that are available in the key manager."""
        return self._load_key_info()
