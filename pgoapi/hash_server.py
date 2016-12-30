from __future__ import absolute_import

import ctypes
import base64
import requests

from pgoapi.hash_engine import HashEngine
from pgoapi.exceptions import ServerBusyOrOfflineException, ServerSideAccessForbiddenException, UnexpectedResponseException

class HashServer(HashEngine):
    _session = requests.session()
    _session.verify = True
    _session.headers.update({'User-Agent': 'Python pgoapi @pogodev'})
    endpoint = "https://pokehash.buddyauth.com/api/v121_2/hash"

    def __init__(self, auth_token):
        self.headers = {'content-type': 'application/json', 'Accept' : 'application/json', 'X-AuthToken' : auth_token}

    def hash(self, timestamp, latitude, longitude, altitude, authticket, sessiondata, requestslist):
        self.location_hash = None
        self.location_auth_hash = None
        self.request_hashes = []

        payload = {}
        payload["Timestamp"] = timestamp
        payload["Latitude"] = latitude
        payload["Longitude"] = longitude
        payload["Altitude"] = altitude
        payload["AuthTicket"] = base64.b64encode(authticket).decode('ascii')
        payload["SessionData"] = base64.b64encode(sessiondata).decode('ascii')
        payload["Requests"] = []
        for request in requestslist:
            payload["Requests"].append(base64.b64encode(request.SerializeToString()).decode('ascii'))

        # ask hash server how is it going ? and get json
        try:
            response = self._session.post(self.endpoint, json=payload, headers=self.headers, timeout=30)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as error:
            raise ServerBusyOrOfflineException(error)

        if response.status_code == 400:
            raise UnexpectedResponseException("400 : Bad request, error: {}".format(response.text))
        elif response.status_code == 401:
            raise ServerSideAccessForbiddenException("401 : You are not authorized to use this service")
        elif response.status_code == 429:
            raise ServerSideAccessForbiddenException("429 : Request limited, error: {}".format(response.text))
        elif response.status_code != 200:
            error = 'Unexpected HTTP server response - needs 200 got {}'.format(response.status_code)
            raise UnexpectedResponseException(error)

        if not response.content:
            raise UnexpectedResponseException

        response_parsed = response.json()
        self.location_auth_hash = ctypes.c_int32(response_parsed['locationAuthHash']).value
        self.location_hash = ctypes.c_int32(response_parsed['locationHash']).value

        for request_hash in response_parsed['requestHashes']:
            self.request_hashes.append(ctypes.c_int64(request_hash).value)
