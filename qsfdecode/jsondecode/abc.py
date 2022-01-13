from bs4 import BeautifulSoup
from collections import OrderedDict
from qsfdecode.jsondecode.utl import tab
from qsfdecode.jsondecode.decorator import comment_method
from typing import Dict
import re


class SurveyObjectBase(OrderedDict):

    _TEXT_PIPE_RE = re.compile(r"[$][{]q://(?P<qid>QID[0-9]+)/(?P<property>[a-zA-Z]+)[}]")
    _NON_ASCII_RE_ = re.compile(r'[^\x20-\x7E]')

    class AttributeNotFound(object):
        pass

    __counter__ = 0

    def __init__(self, items, **kwargs):
        super().__init__(items, **kwargs)
        self._survey = None

    def __str__(self):
        return "{\n" + "\n".join(f"{key}: {value}" for key, value in self.items()) + "\n}"

    @property
    def survey(self):
        return self._survey

    @survey.setter
    def survey(self, value):
        self._survey = value

    def some_func(self, text_value):

        pipe = self._TEXT_PIPE_RE.match(text_value)
        if pipe is None:
            result = text_value
        else:
            qid = pipe['qid']
            property = pipe['property']
            result = self.survey.get_question(qid)[property]

        return result

    @staticmethod
    def _multi_replace_(txt, repl, ignore_case=False, whole_word_only=False):
        """
        caastools.utils._multi_replace_(text, repl, ignore_case=False, whole_word_only=False) -> str
        Performs simultaneous multi-replacement of substrings within a string
        :param txt: string in which replacements are to be performed
        :param repl: dictionary mapping substrings to be replaced with their replacements
        :param ignore_case: specifies whether to ignore case in search/replacement. Default False
        :param whole_word_only: specifies whether to replace only on whole word matches. Default False
        :return: string with replacements made
        """

        repl_str = "{0}{{0}}{0}".format("\\b" if whole_word_only else '')

        # The problem is that there is the risk of having one replacement be
        # the substring of another. Deal with this issue by sorting long to short
        replacements = sorted(repl, key=len, reverse=True)

        # Next, we can just use the regex engine to do the replacements all at once
        # Preferable to iteration because sequential replacement may cause undesired results
        replace_re = re.compile("|".join(map(lambda x: repl_str.format(re.escape(x)), replacements)),
                                re.IGNORECASE if ignore_case else 0)

        return replace_re.sub(lambda match: repl[match.group(0)], txt)

    @staticmethod
    def _sanitize_for_spss_(dirty_str, sub=None):
        """
        _sanitize_for_spss_(str, subs={}) -> str
        Sanitizes the provided string into an SPSS-Compatible identifier
        :param dirty_str: the string to be sanitized
        :param sub: A dictionary of substitutions to use in the santization process. Keys will be replaced with values
        in the sanitized string. Note that using unsanitary values will cause custom substitutions to themselves be sanitized.
        Default None
        :return: str
        """
        # SPSS has specifications on variable names. These will help ensure they are met
        max_length = 64
        invalid_chars = re.compile(r"[^a-zA-Z0-9_.]")
        invalid_starts = re.compile(r"[^a-zA-Z]+")
        subs = {} if sub is None else sub

        # Remove invalid starting characters
        start_invalid = invalid_starts.match(dirty_str)
        new_var = invalid_starts.sub('', dirty_str, count=1) if start_invalid else dirty_str

        # Possible that the process of removing starting chars could create empty string,
        # so create valid var name in that case
        if len(new_var) == 0:
            SurveyObjectBase.__counter__ += 1
            new_var = "VAR_{0}".format(SurveyObjectBase.__counter__)

        # Trim off excess characters to fit into maximum allowable length
        new_var = new_var[:max_length] if len(new_var) > max_length else new_var

        # If any custom substitutions are required, perform prior to final sanitization
        if len(subs) > 0:
            new_var = SurveyObjectBase._multi_replace_(new_var, subs)

        # locate invalid characters and replace with underscores
        replacements = {x: "_" for x in invalid_chars.findall(new_var)}
        new_var = SurveyObjectBase._multi_replace_(new_var, replacements) if len(replacements) > 0 else new_var

        return new_var


class SurveyQuestion(SurveyObjectBase):

    _content_types_ = {'ValidEmail': None, "ValidZip": "ValidZipType", "ValidDate": "ValidDateType",
                       "ValidTextOnly": None, "ValidUSState": None, "ValidPhone": None, "ValidNumber": "ValidNumber"}

    _validation_types_ = {"MinChar": "MinChars", "TotalChar": "TotalChars",
                          "None": None}
    CONTENT_TYPE = "ContentType"

    def __init__(self, items, **kwargs):
        super().__init__(items, **kwargs)

        # Qualtrics has a hard limit of 100 characters on the QuestionDescription attribute,
        # which is what is used to create value labels.
        # This causes truncation when the Configuration.QuestionDescriptionOption value is set to 'UseText'
        # Override this property with the QuestionText when QuestionDescriptionOption is 'UseText' and the two are NE
        qdo = self['Payload']['Configuration']['QuestionDescriptionOption']
        text = (BeautifulSoup(self['Payload']['QuestionText'], "lxml").get_text().replace("\n", " ").replace("'", "''"))

        # There are likely a lot of non-ascii characters in variable labels, and we need to strip them out
        text = SurveyObjectBase._NON_ASCII_RE_.sub(r'', text)

        desc = self['Payload']['QuestionDescription']
        desc = SurveyObjectBase._NON_ASCII_RE_.sub(r'', desc)
        if qdo == 'UseText' and text != desc:
            self['Payload']['QuestionDescription'] = text

    @staticmethod
    def _labels_(labels: Dict[str, str]) -> str:
        return f"\n{tab(2)}".join(f"{key} '{value}'" for key, value in labels.items())

    def create_spss_code(self, **kwargs):
        raise NotImplementedError()

    @comment_method("Value Labels")
    def create_spss_value_labels(self):

        # Each choice corresponds to a variable, but all variables have the same value labels in RO question
        value_label_defs = f'\n{tab()}/'.join(
            f"{var_name}\n{tab(2)}{self._labels_(var_labels)}"
            for var_name, var_labels in self.value_labels().items()
        )
        defs = f"VALUE LABELS\n{tab()}{value_label_defs}.\n"

        return defs

    def payload(self):
        return self.get('Payload')

    def variable_labels(self):
        raise NotImplementedError()

    def value_labels(self):
        raise NotImplementedError()

    def variable_names(self):
        raise NotImplementedError()

