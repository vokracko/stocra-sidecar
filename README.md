# Sidecar

Application exposing a REST API to access block and transaction data from blockchain nodes and caching responses.
Uses [genesis](https://github.com/vokracko/stocra-genesis) to communicate with blockchain nodes.

The application exposes public endpoints on `:8000`:
- `/v1.0/status` - returns the status of the application
- `/v1.0/tokens` - returns known tokens (ethereum, aptos)
- `/v1.0/blocks/lastest` - returns the last block number
- `/v1.0/blocks/<block_number>` - returns block data for the given block number
- `/v1.0/blocks/<block_hash>` - returns block data for the given block hash
- `/v1.0/transactions/<transaction_hash>` - returns transaction data for the given transaction hash


## How to run locally
Define the following variables in `.env` file:
```dotenv
NODE_BLOCKCHAIN=<blockchain name>
NODE_URL=<blockchain node url>
NODE_TOKEN=<blockchain node token>
REDIS_HOST=<redis host>
ENVIRONMENT=<environment name>

# the following are necessary only you are running multiple deployments
# using different redises to synchronize limits
SIDECAR_TOKEN=<sidecar token> 
SIDECAR_URLS='[<http://another-sidecar-url.com/>]'
```
### Terminal
```bash
./scripts/entrypoint --reload
```

### Docker compose
```bash
docker-compose up -d
```
