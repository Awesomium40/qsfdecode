from qsfdecode.jsondecode.questions import *
from qsfdecode.jsondecode.abc import SurveyObjectBase, SurveyQuestion
from collections import OrderedDict
import json


class SurveyObjectDecoder(json.JSONDecoder):

    _question_map_ = {'Matrix': (MatrixQuestion, MultiAnswerMatrixQuestion,),
                      'MC': (MultiChoiceQuestion, MultiAnswerMultiChoiceQuestion,),
                      "RO": RankOrderQuestion,
                      "Slider": SliderQuestion,
                      "TE": TextEntryQuestion,
                      'SBS': SideBySideQuestion}

    _block_keys_ = ('description', 'elements',)
    _survey_keys_ = ('SurveyEntry', 'SurveyElements',)
    _multi_answer_selectors = ['MAVR', 'MAHR', 'MACOL', 'MSB', 'MultipleAnswer']

    def __init__(self, *args, **kwargs):
        hook = self.object_hook if 'object_hook' not in kwargs else kwargs.pop('object_hook')

        super().__init__(object_hook=hook, *args, **kwargs)

    def _is_question_(self, data):
        return data.get('Element') == 'SQ'

    def _is_block_(self, data):
        return all(itm in self._block_keys_ for itm in data.keys())

    def _is_survey_(self, data):
        return all(itm in data for itm in self._survey_keys_)

    def object_hook(self, data):

        if self._is_survey_(data):
            cls = OrderedDict
        elif self._is_question_(data):
            question_type = data['Payload']['QuestionType']
            possible_cls = self._question_map_.get(question_type, SurveyQuestion)
            if question_type == 'MC':
                idx = int(data['Payload']['Selector'] in self._multi_answer_selectors)
                cls = possible_cls[idx]
            elif question_type == 'Matrix':
                try:
                    idx = int(data['Payload']['SubSelector'] in self._multi_answer_selectors or
                              data['Payload']['Selector'] == 'TE')
                except KeyError:
                    idx = 0
                cls = possible_cls[idx]
            else:
                cls = possible_cls

        else:
            cls = SurveyObjectBase
        
        return cls(data)

    def object_pairs_hook(self, data):
        return OrderedDict(data)

