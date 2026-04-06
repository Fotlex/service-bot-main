from maxapi import Dispatcher

from . import complaint, conditioner, dealer, manuals, start


def setup_handlers(dp: Dispatcher):
    dp.include_routers(
        complaint.router,
        conditioner.router,
        dealer.router,
        manuals.router,
        start.router,
    )
