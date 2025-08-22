from aiogram import Router
from aiogram_dialog import setup_dialogs

from .complaint import router as complaint_router
from .main import router as main_router
from .dealer import router as dealer_router
from .conditioner import router as conditioner_router

router = Router()
router.include_routers(
    complaint_router,
    main_router,
    dealer_router,
    conditioner_router,
)

setup_dialogs(router=router)
