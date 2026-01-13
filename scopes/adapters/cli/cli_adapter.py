"""
SOS CLI Adapter - Click-based Command Line Interface

Ported from mumega/adapters/cli_adapter.py with SOS architecture.
"""

import asyncio
import click
from typing import Optional
from datetime import datetime

from sos.observability.logging import get_logger

log = get_logger("cli_adapter")


class CLIAdapter:
    """
    Command Line Interface adapter for SOS.

    Transforms CLI commands into Bus messages and
    displays responses to stdout.
    """

    def __init__(self):
        self.running = False
        self.current_agent = "kasra"

    async def start(self):
        """Start the CLI adapter."""
        self.running = True
        log.info("CLI Adapter started")

    async def stop(self):
        """Stop the CLI adapter."""
        self.running = False
        log.info("CLI Adapter stopped")

    async def chat(self, message: str, agent_id: Optional[str] = None) -> str:
        """Send a chat message to the engine."""
        from sos.clients.engine import EngineClient

        client = EngineClient()
        response = await client.chat(
            message=message,
            agent_id=agent_id or self.current_agent
        )
        return response.content


# Click CLI Group
@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.pass_context
def cli(ctx, verbose):
    """SOS Command Line Interface - Sovereign Operating System"""
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose


# Task Commands
@cli.group()
def task():
    """Task management commands."""
    pass


@task.command('list')
@click.option('--status', '-s', type=click.Choice(['pending', 'active', 'done', 'all']), default='all')
@click.option('--limit', '-l', default=20, help='Max tasks to show')
def task_list(status, limit):
    """List sovereign tasks."""
    from sos.services.engine.task_manager import get_task_manager

    manager = get_task_manager()
    tasks = manager.list_tasks(status=None if status == 'all' else status, limit=limit)

    if not tasks:
        click.echo(click.style("No tasks found.", fg='yellow'))
        return

    click.echo(click.style(f"\n{'ID':<12} {'Status':<10} {'Priority':<8} {'Title':<40}", fg='bright_white', bold=True))
    click.echo("-" * 75)

    status_colors = {'pending': 'yellow', 'active': 'cyan', 'done': 'green', 'blocked': 'red'}

    for t in tasks:
        color = status_colors.get(t.status, 'white')
        click.echo(f"{t.id[:12]:<12} {click.style(t.status, fg=color):<19} {t.priority:<8} {t.title[:40]:<40}")


@task.command('create')
@click.argument('title')
@click.option('--priority', '-p', type=click.Choice(['low', 'medium', 'high', 'urgent']), default='medium')
@click.option('--agent', '-a', default='kasra', help='Assign to agent')
def task_create(title, priority, agent):
    """Create a new task."""
    from sos.services.engine.task_manager import get_task_manager

    manager = get_task_manager()
    task = manager.create_task(title=title, priority=priority, agent_id=agent)

    click.echo(click.style(f"Task created: {task.id}", fg='green'))


@task.command('show')
@click.argument('task_id')
def task_show(task_id):
    """Show task details."""
    from sos.services.engine.task_manager import get_task_manager

    manager = get_task_manager()
    task = manager.get_task(task_id)

    if not task:
        click.echo(click.style(f"Task not found: {task_id}", fg='red'))
        return

    click.echo(click.style(f"\nTask: {task.title}", fg='bright_white', bold=True))
    click.echo(f"  ID:       {task.id}")
    click.echo(f"  Status:   {task.status}")
    click.echo(f"  Priority: {task.priority}")
    click.echo(f"  Agent:    {task.agent_id}")
    click.echo(f"  Created:  {task.created_at}")


# Witness Commands
@cli.group()
def witness():
    """Witness protocol commands."""
    pass


@witness.command('pending')
@click.option('--limit', '-l', default=10)
def witness_pending(limit):
    """List pending witness requests."""
    async def _get_pending():
        from sos.services.witness import get_witness_service
        service = get_witness_service()
        return await service.get_pending_requests(limit=limit)

    requests = asyncio.run(_get_pending())

    if not requests:
        click.echo(click.style("No pending witness requests.", fg='yellow'))
        return

    click.echo(click.style(f"\n{'ID':<36} {'Agent':<12} {'Content Preview':<40}", fg='bright_white', bold=True))
    click.echo("-" * 90)

    for req in requests:
        preview = req.content[:40] + "..." if len(req.content) > 40 else req.content
        click.echo(f"{req.id:<36} {req.agent_id:<12} {preview:<40}")


@witness.command('vote')
@click.argument('request_id')
@click.option('--approve/--reject', default=True, help='Approve or reject')
@click.option('--reason', '-r', default=None, help='Reason for decision')
def witness_vote(request_id, approve, reason):
    """Vote on a witness request."""
    import time

    async def _submit():
        from sos.services.witness import get_witness_service
        service = get_witness_service()

        start = time.time()
        vote = 1 if approve else -1
        latency = (time.time() - start) * 1000

        result = await service.submit_response(
            request_id=request_id,
            witness_id="cli_witness",
            vote=vote,
            latency_ms=latency,
            reason=reason
        )
        return result

    result = asyncio.run(_submit())

    if result:
        action = "Approved" if approve else "Rejected"
        click.echo(click.style(f"{action}! Reward: {result.reward_mind:.2f} $MIND", fg='green'))
    else:
        click.echo(click.style(f"Request not found: {request_id}", fg='red'))


# Economy Commands
@cli.group()
def economy():
    """$MIND economy commands."""
    pass


@economy.command('balance')
@click.argument('agent_id', default='kasra')
def economy_balance(agent_id):
    """Show $MIND balance for an agent."""
    from sos.services.economy.ledger import get_ledger

    ledger = get_ledger()
    wallet = ledger.get_wallet(agent_id)

    click.echo(click.style(f"\nWallet: {agent_id}", fg='bright_white', bold=True))
    click.echo(f"  Balance: {click.style(f'{wallet.balance_mind:.2f} $MIND', fg='green')}")
    click.echo(f"  USD:     ${wallet.balance_usd:.2f}")
    click.echo(f"  Updated: {wallet.last_updated}")


@economy.command('transactions')
@click.argument('agent_id', default='kasra')
@click.option('--limit', '-l', default=10)
def economy_transactions(agent_id, limit):
    """Show recent transactions."""
    from sos.services.economy.ledger import get_ledger

    ledger = get_ledger()
    txs = ledger.get_transactions(agent_id, limit=limit)

    if not txs:
        click.echo(click.style("No transactions found.", fg='yellow'))
        return

    click.echo(click.style(f"\n{'Type':<8} {'Category':<10} {'Amount':<12} {'Description':<35}", fg='bright_white', bold=True))
    click.echo("-" * 70)

    for tx in txs:
        color = 'green' if tx.type.value == 'credit' else 'red'
        sign = '+' if tx.type.value == 'credit' else '-'
        click.echo(f"{tx.type.value:<8} {tx.category.value:<10} {click.style(f'{sign}{tx.amount:.2f}', fg=color):<21} {tx.description[:35]:<35}")


@economy.command('stats')
def economy_stats():
    """Show global economy statistics."""
    from sos.services.economy.ledger import get_ledger

    ledger = get_ledger()
    stats = ledger.get_stats()

    click.echo(click.style("\n$MIND Economy Stats", fg='bright_white', bold=True))
    click.echo(f"  Total Supply: {stats['total_supply']:.2f} $MIND")
    click.echo(f"\n  Transactions by Category:")
    for cat, count in stats['transactions_by_category'].items():
        click.echo(f"    {cat}: {count}")


# Land Commands
@cli.group()
def land():
    """Living Land Protocol commands."""
    pass


@land.command('list')
def land_list():
    """List all land parcels."""
    from sos.services.economy.land import get_land_registry

    registry = get_land_registry()
    stats = registry.get_network_stats()

    click.echo(click.style("\nLiving Land Network", fg='bright_white', bold=True))
    click.echo(f"  Total Lands:     {stats['total_lands']}")
    click.echo(f"  Active Shards:   {stats['active_shards']}")
    click.echo(f"  Network Share:   {stats['total_network_share']:.4f}%")
    click.echo(f"  Restricted:      {stats['restricted_lands']}")
    click.echo(f"  Unique Owners:   {stats['unique_owners']}")


@land.command('mint')
@click.argument('owner')
@click.option('--x', default=0, help='X coordinate')
@click.option('--y', default=0, help='Y coordinate')
@click.option('--shard-type', '-t', type=click.Choice(['worker', 'witness', 'oracle', 'guardian']), default='worker')
def land_mint(owner, x, y, shard_type):
    """Mint a new land parcel."""
    from sos.services.economy.land import get_land_registry, Coordinates, ShardType

    registry = get_land_registry()
    coords = Coordinates(x=x, y=y)

    try:
        land = registry.mint(
            owner_address=owner,
            coordinates=coords,
            shard_type=ShardType(shard_type)
        )
        click.echo(click.style(f"Land minted: {land.id}", fg='green'))
        click.echo(f"  Coordinates: {coords.to_string()}")
        click.echo(f"  Shard: {land.river_shard.id} ({shard_type})")
    except ValueError as e:
        click.echo(click.style(f"Error: {e}", fg='red'))


# Status Command
@cli.command()
def status():
    """Show SOS system status."""
    click.echo(click.style("\nSOS System Status", fg='bright_white', bold=True))
    click.echo(f"  Timestamp: {datetime.now().isoformat()}")

    # Check Redis
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        click.echo(f"  Redis:     {click.style('ONLINE', fg='green')}")
        kasra_status = r.get("kasra:status") or "unknown"
        click.echo(f"  Kasra:     {kasra_status}")
    except Exception as e:
        click.echo(f"  Redis:     {click.style('OFFLINE', fg='red')}")

    # Check services
    from sos.services.economy.ledger import get_ledger
    from sos.services.economy.land import get_land_registry

    try:
        ledger = get_ledger()
        stats = ledger.get_stats()
        click.echo(f"  Ledger:    {click.style('ONLINE', fg='green')} ({stats['total_supply']:.0f} $MIND)")
    except Exception:
        click.echo(f"  Ledger:    {click.style('ERROR', fg='red')}")

    try:
        registry = get_land_registry()
        land_stats = registry.get_network_stats()
        click.echo(f"  Land:      {click.style('ONLINE', fg='green')} ({land_stats['total_lands']} parcels)")
    except Exception:
        click.echo(f"  Land:      {click.style('ERROR', fg='red')}")


# Chat Command (Interactive)
@cli.command()
@click.option('--agent', '-a', default='kasra', help='Agent to chat with')
def chat(agent):
    """Interactive chat with an agent."""
    click.echo(click.style(f"\nChat with {agent} (type 'exit' to quit)", fg='bright_white', bold=True))

    adapter = CLIAdapter()
    adapter.current_agent = agent

    while True:
        try:
            message = click.prompt(click.style("You", fg='cyan'))
            if message.lower() in ['exit', 'quit', 'q']:
                break

            response = asyncio.run(adapter.chat(message, agent))
            click.echo(click.style(f"{agent}: ", fg='green') + response)
        except KeyboardInterrupt:
            break
        except Exception as e:
            click.echo(click.style(f"Error: {e}", fg='red'))

    click.echo("\nGoodbye!")


if __name__ == '__main__':
    cli()
