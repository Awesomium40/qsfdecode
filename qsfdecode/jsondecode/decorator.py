

def comment(procedure, variable) -> str:

    return f"/******Create {procedure} for {variable}******/."


def parametrized(dec):
    def inner(*args, **kwargs):
        def repl(f):
            return dec(f, *args, **kwargs)
        return repl
    return inner


@parametrized
def comment_method(func, procedure):
    def inner(self, *args, **kwargs):
        c = comment(procedure, self['Payload']['DataExportTag']) + "\n"
        return c + func(self, *args, **kwargs)

    return inner

