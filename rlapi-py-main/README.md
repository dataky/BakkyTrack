# rlapi-py

A reverse-engineered Python SDK for Rocket League's internal APIs, providing complete access to item shops, player stats, inventory, match history, replays, and more.

## Features

- **Complete Authentication Flow** - Epic Games Store (EGS) and Steam session ticket authentication
- **WebSocket API** - Full access to PsyNet's WebSocket protocol
- **Item Shop** - Monitor and query the item shop catalog
- **Player Data** - Access inventory, match history, stats, and skill ratings
- **Tournaments** - View schedules and tournament information
- **Clubs & Parties** - Manage clubs and party systems
- **Training Packs** - Browse and query training pack metadata

## Installation

```bash
pip install -r requirements.txt
```

## Examples

- **[Authentication](examples/auth/main.py)** - Basic authentication flow
- **[Item Shop Monitor](examples/itemshop/main.py)** - Poll item shop for changes
- **[Tournament Schedule](examples/tournaments/main.py)** - View tournament schedules

## API Documentation

### Authentication

Rocket League uses [Epic Online Services (EOS)](https://dev.epicgames.com/docs/web-api-ref/authentication) for authentication. The SDK supports:

1. **Epic Games Store (EGS)** - Browser-based authorization code flow
2. **Steam** - Session ticket exchange for EOS token

All API requests require HMAC-SHA256 signatures with reverse-engineered signing keys from the game binary.

### Available APIs

The SDK provides access to the following API categories:

- **Challenges** - Active challenges and rewards
- **Clubs** - Club management and statistics
- **GameServer** - Server regions and ping information
- **Matches** - Match history with replay URLs
- **Matchmaking** - Queue for matches
- **Party** - Party creation and management
- **Players** - Profiles, XP, ban status
- **Playlists** - Active playlists and population
- **Products** - Inventory, trade-ins, containers
- **RocketPass** - Rocket Pass progress and rewards
- **Shops** - Item shop catalog and purchases
- **Skills** - Skill ratings and leaderboards
- **Stats** - Global leaderboards
- **Tournaments** - Tournament schedules and registration
- **Training** - Training pack metadata

For detailed request/response schemas, see [REQUESTS.md](requests.md).

## Technical Details

### Request Signing

All requests include a `PsySig` header with HMAC-SHA256 signatures:

- **Request**: `HMAC-SHA256(key, "-" + body)`
- **Response**: `HMAC-SHA256(key, PsyTime + "-" + body)`

Keys are XOR-encrypted in the game binary with a 4-byte pattern.

### WebSocket Protocol

After HTTP authentication, all communication occurs over WebSocket with custom headers:

```
PsyService: Shops/GetStandardShops v1
PsyRequestID: PsyNetMessage_X_1
PsyToken: <auth-token>
PsySessionID: <session-id>
PsySig: <signature>
PsyBuildID: 151471783
User-Agent: RL Win/250811.43331.492665 gzip
PsyEnvironment: Prod

{"PlayerID": "Epic|abc123|0"}
```

### Player ID Format

Player IDs use the format: `<platform>|<platform-account-id>|0`

Examples:
- Epic: `Epic|e57c936318a5421a9214cf238d369cf6|0`
- Steam: `Steam|76561197960287930|0`

**Note**: Not all endpoints are fully documented. This is a community-driven reverse engineering effort.

## Disclaimer

This project is for educational and research purposes only. It is not affiliated with or endorsed by Psyonix or Epic Games. Use at your own risk.

## License

MIT License - see LICENSE file for details
