from qsfdecode.jsondecode.decorator import comment_method
from qsfdecode.jsondecode.abc import SurveyQuestion
from qsfdecode.jsondecode.utl import tab
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

__all__ = ['MatrixQuestion', 'MultiAnswerMatrixQuestion', 'MultiChoiceQuestion', 'MultiAnswerMultiChoiceQuestion',
           'RankOrderQuestion', 'SideBySideQuestion', 'SliderQuestion', 'TextEntryQuestion']


@dataclass(order=True)
class AnswerChoiceBase:
    sort_index: int = field(init=False, repr=False)
    value: int
    display: str
    choice_order: int

    def __post_init__(self):
        self.sort_index = self.choice_order
        if self.value == int(self.value):
            self.value = int(self.value)


@dataclass
class ChoiceBase(AnswerChoiceBase):
    has_text_entry: bool = False


@dataclass
class MatrixChoice(ChoiceBase):
    export_tag: str = ''


@dataclass
class MatrixAnswer(AnswerChoiceBase):
    recode_value: int = None
    label: str = ''

    def __post_init__(self):
        super().__post_init__()
        if int(self.recode_value) == self.recode_value:
            self.recode_value = int(self.recode_value)


@dataclass
class MCChoice(ChoiceBase):
    recode_value: int = None
    label: str = ''
    var_naming: str = ''

    def __post_init__(self):
        super().__post_init__()
        if int(self.recode_value) == self.recode_value:
            self.recode_value = int(self.recode_value)


class MatrixQuestion(SurveyQuestion):

    def __init__(self, items, **kwargs):
        super().__init__(items, **kwargs)

        # For a matrix style question, statements, or questions are the 'Choices', and responses are 'Answers'
        # Retrieve the relevant info for statements/items
        payload = self['Payload']
        statements = payload.get('Choices')
        statement_order = {x: int(x) for x in payload.get('ChoiceOrder')} \
            if payload.get('ChoiceOrder') is not None else {x: i for i, x in enumerate(payload.get('Choices'))}
        text_entry = {key: value.get('TextEntry', 'false').lower() == 'true' for key, value in statements.items()}

        # ChoiceDataExport tags are custom variable names for individual items.
        # Storage is a bit weird. If there are no tags, this value is False, but a dict otherwise
        # if ChoiceDataExportTags DNE, then the variable names for each statement are QuestionDescription_choice
        stmt_variable_names = payload.get('ChoiceDataExportTags')

        if not stmt_variable_names:
            stmt_variable_names = {key: f"{payload['DataExportTag']}_{key}" for key, value in statements.items()}
        else:
            # it can and does happen that ChoiceDataExportTags exists, but doesn't have entries or has blank entries
            # for variables. attempt to construct valid export tags for those
            i = 0
            for key in statements.keys():
                qet = stmt_variable_names.get(key)
                if qet is not None and qet.strip() == '':
                    stmt_variable_names[key] = f"{chr(65 + i)}"
                    i += 1

        sorted_topics = sorted(
            MatrixChoice(value=int(key),
                         display=str.replace(entry.get('Display'), "'", "''").encode('ascii', errors='ignore').decode(),
                         choice_order=statement_order.get(key, 0), has_text_entry=text_entry.get(key),
                         export_tag=stmt_variable_names.get(key)) for key, entry in statements.items())

        self._statements = tuple(sorted_topics)

        # For matrix style question, responses are stored in 'Answers' and related attributes
        # Answers have an order, potentially recoded, values, and value labels associated with them
        # Order of answers is stored in AnswerOrder
        # The recoded values are stored in RecodeValues if they exist, or as the keys of Answers
        # value labels are stored in VariableNaming if it exists, or as the Display attribute of Answers
        answers = payload.get('Answers')
        answer_order = {x: int(x) for x in payload.get('AnswerOrder')}
        answer_recodes = payload.get('RecodeValues', {key: key for key in answers.keys()})
        answer_labels = payload.get('VariableNaming', {key: value['Display'] for key, value in answers.items()})

        sorted_answers = sorted(
            MatrixAnswer(value=int(key),
                         display=str.replace(value.get('Display'), "'", "''").encode('ascii', errors='ignore').decode(),
                         choice_order=answer_order.get(key, 0), recode_value=float(answer_recodes.get(key)),
                         label=str.replace(answer_labels.get(key), "'", "''")) for key, value in answers.items())
        self._answers = tuple(sorted_answers)

    def create_spss_code(self, **kwargs) -> str:

        include_declarations = kwargs.get('include_declarations', False)
        lbl_include_question = kwargs.get('lbl_include_question', False)

        defs = self.create_spss_variable_declarations() if include_declarations else ''

        defs += self.create_spss_variable_labels(lbl_include_question=lbl_include_question)

        defs += self.create_spss_value_labels()

        return defs

    @comment_method("Variable Labels")
    def create_spss_variable_labels(self, lbl_include_question=False):
        defs = f"VARIABLE LABELS\n{tab()}" + \
               f"\n{tab()}".join(f"{var_name} '{label}'"
                            for var_name, label in self.variable_labels(lbl_include_question).items()) + ".\n"

        return defs

    @comment_method("Variable Declarations")
    def create_spss_variable_declarations(self):

        defs = '\n'.join(f"NUMERIC {s.export_tag} (F40.0)." for s in self._statements) + "\n"
        defs += "\n".join(f"STRING {s.export_tag}_TEXT (A2000)."
                          for s in self._statements
                          if s.has_text_entry) + "\n"

        return defs

    def value_labels(self) -> Dict[str, Dict[int, str]]:
        value_labels = {a.recode_value: a.label for a in self._answers}
        labels = {s.export_tag: value_labels for s in self._statements}

        return labels

    def variable_labels(self, include_question_text=False) -> Dict[str, str]:
        stub = f"{self['Payload']['QuestionDescription']} - " if include_question_text else ''
        labels = {s.export_tag: f'{stub}{s.display}' for s in self._statements}
        labels.update({f"{s.export_tag}_TEXT": f"{stub}{s.display} - Text"
                       for s in self._statements if s.has_text_entry})

        return labels

    def variable_names(self) -> List[str]:
        return [s.export_tag for s in self._statements]


class MultiAnswerMatrixQuestion(MatrixQuestion):

    def __init__(self, items, **kwargs):
        super().__init__(items, **kwargs)

    def create_spss_code(self, **kwargs) -> str:
        """
        returns a string that contains the SPSS syntax which defines the variables associated with the matrix question
        :param include_declarations: kwarg whether to include statements to declare the variables. Default False
        :param lbl_include_question: kwarg whether to include base question description in variable labels. Default False
        :param lbl_include_answer: kwarg whether to include response labels in variable labels. Default False
        :return: str
        """
        include_declarations = kwargs.get('include_declarations', False)
        lbl_include_question = kwargs.get('lbl_include_question', False)
        lbl_include_answer = kwargs.get('lbl_include_answer', False)

        # Each cell in the matrix has its own numeric variable which needs to be declared.
        # Each statement that has text entry has an additional string variable that needs to be declared
        defs = self.create_spss_variable_declarations() if include_declarations else ''

        # After the variables are declared, they need to be labeled
        defs += self.create_spss_variable_labels(lbl_include_question=lbl_include_question,
                                                 lbl_include_answer=lbl_include_answer)

        # Finally add the value labels
        defs += self.create_spss_value_labels()

        return defs

    @comment_method("Value Labels")
    def create_spss_variable_labels(self, lbl_include_question=False, lbl_include_answer=False):

        var_labels = self.variable_labels(include_question_text=lbl_include_question, include_answer=lbl_include_answer)
        var_label_defs = f'\n{tab()}'.join(f"{var_name} '{var_label}'" for var_name, var_label in var_labels.items())
        defs = f'VARIABLE LABELS\n{tab()}{var_label_defs}.\n'
        return defs

    @comment_method("Variable Declarations")
    def create_spss_variable_declarations(self):
        defs = '\n'.join(f"NUMERIC {s.export_tag}_{a.recode_value} (F40.0)."
                         for s in self._statements for a in self._answers) + '\n'
        defs += '\n'.join(f'STRING {s.export_tag}_TEXT (A2000).'
                          for s in self._statements if s.has_text_entry) + '\n'

        return defs

    def value_labels(self) -> Dict[str, Dict[int, str]]:

        # For multi answer matrix questions, each variable has exactly one value label
        # This value label corresponds to the value label of the answer to which the variable corresponds
        # The value for this is always 1
        value_labels = {f'{s.export_tag}_{a.recode_value}': {1: a.label}
                        for a in self._answers for s in self._statements}

        return value_labels

    def variable_labels(self, include_question_text=False, include_answer=False) -> Dict[str, str]:
        var_labels = {}

        # for multi choice matrix questions, value labels are created from
        # <QuestionDescription> - <Choice.Display> <[VariableNaming|Answer.Display]>
        # Statements can have text entry, which has its own labeled variable as well
        for statement in self._statements:  # type: MatrixChoice
            trunk = f"{self['Payload']['QuestionDescription']} - " if include_question_text else ''
            var_labels.update({f'{statement.export_tag}_{a.recode_value}':
                               f'{trunk}{statement.display}{" " + a.label if include_answer else ""}'
                               for a in self._answers})
            if statement.has_text_entry:
                var_labels.update({f'{statement.export_tag}_TEXT': f''})

        return var_labels

    def variable_names(self) -> List[str]:
        var_names = []

        # For multi choice matrix questions, each cell (combo of question and response) has its own variable
        # Statements can also have a text entry option, which will have its own variable as well
        # variable names are the combination of a statements export tag and the recode value of a response
        for statement in self._statements:  # type: MatrixChoice
            names = [f'{statement.export_tag}_{a.recode_value}' for a in self._answers]
            if statement.has_text_entry:
                names.append(f'{statement.export_tag}_TEXT')

            var_names.extend(names)

        return var_names


class MultiChoiceQuestion(SurveyQuestion):

    def __init__(self, items, **kwargs):

        super().__init__(items, **kwargs)
        payload = self['Payload']
        # Most of the important data is centered around the Choices dictionary
        choices = payload.get('Choices')
        choice_order = payload['ChoiceOrder']
        if len(choices) == 0:
            return

        # Value recodes, if they exist, are stored in the RecodeValues entry.
        # If that does not exist, then values should be recoded to themselves
        recodes: dict = payload.get('RecodeValues', {key: key for key in choices})

        # Custom value labels, if they exist, are stored in VariableNaming entry of payload
        # If that does not exist, labels are the display entry of a choice
        labels: dict = payload.get(
            'VariableNaming', {key: str.replace(choices[key]['Display'], "'", "''") for key in recodes}
        )

        # Whether a choice has text entry is stored in the TextEntry entry of a choice
        # Non-existence of this entry implies no text entry
        if isinstance(choices, list):
            x = 25
        text_entry = {key: value.get('TextEntry') == 'true' for key, value in choices.items()}

        # The order in which choices appear is stored in the ChoiceOrder entry of payload
        order = {key: i for i, key in enumerate(choices.keys())}

        # noinspection PyTypeChecker
        sorted_choices = sorted(MCChoice(int(key),
                                         str.replace(value.get('Display'), "'", "''").encode('ascii', errors='ignore').decode(),
                                         int(order.get(key)), text_entry.get(key),
                                         int(recodes.get(key)), labels.get(key))
                         for key, value in choices.items())
        self._choices = tuple(sorted_choices)  # type: Tuple[MCChoice]

        self._has_text_entry = any(c.has_text_entry for c in self._choices)

    def create_spss_code(self, **kwargs) -> str:
        """
        Emits SPSS code that defines the SPSS variables corresponding to the current instance
        :param kwargs: keyword arguments. Valid args are include_declarations (bool)
        :return: str
        """

        include_declarations = kwargs.get('include_declarations', False)

        # If declarations of variables are desired, include them
        defs = self.create_spss_variable_declarations() if include_declarations else ''

        defs += self.create_spss_variable_labels()

        defs += self.create_spss_value_labels()

        return defs

    @comment_method("Variable Declarations")
    def create_spss_variable_declarations(self):
        payload = self['Payload']
        name_base = payload['DataExportTag']
        var_names = f"NUMERIC {name_base} (F40.0).\n"
        var_names += "\n".join(f"STRING {name_base}_{c.recode_value}_TEXT (A2000)." for c in self._choices
                               if c.has_text_entry) + '\n'

        return var_names

    @comment_method("Variable labels")
    def create_spss_variable_labels(self):
        # add in the variable labels
        defs = f"VARIABLE LABELS\n{tab()}" + \
               f"\n{tab()}".join(f"{name} '{label}'" for name, label in self.variable_labels().items()) + '.\n'

        return defs

    def variable_labels(self) -> dict[str, str]:
        payload = self['Payload']
        selected_choice = ' - SelectedChoice' if self.has_text_entry else ''
        te_choice = ' - TextEntryChoice - Text' if self.has_text_entry else ''
        label_base = payload['QuestionDescription']
        name_base = payload['DataExportTag']
        labels = {name_base: f'{label_base}{selected_choice}'}
        labels.update({f'{name_base}_{c.recode_value}_TEXT': f'{label_base}{te_choice}'
                       for c in self._choices if c.has_text_entry})

        return labels

    def variable_names(self) -> list[str]:
        payload = self['Payload']
        name_base = payload['DataExportTag']
        variable_names = [name_base] + \
                         [f'{name_base}_{x.recode_value}_TEXT' for x in self._choices if x.has_text_entry]
        return variable_names

    def value_labels(self) -> Dict[str, Dict[int, str]]:
        payload = self['Payload']
        return {payload['DataExportTag']: {c.recode_value: c.label for c in self._choices}}

    @property
    def has_text_entry(self):
        return self._has_text_entry


class MultiAnswerMultiChoiceQuestion(MultiChoiceQuestion):

    def __init__(self, items, **kwargs):
        super().__init__(items, **kwargs)

    @comment_method("Variable Declarations")
    def create_spss_variable_declarations(self) -> str:
        name_base = self['Payload']['DataExportTag']
        defs = "\n".join(f"NUMERIC {name_base}_{c.recode_value} (F40.0)." for c in self._choices) + "\n"

        defs += "\n".join(f"STRING {name_base}_{c.recode_value}_TEXT (A2000)."
                          for c in self._choices if c.has_text_entry) + "\n"

        return defs

    def value_labels(self) -> Dict[str, Dict[int, str]]:
        payload = self['Payload']
        name_base = payload['DataExportTag']

        # For multi-answer MC questions, each choice becomes its own variable, and has exactly 1 value label
        # value label is 1: <choice[variableNaming|display}]>
        labels = {f'{name_base}_{c.recode_value}': {1: c.label} for c in self._choices}

        return labels

    def variable_labels(self) -> Dict[str, str]:
        payload = self['Payload']
        selected_choice = ' - SelectedChoice' if self.has_text_entry else ''
        te_choice = ' - TextEntryChoice - Text' if self.has_text_entry else ''
        label_base = payload['QuestionDescription']
        name_base = payload['DataExportTag']
        labels = {f'{name_base}_{c.recode_value}': f'{label_base}{selected_choice} {c.label}' for c in self._choices}
        labels.update({f'{name_base}_{c.recode_value}_TEXT': f'{label_base}{te_choice}'
                       for c in self._choices if c.has_text_entry})

        return labels

    def variable_names(self) -> List[str]:
        payload = self['Payload']
        name_base = payload['DataExportTag']
        variable_names = []
        for choice in self._choices:
            variable_names.append(f'{name_base}_{choice.recode_value}')
            if choice.has_text_entry:
                variable_names.append(f'{name_base}_{choice.recode_value}_TEXT')

        return variable_names


class RankOrderQuestion(SurveyQuestion):

    def __init__(self, items, **kwargs):
        super().__init__(items, **kwargs)

        payload = self['Payload']

        # Data relevant to creating variables is stored in Choices and related attributes
        # Choice order specifies order in which choices appear on the survey
        # recodes specify recoded values of eah choice, and are used in naming variables
        # VariableNaming specifies the label given to a choice and is used in variable labels
        choices = payload.get('Choices')
        choice_order = payload.get('ChoiceOrder')
        recodes = payload.get('RecodeValues', {key: int(key) for key in choices.keys()})
        var_naming = payload.get('VariableNaming', {key: value['Display'] for key, value in choices.items()})

        self._choices = [
            MCChoice(value=int(key),
                     display=str.replace(choices[key]['Display'], "'", "''").encode('ascii', errors='ignore').decode(),
                     choice_order=i, has_text_entry=False, recode_value=recodes[key],
                     var_naming=var_naming[key]) for i, key in enumerate(choice_order)]

    def create_spss_code(self, **kwargs) -> str:

        include_declarations = kwargs.get('include_declarations', False)
        lbl_include_question = kwargs.get('lbl_include_question', False)

        # If declarations are desired, include for both numeric and text questions if they exist
        defs = self.create_spss_variable_declarations() if include_declarations else ''

        # Construct the syntax for variable labels
        defs += self.create_spss_variable_labels(lbl_include_question)

        # add value label syntax
        defs += self.create_spss_value_labels()

        return defs

    @comment_method("Variable Declarations")
    def create_spss_variable_declarations(self):
        return '\n'.join(f"NUMERIC {n} (F40.0)." for n in self.variable_names()) + '\n'

    @comment_method("Variable Labels")
    def create_spss_variable_labels(self, lbl_include_question=False):

        # Each choice in a RO question has a variable label that should be defined
        var_label_defs = "\n{tab()}".join(
            f"{name} '{label}'" for name, label in self.variable_labels(lbl_include_question).items()
        )
        defs = f"VARIABLE LABELS\n{tab()}{var_label_defs}.\n"
        return defs

    def value_labels(self) -> Dict[str, Dict[int, str]]:
        export_tag = self["Payload"]["DataExportTag"]
        return {f'{export_tag}_{c.recode_value}': {c2.value: str(c2.value) for c2 in self._choices}
                for c in self._choices}

    def variable_names(self) -> List[str]:
        export_tag = self["Payload"]["DataExportTag"]
        return [f'{export_tag}_{c.recode_value}' for c in self._choices]

    def variable_labels(self, include_question_text=False) -> Dict[str, str]:
        stub = f"{self['Payload']['QuestionDescription']} - " if include_question_text else ''
        return {f'{self["Payload"]["DataExportTag"]}_{c.recode_value}': f"{stub}{c.var_naming}" for c in self._choices}


class SideBySideColumn(SurveyQuestion):

    def __init__(self, parent, entry_key, items, **kwargs):
        super().__init__(items, **kwargs)

        # Single answer SBS columns have a single variable per statement,
        # Plus an additional variable for each statement with text entry option
        # Statements are stored in the Choices attribute, other aspects stored in related attributes
        self['Payload'] = {'DataExportTag': f"{parent['Payload']['DataExportTag']}_{entry_key}"}
        p_payload = parent['Payload']
        self['QuestionDescription'] = f"{p_payload['QuestionDescription']} - {self['QuestionDescription']}"
        choices = self['Choices']  # type: dict
        choice_order = {c: i for i, c in enumerate(p_payload['ChoiceOrder'])}
        export_tags = self['ChoiceDataExportTags']
        self._column_tag = self.get('AnswerDataExportTag', entry_key)
        if not export_tags:
            export_tags = {c: f"{parent['Payload']['DataExportTag']}_{entry_key}_{c}" for c in choices}
        text_entry = {key: entry.get('TextEntry', 'false') == 'true' for key, entry in choices.items()}

        self._choices = sorted(MatrixChoice(
            value=int(key),
            display=str.replace(value['Display'].strip(), "'", "''").encode('ascii', errors='ignore').decode(),
            choice_order=choice_order[key],
            has_text_entry=text_entry[key],
            export_tag=f"{export_tags[key]}_{self._column_tag}") for key, value in choices.items())

        # Single Answer SBS columns also have Responses, just like Matrix questions do
        # Here, they are stored in the Answers and related attributes
        # Need a value, display, choice_order, recode, and label
        answers = self['Answers']
        answer_order = {key: int(key) for key in answers}
        recodes = self['RecodeValues']
        if len(recodes) == 0:
            recodes = {key: key for key in answers}
        labels = self['VariableNaming']
        if len(labels) == 0:
            labels = {key: value['Display'].strip() for key, value in answers.items()}

        self._answers = sorted(MatrixAnswer(
            value=int(key),
            display=str.replace(entry['Display'].strip(), "'", "''").encode('ascii', errors='ignore').decode(),
            choice_order=answer_order[key],
            recode_value=recodes[key],
            label=str.replace(labels[key].strip(), "'", "''")) for key, entry in answers.items())

    def _var_declaration_data_(self):
        return [(c.export_tag, c.has_text_entry,) for c in self._choices]

    def create_spss_code(self, **kwargs) -> str:

        include_declarations = kwargs.get('include_declarations', False)
        lbl_include_question = kwargs.get('lbl_include_question', False)

        # If declarations are desired, include for both numeric and text questions if they exist
        defs = self.create_spss_variable_declarations() if include_declarations else ''

        # Construct the syntax for variable labels
        defs += self.create_spss_variable_labels(lbl_include_question)

        # TextEntry columns have no value labels associated with them
        defs += self.create_spss_value_labels()

        return defs

    @comment_method("Value Labels")
    def create_spss_value_labels(self):

        # TextEntry columns have no value labels associated with them
        if self['Selector'] != 'TE':
            # Construct the syntax for value labels
            value_labels = f"\n{tab()}/".join(
                f"{var_name} {' '.join(f'{value} {chr(39)}{label}{chr(39)}' for value, label in labels.items())}"
                for var_name, labels in self.value_labels().items()
            )

            declarations = f"VALUE LABELS\n{tab()}{value_labels}.\n"
        else:
            declarations = ''

        return declarations

    @comment_method("Variable Declarations")
    def create_spss_variable_declarations(self) -> str:
        var_data = self._var_declaration_data_()
        type = 'STRING' if self['Selector'] == 'TE' else 'NUMERIC'
        format = 'A2000' if self['Selector'] == 'TE' else "F40.0"
        declarations = "\n".join(f"{type} {tag} ({format})." +
                                 f"{f'{chr(10)}STRING {tag}_TEXT (A2000).' if has_text else ''}"
                                 for tag, has_text in var_data) + "\n"

        return declarations

    def create_spss_variable_labels(self, lbl_include_question=False):

        # Construct the syntax for variable labels
        var_labels = f"\n{tab()}".join(f"{var_name} '{var_label}'"
                                 for var_name, var_label in self.variable_labels(lbl_include_question).items())
        defs = f"VARIABLE LABELS\n{tab()}{var_labels}.\n"

        return defs

    def value_labels(self) -> Dict[str, Dict[int, str]]:
        labels = {c.export_tag: {a.recode_value: a.label for a in self._answers} for c in self._choices}
        return labels

    def variable_labels(self, include_question_text=False):
        stub = f"{self['QuestionDescription']} - " if include_question_text else ''
        labels = {c.export_tag: f"{stub}{c.display}" for c in self._choices}
        return labels

    def variable_names(self) -> List[str]:
        pass


class MultiAnswerSideBySideColumn(SideBySideColumn):

    def __init__(self, parent, entry_key, items, **kwargs):
        super().__init__(parent, entry_key, items, **kwargs)

    def _var_declaration_data_(self):
        return [(f"{c.export_tag}_{a.recode_value}", c.has_text_entry,) for a in self._answers for c in self._choices]

    def value_labels(self) -> Dict[str, Dict[int, str]]:

        # Text Entry SBS have no value labels associated with them
        if self['Selector'] == 'TE':
            labels = {}
        else:
            labels = {f"{c.export_tag}_{a.recode_value}": {1: a.label} for a in self._answers for c in self._choices}
        return labels

    def variable_labels(self, include_question_text=False, include_answer=False) -> Dict[str, str]:
        var_labels = {}

        # for multi choice matrix questions, value labels are created from
        # <QuestionDescription> - <Choice.Display> <[VariableNaming|Answer.Display]>
        # Statements can have text entry, which has its own labeled variable as well
        for choice in self._choices:  # type: MatrixChoice
            trunk = f"{self['QuestionDescription']} - " if include_question_text else ''
            var_labels.update({f'{choice.export_tag}_{a.recode_value}':
                                f'{trunk}{choice.display}{" " + a.label if include_answer else ""}'
                               for a in self._answers})
            if choice.has_text_entry:
                var_labels.update({f'{choice.export_tag}_TEXT': f''})

        return var_labels

    def variable_names(self) -> List[str]:
        var_names = []

        # For multi choice matrix questions, each cell (combo of question and response) has its own variable
        # Statements can also have a text entry option, which will have its own variable as well
        # variable names are the combination of a statements export tag and the recode value of a response
        for choice in self._choices:  # type: MatrixChoice
            names = [f'{choice.export_tag}_{a.recode_value}' for a in self._answers]
            if choice.has_text_entry:
                names.append(f'{choice.export_tag}_TEXT')

            var_names.extend(names)

        return var_names


class SideBySideQuestion(SurveyQuestion):

    def __init__(self, items, **kwargs):
        super().__init__(items, **kwargs)

        self._columns: Dict[str, SideBySideColumn] = {
            key: MultiAnswerSideBySideColumn(self, key, items=(), **value)
            if value['SubSelector'] == 'MultipleAnswer'or value['Selector'] == 'TE'
            else SideBySideColumn(self, key, items=(), **value)
        for key, value in self['Payload']['AdditionalQuestions'].items()}

    def value_labels(self) -> Dict[str, Dict[int, str]]:
        labels = {}
        for key, column in self._columns.items():
            labels.update(column.value_labels())

        return labels

    def create_spss_code(self, **kwargs) -> str:
        return "\n\n".join(column.create_spss_code(**kwargs)
                           for key, column in self._columns.items())

    def variable_labels(self, include_question_text=False) -> Dict[str, str]:
        labels = {}
        for key, column in self._columns.items():
            labels.update(column.variable_labels(include_question_text=include_question_text))

        return labels

    def variable_names(self) -> List[str]:
        names = []
        for key, column in self._columns.items():
            names.extend(column.variable_names())

        return names


class SliderQuestion(SurveyQuestion):

    def __init__(self, items, **kwargs):
        super().__init__(items, **kwargs)

    def create_spss_code(self, **kwargs):

        include_declarations = kwargs.get('include_declarations', False)

        defs = self.create_spss_variable_declarations() if include_declarations else ''

        defs += self.create_spss_variable_labels()

        defs += self.create_spss_value_labels()

        return defs

    def create_spss_value_labels(self) -> str:
        return ''

    @comment_method("Variable Declarations")
    def create_spss_variable_declarations(self) -> str:
        var_decs = "\n".join(f"NUMERIC {vn} (F40.0)." for vn in self.variable_names()) + "\n"
        return var_decs

    @comment_method("Variable Labels")
    def create_spss_variable_labels(self, lbl_include_question=False) -> str:
        label_decs = f"\n{tab()}".join(f"{key} '{value}'" for key, value in self.variable_labels(lbl_include_question).items())
        return f"VARIABLE LABELS\n{tab()}{label_decs}.\n"

    def value_labels(self) -> Dict[str, Dict[int, str]]:
        return {}

    def variable_labels(self, include_question_text=False) -> Dict[str, str]:
        payload = self['Payload']
        choices = payload['Choices']
        stub = f"{payload['QuestionDescription']} - " if include_question_text else ''
        return {f"{payload['DataExportTag']}_{key}":  f"{stub}{value['Display']}" for key, value in choices.items()}

    def variable_names(self):
        payload = self['Payload']
        choices = payload['Choices']
        return [f"{payload['DataExportTag']}_{key}" for key, value in choices.items()]


class TextEntryQuestion(SurveyQuestion):

    def __init__(self, items, **kwargs):
        super().__init__(items, **kwargs)

    def value_label_declarations(self):
        return ''

    def value_labels(self) -> Dict[str, Dict[int, str]]:
        return {}

    def create_spss_code(self, **kwargs):

        include_declarations = kwargs.get('include_declarations', False)

        defs = self.create_spss_variable_declarations() if include_declarations else ''

        defs += self.create_spss_variable_labels()

        defs += self.create_spss_value_labels()

        return defs

    def create_spss_value_labels(self) -> str:
        return ''

    @comment_method("Variable Declarations")
    def create_spss_variable_declarations(self) -> str:
        return "\n".join(f"STRING {vn} (A2000)." for vn in self.variable_names()) + "\n"

    @comment_method("Variable Labels")
    def create_spss_variable_labels(self):
        labels = f"\n{tab()}".join(f"{key} '{value}'" for key, value in self.variable_labels().items())
        return f"VARIABLE LABELS\n{tab()}{labels}.\n"

    @comment_method("Variable Declarations")
    def create_spss_variable_declarations(self):
        return f"STRING {self['Payload']['DataExportTag']} (A2000).\n"

    def variable_labels(self) -> Dict[str, str]:
        return {self['Payload']['DataExportTag']: self['Payload']['QuestionDescription']}

    def variable_names(self):
        return [self['Payload']['DataExportTag']]
