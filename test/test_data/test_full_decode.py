from pathlib import Path
from qsfdecode import translate_to_sps, SurveyExporter
import unittest


class TestFullDecode(unittest.TestCase):

    def test_decode(self):
        se = SurveyExporter()
        sd = se.export(format='text')
        sd = sd.replace('99.1', '99')

        translate_to_sps(sd, Path(r'D:\test.sps'), include_declarations=False, lbl_include_answer=True,
                         lbl_include_question=False)
