"""Type definitions for Rocket League API."""
from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict
from enum import IntEnum


# Type aliases
ShopID = int
ClubID = int
ChallengeID = int
PlaylistID = int
TournamentID = str
PartyID = str


@dataclass
class PlayerData:
    """Player data."""

    PlayerID: str
    PlayerName: str
    PresenceState: str
    PresenceInfo: str


@dataclass
class PlayerXPInfo:
    """Player XP information."""

    TotalXP: int
    XPLevel: int
    XPTitle: str
    XPProgressInCurrentLevel: int
    XPRequiredForNextLevel: int


@dataclass
class ProductAttribute:
    """Product attribute."""

    Key: str
    Value: Any


@dataclass
class Product:
    """Game product/item."""

    ProductID: int
    InstanceID: Optional[str] = None
    Attributes: List[ProductAttribute] = field(default_factory=list)
    SeriesID: int = 0
    AddedTimestamp: Optional[int] = None
    UpdatedTimestamp: Optional[int] = None


@dataclass
class DeliverableProduct:
    """Deliverable product from shop purchase."""

    Count: int
    Product: Product
    SortID: Optional[int] = None
    IsOwned: Optional[bool] = None


@dataclass
class DeliverableCurrency:
    """Deliverable currency from shop purchase."""

    ID: int
    Amount: int


@dataclass
class CurrencyPrice:
    """Currency price."""

    ID: int
    Amount: int


@dataclass
class ShopItemCost:
    """Shop item cost."""

    ShopItemCostID: int
    StartDate: int
    Price: List[CurrencyPrice]
    SortID: int
    DisplayTypeID: int
    ShopScaledCost: Any
    ResetTime: Optional[int] = None
    EndDate: Optional[int] = None
    Discount: Optional[Any] = None
    BulkDiscounts: Optional[Any] = None


@dataclass
class ShopItem:
    """Shop item."""

    ShopItemID: int
    StartDate: int
    DeliverableProducts: List[DeliverableProduct]
    DeliverableCurrencies: List[DeliverableCurrency]
    Costs: List[ShopItemCost]
    ShopItemLocations: List[int]
    Attributes: List[ProductAttribute]
    PurchasedQuantity: int
    Purchasable: bool
    FeaturedCollections: List[Any] = field(default_factory=list)
    EndDate: Optional[int] = None
    MaxQuantityPerPlayer: Optional[int] = None
    ImageURL: Optional[str] = None
    Title: Optional[str] = None
    Description: Optional[str] = None
    Disclaimer: Optional[str] = None
    MaxQuantityPerDay: Optional[int] = None
    DailyPurchasedQuantity: Optional[int] = None


@dataclass
class Shop:
    """Shop."""

    ID: ShopID
    Type: str
    StartDate: int
    EndDate: Optional[int] = None
    LogoURL: Optional[str] = None
    Name: Optional[str] = None
    Title: Optional[str] = None


@dataclass
class ShopCatalogue:
    """Shop catalogue."""

    ShopID: ShopID
    ShopItems: List[ShopItem]


@dataclass
class MatchSkills:
    """Match skills data."""

    Mu: float
    Sigma: float
    Tier: int
    Division: int
    PrevMu: float
    PrevSigma: float
    PrevTier: int
    PrevDivision: int
    bValid: bool


@dataclass
class MatchPlayer:
    """Match player data."""

    PlayerID: str
    PlayerName: str
    ConnectTimestamp: int
    JoinTimestamp: int
    LeaveTimestamp: int
    PartyLeaderID: str
    InParty: bool
    bAbandoned: bool
    bMvp: bool
    LastTeam: int
    TeamColor: str
    SecondsPlayed: float
    Score: int
    Goals: int
    Assists: int
    Saves: int
    Shots: int
    Demolishes: int
    OwnGoals: int
    Skills: MatchSkills


@dataclass
class Match:
    """Match data."""

    MatchGUID: str
    RecordStartTimestamp: int
    MapName: str
    Playlist: int
    SecondsPlayed: float
    OvertimeSecondsPlayed: float
    WinningTeam: int
    Team0Score: int
    Team1Score: int
    bOverTime: bool
    bNoContest: bool
    bForfeit: bool
    bClubVsClub: bool
    Mutators: List[str]
    Players: List[MatchPlayer]
    CustomMatchCreatorPlayerID: Optional[str] = None


@dataclass
class MatchEntry:
    """Match history entry."""

    ReplayUrl: str
    Match: Match


@dataclass
class Skill:
    """Player skill data for a playlist."""

    Playlist: int
    Mu: float
    Sigma: float
    Tier: int
    Division: int
    MMR: float
    WinStreak: int
    MatchesPlayed: int
    PlacementMatchesPlayed: int


@dataclass
class RewardLevels:
    """Seasonal reward level information."""

    SeasonLevel: int
    SeasonLevelWins: int


@dataclass
class LeaderboardPlayer:
    """Leaderboard player entry."""

    PlayerID: str
    PlayerName: str
    MMR: float
    Value: int


@dataclass
class PlatformLeaderboard:
    """Platform leaderboard data."""

    Platform: str
    Players: List[LeaderboardPlayer]


# Club types
@dataclass
class ClubMember:
    """Club member."""

    PlayerID: str
    PlayerName: str
    EpicPlayerID: str
    EpicPlayerName: str
    RoleID: int
    CreatedTime: int
    DeletedTime: int
    PsyonixID: Optional[str] = None


@dataclass
class ClubBadge:
    """Club badge."""

    Stat: str
    Badge: int


@dataclass
class ClubDetails:
    """Club details."""

    ClubID: ClubID
    ClubName: str
    ClubTag: str
    PrimaryColor: int
    AccentColor: int
    EquippedTitle: str
    OwnerPlayerID: str
    Members: List[ClubMember]
    Badges: List[ClubBadge]
    Flags: List[Any]
    bVerified: bool
    CreatedTime: int
    LastUpdatedTime: int
    NameLastUpdatedTime: int
    DeletedTime: int


# Party types
@dataclass
class PartyInfo:
    """Party information."""

    PartyID: str
    CreatedAt: int
    CreatedByUserID: str
    JoinID: str


@dataclass
class PartyMember:
    """Party member."""

    PartyID: str
    UserID: str
    UserName: str
    JoinedAt: int
    Role: str


@dataclass
class PartyResponse:
    """Party response."""

    Info: PartyInfo
    Members: List[PartyMember]


# Playlist types
@dataclass
class Playlist:
    """Game playlist."""

    NodeID: str
    Playlist: int
    Type: int
    StartTime: Optional[int] = None
    EndTime: Optional[int] = None


@dataclass
class PlaylistPopulation:
    """Playlist population data."""

    PlaylistID: PlaylistID
    Population: int


# Matchmaking types
@dataclass
class MatchmakingRegion:
    """Matchmaking region."""

    Name: str
    Ping: int


# Challenge types
@dataclass
class ChallengeRequirement:
    """Challenge requirement."""

    RequiredCount: int


@dataclass
class ChallengeRewards:
    """Challenge rewards."""

    XP: int
    Currency: List[Any]
    Products: List[Any]
    Pips: int


@dataclass
class Challenge:
    """In-game challenge."""

    ID: ChallengeID
    Title: str
    Description: str
    Sort: int
    GroupID: int
    XPUnlockLevel: int
    bIsRepeatable: bool
    RepeatLimit: int
    IconURL: str
    BackgroundColor: int
    Requirements: List[ChallengeRequirement]
    Rewards: ChallengeRewards
    bAutoClaimRewards: bool
    bIsPremium: bool
    UnlockChallengeIDs: List[ChallengeID]
    BackgroundURL: Optional[str] = None


# Rocket Pass types
@dataclass
class RocketPassInfo:
    """Rocket Pass player information."""

    TierLevel: int
    bOwnsPremium: bool
    XPMultiplier: float
    Pips: int
    PipsPerLevel: int


@dataclass
class XPReward:
    """XP reward."""

    Name: str
    Amount: float


@dataclass
class CurrencyDrop:
    """Currency drop."""

    ID: int
    CurrencyID: int
    Amount: int


@dataclass
class RocketPassReward:
    """Rocket Pass reward."""

    Tier: int
    ProductData: List[Product]
    XPRewards: List[XPReward]
    CurrencyDrops: List[CurrencyDrop]


# Training types
@dataclass
class TrainingPack:
    """Training pack."""

    Code: str
    TM_Name: str
    Type: int
    Difficulty: int
    CreatorName: str
    MapName: str
    Tags: List[str]
    NumRounds: int
    TM_Guid: str
    CreatedAt: int
    UpdatedAt: int
    CreatorPlayerID: Optional[str] = None


# Tournament types
@dataclass
class Tournament:
    """Tournament."""

    ID: int
    Title: str
    CreatorName: str
    CreatorPlayerID: str
    StartTime: int
    MaxBracketSize: int
    RankMin: int
    RankMax: int
    Region: str
    Platforms: List[str]
    GameTags: str
    GameMode: int
    GameModes: List[int]
    TeamSize: int
    DisabledMaps: List[str]
    SeriesLength: int
    FinalSeriesLength: int
    SeriesRoundLengths: List[int]
    SeedingType: int
    TieBreaker: int
    bPublic: bool
    TeamsRegistered: int
    IsSchedulingTournament: bool
    GenerateBracketTime: Optional[int] = None
    MapSetName: Optional[str] = None
    ScheduleID: Optional[int] = None


# MTX types
@dataclass
class MTXCurrency:
    """MTX currency."""

    ID: int
    CurrencyID: int
    Amount: int


@dataclass
class MTXProduct:
    """MTX product."""

    ID: int
    Title: str
    Description: str
    TabTitle: str
    PriceDescription: str
    ImageURL: str
    PlatformProductID: str
    bIsOwned: bool
    Items: List[Product]
    Currencies: List[MTXCurrency]


# Region types
@dataclass
class Region:
    """Server region."""

    Region: str
    Label: str
    SubRegions: List[str]


@dataclass
class Server:
    """Game server."""

    Region: str
    Host: str
    Port: str
    SubRegion: str
