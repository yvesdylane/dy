from previouse.bot.handlers.admin import admin_handlers
from previouse.bot.handlers.csv_export import csv_handlers
from previouse.bot.handlers.leave import leave_handlers
from previouse.bot.handlers.notes import notes_handlers
from previouse.bot.handlers.profile import profile_handlers
from previouse.bot.handlers.tasks import tasks_handlers
from previouse.bot.handlers.views import views_handlers

handlers = (
    admin_handlers
    + tasks_handlers
    + notes_handlers
    + profile_handlers
    + leave_handlers
    + views_handlers
    + csv_handlers
)
