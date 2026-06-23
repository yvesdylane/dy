from bot.handlers.admin import admin_handlers
from bot.handlers.csv_export import csv_handlers
from bot.handlers.leave import leave_handlers
from bot.handlers.notes import notes_handlers
from bot.handlers.profile import profile_handlers
from bot.handlers.tasks import tasks_handlers
from bot.handlers.views import views_handlers

handlers = (
    admin_handlers
    + tasks_handlers
    + notes_handlers
    + profile_handlers
    + leave_handlers
    + views_handlers
    + csv_handlers
)
