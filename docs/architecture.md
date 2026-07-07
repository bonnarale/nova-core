# Architecture

NOVA CORE is organized as a monorepo with isolated service boundaries:

- `backend`: FastAPI API and service integrations
- `frontend`: static frontend entrypoint
- `agents`: agent definitions and execution contracts
- `memory`: long-term memory design and adapters
- `rag`: retrieval and indexing pipelines
- `workflows`: workflow automation assets
- `docker`: container and proxy configuration
- `config`: versioned runtime configuration defaults

Runtime traffic enters through Traefik. Data services remain on the internal Docker network and are not published directly to the host.

