def recommendations(features, score, factors):
    """Create deterministic, model-informed recommendations from real UCI inputs.

    SHAP explains the model; these explicit rules turn measurable risk factors
    into possible support actions. They do not claim causal effects.
    """
    priority = 'High' if score < 8 else 'Medium'
    rules = [
        ('absences', lambda value: value is not None and float(value) > 10,
         'Attendance support', 'High absence count is a relevant academic risk factor.',
         'Schedule an attendance follow-up and monitor attendance.'),
        ('studytime', lambda value: value is not None and float(value) <= 1,
         'Study-planning support', 'Low reported study time is a relevant academic risk factor.',
         'Create a structured study schedule with manageable weekly goals.'),
        ('G1', lambda value: value is not None and float(value) < 10,
         'Targeted revision support', 'Previous-period performance is a relevant academic risk factor.',
         'Offer targeted revision planning and remedial academic support.'),
        ('G2', lambda value: value is not None and float(value) < 10,
         'Recent performance review', 'Latest previous-period performance is a relevant academic risk factor.',
         'Review recent coursework with faculty and agree on focused academic support.'),
        ('failures', lambda value: value is not None and float(value) > 0,
         'Faculty mentoring', 'Previous course failures are a relevant academic risk factor.',
         'Arrange faculty mentoring and additional academic support.'),
    ]
    output = []
    for factor, applies, title, reason, action in rules:
        try:
            if applies(features.get(factor)):
                output.append({'source': 'automatic', 'priority': priority, 'factor': factor,
                               'title': title, 'reason': reason,
                               'action': action, 'purpose': 'Model-informed support; not a guaranteed outcome.'})
        except (TypeError, ValueError):
            continue
    if score < 8 and not output:
        output.append({'source': 'automatic', 'priority': 'High', 'factor': 'risk_level',
                       'title': 'Faculty review',
                       'reason': 'The model prediction is in the high-risk range.',
                       'action': 'Prioritize the student for a faculty review and agree on appropriate support.',
                       'purpose': 'Model-informed support; not a guaranteed outcome.'})
    return output
