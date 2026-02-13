"""
API Routes Module
"""
from .device_routes import register_device_routes
from .reminder_routes import register_reminder_routes
from .sync_routes import register_sync_routes

__all__ = ['register_device_routes', 'register_reminder_routes', 'register_sync_routes']
