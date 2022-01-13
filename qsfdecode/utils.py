
def _static_vars_(**kwargs):
    """
    Adds static variables to a decorated function
    Code taken from https://stackoverflow.com/questions/279561/
    what-is-the-python-equivalent-of-static-variables-inside-a-function
    :param kwargs:
    :return:
    """
    def decorate(func):
        for k in kwargs:
            setattr(func, k, kwargs[k])
        return func
    return decorate


def _progress_bar_(iteration, total, prefix='', suffix='', decimals=1, length=50, fill='█', print_end="\r"):
    """
    prints progress bar to the console window. Use inside of a loop to get the proper effect
    :param iteration: current iteration
    :param total: total iterations
    :param prefix: string to appear to the left of the progress bar
    :param suffix: string to appear to the right of the progress bar
    :param decimals: number of decimals to show in the pct complete
    :param length: length of the progress bar
    :param fill: character to fill in completed portion of progres bar
    :param print_end: EOL character
    :return:
    """

    percent = (iteration / float(total))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(f"\r{prefix} |{bar}| {percent:.2%} {suffix} ", end=print_end)
    # Print New Line on Complete
    if iteration == total:
        print()
