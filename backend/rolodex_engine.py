# rolodex_engine.py
# -----------------------------------------------------------------------------
# STRATEX™ GM Rolodex Engine — verbatim user spec + multi-store registry.
# Pure addition (preservation lock); no existing files modified.
# -----------------------------------------------------------------------------
from __future__ import annotations
from typing import Dict, Any


class GM_RolodexEngine:
    """Autonomous account registry engine monitoring public building datasets for contractor conversion opportunities."""
    def __init__(self, store_territory_bounding: str, assigned_salesrep_id: str):
        self.territory = store_territory_bounding
        self.default_rep = assigned_salesrep_id
        self.active_customers: Dict[str, Dict[str, Any]] = {}
        self.target_customers: Dict[str, Dict[str, Any]] = {}

    def evaluate_discovered_entity(self, company_name: str, trade_scope: str, localization: str) -> None:
        if company_name in self.active_customers or company_name in self.target_customers:
            return

        self.target_customers[company_name] = {
            "scope": trade_scope,
            "city": localization,
            "assigned_rep": self.default_rep,
            "conversion_invoiced": False,
        }

    def process_first_invoice(self, company_name: str, initial_invoice_value: float) -> None:
        if company_name in self.target_customers:
            account_data = self.target_customers.pop(company_name)
            account_data["conversion_invoiced"] = True
            account_data["initial_order_value"] = initial_invoice_value
            self.active_customers[company_name] = account_data


class RolodexRegistry:
    """One GM_RolodexEngine per store_territory."""
    def __init__(self):
        self.by_territory: Dict[str, GM_RolodexEngine] = {}

    def ensure(self, territory: str, default_rep: str) -> GM_RolodexEngine:
        e = self.by_territory.get(territory)
        if not e:
            e = GM_RolodexEngine(territory, default_rep)
            self.by_territory[territory] = e
        return e


REGISTRY = RolodexRegistry()
