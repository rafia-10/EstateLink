"""Database connection and cursor implementation using Supabase REST API"""
from datetime import datetime, timedelta
import logging
import httpx
from .config import SUPABASE_URL, SUPABASE_HEADERS

logger = logging.getLogger(__name__)


class SupabaseConnection:
    """Mock connection object that uses Supabase REST API"""
    def __init__(self):
        self.url = SUPABASE_URL
        self.headers = SUPABASE_HEADERS

    def cursor(self):
        return SupabaseCursor(self.url, self.headers)

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


class SupabaseCursor:
    """Mock cursor that executes queries via Supabase REST API"""

    CONTRACT_COLS = [
        ('contract_id',), ('tenant_id',), ('property_name',), ('location',),
        ('start_date',), ('expiry_date',), ('annual_rent',), ('num_checks',),
        ('payment_method',), ('agent_name',), ('agent_email',),
        ('tenant_name',), ('tenant_email',), ('tenant_phone',)
    ]

    def __init__(self, url, headers):
        self.url = url
        self.headers = headers
        self.description = None
        self._results = []
        self._row_index = 0

    @staticmethod
    def _to_date(val):
        """Convert date string to date object if needed"""
        return datetime.fromisoformat(val).date() if isinstance(val, str) else val

    def _fetch(self, endpoint):
        """GET request, return JSON or empty list"""
        r = httpx.get(f"{self.url}/{endpoint}", headers=self.headers)
        return r.json() if r.status_code == 200 else []

    def _build_contract_row(self, c):
        """Build contract row from API data"""
        tenant = c.get('tenants', {})
        return (
            c['id'], c['tenant_id'], c['property_name'], c['location'],
            self._to_date(c['start_date']), self._to_date(c['expiry_date']),
            c['annual_rent'], c['num_checks'], c['payment_method'],
            c['agent_name'], c['agent_email'],
            tenant.get('name'), tenant.get('email'), tenant.get('phone')
        )

    def _build_check_row(self, ch, today, upcoming=False):
        """Build check row from API data"""
        contract = ch.get('contracts', {})
        tenant = contract.get('tenants', {}) if contract else {}
        check_date = self._to_date(ch['check_date'])
        days = (check_date - today).days if upcoming else (today - check_date).days

        return (
            ch['id'], ch['check_no'], ch['check_date'], ch['amount'], ch['contract_id'],
            contract.get('property_name'), contract.get('location'),
            tenant.get('name'), tenant.get('email'), tenant.get('phone'),
            contract.get('agent_name'), contract.get('agent_email'), days
        )

    def execute(self, query, params=None):
        """Execute SQL-like operations via REST API"""
        self._row_index = 0
        q = query.lower().strip()

        if "count(*)" in q:
            self._handle_count(query, params)
        elif q.startswith("select"):
            self._handle_select(query, params)
        elif q.startswith("insert"):
            self._handle_insert(query, params)
        else:
            logger.warning(f"Unsupported query: {query[:50]}...")

    def _handle_select(self, query, params):
        """Handle SELECT queries"""
        q = query.lower()

        # Contracts with tenants
        if "from contracts" in q and "join tenants" in q:
            endpoint = "contracts?select=*,tenants(name,email,phone)"
            if params and len(params) == 1:
                endpoint += f"&id=eq.{params[0]}"
            contracts = self._fetch(endpoint)
            self._results = [self._build_contract_row(c) for c in contracts]
            self.description = self.CONTRACT_COLS

        # Checks for a contract
        elif "from checks" in q and "where contract_id" in q:
            cid = params[0] if params else None
            checks = self._fetch(f"checks?contract_id=eq.{cid}&order=check_date.asc")
            self._results = [(c['id'], c['check_no'], c['check_date'], c['amount']) for c in checks]
            self.description = [('id',), ('check_no',), ('check_date',), ('amount',)]

        # Overdue or upcoming checks
        elif "from checks ch" in q and "join contracts" in q:
            today = params[0] if params else datetime.now().date()
            check_cols = [
                ('check_id',), ('check_no',), ('check_date',), ('amount',), ('contract_id',),
                ('property_name',), ('location',), ('tenant_name',), ('tenant_email',),
                ('tenant_phone',), ('agent_name',), ('agent_email',)
            ]

            if "where ch.check_date <" in q:
                checks = self._fetch(f"checks?select=*,contracts(property_name,location,agent_name,agent_email,tenants(name,email,phone))&check_date=lt.{today}&order=check_date.asc")
                self._results = [self._build_check_row(ch, today) for ch in checks]
                self.description = check_cols + [('days_overdue',)]
            elif "where ch.check_date between" in q:
                future = params[2] if params and len(params) >= 3 else today + timedelta(days=30)
                checks = self._fetch(f"checks?select=*,contracts(property_name,location,agent_name,agent_email,tenants(name,email,phone))&check_date=gte.{today}&check_date=lte.{future}&order=check_date.asc")
                self._results = [self._build_check_row(ch, today, True) for ch in checks]
                self.description = check_cols + [('days_until_due',)]

        # Expiry alerts
        elif "where c.expiry_date between" in q:
            today = params[1] if params and len(params) >= 2 else datetime.now().date()
            threshold = params[2] if params and len(params) >= 3 else today + timedelta(days=100)
            contracts = self._fetch(f"contracts?select=*,tenants(name,email,phone)&expiry_date=gte.{today}&expiry_date=lte.{threshold}&order=expiry_date.asc")

            self._results = []
            for c in contracts:
                tenant = c.get('tenants', {})
                days = (self._to_date(c['expiry_date']) - today).days
                self._results.append((
                    c['id'], c['property_name'], c['location'], c['start_date'], c['expiry_date'],
                    c['annual_rent'], c['num_checks'], c['payment_method'],
                    c['agent_name'], c['agent_email'],
                    tenant.get('name'), tenant.get('email'), tenant.get('phone'), days
                ))
            self.description = [
                ('contract_id',), ('property_name',), ('location',), ('start_date',), ('expiry_date',),
                ('annual_rent',), ('num_checks',), ('payment_method',), ('agent_name',), ('agent_email',),
                ('tenant_name',), ('tenant_email',), ('tenant_phone',), ('days_until_expiry',)
            ]

        # Generic contracts
        else:
            contracts = self._fetch("contracts?select=*&order=id.asc")
            self._results = [
                (c['id'], self._to_date(c['start_date']), self._to_date(c['expiry_date']),
                 c['annual_rent'], c['num_checks'])
                for c in contracts
            ]
            self.description = [('id',), ('start_date',), ('expiry_date',), ('annual_rent',), ('num_checks',)]

    def _handle_count(self, query, params):
        """Handle COUNT queries"""
        q = query.lower()
        if "from checks where contract_id" in q:
            result = self._fetch(f"checks?contract_id=eq.{params[0]}&select=count")
            self._results = [(result[0]['count'] if result else 0,)]
        elif "from checks where check_no" in q:
            result = self._fetch(f"checks?check_no=eq.{params[0]}&select=id")
            self._results = [(result[0]['id'],)] if result else []

    def _handle_insert(self, query, params):
        """Handle INSERT queries"""
        if "into checks" in query.lower():
            cid, check_no, check_date, amount = params
            data = {"contract_id": cid, "check_no": check_no, "check_date": str(check_date), "amount": float(amount)}
            r = httpx.post(f"{self.url}/checks", headers=self.headers, json=data)
            logger.debug(f"Insert check: {check_no}, status: {r.status_code}")

    def fetchall(self):
        return self._results

    def fetchone(self):
        if self._results and self._row_index < len(self._results):
            result = self._results[self._row_index]
            self._row_index += 1
            return result
        return (0,) if not self._results and self.description is None else None

    def close(self):
        pass
