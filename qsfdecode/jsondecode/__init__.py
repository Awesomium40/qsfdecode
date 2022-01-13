import itertools
from itertools import chain
from pathlib import Path
from qsfdecode.jsondecode.surveyobjectdecoder import SurveyObjectDecoder
from qsfdecode.jsondecode.abc import SurveyQuestion, SurveyObjectBase
import json

__all__ = ['translate_to_sps']


def translate_to_sps(
        data,
        path: Path,
        include_declarations=False,
        lbl_include_question=False,
        lbl_include_answer=False
):
    """
    Translates a QSF survey definition SPSS Syntax that defines the variables in a response dataset
    :param data: text that contains json QSF to be translated
    :param path: Path object through which to write output
    :param include_declarations: Whether to include variable declarations in the output. Default False
    :param lbl_include_question: Whether labels of matrix variables should include base question text. Default False
    :param lbl_include_answer: Whether labels of matrix variables should include answer text. Default False
    :return: None
    """

    # First step is to actually decode the JSON data into the various Question objects
    s = json.loads(data, cls=SurveyObjectDecoder)['result']

    # Questions in the trash block need to be filtered out, so get the trash block and any questions it contains
    blocks = next(filter(lambda x: x['Element'] == 'BL', s['SurveyElements']))
    trash = pop_trash(blocks)
    trash_questions = [x['QuestionID'] for x in trash['BlockElements'] if x['Type'] == 'Question']

    # It is possible that questions/blocks can exist in a survey, but not be in the flow
    # Questions that are not in the flow are not exported, even though they exist
    # In order to ensure that these questions don't make it into the conversion, process the flow element
    # to extract only blocks that are in the flow and the associated questions
    survey_flow = next(filter(lambda x: x['Element'] == 'FL', s['SurveyElements']))
    blocks_in_flow = extract_blocks(survey_flow['Payload']['Flow'])
    block_payload = blocks['Payload'].items() if hasattr(blocks['Payload'], 'items') else enumerate(blocks['Payload'])
    blocks_to_process = [entry for key, entry in block_payload
                         if entry['Type'] in ('Standard', 'Block', 'Default') and entry['ID'] in blocks_in_flow]

    questions_to_process = list(chain(*((x['QuestionID'] for x in block['BlockElements'] if x['Type'] == 'Question')
                                   for block in blocks_to_process)))

    # QSF contain data for many things, not just questions.
    # All we are interested in in the questions, so extract only those
    questions = list(
        x for x in s['SurveyElements']
        if x['Element'] == 'SQ'
        and x['Payload']['QuestionID'] in questions_to_process
        and x['Payload']['QuestionType'] != 'DB'
    )

    # Question objects generate their own SPSS code upon request, so write those calls to the specified file
    with path.open('w', encoding='utf-8') as out_file:

        for q in questions:  # type: SurveyQuestion
            try:
                out_file.write(q.create_spss_code(include_declarations=include_declarations,
                                                  lbl_include_question=lbl_include_question,
                                                  lbl_include_answer=lbl_include_answer) + "\n")
            except NotImplementedError:
                continue
            except:
                print(f"Unable to write syntax for question {q['Payload']['DataExportTag']}.")


def get_all_block_questions(survey_blocks):

    try:
        items = survey_blocks['Payload'].items()
    except AttributeError:
        items = enumerate(survey_blocks['Payload'])

    return chain(*((x['QuestionID'] for x in block['BlockElements'] if x['Type'] == 'Question') for i, block in items))


def pop_trash(blocks: SurveyObjectBase) -> SurveyObjectBase:
    """
    Pops the trash block from the payload of blocks
    :param blocks: Blocks element from a QSF survey
    :return: Trash block element
    """
    try:
        items = blocks['Payload'].items()
    except AttributeError:
        items = enumerate(blocks['Payload'])

    for i, blk in items:
        if blk['Type'] == 'Trash':
            trash = blocks['Payload'].pop(i)
            return trash


def extract_blocks(flow):

    BLOCK_TYPES = ['Standard', 'Block', 'Default']
    FLOW_TYPES = ['Branch', 'Group']
    blocks = []

    for entry in flow:
        if entry['Type'] in FLOW_TYPES:
            blocks.extend(extract_blocks(entry['Flow']))
        elif entry['Type'] in BLOCK_TYPES:
            blocks.append(entry['ID'])

    return blocks
