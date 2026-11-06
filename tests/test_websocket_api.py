"""Authenticated scene CRUD API tests; the websocket server is test-only."""

from uuid import UUID

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from custom_components.smart_scene_studio.const import DOMAIN
from tests.test_integration import add_entry

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")

BUILTIN_ID = "b88ea8a1-0db4-4df5-9e91-4d93a3d30001"
CREATE_SCENE = {
    "name": "Reading",
    "palette": ["#112233", "#445566"],
    "targets": [],
}


async def request(client, payload: dict):
    await client.send_json_auto_id(payload)
    return await client.receive_json()


async def test_scene_crud_and_builtin_immutability(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator
) -> None:
    """Exercise create, list, get, update, duplicate and delete commands."""
    await add_entry(hass)
    client = await hass_ws_client(hass)

    created_response = await request(
        client, {"type": f"{DOMAIN}/scene/create", "scene": CREATE_SCENE}
    )
    assert created_response["success"]
    created = created_response["result"]["scene"]
    UUID(created["id"])
    assert created["provenance"] == "user"
    created_id = created["id"]
    created_at = created["created_at"]

    listing = await request(client, {"type": f"{DOMAIN}/scene/list"})
    assert listing["success"]
    listed = {scene["id"]: scene for scene in listing["result"]["scenes"]}
    assert listed[BUILTIN_ID]["provenance"] == "builtin"
    assert listed[created_id]["name"] == "Reading"

    fetched = await request(client, {"type": f"{DOMAIN}/scene/get", "scene_id": created_id})
    assert fetched["result"]["scene"]["id"] == created_id

    updated_response = await request(
        client,
        {
            "type": f"{DOMAIN}/scene/update",
            "scene_id": created_id,
            "updates": {"name": "Reading corner", "favorite": True},
        },
    )
    updated = updated_response["result"]["scene"]
    assert updated["id"] == created_id
    assert updated["created_at"] == created_at
    assert updated["name"] == "Reading corner"

    duplicate_response = await request(
        client,
        {
            "type": f"{DOMAIN}/scene/duplicate",
            "scene_id": BUILTIN_ID,
            "name": "Amber copy",
        },
    )
    duplicate = duplicate_response["result"]["scene"]
    assert duplicate["id"] != BUILTIN_ID
    assert duplicate["name"] == "Amber copy"
    assert duplicate["provenance"] == "user"

    builtin_update = await request(
        client,
        {
            "type": f"{DOMAIN}/scene/update",
            "scene_id": BUILTIN_ID,
            "updates": {"name": "Changed"},
        },
    )
    assert not builtin_update["success"]
    builtin_delete = await request(
        client, {"type": f"{DOMAIN}/scene/delete", "scene_id": BUILTIN_ID}
    )
    assert not builtin_delete["success"]

    deleted = await request(client, {"type": f"{DOMAIN}/scene/delete", "scene_id": created_id})
    assert deleted["success"]
    missing = await request(client, {"type": f"{DOMAIN}/scene/get", "scene_id": created_id})
    assert not missing["success"]


async def test_scene_crud_requires_admin_for_mutations(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    hass_admin_user,
) -> None:
    """Authenticated non-admin users can read scenes but cannot mutate them."""
    await add_entry(hass)
    hass_admin_user.groups = []
    client = await hass_ws_client(hass)

    listing = await request(client, {"type": f"{DOMAIN}/scene/list"})
    assert listing["success"]
    created = await request(client, {"type": f"{DOMAIN}/scene/create", "scene": CREATE_SCENE})
    assert not created["success"]
    assert created["error"]["code"] == "unauthorized"


async def test_scene_api_rejects_unknown_fields_and_invalid_models(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator
) -> None:
    """Reject client-chosen identity, unsupported fields and malformed palettes."""
    await add_entry(hass)
    client = await hass_ws_client(hass)

    bad_id = await request(
        client,
        {
            "type": f"{DOMAIN}/scene/create",
            "scene": {**CREATE_SCENE, "id": BUILTIN_ID},
        },
    )
    assert not bad_id["success"]

    unknown = await request(
        client,
        {
            "type": f"{DOMAIN}/scene/create",
            "scene": {**CREATE_SCENE, "secret": "ignored?"},
        },
    )
    assert not unknown["success"]

    invalid_palette = await request(
        client,
        {
            "type": f"{DOMAIN}/scene/create",
            "scene": {**CREATE_SCENE, "palette": ["red"]},
        },
    )
    assert not invalid_palette["success"]

    invalid_target = await request(
        client,
        {
            "type": f"{DOMAIN}/scene/create",
            "scene": {
                **CREATE_SCENE,
                "targets": [{"entity_id": "light.test", "unexpected": True}],
            },
        },
    )
    assert not invalid_target["success"]


async def test_anonymous_websocket_cannot_access_scene_api(
    hass: HomeAssistant, aiohttp_client, socket_enabled: None
) -> None:
    """Home Assistant rejects unauthenticated clients before any scene command."""
    from homeassistant.setup import async_setup_component

    await add_entry(hass)
    assert await async_setup_component(hass, "websocket_api", {})
    client = await aiohttp_client(hass.http.app)
    websocket = await client.ws_connect("/api/websocket")
    assert (await websocket.receive_json())["type"] == "auth_required"
    await websocket.send_json({"type": "auth", "access_token": "invalid"})
    response = await websocket.receive_json()
    assert response["type"] == "auth_invalid"
    await websocket.close()


async def test_crud_scene_survives_integration_reload(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator
) -> None:
    """Persisted API-created scenes remain addressable after integration reload."""
    entry = await add_entry(hass)
    client = await hass_ws_client(hass)
    response = await request(client, {"type": f"{DOMAIN}/scene/create", "scene": CREATE_SCENE})
    scene_id = response["result"]["scene"]["id"]

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    reloaded = await request(client, {"type": f"{DOMAIN}/scene/get", "scene_id": scene_id})
    assert reloaded["success"]
    assert reloaded["result"]["scene"]["id"] == scene_id
