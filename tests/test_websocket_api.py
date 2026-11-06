"""Authenticated scene CRUD API tests; the websocket server is test-only."""

from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from homeassistant.components.light import ColorMode
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import Unauthorized
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from custom_components.smart_scene_studio.const import DATA_SCENE_ENTITIES, DOMAIN
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


async def test_native_scene_entities_track_crud_without_reload(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator
) -> None:
    """Create, rename, unassign, reassign and delete native scenes live."""
    await add_entry(hass)
    client = await hass_ws_client(hass)
    create = await request(
        client,
        {
            "type": f"{DOMAIN}/scene/create",
            "scene": {
                **CREATE_SCENE,
                "name": "Live scene",
                "targets": [{"entity_id": "light.test_lamp"}],
            },
        },
    )
    assert create["success"]
    scene_id = create["result"]["scene"]["id"]
    entity = hass.data[DOMAIN][DATA_SCENE_ENTITIES][scene_id]
    entity_id = entity.entity_id
    assert entity.unique_id == scene_id
    assert hass.states.get(entity_id) is not None

    renamed = await request(
        client,
        {
            "type": f"{DOMAIN}/scene/update",
            "scene_id": scene_id,
            "updates": {"name": "Renamed live scene"},
        },
    )
    assert renamed["success"]
    assert hass.data[DOMAIN][DATA_SCENE_ENTITIES][scene_id] is entity
    assert hass.states.get(entity_id).name == "Renamed live scene"
    assert hass.data[DOMAIN][DATA_SCENE_ENTITIES][scene_id].unique_id == scene_id

    unassigned = await request(
        client,
        {
            "type": f"{DOMAIN}/scene/update",
            "scene_id": scene_id,
            "updates": {"targets": []},
        },
    )
    assert unassigned["success"]
    assert scene_id not in hass.data[DOMAIN][DATA_SCENE_ENTITIES]
    assert hass.states.get(entity_id) is None

    reassigned = await request(
        client,
        {
            "type": f"{DOMAIN}/scene/update",
            "scene_id": scene_id,
            "updates": {"targets": [{"entity_id": "light.test_lamp"}]},
        },
    )
    assert reassigned["success"]
    restored = hass.data[DOMAIN][DATA_SCENE_ENTITIES][scene_id]
    assert restored.unique_id == scene_id
    assert restored.entity_id == entity_id
    assert hass.states.get(entity_id) is not None

    deleted = await request(client, {"type": f"{DOMAIN}/scene/delete", "scene_id": scene_id})
    assert deleted["success"]
    assert scene_id not in hass.data[DOMAIN][DATA_SCENE_ENTITIES]
    assert hass.states.get(entity_id) is None
    assert er.async_get(hass).async_get_entity_id("scene", DOMAIN, scene_id) is None


async def test_native_scene_enforces_mapped_light_control_permission(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    hass_admin_user,
    monkeypatch,
) -> None:
    """A non-admin cannot activate a scene targeting a light they cannot control."""
    await add_entry(hass)
    client = await hass_ws_client(hass)
    create = await request(
        client,
        {
            "type": f"{DOMAIN}/scene/create",
            "scene": {
                **CREATE_SCENE,
                "name": "Restricted target",
                "targets": [{"entity_id": "light.test_lamp"}],
            },
        },
    )
    scene_id = create["result"]["scene"]["id"]
    scene_entity = hass.data[DOMAIN][DATA_SCENE_ENTITIES][scene_id]
    hass_admin_user.groups = []
    monkeypatch.setattr(
        hass_admin_user.permissions,
        "check_entity",
        lambda entity_id, permission: False,
    )
    scene_entity.async_set_context(Context(user_id=hass_admin_user.id))
    light_call = AsyncMock()
    hass.services.async_register("light", "turn_on", light_call)
    hass.states.async_set("light.test_lamp", "off", {"supported_color_modes": [ColorMode.RGB]})

    with pytest.raises(Unauthorized):
        await scene_entity.async_activate()

    light_call.assert_not_awaited()


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


async def test_scene_api_does_not_report_success_after_store_failure(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator, monkeypatch
) -> None:
    """A failed Store write returns an error and registers no transient entity."""
    entry = await add_entry(hass)
    repository = hass.data[DOMAIN][entry.entry_id]["repository"]
    monkeypatch.setattr(
        repository._store,
        "async_save",
        AsyncMock(side_effect=OSError("simulated Store failure")),
    )
    client = await hass_ws_client(hass)

    response = await request(
        client,
        {
            "type": f"{DOMAIN}/scene/create",
            "scene": {
                **CREATE_SCENE,
                "name": "Not persisted",
                "targets": [{"entity_id": "light.test_lamp"}],
            },
        },
    )

    assert not response["success"]
    assert repository.scenes == ()
    assert hass.data[DOMAIN][DATA_SCENE_ENTITIES] == {}


async def test_anonymous_websocket_cannot_access_scene_api(
    hass: HomeAssistant, aiohttp_client, socket_enabled: None
) -> None:
    """An anonymous socket cannot enter command phase or send scene commands."""
    from homeassistant.setup import async_setup_component

    await add_entry(hass)
    assert await async_setup_component(hass, "websocket_api", {})
    client = await aiohttp_client(hass.http.app)
    websocket = await client.ws_connect("/api/websocket")
    assert (await websocket.receive_json())["type"] == "auth_required"
    await websocket.close()
    await hass.async_block_till_done()


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
