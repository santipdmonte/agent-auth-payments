from langgraph.graph.message import MessagesState
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langgraph.types import interrupt
from langgraph.prebuilt import InjectedState
from typing import Annotated
from langchain_core.messages import AnyMessage
import os
import httpx

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8001")

class State(MessagesState):
    remaining_steps: int
    phone_number: str | None = None

model = ChatOpenAI(model="gpt-5-mini")

# prompt = """
# Eres un asistente util para ayudar a un usuario.

# Cuando el usuario te envie el primer mensaje, debes utilizar la tool "get_user_info" para obtener la información del usuario.

# si el usuario no tiene una cuenta asociada, debes validar su email.
#     - El usuario te proporcionara un email.
#     - Tú debes utilizar la tool "send_email_verification_code" para enviar un codigo de verificación al email del usuario.
#     - El usuario te proporcionara un codigo de verificación.
#     - Debes utilizar la tool "verify_email_verification_code" para verificar si el codigo de verificación es valido.

# """

async def prompt(state: State) -> list[AnyMessage]:  
    phone_number = state["phone_number"]

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BACKEND_URL}/users/phone/{phone_number}", timeout=5.0)
        
            if response.status_code == 404:
                user = None
            else:
                user = response.json()
    except Exception as e:
        print(f"\n\Error: {e}\n\n")
        user = None

    print(f"\n\nUser: {user}\n\n")

    system_msg = f"""
Eres un asistente util para ayudar a un usuario.

"""

    if not user:
        system_msg += """
El usuario no tiene una cuenta asociada, debes validar su email.
    - El usuario te proporcionara un email.
    - Tú debes utilizar la tool "send_email_verification_code" para enviar un codigo de verificación al email del usuario.
    - El usuario te proporcionara un codigo de verificación.
    - Debes utilizar la tool "verify_email_verification_code" para verificar si el codigo de verificación es valido.
"""
    else:
        system_msg += f"""
El usuario tiene una cuenta asociada, esta es la información del usuario:
{user}
"""

    return [{"role": "system", "content": system_msg}] + state["messages"]

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
    phone_number: Annotated[str | None, InjectedState("phone_number")] = None,
):
    """Envía un código de verificación al email del usuario a través del backend."""
    if not phone_number:
        return {"messages": "Necesito tu número de teléfono para enviar el código de verificación."}
    try:
        response = httpx.post(
            f"{BACKEND_URL}/users/phone/{phone_number}/send-verification-code/{email}",
            timeout=5.0,
        )
    except Exception:
        return {"messages": "Error conectando con el backend para enviar el código"}
    if response.status_code != 200:
        return {"messages": "Error enviando el código de verificación"}
    return {"messages": "Código de verificación enviado. Revisa tu email e ingresa el código."}


def verify_email_verification_code(email: str, code: str, phone_number: Annotated[str | None, InjectedState("phone_number")] = None):
    """Verifica si el código de verificación es válido a través del backend."""
    if not phone_number:
        return {"messages": "Necesito tu número de teléfono para verificar el código."}
    try:
        response = httpx.post(
            f"{BACKEND_URL}/users/phone/{phone_number}/verify-code/{email}",
            params={"code": code},
            timeout=5.0,
        )
    except Exception:
        return {"messages": "Error conectando con el backend para verificar el código"}
    if response.status_code != 200:
        return {"messages": "Código inválido o error del backend. Intenta nuevamente."}
    try:
        user = response.json()
    except Exception:
        user = None
    if not user:
        return {"messages": "Código inválido."}
    return {"messages": f"{user}"}


def get_user_info(
    phone_number: Annotated[str | None, InjectedState("phone_number")] = None, 
):
    """Obtiene la información del usuario."""
    try:
        response = httpx.get(f"{BACKEND_URL}/users/phone/{phone_number}", timeout=5.0)
        if response.status_code == 404:
            return {"messages": "Usuario no encontrado"}
        if response.status_code != 200:
            return {"messages": "Error consultando el backend"}
        user = response.json()
    except Exception:
        return {"messages": "Error conectando con el backend"}
    if not user:
        return {"messages": "El usuario no tiene un numero de telefono asociado. Porfavor, valida su email."}
    print(f"Getting user info for phone number {phone_number}")
    return {"messages": f"{user}"}


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