import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.config import settings
from app.firestore_client import create_if_absent, get_by_code
from app.middleware.auth import require_api_key
from app.models import CreateUrlRequest, UrlRecord
from app.utils.shortcode import generate_short_code

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/urls",
    tags=["urls"],
    dependencies=[Depends(require_api_key)]
)

MAX_COLLISION_RETRIES = 3


@router.post(
    "",
    response_model=UrlRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Create a short code for a long URL",
)
async def create_url(payload: CreateUrlRequest) -> UrlRecord:
    long_url = str(payload.long_url)

    for attempt in range(MAX_COLLISION_RETRIES):
        code = generate_short_code()
        record = UrlRecord.new(code=code, long_url=long_url)

        created = await create_if_absent(record)
        if created:
            logger.info("url created: code=%s", code)
            record.short_url = f"{settings.redirect_base_url.rstrip('/')}/{code}"
            return record

        logger.warning(
            "short code collision, retrying (attempt %d): code=%s",
            attempt + 1,
            code,
        )

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Could not generate a unique short code; please retry.",
    )


@router.get(
    "/{code}",
    response_model=UrlRecord,
    summary="Look up a URL record by its short code",
)
async def get_url(code: str) -> UrlRecord:
    record = await get_by_code(code)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Short code not found: {code}",
        )
    return record
