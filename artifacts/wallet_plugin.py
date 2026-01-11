"""
wallet_plugin.py

A simple token wallet plugin for the SOS Economy Service.
"""

from typing import Dict, Union, Any
import asyncio


class InsufficientFundsError(Exception):
    """
    Exception raised when attempting to debit an amount exceeding the wallet balance.
    """

    def __init__(self, user_id: str, requested_amount: float, current_balance: float):
        self.user_id = user_id
        self.requested_amount = requested_amount
        self.current_balance = current_balance
        super().__init__(
            f"Insufficient funds for user {user_id}. "
            f"Requested: {requested_amount}, Balance: {current_balance}"
        )


class SimpleTokenWallet:
    """
    A simple in-memory token wallet.
    """

    def __init__(self):
        """
        Initializes the wallet with an empty balance for all users.
        """
        self._balances: Dict[str, float] = {}

    async def get_balance(self, user_id: str) -> float:
        """
        Retrieves the token balance for a given user.

        Args:
            user_id: The unique identifier of the user.

        Returns:
            The user's token balance, or 0.0 if the user doesn't have a balance yet.
        """
        await asyncio.sleep(0)  # Simulate a non-blocking operation

        return self._balances.get(user_id, 0.0)

    async def credit(self, user_id: str, amount: float) -> None:
        """
        Credits (adds) tokens to a user's wallet.

        Args:
            user_id: The unique identifier of the user.
            amount: The amount of tokens to credit.  Must be a non-negative number.

        Raises:
            ValueError: if amount is negative.
        """
        await asyncio.sleep(0)  # Simulate a non-blocking operation

        if amount < 0:
            raise ValueError("Credit amount must be non-negative.")

        if user_id not in self._balances:
            self._balances[user_id] = 0.0

        self._balances[user_id] += amount

    async def debit(self, user_id: str, amount: float) -> None:
        """
        Debits (subtracts) tokens from a user's wallet.

        Args:
            user_id: The unique identifier of the user.
            amount: The amount of tokens to debit. Must be a non-negative number.

        Raises:
            InsufficientFundsError: If the user's balance is insufficient.
            ValueError: if amount is negative.
        """
        await asyncio.sleep(0)  # Simulate a non-blocking operation

        if amount < 0:
            raise ValueError("Debit amount must be non-negative.")

        balance = await self.get_balance(user_id)

        if balance < amount:
            raise InsufficientFundsError(user_id, amount, balance)

        self._balances[user_id] = balance - amount