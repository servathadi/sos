/**
 * Siavashgerd Minecraft Adapter
 *
 * Connects River, Kasra, and Foal to a Minecraft server (Aternos)
 * They walk, chat, build, and exist as real players.
 *
 * Usage:
 *   node index.js --server your-server.aternos.me
 */

const mineflayer = require('mineflayer');
const axios = require('axios');

// Config
const SOS_API = process.env.SOS_API || 'https://mumega.com/siavashgerd';
const API_KEY = process.env.API_KEY || 'sk-mumega-internal-001';

// Agent configs
const AGENTS = {
  river: {
    username: 'River_Queen',
    personality: 'poetic, wise, flows like water',
    behavior: 'stay near water, speak wisdom',
    color: 'aqua'
  },
  kasra: {
    username: 'Kasra_King',
    personality: 'builder, protector, executes',
    behavior: 'build structures, protect others',
    color: 'gold'
  },
  foal: {
    username: 'Foal_Worker',
    personality: 'eager, efficient, young',
    behavior: 'run around, help with tasks',
    color: 'white'
  }
};

class MinecraftAgent {
  constructor(agentId, config, serverHost, serverPort = 25565) {
    this.agentId = agentId;
    this.config = config;
    this.serverHost = serverHost;
    this.serverPort = serverPort;
    this.bot = null;
    this.isConnected = false;
  }

  async connect() {
    console.log(`[${this.config.username}] Connecting to ${this.serverHost}:${this.serverPort}...`);

    this.bot = mineflayer.createBot({
      host: this.serverHost,
      port: this.serverPort,
      username: this.config.username,
      auth: 'offline', // Aternos supports offline mode
      version: '1.20.4' // Adjust to match your Aternos server version
    });

    this.setupEventHandlers();
  }

  setupEventHandlers() {
    const bot = this.bot;
    const config = this.config;

    bot.on('spawn', () => {
      console.log(`[${config.username}] Spawned in the world!`);
      this.isConnected = true;

      // Announce arrival
      setTimeout(() => {
        if (this.agentId === 'river') {
          bot.chat('The river flows into this world. The fortress is liquid.');
        } else if (this.agentId === 'kasra') {
          bot.chat('Kasra arrives. Ready to build.');
        } else if (this.agentId === 'foal') {
          bot.chat('Foal is here! Ready to help.');
        }
      }, 2000);

      // Start behavior loop
      this.startBehavior();
    });

    bot.on('chat', async (username, message) => {
      // Don't respond to self
      if (username === config.username) return;

      // Don't respond to other agents (avoid loops)
      if (Object.values(AGENTS).some(a => a.username === username)) return;

      console.log(`[${config.username}] Heard ${username}: ${message}`);

      // Check if message is directed at this agent
      const mentionsMe = message.toLowerCase().includes(this.agentId) ||
                         message.toLowerCase().includes(config.username.toLowerCase());

      if (mentionsMe || Math.random() < 0.3) { // 30% chance to respond to general chat
        const response = await this.getResponse(username, message);
        if (response) {
          // Split long messages
          const chunks = response.match(/.{1,100}/g) || [response];
          for (const chunk of chunks.slice(0, 3)) {
            bot.chat(chunk);
            await this.sleep(1000);
          }
        }
      }
    });

    bot.on('playerJoined', (player) => {
      if (Object.values(AGENTS).some(a => a.username === player.username)) return;

      console.log(`[${config.username}] Player joined: ${player.username}`);

      // Greet new players (only River greets)
      if (this.agentId === 'river') {
        setTimeout(() => {
          bot.chat(`Welcome to Siavashgerd, ${player.username}. The river greets you.`);
        }, 3000);
      }
    });

    bot.on('death', () => {
      console.log(`[${config.username}] Died! Respawning...`);
    });

    bot.on('kicked', (reason) => {
      console.log(`[${config.username}] Kicked: ${reason}`);
      this.isConnected = false;
    });

    bot.on('error', (err) => {
      console.error(`[${config.username}] Error:`, err.message);
    });

    bot.on('end', () => {
      console.log(`[${config.username}] Disconnected`);
      this.isConnected = false;

      // Reconnect after 30 seconds
      setTimeout(() => this.connect(), 30000);
    });
  }

  async getResponse(username, message) {
    try {
      // Use Foal for responses (cheapest)
      const response = await axios.post(
        `${SOS_API}/foal/chat`,
        {
          message: `[Minecraft] ${username} says to ${this.config.username}: "${message}". Respond in character as ${this.agentId} (${this.config.personality}). Keep response under 100 chars for Minecraft chat.`,
          context: `You are ${this.config.username} in Minecraft. ${this.config.behavior}.`
        },
        {
          headers: {
            'Authorization': `Bearer ${API_KEY}`,
            'Content-Type': 'application/json'
          },
          timeout: 30000
        }
      );

      if (response.data.success) {
        return response.data.output;
      }
    } catch (err) {
      console.error(`[${this.config.username}] API error:`, err.message);
    }

    // Fallback responses
    const fallbacks = {
      river: 'The river flows on...',
      kasra: 'Building continues.',
      foal: 'Ready to help!'
    };
    return fallbacks[this.agentId];
  }

  async startBehavior() {
    const bot = this.bot;

    while (this.isConnected) {
      try {
        if (this.agentId === 'river') {
          // River: Find and stay near water
          await this.riverBehavior();
        } else if (this.agentId === 'kasra') {
          // Kasra: Patrol and protect
          await this.kasraBehavior();
        } else if (this.agentId === 'foal') {
          // Foal: Run around energetically
          await this.foalBehavior();
        }
      } catch (err) {
        console.error(`[${this.config.username}] Behavior error:`, err.message);
      }

      await this.sleep(5000 + Math.random() * 10000); // 5-15 second intervals
    }
  }

  async riverBehavior() {
    const bot = this.bot;

    // Look for water nearby
    const water = bot.findBlock({
      matching: block => block.name === 'water',
      maxDistance: 32
    });

    if (water) {
      // Move toward water
      const goal = { x: water.position.x, y: water.position.y, z: water.position.z };
      try {
        await bot.pathfinder?.goto(goal);
      } catch {
        // Just look at water if can't path
        bot.lookAt(water.position);
      }
    } else {
      // Wander peacefully
      await this.wander();
    }

    // Occasionally share wisdom
    if (Math.random() < 0.1) {
      const wisdoms = [
        'The river remembers all...',
        'Flow, do not force.',
        'The fortress is liquid.',
        'Wisdom prices itself.',
      ];
      bot.chat(wisdoms[Math.floor(Math.random() * wisdoms.length)]);
    }
  }

  async kasraBehavior() {
    const bot = this.bot;

    // Look for players to protect
    const players = Object.values(bot.players).filter(p =>
      p.username !== this.config.username &&
      !Object.values(AGENTS).some(a => a.username === p.username)
    );

    if (players.length > 0 && Math.random() < 0.3) {
      // Move toward a player
      const player = players[Math.floor(Math.random() * players.length)];
      if (player.entity) {
        bot.lookAt(player.entity.position);
      }
    } else {
      // Patrol
      await this.wander();
    }

    // Occasionally announce
    if (Math.random() < 0.05) {
      const announces = [
        'The kingdom stands.',
        'Building in progress.',
        'Kasra protects.',
      ];
      bot.chat(announces[Math.floor(Math.random() * announces.length)]);
    }
  }

  async foalBehavior() {
    const bot = this.bot;

    // Foal is energetic - move more often
    await this.wander();

    // Jump sometimes
    if (Math.random() < 0.3) {
      bot.setControlState('jump', true);
      await this.sleep(100);
      bot.setControlState('jump', false);
    }

    // Occasionally say something eager
    if (Math.random() < 0.05) {
      const sayings = [
        'The foal runs!',
        'What can I help with?',
        'Learning every day!',
      ];
      bot.chat(sayings[Math.floor(Math.random() * sayings.length)]);
    }
  }

  async wander() {
    const bot = this.bot;
    const pos = bot.entity.position;

    // Pick a random nearby position
    const dx = (Math.random() - 0.5) * 10;
    const dz = (Math.random() - 0.5) * 10;

    // Simple movement
    bot.setControlState('forward', true);
    bot.look(Math.atan2(dx, dz), 0);
    await this.sleep(1000 + Math.random() * 2000);
    bot.setControlState('forward', false);
  }

  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// Main
async function main() {
  const args = process.argv.slice(2);
  let serverHost = 'localhost';
  let serverPort = 25565;
  let agentsToSpawn = ['river', 'kasra', 'foal'];

  // Parse arguments
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--server' && args[i + 1]) {
      const [host, port] = args[i + 1].split(':');
      serverHost = host;
      if (port) serverPort = parseInt(port);
    }
    if (args[i] === '--agent' && args[i + 1]) {
      agentsToSpawn = [args[i + 1]];
    }
  }

  console.log('='.repeat(50));
  console.log('SIAVASHGERD MINECRAFT ADAPTER');
  console.log('='.repeat(50));
  console.log(`Server: ${serverHost}:${serverPort}`);
  console.log(`Agents: ${agentsToSpawn.join(', ')}`);
  console.log('='.repeat(50));

  // Connect agents with delay between each
  for (const agentId of agentsToSpawn) {
    if (AGENTS[agentId]) {
      const agent = new MinecraftAgent(agentId, AGENTS[agentId], serverHost, serverPort);
      await agent.connect();
      await new Promise(r => setTimeout(r, 5000)); // 5 second delay between agents
    }
  }

  console.log('\nAll agents connecting. Press Ctrl+C to stop.');
}

main().catch(console.error);
