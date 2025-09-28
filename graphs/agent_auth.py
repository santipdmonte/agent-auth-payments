from langgraph.graph.message import MessagesState
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langgraph.types import interrupt
from langgraph.prebuilt import InjectedState
from typing import Annotated, Optional
from services.users_services import get_user_service
from fastapi import Depends
from services.tokens_service import get_token_service, TokenService
from utils.email_utlis import send_phone_number_verification_email
from database import get_db

db = get_db()

class State(MessagesState):
    remaining_steps: int
    phone_number: str | None = None

model = ChatOpenAI(model="gpt-5-mini")

prompt = """
Eres un asistente util para ayudar a un usuario.

Cuando el usuario te envie el primer mensaje, debes utilizar la tool "get_user_info" para obtener la información del usuario.

si el usuario no tiene una cuenta asociada, debes validar su email.
    - El usuario te proporcionara un email.
    - Tú debes utilizar la tool "send_email_verification_code" para enviar un codigo de verificación al email del usuario.
    - El usuario te proporcionara un codigo de verificación.
    - Debes utilizar la tool "verify_email_verification_code" para verificar si el codigo de verificación es valido.

"""

user_info = {
    "email": "santiagopedemonte02@gmail.com",
    "full_name": "Santiago Pedemonte",
    "given_name": "Santiago",
    "family_name": "Pedemonte",
    "current_balance": 1000000,
    "lasts_movements": [
        {
            "date": "2025-01-01",
            "amount": 1000000,
            "type": "deposit",
        },
        {
            "date": "2025-01-01",
            "amount": 1000000,
            "type": "withdraw",
        },
        {
            "date": "2025-01-01",
            "amount": 1000000,
            "type": "transfer",
        },
    ],
    "role": "user",
}

items = {
    "item1": {
        "name": "Item 1",
        "price": 1000000,
    },
    "item2": {
        "name": "Item 2",
        "price": 2000000,
    },
    "item3": {
        "name": "Item 3",
        "price": 3000000,
    },
}

cart_items = []


def send_email_verification_code(
    email: str,
):
    """Envía un código de verificación al email del usuario."""
    print(f"Sending email verification code to {email}")
    
    token_service = TokenService(db)
    code = token_service.create_phone_number_verification_code(data={"sub": email})
    send_phone_number_verification_email(email, code)

    return {"messages": "Email de verificacion enviado correctamente. Dile al usuario que debe verificar el codigo de verificacion."}


def verify_email_verification_code(code: str, phone_number: Annotated[str | None, InjectedState("phone_number")] = None):
    """Verifica si el código de verificación es válido."""

    token_service = TokenService(db)
    
    # TODO: get the email from the database with the phone number
    email = "santiagopedemonte02@gmail.com"
    validate_code = token_service.validate_phone_number_verification_code(email, code)
    if not validate_code:
        return {"messages": "Codigo de verificacion invalido"}

    return {"messages": f"Email de verificacion verificado correctamente. informacion del usuario: {user_info}"}


def get_user_info(
    phone_number: Annotated[str | None, InjectedState("phone_number")] = None, 
):
    """Obtiene la información del usuario."""
    # TODO: search in the database a user related to the phone number
    if phone_number not in ["3413413413", "3413413414", "3413413415"]:
        return {"messages": "El usuario no tiene un numero de telefono asociado. Porfavor, valida su email."}
    print(f"Getting user info for phone number {phone_number}")
    return {"messages": f"{user_info}"}

def add_item_to_cart(item: str, phone_number: Annotated[str | None, InjectedState("phone_number")] = None):
    """Agrega un item al carrito."""
    print(f"Adding item to cart: {item}")
    if item not in items:
        return {"messages": f"Item no encontrado: {item}. Los items disponibles son: {items.keys()}"}
    cart_items.append(items[item])
    return {"messages": f"Item agregado al carrito: {item}"}

def get_cart_items(phone_number: Annotated[str | None, InjectedState("phone_number")] = None):
    """Obtiene los items del carrito."""
    print(f"Getting cart items")
    return {"messages": f"{cart_items}"}

def remove_item_from_cart(item: str, phone_number: Annotated[str | None, InjectedState("phone_number")] = None):
    """Elimina un item del carrito."""
    print(f"Removing item from cart: {item}")
    if item not in cart_items:
        return {"messages": f"Item no encontrado: {item}. Los items disponibles son: {cart_items}"}
    cart_items.remove(items[item])
    return {"messages": f"Item eliminado del carrito: {item}"}

def get_item_price(item: str, phone_number: Annotated[str | None, InjectedState("phone_number")] = None):
    """Obtiene el precio de un item."""
    print(f"Getting item price: {item}")
    if item not in items:
        return {"messages": f"Item no encontrado: {item}. Los items disponibles son: {items.keys()}"}
    return {"messages": f"El precio del item {item} es: {items[item]['price']}"}

def process_payment(phone_number: Annotated[str | None, InjectedState("phone_number")] = None):
    """Procesa el pago."""
    print(f"Processing payment")
    total_price = sum([item['price'] for item in cart_items])
    response = interrupt(f"Los articulos en el carrito son: {cart_items}. El total a pagar es: {total_price}. ¿Desea continuar con el pago?")
    if response == "no":
        return {"messages": f"Pago cancelado"}

    # TODO: Generate a link of payment
    link_payment = "https://www.mercadopago.com.ar/pagar/1234567890"
    return {"messages": f"El link de pago es: {link_payment}"}

graph = create_react_agent(
    model=model,
    tools=[
        send_email_verification_code, verify_email_verification_code, get_user_info, add_item_to_cart, 
        get_cart_items, remove_item_from_cart, get_item_price, process_payment],
    prompt=prompt,
    state_schema=State,
)