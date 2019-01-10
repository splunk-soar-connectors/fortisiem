# Phantom App imports
import phantom.app as phantom
from phantom.base_connector import BaseConnector
from phantom.action_result import ActionResult

# Usage of the consts file is recommended
# from fortisiem_consts import *
import requests
import json
import xml.etree.ElementTree as ET
import queryxml
from datetime import datetime
import re
from bs4 import BeautifulSoup
from HTMLParser import HTMLParseError


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class FortisiemConnector(BaseConnector):

    def __init__(self):

        # Call the BaseConnectors init first
        super(FortisiemConnector, self).__init__()

        self._state = None
        self._base_url = None

    def initialize(self):

        # Load the state in initialize, use it to store data that needs to be accessed across actions
        self._state = self.load_state()

        # get the asset config
        config = self.get_config()
        self._base_url = 'https://{0}/'.format(config['server'])
        # combine organization and username to get fortisiem login username
        self._username = "{}/{}".format(config.get('org'), config.get('username'))
        self._password = config.get('password')
        self._incidentCategories = config.get('incidentCategories', None)
        self._verify_server_cert = config.get('verify_server_cert', False)
        self._timeWindow = config.get('timeWindow')
        self._minimumSeverity = config.get('minimumSeverity')

        return phantom.APP_SUCCESS

    def convert_time(self, utctime):

        # Extract the year and the rest of date from utc time. Discard the timezone
        match = re.search(r'(?P<restofdate>.*)\s(?P<timezone>[A-Z]{2,4})\s(?P<year>[0-9]{4})', utctime)
        restofdate = match.group('restofdate')
        # timezone = match.group('timezone')
        year = match.group('year')

        naivetime = "{0} UTC {1}".format(restofdate, year)
        # %a Weekday as locale's abbreviated name.
        # %b Month as locale's abbreviated name.
        # %d Day of the month as a zero-padded decimal number.
        # %H Hour (24-hour clock) as a zero-padded decimal number.
        # %M Minute as a zero-padded decimal number.
        # %S Second as a zero-padded decimal number.
        # %Z Time zone name
        # %Y Year with century as a decimal number.
        # Example: 'Mon Jul 30 17:28:00 PDT 2018'
        isotime = datetime.strptime(naivetime, '%a %b %d %H:%M:%S %Z %Y')
        isotimewithzulu = "{0}{1}".format(isotime.isoformat(), "Z")
        return isotimewithzulu

    def _process_empty_reponse(self, response, action_result):

        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(action_result.set_status(phantom.APP_ERROR, "Empty response and no information in the header"), None)

    def _process_html_response(self, response, action_result):

        # An html response, treat it like an error
        status_code = response.status_code

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            error_text = soup.text
            split_lines = error_text.split('\n')
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = '\n'.join(split_lines)
        except HTMLParseError:
            error_text = "Cannot parse error details"

        message = "Status Code: {0}. Data from server:\n{1}\n".format(status_code, error_text)

        message = message.replace('{', '{{').replace('}', '}}')

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, r, action_result):

        # Try a json parse
        try:
            resp_json = r.json()
        except Exception as e:
            return RetVal(action_result.set_status(phantom.APP_ERROR, "Unable to parse JSON response. Error: {0}".format(str(e))), None)

        # Please specify the status codes here
        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # You should process the error returned in the json
        # Use "replace" so original curly braces are preserved
        message = "Error from server. Status Code: {0} Data from server: {1}".format(
                r.status_code, r.text.replace('{', '{{').replace('}', '}}'))

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, r, action_result):

        # store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, 'add_debug_data'):
            action_result.add_debug_data({'r_status_code': r.status_code})
            action_result.add_debug_data({'r_text': r.text})
            action_result.add_debug_data({'r_headers': r.headers})

        # Process each 'Content-Type' of response separately

        # Process a json response
        if 'json' in r.headers.get('Content-Type', ''):
            return self._process_json_response(r, action_result)

        # Process an HTML resonse, Do this no matter what the api talks.
        # There is a high chance of a PROXY in between phantom and the rest of
        # world, in case of errors, PROXY's return HTML, this function parses
        # the error and adds it to the action_result.
        if 'html' in r.headers.get('Content-Type', ''):
            return self._process_html_response(r, action_result)

        # Process return type "text/plain"
        # Return the text as response
        if 'plain' in r.headers.get('Content-Type', ''):
            return RetVal(phantom.APP_SUCCESS, r.text)

        # Process return type "text/xml"
        # # Return response as plain text
        if 'xml' in r.headers.get('Content-Type', ''):
            return RetVal(phantom.APP_SUCCESS, r.text)

        # it's not content-type that is to be parsed, handle an empty response
        if not r.text:
            return self._process_empty_reponse(r, action_result)

        # everything else is actually an error at this point
        message = "Can't process response from server. Status Code: {0} Data from server: {1}".format(
                r.status_code, r.text.replace('{', '{{').replace('}', '}}'))

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _make_rest_call(self, method, endpoint, action_result, body=None, content_type=None):

        # Create URL for request
        url = self._base_url + endpoint

        # Create Content-Type header
        if content_type:
            headers = {'Content-Type': content_type}
        else:
            headers = None

        # Get request function based on the method type
        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, "Invalid method: {0}".format(method)), None)

        # Make HTTP request call
        try:
            r = request_func(
                            url,
                            auth=(self._username, self._password),
                            data=body,
                            headers=headers,
                            verify=self._verify_server_cert)
        except Exception as e:
            return RetVal(action_result.set_status(phantom.APP_ERROR, "Error Connecting to server. Details: {0}".format(str(e))), None)

        return self._process_response(r, action_result)

    def _handle_test_connectivity(self, param):

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        self.save_progress("Connecting to endpoint")

        # To test connectivity and credentials make empty request to device discovery endopoint
        query = queryxml.create_null_discovery_request()
        ret_val, response = self._make_rest_call(
                                 method="put",
                                 endpoint="phoenix/rest/deviceMon/discover",
                                 action_result=action_result,
                                 body=query,
                                 content_type="text/xml")

        if (phantom.is_fail(ret_val)):
            # the call to the 3rd party device or service failed
            # action result should contain all the error details so just return from here
            self.save_progress("Test Connectivity Failed.")
            return action_result.get_status()

        # Return success
        self.save_progress("Test Connectivity Passed.")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_events(self, action_result):

        try:
            query = queryxml.create_query_xml(self._incidentCategories, self._timeWindow, self._minimumSeverity)

            # Initiate query
            ret_val, text_response = self._make_rest_call(
                            method="post",
                            endpoint="phoenix/rest/query/eventQuery",
                            action_result=action_result,
                            body=query,
                            content_type="text/xml")
            queryId = text_response

            # Check query progress
            progress = 0
            while (progress < 100):
                print "Progress = {0}%".format(progress)
                ret_val, text_response = self._make_rest_call(
                            method="get",
                            endpoint="phoenix/rest/query/progress/{0}".format(queryId),
                            action_result=action_result)
                progress = int(text_response)

            # Keep fetching events until all queried events have been returned
            total_event_count = None
            queried_all_events = False
            events = []
            first_event = 0
            increment = 1000
            last_event = increment

            while not queried_all_events:

                # Get events in xml format
                ret_val, xml_response = self._make_rest_call(
                                method="get",
                                endpoint="phoenix/rest/query/events/{0}/{1}/{2}".format(queryId, first_event, last_event),
                                action_result=action_result)

                # Convert xml response into a list of events
                # Each event is a dictionary of attributes
                root = ET.fromstring(xml_response)
                for event in root.iter("event"):
                    event_dict = {}
                    for attribute in event.iter("attribute"):
                        event_dict[attribute.get("name")] = attribute.text
                    events.append(event_dict)

                # Get the total event count on the first loop
                if not total_event_count:
                    total_event_count = int(root.get("totalCount", 0))
                    self.save_progress("FortiSIEM found {} events matching query".format(total_event_count))

                if last_event < total_event_count:
                    self.save_progress("Downloaded events {} of {} from FortiSIEM".format(last_event, total_event_count))
                    first_event += increment
                    last_event += increment
                else:
                    self.save_progress("Download events complete!".format(total_event_count, total_event_count))
                    queried_all_events = True

            return events

        except Exception as e:
            raise e

    def _handle_on_poll(self, param):

        # Log current action
        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Get events from the FortiSIEM and process them as Phantom containers
        try:
            events = self._get_events(action_result)
            for event in events:

                # Map attributes returned from FortiSIEM into Common Event Format (cef)
                cef = {
                    'baseEventCount': event.get('count', ""),
                    'cs1': self.convert_time(event.get('incidentLastSeen', "")),
                    'cs1Label': "Incident Last Seen",
                    'cs2': json.dumps(event),
                    'cs2Label': "Raw Event Data",
                    'cs3': event.get('incidentTarget', ""),
                    'cs3Label': "Incident Target",
                    'deviceHostname': event.get('incidentRptDevName', ""),
                    'deviceAddress': event.get('incidentRptIp', ""),
                    'sourceAddress': event.get('srcipAddr', "")
                }

                # Create Phantom container object to store event
                container = {}
                container['name'] = event['eventName']
                sdi = event.get('incidentId', "")
                container['source_data_identifier'] = sdi
                container['artifacts'] = [
                    {
                        'cef': cef,
                        'label': 'event',
                        'data': json.dumps(event),
                        'description': event.get('incidentDetail', ""),
                        'name': event.get('eventName', ""),
                        'type': event.get('eventType', ""),
                        'severity': event.get('eventSeverityCat', ""),
                        'source_data_identifier': sdi,
                        'start_time': self.convert_time(event.get('incidentFirstSeen', ""))
                    }
                ]
                ret_val, msg, cid = self.save_container(container)
                if phantom.is_fail(ret_val):
                    self.save_progress("Error saving container: {}".format(msg))
                    self.debug_print("Error saving container: {} -- CID: {}".format(msg, cid))

            # Log results
            action_result.add_data(events)
            summary = action_result.update_summary({})
            summary['Number of Events Found'] = len(events)
            self.save_progress("Phantom imported {0} events".format(len(events)))
            return action_result.set_status(phantom.APP_SUCCESS)

        except Exception as e:
            self.save_progress("Exception = {0}".format(str(e)))
            return action_result.set_status(phantom.APP_ERROR, "Error getting events. Details: {0}".format(str(e)))

    def handle_action(self, param):

        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == 'test_connectivity':
            ret_val = self._handle_test_connectivity(param)

        elif action_id == 'on_poll':
            ret_val = self._handle_on_poll(param)

        return ret_val

    def finalize(self):

        # Save the state, this data is saved accross actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


if __name__ == '__main__':

    import pudb
    import argparse

    pudb.set_trace()

    argparser = argparse.ArgumentParser()

    argparser.add_argument('input_test_json', help='Input Test JSON file')
    argparser.add_argument('-u', '--username', help='username', required=False)
    argparser.add_argument('-p', '--password', help='password', required=False)

    args = argparser.parse_args()
    session_id = None

    username = args.username
    password = args.password

    if (username is not None and password is None):

        # User specified a username but not a password, so ask
        import getpass
        password = getpass.getpass("Password: ")

    if (username and password):
        try:
            print ("Accessing the Login page")
            r = requests.get("https://127.0.0.1/login", verify=False)
            csrftoken = r.cookies['csrftoken']

            data = dict()
            data['username'] = username
            data['password'] = password
            data['csrfmiddlewaretoken'] = csrftoken

            headers = dict()
            headers['Cookie'] = 'csrftoken=' + csrftoken
            headers['Referer'] = 'https://127.0.0.1/login'

            print ("Logging into Platform to get the session id")
            r2 = requests.post("https://127.0.0.1/login", verify=False, data=data, headers=headers)
            session_id = r2.cookies['sessionid']
        except Exception as e:
            print ("Unable to get session id from the platfrom. Error: " + str(e))
            exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = FortisiemConnector()
        connector.print_progress_message = True

        if (session_id is not None):
            in_json['user_session_token'] = session_id
            connector._set_csrf_info(csrftoken, headers['Referer'])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print (json.dumps(json.loads(ret_val), indent=4))

    exit(0)
