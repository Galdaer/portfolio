"""
Configuration Hot-Reload Monitor
Monitors configuration files for changes and automatically reloads them
"""

import time
from collections.abc import Callable
from pathlib import Path

from core.infrastructure.healthcare_logger import get_healthcare_logger

logger = get_healthcare_logger("config.monitor")

# Try to import watchdog for file system monitoring
try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
    WATCHDOG_AVAILABLE = True
except ImportError:
    logger.warning("watchdog not available - file system monitoring disabled")
    WATCHDOG_AVAILABLE = False

    # Create dummy classes for fallback
    class FileSystemEventHandler:
        pass

    class Observer:
        def schedule(self, *args, **kwargs):
            pass
        def start(self):
            pass
        def stop(self):
            pass
        def join(self):
            pass


class ConfigurationFileHandler(FileSystemEventHandler):
    """Handle configuration file change events"""

    def __init__(self, reload_callbacks: dict[str, Callable]):
        super().__init__()
        self.reload_callbacks = reload_callbacks
        self.last_modified = {}
        self.cooldown_period = 1.0  # Prevent rapid-fire reloads

    def on_modified(self, event):
        """Handle file modification events"""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Check if this is a configuration file we care about
        if file_path.suffix in [".yml", ".yaml"] and file_path.stem in self.reload_callbacks:
            # Implement cooldown to prevent rapid reloads
            current_time = time.time()
            last_mod_time = self.last_modified.get(str(file_path), 0)

            if current_time - last_mod_time > self.cooldown_period:
                self.last_modified[str(file_path)] = current_time
                self.reload_configuration(file_path)

    def reload_configuration(self, file_path: Path):
        """Reload configuration for a specific file"""
        try:
            config_name = file_path.stem

            if config_name in self.reload_callbacks:
                callback = self.reload_callbacks[config_name]
                callback()
                logger.info(f"Hot-reloaded configuration: {config_name}")
            else:
                logger.warning(f"No reload callback for configuration: {config_name}")

        except Exception as e:
            logger.exception(f"Failed to hot-reload configuration {file_path}: {e}")


class ConfigurationMonitor:
    """Monitor configuration files and provide hot-reload functionality"""

    def __init__(self, config_directory: str | Path):
        self.config_directory = Path(config_directory)
        self.observer = None
        self.reload_callbacks = {}
        self.is_monitoring = False

    def register_reload_callback(self, config_name: str, callback: Callable):
        """Register a callback to be called when a specific config file changes"""
        self.reload_callbacks[config_name] = callback
        logger.info(f"Registered reload callback for {config_name}")

    def start_monitoring(self):
        """Start monitoring configuration files for changes"""
        if self.is_monitoring:
            logger.warning("Configuration monitoring is already running")
            return

        if not WATCHDOG_AVAILABLE:
            logger.info("File system monitoring disabled (watchdog not available)")
            logger.info("Configuration changes will require manual reload or service restart")
            return

        if not self.config_directory.exists():
            logger.error(f"Configuration directory does not exist: {self.config_directory}")
            return

        try:
            # Create file system event handler
            event_handler = ConfigurationFileHandler(self.reload_callbacks)

            # Create and start observer
            self.observer = Observer()
            self.observer.schedule(
                event_handler,
                str(self.config_directory),
                recursive=False,
            )
            self.observer.start()
            self.is_monitoring = True

            logger.info(f"Started configuration monitoring for: {self.config_directory}")

        except Exception as e:
            logger.exception(f"Failed to start configuration monitoring: {e}")
            raise

    def stop_monitoring(self):
        """Stop monitoring configuration files"""
        if not self.is_monitoring:
            return

        try:
            if self.observer:
                self.observer.stop()
                self.observer.join()
                self.observer = None

            self.is_monitoring = False
            logger.info("Stopped configuration monitoring")

        except Exception as e:
            logger.exception(f"Error stopping configuration monitoring: {e}")

    def reload_all_configurations(self):
        """Manually reload all registered configurations"""
        logger.info("Manually reloading all configurations")

        for config_name, callback in self.reload_callbacks.items():
            try:
                callback()
                logger.info(f"Reloaded configuration: {config_name}")
            except Exception as e:
                logger.exception(f"Failed to reload configuration {config_name}: {e}")


class HotReloadService:
    """Service for managing configuration hot-reload functionality"""

    def __init__(self):
        self.monitor = None
        self.reload_handlers = {}

    async def initialize(self, config_directory: str | Path):
        """Initialize the hot-reload service"""
        try:
            self.monitor = ConfigurationMonitor(config_directory)

            # Register default reload handlers
            await self.register_default_handlers()

            # Start monitoring
            self.monitor.start_monitoring()

            logger.info("Hot-reload service initialized successfully")

        except Exception as e:
            logger.exception(f"Failed to initialize hot-reload service: {e}")
            raise

    async def register_default_handlers(self):
        """Register default configuration reload handlers"""

        # UI Configuration reload
        def reload_ui_config():
            try:
                from config.ui_config_loader import reload_ui_config
                reload_ui_config()
                logger.info("UI configuration reloaded")
            except Exception as e:
                logger.exception(f"Failed to reload UI configuration: {e}")

        # Transcription Configuration reload
        def reload_transcription_config():
            try:
                from config.transcription_config_loader import reload_transcription_config
                reload_transcription_config()
                logger.info("Transcription configuration reloaded")
            except Exception as e:
                logger.exception(f"Failed to reload transcription configuration: {e}")

        # Medical Search Configuration reload
        def reload_medical_search_config():
            try:
                # Medical search config would need similar reload functionality
                logger.info("Medical search configuration reload requested")
            except Exception as e:
                logger.exception(f"Failed to reload medical search configuration: {e}")

        # Register callbacks
        self.monitor.register_reload_callback("ui_config", reload_ui_config)
        self.monitor.register_reload_callback("transcription_config", reload_transcription_config)
        self.monitor.register_reload_callback("medical_search_config", reload_medical_search_config)

    def register_custom_handler(self, config_name: str, handler: Callable):
        """Register a custom configuration reload handler"""
        if self.monitor:
            self.monitor.register_reload_callback(config_name, handler)
        else:
            # Store for later registration
            self.reload_handlers[config_name] = handler

    async def shutdown(self):
        """Shutdown the hot-reload service"""
        try:
            if self.monitor:
                self.monitor.stop_monitoring()
                self.monitor = None

            logger.info("Hot-reload service shutdown complete")

        except Exception as e:
            logger.exception(f"Error during hot-reload service shutdown: {e}")

    def force_reload_all(self):
        """Force reload all configurations"""
        if self.monitor:
            self.monitor.reload_all_configurations()
        else:
            logger.warning("Hot-reload service not initialized")


# Global hot-reload service instance
hot_reload_service = HotReloadService()


async def initialize_hot_reload(config_directory: str | Path):
    """Initialize global hot-reload service"""
    await hot_reload_service.initialize(config_directory)


async def shutdown_hot_reload():
    """Shutdown global hot-reload service"""
    await hot_reload_service.shutdown()


def register_config_reload_handler(config_name: str, handler: Callable):
    """Register a configuration reload handler"""
    hot_reload_service.register_custom_handler(config_name, handler)


def force_reload_configurations():
    """Force reload all configurations"""
    hot_reload_service.force_reload_all()
