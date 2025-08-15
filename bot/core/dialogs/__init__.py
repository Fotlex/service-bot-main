from aiogram import Router
from aiogram_dialog import setup_dialogs

from .main import router as main_router
from .dealer import router as dealer_router
from .conditioner import router as conditioner_router
from .complaint import router as complaint_router

router = Router()
router.include_routers(
    main_router,
    dealer_router,
    conditioner_router,
    complaint_router
)

setup_dialogs(router=router)
