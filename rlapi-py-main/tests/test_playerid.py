"""Tests for PlayerID."""
import pytest
from rlapi.playerid import PlayerID, Platform, new_player_id, parse_player_id


def test_new_player_id():
    """Test creating a new PlayerID."""
    player_id = new_player_id(Platform.EPIC, "test123")
    assert str(player_id) == "Epic|test123|0"


def test_player_id_create():
    """Test PlayerID.create class method."""
    player_id = PlayerID.create(Platform.STEAM, "76561198012345678")
    assert str(player_id) == "Steam|76561198012345678|0"


def test_player_id_parse():
    """Test parsing a PlayerID."""
    player_id = PlayerID("Epic|abc123|0")
    platform, id_str = player_id.parse()

    assert platform == Platform.EPIC
    assert id_str == "abc123"


def test_parse_player_id_function():
    """Test parse_player_id function."""
    platform, id_str = parse_player_id("PS4|psn_user|0")

    assert platform == Platform.PS4
    assert id_str == "psn_user"


def test_player_id_invalid_format():
    """Test that parsing invalid PlayerID raises ValueError."""
    player_id = PlayerID("Invalid")

    with pytest.raises(ValueError, match="Invalid PlayerID format"):
        player_id.parse()


def test_player_id_all_platforms():
    """Test creating PlayerIDs for all platforms."""
    platforms = [
        (Platform.EPIC, "Epic"),
        (Platform.STEAM, "Steam"),
        (Platform.PS4, "PS4"),
        (Platform.XBOX, "XboxOne"),
        (Platform.SWITCH, "Switch"),
    ]

    for platform, expected_name in platforms:
        player_id = new_player_id(platform, "test123")
        assert str(player_id) == f"{expected_name}|test123|0"

        parsed_platform, parsed_id = player_id.parse()
        assert parsed_platform == platform
        assert parsed_id == "test123"


def test_player_id_string_representation():
    """Test PlayerID string representation."""
    player_id = new_player_id(Platform.EPIC, "myid")
    assert str(player_id) == "Epic|myid|0"
    assert repr(player_id) == "'Epic|myid|0'"
