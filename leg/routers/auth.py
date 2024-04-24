from __future__ import annotations as _annotations

from typing import Annotated

from sqlmodel import Session
from fastapi import APIRouter, Depends, Header
from fastui import AnyComponent, FastUI, components as c
from fastui.events import AuthEvent, GoToEvent, PageEvent
from fastui.forms import fastui_form
from pydantic import BaseModel, EmailStr, Field, SecretStr

from DecodeTheBot.models.user import User

router = APIRouter()


async def get_user_auth(
    authorization: Annotated[str, Header()] = "", session: Session = Depends(get_session)
) -> User | None:
    try:
        token = authorization.split(" ", 1)[1]
    except IndexError:
        return None
    else:
        return await session.query(User).filter_by(token=token).first()


@router.get("/login", response_model=FastUI, response_model_exclude_none=True)
def auth_login(user: Annotated[str | None, Depends(get_user_auth)]) -> list[AnyComponent]:
    if user is None:
        return fast_ui_default_page(
            c.Paragraph(
                text=(
                    "This is a very simple demo of authentication, "
                    'here you can "login" with any email address and password.'
                )
            ),
            c.Heading(text="Login"),
            c.ModelForm(model=LoginForm, submit_url="/api/auth/login"),
            title="Authentication",
        )
    else:
        return [c.FireEvent(event=GoToEvent(url="/auth/profile"))]


class LoginForm(BaseModel):
    email: EmailStr = Field(title="Email Address", description="Enter whatever value you like")
    password: SecretStr = Field(
        title="Password",
        description="Enter whatever value you like, password is not checked",
        json_schema_extra={"autocomplete": "current-password"},
    )


@router.post("/login", response_model=FastUI, response_model_exclude_none=True)
async def login_form_post(form: Annotated[LoginForm, fastui_form(LoginForm)]) -> list[AnyComponent]:
    token = await create_user(form.email)
    return [c.FireEvent(event=AuthEvent(token=token, url="/auth/profile"))]


@router.get("/profile", response_model=FastUI, response_model_exclude_none=True)
async def profile(user: Annotated[gurupod.models.user.User | None, Depends(get_user_auth)]) -> list[AnyComponent]:
    if user is None:
        return [c.FireEvent(event=GoToEvent(url="/auth/login"))]
    else:
        # active_count = await count_users()
        return fast_ui_default_page(
            c.Paragraph(text=f'You are logged in as "{user.email}", XXXXXX active users right now.'),
            c.Button(text="Logout", on_click=PageEvent(name="submit-form")),
            c.Form(
                submit_url="/api/auth/logout",
                form_fields=[c.FormFieldInput(name="test", title="", initial="data", html_type="hidden")],
                footer=[],
                submit_trigger=PageEvent(name="submit-form"),
            ),
            title="Authentication",
        )


@router.post("/logout", response_model=FastUI, response_model_exclude_none=True)
async def logout_form_post(
    user: Annotated[gurupod.models.user.User | None, Depends(get_user_auth)],
) -> list[AnyComponent]:
    # if user is not None:
    #     await db.delete_user(user)
    return [c.FireEvent(event=AuthEvent(token=False, url="/auth/login"))]
