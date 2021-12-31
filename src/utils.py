def extract_argument(event: dict, argument: str) -> any:
    """
    the function extract specified argument from the event
    :param event: dict
    :param argument: str
    :return: argument value
    """
    return event.get('args', {}).get(argument, "")
