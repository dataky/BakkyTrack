"""All API endpoints combined for convenience."""
from typing import List, Dict, Any, Optional

from .types import (
    ShopID,
    ClubID,
    ChallengeID,
    PlaylistID,
    TournamentID,
    PartyID,
)
from .playerid import PlayerID


class MatchesAPI:
    """Match-related API endpoints."""

    async def get_match_history(self, timeout: Optional[float] = None) -> List[Dict[str, Any]]:
        """Retrieve match history for the authenticated player."""
        request = {"PlayerID": str(self.local_player_id)}
        result = await self.send_request_sync("Matches/GetMatchHistory v1", request, timeout)
        return result.get("Matches", [])


class SkillsAPI:
    """Skills and ranking API endpoints."""

    async def get_player_skill(self, player_id: PlayerID, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Retrieve skill data for a given player."""
        request = {"PlayerID": str(player_id)}
        return await self.send_request_sync("Skills/GetPlayerSkill v1", request, timeout)

    async def get_players_skills(self, player_ids: List[PlayerID], timeout: Optional[float] = None) -> List[Dict[str, Any]]:
        """Retrieve skill data for given players."""
        request = {"PlayerIDs": [str(pid) for pid in player_ids]}
        result = await self.send_request_sync("Skills/GetPlayersSkills v1", request, timeout)
        return result.get("Players", [])

    async def get_skill_leaderboard(self, playlist: PlaylistID, disable_crossplay: bool = False, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Retrieve the skill leaderboard for a given playlist."""
        request = {"Playlist": playlist, "bDisableCrossplay": disable_crossplay}
        return await self.send_request_sync("Skills/GetSkillLeaderboard v1", request, timeout)

    async def get_skill_leaderboard_value_for_user(self, playlist: PlaylistID, player_id: PlayerID, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Retrieve a player's position on the skill leaderboard."""
        request = {"Playlist": playlist, "PlayerID": str(player_id)}
        return await self.send_request_sync("Skills/GetSkillLeaderboardValueForUser v1", request, timeout)

    async def get_skill_leaderboard_rank_for_users(self, playlist: PlaylistID, player_ids: List[PlayerID], timeout: Optional[float] = None) -> Dict[str, Any]:
        """Retrieve rank information for multiple players on the skill leaderboard."""
        request = {"Playlist": playlist, "PlayerIDs": [str(pid) for pid in player_ids]}
        return await self.send_request_sync("Skills/GetSkillLeaderboardRankForUsers v1", request, timeout)


class StatsAPI:
    """Statistics and leaderboard API endpoints."""

    async def get_stat_leaderboard(self, stat_name: str, disable_crossplay: bool = False, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Retrieve the stats leaderboard for a given stat."""
        request = {"Stat": stat_name, "bDisableCrossplay": disable_crossplay}
        return await self.send_request_sync("Stats/GetStatLeaderboard v1", request, timeout)

    async def get_stat_leaderboard_value_for_user(self, stat_name: str, player_id: PlayerID, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Retrieve a player's position on a stat leaderboard."""
        request = {"Stat": stat_name, "PlayerID": str(player_id)}
        return await self.send_request_sync("Stats/GetStatLeaderboardValueForUser v1", request, timeout)

    async def get_stat_leaderboard_rank_for_users(self, stat_name: str, player_ids: List[PlayerID], timeout: Optional[float] = None) -> Dict[str, Any]:
        """Retrieve rank information for multiple players on a stat leaderboard."""
        request = {"Stat": stat_name, "PlayerIDs": [str(pid) for pid in player_ids]}
        return await self.send_request_sync("Stats/GetStatLeaderboardRankForUsers v1", request, timeout)


class ClubsAPI:
    """Clubs API endpoints."""

    async def get_club_details(self, club_id: ClubID, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Retrieve detailed information about a given club."""
        request = {"ClubID": club_id}
        result = await self.send_request_sync("Clubs/GetClubDetails v1", request, timeout)
        return result.get("ClubDetails", {})

    async def get_player_club_details(self, player_id: PlayerID, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Retrieve club details for a given player."""
        request = {"PlayerID": str(player_id)}
        result = await self.send_request_sync("Clubs/GetPlayerClubDetails v2", request, timeout)
        return result.get("ClubDetails", {})

    async def create_club(self, club_name: str, club_tag: str, primary_color: int, accent_color: int, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Create a new club."""
        request = {
            "ClubName": club_name,
            "ClubTag": club_tag.upper(),
            "PrimaryColor": primary_color,
            "AccentColor": accent_color,
        }
        result = await self.send_request_sync("Clubs/CreateClub v1", request, timeout)
        return result.get("ClubDetails", {})

    async def update_club(self, update_data: Dict[str, Any], timeout: Optional[float] = None) -> Dict[str, Any]:
        """Update club details."""
        result = await self.send_request_sync("Clubs/UpdateClub v2", update_data, timeout)
        return result.get("ClubDetails", {})

    async def get_club_stats(self, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Retrieve statistics for the current player's club."""
        result = await self.send_request_sync("Clubs/GetStats v1", {}, timeout)
        return result.get("Stats", {})

    async def leave_club(self, timeout: Optional[float] = None) -> None:
        """Leave a club."""
        await self.send_request_sync("Clubs/LeaveClub v1", {}, timeout)

    async def get_club_invites(self, timeout: Optional[float] = None) -> List[Dict[str, Any]]:
        """Retrieve pending club invitations."""
        result = await self.send_request_sync("Clubs/GetClubInvites v1", {}, timeout)
        return result.get("ClubInvites", [])

    async def invite_to_club(self, player_id: PlayerID, timeout: Optional[float] = None) -> None:
        """Invite a player to join a club."""
        request = {"PlayerID": str(player_id)}
        await self.send_request_sync("Clubs/InviteToClub v4", request, timeout)

    async def accept_club_invite(self, club_id: ClubID, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Accept an invitation to join a club."""
        request = {"ClubID": club_id}
        result = await self.send_request_sync("Clubs/AcceptClubInvite v2", request, timeout)
        return result.get("ClubDetails", {})

    async def reject_club_invite(self, club_id: ClubID, timeout: Optional[float] = None) -> None:
        """Reject an invitation to join a club."""
        request = {"ClubID": club_id}
        await self.send_request_sync("Clubs/RejectClubInvite v1", request, timeout)


class PartyAPI:
    """Party API endpoints."""

    async def get_player_party_info(self, timeout: Optional[float] = None) -> List[Any]:
        """Get pending party invitations for the authenticated player."""
        result = await self.send_request_sync("Party/GetPlayerPartyInfo v1", {}, timeout)
        return result.get("Invites", [])

    async def create_party(self, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Create a new party."""
        request = {"bForcePartyonix": True}
        return await self.send_request_sync("Party/CreateParty v1", request, timeout)

    async def join_party(self, join_id: str, party_id: PartyID, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Join an existing party."""
        request = {"JoinID": join_id, "PartyID": party_id}
        return await self.send_request_sync("Party/JoinParty v1", request, timeout)

    async def leave_party(self, party_id: PartyID, timeout: Optional[float] = None) -> None:
        """Leave a party."""
        request = {"PartyID": party_id}
        await self.send_request_sync("Party/LeaveParty v1", request, timeout)

    async def send_party_invite(self, invitee_id: PlayerID, party_id: PartyID, timeout: Optional[float] = None) -> None:
        """Send an invitation to join the party."""
        request = {"InviteeID": str(invitee_id), "PartyID": party_id}
        await self.send_request_sync("Party/SendPartyInvite v2", request, timeout)

    async def change_party_owner(self, new_owner_id: PlayerID, party_id: PartyID, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Transfer party ownership."""
        request = {"NewOwnerID": str(new_owner_id), "PartyID": party_id}
        return await self.send_request_sync("Party/ChangePartyOwner v1", request, timeout)

    async def kick_party_members(self, members: List[PlayerID], kick_reason: int, party_id: PartyID, timeout: Optional[float] = None) -> None:
        """Remove members from the party."""
        request = {
            "Members": [str(pid) for pid in members],
            "KickReason": kick_reason,
            "PartyID": party_id,
        }
        await self.send_request_sync("Party/KickPartyMembers v1", request, timeout)

    async def send_party_chat_message(self, message: str, party_id: PartyID, timeout: Optional[float] = None) -> None:
        """Send a chat message to the party."""
        request = {"Message": message, "PartyID": party_id}
        await self.send_request_sync("Party/SendPartyChatMessage v1", request, timeout)


class MatchmakingAPI:
    """Matchmaking API endpoints."""

    async def start_matchmaking(
        self,
        playlists: List[int],
        regions: List[Dict[str, Any]],
        disable_crossplay: bool,
        party_id: PartyID,
        party_members: List[PlayerID],
        timeout: Optional[float] = None,
    ) -> int:
        """Start matchmaking."""
        request = {
            "Regions": regions,
            "Playlists": playlists,
            "SecondsSearching": 1,
            "CurrentServerID": "",
            "bDisableCrossplay": disable_crossplay,
            "PartyID": party_id,
            "PartyMembers": [str(pid) for pid in party_members],
        }
        result = await self.send_request_sync("Matchmaking/StartMatchmaking v2", request, timeout)
        return result.get("EstimatedQueueTime", 0)

    async def player_cancel_matchmaking(self, timeout: Optional[float] = None) -> None:
        """Cancel ongoing matchmaking."""
        await self.send_request_sync("Matchmaking/PlayerCancelMatchmaking v1", {}, timeout)


class PlaylistsAPI:
    """Playlists API endpoints."""

    async def get_active_playlists(self, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Retrieve all currently active playlists."""
        return await self.send_request_sync("Playlists/GetActivePlaylists v1", {}, timeout)


class PopulationAPI:
    """Population API endpoints."""

    async def get_population(self, timeout: Optional[float] = None) -> List[Dict[str, Any]]:
        """Retrieve current game population by playlists."""
        result = await self.send_request_sync("Population/GetPopulation v1", {}, timeout)
        return result.get("Playlists", [])

    async def update_player_playlist(self, playlist_id: PlaylistID, num_local_players: int, timeout: Optional[float] = None) -> None:
        """Update player playlist."""
        request = {"Playlist": playlist_id, "NumLocalPlayers": num_local_players}
        await self.send_request_sync("Population/UpdatePlayerPlaylist v1", request, timeout)


class ProductsAPI:
    """Products/Inventory API endpoints."""

    async def get_player_products(self, updated_timestamp: int = 0, timeout: Optional[float] = None) -> List[Dict[str, Any]]:
        """Retrieve all products/items owned by the authenticated player."""
        request = {"PlayerID": str(self.local_player_id), "UpdatedTimestamp": str(updated_timestamp)}
        result = await self.send_request_sync("Products/GetPlayerProducts v2", request, timeout)
        return result.get("ProductData", [])

    async def get_container_drop_table(self, timeout: Optional[float] = None) -> List[Dict[str, Any]]:
        """Retrieve the drop table for containers."""
        result = await self.send_request_sync("Products/GetContainerDropTable v2", {}, timeout)
        return result.get("ContainerDrops", [])

    async def unlock_container(self, instance_ids: List[str], timeout: Optional[float] = None) -> List[Dict[str, Any]]:
        """Unlock containers."""
        request = {
            "PlayerID": str(self.local_player_id),
            "InstanceIDs": instance_ids,
            "KeyInstanceIDs": [],
        }
        result = await self.send_request_sync("Products/UnlockContainer v2", request, timeout)
        return result.get("Drops", [])

    async def trade_in(self, product_instances: List[str], timeout: Optional[float] = None) -> List[Dict[str, Any]]:
        """Trade in multiple items for new items."""
        request = {"PlayerID": str(self.local_player_id), "ProductInstances": product_instances}
        result = await self.send_request_sync("Products/TradeIn v2", request, timeout)
        return result.get("Drops", [])


class MTXAPI:
    """Microtransaction API endpoints."""

    async def get_mtx_catalog(self, category: str = "", timeout: Optional[float] = None) -> Dict[str, Any]:
        """Retrieve the DLC catalog."""
        request = {"PlayerID": str(self.local_player_id), "Category": category}
        return await self.send_request_sync("Microtransaction/GetCatalog v1", request, timeout)

    async def start_mtx_purchase(self, cart_items: List[Dict[str, Any]], timeout: Optional[float] = None) -> None:
        """Initiate a DLC purchase."""
        request = {
            "Language": "INT",
            "PlayerID": str(self.local_player_id),
            "CartItems": cart_items,
        }
        await self.send_request_sync("Microtransaction/StartPurchase v1", request, timeout)


class RocketPassAPI:
    """Rocket Pass API endpoints."""

    async def get_rocket_pass_player_info(self, rocket_pass_id: int, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Retrieve Rocket Pass information for the authenticated player."""
        request = {
            "PlayerID": str(self.local_player_id),
            "RocketPassID": rocket_pass_id,
            "RocketPassInfo": {},
            "RocketPassStore": {},
        }
        return await self.send_request_sync("RocketPass/GetPlayerInfo v2", request, timeout)

    async def get_rocket_pass_reward_content(
        self,
        rocket_pass_id: int,
        tier_cap: int,
        free_max_level: int,
        premium_max_level: int,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Retrieve reward content for a Rocket Pass."""
        request = {
            "RocketPassID": rocket_pass_id,
            "TierCap": tier_cap,
            "FreeMaxLevel": free_max_level,
            "PremiumMaxLevel": premium_max_level,
        }
        return await self.send_request_sync("RocketPass/GetRewardContent v1", request, timeout)


class ChallengesAPI:
    """Challenges API endpoints."""

    async def get_active_challenges(self, timeout: Optional[float] = None) -> List[Dict[str, Any]]:
        """Retrieve currently active challenges."""
        request = {"Challenges": [], "Folders": []}
        result = await self.send_request_sync("Challenges/GetActiveChallenges v1", request, timeout)
        return result.get("Challenges", [])

    async def get_challenge_progress(self, challenge_ids: List[ChallengeID], timeout: Optional[float] = None) -> List[Dict[str, Any]]:
        """Retrieve challenge progress."""
        request = {"PlayerID": str(self.local_player_id), "ChallengeIDs": challenge_ids}
        result = await self.send_request_sync("Challenges/PlayerProgress v1", request, timeout)
        return result.get("ProgressData", [])

    async def collect_challenge_reward(self, challenge_id: ChallengeID, timeout: Optional[float] = None) -> None:
        """Collect rewards from a completed challenge."""
        request = {"PlayerID": str(self.local_player_id), "ID": challenge_id}
        await self.send_request_sync("Challenges/CollectReward v1", request, timeout)


class TournamentsAPI:
    """Tournaments API endpoints."""

    async def get_tournament_schedule_region(self, timeout: Optional[float] = None) -> str:
        """Retrieve tournament schedule region."""
        request = {"PlayerID": str(self.local_player_id)}
        result = await self.send_request_sync("Tournaments/Status/GetScheduleRegion v1", request, timeout)
        return result.get("ScheduleRegion", "")

    async def get_tournament_schedule(self, region: str, timeout: Optional[float] = None) -> List[Dict[str, Any]]:
        """Retrieve tournament schedule for a region."""
        request = {"PlayerID": str(self.local_player_id), "Region": region}
        result = await self.send_request_sync("Tournaments/Search/GetSchedule v1", request, timeout)
        return result.get("Schedules", [])


class TrainingAPI:
    """Training API endpoints."""

    async def browse_training_data(self, featured_only: bool = False, timeout: Optional[float] = None) -> List[Dict[str, Any]]:
        """Retrieve training packs."""
        request = {"bFeaturedOnly": featured_only}
        result = await self.send_request_sync("Training/BrowseTrainingData v1", request, timeout)
        return result.get("TrainingData", [])

    async def get_training_metadata(self, codes: List[str], timeout: Optional[float] = None) -> List[Dict[str, Any]]:
        """Retrieve training pack metadata."""
        request = {"Codes": codes}
        result = await self.send_request_sync("Training/GetTrainingMetadata v1", request, timeout)
        return result.get("TrainingData", [])


class MiscAPI:
    """Miscellaneous API endpoints."""

    async def get_sub_regions(self, timeout: Optional[float] = None) -> List[Dict[str, Any]]:
        """Retrieve available server regions."""
        request = {"RequestRegions": [], "Regions": []}
        result = await self.send_request_sync("Regions/GetSubRegions v1", request, timeout)
        return result.get("Regions", [])

    async def get_game_server_ping_list(self, timeout: Optional[float] = None) -> List[Dict[str, Any]]:
        """Retrieve ping information for game servers."""
        result = await self.send_request_sync("GameServer/GetGameServerPingList v2", {}, timeout)
        return result.get("Servers", [])

    async def filter_content(self, content: List[str], policy: str, timeout: Optional[float] = None) -> List[str]:
        """Filter content using the content filter."""
        request = {"Content": content, "Policy": policy}
        result = await self.send_request_sync("Filters/FilterContent v1", request, timeout)
        return result.get("FilteredContent", [])

    async def can_show_avatar(self, player_ids: List[PlayerID], timeout: Optional[float] = None) -> Dict[str, Any]:
        """Check if players' avatars can be shown."""
        request = {"PlayerIDs": [str(pid) for pid in player_ids]}
        return await self.send_request_sync("Users/CanShowAvatar v1", request, timeout)
