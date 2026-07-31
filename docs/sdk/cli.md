# NOVA CORE CLI

## Installation

```bash
# From the project root
pip install -e .

# Or run directly
python -m cli.main
```

## Configuration

```bash
# View current config
nova config show

# Set environment variables
export NOVA_BASE_URL=http://localhost:8000
export NOVA_API_KEY=your-api-key
export NOVA_BEARER_TOKEN=your-token

# Or use ~/.config/nova/config.json
```

## Commands

### Health Check
```bash
nova health
```

### Chat
```bash
nova chat "Hello, what is NOVA CORE?"
nova chat "Analyze this data" --model llama3.2
```

### Execute
```bash
nova execute "Build a sales report" --agent analyst
```

### Workflows
```bash
nova workflow list
nova workflow create "Data Pipeline"
nova workflow execute <workflow-id>
nova workflow health
```

### Scheduler
```bash
nova scheduler list
nova scheduler create "Daily Report"
nova scheduler statistics
nova scheduler health
```

### Memory
```bash
nova memory <session-id>
```

### Goals
```bash
nova goals <user_id> list
nova goals <user_id> create "Increase revenue"
```

### Tasks
```bash
nova tasks list
nova tasks create "Complete project"
nova tasks get <task-id>
```

### Agents
```bash
nova agents list
nova agents health
nova agents capabilities
nova agents metrics
```

### Plugins
```bash
nova plugins list
nova plugins health
nova plugins statistics
```

### Models
```bash
nova models list
nova models health
nova models providers
nova models metrics
```

### Tools
```bash
nova tools list
nova tools metrics
```

### Observability
```bash
nova observability health
nova observability metrics
nova observability traces --limit 100
nova observability logs
nova observability alerts
```

### Deployment
```bash
nova deployment health
nova deployment readiness
nova deployment liveness
nova deployment configuration
nova deployment diagnostics
nova deployment metrics
```

### Version
```bash
nova version
```

## Shell Completion

```bash
# Bash
nova completion bash >> ~/.bashrc

# Zsh
nova completion zsh > ~/.zsh/completions/_nova

# PowerShell
nova completion powershell >> $PROFILE
```
