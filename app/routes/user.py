from ast import literal_eval
from datetime import datetime

from fastapi import APIRouter, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt

from app.crud.user import get_user_by_email, get_user_by_username, create_user
from app.util.auth import SECRET_KEY, ALGORITHM, verify_password, create_access_token, create_refresh_token, \
    get_password_hash, auth_scheme, get_token_info

router = APIRouter(
    prefix="/users",
    tags=["users"]
)


@router.post("/login/")
async def login(email: str = Form(), password: str = Form()):
    user_info = await get_user_by_email(email)
    user_info_dict = dict(user_info)
    if user_info is None:
        raise HTTPException(status_code=404, detail="email is not found")

    if not verify_password(password, user_info.password):
        raise HTTPException(status_code=401, detail="password is wrong")

    del user_info_dict["password"]
    user_info_dict['created_at'] = str(datetime.now())

    token_info = get_token_info(user_info.email, user_info.username)
    access_token = create_access_token(token_info)
    refresh_token = create_refresh_token(token_info)

    return JSONResponse({"access_token": access_token, "refresh_token": refresh_token}, status_code=200)


@router.post('/signup')
async def sign_up(email: str = Form(), password: str = Form(), username: str = Form()):
    user_data = await get_user_by_email(email)

    if user_data:
        raise HTTPException(status_code=409, detail="user is already exists")

    user_data = await get_user_by_username(username)

    if user_data:
        raise HTTPException(status_code=409, detail="username is already exists")

    hashed_password = get_password_hash(password)
    await create_user(email=email, hashed_password=hashed_password, username=username,
                      created_at=datetime.now())

    token_info = get_token_info(email=email, username=username)
    access_token = create_access_token(token_info)
    refresh_token = create_refresh_token(token_info)

    return JSONResponse({"access_token": access_token, "refresh_token": refresh_token}, status_code=201)


@router.post("/refresh")
async def get_new_access_token(refresh_token: HTTPAuthorizationCredentials = Depends(auth_scheme)):
    try:
        user_info = jwt.decode(refresh_token.credentials, SECRET_KEY, ALGORITHM)
    except Exception as e:
        print(e)
        return HTTPException(status_code=500, detail="a")

    user_sub = literal_eval(user_info['sub'])
    email = user_sub['email']
    created_at = datetime.strptime(user_sub['created_at'], '%Y-%m-%d %H:%M:%S.%f')
    username = user_sub['username']
    now = datetime.now()

    token_info = get_token_info(email=email, username=username)

    if email is None:
        return HTTPException(status_code=401, detail="not unauthorized")

    if created_at > now:
        return HTTPException(status_code=401, detail="not unauthorized")
    else:
        return {"access_token": create_access_token(token_info)}
