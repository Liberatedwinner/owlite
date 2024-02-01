import json
from pathlib import Path
from typing import Optional

from . import BaseURLs, ClassDecoder, ClassEncoder, Device, DeviceManager, Tokens, owlite_cache_dir, read_text
from .logger import log


class OwLiteSettings:
    """Handles OwLite settings including token management.

    OwLiteSettings manages tokens and URLs within the OwLite system.
    It provides methods to retrieve and store tokens for authentication.

    Attributes:
        path_tokens (Path): Path to store token information.
        path_url (Path): Path to store URL information.
    """

    def __init__(self) -> None:
        """Initialize OwLite settings.

        Initialize paths for OwLite cache directory to store tokens and URLs.
        """
        Path(owlite_cache_dir).mkdir(parents=True, exist_ok=True)

        self.tokens_cache = Path(owlite_cache_dir) / "tokens"
        self.devices_cache = Path(owlite_cache_dir) / "devices"
        self.connected_cache = Path(owlite_cache_dir) / "connected"
        self.urls_cache = Path(owlite_cache_dir) / "urls"

    @property
    def tokens(self) -> Optional[Tokens]:
        """Retrieves tokens or None if they don't exist.

        Returns:
            Optional[Tokens]: An instance of Tokens representing the access token and refresh token,
            or None if the tokens don't exist.
        """
        read_tokens = read_text(self.tokens_cache)
        if not read_tokens:
            return None
        return json.loads(read_tokens, cls=ClassDecoder)

    @tokens.setter
    def tokens(self, new_tokens: Optional[Tokens]) -> None:
        """Sets new tokens or removes existing tokens.

        Args:
            new_tokens (Optional[Tokens]): An instance of Tokens representing the new access token and refresh token.
            If None, existing tokens will be removed.
        """
        if new_tokens:
            self.tokens_cache.write_text(json.dumps(new_tokens, cls=ClassEncoder), encoding="utf-8")
        else:
            self.tokens_cache.unlink(missing_ok=True)

    @property
    def managers(self) -> dict[str, DeviceManager]:
        """Retrieves the device manager dictionary.

        Returns:
            dict[str, DeviceManager]: Device manager dictionary,
        """

        def _backward_compatibility(cached_managers: dict) -> dict:
            cached_managers.pop("DEFAULT", None)
            cached_managers.pop("NEST", None)
            for key, value in cached_managers.items():
                if isinstance(value, str):
                    new_value = DeviceManager(name=key, url=value)
                    cached_managers[key] = new_value
            self.devices_cache.write_text(json.dumps(cached_managers, cls=ClassEncoder), encoding="utf-8")
            return cached_managers

        default_manager = DeviceManager("NEST", self.base_url.NEST)
        registered_managers = {"NEST": default_manager}

        cache_content = read_text(self.devices_cache)
        if cache_content is None:
            return registered_managers

        cached_managers: dict[str, DeviceManager] = json.loads(cache_content, cls=ClassDecoder)
        cached_managers = _backward_compatibility(cached_managers)
        assert cached_managers
        registered_managers.update(cached_managers)
        return registered_managers

    def add_manager(self, manager: DeviceManager) -> None:
        """Adds new device to the cache

        Args:
            manager (DeviceManager): a new manager
        """
        manager_dict = self.managers
        manager_dict[manager.name] = manager
        manager_dict.pop("NEST")
        self.devices_cache.write_text(json.dumps(manager_dict, cls=ClassEncoder), encoding="utf-8")

    def remove_manager(self, name: str) -> None:
        """Removes an existing device manager from the cache

        Args:
            name (str): the name of the manager to remove
        """
        manager_dict = self.managers
        manager_dict.pop(name, None)
        manager_dict.pop("NEST")
        if bool(manager_dict):
            self.devices_cache.write_text(json.dumps(manager_dict, cls=ClassEncoder), encoding="utf-8")
        else:
            self.devices_cache.unlink(missing_ok=True)

    @property
    def connected_device(self) -> Optional[Device]:
        """Retrieves the connected device.

        Returns:
            Device, optional: An instance representing the device manager's name, url and selected device,
            or None if no device is selected.
        """
        connected_device = read_text(self.connected_cache)
        if connected_device:
            device = json.loads(connected_device, cls=ClassDecoder)
            if not isinstance(device, Device):
                log.warning("Your device connection is outdated. Please retry `owlite device connect --name (name)`")
                self.connected_device = None
            return device
        return None

    @connected_device.setter
    def connected_device(self, device: Optional[Device] = None) -> None:
        """Connects to the device manager and selects a device or deletes a device setting from storage.

        Does not fail if the device does not exist.

        Args:
            device (Device): The instance representing the device manager's name, url, and device to connect.
        """
        if device:
            self.connected_cache.write_text(json.dumps(device, cls=ClassEncoder), encoding="utf-8")
        else:
            self.connected_cache.unlink(missing_ok=True)

    @property
    def base_url(self) -> BaseURLs:
        """Retrieves base URLs.

        Returns the base URLs including FRONT, MAIN, and DOVE.
        If no custom URLs are set, it defaults to OwLite base URLs.

        Returns:
            BaseURLs: an instance of BaseURLs.
        """
        base_urls = read_text(self.urls_cache)
        if not base_urls:
            return BaseURLs()
        return json.loads(base_urls, cls=ClassDecoder)

    @base_url.setter
    def base_url(self, base_urls: BaseURLs) -> None:
        """Sets or removes custom base URLs.

        Args:
            base_urls (BaseURLs): An instance of BaseURLs to set or remove custom base URLs.

        Raises:
            ValueError: If the provided 'base_urls' instance is invalid or incomplete.
        """

        self.urls_cache.write_text(json.dumps(base_urls, cls=ClassEncoder))


OWLITE_SETTINGS = OwLiteSettings()
