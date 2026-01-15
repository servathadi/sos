# WordPress MCP Pattern

**Reusable pattern for exposing any WordPress site to AI agents via MCP.**

## Overview

Three approaches to connect WordPress to AI agents:

| Approach | Best For | Complexity |
|----------|----------|------------|
| **Official Remote MCP** | Standard WordPress sites | Low |
| **Custom Agent MCP** | Custom data models, specialized agents | Medium |
| **WordPress MCP Adapter** | Local sites, WP-CLI access | Low |

## Option 1: Official Automattic Remote MCP (Recommended)

Use [@automattic/mcp-wordpress-remote](https://github.com/Automattic/mcp-wordpress-remote) for any WordPress site:

```json
{
  "mcpServers": {
    "wordpress": {
      "command": "npx",
      "args": ["-y", "@automattic/mcp-wordpress-remote"],
      "env": {
        "WP_API_URL": "https://your-site.com",
        "WP_API_USERNAME": "username",
        "WP_API_PASSWORD": "app_password",
        "OAUTH_ENABLED": "false"
      }
    }
  }
}
```

**Authentication options:**
- OAuth 2.1 (browser flow)
- Application Password (recommended for automation)
- JWT Token

## Option 2: Custom Agent MCP (Our Pattern)

For specialized agents with custom endpoints (like Dandan for DentalNearYou):

This pattern creates a bridge between WordPress sites and AI agents (Claude, SOS) using:
1. **WordPress Plugin** - REST API endpoints with API key auth
2. **MCP Server** - Node.js server exposing tools to Claude Desktop/SOS

## Quick Start

To add MCP to any WordPress site:

1. Copy the plugin template to your WordPress
2. Customize endpoints for your data model
3. Build the MCP server
4. Add to Claude Desktop config

## Architecture

```
┌──────────────────┐     stdio      ┌──────────────────┐     HTTPS     ┌──────────────────┐
│   Claude/SOS     │ ◄────────────► │   MCP Server     │ ◄───────────► │   WordPress      │
│   (MCP Client)   │                │   (Node.js)      │               │   (REST API)     │
└──────────────────┘                └──────────────────┘               └──────────────────┘
```

## WordPress Plugin Template

### File: `{agent-name}-agent.php`

```php
<?php
/**
 * Plugin Name: {Agent Name} Agent
 * Description: AI agent REST API for {Site Name}
 * Version: 1.0.0
 */

if (!defined('ABSPATH')) exit;

class Agent_Name_Agent {
    private $api_key;

    public function __construct() {
        $this->api_key = get_option('{agent}_api_key');
        if (!$this->api_key) {
            $this->api_key = '{agent}_' . wp_generate_password(32, false);
            update_option('{agent}_api_key', $this->api_key);
        }
        add_action('rest_api_init', [$this, 'register_routes']);
    }

    public function register_routes() {
        $namespace = '{agent}/v1';

        // Health check (always include)
        register_rest_route($namespace, '/health', [
            'methods' => 'GET',
            'callback' => [$this, 'health_check'],
            'permission_callback' => [$this, 'check_api_key'],
        ]);

        // Site info (always include)
        register_rest_route($namespace, '/site-info', [
            'methods' => 'GET',
            'callback' => [$this, 'site_info'],
            'permission_callback' => [$this, 'check_api_key'],
        ]);

        // Add your custom endpoints here...
    }

    public function check_api_key($request) {
        $provided_key = $request->get_header('X-API-Key');
        return $provided_key === $this->api_key;
    }

    public function health_check() {
        return [
            'status' => 'healthy',
            'agent' => '{Agent Name}',
            'version' => '1.0.0',
            'site' => get_bloginfo('name'),
            'timestamp' => current_time('mysql'),
        ];
    }

    public function site_info() {
        return [
            'site_name' => get_bloginfo('name'),
            'site_url' => get_site_url(),
            'agent' => '{Agent Name}',
            'agent_version' => '1.0.0',
            'wordpress_version' => get_bloginfo('version'),
            'theme' => wp_get_theme()->get('Name'),
        ];
    }
}

new Agent_Name_Agent();
```

## MCP Server Template

### File: `src/index.ts`

```typescript
#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from "@modelcontextprotocol/sdk/types.js";

// Configuration from environment
const WP_URL = process.env.{AGENT}_WP_URL || "https://example.com";
const API_KEY = process.env.{AGENT}_API_KEY || "";

// API helper
async function apiCall(
  endpoint: string,
  method: string = "GET",
  body?: object
): Promise<any> {
  const url = `${WP_URL}/wp-json/{agent}/v1${endpoint}`;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (API_KEY) {
    headers["X-API-Key"] = API_KEY;
  }

  const options: RequestInit = { method, headers };

  if (body && method !== "GET") {
    options.body = JSON.stringify(body);
  }

  const response = await fetch(url, options);

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`API Error ${response.status}: ${error}`);
  }

  return response.json();
}

// Define tools
const tools: Tool[] = [
  {
    name: "{agent}_health",
    description: "Check site health and agent status",
    inputSchema: {
      type: "object",
      properties: {},
    },
  },
  {
    name: "{agent}_site_info",
    description: "Get site information and stats",
    inputSchema: {
      type: "object",
      properties: {},
    },
  },
  // Add your custom tools here...
];

// Tool handlers
async function handleTool(name: string, args: Record<string, unknown>): Promise<string> {
  switch (name) {
    case "{agent}_health":
      return JSON.stringify(await apiCall("/health"), null, 2);

    case "{agent}_site_info":
      return JSON.stringify(await apiCall("/site-info"), null, 2);

    // Add your custom handlers here...

    default:
      throw new Error(`Unknown tool: ${name}`);
  }
}

// Create and run server
const server = new Server(
  { name: "{agent}-mcp", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools }));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    const result = await handleTool(name, (args as Record<string, unknown>) || {});
    return { content: [{ type: "text", text: result }] };
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return { content: [{ type: "text", text: `Error: ${errorMessage}` }], isError: true };
  }
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("{Agent} MCP Server running on stdio");
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
```

### File: `package.json`

```json
{
  "name": "{agent}-mcp-server",
  "version": "1.0.0",
  "type": "module",
  "bin": {
    "{agent}-mcp": "./dist/index.js"
  },
  "scripts": {
    "build": "tsc",
    "start": "node dist/index.js"
  },
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.0.0"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "typescript": "^5.0.0"
  }
}
```

### File: `tsconfig.json`

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "declaration": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

## Claude Desktop Configuration

Add to `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "{agent}": {
      "command": "node",
      "args": ["/path/to/mcp-server/dist/index.js"],
      "env": {
        "{AGENT}_WP_URL": "https://your-site.com",
        "{AGENT}_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

## Common Endpoint Patterns

### CRUD for Custom Post Type

```php
// GET /items - List items
register_rest_route($namespace, '/items', [
    'methods' => 'GET',
    'callback' => function($request) {
        $args = [
            'post_type' => 'your_cpt',
            'posts_per_page' => $request->get_param('per_page') ?: 20,
            'paged' => $request->get_param('page') ?: 1,
        ];
        $posts = get_posts($args);
        return array_map([$this, 'format_item'], $posts);
    },
    'permission_callback' => [$this, 'check_api_key'],
]);

// POST /items - Create item
register_rest_route($namespace, '/items', [
    'methods' => 'POST',
    'callback' => function($request) {
        $data = $request->get_json_params();
        $post_id = wp_insert_post([
            'post_type' => 'your_cpt',
            'post_title' => $data['name'],
            'post_content' => $data['description'] ?? '',
            'post_status' => $data['status'] ?? 'draft',
        ]);
        return ['id' => $post_id, 'success' => true];
    },
    'permission_callback' => [$this, 'check_api_key'],
]);

// PUT /items/{id} - Update item
register_rest_route($namespace, '/items/(?P<id>\d+)', [
    'methods' => 'PUT',
    'callback' => function($request) {
        $id = $request->get_param('id');
        $data = $request->get_json_params();
        wp_update_post([
            'ID' => $id,
            'post_title' => $data['name'] ?? get_the_title($id),
        ]);
        return ['id' => $id, 'success' => true];
    },
    'permission_callback' => [$this, 'check_api_key'],
]);
```

### Taxonomy Endpoints

```php
// GET /categories
register_rest_route($namespace, '/categories', [
    'methods' => 'GET',
    'callback' => function() {
        $terms = get_terms(['taxonomy' => 'your_taxonomy', 'hide_empty' => false]);
        return array_map(function($term) {
            return ['id' => $term->term_id, 'name' => $term->name, 'slug' => $term->slug];
        }, $terms);
    },
    'permission_callback' => [$this, 'check_api_key'],
]);
```

### Mirror Memory Integration

```php
// POST /mirror/store
register_rest_route($namespace, '/mirror/store', [
    'methods' => 'POST',
    'callback' => function($request) {
        $data = $request->get_json_params();
        $mirror_url = 'https://mumega.com/mirror/store';
        $response = wp_remote_post($mirror_url, [
            'headers' => [
                'Authorization' => 'Bearer ' . MIRROR_TOKEN,
                'Content-Type' => 'application/json',
            ],
            'body' => json_encode([
                'agent' => '{agent}',
                'context_id' => $data['context'] ?? 'general',
                'text' => $data['text'],
            ]),
        ]);
        return json_decode(wp_remote_retrieve_body($response), true);
    },
    'permission_callback' => [$this, 'check_api_key'],
]);
```

## Implementations

| Agent | Site | Plugin | Status |
|-------|------|--------|--------|
| Dandan | dentalnearyou.com | dandan-agent | Active |

## Installation Checklist

- [ ] Copy plugin to `wp-content/plugins/`
- [ ] Activate plugin in WordPress admin
- [ ] Note the generated API key from `wp_options`
- [ ] Clone MCP server template
- [ ] Run `npm install && npm run build`
- [ ] Add to Claude Desktop config
- [ ] Test with `curl -H "X-API-Key: xxx" https://site.com/wp-json/{agent}/v1/health`

## Security Notes

1. API keys are stored in `wp_options` table
2. Always use HTTPS in production
3. Consider IP whitelisting for sensitive operations
4. Rotate API keys periodically
5. Log API access for audit

## Option 3: WordPress MCP Adapter (Local/WP-CLI)

For local WordPress installations with WP-CLI access, use the official [WordPress/mcp-adapter](https://github.com/WordPress/mcp-adapter):

```bash
composer require wordpress/abilities-api wordpress/mcp-adapter
```

Claude Desktop config:
```json
{
  "mcpServers": {
    "wordpress-local": {
      "command": "wp",
      "args": [
        "--path=/path/to/wordpress",
        "mcp-adapter",
        "serve",
        "--server=mcp-adapter-default-server",
        "--user=admin"
      ]
    }
  }
}
```

## When to Use Which

| Scenario | Recommended Approach |
|----------|---------------------|
| Quick WordPress access | Option 1: Official Remote MCP |
| Custom agent with specialized tools | Option 2: Custom Agent MCP |
| Local development with WP-CLI | Option 3: MCP Adapter |
| Listeo/directory sites | Option 2: Custom Agent MCP |
| Standard blog/WooCommerce | Option 1: Official Remote MCP |

## Official Resources

- [WordPress/mcp-adapter](https://github.com/WordPress/mcp-adapter) - Official WordPress MCP adapter
- [Automattic/mcp-wordpress-remote](https://github.com/Automattic/mcp-wordpress-remote) - Remote WordPress MCP
- [mcp-wp Organization](https://github.com/mcp-wp) - Community MCP for WordPress
- [MCP for WordPress Docs](https://mcp-wp.github.io/docs) - Documentation

## Related

- [MCP Protocol Docs](https://modelcontextprotocol.io/)
- [WordPress REST API](https://developer.wordpress.org/rest-api/)
- [SOS Architecture](/home/mumega/SOS/docs/docs/architecture/README.md)
