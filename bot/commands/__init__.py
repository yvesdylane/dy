from bot.commands.admin import admin_handlers
from bot.commands.views import views_handlers
from bot.commands.info import info_handlers
from bot.commands.profile import profile_handlers
from bot.commands.tasks import tasks_handlers
from bot.commands.leave import leave_handlers
from bot.commands.link import link_handlers
from bot.commands.attendance import attendance_handlers
from bot.commands.eval import eval_handlers
from bot.commands.export import export_handlers

handlers = (
    admin_handlers
    + views_handlers
    + info_handlers
    + profile_handlers
    + tasks_handlers
    + leave_handlers
    + link_handlers
    + attendance_handlers
    + eval_handlers
    + export_handlers
)
