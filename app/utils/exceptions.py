# app/utils/exceptions.py
from fastapi import HTTPException, status


def not_found(entity: str = "Resource"):
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=f"{entity} not found"
    )


def forbidden(message="Forbidden"):
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)


def bad_request(message="Bad request"):
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


def unauthorized(message="Unauthorized"):
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)
