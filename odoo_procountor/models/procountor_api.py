# -*- coding: utf-8 -*-
import json
import time
import logging
import base64
import requests

from odoo import models

_logger = logging.getLogger(__name__)

class ProcountorAPI(models.AbstractModel):
    _name = 'procountor.api'
    _description = 'Procountor API Client'

    # ----------------------------------------------------------------------
    # UTILITIES
    # ----------------------------------------------------------------------
    def _is_mock_mode(self):
        ICP = self.env["ir.config_parameter"].sudo()
        return ICP.get_param("procountor.mock_mode") in ["True", "true", "1"]

    def _base_url(self):
        ICP = self.env["ir.config_parameter"].sudo()
        url = ICP.get_param("procountor.base_url", "")
        return url.rstrip("/")

    def _client_id(self):
        return self.env['ir.config_parameter'].sudo().get_param('procountor.client_id')

    def _client_secret(self):
        return self.env['ir.config_parameter'].sudo().get_param('procountor.client_secret')

    # ----------------------------------------------------------------------
    # TOKEN
    # ----------------------------------------------------------------------
    def _get_access_token(self):

        # ✅ MOCK-TOKEN heti alkuun
        if self._is_mock_mode():
            token = {
                "access_token": "MOCK_TOKEN",
                "token_type": "Bearer",
                "expires_in": 3600,
                "mock": True
            }
            _logger.info("[Procountor MOCK] Token palautettu: %s", token)
            return token

        # ✅ Oikea token-haku (jos mock ei ole päällä)
        url = f"{self._base_url()}/oauth/token"
        auth = f"{self._client_id()}:{self._client_secret()}".encode("utf-8")
        b64 = base64.b64encode(auth).decode("ascii")

        headers = {
            "Authorization": f"Basic {b64}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {"grant_type": "client_credentials"}

        try:
            resp = requests.post(url, data=data, headers=headers, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            raise Exception(f"Procountor token haku epäonnistui: {str(e)}")

    # ----------------------------------------------------------------------
    # HEADERS
    # ----------------------------------------------------------------------
    def _headers(self):
        # Mock-tilassa ei tarvita oikeaa tokenia
        if self._is_mock_mode():
            return {
                "Content-Type": "application/json",
                "Authorization": "Bearer MOCK_TOKEN",
                "X-Procountor-Mock": "1",
            }

        token = self._get_access_token()
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token.get('access_token')}",
        }

    # ----------------------------------------------------------------------
    # REQUEST WRAPPER
    # ----------------------------------------------------------------------
    def _request(self, method, endpoint, payload=None, params=None):

        # ✅ MOCK-versio ohittaa kaiken oikean HTTP-liikenteen
        if self._is_mock_mode():
            return self._mock_response(method, endpoint, payload, params)

        # ✅ Oikea HTTP-kutsu
        url = f"{self._base_url()}{endpoint}"
        headers = self._headers()

        try:
            if method.upper() == "POST":
                resp = requests.post(url, json=payload, headers=headers, timeout=30)
            else:
                resp = requests.get(url, params=params, headers=headers, timeout=30)

            resp.raise_for_status()
            return resp.json() if resp.text else {}
        except Exception as e:
            raise Exception(f"Procountor API-kutsu epäonnistui: {method} {endpoint}: {str(e)}")

    # ----------------------------------------------------------------------
    # MOCK RESPONSES
    # ----------------------------------------------------------------------
    def _mock_response(self, method, endpoint, payload, params):

        _logger.info("[Procountor MOCK] %s %s payload=%s", method, endpoint, payload)

        # ✅ mock-token
        if endpoint == "/oauth/token":
            return {
                "access_token": "MOCK_TOKEN",
                "token_type": "Bearer",
                "expires_in": 3600,
                "mock": True,
            }

        # ✅ mock-laskun lähetys
        if endpoint == "/invoices" and method.upper() == "POST":
            mock_id = int(time.time())

            return {
                "status": "OK",
                "id": mock_id,
                "mock": True,
                "externalReference": f"MOCK-{mock_id}",
            }

        # ✅ mock-laskun haku
        if endpoint.startswith("/invoices/") and method.upper() == "GET":
            return {
                "status": "SENT",
                "mock": True,
                "id": endpoint.split("/")[-1],
            }

        # ✅ Oletus
        return {
            "status": "OK",
            "mock": True,
            "echo": payload,
        }

    # ----------------------------------------------------------------------
    # PUBLIC APIS
    # ----------------------------------------------------------------------
    def api_post(self, endpoint, payload):
        return self._request("POST", endpoint, payload=payload)

    def api_get(self, endpoint, params=None):
        return self._request("GET", endpoint, params=params)
