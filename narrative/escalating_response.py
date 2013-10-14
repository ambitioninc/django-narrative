def construct_escalating_response(issue, response_map):
    """
    Sometimes we need to have a response that can escalate
    if not addressed in a certain amount of time.  We support
    this in this function by constructing a response based on a
    'response_map' that maps a given response to a specific
    escalation_number (ie, how many previous responses there
    has been to this issue).
    """
    non_pass_steps = issue.get_non_pass_steps()

    return response_map.get(len(non_pass_steps), lambda x: None)(non_pass_steps)
