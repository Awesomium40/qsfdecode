from . import constants
from . import utils
from . import exceptions
import datetime
import getpass
import io
import logging
import os
import re
import requests
import time
import zipfile


_QDC = 'Q_DATA_CENTER'
_QAT = 'Q_API_TOKEN'


logging.getLogger('exportclient').addHandler(logging.NullHandler())


class SurveyExporter(object):

    date_time_format = '%Y-%m-%dT%H:%M:%SZ'
    date_time_re = re.compile(r'^(?P<year>[0-9]{4})-(?P<month>[0-1]((?<=1)[0-2]|(?<=0)[0-9]))-' +
                              r'(?P<day>[0-3]((?<=3)[0-1]|(?<=[0-2])[0-9]))' +
                              r'(?P<time>T[0-9]{2}:[0-9]{2}:[0-9]{2}Z)$')

    def __init__(self, data_center=None, token=None, **kwargs):
        """
        Creates a new instance of ExportClient class
        :param data_center: string. Can specify either your qualtrics data center or the OS environment variable at
        which this data is stored. Optional.
        Omitting will cause a search for the OS environment variable 'Q_DATA_CENTER'
        :param token: string. Can specify either your qualtrics API key or the OS environment variable at which
        this data is stored. Optional
        Omittign will cause a search for the OS environment variable 'Q_API_KEY'
        :param kwargs:
        """

        ERR_BASE = ("parameter '{0}' was not specified and variable '{1}' was " +
                    "not found in environment variables. Please specify {0} or add {1} " +
                    "to your OS environment variables.")
        if data_center is not None:
            dc = os.environ.get(data_center, data_center)
        else:
            dc = os.environ.get(_QDC, None)
            if dc is None:
                dc = getpass.getpass("Please enter your Qualtrics data center: ")

        if token is not None:
            tkn = os.environ.get(token, token)
        else:
            tkn = os.environ.get(_QAT, None)
            if tkn is None:
                tkn = getpass.getpass("Please enter your Qualtrics API token: ")

        if tkn is None:
            raise ValueError(ERR_BASE.format('token', _QAT))
        if dc is None:
            raise ValueError(ERR_BASE.format('data_center', _QDC))

        self._data_center = dc
        self._token = tkn

        self._headers = {
            "content-type": "application/json",
        }

        self._url_base = f'https://{self._data_center}.qualtrics.com/API/v3/'

    @staticmethod
    def _await_export_(url, headers, survey_name=None, report_progress=True, update_every=0.5):
        """
        ec._await_export_(url, headers, report_progress=True) -> str
        :param url: the qualtrics request check URL for the survey responses export
        :param headers: Headers for the request
        :param report_progress: Whether to display the progress of the export process. Default True
        :param update_every: How often (in seconds) to check status of the export. Default 0.5
        :return: json object containing the request response
        """

        status = None
        prefix = f"Exporting {survey_name}: " if survey_name is not None else 'Export Progress: '
        # Periodically check the update of the export
        while status not in ('complete', 'failed'):
            response = requests.get(url, headers=headers)
            response_json = response.json()
            progress = response_json['result']['percentComplete']
            if report_progress:
                utils._progress_bar_(progress, 100, prefix=prefix)
            status = response_json['result']['status']
            time.sleep(update_every)

        if status == 'failed':
            raise exceptions.ExportException('Export Failed', response.reason)

        return response_json

    @staticmethod
    def _create_cre_body_(**kwargs):
        """

        :param format:
        :param startDate: DateTime or ISO-8601 string in UTC time. Only export responses recorded after this date
        :param endDate: DateTime or ISO-8601 string. Only export responses recorded prior to this date
        :param limit: integer. Maximum number of responses to export
        :param useLabels: Boolean specifying whether to export recode value instead of text of answer choice
        :param seenUnansweredRecode: Int with which to recode seen, but unanswered questions
        :param multiselectSeenUnansweredRecode: int with which to recode seen but unanswered choices for MS questions
        :param includeDisplayOrder: Bool specifying whether to include display order information
        :param formatDecimalAsComma: Bool specifying whehter to use commas instead of period as decimal separator
        :param timeZone: constants.TimeZone specifying response date values. None for GMT
        :param newlineReplacement: string specifying newline delimiter for CSV/TSV formats
        :param questionIds: list[str]. Only export questions with IDs in the list
        :param embeddedDataIds: list[str] Export only specified embeddeddata
        :param surveyMetadataIds: Export only specified metadata columns
        :param compress: Boolean whether to export results in compressed format
        :param exportResponsesInProgress: Boolean whether to export the in-progress responses only
        :param breakoutSets: Boolean split multi-value fields into columns
        :param filterId: Export only responses that match a saved filter
        :param allowContinuation: Boolean. Set True in order to request a continuation token when export finished
        :param continuationToken: String continuation token used to get new responses recorded since last export
        :return: object
        """

        def date_func(date_value: datetime.datetime):

            try:
                result = date_value.strftime(SurveyExporter.date_time_format)
            except AttributeError:
                match = SurveyExporter.date_time_re.search(date_value)
                result = date_value if match is not None else None
            return result

        bool_func = lambda x: str(bool(x)).lower()
        list_func = lambda items: list(items)

        keywords = {'startDate': date_func, 'endDate': date_func, 'limit': int,
                    'useLabels': bool_func, 'seenUnansweredRecode': int,
                    'multiselectSeenUnansweredRecode': int, 'includeDisplayOrder': bool,
                    'formatDecimalAsComma': bool_func, 'timeZone': lambda x: x,
                    'newlineReplacement': lambda x: x,
                    'questionIds': list_func, 'embeddedDataIds': list_func, 'surveyMetadataIds': list_func,
                    'compress': bool_func,
                    'exportResponsesInProgress': bool_func, 'breakoutSets': bool_func,
                    ' filterId': lambda x: str(x), 'allowContinuation': bool_func,
                    'continuationToken': lambda x: str(x)}
        params = {key: keywords.get(key)(value) for key, value in kwargs.items()
                  if key in keywords and keywords.get(key)(value) is not None}
        body = {key: value for key, value in params.items()} if len(params) > 0 else {}

        return body

    def _locate_survey_id_(self, locator=None):
        """
        ec._locate_survey_id(locator) -> str
        returns either the survey ID located by the callable locator
        or by the default of ExportClient._prompt_for_survey_ if locator is not specified
        :param locator: callable which returns a valid qualtrics survey ID
        :return:
        """
        locator = self._prompt_for_survey_ if locator is None or not callable(locator) else locator
        survey_id = locator()

        if survey_id is None:
            raise ValueError("Must specify valid value for either survey_id or locator")

        return survey_id

    def _prompt_for_survey_(self):

        try_again = True
        survey_id = None
        surveys = self.get_surveys()
        survey_list = {i: survey_data for i, survey_data in enumerate(surveys.items(), 1)}

        prompt = ("Surveys:\n" +
                  "\n".join(f'{key}: {value[1]}' for key, value in survey_list.items()) +
                  '\nc: cancel')

        while try_again:
            print(prompt)
            selection = input("Please select a survey: ")

            if selection.lower() == 'c':
                try_again = False
                continue

            try:
                selection = int(selection)
                survey_id = survey_list.get(selection)[0]
            except ValueError as err:
                print("invalid selection")
                try_again = input("Select again (y/n)? ").lower() == 'y'
                survey_id = None
            except TypeError as err:
                print("invalid selection")
                try_again = input("Select again (y/n)? ").lower() == 'y'
                survey_id = None
            else:
                try_again = False

        return survey_id

    def get_surveys(self):
        """
        ec.list_surveys() -> dict[str: str]
        Queries the qualtrics List Surveys API for surveys owned by the current user and returns a dictonary
        whose keys are survey ID and whose values are survey names
        :return: dict
        """
        url = f'{self._url_base}surveys'
        headers = {'x-api-token': self._token,
                   "content-type": "multipart/form-data"}
        response = requests.get(url, headers=headers)

        if not response.ok:
            raise exceptions.ExportException("Unable to retrieve list of surveys", response.reason)

        data = response.json()['result']['elements']
        return {itm.get('id'): itm.get('name') for itm in data}

    def export(self, survey_id=None, locator=None, format=constants.Format.JSON):
        """
        ec.export_survey_definition(survey_id=None, locator=None, format=constants.Format.JSON) -> object
        Exports the survey definition (qsf) associated with the survey specified by survey_id or located by locator
        :param survey_id: The ID of the survey whose definition is to be exported
        :param locator: Callable which returns the ID of the survey to be exported when survey_id is None
        :param format: constants.Format that specifies output type. Format.JSON or Format.TXT
        :return: text or JSON data, as specified by format
        """
        locator = self._prompt_for_survey_ if locator is None or not callable(locator) else locator
        survey_id = locator() if survey_id is None else survey_id

        url = f'{self._url_base}survey-definitions/{survey_id}?format=qsf'
        headers = {'x-api-token': self._token}

        response = requests.get(url, headers=headers)

        if not response.ok:
            raise exceptions.ExportException(f"Unable to export definition for survey {survey_id}. " +
                                             "Check result for details", response.reason)

        return response.json() if format == constants.Format.JSON else response.text


