# Adapter Scope: The Steering Wheel & Dashboard

## Philosophy
This is how different users "drive" the car. The car is the same, but the interface changes based on the user.

## Components
*   **CLI (`scopes/adapters/cli`):**
    *   **For You (Freelancer/Dev):** "Service Mode".
    *   Raw access, deep diagnostics, coding tools.
    *   The Scepter of the Sovereign.
*   **Telegram (`scopes/adapters/telegram`):**
    *   **For the Old Man / Gamer:** "Key Fob / Mobile App".
    *   Simple buttons: "Witness", "Earn", "Status".
    *   Low bandwidth, high accessibility.
*   **Web (`scopes/adapters/web`):**
    *   **For Enterprise / SME:** "Fleet Command Center".
    *   Dashboards, Analytics, Team Management.
    *   Visualizing the Hive.

## Rule of Access
Adapters transform user intent into standardized Bus Messages. They never execute logic themselves.
